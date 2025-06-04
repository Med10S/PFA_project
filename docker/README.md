# Système IDS Distribué - Structure Docker

## 📁 Structure des Dossiers

```
docker/
├── docker-compose.yml          # Orchestration principale
├── config/                     # Configurations partagées
│   ├── nginx.conf             # Configuration Nginx
│   ├── redis.conf             # Configuration Redis
│   └── requirements.txt       # Dépendances Python
├── services/                   # Services microservices
│   ├── capture/               # Service de capture de paquets
│   │   ├── Dockerfile
│   │   └── packet_capture_service.py
│   ├── extractor/             # Service d'extraction de features
│   │   ├── Dockerfile
│   │   └── feature_extraction_service.py
│   ├── monitoring/            # Service de monitoring
│   │   ├── Dockerfile
│   │   └── monitoring_service.py
│   ├── alerts/                # Service de gestion d'alertes
│   │   ├── Dockerfile
│   │   └── alert_manager_service.py
│   ├── backup/                # Service de sauvegarde
│   │   ├── Dockerfile
│   │   └── backup_service.py
│   └── ml-api/                # Service ML (API de détection)
│       └── Dockerfile
└── scripts/                   # Scripts utilitaires
    ├── deploy.ps1             # Déploiement PowerShell
    ├── deploy.sh              # Déploiement Bash
    └── test_system.py         # Tests système
```

## 🚀 Déploiement

### 1. Configuration initiale

```powershell
# Copier le fichier de configuration
cd docker/config
Copy-Item .env.example .env

# Éditer les variables d'environnement
notepad .env
```

### 2. Démarrage du système

```powershell
# Depuis le dossier docker/
docker-compose up -d
```

### 3. Vérification des services

```powershell
# Vérifier le statut
docker-compose ps

# Consulter les logs
docker-compose logs -f

# Accéder au dashboard de monitoring
# http://localhost (redirigé vers le service de monitoring)
```

## 🔧 Services

### 🕸️ Capture de paquets (packet-capture)
- **Port**: 9001
- **Fonction**: Capture les paquets réseau et les envoie vers Redis
- **Privilèges**: Nécessite NET_ADMIN et NET_RAW

### ⚙️ Extraction de features (feature-extractor)
- **Port**: 9002
- **Fonction**: Traite les paquets et extrait les features pour l'analyse ML
- **Dépendances**: unsw_nb15_feature_extractor.py

### 🤖 API ML (ml-api)
- **Port**: 5000
- **Fonction**: Analyse ML pour la détection d'intrusions
- **Endpoint**: http://localhost:5000/predict

### 🚨 Gestion d'alertes (alert-manager)
- **Port**: 9003
- **Fonction**: Traite et notifie les alertes de sécurité

### 📊 Monitoring (monitoring)
- **Port**: 9000
- **Fonction**: Dashboard de surveillance du système
- **Interface**: http://localhost/

### 💾 Backup (backup-service)
- **Port**: 9004
- **Fonction**: Sauvegarde automatique des données critiques

### 🌐 Nginx (Load Balancer)
- **Port**: 80, 443
- **Fonction**: Proxy inverse et équilibrage de charge

### 🗄️ Redis
- **Port**: 6379
- **Fonction**: Bus de communication entre services

## 📋 API Endpoints

### Monitoring
- `GET /` - Dashboard principal
- `GET /metrics` - Métriques JSON
- `GET /health` - Statut santé

### Alertes
- `GET /alerts` - Liste des alertes
- `POST /alerts/{id}/acknowledge` - Acquitter une alerte
- `GET /stats` - Statistiques des alertes

### Backup
- `POST /backup` - Créer une sauvegarde
- `GET /backups` - Lister les sauvegardes
- `GET /backups/{id}/download` - Télécharger une sauvegarde

### ML API
- `POST /predict` - Prédiction ML
- `GET /health` - Statut du modèle

## 🛠️ Développement

### Structure modulaire
Chaque service est autonome avec :
- Son propre Dockerfile
- Ses dépendances spécifiques
- Son code source isolé
- Sa configuration dédiée

### Communication
- **Redis**: Bus de messages entre services
- **HTTP REST**: APIs externes
- **Nginx**: Routage et load balancing

### Logging
Tous les logs sont centralisés dans `/app/logs/` et peuvent être consultés via :
```powershell
docker-compose logs [service-name]
```

## 🔒 Sécurité

### Chiffrement
- Communications chiffrées entre services
- Clés de chiffrement configurables
- Isolation réseau Docker

### Authentification
- Variables d'environnement pour les credentials
- Pas de mots de passe en dur dans le code

### Monitoring sécurisé
- Alertes automatiques sur les anomalies
- Dashboard temps réel des métriques
- Sauvegarde automatique des données critiques

## 📈 Performance

### Optimisations
- Traitement parallèle configurable
- Cache Redis optimisé
- Load balancing Nginx
- Ressources Docker limitées

### Monitoring
- Métriques CPU, mémoire, disque
- Temps de réponse des services
- Débit de traitement des paquets
- Alertes de performance

## 🐛 Dépannage

### Vérifier les services
```powershell
docker-compose ps
```

### Consulter les logs
```powershell
docker-compose logs [service-name]
```

### Redémarrer un service
```powershell
docker-compose restart [service-name]
```

### Reconstruire les images
```powershell
docker-compose build --no-cache
```
