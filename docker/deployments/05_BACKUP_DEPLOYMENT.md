# Backup Service Deployment Guide - GNS3 Topology

## Service Overview
The Backup Service provides automated data backup and archival capabilities for the IDS distributed system. It backs up Redis data, logs, configurations, and ML models on scheduled intervals.

## Prerequisites
- Redis container deployed and running (172.20.0.10)
- Docker Engine installed and running
- GNS3 network `ids-network` created
- Sufficient storage space for backups

## Configuration Files


### 1. Environment File (`.env`)
Create `c:\ids-deployment\backup\.env`:

```env
# Redis Configuration
REDIS_HOST=172.20.0.10
REDIS_PORT=6379
REDIS_PASSWORD=SecureRedisPassword123!
REDIS_DB=0

# Flask Application Configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=9004
FLASK_DEBUG=false
FLASK_SECRET_KEY=BackupServiceSecretKey123!

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/app/logs/backup.log
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=5

# Backup Configuration
BACKUP_INTERVAL_HOURS=6
BACKUP_RETENTION_DAYS=30
BACKUP_BASE_PATH=/app/backups
BACKUP_COMPRESSION=gzip
BACKUP_ENCRYPTION=false
BACKUP_ENCRYPTION_KEY=

# Backup Types
ENABLE_REDIS_BACKUP=true
ENABLE_LOG_BACKUP=true
ENABLE_CONFIG_BACKUP=true
ENABLE_MODEL_BACKUP=true

# Redis Backup Configuration
REDIS_BACKUP_FORMAT=rdb
REDIS_BACKUP_COMPRESSION=true
REDIS_BACKUP_RETENTION_DAYS=30

# Log Backup Configuration
LOG_BACKUP_PATHS=/app/logs,/app/shared/logs
LOG_BACKUP_PATTERNS=*.log,*.txt
LOG_BACKUP_COMPRESSION=true
LOG_BACKUP_RETENTION_DAYS=30

# Configuration Backup
CONFIG_BACKUP_PATHS=/app/config,/app/.env
CONFIG_BACKUP_RETENTION_DAYS=90

# Model Backup Configuration
MODEL_BACKUP_PATHS=/app/models
MODEL_BACKUP_PATTERNS=*.pkl,*.joblib,*.model
MODEL_BACKUP_RETENTION_DAYS=90

# Storage Configuration
MAX_BACKUP_SIZE_GB=50
FREE_SPACE_THRESHOLD_GB=10
BACKUP_VERIFICATION=true
BACKUP_CHECKSUMS=true

# Cleanup Configuration
AUTO_CLEANUP_ENABLED=true
CLEANUP_SCHEDULE=daily
CLEANUP_TIME=02:00

# Notification Configuration
BACKUP_NOTIFICATIONS=true
NOTIFICATION_ON_SUCCESS=false
NOTIFICATION_ON_FAILURE=true
NOTIFICATION_EMAIL=backup-admin@company.com

# Performance Settings
BACKUP_PARALLEL_JOBS=2
BACKUP_TIMEOUT_MINUTES=60
COMPRESSION_LEVEL=6
BUFFER_SIZE_MB=64

# Cloud Storage (Optional)
CLOUD_BACKUP_ENABLED=false
CLOUD_PROVIDER=aws
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_BUCKET_NAME=
AWS_REGION=us-east-1

# Monitoring Integration
ENABLE_METRICS=true
METRICS_PORT=9005
HEALTH_CHECK_ENABLED=true
```

## Docker Build

### 1. Create Dockerfile
Create the following Dockerfile at: `c:\ids-deployment\backup\Dockerfile`

```dockerfile
# Dockerfile pour le service de backup
FROM python:3.11-slim

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    gzip \
    tar \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Création du répertoire de travail
WORKDIR /app

# Copie des requirements spécifiques au service
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie du service de backup
COPY backup_service.py .

# Création des dossiers nécessaires
RUN mkdir -p /app/logs /app/backups /app/config

# Configuration des permissions
RUN chmod +x backup_service.py

# Port d'exposition
EXPOSE 9004

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=backup_service.py

# Configuration Redis
ENV REDIS_HOST=redis \
    REDIS_PORT=6379 \
    REDIS_DB=0 \
    REDIS_PASSWORD=""

# Configuration des sauvegardes
ENV BACKUP_INTERVAL_HOURS=6 \
    BACKUP_RETENTION_DAYS=30 \
    BACKUP_BASE_PATH=/app/backups \
    BACKUP_COMPRESSION=gzip

# Configuration Flask
ENV FLASK_HOST=0.0.0.0 \
    FLASK_PORT=9004 \
    FLASK_DEBUG=false

# Configuration des logs
ENV LOG_LEVEL=INFO \
    LOG_FILE=/app/logs/backup.log

# Volume pour les sauvegardes
VOLUME ["/app/backups", "/app/logs"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9004/health || exit 1

# Commande de démarrage
CMD ["python", "backup_service.py"]
```


## Health Checks and Validation

### 1. Container Health Check
```powershell
# Check if container is running
docker ps -f name=ids-backup

# Check container health
docker exec ids-backup curl -f http://localhost:9004/health || echo "Health check failed"
```

### 2. Service Accessibility Test
```powershell
# Test from host system
curl http://172.20.0.50:9004/health

# Test from another container
docker run --rm --network ids-network curlimages/curl:latest `
  curl -f http://172.20.0.50:9004/health
```


### 3. Backup Storage Test
```powershell
# Check backup directory
docker exec ids-backup ls -la /app/backups

# Check available disk space
docker exec ids-backup df -h /app/backups
```

## Service Endpoints

### Web Dashboard
- **URL:** http://172.20.0.50:9004/
- **Description:** Backup management dashboard
- **Features:** Backup history, manual backup triggers, restore operations

### API Endpoints
- **Health Check:** `GET /health`
- **List Backups:** `GET /api/backups`
- **Create Backup:** `POST /api/backups`
- **Backup Details:** `GET /api/backups/{id}`
- **Restore Backup:** `POST /api/backups/{id}/restore`
- **Delete Backup:** `DELETE /api/backups/{id}`
- **Backup Statistics:** `GET /api/stats`
- **Manual Cleanup:** `POST /api/cleanup`

### Manual Backup Request Format
```json
{
  "backup_type": "full",
  "include_redis": true,
  "include_logs": true,
  "include_config": true,
  "include_models": true,
  "compression": "gzip",
  "description": "Manual backup before maintenance"
}
```

## Integration with Other Services

### Redis Integration
- **Backup Channel:** `backup_requests`
- **Status Channel:** `backup_status`
- **Metrics Channel:** `backup_metrics`

### Monitoring Integration
- Health endpoint monitored by Monitoring Service
- Backup metrics exposed for monitoring dashboard
- Alert integration for backup failures

### Service Data Backup
- **Redis Data:** Full Redis dump with compression
- **Application Logs:** All service logs with rotation
- **Configuration Files:** Service configs and environment files
- **ML Models:** Model files and scalers

## Automated Backup Schedule

### Default Schedule
- **Full Backup:** Every 6 hours
- **Incremental Backup:** Every hour (if supported)
- **Log Backup:** Daily at 02:00
- **Cleanup:** Daily at 03:00

### Backup Types
1. **Full Backup:** Complete system backup including all data
2. **Redis Backup:** Redis data dump only
3. **Log Backup:** Application logs only
4. **Config Backup:** Configuration files only
5. **Model Backup:** ML models and related files only

## Troubleshooting

### Common Issues

#### 1. Container Won't Start
```powershell
# Check Docker logs
docker logs ids-backup

# Common causes:
# - Port 9004 already in use
# - Invalid environment variables
# - Missing Redis connection
# - Insufficient disk space
# - Permission issues with backup directory
```

#### 2. Backup Failures
```powershell
# Check backup logs
docker exec ids-backup cat /app/logs/backup.log | grep ERROR

# Check available disk space
docker exec ids-backup df -h /app/backups

# Test Redis connectivity
docker exec ids-backup python -c "
import redis
r = redis.Redis(host='172.20.0.10', port=6379, password='SecureRedisPassword123!')
print(r.ping())
"
```

#### 3. High Storage Usage
```powershell
# Check backup sizes
docker exec ids-backup ls -lah /app/backups

# Manual cleanup
curl -X POST http://172.20.0.50:9004/api/cleanup

# Check retention settings
docker exec ids-backup printenv | grep RETENTION
```

## Security Considerations

### 1. Network Security
- Service bound to internal IP (172.20.0.50)
- Dashboard access limited to port 9004
- API endpoints with authentication

### 2. Data Protection
- Backup data compression and optional encryption
- Secure storage of backup files
- Access control for backup operations

### 3. Backup Integrity
- Checksum verification for all backups
- Backup validation before storage
- Restore testing for critical backups

## Performance Optimization

### 1. Backup Performance
- Configure appropriate compression levels
- Use parallel backup jobs for large datasets
- Implement incremental backup strategies

### 2. Storage Optimization
- Automatic cleanup of old backups
- Compression for space efficiency
- Deduplication for repeated data

### 3. Resource Management
- Monitor CPU and memory usage during backups
- Configure backup scheduling during low-usage periods
- Implement backup throttling for production systems

## Next Steps
After Backup Service deployment is complete and validated:
1. Verify backup dashboard is accessible
2. Test manual backup creation
3. Confirm automated backup scheduling
4. Deploy Feature Extractor Service
5. Verify Backup Service appears in monitoring dashboard

## Support
- Flask Documentation: https://flask.palletsprojects.com/
- Redis-py Documentation: https://redis-py.readthedocs.io/
- Python Backup Libraries: https://docs.python.org/3/library/shutil.html
- Cron Scheduling: https://en.wikipedia.org/wiki/Cron
