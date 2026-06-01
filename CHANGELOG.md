# Changelog

All notable changes to **siberbox** — the machine-lab platform (FastAPI manager + container host-agent + OpenVPN + per-lab Docker compose).

Loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [SemVer](https://semver.org/spec/v2.0.0.html). No git tags yet; versions below are inferred from commit history. `v2.0.0` is anchored to the multi-IP redesign (a breaking change in how labs declare services).

## [Unreleased]

## [2.2.0] — 2026-06-01 (IP pool + cleanup)
### Added
- **VPN subnet bumped to `/22`** (`10.8.0.0 255.255.252.0`): 1022 slots vs the previous 253. `init_openvpn.sh` idempotently rewrites the `server` line in an existing `server.conf` and updates every CCD `ifconfig-push` netmask in place, so already-issued user `.ovpn` files keep working post-bump (override via `VPN_NETWORK` / `VPN_NETMASK` env).
- **Stale-container reaper** (`reap_stale_containers`): periodic task that sweeps `containers.status='running'` rows older than `MANAGER_REAPER_MAX_LIFETIME_MIN` (default 360 min / 6 h) and calls the existing teardown path. Backstop for orphans the akademi scheduler can't see.
- **Orphan VPN profile reaper** (`reap_orphan_vpn_profiles`): periodic task that finds non-revoked profiles whose `client_name` is `<UUID>-<svc>` but whose `Container` row is gone, and revokes them. Touches only container-service profiles; user-permanent profiles are excluded by the UUID-prefix check.
- Multi-service lab reference under `example/multi-service-lab/` (`siberbox.json` + sample `src.zip` + README).
- New helper `app/internal/openvpn_mgmt.py` for talking to the OpenVPN management interface.

### Changed
- IP allocator now subnet-agnostic — walks `NETWORK.hosts()` and picks the lowest unused IP. Previously assumed `/24` by splitting on the last octet.

### Configuration
- `MANAGER_REAPER_MAX_LIFETIME_MIN` (default `360`).
- `MANAGER_REAPER_INTERVAL_SEC` (default `300`).
- `MANAGER_VPN_REAPER_INTERVAL_SEC` (default `600`).
- `VPN_NETWORK` / `VPN_NETMASK` (defaults `10.8.0.0` / `255.255.252.0`).

## [2.1.0] — 2026-05-31 (Multi-service reachability)
### Added
- OpenVPN management interface on `127.0.0.1:7505` (loopback-only) in the manager container, enabled by both fresh and existing `server.conf` paths via an idempotent block in `init_openvpn.sh`.
- `openvpn_mgmt.kick_client(common_name)` async helper.

### Fixed
- Secondary VPN IPs (`10.8.0.62`, `.63`, …) were unreachable from the user's already-connected OpenVPN client because `add_iroute_to_ccd()` writes to the user's CCD after they connected, and OpenVPN only reads CCD at connect time. The manager now calls `kick_client(primary_service_cn)` after the iroute loop; the client auto-reconnects within 2–3 s with fresh CCD.

## [2.0.4] — Operational hardening
### Added
- Per-user VPN isolation **persisted across manager restarts**: a startup hook re-applies the ACCEPT pairs in iptables FORWARD for every running container.
- Per-lab memory/CPU caps in the host-agent so one lab can't starve the host.

### Changed
- Removed redundant `ip_forward` echo (handled by `compose.sysctls`).
- Bridge subnet moved to the `10.10.x.x` range after `172.x` collisions on the prod VPS.

### Fixed
- Per-lab subnet collisions, gateway script exec format, volume mount issues, backward compat for legacy `vpn.ovpn` location.

## [2.0.0] — Multi-IP VPN + DNS  *(breaking)*
### Added
- **Multi-service lab architecture**: a lab declares N services in `siberbox.json`, each getting its own VPN IP and DNS hostname (e.g. `target.lab`, `attacker.lab`). The host-agent injects a `siberbox-gateway` sidecar with OpenVPN client + dnsmasq + per-service DNAT.
- DNS resolution from VPN clients via the gateway's dnsmasq.
- Single-tun gateway with iroute fan-out for multi-IP routing.

### Changed *(breaking)*
- Old single-service `docker-compose.yaml` labs **must** add a `siberbox.json` to opt into the multi-IP gateway. Auto-detect fallback for legacy labs retained but not recommended for new content.

### Fixed
- Per-lab subnet uniqueness, attacker user privileges (`hacker` non-root), subnet computed early to avoid a race during gateway startup.

## [1.x] — Pre-multi-IP (historical)
Initial machine-lab-platform release: single VPN IP per lab, hand-rolled `vpn.ovpn` per service, single bridge network shared across labs. Anchored by commits up to `bbc8f5f docs: fix documentation`.
