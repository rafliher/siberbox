# SiberBox Platform

A distributed container orchestration platform for cybersecurity training environments, designed for educational institutions and security professionals.

---

## 📋 Table of Contents

- [**Page 1: Overview & Architecture**](#page-1-overview--architecture)
- [**Page 2: Quick Start Guide**](#page-2-quick-start-guide)
- [**Page 3: Components & Documentation**](#page-3-components--documentation)

---

## Page 1: Overview & Architecture

### 🎯 Project Overview

SiberBox is a comprehensive platform that enables educators and security professionals to deploy isolated, containerized cybersecurity training environments across multiple host machines. The platform provides automated container orchestration, VPN-based network isolation, and centralized management capabilities.

### 🏗️ System Architecture

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Web Interface     │    │  Machine Lab        │    │  Container Host     │
│                     │◄──►│    Manager          │◄──►│     Agents          │
│                     │    │                     │    │                     │
│  - Dashboard        │    │  - API Server       │    │  - Docker Engine    │
│  - Container Mgmt   │    │  - VPN Server       │    │  - Container Mgmt   │
│  - Host Monitoring  │    │  - Database         │    │  - Resource Monitor │
└─────────────────────┘    │  - Authentication   │    └─────────────────────┘
                           └─────────────────────┘
                                     │
                              ┌─────────────┐
                              │ PostgreSQL  │
                              │ Database    │
                              └─────────────┘
```

### 🔧 Core Features

- **Multi-Host Container Orchestration**: Deploy containers across multiple host machines
- **VPN Network Isolation**: Automatic VPN profile generation for secure network isolation
- **RESTful API**: Comprehensive API for integration with external systems
- **Load Balancing**: Intelligent container distribution based on host capacity
- **Real-time Monitoring**: Host health monitoring and container status tracking
- **Security First**: JWT authentication, API key management, and network isolation

### 🎓 Use Cases

- Cybersecurity training laboratories
- Capture The Flag (CTF) environments
- Penetration testing sandboxes
- Security research environments
- Educational institution lab management

---

## Page 2: Quick Start Guide

### 📋 Prerequisites

- **Docker & Docker Compose**: Latest stable version
- **Python 3.8+**: For running components in bare metal
- **PostgreSQL**: Database server (or use Docker)
- **OpenVPN**: For VPN functionality
- **Node.js 16+**: For UI component (optional)

### ⚡ Quick Deployment

#### 1. Clone Repository
```bash
git clone https://github.com/rafliher/machine-lab-platform.git
cd machine-lab-platform
```

#### 2. Start Manager (Main Server)
```bash
cd machine-lab-manager
# Configure .env file (see component README)
docker compose up -d
```

#### 3. Deploy Host Agents
```bash
cd container-host-agent
# Register host in manager first, get server key and host ID
# Configure .env file with obtained credentials
docker compose up -d
```

#### 4. Optional: Start Web Interface
```bash
cd machine-lab-platform-ui
# Configure .env file
npm install
npm run serve
```

### 🔧 Development Mode

For development, the Manager exposes API documentation at `/api-docs` endpoint.

### 🌐 Integration

The Machine Lab Manager API is designed to be integrated with larger educational or training platforms. The web UI is optional and primarily for testing or direct interaction.

---

## Page 3: Components & Documentation

### 📁 Component Structure

```
machine-lab-platform/
├── machine-lab-manager/      # Central management server
├── container-host-agent/     # Distributed container agents  
├── machine-lab-platform-ui/  # Web interface 
├── docs/                     # Documentation and diagrams
└── example/                  # Example challenges and setups
```

### 🔗 Component Details

#### 🖥️ Machine Lab Manager
**Location**: `machine-lab-manager/`

The central API server that manages the entire platform, including VPN server functionality.

- **Purpose**: Container orchestration, host management, VPN provisioning
- **Technology**: FastAPI (Python), PostgreSQL, OpenVPN
- **Deployment**: Docker Compose or bare metal
- **API Documentation**: Available at `/api-docs` in development mode

📖 **[Detailed README →](machine-lab-manager/README.md)**

---

#### 🤖 Container Host Agent  
**Location**: `container-host-agent/`

Distributed agents that run on host machines to manage Docker containers.

- **Purpose**: Container lifecycle management, resource monitoring
- **Technology**: FastAPI (Python), Docker API
- **Setup**: Register host in manager, configure credentials, deploy
- **Requirements**: Server key and host ID from manager

📖 **[Detailed README →](container-host-agent/README.md)**

---

#### 🌐 Machine Lab Platform UI
**Location**: `machine-lab-platform-ui/`

Optional web interface for platform management and testing.

- **Purpose**: Direct interaction, testing, demonstration
- **Technology**: Vue.js, Vuetify
- **Note**: Manager API designed for integration with larger systems
- **Deployment**: Development server or production build

📖 **[Detailed README →](machine-lab-platform-ui/README.md)**

---

### 📚 Additional Resources

- **Architecture Documentation**: `docs/machine_lab_environment_scheme.md`
- **Example Challenges**: `example/` directory
- **API Integration**: Comprehensive OpenAPI documentation available

### 🤝 Support & Contribution

For detailed setup instructions, configuration options, and troubleshooting guides, please refer to the individual component README files linked above. Each component directory contains comprehensive documentation for both Docker and bare metal deployments.
