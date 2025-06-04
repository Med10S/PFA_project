# Dockerfile pour l'API ML
FROM python:3.11-slim

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Création du répertoire de travail
WORKDIR /app

# Copie des requirements spécifiques au service
COPY docker/services/ml-api/requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie du service ML
COPY realtime_detection_service.py .
COPY models/ ./models/

# Création des dossiers nécessaires
RUN mkdir -p /app/logs

# Configuration des permissions
RUN chmod +x realtime_detection_service.py

# Port d'exposition
EXPOSE 5000

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=realtime_detection_service.py

# Commande de démarrage
CMD ["python", "realtime_detection_service.py"]
# Configuration de l'API
ENV API_HOST=0.0.0.0
ENV API_PORT=8000
ENV API_TITLE="Système de Détection d'Intrusion Temps Réel"
ENV API_VERSION=1.0.0

# Seuils de détection
ENV DETECTION_THRESHOLD=0.5
ENV CONFIDENCE_THRESHOLD=0.7

# Poids des modèles
ENV KNN_MODEL_WEIGHT=0.3
ENV MLP_MODEL_WEIGHT=0.35
ENV XGB_MODEL_WEIGHT=0.35

# Configuration du logging
ENV LOG_LEVEL=INFO
ENV LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Configuration des alertes
ENV ALERT_ENABLE_LOGGING=true
ENV ALERT_ENABLE_WEBHOOKS=false
ENV ALERT_WEBHOOK_URL=""
ENV ALERT_LOG_FILE=alerts.log