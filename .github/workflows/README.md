# CI/CD Pipeline Documentation

## Overview
This directory contains GitHub Actions workflows for automated building, testing, and deployment of microservices.

## Workflows

### Equipment Service CI/CD
**File**: `equipment-service-cicd.yml`

**Triggers**:
- Push to `main` branch with changes in `services/equipment-service/`
- Pull requests to `main`

**Steps**:
1. **Build**: Compiles .NET application
2. **Test**: Runs unit tests (if available)
3. **Docker**: Builds container image with version tag
4. **Artifact**: Saves image for deployment

**Version Tagging**: `vYYYYMMDD.HHMMSS` (e.g., v20241123.143045)

## Local Deployment (KIND)

After workflow completes:
```bash
# Load image to KIND cluster
kind load docker-image equipment-service:latest --name digital-twin

# Deploy to Kubernetes
kubectl apply -f services/equipment-service/k8s/equipment-deployment-prod.yaml

# Verify deployment
kubectl rollout status deployment equipment-api -n digital-twin
kubectl get pods -n digital-twin
```

## Production Deployment (Future)

For Azure AKS deployment, the workflow would:
1. Push image to Azure Container Registry
2. Update Kubernetes manifest with new image tag
3. Apply rolling update to AKS cluster
4. Verify health checks pass
5. Auto-rollback on failure

## Features

✅ Automated builds on code changes
✅ Version tagging with timestamps
✅ Docker multi-stage builds
✅ Build artifacts for deployment
✅ GitHub Actions summaries
✅ Zero-downtime deployments (when deployed to K8s)
