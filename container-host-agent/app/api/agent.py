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
    vpn_dir = os.path.join(work_dir, "siberbox-vpn")
    os.makedirs(vpn_dir, exist_ok=True)

    # Write VPN configs for each service
    for svc_name, svc_conf in services.items():
        ovpn_path = os.path.join(vpn_dir, f"{svc_name}.ovpn")
        with open(ovpn_path, "wb") as f:
            f.write(base64.b64decode(svc_conf.vpn_conf_base64))

    # Write DNS config for dnsmasq
    # Bind to bridge IP + all VPN IPs. Avoid 127.0.0.1 (Docker DNS DNAT conflict).
    vpn_ips = list(dns_entries.values()) if dns_entries else []
    listen_addrs = [dns_ip] + vpn_ips
    dnsmasq_conf = "bind-interfaces\n"
    dnsmasq_conf += "no-resolv\n"
    for addr in listen_addrs:
        dnsmasq_conf += f"listen-address={addr}\n"
    for hostname, ip in (dns_entries or {}).items():
        dnsmasq_conf += f"address=/{hostname}/{ip}\n"
    dnsmasq_conf += "server=8.8.8.8\n"

    with open(os.path.join(vpn_dir, "dnsmasq.conf"), "w") as f:
        f.write(dnsmasq_conf)

    # Write gateway entrypoint script
    svc_names = list(services.keys())
    # Use first service's VPN profile as the primary connection
    # Add other service IPs as secondary addresses on the same tun0
    primary_svc = svc_names[0]
    secondary_svcs = svc_names[1:]

    # Build iptables DNAT rules: forward VPN traffic to internal Docker service IPs
    # The gateway gets VPN IPs on tun devices but services listen on the Docker bridge.
    # We DNAT incoming traffic on each tun to the corresponding service's Docker IP.
    nat_rules = []
    for i, svc_name in enumerate(svc_names):
        # Traffic arriving on tun{i} destined for this gateway → forward to Docker service
        # The Docker service name resolves to its bridge IP via Docker DNS
        nat_rules.append(
            f"# Forward tun{i} traffic to {svc_name} Docker service"
        )
        nat_rules.append(
            f"iptables -t nat -A PREROUTING -i tun{i} -j DNAT --to-destination $({svc_name}_IP)"
        )
        nat_rules.append(
            f"iptables -t nat -A POSTROUTING -o eth0 -d $({svc_name}_IP) -j MASQUERADE"
        )

    lines = [
        "#!/bin/sh",
        "",
        "mkdir -p /dev/net",
        "[ -c /dev/net/tun ] || mknod /dev/net/tun c 10 200",
        "",
        "echo 1 > /proc/sys/net/ipv4/ip_forward 2>/dev/null || true",
        "",
        f"# Primary VPN: {primary_svc}",
        f"openvpn --config /vpn/{primary_svc}.ovpn --dev tun0 --daemon vpn-primary",
        "",
        "# Wait for VPN tunnel",
        "sleep 8",
        "",
    ]

    # Add secondary IPs from other service profiles onto tun0
    for svc_name in secondary_svcs:
        ip = dns_entries.get(
            next((h for h, v in dns_entries.items() if services[svc_name].hostname == h), ""),
            ""
        )
    # Actually we need the VPN IPs, not hostnames. Get them from dnsmasq.conf.

    # Simpler: parse the IPs from the ovpn CCD (they're assigned by the server)
    # But we don't know them in the gateway script. We DO know them from dns_entries.
    # dns_entries maps hostname → vpn_ip. services maps svc_name → hostname.
    for svc_name in secondary_svcs:
        hostname = services[svc_name].hostname or f"{svc_name}.lab"
        vpn_ip = dns_entries.get(hostname, "")
        if vpn_ip:
            lines.append(f"# Add secondary IP for {svc_name} ({vpn_ip})")
            lines.append(f"ip addr add {vpn_ip}/24 dev tun0 2>/dev/null || true")
            lines.append("")

    # Exclude DNS (port 53) from DNAT so dnsmasq handles it locally
    lines.append("# DNS exceptions — keep port 53 local for dnsmasq")
    all_vpn_ips = list(dns_entries.values()) if dns_entries else []
    for vip in all_vpn_ips:
        lines.append(f"iptables -t nat -A PREROUTING -d {vip} -p udp --dport 53 -j ACCEPT")
        lines.append(f"iptables -t nat -A PREROUTING -d {vip} -p tcp --dport 53 -j ACCEPT")
    lines.append("")

    lines.append("# NAT: forward VPN traffic to Docker services")
    for svc_name in svc_names:
        safe_name = svc_name.replace("-", "_")
        hostname = services[svc_name].hostname or f"{svc_name}.lab"
        vpn_ip = dns_entries.get(hostname, "")
        lines.extend([
            f'{safe_name}_IP=$(getent hosts {svc_name} | awk \'{{print $1}}\')',
            f'echo "Service {svc_name} ({vpn_ip}) -> ${safe_name}_IP"',
            f'if [ -n "${safe_name}_IP" ] && [ -n "{vpn_ip}" ]; then',
            f'  iptables -t nat -A PREROUTING -d {vpn_ip} -j DNAT --to-destination ${safe_name}_IP',
            f'  iptables -t nat -A POSTROUTING -d ${safe_name}_IP -j MASQUERADE',
            "fi",
            "",
        ])

    lines.extend([
        "",
        "# Start dnsmasq AFTER tun0 is up (binds to VPN IPs)",
        "dnsmasq --conf-file=/vpn/dnsmasq.conf --log-queries &",
        "",
        f'echo "Gateway ready with {len(svc_names)} VPN tunnels + DNS + NAT"',
        "tail -f /dev/null",
    ])
    entrypoint = "\n".join(lines) + "\n"

    entrypoint_path = os.path.join(vpn_dir, "gateway.sh")
    with open(entrypoint_path, "w") as f:
        f.write(entrypoint)
    os.chmod(entrypoint_path, 0o755)

    # Write gateway Dockerfile
    # Copy all VPN configs and dnsmasq.conf into the image so no volume mount needed
    dockerfile = "FROM alpine:3.19\n"
    dockerfile += "RUN apk add --no-cache openvpn dnsmasq iptables\n"
    dockerfile += "RUN mkdir -p /vpn\n"
    dockerfile += "COPY gateway.sh /gateway.sh\n"
    dockerfile += "COPY dnsmasq.conf /vpn/dnsmasq.conf\n"
    for svc_name in services:
        dockerfile += f"COPY {svc_name}.ovpn /vpn/{svc_name}.ovpn\n"
    dockerfile += "RUN chmod +x /gateway.sh\n"
    dockerfile += 'ENTRYPOINT ["/gateway.sh"]\n'
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

    # Add gateway service with unique /24 subnet per lab
    # Use atomic counter file to guarantee no collisions across concurrent labs
    import fcntl
    counter_file = os.path.join(WORK_DIR, ".subnet_counter")
    try:
        fd = open(counter_file, "r+")
        fcntl.flock(fd, fcntl.LOCK_EX)
        val = int(fd.read().strip() or "0")
        next_val = (val % 253) + 1  # 1-253, wraps around
        fd.seek(0)
        fd.write(str(next_val))
        fd.truncate()
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()
    except FileNotFoundError:
        next_val = 1
        with open(counter_file, "w") as fd:
            fd.write("1")
    subnet_third = next_val
    dns_ip = f"172.30.{subnet_third}.254"
    compose["networks"]["siberbox_vpn"] = {
        "driver": "bridge",
        "ipam": {
            "config": [{"subnet": f"172.30.{subnet_third}.0/24"}],
        },
    }

    compose["services"]["siberbox-gateway"] = {
        "build": {"context": "./siberbox-vpn"},
        "cap_add": ["NET_ADMIN"],
        "devices": ["/dev/net/tun:/dev/net/tun"],
        "sysctls": ["net.ipv4.ip_forward=1"],
        "networks": {
            "siberbox_vpn": {"ipv4_address": dns_ip},
        },
        "extra_hosts": ["host.docker.internal:host-gateway"],
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
