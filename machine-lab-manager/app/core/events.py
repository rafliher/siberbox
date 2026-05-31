import asyncio
import logging
import os
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import engine, Base, SessionLocal
from app.models import User, UserRole
from app.core.security import hash_password
from app.core.config import get_settings
import datetime
from datetime import timezone

logger = logging.getLogger(__name__)

async def init_models():
    async with engine.begin() as conn:
        # create tables
        await conn.run_sync(Base.metadata.create_all)

async def create_default_admin():
    settings = get_settings()
    async with SessionLocal() as session:
        stmt = select(User).where(User.email == settings.admin_default_email)
        result = await session.execute(stmt)
        admin = result.scalar_one_or_none()
        if admin:
            return
        new_admin = User(
            email=settings.admin_default_email,
            username="admin",
            password_hash=hash_password(settings.admin_default_password),
            role=UserRole.admin
        )
        session.add(new_admin)
        await session.commit()

async def monitor_offline_hosts():
    """
    Periodically scan all hosts: if last_seen > 30s ago, mark offline.
    """
    from sqlalchemy.future import select
    from app.core.database import SessionLocal
    from app.models import ContainerHost, HostStatus

    THRESHOLD = 30  # seconds
    while True:
        async with SessionLocal() as session:
            stmt = select(ContainerHost)
            res = await session.execute(stmt)
            hosts = res.scalars().all()
            now = datetime.datetime.now(timezone.utc)
            for host in hosts:
                if not host.last_seen or (now - host.last_seen).total_seconds() > THRESHOLD:
                    if host.status != HostStatus.offline:
                        host.status = HostStatus.offline
            await session.commit()
        await asyncio.sleep(THRESHOLD)

async def restore_vpn_rules():
    """Re-apply per-user/lab ACCEPT pairs on startup (iptables are reset when manager container restarts)."""
    from sqlalchemy.future import select
    from app.core.database import SessionLocal
    from app.models import Container, ContainerStatus, VPNProfile, ContainerService
    from app.internal.vpn import apply_vpn_rule
    async with SessionLocal() as session:
        result = await session.execute(select(Container).where(Container.status == ContainerStatus.running))
        for c in result.scalars().all():
            ures = await session.execute(
                select(VPNProfile).where(VPNProfile.client_name == str(c.user_id), VPNProfile.revoked == False)
            )
            uprof = ures.scalar_one_or_none()
            if not uprof:
                continue
            sres = await session.execute(select(ContainerService).where(ContainerService.container_id == c.id))
            for s in sres.scalars().all():
                try:
                    apply_vpn_rule(str(uprof.ip_address), str(s.vpn_ip))
                except Exception as e:
                    print(f"[restore_vpn_rules] {c.id} {s.vpn_ip}: {e}")


async def reap_stale_containers():
    """Periodically stop lab containers that have outlived the safety threshold.

    Akademi's own scheduler (`utils/machineLabScheduler.js`) handles the normal
    case: it sees an instance row, sees `scheduledShutdownAt` elapsed, calls
    our DELETE. This loop is the backstop for orphans the akademi scheduler
    can't see — e.g. a launch where the akademi row was deleted before our
    DELETE ran, leaving us with a `containers` row + a live Docker project +
    consumed VPN IPs.

    Source of truth: this manager's own `containers` table. Only acts on rows
    we created. Never touches Docker objects we don't track.
    """
    from app.api.containers import stop_and_remove_container
    from app.models import Container, ContainerStatus

    MAX_LIFETIME_MIN = int(os.getenv("MANAGER_REAPER_MAX_LIFETIME_MIN", "360"))  # 6h
    INTERVAL_SEC = int(os.getenv("MANAGER_REAPER_INTERVAL_SEC", "300"))  # 5min
    logger.info(
        f"[reaper] started: lifetime>{MAX_LIFETIME_MIN}min, every {INTERVAL_SEC}s"
    )

    while True:
        try:
            threshold = datetime.datetime.now(timezone.utc) - datetime.timedelta(
                minutes=MAX_LIFETIME_MIN
            )
            async with SessionLocal() as session:
                stmt = select(Container).where(
                    Container.status == ContainerStatus.running,
                    Container.created_at < threshold,
                )
                stale = (await session.execute(stmt)).scalars().all()
                for c in stale:
                    age_min = int(
                        (
                            datetime.datetime.now(timezone.utc) - c.created_at
                        ).total_seconds()
                        / 60
                    )
                    logger.warning(
                        f"[reaper] stopping stale container {c.id} (age={age_min}min)"
                    )
                    try:
                        await stop_and_remove_container(c.id, session)
                        logger.info(f"[reaper] reaped {c.id}")
                    except Exception as e:
                        logger.error(f"[reaper] failed to reap {c.id}: {e}")
        except Exception as e:
            logger.error(f"[reaper] sweep error: {e}")
        await asyncio.sleep(INTERVAL_SEC)


async def reap_orphan_vpn_profiles():
    """Revoke VPN profiles that look like container-service profiles whose
    Container row no longer exists.

    Container-service profiles have client_name = `<container_id>-<svc>`.
    User profiles have client_name = `<user_uuid>` (no dash + svc suffix on
    the matching Container pattern). When a delete failed mid-way in the
    past, the Container row was removed but the per-service VPNProfile was
    left non-revoked, leaking VPN IPs forever.
    """
    from app.models import Container, VPNProfile
    from app.internal.vpn import remove_vpn_profile

    INTERVAL_SEC = int(os.getenv("MANAGER_VPN_REAPER_INTERVAL_SEC", "600"))  # 10min
    logger.info(f"[vpn-reaper] started: every {INTERVAL_SEC}s")

    while True:
        try:
            async with SessionLocal() as session:
                # All live container IDs, as strings, for prefix matching.
                live_ids = {
                    str(c.id) for c in (
                        await session.execute(select(Container))
                    ).scalars().all()
                }
                # All non-revoked profiles.
                profiles = (
                    await session.execute(
                        select(VPNProfile).where(VPNProfile.revoked == False)
                    )
                ).scalars().all()
                for p in profiles:
                    name = str(p.client_name)
                    # Service profile pattern: <UUID>-<svc>. Split off final segment
                    # and check the prefix matches a known container.
                    if "-" not in name:
                        continue
                    prefix = name.rsplit("-", 1)[0]
                    # A UUID has 4 dashes — make sure we're not chopping inside one
                    # by requiring the prefix to look like a UUID (5 hex groups).
                    if prefix.count("-") != 4:
                        continue
                    if prefix in live_ids:
                        continue
                    # Orphan: revoke + cleanup.
                    print(f"[vpn-reaper] revoking orphan profile {name} (ip={p.ip_address})", flush=True)
                    try:
                        await remove_vpn_profile(session, name)
                    except Exception as e:
                        logger.error(f"[vpn-reaper] failed to revoke {name}: {e}")
        except Exception as e:
            logger.error(f"[vpn-reaper] sweep error: {e}")
        await asyncio.sleep(INTERVAL_SEC)


async def startup():
    await init_models()
    await create_default_admin()
    asyncio.create_task(monitor_offline_hosts())
    asyncio.create_task(reap_stale_containers())
    asyncio.create_task(reap_orphan_vpn_profiles())
    await restore_vpn_rules()
