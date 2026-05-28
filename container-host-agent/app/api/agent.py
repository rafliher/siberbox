import os
import subprocess
import zipfile
import base64
import shutil
import datetime
import json
import textwrap

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import docker
import psutil

from app.api.deps import get_server_key
from app.core.config import settings

router = APIRouter(
    prefix="/agent",
    tags=["agent"],
    dependencies=[Depends(get_server_key)],
)

client = docker.from_env()
WORK_DIR = "/opt/containers"
os.makedirs(WORK_DIR, exist_ok=True)


# ─── Schemas ─────────────────────────────────────────────────────────

class ContainerInfo(BaseModel):
    id: str
    name: str
    image: str
    status: str


class ServiceVPNConf(BaseModel):
    vpn_conf_base64: str
    hostname: str | None = None


class StartContainerReq(BaseModel):
    name: str
    docker_zip_base64: str
    # New multi-service format
    services: dict[str, ServiceVPNConf] | None = None
    dns_entries: dict[str, str] | None = None  # hostname -> vpn_ip
    # Legacy single-service format (backward compatible)
    vpn_conf_base64: str | None = None


class ActionResponse(BaseModel):
    name: str
    status: str


# ─── Helpers ─────────────────────────────────────────────────────────

def _inject_gateway(work_dir: str, services: dict, dns_entries: dict):
    """
    Inject a VPN gateway sidecar into the docker-compose.
    The gateway runs:
    - One OpenVPN client per exposed service
    - dnsmasq for DNS resolution of hostnames to VPN IPs
    Each original service routes its traffic through the gateway.
    """
    # Write VPN configs for each service
    vpn_dir = os.path.join(work_dir, "siberbox-vpn")
    os.makedirs(vpn_dir, exist_ok=True)

    for svc_name, svc_conf in services.items():
        ovpn_path = os.path.join(vpn_dir, f"{svc_name}.ovpn")
        with open(ovpn_path, "wb") as f:
            f.write(base64.b64decode(svc_conf.vpn_conf_base64))

    # Write DNS config for dnsmasq
    dnsmasq_conf = ""
    for hostname, ip in (dns_entries or {}).items():
        dnsmasq_conf += f"address=/{hostname}/{ip}\n"
    # Also resolve .lab TLD
    dnsmasq_conf += "server=8.8.8.8\n"

    with open(os.path.join(vpn_dir, "dnsmasq.conf"), "w") as f:
        f.write(dnsmasq_conf)

    # Write gateway entrypoint script
    svc_names = list(services.keys())
    ovpn_cmds = []
    for i, svc_name in enumerate(svc_names):
        # Each VPN client uses a different tun device
        ovpn_cmds.append(
            f"openvpn --config /vpn/{svc_name}.ovpn --dev tun{i} --daemon vpn-{svc_name}"
        )

    entrypoint = textwrap.dedent(f"""\
        #!/bin/sh
        set -e

        # Create tun devices
        mkdir -p /dev/net
        [ -c /dev/net/tun ] || mknod /dev/net/tun c 10 200

        # Start dnsmasq
        dnsmasq --conf-file=/vpn/dnsmasq.conf --no-daemon --log-queries &

        # Start OpenVPN clients
        {chr(10).join(ovpn_cmds)}

        # Wait for VPN tunnels to come up
        sleep 5

        # Enable forwarding
        echo 1 > /proc/sys/net/ipv4/ip_forward

        # Keep running
        echo "Gateway ready with {len(svc_names)} VPN tunnels + DNS"
        tail -f /dev/null
    """)

    entrypoint_path = os.path.join(vpn_dir, "gateway.sh")
    with open(entrypoint_path, "w") as f:
        f.write(entrypoint)
    os.chmod(entrypoint_path, 0o755)

    # Write gateway Dockerfile
    dockerfile = textwrap.dedent("""\
        FROM alpine:3.19
        RUN apk add --no-cache openvpn dnsmasq iptables
        COPY gateway.sh /gateway.sh
        RUN chmod +x /gateway.sh
        ENTRYPOINT ["/gateway.sh"]
    """)
    with open(os.path.join(vpn_dir, "Dockerfile"), "w") as f:
        f.write(dockerfile)

    # Read existing docker-compose.yml
    compose_path = None
    for name in ("docker-compose.yml", "docker-compose.yaml"):
        p = os.path.join(work_dir, name)
        if os.path.exists(p):
            compose_path = p
            break

    if not compose_path:
        raise HTTPException(status_code=400, detail="No docker-compose.yml found in ZIP")

    import yaml
    with open(compose_path) as f:
        compose = yaml.safe_load(f)

    # Ensure networks section exists
    if "networks" not in compose:
        compose["networks"] = {}
    compose["networks"]["siberbox_vpn"] = {"driver": "bridge"}

    # Add gateway service
    dns_ip = "172.28.0.2"  # Fixed IP for DNS server
    compose["networks"]["siberbox_vpn"] = {
        "driver": "bridge",
        "ipam": {
            "config": [{"subnet": "172.28.0.0/16"}],
        },
    }

    compose["services"]["siberbox-gateway"] = {
        "build": {"context": "./siberbox-vpn"},
        "cap_add": ["NET_ADMIN"],
        "devices": ["/dev/net/tun:/dev/net/tun"],
        "volumes": [
            "./siberbox-vpn:/vpn:ro",
        ],
        "networks": {
            "siberbox_vpn": {"ipv4_address": dns_ip},
        },
        "restart": "unless-stopped",
    }

    # Update existing services:
    # - Remove NET_ADMIN/tun from original services (gateway handles VPN now)
    # - Add siberbox_vpn network
    # - Set DNS to gateway
    for svc_name, svc_conf in compose.get("services", {}).items():
        if svc_name == "siberbox-gateway":
            continue

        # Add to VPN network
        if "networks" not in svc_conf:
            svc_conf["networks"] = {}
        if isinstance(svc_conf["networks"], list):
            svc_conf["networks"].append("siberbox_vpn")
        else:
            svc_conf["networks"]["siberbox_vpn"] = {}

        # Point DNS to gateway
        svc_conf["dns"] = [dns_ip]

        # Remove VPN-related caps from original services (gateway handles it)
        if "cap_add" in svc_conf:
            svc_conf["cap_add"] = [c for c in svc_conf["cap_add"] if c != "NET_ADMIN"]
            if not svc_conf["cap_add"]:
                del svc_conf["cap_add"]
        if "devices" in svc_conf:
            svc_conf["devices"] = [d for d in svc_conf["devices"] if "tun" not in str(d)]
            if not svc_conf["devices"]:
                del svc_conf["devices"]

    # Write modified compose
    with open(compose_path, "w") as f:
        yaml.dump(compose, f, default_flow_style=False, sort_keys=False)


# ─── List containers ─────────────────────────────────────────────────

@router.get("/containers", response_model=list[ContainerInfo])
def list_containers():
    ctrs = client.containers.list()
    return [
        ContainerInfo(
            id=c.id,
            name=c.name,
            image=c.image.tags[0] if c.image.tags else "",
            status=c.status,
        )
        for c in ctrs
    ]


# ─── Start container ─────────────────────────────────────────────────

@router.post(
    "/containers",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Deploy environment with multi-service VPN + DNS",
)
def start_container(req: StartContainerReq):
    work_dir = os.path.join(WORK_DIR, req.name)

    # Clean old project
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir)

    # Extract ZIP
    ctx_zip = os.path.join(work_dir, "context.zip")
    with open(ctx_zip, "wb") as f:
        f.write(base64.b64decode(req.docker_zip_base64))
    with zipfile.ZipFile(ctx_zip, "r") as z:
        z.extractall(work_dir)
    os.remove(ctx_zip)

    if req.services:
        # Multi-service mode: inject VPN gateway sidecar
        _inject_gateway(work_dir, req.services, req.dns_entries or {})
    elif req.vpn_conf_base64:
        # Legacy single-service mode: write vpn.ovpn as before
        vpn_path = os.path.join(work_dir, "vpn.ovpn")
        with open(vpn_path, "wb") as f:
            f.write(base64.b64decode(req.vpn_conf_base64))

    # Launch
    try:
        subprocess.run(
            ["docker", "compose", "up", "-d", "--build"],
            cwd=work_dir,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"docker compose up failed: {e}")

    return ActionResponse(name=req.name, status="started")


# ─── Restart ─────────────────────────────────────────────────────────

@router.post(
    "/containers/{name}/restart",
    response_model=ActionResponse,
    summary="Rebuild & restart environment",
)
def restart_container(name: str):
    work_dir = os.path.join(WORK_DIR, name)
    if not os.path.isdir(work_dir):
        raise HTTPException(status_code=404, detail="Environment not found")

    try:
        subprocess.run(["docker", "compose", "build"], cwd=work_dir, check=True)
        subprocess.run(["docker", "compose", "up", "-d"], cwd=work_dir, check=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Restart failed: {e}")

    return ActionResponse(name=name, status="restarted")


# ─── Remove ──────────────────────────────────────────────────────────

@router.delete(
    "/containers/{name}",
    response_model=ActionResponse,
    summary="Remove environment",
)
def remove_container(name: str):
    work_dir = os.path.join(WORK_DIR, name)
    if not os.path.isdir(work_dir):
        raise HTTPException(status_code=404, detail="Environment not found")

    try:
        subprocess.run(
            ["docker", "compose", "down", "--volumes"],
            cwd=work_dir,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"docker compose down failed: {e}")

    shutil.rmtree(work_dir)
    return ActionResponse(name=name, status="removed")


# ─── Health ──────────────────────────────────────────────────────────

@router.get("/health", status_code=status.HTTP_200_OK)
def health():
    uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())
    running = len(client.containers.list())
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.5)
    return {
        "uptime_seconds": int(uptime.total_seconds()),
        "running_containers": running,
        "mem_percent": mem.percent,
        "cpu_percent": cpu,
    }
