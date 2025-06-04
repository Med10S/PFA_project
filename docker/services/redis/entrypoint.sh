#!/bin/sh

# Try to set vm.overcommit_memory if available (skip if not available)
if command -v sysctl > /dev/null 2>&1; then
    sysctl -w vm.overcommit_memory=1 2>/dev/null || echo "Warning: Could not set vm.overcommit_memory"
else
    echo "Warning: sysctl not available, skipping vm.overcommit_memory setting"
fi

# Interpole les variables d'environnement dans le fichier de configuration
envsubst < /usr/local/etc/redis/redis.conf.template > /usr/local/etc/redis/redis.conf

# Add password if provided
if [ -n "$REDIS_PASSWORD" ]; then
    echo "requirepass $REDIS_PASSWORD" >> /usr/local/etc/redis/redis.conf
fi

# Verifiez si le fichier de configuration est valide
echo "Configuration Redis generee avec succes"

# Demarrer Redis avec le fichier de configuration interpole
exec "$@"