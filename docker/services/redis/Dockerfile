# Utilisez l'image officielle de Redis comme base
FROM redis:latest


# Update the system packages
RUN apt-get update && apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Exposez le port par défaut de Redis
EXPOSE 6379

# Définissez les variables d'environnement par défaut
ENV REDIS_PASSWORD=""
ENV REDIS_MAX_MEMORY="256mb"
ENV REDIS_APPENDONLY="yes"

# Copiez le script de configuration personnalisé dans l'image
COPY redis.conf /usr/local/etc/redis/redis.conf

# Utilisez le script de configuration personnalisé pour démarrer Redis
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
