# ML-API Service Deployment Guide - GNS3 Topology

## Service Overview
The ML-API Service provides real-time machine learning-based intrusion detection using ensemble models (KNN, MLP, XGBoost). It processes network features and returns threat classifications with confidence scores.

## Prerequisites
- Redis container deployed and running (172.20.0.10)
- Docker Engine installed and running
- GNS3 network `ids-network` created
- ML model files available (KNN, MLP, XGBoost models)

## Configuration Files

### 1. Create ML-API Service Directory
```powershell
mkdir "c:\ids-deployment\ml-api"
mkdir "c:\ids-deployment\ml-api\logs"
mkdir "c:\ids-deployment\ml-api\models"
mkdir "c:\ids-deployment\ml-api\functions"
```

### 2. Environment File (`.env`)
Create `c:\ids-deployment\ml-api\.env`:

```env
# Redis Configuration
REDIS_HOST=172.20.0.10
REDIS_PORT=6379
REDIS_PASSWORD=SecureRedisPassword123!
REDIS_DB=0

# API Configuration
API_HOST=0.0.0.0
API_PORT=5000
API_TITLE=IDS ML Detection API
API_VERSION=1.0.0
API_DEBUG=false

# Detection Thresholds
DETECTION_THRESHOLD=0.5
CONFIDENCE_THRESHOLD=0.7

# Model Weights (Ensemble)
KNN_MODEL_WEIGHT=0.3
MLP_MODEL_WEIGHT=0.35
XGB_MODEL_WEIGHT=0.35

# Model File Paths
KNN_MODEL_PATH=/app/models/KNN_best.pkl
MLP_MODEL_PATH=/app/models/mlp_best.pkl
XGB_MODEL_PATH=/app/models/xgb_best.pkl
SCALER_PATH=/app/models/scaler.pkl
LABEL_ENCODER_PATH=/app/models/label_encoders.pkl

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=/app/logs/ml_api.log
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=5

# Alert Configuration
ALERT_ENABLE_LOGGING=true
ALERT_ENABLE_WEBHOOKS=false
ALERT_WEBHOOK_URL=
ALERT_LOG_FILE=/app/logs/alerts.log
ALERT_REDIS_CHANNEL=ml_alerts
ALERT_SEVERITY_MAPPING={"normal": 0, "suspicious": 1, "malicious": 2}

# Performance Settings
MAX_BATCH_SIZE=1000
PREDICTION_TIMEOUT=30
ENABLE_CACHING=true
CACHE_TTL_SECONDS=300
MAX_CONCURRENT_REQUESTS=50

# Feature Processing
FEATURE_VALIDATION=true
NORMALIZE_FEATURES=true
HANDLE_MISSING_VALUES=true
MISSING_VALUE_STRATEGY=median

# Health Check Configuration
HEALTH_CHECK_MODELS=true
HEALTH_CHECK_REDIS=true
HEALTH_CHECK_INTERVAL=60
```

## Docker Build

### 1. Create Dockerfile
Create the following Dockerfile at: `c:\ids-deployment\ml-api\Dockerfile`

```dockerfile
# Dockerfile pour l'API ML
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

# Copie du service ML et des modèles
COPY realtime_detection_service.py .
COPY models/ ./models/
COPY functions/ ./functions/
COPY config.py ./config.py

# Création des dossiers nécessaires
RUN mkdir -p /app/logs

# Configuration des permissions
RUN chmod +x realtime_detection_service.py

# Port d'exposition
EXPOSE 5000

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=realtime_detection_service.py

# Configuration de l'API
ENV API_HOST=0.0.0.0 \
    API_PORT=5000 \
    API_TITLE="IDS ML Detection API" \
    API_VERSION=1.0.0

# Seuils de détection
ENV DETECTION_THRESHOLD=0.5 \
    CONFIDENCE_THRESHOLD=0.7

# Poids des modèles
ENV KNN_MODEL_WEIGHT=0.3 \
    MLP_MODEL_WEIGHT=0.35 \
    XGB_MODEL_WEIGHT=0.35

# Configuration du logging
ENV LOG_LEVEL=INFO \
    LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Configuration des alertes
ENV ALERT_ENABLE_LOGGING=true \
    ALERT_ENABLE_WEBHOOKS=false \
    ALERT_WEBHOOK_URL="" \
    ALERT_LOG_FILE=alerts.log

# Configuration Redis
ENV REDIS_HOST=redis \
    REDIS_PORT=6379 \
    REDIS_DB=0 \
    REDIS_PASSWORD=""

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Commande de démarrage
CMD ["python", "realtime_detection_service.py"]
```

## Health Checks and Validation

### 1. Container Health Check
```powershell
# Check if container is running
docker ps -f name=ids-ml-api

# Check container health
docker exec ids-ml-api curl -f http://localhost:5000/health || echo "Health check failed"
```

### 2. Service Accessibility Test
```powershell
# Test from host system
curl http://172.20.0.30:5000/health

# Test from another container
docker run --rm --network ids-network curlimages/curl:latest `
  curl -f http://172.20.0.30:5000/health
```



## Service Endpoints

### API Endpoints
- **Health Check:** `GET /health`
- **Prediction:** `POST /predict`
- **Batch Prediction:** `POST /predict/batch`
- **Model Info:** `GET /models/info`
- **Metrics:** `GET /metrics`

### Prediction Request Format
```json
{
  "features": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
}
```

### Prediction Response Format
```json
{
  "prediction": "normal",
  "confidence": 0.95,
  "threat_score": 0.05,
  "model_votes": {
    "knn": "normal",
    "mlp": "normal", 
    "xgb": "normal"
  },
  "timestamp": "2025-06-04T10:30:00Z"
}
```

## Integration with Other Services

### Redis Integration
- **Alert Channel:** `ml_alerts`
- **Prediction Queue:** `ml_predictions`
- **Feature Queue:** `feature_queue`

### Feature Extractor Integration
- Receives processed features from Feature Extractor
- Publishes predictions to Alert Manager

### Monitoring Integration
- Health endpoint monitored by Monitoring Service
- Metrics exposed for monitoring dashboard

## Troubleshooting

### Common Issues

#### 1. Container Won't Start
```powershell
# Check Docker logs
docker logs ids-ml-api

# Common causes:
# - Port 5000 already in use
# - Missing model files
# - Invalid environment variables
# - Insufficient memory for models
```

#### 2. Model Loading Errors
```powershell
# Check model files
docker exec ids-ml-api ls -la /app/models/

# Test model loading
docker exec ids-ml-api python -c "
import joblib
try:
    model = joblib.load('/app/models/KNN_best.pkl')
    print('KNN model loaded successfully')
except Exception as e:
    print(f'KNN model error: {e}')
"
```

#### 3. Prediction Errors
```powershell
# Check prediction logs
docker exec ids-ml-api cat /app/logs/ml_api.log | grep ERROR

# Test with sample data
curl -X POST -H "Content-Type: application/json" -d '{"features": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]}' http://172.20.0.30:5000/predict
```

#### 4. High Memory Usage
```powershell
# Check container resources
docker stats ids-ml-api --no-stream

# If memory usage is high, consider:
# - Reducing batch size
# - Using lighter models
# - Enabling model caching optimization
```

## Security Considerations

### 1. Network Security
- Service bound to internal IP (172.20.0.30)
- API access limited to port 5000
- No external dependencies required

### 2. Model Security
- Models stored in protected volumes
- No model updates via API (read-only)
- Prediction logging for audit trail

### 3. Data Protection
- Input validation on all prediction requests
- Sensitive data not logged
- Redis communication encrypted

## Performance Optimization

### 1. Model Optimization
- Enable model caching with `ENABLE_CACHING=true`
- Adjust cache TTL based on usage patterns
- Use batch predictions for multiple features

### 2. Resource Management
- Set appropriate memory limits in Docker
- Monitor CPU usage during peak loads
- Configure request timeouts

### 3. Scaling Considerations
- Deploy multiple ML-API instances for load balancing
- Use Redis for prediction result caching
- Implement prediction queuing for high loads

## Next Steps
After ML-API Service deployment is complete and validated:
1. Verify API endpoints are accessible
2. Test prediction functionality with sample data
3. Confirm Redis integration is working
4. Deploy Alert Manager Service
5. Verify ML-API appears in monitoring dashboard

## Support
- Flask Documentation: https://flask.palletsprojects.com/
- Scikit-learn Documentation: https://scikit-learn.org/
- XGBoost Documentation: https://xgboost.readthedocs.io/
- Redis-py Documentation: https://redis-py.readthedocs.io/
