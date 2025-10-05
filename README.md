# Avalon Tunnel

**An intelligent, self-hosted proxy management system optimized for IPv6-only environments, featuring a dynamic deception layer for advanced camouflage.**

---

## 🎯 Core Features

-   **🛡️ Dynamic Deception Layer**: Goes beyond simple static pages. The decoy website is a living, interactive application designed to generate plausible, dynamic traffic patterns (e.g., a mini-game, a blog with simulated user activity) to provide ultimate camouflage against passive traffic analysis.
-   **🔐 Robust Security**: Each user is assigned a unique UUID and a unique high-entropy secret path. Credentials are not shared, and traffic is end-to-end encrypted with TLS 1.3.
-   **🚀 Fully Automated Deployment**: A single `make deploy` command handles firewall configuration, service setup, automatic TLS certificate acquisition (via Caddy), and post-deployment validation.
-   **⚙️ RESTful API**: A FastAPI-based control plane for dynamic user management, device tracking, and configuration updates without service interruption.
-   **🌐 IPv6-First Design**: Optimized for IPv6-only servers, incorporating DNS64/NAT64 awareness and IPv6-centric configurations.

---

## 🏗️ Architecture Overview

Avalon Tunnel employs a multi-layered, service-oriented architecture designed for security and scalability.

```mermaid
graph TD
    subgraph Client Side
        Client[<fa:fa-user> User's Client]
    end

    subgraph Server Side your-domain.com
        subgraph Gateway Layer
            Firewall( <fa:fa-shield-alt> Firewall <br> UFW + Cloud VPC)
            Caddy( <fa:fa-sitemap> Caddy <br> Reverse Proxy & TLS)
        end

        subgraph Application Layer
            Decoy[ <fa:fa-theater-masks> Dynamic Decoy Site <br> FastAPI / Python ]
            API[ <fa:fa-cogs> Management API <br> FastAPI / Python ]
            V2Ray( <fa:fa-rocket> V2Ray Core <br> VLESS + WebSocket)
            Database[( <fa:fa-database> SQLite DB <br> Users & Devices )]
        end
    end

    Client -- HTTPS / WSS on Port 443 --> Firewall
    Firewall -- Allow 80, 443 --> Caddy

    Caddy -- Root Path (/) --> Decoy
    Caddy -- API Path (/api/v1) --> API
    Caddy -- User's Secret Path (e.g., /media/...) --> V2Ray

    API <-- CRUD Operations --> Database
    V2Ray -- Authenticates via --> Database
    Decoy -- Generates Content from --> Database
````

**How it Works**:

1.  All traffic enters through a hardened firewall on port 443, handled by the Caddy reverse proxy.
2.  Caddy serves the **Dynamic Decoy Site** on the root path (`/`), making the server appear as a legitimate, interactive web application.
3.  Only clients with knowledge of their unique secret path can access the V2Ray service. Caddy forwards this specific traffic to the V2Ray Core.
4.  A FastAPI application serves as the **Control Plane**, providing a RESTful API for management and serving the dynamic content for the decoy site, with all state stored in a SQLite database.

-----

## 🚀 Quick Start

### Prerequisites

  - **Server**: Ubuntu 20.04+ with a public IPv6 address.
  - **Domain**: An FQDN pointed to your server's IP address.
  - **Firewall**: Ports 80 and 443 must be open in your cloud provider's firewall (e.g., OCI Security List).

### One-Command Deployment

```bash
# 1. Clone the repository
git clone [https://github.com/your-repo/Avalon-Tunnel.git](https://github.com/your-repo/Avalon-Tunnel.git)
cd Avalon-Tunnel

# 2. Configure your domain
echo "DOMAIN=your-domain.com" > .env

# 3. Deploy everything (firewall, configs, services, validation)
make deploy
```

**That's it\!** 🎉 After a few moments, the system will be live.

-----

## 📱 Client Configuration

The deployment script will output the connection info for the default user. You can also retrieve it later via the API.

**Example VLESS URI:**

```
vless://a1b2c3d4-...@your-domain.com:443?type=ws&security=tls&path=%2Fyour-secret-path...#MyConnection
```

**Important**: For IPv6-only servers, ensure your client has an option like **"Prefer IPv6"** enabled.

-----

## 🔧 Management CLI (Makefile)

### Core Services

```bash
make start        # Start core services (V2Ray + Caddy)
make stop         # Stop all services
make restart      # Restart core services
make status       # Check service status
```

### API & Management

```bash
make api-start    # Start the API server
make api-stop     # Stop the API server
make api-logs     # View API logs
make add-user EMAIL="new@user.com" # Add a new user
```

### Diagnostics & Maintenance

```bash
make config       # Regenerate config files from templates
make test-pre     # Run pre-flight environment checks
make test-post    # Run post-deployment service validation
make clean        # Clean up all containers and networks
make clean-data   # ⚠️  DANGEROUS: Wipes the user database and certificates
```

-----

## 🔐 Security Model

### Defense Layers

1.  **Unique Credentials**: Each user has a dedicated `inbound` in V2Ray, with a unique UUID and a unique, high-entropy secret path.
2.  **Dynamic Deception**: The proxy's traffic signature is masked by a legitimate, dynamic web application that generates plausible user traffic patterns.
3.  **Device Fingerprinting**: The system logs `User-Agent` and source IP for every connection, paving the way for device-limit enforcement.
4.  **End-to-End Encryption**: All traffic is encrypted using TLS 1.3, managed automatically by Caddy.

### Anti-Abuse Mechanisms

  - **No Credential Sharing**: Because the UUID and secret path are uniquely tied, simply sharing a VLESS URI is insufficient to grant access if the backend logic requires strict matching (as it does here).
  - **Optional Credential Rotation**: The API-driven architecture allows for optional, low-frequency (e.g., monthly) automated rotation of secret paths as a security hygiene measure.
  - *(Planned)* **Device Count Limits**: The system will support a configurable limit on the number of unique devices that can be associated with a single user account.

-----

## 🗺️ Development Roadmap

### ✅ Phase 1 & 2 (Complete)

  - [x] Core proxy functionality (V2Ray + Caddy).
  - [x] Dynamic Deception Layer (FastAPI-driven decoy site).
  - [x] Database-driven configuration (SQLite).
  - [x] RESTful API for user management.
  - [x] Fully automated deployment and management via `Makefile`.
  - [x] Device access logging (fingerprinting).

### 🔜 Phase 3 (Planned)

  - [ ] **Enforce Device Limits**: Implement logic to block connections from exceeding the configured device limit per user.
  - [ ] **Traffic & Performance Monitoring**: Integrate a monitoring stack (e.g., Prometheus + Grafana) for real-time dashboards.
  - [ ] **Web-based Admin UI**: A simple web interface for managing users and viewing stats.
  - [ ] **CI/CD Integration**: Automated testing and deployment pipelines.

-----

## 🛠️ Tech Stack

| Component         | Technology            | Purpose                               |
| ----------------- | --------------------- | ------------------------------------- |
| **Proxy Core** | V2Ray (VLESS)         | Core proxy engine                     |
| **Reverse Proxy** | Caddy 2               | Automatic TLS, routing, gateway       |
| **Control Plane** | FastAPI + Uvicorn     | RESTful API & Dynamic Decoy Site      |
| **Database** | SQLite                | User, device, and config storage      |
| **Container** | Docker + Compose      | Service orchestration                 |
| **Automation** | Makefile + Shell      | Deployment & management               |

```
```