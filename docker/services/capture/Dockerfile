# Dockerfile pour le service de capture de paquets
FROM python:3.11-slim

# Installation des dépendances système pour capture et forwarding
RUN apt-get update && apt-get install -y \
    tcpdump \
    libpcap-dev \
    gcc \
    iptables \
    iproute2 \
    bridge-utils \
    net-tools \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Configuration pour le forwarding IP
RUN echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf

# Création du répertoire de travail
WORKDIR /app

# Copie des requirements spécifiques au service
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie du service de capture
COPY packet_capture_service.py .

# Création des dossiers nécessaires
RUN mkdir -p /app/shared /app/logs /app/buffer

# Configuration des permissions
RUN chmod +x packet_capture_service.py

# Port d'exposition (pour monitoring)
EXPOSE 9001

# Variables d'environnement par défaut
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV INTERFACE=eth0 \
    CAPTURE_INTERVAL=10 \
    REDIS_DB=0 \
    BUFFER_SIZE=1000 \
    REDIS_HOST=redis \
    REDIS_PORT=6379 \
    LOG_LEVEL=INFO \
    REDIS_PASSWORD="" \
    ENCRYPTION_KEY=""

# Commande de démarrage
CMD ["python", "packet_capture_service.py"]
