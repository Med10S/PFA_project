# IDS Distributed System - GNS3 Deployment Guide

## Overview

This guide provides instructions for deploying the IDS distributed system as individual Docker containers in a GNS3 topology. Each service runs as a standalone container with environment variable configuration.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐     ┌─────────────────┐
│   Packet        │    │   Feature       │     │   ML-API        │
│   Capture       │───▶│   Extractor     │───▶│   Service       │
│   Service       │    │   Service       │     │   Service       │
└─────────────────┘    └─────────────────┘     └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Redis Message Queue                      │
└─────────────────────────────────────────────────────────────────┘
                      │                       │            
                      ▼                       ▼            
             ┌─────────────────┐    ┌─────────────────┐   
             │   Alert         │    │   Monitoring    │    
             │   Manager       │    │   Service       │    
             │   Service       │    │   Service       │    
             └─────────────────┘    └─────────────────┘    
```

## Deployment Order

**IMPORTANT:** Deploy services in this exact order to ensure proper dependencies:

1. **Redis** (Infrastructure)
2. **Monitoring Service** (Health monitoring)
3. **ML-API Service** (Machine Learning endpoint)
4. **Alert Manager Service** (Alert handling)
5. **Feature Extractor Service** (Packet processing)
6. **Packet Capture Service** (Network capture)

## Network Configuration

### GNS3 Network Settings
- **Network Name:** `ids-network`
- **Subnet:** `172.20.0.0/16`
- **Gateway:** `172.20.0.1`

### Container IP Assignments
| Service | Container Name | IP Address | Port(s) |
|---------|---------------|------------|---------|
| Redis | ids-redis | 172.20.0.10 | 6379 |
| Monitoring | ids-monitoring | 172.20.0.20 | 9000 |
| ML-API | ids-ml-api | 172.20.0.30 | 5000 |
| Alert Manager | ids-alert-manager | 172.20.0.40 | 9003 |
| Feature Extractor | ids-feature-extractor | 172.20.0.60 | - |
| Packet Capture | ids-packet-capture | 172.20.0.70 | - |

## Prerequisites

### Docker Environment
- Docker Engine 20.10+
- Available RAM: 8GB minimum
- Available Storage: 10GB minimum

### Network Interface
- Access to network interface for packet capture
- Promiscuous mode capability
- NET_ADMIN and NET_RAW capabilities

### File Structure
Ensure the following directory structure exists:
```
/app/
├── shared/          # Shared data between services
├── logs/           # Application logs
├── models/         # ML models
├── functions/      # Shared functions
└── buffer/         # Packet buffer
```

## Environment Files

Each service requires a `.env` file with specific configuration. Create these files before deployment:

- `redis/.env`
- `monitoring/.env`
- `ml-api/.env`
- `alerts/.env`
- `extractor/.env`
- `capture/.env`

Refer to individual service deployment guides for specific environment variables.

## Security Considerations

### Redis Authentication
- **REQUIRED:** Set `REDIS_PASSWORD` environment variable
- Use strong password (minimum 16 characters)
- Example: `REDIS_PASSWORD=SecureRedisPassword123!`

### Network Security
- Use internal IPs for service communication
- Expose only necessary ports to external networks
- Enable Docker security features

### Data Protection
- Encrypt sensitive environment variables
- Use Docker secrets for production deployment
- Regular backup of configuration files

## Monitoring and Health Checks

### Service Health Endpoints
- **Monitoring:** `http://172.20.0.20:9000/health`
- **ML-API:** `http://172.20.0.30:5000/health`
- **Alert Manager:** `http://172.20.0.40:9003/health`

### Redis Health Check
```bash
docker exec ids-redis redis-cli ping
```

## Deployment Commands Summary

```bash
# 1. Redis
docker run -d --name ids-redis --ip 172.20.0.10 --network ids-network ...

# 2. Monitoring
docker run -d --name ids-monitoring --ip 172.20.0.20 --network ids-network ...

# 3. ML-API
docker run -d --name ids-ml-api --ip 172.20.0.30 --network ids-network ...

# 4. Alert Manager
docker run -d --name ids-alert-manager --ip 172.20.0.40 --network ids-network ...

# 6. Feature Extractor
docker run -d --name ids-feature-extractor --ip 172.20.0.60 --network ids-network ...

# 7. Packet Capture
docker run -d --name ids-packet-capture --ip 172.20.0.70 --network ids-network ...
```

## Troubleshooting

### Common Issues
1. **Service won't start:** Check environment variables and dependencies
2. **Network connectivity:** Verify IP assignments and network configuration
3. **Redis connection:** Ensure Redis is running and password is correct
4. **Permission errors:** Check Docker privileges and file permissions

### Logs Location
- Container logs: `docker logs <container-name>`
- Application logs: `/app/logs/` (mounted volumes)

### Container Management
```bash
# Check container status
docker ps -a

# View container logs
docker logs ids-<service-name>

# Access container shell
docker exec -it ids-<service-name> /bin/bash

# Restart container
docker restart ids-<service-name>
```

## Individual Service Guides

Refer to the following individual deployment guides for detailed instructions:

1. [Redis Deployment](./docker/deployments/01_REDIS_DEPLOYMENT.md)
2. [Monitoring Service Deployment](./docker/deployments/02_MONITORING_DEPLOYMENT.md)
3. [ML-API Service Deployment](./docker/deployments/03_ML_API_DEPLOYMENT.md)
4. [Alert Manager Deployment](./docker/deployments/04_ALERT_MANAGER_DEPLOYMENT.md)
5. [Feature Extractor Deployment](./docker/deployments/06_FEATURE_EXTRACTOR_DEPLOYMENT.md)
6. [Packet Capture Deployment](./docker/deployments/07_PACKET_CAPTURE_DEPLOYMENT.md)

## Support

For additional support or troubleshooting, refer to:
- Individual service README files
- Docker documentation
- GNS3 documentation
- Service-specific logs and health checks
