"""OpenVPN management-interface helper.

Used to force-disconnect a client so it reconnects and picks up CCD changes
(e.g. new `iroute` directives added after a multi-service lab launch).

Server config must declare `management 127.0.0.1 7505` (loopback-only;
no auth required since it only listens on lo inside the manager container).
"""
import asyncio
import logging
import os

logger = logging.getLogger(__name__)

MGMT_HOST = os.getenv("OPENVPN_MGMT_HOST", "127.0.0.1")
MGMT_PORT = int(os.getenv("OPENVPN_MGMT_PORT", "7505"))
MGMT_TIMEOUT = float(os.getenv("OPENVPN_MGMT_TIMEOUT", "3.0"))


async def kick_client(common_name: str) -> bool:
    """Disconnect the given OpenVPN client by CN.

    Returns True on success, including the idempotent case where the client
    wasn't connected (`ERROR: client not found`). Returns False on transport
    errors so the caller can log and continue.
    """
    if not common_name:
        return True
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(MGMT_HOST, MGMT_PORT), timeout=MGMT_TIMEOUT
        )
    except (OSError, asyncio.TimeoutError) as e:
        logger.warning("openvpn-mgmt connect failed: %s", e)
        return False

    try:
        # Drain the welcome banner.
        try:
            await asyncio.wait_for(reader.readline(), timeout=MGMT_TIMEOUT)
        except asyncio.TimeoutError:
            pass

        writer.write(f"client-kill {common_name}\n".encode())
        await writer.drain()

        # Read at most a few lines of response.
        resp_lines: list[str] = []
        for _ in range(4):
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=MGMT_TIMEOUT)
            except asyncio.TimeoutError:
                break
            if not line:
                break
            resp_lines.append(line.decode(errors="ignore").strip())
            if resp_lines[-1].startswith(("SUCCESS:", "ERROR:")):
                break

        resp = "\n".join(resp_lines)
        if "SUCCESS" in resp or "client not found" in resp.lower():
            logger.info("openvpn kick %s: %s", common_name, resp or "(no reply)")
            return True
        logger.warning("openvpn kick %s: unexpected reply %r", common_name, resp)
        return False
    finally:
        try:
            writer.write(b"quit\n")
            await writer.drain()
        except Exception:
            pass
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
