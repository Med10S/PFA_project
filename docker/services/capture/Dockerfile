# Dockerfile pour le service de capture de paquets
FROM python:3.11-slim

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    tcpdump \
    libpcap-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Création du répertoire de travail
WORKDIR /app

# Copie des requirements spécifiques au service
COPY docker/services/capture/requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie du service de capture
COPY docker/services/capture/packet_capture_service.py .

# Création des dossiers nécessaires
RUN mkdir -p /app/shared /app/logs /app/buffer

# Configuration des permissions
RUN chmod +x packet_capture_service.py

# Port d'exposition (pour monitoring)
EXPOSE 9001

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Commande de démarrage
CMD ["python", "packet_capture_service.py"]
