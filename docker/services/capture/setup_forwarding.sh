#!/bin/sh
# Script de configuration du forwarding réseau pour le conteneur de capture

echo "=== Configuration du forwarding réseau ==="

# Activer le forwarding IP immédiatement
echo 1 > /proc/sys/net/ipv4/ip_forward
echo "✓ IP forwarding activé"

# Configurer les règles iptables pour le forwarding
echo "Configuration des règles iptables..."

# Vider les règles existantes
iptables -F
iptables -t nat -F
iptables -t mangle -F

# Politique par défaut ACCEPT pour le forwarding
iptables -P FORWARD ACCEPT
iptables -P INPUT ACCEPT
iptables -P OUTPUT ACCEPT

# Permettre le forwarding entre toutes les interfaces
iptables -A FORWARD -j ACCEPT

# Permettre le forwarding spécifique pour Redis (port 6379)
iptables -A FORWARD -p tcp --dport 6379 -j ACCEPT
iptables -A FORWARD -p tcp --sport 6379 -j ACCEPT

# NAT pour le trafic sortant si nécessaire
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

# Autoriser le trafic local
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# Autoriser les connexions établies
iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT

echo "✓ Règles iptables configurées"

# Afficher la configuration
echo "=== Configuration réseau actuelle ==="
echo "IP forwarding: $(cat /proc/sys/net/ipv4/ip_forward)"
echo "Interfaces réseau:"
ip addr show
echo "Routes:"
ip route show
echo "Règles iptables:"
iptables -L -n
echo "Règles NAT:"
iptables -t nat -L -n

echo "=== Configuration terminée ==="
