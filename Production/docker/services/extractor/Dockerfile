# Dockerfile pour le service d'extraction de features
FROM python:3.11-slim

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    libpcap-dev \
    gcc \
    vi \
    && rm -rf /var/lib/apt/lists/*

# Création du répertoire de travail
WORKDIR /app

COPY . .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt


# Création des dossiers nécessaires
RUN mkdir -p /app/shared /app/logs /app/temp_pcap

# Configuration des permissions
RUN chmod +x feature_extraction_service.py

# Port d'exposition (pour monitoring)
EXPOSE 9002

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV REDIS_HOST=redis \
    REDIS_PORT=6379 \
    PROCESSING_WORKERS=4 \
    BATCH_SIZE=100 \
    API_ENDPOINT=http://ml-api:8001 \
    LOG_LEVEL=INFO \
    ENCRYPTION_KEY="" \
    NODE_ID=extractor-node \
    REDIS_DB=1

# Commande de démarrage
CMD ["python", "feature_extraction_service.py"]
