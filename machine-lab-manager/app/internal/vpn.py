# app/internal/vpn.py

import os
import glob
import subprocess
from subprocess import CalledProcessError
import datetime
from pathlib import Path
from ipaddress import IPv4Network
import asyncio
import uuid
from ipaddress import IPv4Address

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import VPNProfile

# Paths
EASYRSA_DIR = "/etc/openvpn/easy-rsa"
PKI_DIR = os.path.join(EASYRSA_DIR, "pki")
OVPN_DIR = "/etc/openvpn/pki/ovpns"
CCD_DIR = "/etc/openvpn/ccd"

VPN_SUBNET = os.getenv("VPN_INTERNAL_SUBNET", "10.8.0.0/22")
NETWORK = IPv4Network(VPN_SUBNET)
# .1 is reserved as the OpenVPN server's tun0 gateway address.
RESERVED_IPS = {NETWORK.network_address, NETWORK.network_address + 1, NETWORK.broadcast_address}


def _run_sync(cmd: list[str]) -> None:
    """Blocking: run an Easy-RSA command."""
    subprocess.check_call(cmd, cwd=EASYRSA_DIR)


def _cleanup_artifacts_sync(client: str):
    """Blocking: remove old certs/keys and .ovpn."""
    patterns = [
        os.path.join(PKI_DIR, "issued", f"{client}.*"),
        os.path.join(PKI_DIR, "private", f"{client}.*"),
        os.path.join(PKI_DIR, "reqs", f"{client}.*"),
        os.path.join(OVPN_DIR, f"{client}.ovpn"),
        os.path.join(CCD_DIR, client),
    ]
    for pat in patterns:
        for path in glob.glob(pat):
            try:
                if os.path.isdir(path):
                    subprocess.check_call(["rm", "-rf", path])
                else:
                    os.remove(path)
            except OSError:
                pass


def _make_client_sync(name: str, ip: str) -> str:
    """Blocking: build cert+key and bundle .ovpn with static IP."""
    _run_sync(["./easyrsa", "--batch", "build-client-full", name, "nopass"])

    # Read pieces...
    ca = open(os.path.join(PKI_DIR, "ca.crt")).read().strip()
    cert = open(os.path.join(PKI_DIR, "issued", f"{name}.crt")).read().strip()
    key = open(os.path.join(PKI_DIR, "private", f"{name}.key")).read().strip()
    ta = open(os.path.join(EASYRSA_DIR, "ta.key")).read().strip()

    host = os.getenv("OPENVPN_SERVER_HOST", "vpn.example.com")
    port = os.getenv("OPENVPN_SERVER_PORT", "1194")
    proto = os.getenv("OPENVPN_PROTO", "udp")
    dev = os.getenv("OPENVPN_DEV", "tun")

    conf = [
        "client",
        f"dev {dev}",
        f"proto {proto}",
        f"remote {host} {port}",
        "nobind",
        "remote-cert-tls server",
        "<ca>",
        ca,
        "</ca>",
        "<cert>",
        cert,
        "</cert>",
        "<key>",
        key,
        "</key>",
        "key-direction 1",
        "<tls-auth>",
        ta,
        "</tls-auth>",
        "verb 3",
    ]

    Path(OVPN_DIR).mkdir(parents=True, exist_ok=True)
    out_path = os.path.join(OVPN_DIR, f"{name}.ovpn")
    with open(out_path, "w") as f:
        f.write("\n".join(conf) + "\n")

    ccd_path = os.path.join(CCD_DIR, name)
    with open(ccd_path, "w") as ccd:
        ccd.write(f"ifconfig-push {ip} {NETWORK.netmask}\n")

    return out_path


def push_dns_to_ccd(client_name: str, dns_ip: str):
    """Push DNS server to a user's CCD so their VPN client uses lab DNS."""
    ccd_path = os.path.join(CCD_DIR, client_name)
    if not os.path.exists(ccd_path):
        return
    with open(ccd_path, "a") as ccd:
        ccd.write(f'push "dhcp-option DNS {dns_ip}"\n')


def add_iroute_to_ccd(client_name: str, extra_ip: str):
    """
    Add an iroute directive to a client's CCD file so the OpenVPN server
    routes traffic for extra_ip through this client's tunnel.
    Used for multi-service labs where one gateway handles multiple VPN IPs.
    """
    ccd_path = os.path.join(CCD_DIR, client_name)
    if not os.path.exists(ccd_path):
        return
    with open(ccd_path, "a") as ccd:
        ccd.write(f"iroute {extra_ip} 255.255.255.255\n")


async def create_or_get_profile(db: AsyncSession, user_id: str) -> str:
    """
    1) Check for existing non-revoked profile.
    2) Allocate a new IP if needed.
    3) Offload blocking work -> asyncio.to_thread.
    4) Persist and return the .ovpn path.
    """
    # 1) Existing?
    stmt = select(VPNProfile).where(
        VPNProfile.client_name == user_id, VPNProfile.revoked == False
    )
    res = await db.execute(stmt)
    prof = res.scalar_one_or_none()
    if prof:
        return prof.config_path

    # 2) Allocate next IP (works for any subnet size). Walk the full host range
    #    and pick the lowest IP not held by a live (non-revoked) profile.
    existing_ips = (await db.execute(
        select(VPNProfile.ip_address).where(VPNProfile.revoked == False)
    )).scalars().all()
    used = {IPv4Address(str(ip)) for ip in existing_ips if ip is not None}
    ip = None
    for candidate in NETWORK.hosts():
        if candidate in RESERVED_IPS or candidate in used:
            continue
        ip = str(candidate)
        break
    if ip is None:
        raise RuntimeError(f"No free IP in VPN subnet {NETWORK}")

    # 3) Offload cleanup & generation to threadpool
    await asyncio.to_thread(_cleanup_artifacts_sync, user_id)
    ovpn_path = await asyncio.to_thread(_make_client_sync, user_id, ip)

    # 4) Persist in DB
    new = VPNProfile(
        client_name=user_id,
        ip_address=ip,
        config_path=ovpn_path,
        revoked=False,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(new)
    await db.commit()
    await db.refresh(new)
    return ovpn_path


def apply_vpn_rule(src_ip: str, dst_ip: str):
    """
    Allow traffic only between src_ip and dst_ip over tun0.
    Inserts two ACCEPT rules (src→dst and dst→src) in FORWARD.
    """
    src = str(src_ip)
    dst = str(dst_ip)
    for s, d in ((src, dst), (dst, src)):
        cmd = [
            "iptables",
            "-I",
            "FORWARD",
            "-i",
            "tun0",
            "-o",
            "tun0",
            "-s",
            s,
            "-d",
            d,
            "-j",
            "ACCEPT",
        ]
        subprocess.check_call(cmd)


def remove_vpn_rule(ip: str):
    """
    Remove all FORWARD-chain rules on tun0 where -s ip or -d ip.
    We list rules, find those matching, convert -A → -D, and delete.
    """
    ip = str(ip)
    if not ip:
        return

    # Fetch all FORWARD rules
    try:
        raw = subprocess.check_output(["iptables", "-S", "FORWARD"], text=True)
    except CalledProcessError:
        return

    for line in raw.splitlines():
        # Look for a rule on tun0→tun0 that mentions this IP
        if (
            "-i tun0" in line
            and "-o tun0" in line
            and (f"-s {ip}" in line or f"-d {ip}" in line)
        ):
            parts = line.split()
            # parts = ["-A", "FORWARD", ..., "-j", "ACCEPT"]
            parts[0] = "-D"  # change append to delete
            cmd = ["iptables"] + parts
            try:
                subprocess.check_call(cmd)
            except CalledProcessError:
                # maybe someone already removed it
                pass


async def remove_vpn_profile(db: AsyncSession, user_id: uuid.UUID | str):
    """
    Mark profile revoked, drop iptables rule, and clean up all VPN files.
    """
    stmt = select(VPNProfile).where(
        VPNProfile.client_name == str(user_id), VPNProfile.revoked == False
    )
    res = await db.execute(stmt)
    profiles_to_cleanup = []
    
    for prof in res.scalars().all():
        prof.revoked = True
        # Remove iptables rules for this IP
        remove_vpn_rule(prof.ip_address)
        profiles_to_cleanup.append(str(user_id))
            
    await db.commit()
    
    # Clean up all VPN files after successful database commit
    for client_name in profiles_to_cleanup:
        await asyncio.to_thread(_cleanup_artifacts_sync, client_name)
