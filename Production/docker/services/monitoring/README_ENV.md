# Service de Monitoring - Configuration des Variables d'Environnement

## Vue d'ensemble

Le service de monitoring pour le système IDS distribué utilise maintenant des variables d'environnement pour une configuration flexible et adaptable à différents environnements (développement, test, production).

## Structure des Fichiers

```
monitoring/
├── monitoring_service.py          # Service principal (modifié pour env vars)
├── .env.example                   # Exemple de configuration
├── docker-compose.monitoring.yml  # Configuration Docker Compose
├── validate_monitoring_config.ps1 # Script de validation
├── Dockerfile                     # Image Docker
└── README_ENV.md                  # Cette documentation
```

## Variables d'Environnement Disponibles

### 🔧 Configuration du Logging

| Variable | Valeur par défaut | Description |
|----------|-------------------|-------------|
| `LOG_LEVEL` | `INFO` | Niveau de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LOG_FILE` | `monitoring.log` | Fichier de log |
| `LOG_FORMAT` | `%(asctime)s - %(name)s - %(levelname)s - %(message)s` | Format des logs |

### 🗄️ Configuration Redis

| Variable | Valeur par défaut | Description |
|----------|-------------------|-------------|
| `REDIS_HOST` | `redis` | Hôte Redis |
| `REDIS_PORT` | `6379` | Port Redis |
| `REDIS_DB` | `0` | Base de données Redis |
| `REDIS_PASSWORD` | (vide) | Mot de passe Redis |

### 🌐 Configuration Flask

| Variable | Valeur par défaut | Description |
|----------|-------------------|-------------|
| `FLASK_HOST` | `0.0.0.0` | Interface d'écoute Flask |
| `FLASK_PORT` | `9000` | Port Flask |
| `FLASK_DEBUG` | `false` | Mode debug Flask |

### 📊 Configuration du Monitoring

| Variable | Valeur par défaut | Description |
|----------|-------------------|-------------|
| `MONITORING_INTERVAL` | `30` | Intervalle de monitoring (secondes) |
| `HISTORY_LIMIT` | `1000` | Nombre d'entrées d'historique |
| `DASHBOARD_REFRESH` | `30` | Rafraîchissement dashboard (secondes) |

### 🚨 Configuration des Seuils d'Alerte

| Variable | Valeur par défaut | Description |
|----------|-------------------|-------------|
| `CPU_ALERT_THRESHOLD` | `90` | Seuil d'alerte CPU (%) |
| `MEMORY_ALERT_THRESHOLD` | `90` | Seuil d'alerte mémoire (%) |
| `DISK_ALERT_THRESHOLD` | `90` | Seuil d'alerte disque (%) |

### 🔍 Configuration des Services à Monitorer

| Variable | Valeur par défaut | Description |
|----------|-------------------|-------------|
| `SERVICE_CHECK_INTERVAL` | `30` | Intervalle de vérification (secondes) |
| `SERVICE_TIMEOUT` | `5` | Timeout des requêtes (secondes) |

#### Services Configurables

Pour chaque service (`PACKET_CAPTURE`, `FEATURE_EXTRACTOR`, `ML_API`, `ALERT_MANAGER`, `BACKUP_SERVICE`) :

| Pattern de Variable | Exemple | Description |
|---------------------|---------|-------------|
| `{SERVICE}_HOST` | `PACKET_CAPTURE_HOST=packet-capture` | Hôte du service |
| `{SERVICE}_PORT` | `PACKET_CAPTURE_PORT=9001` | Port du service |
| `{SERVICE}_PROTOCOL` | `PACKET_CAPTURE_PROTOCOL=http` | Protocole (http/https) |
| `{SERVICE}_ENABLED` | `PACKET_CAPTURE_ENABLED=true` | Activer le monitoring |

## Utilisation

### 1. Configuration Basic

```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer selon vos besoins
nano .env
```

### 2. Configuration pour Développement

```bash
# .env
LOG_LEVEL=DEBUG
FLASK_DEBUG=true
MONITORING_INTERVAL=10
DASHBOARD_REFRESH=10
CPU_ALERT_THRESHOLD=80
MEMORY_ALERT_THRESHOLD=80
```

### 3. Configuration pour Production

```bash
# .env
LOG_LEVEL=WARNING
MONITORING_INTERVAL=60
DASHBOARD_REFRESH=60
CPU_ALERT_THRESHOLD=95
MEMORY_ALERT_THRESHOLD=95
DISK_ALERT_THRESHOLD=95
```

### 4. Validation de la Configuration

```powershell
# Valider la configuration
.\validate_monitoring_config.ps1

# Valider avec détails
.\validate_monitoring_config.ps1 -Verbose

# Valider un fichier .env spécifique
.\validate_monitoring_config.ps1 -EnvFile "production.env"
```

### 5. Démarrage avec Docker Compose

```bash
# Démarrage basic
docker-compose -f docker-compose.monitoring.yml up

# Avec variables d'environnement custom
ENV_FILE=production.env docker-compose -f docker-compose.monitoring.yml up

# En mode détaché
docker-compose -f docker-compose.monitoring.yml up -d
```

## Exemples de Configuration

### Configuration Haute Surveillance

```bash
# Monitoring très fréquent pour environnements critiques
MONITORING_INTERVAL=5
DASHBOARD_REFRESH=5
CPU_ALERT_THRESHOLD=70
MEMORY_ALERT_THRESHOLD=70
DISK_ALERT_THRESHOLD=85
HISTORY_LIMIT=5000
SERVICE_CHECK_INTERVAL=10
SERVICE_TIMEOUT=3
```

### Configuration Économe en Ressources

```bash
# Monitoring moins fréquent pour économiser les ressources
MONITORING_INTERVAL=120
DASHBOARD_REFRESH=120
CPU_ALERT_THRESHOLD=95
MEMORY_ALERT_THRESHOLD=95
HISTORY_LIMIT=500
SERVICE_CHECK_INTERVAL=60
```

### Configuration avec Services Personnalisés

```bash
# Désactiver certains services
BACKUP_SERVICE_ENABLED=false
PACKET_CAPTURE_ENABLED=false

# Modifier les ports
ML_API_PORT=8080
ALERT_MANAGER_PORT=8081

# Utiliser HTTPS
ML_API_PROTOCOL=https
ALERT_MANAGER_PROTOCOL=https
```

## Priorité des Variables

1. **Variables d'environnement système** (priorité la plus haute)
2. **Fichier .env**
3. **Valeurs par défaut** (priorité la plus basse)

```bash
# Exemple: overrider temporairement
LOG_LEVEL=DEBUG docker-compose up
```

## Monitoring et Debugging

### Variables de Debug Utiles

```bash
LOG_LEVEL=DEBUG
FLASK_DEBUG=true
MONITORING_INTERVAL=5
SERVICE_TIMEOUT=10
```

### Logs Détaillés

```bash
# Activer tous les logs
LOG_LEVEL=DEBUG
LOG_FORMAT="%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
```

## Intégration avec Docker

### Variables dans docker-compose.yml

```yaml
services:
  monitoring:
    environment:
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - REDIS_HOST=${REDIS_HOST:-redis}
      - FLASK_PORT=${FLASK_PORT:-9000}
```

### Variables via fichier .env

```bash
# Le fichier .env est automatiquement lu par docker-compose
docker-compose -f docker-compose.monitoring.yml up
```

## Sécurité

### Variables Sensibles

```bash
# Ne jamais commiter ces variables dans le code
REDIS_PASSWORD=secret_password

# Utiliser des secrets Docker en production
```

### Permissions

```bash
# Protéger le fichier .env
chmod 600 .env
```

## Troubleshooting

### Problèmes Courants

1. **Service non accessible**
   ```bash
   # Vérifier la configuration réseau
   PACKET_CAPTURE_HOST=localhost
   PACKET_CAPTURE_PORT=9001
   ```

2. **Timeouts fréquents**
   ```bash
   # Augmenter le timeout
   SERVICE_TIMEOUT=15
   ```

3. **Trop d'alertes**
   ```bash
   # Ajuster les seuils
   CPU_ALERT_THRESHOLD=95
   MEMORY_ALERT_THRESHOLD=95
   ```

### Logs de Debug

```bash
# Activer le debug complet
LOG_LEVEL=DEBUG
FLASK_DEBUG=true

# Vérifier les logs
docker-compose logs monitoring
```

## Migration depuis l'Ancienne Version

1. **Sauvegardez votre configuration actuelle**
2. **Identifiez les valeurs modifiées** par rapport aux défauts
3. **Créez un fichier .env** avec vos valeurs
4. **Testez avec le script de validation**
5. **Déployez la nouvelle version**

Exemple de migration :

```bash
# Ancienne configuration (dans le code)
# self.redis_client = redis.Redis(host='redis', port=6379)
# self.app.run(host='0.0.0.0', port=9000)

# Nouvelle configuration (.env)
REDIS_HOST=redis
REDIS_PORT=6379
FLASK_HOST=0.0.0.0
FLASK_PORT=9000
```

## Support et Contribution

Pour des questions ou des améliorations, consultez la documentation principale du projet ou créez une issue dans le repository.
