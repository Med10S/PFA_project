# Alert Manager Service Deployment Guide - GNS3 Topology

## Service Overview
The Alert Manager Service handles real-time alert processing, notification management, and alert correlation for the IDS distributed system. It receives alerts from various services and manages notifications through multiple channels.

## Prerequisites
- Redis container deployed and running (172.20.0.10)
- Docker Engine installed and running
- GNS3 network `ids-network` created
- SMTP server configuration (optional, for email alerts)

## Configuration Files

### 1. Create Alert Manager Service Directory
```powershell
mkdir "c:\ids-deployment\alerts"
mkdir "c:\ids-deployment\alerts\logs"
mkdir "c:\ids-deployment\alerts\templates"
```

### 2. Environment File (`.env`)
Create `c:\ids-deployment\alerts\.env`:

```env
# Redis Configuration
REDIS_HOST=172.20.0.10
REDIS_PORT=6379
REDIS_PASSWORD=SecureRedisPassword123!
REDIS_DB=0
REDIS_ALERTS_LIMIT=10000
REDIS_SEVERITY_LIMIT=1000

# Flask Application Configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=9003
FLASK_DEBUG=false
FLASK_SECRET_KEY=AlertManagerSecretKey123!

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/app/logs/alerts.log
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=5

# Alert Processing Configuration
MAX_ALERTS_PER_PAGE=100
ALERT_HISTORY_LIMIT=1000
MAX_SEVERITY_SCORE=5
REPEATED_ALERT_WINDOW_MINUTES=5
REPEATED_ALERT_CHECK_COUNT=50

# SMTP Configuration for Email Alerts
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=ids-alerts@company.com

# Email Recipients
ALERT_EMAIL_RECIPIENT=admin@company.com
CRITICAL_EMAIL_RECIPIENT=security-team@company.com
EMERGENCY_EMAIL_RECIPIENT=incident-response@company.com

# Slack Configuration (Optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
SLACK_CHANNEL=ids-alerts
SLACK_USERNAME=IDS-Alert-Bot

# SMS Configuration (Optional)
SMS_PROVIDER=twilio
SMS_ACCOUNT_SID=your-twilio-sid
SMS_AUTH_TOKEN=your-twilio-token
SMS_FROM_NUMBER=+1234567890
SMS_TO_NUMBER=+0987654321

# Notification Methods by Severity
CRITICAL_NOTIFICATION_METHODS=email,sms,slack
HIGH_NOTIFICATION_METHODS=email,slack
MEDIUM_NOTIFICATION_METHODS=email
LOW_NOTIFICATION_METHODS=dashboard

# Alert Channels Configuration
ALERT_CHANNELS=alerts:ml,alerts:monitoring,alerts:network,alerts:system

# Alert Filtering and Correlation
ENABLE_ALERT_CORRELATION=true
CORRELATION_WINDOW_SECONDS=300
ENABLE_ALERT_SUPPRESSION=true
SUPPRESSION_WINDOW_SECONDS=600
ENABLE_RATE_LIMITING=true
MAX_ALERTS_PER_MINUTE=100

# Dashboard Configuration
DASHBOARD_REFRESH_INTERVAL=5000
MAX_DASHBOARD_ALERTS=200
ALERT_AUTO_REFRESH=true
SHOW_RESOLVED_ALERTS=true
ALERT_RETENTION_DAYS=30

# Security Configuration
ENABLE_API_AUTHENTICATION=false
API_KEY=your-api-key-here
ALLOWED_ORIGINS=http://localhost:3000,http://172.20.0.20:9000

# Performance Settings
ALERT_PROCESSING_THREADS=4
NOTIFICATION_QUEUE_SIZE=1000
BATCH_NOTIFICATION_SIZE=10
NOTIFICATION_RETRY_COUNT=3
NOTIFICATION_TIMEOUT_SECONDS=30
```

## Docker Build

### 1. Create Dockerfile
Create the following Dockerfile at: `c:\ids-deployment\alerts\Dockerfile`

```dockerfile
# Dockerfile pour le service de gestion d'alertes
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

# Copie du service d'alertes
COPY alert_manager_service.py .

# Création des dossiers nécessaires
RUN mkdir -p /app/logs /app/templates

# Configuration des permissions
RUN chmod +x alert_manager_service.py

# Port d'exposition
EXPOSE 9003

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=alert_manager_service.py

# Configuration des logs
ENV LOG_LEVEL=INFO \
    LOG_FILE=/app/logs/alerts.log \
    LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Configuration Redis
ENV REDIS_HOST=redis \
    REDIS_PORT=6379 \
    REDIS_DB=0 \
    REDIS_ALERTS_LIMIT=10000 \
    REDIS_SEVERITY_LIMIT=1000

# Configuration Flask
ENV FLASK_HOST=0.0.0.0 \
    FLASK_PORT=9003 \
    FLASK_DEBUG=false

# Configuration des alertes
ENV MAX_ALERTS_PER_PAGE=100 \
    ALERT_HISTORY_LIMIT=1000 \
    MAX_SEVERITY_SCORE=5 \
    REPEATED_ALERT_WINDOW_MINUTES=5 \
    REPEATED_ALERT_CHECK_COUNT=50

# Configuration SMTP
ENV SMTP_SERVER=localhost \
    SMTP_PORT=587 \
    SMTP_FROM_EMAIL=ids-alerts@company.com \
    ALERT_EMAIL_RECIPIENT=admin@company.com

# Configuration des méthodes de notification
ENV CRITICAL_NOTIFICATION_METHODS=email,sms \
    HIGH_NOTIFICATION_METHODS=email \
    MEDIUM_NOTIFICATION_METHODS=dashboard \
    LOW_NOTIFICATION_METHODS=dashboard

# Configuration des canaux d'alerte
ENV ALERT_CHANNELS=alerts:ml,alerts:monitoring,alerts:network

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9003/health || exit 1

# Commande de démarrage
CMD ["python", "alert_manager_service.py"]
```

### 2. Service Accessibility Test
```powershell
# Test from host system
curl http://172.20.0.40:9003/health

# Test from another container
docker run --rm --network ids-network curlimages/curl:latest `
  curl -f http://172.20.0.40:9003/health
```

## Service Endpoints

### Web Dashboard
- **URL:** http://172.20.0.40:9003/
- **Description:** Alert management dashboard
- **Features:** Alert viewing, management, statistics, notification settings

### API Endpoints
- **Health Check:** `GET /health`
- **Alerts:** `GET /api/alerts`
- **Create Alert:** `POST /api/alerts`
- **Alert Details:** `GET /api/alerts/{id}`
- **Update Alert:** `PUT /api/alerts/{id}`
- **Delete Alert:** `DELETE /api/alerts/{id}`
- **Alert Statistics:** `GET /api/stats`
- **Notification Test:** `POST /api/test-notification`

### Alert Creation Format
```json
{
  "title": "Network Intrusion Detected",
  "message": "Suspicious activity detected from IP 192.168.1.100",
  "severity": "high",
  "source": "ml-api",
  "category": "security",
  "tags": ["intrusion", "network", "suspicious"],
  "metadata": {
    "source_ip": "192.168.1.100",
    "confidence": 0.95,
    "threat_type": "malware"
  }
}
```

## Integration with Other Services

### Redis Integration
- **Alert Channels:** `alerts:ml`, `alerts:monitoring`, `alerts:network`
- **Notification Queue:** `notification_queue`
- **Alert History:** `alert_history`

### ML-API Integration
- Receives threat detection alerts
- Processes ML model predictions
- Correlates security events

### Monitoring Integration
- Receives system health alerts
- Processes performance warnings
- Handles service status changes

### Notification Methods
- **Email:** SMTP-based email notifications
- **Slack:** Webhook-based Slack notifications
- **SMS:** Twilio-based SMS notifications
- **Dashboard:** Real-time dashboard alerts

## Troubleshooting

### Common Issues

#### 1. Container Won't Start
```powershell
# Check Docker logs
docker logs ids-alert-manager

# Common causes:
# - Port 9003 already in use
# - Invalid environment variables
# - Missing Redis connection
# - SMTP configuration errors
```

#### 2. Email Notifications Not Working
```powershell
# Test SMTP configuration
docker exec ids-alert-manager python -c "
import smtplib
import os
server = smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT')))
server.starttls()
server.login(os.getenv('SMTP_USERNAME'), os.getenv('SMTP_PASSWORD'))
print('SMTP authentication successful')
server.quit()
"

# Check SMTP logs
docker exec ids-alert-manager cat /app/logs/alerts.log | grep SMTP
```

#### 3. High Alert Volume
```powershell
# Check alert processing performance
docker stats ids-alert-manager --no-stream

# Monitor alert queue
docker exec ids-alert-manager python -c "
import redis
import os
r = redis.Redis(host=os.getenv('REDIS_HOST'), port=int(os.getenv('REDIS_PORT')), password=os.getenv('REDIS_PASSWORD'))
print(f'Alert queue length: {r.llen(\"alert_queue\")}')
"
```

#### 4. Redis Connection Issues
```powershell
# Test Redis connectivity
docker exec ids-alert-manager python -c "
import redis
r = redis.Redis(host='172.20.0.10', port=6379, password='SecureRedisPassword123!')
print(r.ping())
"

# Check Redis container status
docker ps -f name=ids-redis
```

## Security Considerations

### 1. Network Security
- Service bound to internal IP (172.20.0.40)
- Dashboard access limited to port 9003
- API endpoints with optional authentication

### 2. Data Protection
- Sensitive alert data encrypted in Redis
- Email credentials securely stored
- Alert history with retention policies

### 3. Notification Security
- SMTP authentication required
- Webhook URLs validated
- SMS provider authentication

## Performance Optimization

### 1. Alert Processing
- Configure appropriate batch sizes
- Enable alert correlation to reduce noise
- Implement rate limiting for high-volume sources

### 2. Notification Optimization
- Use notification queuing for reliability
- Configure retry policies for failed notifications
- Implement notification throttling

### 3. Resource Management
- Monitor memory usage for alert history
- Configure log rotation
- Optimize Redis memory usage

## Next Steps
After Alert Manager Service deployment is complete and validated:
1. Verify alert dashboard is accessible
2. Test notification methods (email, Slack, etc.)
3. Confirm Redis alert channels are working
4. Deploy Backup Service
5. Verify Alert Manager appears in monitoring dashboard

## Support
- Flask Documentation: https://flask.palletsprojects.com/
- Redis-py Documentation: https://redis-py.readthedocs.io/
- SMTP Configuration: https://docs.python.org/3/library/smtplib.html
- Twilio SMS API: https://www.twilio.com/docs/sms
