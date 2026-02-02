# SIBERBOX Platform Architecture Specification

---

## 1. System Overview

SIBERBOX is a distributed container orchestration platform designed for per-user isolated CTF challenge deployment. Each user receives their own containerized environment accessible via VPN, with strict network isolation enforced through iptables rules.

### Key Features

- Multi-host Docker container orchestration
- Per-user VPN profiles with static IP assignment
- iptables-based network segmentation
- RESTful API for programmatic control
- Real-time host health monitoring
- Automatic load balancing across container hosts

---

## 2. Architecture Diagram

![SIBERBOX System Architecture](./images/architecture.png)

```
                    [Admin / C2]
                          |
                    (HTTPS :8000)
                          |
                          v
        +-----------------------------------+
        |   Manager & VPN Host              |
        |                                   |
        |   [FastAPI API]  [PostgreSQL 16]  |
        |   [OpenVPN Server (UDP 1194)]     |
        |   [Placement Engine]               |
        +-----------------------------------+
                /           |           \
               /  (HTTPS)   |  (HTTPS)  \
              /   :8003     |   :8003    \
             v              v             v
    +-------------+  +-------------+  +-------------+
    | Host Agent 1|  | Host Agent 2|  | Host Agent N|
    |             |  |             |  |             |
    | [Docker]    |  | [Docker]    |  | [Docker]    |
    +-------------+  +-------------+  +-------------+
         |                 |                 |
         | (VPN tunnel)    |                 |
         +--------+--------+-----------------+
                  |
                  v
              [End User]
         (OpenVPN :1194/udp)
```

### System Design Principles

- **Manager + VPN Co-location**: OpenVPN server runs on the same host as the Manager API stack. Admin access to the API is restricted through JWT authentication tokens.
- **Traffic Routing**: Users connect to containers through OpenVPN tunneling. The Manager API endpoints are protected by JWT authentication and not directly exposed to container networks.
- **Distributed Orchestration**: Container host agents authenticate with JWT server keys issued during registration. The Manager coordinates deployment across multiple physical hosts.
- **Per-User Segmentation**: Every CTF challenge instance is isolated via VPN routing rules. User A cannot reach User B's containers, even if deployed on the same physical host.

---

## 3. Core Components

### Manager (Control Plane)

**Location**: Central orchestration server  
**Port Bindings**: 8000/tcp (API), 1194/udp (OpenVPN)

Components:
- FastAPI REST API server
- PostgreSQL 16 database for state persistence
- OpenVPN server with Easy-RSA PKI
- Container placement scheduler (least-loaded algorithm)
- iptables firewall rule manager
- JWT authentication system

Responsibilities:
- Host registration and health tracking
- VPN profile generation and revocation
- Container deployment coordination
- User-to-container network isolation enforcement
- Load balancing across container hosts

### Container Host Agent (Execution Plane)

**Location**: Each container host machine  
**Port Binding**: 8003/tcp (API)

Components:
- FastAPI REST API server
- Docker Engine client interface
- System resource monitor (psutil)
- Heartbeat reporting loop

Responsibilities:
- Receive and unpack docker-compose bundles
- Deploy containers in isolated workspaces
- Report CPU, memory, and container count to Manager
- Execute lifecycle operations (start, restart, stop, remove)
- Server key authentication for all Manager requests

### Network Architecture

```
VPN Flow:
[User] ---(OpenVPN:1194)---> [Manager tun0] ---(iptables routing)---> [Container on Host N]

Control Flow:
[Admin] ---(HTTPS:8000)---> [Manager API]
[Manager] ---(HTTPS:8003)---> [Host Agent]
```

Each user VPN profile is assigned a static IP from the 10.8.0.0/24 subnet. iptables rules on the Manager's tun0 interface enforce bidirectional allow rules between user IP and container IP only. Inter-user traffic is blocked by default deny policy.

---

## 4. Database Schema

![Database Entity Relationships](./images/entities.png)

### users
```
id            uuid primary key
email         string unique
username      string
password_hash string (bcrypt)
role          enum(admin, user)
state         enum(active, suspended, deleted)
created_at    timestamp
```

### container_hosts
```
id                 uuid primary key
hostname           string
ip                 inet (management IP)
ssh_port           integer
api_port           integer (default 8003)
max_containers     integer
current_containers integer
cpu_percent        integer (0-100)
mem_percent        integer (0-100)
status             enum(offline, healthy)
last_seen          timestamp with timezone
cred_ref           string (server_key hash)
created_at         timestamp
```

### containers
```
id         uuid primary key
user_id    uuid (references users.id)
host_id    uuid (references container_hosts.id)
name       string unique
status     enum(pending, running, stopped, error)
created_at timestamp
```

### vpn_profiles
```
id          uuid primary key
client_name string unique
config_path text (filesystem path to .ovpn)
revoked     boolean
created_at  timestamp
ip_address  inet unique (10.8.0.x)
```

### api_keys
```
id         uuid primary key
owner_type enum(admin, host)
owner_id   uuid (user or container_host)
key_hash   string (SHA-256 of JWT)
created_at timestamp
expires_at timestamp (nullable, null = no expiry)
```

### Relationships

- `container_hosts.id` → `containers.host_id` (one-to-many)
- `vpn_profiles.client_name` → linked to user or container (flexible association)
- `api_keys.owner_id` → references either users or container_hosts (polymorphic)

---

## 5. Manager API Reference

### Authentication Headers

| Header | Usage | Validation |
|--------|-------|------------|
| `X-Admin-Key` | Admin operations | JWT validated against `api_keys` table |
| `X-Server-Key` | Host agent heartbeat | JWT validated against `container_hosts.cred_ref` |

Both are JWTs whose SHA-256 hashes are stored in the database. Revoked keys are rejected.

---

### /auth (Authentication Module)

| Method | Endpoint | Request Body | Response | Auth Required |
|--------|----------|--------------|----------|---------------|
| POST | `/auth/login` | `{ "email": "admin@example.com", "password": "..." }` | `{ "admin_key": "<JWT>", "expires": null }` | No |
| POST | `/auth/change-password` | `{ "current_password": "...", "new_password": "..." }` | `{ "message": "Password changed successfully" }` | X-Admin-Key |
| POST | `/auth/rotate-key` | - | `{ "message": "...", "admin_key": "<new JWT>" }` | X-Admin-Key |

Notes:
- Admin keys have no expiration by default
- Rotating a key revokes all prior keys for that admin
- Password must meet minimum complexity requirements

---

### /hosts (Host Management Module)

| Method | Endpoint | Request Body | Response | Auth Required |
|--------|----------|--------------|----------|---------------|
| GET | `/hosts/` | - | `[HostInfo]` | X-Admin-Key |
| POST | `/hosts/` | `HostCreate` | `{ "host_id": "<uuid>", "server_key": "<JWT>" }` | X-Admin-Key |
| GET | `/hosts/{id}/status` | - | `HostStatusResponse` | X-Admin-Key |
| PATCH | `/hosts/{id}` | `HostUpdate` (partial) | `HostInfo` | X-Admin-Key |
| DELETE | `/hosts/{id}` | - | 204 No Content | X-Admin-Key |
| POST | `/hosts/{id}/heartbeat` | `{ "cpu": 15, "mem": 45, "containers": 3 }` | `{ "ack": true }` | X-Server-Key |

**HostCreate Schema:**
```json
{
  "hostname": "docker-node-1",
  "ip": "10.0.2.17",
  "ssh_port": 22,
  "api_port": 8003,
  "max_containers": 20
}
```

**Health Status Thresholds:**
- **healthy**: CPU < 75% AND MEM < 75%
- **warning**: CPU >= 75% OR MEM >= 75%
- **critical**: CPU >= 90% OR MEM >= 90%
- **offline**: No heartbeat received in last 60 seconds

**Note**: Always use trailing slash for collection endpoints (`/hosts/` not `/hosts`)

---

### /users (VPN Profile Module)

| Method | Endpoint | Request Body | Response | Auth Required |
|--------|----------|--------------|----------|---------------|
| POST | `/users/vpn` | `{ "client_name": "<uuid or email>" }` | `.ovpn` file (binary stream) | X-Admin-Key |
| POST | `/users/vpn/{client_name}/rotate` | - | `.ovpn` file (binary stream) | X-Admin-Key |

Both routes stream the profile with content-type `application/x-openvpn-profile`.

**Notes:**
- `/users/vpn` is idempotent - returns existing profile if already created
- Rotating revokes the old profile and assigns a new static IP
- VPN profiles are stored in `/etc/openvpn/client-configs/`

---

### /containers (Container Orchestration Module)

| Method | Endpoint | Request Body | Response | Auth Required |
|--------|----------|--------------|----------|---------------|
| GET | `/containers/` | - | `[Container]` (DB records only) | X-Admin-Key |
| POST | `/containers/launch?user_id=<uuid>` | multipart/form-data: `file=<challenge.zip>` | `{ "id": "<uuid>", "host_id": "<uuid>" }` | X-Admin-Key |
| GET | `/containers/{id}` | - | `ContainerInfoResponse` (merged from agent + DB + VPN) | X-Admin-Key |
| POST | `/containers/{id}/restart` | - | `{ "detail": "Container restarted" }` | X-Admin-Key |
| DELETE | `/containers/{id}` | - | `{ "detail": "Container removed" }` | X-Admin-Key |

**Container Launch Flow:**

1. Manager selects least-loaded healthy host
2. Generates VPN profile for user
3. Sends docker-compose ZIP + VPN config to host agent
4. Injects iptables rules: `ACCEPT user_vpn_ip <-> container_ip`
5. Returns container ID and assigned host ID

**Agent Interaction:**

Manager calls these agent endpoints with `X-Server-Key`:
```
POST   http://<host_ip>:8003/agent/containers
GET    http://<host_ip>:8003/agent/containers
POST   http://<host_ip>:8003/agent/containers/{name}/restart
DELETE http://<host_ip>:8003/agent/containers/{name}
```

---

### Common Response Types

**Enums:**

| Type | Values |
|------|--------|
| HostStatus | `offline`, `healthy` |
| Healthiness | `offline`, `healthy`, `warning`, `critical` |
| ContainerStatus | `pending`, `running`, `stopped`, `error` |
| UserRole | `admin`, `user` |
| UserState | `active`, `suspended`, `deleted` |

**Timestamps**: ISO-8601 format in UTC (e.g. `2026-01-30T12:34:56Z`)

---

## 6. Host Agent API Reference

### Authentication

All requests require `X-Server-Key` header containing the JWT issued during host registration.

---

### /agent (Agent Core Module)

| Method | Endpoint | Request Body | Response | Summary |
|--------|----------|--------------|----------|---------|
| GET | `/agent/health` | - | `{ "uptime_seconds": 3600, "running_containers": 5, "mem_percent": 45, "cpu_percent": 15 }` | Health check |
| GET | `/agent/containers` | - | `[ContainerInfo]` | List running containers |
| POST | `/agent/containers` | `StartContainerReq` | `{ "name": "user123-challenge", "status": "started" }` | Deploy new container |
| POST | `/agent/containers/{name}/restart` | - | `{ "name": "user123-challenge", "status": "restarted" }` | Restart container |
| DELETE | `/agent/containers/{name}` | - | `{ "name": "user123-challenge", "status": "removed" }` | Remove container |

**StartContainerReq Schema:**
```json
{
  "name": "user123-challenge",
  "docker_zip_base64": "<base64-encoded ZIP containing docker-compose.yml>",
  "vpn_conf_base64": "<base64-encoded .ovpn profile>"
}
```

**ContainerInfo Schema:**
```json
{
  "id": "d5f6c8a1b2c3",
  "name": "user123-challenge",
  "image": "python:3.12-slim",
  "status": "running"
}
```

---

## 7. Deployment Workflow

### Admin Setup

```
STEP 1: Initial Login
POST /auth/login
  Body: { "email": "admin@example.com", "password": "changeme" }
  Response: { "admin_key": "<JWT>" }

STEP 2: Register Container Host
POST /hosts/
  Header: X-Admin-Key: <JWT>
  Body: { "hostname": "docker-01", "ip": "10.0.2.17", "api_port": 8003, "max_containers": 20 }
  Response: { "host_id": "<uuid>", "server_key": "<JWT>" }

STEP 3: Configure Agent
Update container-host-agent/.env:
  MANAGER_URL=http://host.docker.internal:8000
  HOST_ID=<uuid from step 2>
  SERVER_KEY=<JWT from step 2>

docker compose up -d
```

### Automatic Agent Heartbeat

Every 10 seconds (configurable), the agent:
1. Collects CPU usage via psutil
2. Collects memory usage via psutil
3. Counts running Docker containers
4. Sends POST to `/hosts/{host_id}/heartbeat` with X-Server-Key

Manager updates `last_seen`, `cpu_percent`, `mem_percent`, and computes health status.

### Container Deployment

```
STEP 1: User Requests Container
POST /containers/launch?user_id=alice
  Header: X-Admin-Key: <JWT>
  Body: multipart/form-data with challenge.zip

STEP 2: Manager Orchestration
- Selects host with lowest (current_containers / max_containers) ratio
- Generates VPN profile for alice (assigns 10.8.0.50)
- Creates container VPN profile (assigns 10.8.0.51)
- Injects iptables: ACCEPT 10.8.0.50 <-> 10.8.0.51

STEP 3: Agent Execution
POST http://<host_ip>:8003/agent/containers
  Header: X-Server-Key: <JWT>
  Body: { "name": "alice-challenge", "docker_zip_base64": "...", "vpn_conf_base64": "..." }

Agent:
- Creates /opt/containers/alice-challenge/
- Extracts challenge.zip
- Runs: docker compose up -d
- Saves .ovpn file for audit

STEP 4: User Connection
- Download alice.ovpn from /users/vpn
- Connect: openvpn --config alice.ovpn
- Access container via assigned IP
```

---

## 8. Security Model

### Authentication Layers

1. **Admin Authentication**: JWT-based admin keys with SHA-256 hash storage
2. **Host Authentication**: JWT-based server keys issued per-host
3. **VPN Authentication**: TLS certificate-based (Easy-RSA PKI)

### Network Isolation

**iptables Rules (Manager tun0 interface):**
```bash
# Default deny all forwarded traffic
iptables -P FORWARD DROP

# Allow user VPN IP to container IP (bidirectional)
iptables -A FORWARD -s 10.8.0.50 -d 10.8.0.51 -j ACCEPT
iptables -A FORWARD -s 10.8.0.51 -d 10.8.0.50 -j ACCEPT

# Block inter-user traffic
iptables -A FORWARD -s 10.8.0.50 -d 10.8.0.0/24 -j DROP
```

Each container deployment adds exactly 2 ACCEPT rules (forward + return path). Rules are removed when container is deleted.

### Key Management

- Admin keys: Stored as SHA-256 hashes in `api_keys` table
- Server keys: Stored as SHA-256 hashes in `container_hosts.cred_ref`
- VPN certificates: Managed by Easy-RSA, stored in `/etc/openvpn/easy-rsa/pki/`

Revocation:
- Admin key rotation: Deletes all old keys, generates new one
- Host key rotation: Not implemented (re-register host instead)
- VPN profile rotation: Marks old profile as revoked, generates new certificate

---

## 9. Testing & Debugging

### Health Checks

```bash
# Manager health
curl http://localhost:8000/health

# Agent health
curl http://localhost:8003/agent/health \
  -H "X-Server-Key: <JWT>"
```

### Authentication Test

```bash
# Login
ADMIN_KEY=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"changeme"}' \
  | jq -r '.admin_key')

# List hosts
curl http://localhost:8000/hosts/ \
  -H "X-Admin-Key: $ADMIN_KEY"
```

### Manual Container Deployment

```bash
# Prepare challenge
cd /path/to/challenge
zip -r challenge.zip docker-compose.yml Dockerfile src/

# Deploy
curl -X POST "http://localhost:8000/containers/launch?user_id=test_user" \
  -H "X-Admin-Key: $ADMIN_KEY" \
  -F "file=@challenge.zip"
```

### Direct Agent Test

```bash
# Create base64 payloads
zip -r ctx.zip docker-compose.yml
base64 -w0 ctx.zip > ctx.b64
base64 -w0 user123.ovpn > vpn.b64

# Deploy to agent
curl -X POST http://10.0.2.17:8003/agent/containers \
  -H "X-Server-Key: $SERVER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-deployment",
    "docker_zip_base64": "'$(cat ctx.b64)'",
    "vpn_conf_base64": "'$(cat vpn.b64)'"
  }'
```

---

## 10. Configuration Reference

### Manager Environment Variables

```bash
# Database
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_USER=mlab
POSTGRES_PASSWORD=mlabpass
POSTGRES_DB=mlabdb

# Security
JWT_SECRET=supersecretkey

# VPN
VPN_INTERNAL_SUBNET=10.8.0.0/24
OPENVPN_SERVER_PORT=1194
```

### Agent Environment Variables

```bash
# Manager connection
MANAGER_URL=http://host.docker.internal:8000
HOST_ID=<uuid-from-registration>
SERVER_KEY=<jwt-from-registration>

# Heartbeat
HEARTBEAT_INTERVAL=10  # seconds

# Docker
DOCKER_SOCKET=unix:///var/run/docker.sock
```

### OpenVPN Server Configuration

Located at `/etc/openvpn/server.conf`:
```
port 1194
proto udp
dev tun
server 10.8.0.0 255.255.255.0
push "route 10.8.0.0 255.255.255.0"
keepalive 10 120
cipher AES-256-GCM
```

---

## 11. Performance Characteristics

### Scaling Limits

- **Manager**: Single instance, handles 100+ hosts
- **Agent**: One per physical host, 20-50 containers per host
- **VPN**: OpenVPN supports 1000+ concurrent clients
- **Database**: PostgreSQL 16, handles 10K+ container records

### Resource Requirements

**Manager Host:**
- CPU: 4 cores minimum
- RAM: 8 GB minimum
- Disk: 50 GB for database and VPN profiles
- Network: 1 Gbps recommended

**Container Host:**
- CPU: 8+ cores recommended
- RAM: 32+ GB recommended
- Disk: 100+ GB for container images
- Network: 1 Gbps recommended

---

**Document Version**: 2.0  
**Last Updated**: February 2026  
**Platform Status**: Production-Ready
