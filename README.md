# Refinery Digital Twin Platform

Enterprise-grade digital twin platform for industrial process plants.

## 🏗️ Architecture

- **Infrastructure:** Terraform + Azure AKS
- **Backend Services:** C# ASP.NET Core, Node.js
- **Data Platform:** Databricks, Snowflake, Kafka
- **Frontend:** React + TypeScript
- **ML/AI:** MLflow, Feature Store

## 📁 Project Structure
```
.
├── infrastructure/terraform/   # Infrastructure as Code
├── services/
│   ├── equipment-service/     # Equipment management API (C#)
│   └── sensor-service/        # Sensor data API (Node.js)
├── docs/                      # Documentation
└── .github/workflows/         # CI/CD pipelines
```

## 🚀 Getting Started

### Prerequisites
- Azure subscription
- Terraform 1.6+
- .NET 8 SDK
- Docker

### Quick Start

1. **Deploy Infrastructure**
```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

2. **Run Equipment Service**
```bash
cd services/equipment-service/EquipmentService
dotnet run
```

## 🔧 Technology Stack

**Cloud & Infrastructure:**
- Azure (AKS, ACR, Storage, Data Lake)
- Terraform (IaC)
- Kubernetes + Istio

**Backend:**
- C# ASP.NET Core 8
- Node.js (NestJS)
- Python (FastAPI)

**Data:**
- Databricks (ETL)
- Snowflake (Data Warehouse)
- Kafka (Streaming)
- PostgreSQL, TimescaleDB

**DevOps:**
- Docker + Kubernetes
- GitHub Actions (CI/CD)
- Prometheus + Grafana

## 📊 Current Status

- [x] Infrastructure as Code (Terraform)
- [x] Equipment Service (C# API)
- [ ] Kubernetes Cluster (AKS)
- [ ] CI/CD Pipeline
- [ ] Data Lake Setup
- [ ] ML Platform

## 📝 License

MIT License - See LICENSE file for details

## 👤 Author

Built as an enterprise portfolio project demonstrating production-grade digital twin architecture.
