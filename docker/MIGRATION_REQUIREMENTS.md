# Migration vers Requirements Spécifiques par Service

## 🎯 Objectif Accompli

Transformation du système IDS distribué pour utiliser des fichiers `requirements.txt` spécifiques à chaque service Docker au lieu d'un fichier global.

## 📁 Structure Créée

```
docker/
├── services/
│   ├── ml-api/
│   │   ├── requirements.txt       
│   │   └── Dockerfile              
│   ├── alerts/
│   │   ├── requirements.txt       
│   │   └── Dockerfile              
│   ├── capture/
│   │   ├── requirements.txt       
│   │   └── Dockerfile              
│   ├── extractor/
│   │   ├── requirements.txt       
│   │   └── Dockerfile              
│   ├── monitoring/
│   │   ├── requirements.txt       
│   │   └── Dockerfile              
│   ├── backup/
│   │   ├── requirements.txt       
│   │   └── Dockerfile              
│   └── README.md                   
├── scripts/
│   ├── validate_requirements.ps1   
│   └── build_services.ps1          
└── config/
    └── requirements.txt           ⚠️  OBSOLÈTE
```

## 🔧 Modifications Apportées

### 1. Fichiers Requirements Spécifiques

#### ML-API (`ml-api/requirements.txt`)
```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
scikit-learn==1.3.2
pandas==2.1.4
xgboost==2.0.3
redis==5.0.1
# + autres dépendances ML
```

#### Alert Manager (`alerts/requirements.txt`)
```txt
flask==2.3.3
redis==5.0.1
email-validator==2.0.0
marshmallow==3.20.1
# + dépendances notifications
```

#### Capture Service (`capture/requirements.txt`)
```txt
scapy==2.5.0
redis==5.0.1
cryptography==41.0.4
psutil==5.9.5
# + dépendances réseau
```

#### Feature Extractor (`extractor/requirements.txt`)
```txt
scapy==2.5.0
nfstream==6.5.3
pandas==2.0.3
redis==5.0.1
# + dépendances extraction
```

#### Monitoring (`monitoring/requirements.txt`)
```txt
flask==2.3.3
redis==5.0.1
requests==2.31.0
psutil==5.9.5
jinja2==3.1.2
# + dépendances monitoring
```

#### Backup (`backup/requirements.txt`)
```txt
flask==2.3.3
redis==5.0.1
zipfile36==0.1.3
psutil==5.9.5
# + dépendances backup
```

### 2. Dockerfiles MODIFIÉS

**Avant :**
```dockerfile
COPY docker/config/requirements.txt .
RUN pip install -r requirements.txt && pip install [packages...]
```

**Après :**
```dockerfile
COPY docker/services/[service]/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

### 3. Scripts d'Automatisation

#### Validation (`validate_requirements.ps1`)
- Test d'installation de chaque requirements.txt
- Vérification des conflits de dépendances
- Test de build Docker pour chaque service

#### Build Optimisé (`build_services.ps1`)
- Construction individuelle ou globale
- Support du cache Docker
- Construction parallèle (optionnel)
- Tests de fonctionnement
- Rapport de tailles d'images

## 📊 Avantages Obtenus

###  Images Plus Légères
- **Avant :** Une image avec toutes les dépendances (~2-3 GB)
- **Après :** Images spécialisées (500MB - 1.5GB chacune)

###  Isolation des Dépendances
- Pas de conflits entre services
- Mise à jour indépendante
- Dépendances minimales par service

###  Déploiement Flexible
- Services déployables séparément
- Scaling horizontal facilité
- Rollback par service

###  Maintenance Simplifiée
- Dépendances clairement définies
- Debug plus facile
- Tests isolés

## 🚀 Utilisation

### Construction des Services

```powershell
# Tous les services
docker-compose build

# Service spécifique
docker-compose build ml-api

# Avec script optimisé
.\docker\scripts\build_services.ps1 -Action build -Service all

# Sans cache
.\docker\scripts\build_services.ps1 -Action build -NoCache
```

### Validation des Requirements

```powershell
# Validation complète
.\docker\scripts\validate_requirements.ps1

# Service spécifique
.\docker\scripts\validate_requirements.ps1 -Service ml-api
```

### Tests de Fonctionnement

```powershell
# Test de tous les services
.\docker\scripts\build_services.ps1 -Action test

# Vérification des tailles
.\docker\scripts\build_services.ps1 -Action size
```

## 🔍 Ports et Endpoints

| Service | Port | Health Check |
|---------|------|--------------|
| ML-API | 5000 | `/health` |
| Alerts | 9003 | `/health` |
| Capture | 9001 | (interne) |
| Extractor | 9002 | (interne) |
| Monitoring | 9000 | `/health` |
| Backup | 9004 | `/health` |

## ⚠️ Actions de Migration

### Fichiers Obsolètes
- `docker/config/requirements.txt` peut être supprimé
- Anciens builds Docker à nettoyer

### Commandes de Nettoyage
```powershell
# Suppression des anciennes images
docker image prune -f

# Nettoyage complet
.\docker\scripts\build_services.ps1 -Action clean
```

## 🎉 Résultat Final

 **6 services avec requirements spécifiques**  
 **Dockerfiles optimisés**  
 **Scripts d'automatisation**  
 **Documentation complète**  
 **Tests automatisés**  

Le système IDS distribué est maintenant modulaire avec des dépendances isolées par service, facilitant la maintenance, le déploiement et la scalabilité.

## 📞 Support

Pour toute question sur la nouvelle structure :
1. Consulter `docker/services/README.md`
2. Utiliser les scripts de validation
3. Vérifier les logs de build Docker
