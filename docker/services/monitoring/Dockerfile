# Dockerfile pour le service de monitoring
FROM python:3.11-slim

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Création du répertoire de travail
WORKDIR /app

# Copie des requirements spécifiques au service
COPY docker/services/monitoring/requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie du service de monitoring
COPY docker/services/monitoring/monitoring_service.py .

# Création des dossiers nécessaires
RUN mkdir -p /app/logs

# Configuration des permissions
RUN chmod +x monitoring_service.py

# Port d'exposition
EXPOSE 9000

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=monitoring_service.py

# Commande de démarrage
CMD ["python", "monitoring_service.py"]
