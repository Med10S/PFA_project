# Dockerfile pour le service de backup
FROM python:3.11-slim

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Création du répertoire de travail
WORKDIR /app

# Copie des requirements spécifiques au service
COPY docker/services/backup/requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie du service de backup
COPY docker/services/backup/backup_service.py .

# Création des dossiers nécessaires
RUN mkdir -p /app/logs /app/backups

# Configuration des permissions
RUN chmod +x backup_service.py

# Port d'exposition
EXPOSE 9004

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=backup_service.py
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ENV REDIS_DB=0
ENV REDIS_PASSWORD=""

# Volume pour les sauvegardes
VOLUME ["/app/backups"]

# Commande de démarrage
CMD ["python", "backup_service.py"]
