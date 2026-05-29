# app/api/containers.py
import uuid
import base64
import json
import datetime
import zipfile
import io
import yaml
from pydantic import BaseModel, IPvAnyAddress
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import httpx

from app.api.deps import get_db, get_current_admin
from app.models import (
    ContainerHost,
    HostStatus,
    Container,
    ContainerStatus,
    ContainerService,
    VPNProfile,
)

from app.internal.vpn import (
    create_or_get_profile,
    apply_vpn_rule,
    remove_vpn_rule,
    remove_vpn_profile,
    add_iroute_to_ccd,
    push_dns_to_ccd,
)

router = APIRouter(
    prefix="/containers",
    tags=["containers"],
    dependencies=[Depends(get_current_admin)],
)


# ─── Response Models ─────────────────────────────────────────────────

class ServiceInfo(BaseModel):
    service_name: str
    hostname: Optional[str] = None
    vpn_ip: str

class ContainerLaunchResponse(BaseModel):
    id: str
    host_id: uuid.UUID
    services: list[ServiceInfo]

class ContainerInfoResponse(BaseModel):
    id: str
    host_id: str
    user_id: str
    created_at: datetime.datetime
    name: str
    status: str
    services: list[ServiceInfo]


# ─── Helpers ─────────────────────────────────────────────────────────

def _parse_siberbox_manifest(zip_data: bytes) -> dict:
    """
    Extract siberbox.json from the ZIP if it exists.

    siberbox.json format:
    {
        "services": {
            "web": { "hostname": "web.lab" },
            "db":  { "hostname": "db.lab" },
            "vpn": { "hostname": "attacker.lab" }
        }
    }

    If no siberbox.json, falls back to reading docker-compose.yml
    and exposing all services (except internal ones).
    """
    try:
        with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
            # Try siberbox.json first
            for name in z.namelist():
                if name.endswith("siberbox.json"):
                    return json.loads(z.read(name))

            # Fallback: parse docker-compose.yml to discover services
            for name in z.namelist():
                if name.endswith(("docker-compose.yml", "docker-compose.yaml")):
                    compose = yaml.safe_load(z.read(name))
                    services = {}
                    for svc_name in compose.get("services", {}):
                        services[svc_name] = {"hostname": f"{svc_name}.lab"}
                    return {"services": services}
    except Exception:
        pass

    return {"services": {}}


# ─── Launch ──────────────────────────────────────────────────────────

@router.post(
    "/launch",
    response_model=ContainerLaunchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Launch containerized environment",
    description=(
        "Upload a Docker Compose environment with multi-service VPN support. "
        "Each service gets its own VPN IP and optional DNS hostname. "
        "Include a siberbox.json in the ZIP to control which services are exposed."
    ),
)
async def launch_container(
    user_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    # 1) Read ZIP and parse manifest
    data = await file.read()
    encoded_zip = base64.b64encode(data).decode()
    manifest = _parse_siberbox_manifest(data)
    exposed_services = manifest.get("services", {})

    if not exposed_services:
        raise HTTPException(
            status_code=400,
            detail="No services found. Include siberbox.json or docker-compose.yml in the ZIP.",
        )

    # 2) Pick a healthy host with capacity
    stmt = select(ContainerHost).where(
        ContainerHost.status != HostStatus.offline,
        ContainerHost.cpu_percent < 90,
        ContainerHost.mem_percent < 90,
        ContainerHost.current_containers < ContainerHost.max_containers,
    ).order_by(ContainerHost.current_containers)
    host = (await db.execute(stmt)).scalar_one_or_none()
    if not host:
        raise HTTPException(status_code=503, detail="No available host")

    # 3) Create/fetch user's VPN profile
    try:
        await create_or_get_profile(db, str(user_id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"User VPN profile failed: {e}")

    stmt = select(VPNProfile).where(
        VPNProfile.client_name == str(user_id),
        VPNProfile.revoked == False,
    )
    user_prof = (await db.execute(stmt)).scalar_one_or_none()
    if not user_prof:
        raise HTTPException(status_code=500, detail="User VPN profile missing")

    # 4) Generate container ID
    container_id = str(uuid.uuid4())

    # 5) Create VPN profile for EACH exposed service
    service_vpn_configs = {}  # service_name -> {ip, ovpn_base64, profile_id}
    dns_entries = {}  # hostname -> vpn_ip

    for svc_name, svc_conf in exposed_services.items():
        profile_name = f"{container_id}-{svc_name}"
        try:
            ovpn_path = await create_or_get_profile(db, profile_name)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"VPN profile for service '{svc_name}' failed: {e}",
            )

        stmt = select(VPNProfile).where(
            VPNProfile.client_name == profile_name,
            VPNProfile.revoked == False,
        )
        svc_prof = (await db.execute(stmt)).scalar_one_or_none()
        if not svc_prof:
            raise HTTPException(status_code=500, detail=f"VPN profile missing for {svc_name}")

        with open(ovpn_path, "rb") as f:
            ovpn_b64 = base64.b64encode(f.read()).decode()

        service_vpn_configs[svc_name] = {
            "ip": str(svc_prof.ip_address),
            "ovpn_base64": ovpn_b64,
            "profile_id": svc_prof.id,
        }

        hostname = svc_conf.get("hostname", f"{svc_name}.lab")
        dns_entries[hostname] = str(svc_prof.ip_address)

    # 5b) Add iroutes: the primary (first) service's CCD gets iroutes for all others
    # This tells OpenVPN server to route secondary IPs through the primary client tunnel
    svc_list = list(service_vpn_configs.items())
    if len(svc_list) > 1:
        primary_profile_name = f"{container_id}-{svc_list[0][0]}"
        for _, conf in svc_list[1:]:
            add_iroute_to_ccd(primary_profile_name, conf["ip"])

    # Also need a server-side route for each secondary IP
    # OpenVPN needs `route` in server.conf OR iroute in CCD
    # iroute in CCD tells OpenVPN to route that IP through this client

    # 6) Send to host agent
    agent_url = f"http://{host.ip}:{host.api_port}/agent/containers"
    payload = {
        "name": container_id,
        "docker_zip_base64": encoded_zip,
        "services": {
            svc_name: {
                "vpn_conf_base64": conf["ovpn_base64"],
                "hostname": list(dns_entries.keys())[i],
            }
            for i, (svc_name, conf) in enumerate(service_vpn_configs.items())
        },
        "dns_entries": dns_entries,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            agent_url,
            json=payload,
            headers={"X-Server-Key": host.cred_ref},
            timeout=600.0,
        )

    if resp.status_code != status.HTTP_201_CREATED:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Agent failed: {resp.text}",
        )

    # 7) Persist container + services in DB
    container = Container(
        id=container_id,
        user_id=user_id,
        host_id=host.id,
        name=container_id,
        status=ContainerStatus.running,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(container)

    service_infos = []
    for svc_name, conf in service_vpn_configs.items():
        hostname = next(
            (h for h, ip in dns_entries.items() if ip == conf["ip"]), None
        )
        svc = ContainerService(
            container_id=container_id,
            service_name=svc_name,
            hostname=hostname,
            vpn_ip=conf["ip"],
            vpn_profile_id=conf["profile_id"],
        )
        db.add(svc)
        service_infos.append(ServiceInfo(
            service_name=svc_name,
            hostname=hostname,
            vpn_ip=conf["ip"],
        ))

    host.current_containers += 1
    await db.commit()

    # 8) Apply iptables rules: user ↔ each service
    for conf in service_vpn_configs.values():
        apply_vpn_rule(user_prof.ip_address, conf["ip"])

    # 9) Push DNS to user — gateway's primary IP serves dnsmasq
    primary_ip = svc_list[0][1]["ip"]
    push_dns_to_ccd(str(user_id), primary_ip)

    return ContainerLaunchResponse(
        id=container_id,
        host_id=host.id,
        services=service_infos,
    )


# ─── Restart ─────────────────────────────────────────────────────────

@router.post(
    "/{container_id}/restart",
    status_code=status.HTTP_200_OK,
    summary="Restart container",
)
async def restart_container(
    container_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Container).where(Container.id == container_id)
    cont = (await db.execute(stmt)).scalar_one_or_none()
    if not cont:
        raise HTTPException(status_code=404, detail="Container not found")

    host = await db.get(ContainerHost, cont.host_id)
    if not host:
        raise HTTPException(status_code=500, detail="Host missing")

    agent_url = f"http://{host.ip}:{host.api_port}/agent/containers/{cont.name}/restart"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            agent_url,
            headers={"X-Server-Key": host.cred_ref},
            timeout=30.0,
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Agent restart failed: {resp.text}",
        )

    cont.status = ContainerStatus.running
    await db.commit()
    return {"detail": "Container restarted successfully"}


# ─── Stop & Remove ───────────────────────────────────────────────────

@router.delete(
    "/{container_id}",
    status_code=status.HTTP_200_OK,
    summary="Stop and remove container",
)
async def stop_container(
    container_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Container).where(Container.id == container_id)
    cont = (await db.execute(stmt)).scalar_one_or_none()
    if not cont:
        raise HTTPException(status_code=404, detail="Container not found")

    host = await db.get(ContainerHost, cont.host_id)
    if not host:
        raise HTTPException(status_code=500, detail="Host missing")

    # Tell agent to remove
    agent_url = f"http://{host.ip}:{host.api_port}/agent/containers/{cont.name}"
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            agent_url,
            headers={"X-Server-Key": host.cred_ref},
            timeout=30.0,
        )
    if resp.status_code not in (200, 202, 204, 404):
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Agent delete failed: {resp.text}",
        )

    # Remove VPN profiles for all services
    svcs = (await db.execute(
        select(ContainerService).where(ContainerService.container_id == container_id)
    )).scalars().all()
    for svc in svcs:
        profile_name = f"{container_id}-{svc.service_name}"
        await remove_vpn_profile(db, profile_name)

    # Remove container record (cascades to container_services)
    await db.delete(cont)
    host.current_containers = max(0, host.current_containers - 1)
    await db.commit()
    return {"detail": "Container stopped and removed successfully"}


# ─── Inspect ─────────────────────────────────────────────────────────

@router.get(
    "/{container_id}",
    response_model=ContainerInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="Inspect container status and services",
)
async def inspect_container(
    container_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Container).where(Container.id == container_id)
    cont = (await db.execute(stmt)).scalar_one_or_none()
    if not cont:
        raise HTTPException(status_code=404, detail="Container not found")

    # Get services
    svcs = (await db.execute(
        select(ContainerService).where(ContainerService.container_id == container_id)
    )).scalars().all()

    # Get live status from agent
    host = await db.get(ContainerHost, cont.host_id)
    agent_status = "unknown"
    if host:
        try:
            agent_url = f"http://{host.ip}:{host.api_port}/agent/containers"
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    agent_url,
                    headers={"X-Server-Key": host.cred_ref},
                    timeout=10.0,
                )
            live = resp.json()
            info = next((c for c in live if cont.name in c["name"]), None)
            if info:
                agent_status = info.get("status", "unknown")
        except Exception:
            agent_status = "unreachable"

    return ContainerInfoResponse(
        id=container_id,
        host_id=str(cont.host_id),
        user_id=str(cont.user_id),
        created_at=cont.created_at,
        name=cont.name,
        status=agent_status,
        services=[
            ServiceInfo(
                service_name=s.service_name,
                hostname=s.hostname,
                vpn_ip=str(s.vpn_ip),
            )
            for s in svcs
        ],
    )


# ─── List All ────────────────────────────────────────────────────────

@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="List all containers",
)
async def list_all_containers(
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Container)
    result = await db.execute(stmt)
    containers = result.scalars().all()
    return containers
