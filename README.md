# 🏭 Enterprise Digital Twin Platform

> Production-grade microservices platform for industrial equipment management and digital twin applications

## 📊 Project Overview

This project demonstrates enterprise-level software development skills through building a scalable digital twin platform for industrial process management. Built with modern cloud-native technologies and best practices.

**Target Use Case:** Oil refinery equipment monitoring and management  
**Architecture:** Microservices with event-driven patterns  
**Deployment:** Docker containerization with Azure cloud infrastructure

---

## 🎯 Current Status - Week 1 Complete

### ✅ Implemented Features

- **REST API Microservice** (C# ASP.NET Core 8)
  - 7 production-ready endpoints (CRUD + search + statistics)
  - Async/await patterns for non-blocking I/O
  - Comprehensive error handling and logging
  - Swagger/OpenAPI documentation

- **PostgreSQL Database**
  - Entity Framework Core ORM
  - Code-first migrations
  - Optimized indexes for performance
  - Data persistence with Docker volumes

- **Infrastructure as Code**
  - Terraform for Azure resources
  - Docker multi-stage builds
  - Docker Compose orchestration
  - Health checks and auto-recovery

---

## 🏗️ Architecture
```
┌─────────────────────────────────────────────────────┐
│                    CLIENT LAYER                     │
│              (Swagger UI / API Consumers)           │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│                  API LAYER (Port 8080)              │
│         Equipment Microservice (ASP.NET Core)       │
│  ┌──────────────────────────────────────────────┐  │
│  │  Controllers → Services → DbContext          │  │
│  │  ├─ GET    /api/equipment                    │  │
│  │  ├─ POST   /api/equipment                    │  │
│  │  ├─ PUT    /api/equipment/{id}               │  │
│  │  ├─ DELETE /api/equipment/{id}               │  │
│  │  ├─ GET    /api/equipment/stats              │  │
│  │  └─ GET    /api/equipment/search             │  │
│  └──────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│              DATABASE LAYER (Port 5432)             │
│            PostgreSQL 16 + EF Core ORM              │
│  ┌──────────────────────────────────────────────┐  │
│  │  Equipment Table                             │  │
│  │  ├─ Primary Key: Id                          │  │
│  │  ├─ Unique Index: TagNumber                  │  │
│  │  ├─ Index: Type, Status                      │  │
│  │  └─ Persistent Volume: postgres-data         │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- .NET 8 SDK (for local development)
- Azure CLI (for cloud deployment)
- Terraform (for infrastructure)

### Run with Docker Compose (Recommended)
```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/Process-digital-twin.git
cd Process-digital-twin/services/equipment-service

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Access API
curl http://localhost:8080/api/equipment

# Swagger UI
open http://localhost:8080/swagger
```

### Run Locally (Development)
```bash
cd services/equipment-service/EquipmentService

# Start PostgreSQL
docker run -d --name postgres-db \
  -e POSTGRES_DB=equipmentdb \
  -e POSTGRES_USER=equipmentuser \
  -e POSTGRES_PASSWORD=equipment123 \
  -p 5432:5432 \
  postgres:16-alpine

# Run migrations
dotnet ef database update

# Start API
dotnet run

# Test API
curl http://localhost:5040/api/equipment
```

---

## 📚 API Endpoints

### Equipment Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/equipment` | Get all equipment |
| GET | `/api/equipment/{id}` | Get specific equipment |
| POST | `/api/equipment` | Create new equipment |
| PUT | `/api/equipment/{id}` | Update equipment |
| DELETE | `/api/equipment/{id}` | Delete equipment |
| GET | `/api/equipment/stats` | Get statistics |
| GET | `/api/equipment/search?query=...` | Search equipment |

### Example Request
```bash
# Create new equipment
curl -X POST http://localhost:8080/api/equipment \
  -H "Content-Type: application/json" \
  -d '{
    "tagNumber": "P-101",
    "name": "Crude Feed Pump",
    "type": "Centrifugal Pump",
    "status": "Operating",
    "capacity": 500,
    "unit": "m³/h"
  }'
```

---

## 🛠️ Technology Stack

### Backend
- **C# / .NET 8** - Modern, high-performance framework
- **ASP.NET Core** - Web API framework
- **Entity Framework Core 8** - ORM for database access
- **Npgsql** - PostgreSQL provider

### Database
- **PostgreSQL 16** - Production-grade relational database
- **EF Core Migrations** - Schema versioning

### DevOps
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **Terraform** - Infrastructure as Code
- **Azure** - Cloud platform (Resource Group, ACR, Storage)

### Tools
- **Swagger/OpenAPI** - API documentation
- **GitHub** - Version control
- **VS Code / GitHub Codespaces** - Development environment

---

## 📂 Project Structure
```
Process-digital-twin/
├── infrastructure/
│   └── terraform/
│       ├── main.tf              # Azure resources
│       ├── variables.tf         # Input variables
│       ├── outputs.tf           # Output values
│       └── provider.tf          # Provider configuration
│
├── services/
│   └── equipment-service/
│       ├── EquipmentService/
│       │   ├── Controllers/
│       │   │   └── EquipmentController.cs
│       │   ├── Data/
│       │   │   ├── EquipmentDbContext.cs
│       │   │   └── DesignTimeDbContextFactory.cs
│       │   ├── Models/
│       │   │   └── Equipment.cs
│       │   ├── Migrations/
│       │   │   └── *_InitialCreate.cs
│       │   ├── Program.cs
│       │   ├── Dockerfile
│       │   └── appsettings.json
│       └── docker-compose.yml
│
├── docs/
│   └── (documentation)
│
└── README.md
```

---

## 🎓 Key Learning Outcomes

### Software Engineering
- ✅ RESTful API design principles
- ✅ Async/await patterns for scalability
- ✅ Dependency injection
- ✅ Repository pattern with EF Core
- ✅ Database migrations and versioning

### DevOps & Cloud
- ✅ Infrastructure as Code (Terraform)
- ✅ Container orchestration (Docker Compose)
- ✅ Health checks and auto-recovery
- ✅ Data persistence strategies
- ✅ Azure cloud deployment

### Database
- ✅ PostgreSQL optimization (indexes)
- ✅ ORM patterns (EF Core)
- ✅ Database schema design
- ✅ UTC timestamp handling

---

## 📈 Roadmap

### Week 2: Event-Driven Architecture
- [ ] Add RabbitMQ message broker
- [ ] Implement event publishing
- [ ] Create event consumers
- [ ] Add CQRS pattern

### Week 3: Observability
- [ ] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Distributed tracing
- [ ] Centralized logging

### Week 4: Data Lakehouse
- [ ] Databricks integration
- [ ] Real-time streaming
- [ ] Analytics queries
- [ ] ML model integration

---

## 👤 Author

**Balaji**  
Chemical Engineer transitioning to Software Engineering  
Targeting: Senior/Principal roles at AVEVA, Bentley Systems, Siemens

### Skills Demonstrated
- Enterprise software architecture
- Cloud-native development
- Microservices patterns
- Industrial domain expertise
- Production-ready code

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

Built as part of a 12-week enterprise digital twin platform project demonstrating production-grade software development skills for industrial applications.
