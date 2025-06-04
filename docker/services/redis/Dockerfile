# Utilisez l'image officielle de Redis comme base
FROM redis:latest

# Exposez le port par défaut de Redis
EXPOSE 6379

# Copiez le script de configuration personnalisé dans l'image
COPY redis.conf.template /usr/local/etc/redis/redis.conf.template
COPY entrypoint.sh /entrypoint.sh

# Rendre le script exécutable
RUN chmod +x /entrypoint.sh

# Définissez les variables d'environnement par défaut
ENV REDIS_PASSWORD=""
ENV REDIS_MAX_MEMORY="256mb"
ENV REDIS_APPENDONLY="yes"

# Utilisez le script d'entrée pour démarrer Redis après avoir interpolé les variables
ENTRYPOINT ["/entrypoint.sh"]
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]