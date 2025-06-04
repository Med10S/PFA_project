#!/bin/bash

# Activer vm.overcommit_memory
sysctl -w vm.overcommit_memory=1

# Interpole les variables d'environnement dans le fichier de configuration
envsubst < /usr/local/etc/redis/redis.conf.template > /usr/local/etc/redis/redis.conf

# Vérifiez si le fichier de configuration est valide
if ! redis-server --test-config /usr/local/etc/redis/redis.conf; then
    echo "Erreur de configuration de Redis."
    exit 1
fi

# Démarrer Redis avec le fichier de configuration interpolé
exec "$@"