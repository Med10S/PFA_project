# Dockerfile pour le service de gestion d'alertes
FROM python:3.11-slim

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    vim \
    gcc \
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
RUN mkdir -p /app/logs

# Configuration des permissions
RUN chmod +x alert_manager_service.py

# Port d'exposition
EXPOSE 9003

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=alert_manager_service.py
ENV LOG_LEVEL=INFO \
    LOG_FILE=/app/logs/alerts.log \
    LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s" \
    REDIS_HOST=redis \
    REDIS_PORT=6379 \
    REDIS_DB=2 \
    REDIS_ALERTS_LIMIT=10000 \
    REDIS_SEVERITY_LIMIT=1000 \
    FLASK_HOST=0.0.0.0 \
    FLASK_PORT=9003 \
    FLASK_DEBUG=false \
    MAX_ALERTS_PER_PAGE=100 \
    ALERT_HISTORY_LIMIT=1000 \
    MAX_SEVERITY_SCORE=5 \
    REPEATED_ALERT_WINDOW_MINUTES=5 \
    REPEATED_ALERT_CHECK_COUNT=50 \
    SMTP_SERVER=localhost \
    SMTP_PORT=587 \
    SMTP_FROM_EMAIL=ids-alerts@company.com \
    ALERT_EMAIL_RECIPIENT=admin@company.com \
    CRITICAL_NOTIFICATION_METHODS=email,sms \
    HIGH_NOTIFICATION_METHODS=email \
    MEDIUM_NOTIFICATION_METHODS=dashboard \
    LOW_NOTIFICATION_METHODS=dashboard \
    ALERT_CHANNELS=alerts:ml,alerts:monitoring,alerts:network

# Commande de démarrage
CMD ["python", "alert_manager_service.py"]
