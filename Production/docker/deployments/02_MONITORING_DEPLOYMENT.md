# Monitoring Service Deployment Guide - GNS3 Topology

## Service Overview
The Monitoring Service provides real-time system health monitoring, metrics collection, and dashboard visualization for the IDS distributed system. It monitors all services, Redis performance, and system resources.

## Prerequisites
- Redis container deployed and running (172.20.0.10)
- Docker Engine installed and running
- GNS3 network `ids-network` created

## Configuration Files

### 1. Create Monitoring Service Directory
```powershell
mkdir "c:\ids-deployment\monitoring"
mkdir "c:\ids-deployment\monitoring\logs"
mkdir "c:\ids-deployment\monitoring\static"
mkdir "c:\ids-deployment\monitoring\templates"
```

### 2. Environment File (`.env`)
Create `c:\ids-deployment\monitoring\.env`:

```env
# Redis Configuration
REDIS_HOST=172.20.0.10
REDIS_PORT=6379
REDIS_PASSWORD=SecureRedisPassword123!
REDIS_DB=0

# Flask Application Configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=9000
FLASK_DEBUG=false
FLASK_SECRET_KEY=MonitoringSecretKey123!

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/app/logs/monitoring.log
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=5

# Monitoring Configuration
MONITORING_INTERVAL=30
HEALTH_CHECK_INTERVAL=60
METRICS_RETENTION_HOURS=24
ALERT_THRESHOLD_CPU=80.0
ALERT_THRESHOLD_MEMORY=85.0
ALERT_THRESHOLD_DISK=90.0

# Service Monitoring Configuration
MONITOR_SERVICES=redis,ml-api,alert-manager,backup,feature-extractor,packet-capture
SERVICE_TIMEOUT=10
SERVICE_RETRY_COUNT=3
SERVICE_RETRY_DELAY=5

# Dashboard Configuration
DASHBOARD_REFRESH_RATE=5000
CHART_DATA_POINTS=50
DASHBOARD_THEME=dark
SHOW_DETAILED_METRICS=true

# Alert Configuration
ALERT_COOLDOWN_MINUTES=15
ALERT_MAX_PER_HOUR=10
ENABLE_EMAIL_ALERTS=false
ENABLE_SLACK_ALERTS=false

# Performance Settings
MAX_CONCURRENT_CHECKS=10
CACHE_TTL_SECONDS=30
ENABLE_METRICS_CACHE=true
```

## Docker Build

### 1. Create Dockerfile
Create the following Dockerfile at: `c:\ids-deployment\monitoring\Dockerfile`

```dockerfile
# Dockerfile pour le service de monitoring
FROM python:3.11-slim

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Création du répertoire de travail
WORKDIR /app

# Copie des requirements spécifiques au service
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie du service de monitoring
COPY monitoring_service.py .

# Création des dossiers nécessaires
RUN mkdir -p /app/logs

# Configuration des permissions
RUN chmod +x monitoring_service.py

# Port d'exposition
EXPOSE 9000

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=monitoring_service.py

# Configuration des logs
ENV LOG_LEVEL=INFO \
    LOG_FILE=monitoring.log \
    LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Configuration Redis
ENV REDIS_HOST=redis \
    REDIS_PORT=6379 \
    REDIS_DB=0 \
    REDIS_PASSWORD=""

# Configuration Flask
ENV FLASK_HOST=0.0.0.0 \
    FLASK_PORT=9000 \
    FLASK_DEBUG=false

# Configuration du monitoring
ENV MONITORING_INTERVAL=30 \
    HISTORY_LIMIT=1000 \
    DASHBOARD_REFRESH=30

# Configuration des seuils d'alerte
ENV CPU_ALERT_THRESHOLD=90 \
    MEMORY_ALERT_THRESHOLD=90 \
    DISK_ALERT_THRESHOLD=90

# Configuration des services
ENV SERVICE_CHECK_INTERVAL=30 \
    SERVICE_TIMEOUT=5

# Configuration des services individuels
ENV PACKET_CAPTURE_HOST=packet-capture \
    PACKET_CAPTURE_PORT=9001 \
    PACKET_CAPTURE_PROTOCOL=http \
    PACKET_CAPTURE_ENABLED=true \
    FEATURE_EXTRACTOR_HOST=feature-extractor \
    FEATURE_EXTRACTOR_PORT=9002 \
    FEATURE_EXTRACTOR_PROTOCOL=http \
    FEATURE_EXTRACTOR_ENABLED=true \
    ML_API_HOST=ml-api \
    ML_API_PORT=5000 \
    ML_API_PROTOCOL=http \
    ML_API_ENABLED=true \
    ALERT_MANAGER_HOST=alert-manager \
    ALERT_MANAGER_PORT=9003 \
    ALERT_MANAGER_PROTOCOL=http \
    ALERT_MANAGER_ENABLED=true \
    BACKUP_SERVICE_HOST=backup-service \
    BACKUP_SERVICE_PORT=9004 \
    BACKUP_SERVICE_PROTOCOL=http \
    BACKUP_SERVICE_ENABLED=true

# Commande de démarrage
CMD ["python", "monitoring_service.py"]
```

## Service Endpoints

### Web Dashboard
- **URL:** http://172.20.0.20:9000/
- **Description:** Real-time monitoring dashboard
- **Features:** Service status, metrics, alerts, system health

### API Endpoints
- **Health Check:** `GET /health`
- **Metrics:** `GET /api/metrics`
- **Service Status:** `GET /api/services/status`
- **Alerts:** `GET /api/alerts`
- **System Info:** `GET /api/system`

### Dashboard Features
- Real-time service status monitoring
- Redis performance metrics
- System resource utilization
- Alert history and management
- Service dependency visualization

## Monitoring and Maintenance

### 1. Monitor Service Logs
```powershell
# Real-time log monitoring
docker logs -f ids-monitoring

# Check specific log entries
docker exec ids-monitoring tail -n 100 /app/logs/monitoring.log
```

### 2. Monitor Resource Usage
```powershell
docker stats ids-monitoring
```

### 3. Service Performance Metrics
Access the dashboard at: http://172.20.0.20:9000/

### 4. Manual Health Checks
```powershell
# Test all monitored services
curl http://172.20.0.20:9000/api/services/status

# Get current metrics
curl http://172.20.0.20:9000/api/metrics
```

## Integration with Other Services

### Service Registration
The monitoring service automatically discovers and monitors services based on:
- Redis connectivity
- Configured service endpoints
- Docker container status

### Monitored Services Configuration
Edit the `MONITOR_SERVICES` environment variable to include:
```env
MONITOR_SERVICES=redis,ml-api,alert-manager,backup,feature-extractor,packet-capture
```

### Service Health Check URLs
- **Redis:** Internal Redis ping
- **ML-API:** http://172.20.0.30:5000/health
- **Alert Manager:** http://172.20.0.40:9003/health
- **Backup:** http://172.20.0.50:9004/health
- **Feature Extractor:** Redis queue status
- **Packet Capture:** Redis queue status

## Troubleshooting

### Common Issues

#### 1. Container Won't Start
```powershell
# Check Docker logs
docker logs ids-monitoring

# Common causes:
# - Port 9000 already in use
# - Invalid environment variables
# - Missing Redis connection
# - Dockerfile build issues
```

#### 2. Dashboard Not Accessible
```powershell
# Check if service is listening
docker exec ids-monitoring netstat -tlnp | grep 9000

# Check Flask application logs
docker exec ids-monitoring cat /app/logs/monitoring.log | grep ERROR
```

#### 3. Redis Connection Issues
```powershell
# Test Redis connectivity
docker exec ids-monitoring python -c "
import redis
r = redis.Redis(host='172.20.0.10', port=6379, password='SecureRedisPassword123!')
print(r.ping())
"

# Check Redis container status
docker ps -f name=ids-redis
```

#### 4. High Resource Usage
```powershell
# Check container resources
docker stats ids-monitoring --no-stream

# Adjust monitoring intervals in .env file:
# MONITORING_INTERVAL=60  # Increase interval
# HEALTH_CHECK_INTERVAL=120
```

## Security Considerations

### 1. Network Security
- Service bound to internal IP (172.20.0.20)
- Dashboard access limited to port 9000
- No external database connections required

### 2. Authentication
- Dashboard currently uses basic authentication
- Consider implementing proper user authentication for production
- Redis password protected

### 3. Data Protection
- Sensitive data (passwords) logged securely
- Monitoring data retention limited by configuration
- Log rotation enabled

## Next Steps
After Monitoring Service deployment is complete and validated:
1. Verify monitoring dashboard is accessible
2. Confirm Redis monitoring is working
3. Deploy ML-API Service
4. Verify ML-API service appears in monitoring dashboard

## Support
- Flask Documentation: https://flask.palletsprojects.com/
- Redis-py Documentation: https://redis-py.readthedocs.io/
- Docker Monitoring: https://docs.docker.com/config/containers/runmetrics/
