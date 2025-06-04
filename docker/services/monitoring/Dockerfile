# Dockerfile pour le service de monitoring
FROM python:3.11-slim

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
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
