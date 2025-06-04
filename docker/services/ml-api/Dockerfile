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
