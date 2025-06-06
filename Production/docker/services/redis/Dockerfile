# Utilisez l'image officielle de Redis comme base (version plus sécurisée)
FROM redis:8.0-alpine

# Installez gettext pour envsubst et procps pour sysctl + mises à jour de sécurité
RUN apk update && apk upgrade && apk add --no-cache gettext procps

# Créer un utilisateur non-root pour la sécurité
RUN adduser -D -s /bin/sh redis-user

# Exposez le port par défaut de Redis
EXPOSE 6379

# Copiez le script de configuration personnalisé dans l'image
COPY redis.conf.template /usr/local/etc/redis/redis.conf.template
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# Rendre le script exécutable et créer les répertoires nécessaires
RUN mkdir -p /usr/local/etc/redis && chmod +x /usr/local/bin/entrypoint.sh

# Définissez les variables d'environnement par défaut
ENV REDIS_PASSWORD=""
ENV REDIS_MAX_MEMORY="256mb"
ENV REDIS_APPENDONLY="yes"

# Utilisez le script d'entrée pour démarrer Redis après avoir interpolé les variables
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]