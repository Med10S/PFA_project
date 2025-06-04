# Structure des Requirements par Service

Ce projet utilise maintenant des fichiers `requirements.txt` spécifiques pour chaque service Docker au lieu d'un fichier global. Cela permet une meilleure isolation des dépendances et des images Docker plus légères.

## Structure des Services

### 📡 ML-API Service (`docker/services/ml-api/`)
**Port:** 5000  
**Fonction:** Service principal de détection d'intrusion ML  
**Requirements:** FastAPI, scikit-learn, pandas, XGBoost, Redis

### 🚨 Alert Manager (`docker/services/alerts/`)
**Port:** 9003  
**Fonction:** Gestion et notification des alertes  
**Requirements:** Flask, Redis, email-validator, marshmallow

### 🔍 Packet Capture (`docker/services/capture/`)
**Port:** 9001  
**Fonction:** Capture sécurisée des paquets réseau  
**Requirements:** Scapy, Redis, cryptography, psutil

### ⚙️ Feature Extractor (`docker/services/extractor/`)
**Port:** 9002  
**Fonction:** Extraction de features réseau  
**Requirements:** Scapy, nfstream, pandas, Redis, cryptography

### 📊 Monitoring (`docker/services/monitoring/`)
**Port:** 9000  
**Fonction:** Surveillance système et métriques  
**Requirements:** Flask, Redis, requests, psutil, jinja2

### 💾 Backup Service (`docker/services/backup/`)
**Port:** 9004  
**Fonction:** Sauvegarde et archivage  
**Requirements:** Flask, Redis, zipfile36, psutil

## Avantages de cette Approche

### ✅ Images Docker Plus Légères
- Chaque service n'installe que ses dépendances nécessaires
- Réduction de la taille des images
- Temps de build plus rapides

### ✅ Isolation des Dépendances
- Évite les conflits entre versions
- Facilite la maintenance
- Permet des mises à jour indépendantes

### ✅ Sécurité Améliorée
- Surface d'attaque réduite
- Moins de packages inutiles
- Isolation des vulnérabilités

### ✅ Déploiement Flexible
- Services déployables indépendamment
- Scaling horizontal facilité
- Configuration par service

## Construction des Images

### Construction Individuelle
```powershell
# ML API
docker build -f docker/services/ml-api/Dockerfile -t ids-ml-api .

# Alert Manager
docker build -f docker/services/alerts/Dockerfile -t ids-alerts .

# Packet Capture
docker build -f docker/services/capture/Dockerfile -t ids-capture .

# Feature Extractor
docker build -f docker/services/extractor/Dockerfile -t ids-extractor .

# Monitoring
docker build -f docker/services/monitoring/Dockerfile -t ids-monitoring .

# Backup
docker build -f docker/services/backup/Dockerfile -t ids-backup .
```

### Construction via Docker Compose
```powershell
# Construction de tous les services
docker-compose build

# Construction d'un service spécifique
docker-compose build ml-api
docker-compose build alert-manager
```

## Gestion des Dépendances

### Ajout de Nouvelles Dépendances
1. Modifier le fichier `requirements.txt` du service concerné
2. Reconstruire l'image Docker
3. Tester en local
4. Déployer

### Mise à Jour des Versions
1. Mettre à jour le fichier `requirements.txt` approprié
2. Tester la compatibilité
3. Reconstruire et redéployer

## Migration depuis l'Ancien Système

### Ancien (Fichier Global)
```dockerfile
COPY docker/config/requirements.txt .
RUN pip install -r requirements.txt && pip install [packages...]
```

### Nouveau (Spécifique par Service)
```dockerfile
COPY docker/services/[service]/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

## Commandes Utiles

### Vérification des Dépendances
```powershell
# Lister les packages installés dans un conteneur
docker exec -it ids-ml-api pip list

# Vérifier les conflits
docker exec -it ids-ml-api pip check

# Analyser la taille des images
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
```

### Debug des Requirements
```powershell
# Test d'installation locale
pip install -r docker/services/ml-api/requirements.txt

# Vérification de compatibilité
pip-compile --dry-run docker/services/ml-api/requirements.txt
```

## Structure des Ports

| Service | Port | URL Health Check |
|---------|------|------------------|
| ML-API | 5000 | http://localhost:5000/health |
| Alerts | 9003 | http://localhost:9003/health |
| Capture | 9001 | (monitoring interne) |
| Extractor | 9002 | (monitoring interne) |
| Monitoring | 9000 | http://localhost:9000/health |
| Backup | 9004 | http://localhost:9004/health |
| Redis | 6379 | redis-cli ping |

## Sécurité des Requirements

### Bonnes Pratiques
- ✅ Versions spécifiques (ex: `flask==2.3.3`)
- ✅ Packages officiels uniquement
- ✅ Vérification régulière des vulnérabilités
- ✅ Mise à jour contrôlée

### Commandes de Sécurité
```powershell
# Audit de sécurité
pip audit

# Vérification des vulnérabilités
docker run --rm -v ${PWD}:/code pyupio/safety check -r /code/docker/services/ml-api/requirements.txt
```

---

**Note:** Cette structure modulaire facilite la maintenance et permet un déploiement plus efficace du système IDS distribué.
