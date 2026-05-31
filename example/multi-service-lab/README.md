# Multi-Service Lab Example (SiberBox multi-IP architecture)

This is the **reference example** for the SiberBox multi-IP lab format, where a
single challenge exposes multiple services, each on its own VPN IP + DNS hostname.

## Files

| File                  | Purpose                                                              |
|-----------------------|----------------------------------------------------------------------|
| `docker-compose.yaml` | The standard Docker Compose definition for the lab's services.       |
| `siberbox.json`       | Tells the manager which services to expose over VPN + their hostnames. |

## How it works

1. The user launches this lab from the platform → the manager parses `siberbox.json`.
2. For each entry in `services`, the manager allocates a VPN IP and pushes a DNS
   record (`hostname → IP`) to the user's OpenVPN client.
3. The host-agent on the worker host injects a `siberbox-gateway` sidecar that
   runs the OpenVPN client and DNATs incoming VPN traffic to the correct service
   on the internal Docker bridge.
4. The user (over VPN) can reach each service by hostname *or* IP.

So with this example, the user gets:

```
web.target    → 10.8.0.X    (nginx)
db.target     → 10.8.0.Y    (mysql:3306)
admin.target  → 10.8.0.Z    (admin panel)
```

…and the user's `/etc/resolv.conf` (pushed by the gateway) resolves those hostnames.

## `siberbox.json` schema

```json
{
  "services": {
    "<docker-compose-service-name>": {
      "hostname": "<dns.name.user.sees>"
    }
  }
}
```

- The key must match the service name in `docker-compose.yaml`.
- `hostname` is optional but recommended — without it the user only gets a raw IP.
- Services NOT listed here are still built/run but kept on the internal Docker
  network only (no VPN IP). Useful for databases, caches, etc. you don't want
  exposed (here `db` *is* exposed for completeness; in a real lab you'd usually
  drop it from `siberbox.json`).

## Single-service shortcut

For a typical web challenge you only have one user-facing service. Then:

```json
{
  "services": {
    "main": {
      "hostname": "target.lab"
    }
  }
}
```

If `siberbox.json` is **missing**, the manager falls back to auto-detecting all
services from `docker-compose.yaml` (legacy / convenience behavior).

## Building the dist zip

```
cd multi-service-lab
zip -r src.zip docker-compose.yaml siberbox.json   # plus your Dockerfile, src/, etc.
```

Upload `src.zip` via the platform's lab admin form or `POST /containers/launch`
(manager API) with `file=@src.zip` and `user_id=<uuid>`.
