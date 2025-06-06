#!/bin/sh
# Entrypoint pour le conteneur de capture avec configuration réseau

echo "=== DÉMARRAGE DU SERVICE DE CAPTURE ==="

# Vérifier les privilèges réseau
if [ ! -w /proc/sys/net/ipv4/ip_forward ]; then
    echo "⚠️ ATTENTION: Privilèges réseau insuffisants"
    echo "Le conteneur doit être lancé avec --privileged ou --cap-add=NET_ADMIN"
fi

# Configuration du forwarding réseau
if [ -f /app/setup_forwarding.sh ]; then
    echo "Configuration du forwarding réseau..."
    chmod +x /app/setup_forwarding.sh
    /app/setup_forwarding.sh
else
    echo "⚠️ Script de forwarding non trouvé"
fi

# Créer les répertoires nécessaires
mkdir -p /app/logs /app/buffer /app/shared

# Démarrer le service de capture
echo "Démarrage du service de capture de paquets..."
exec python packet_capture_service.py
