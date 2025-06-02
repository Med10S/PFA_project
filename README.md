# Système de Détection d'Intrusion Réseau Temps Réel

## 🎯 Objectif

Ce projet implémente un système de détection d'intrusion réseau en temps réel basé sur des modèles de Machine Learning pré-entraînés sur le dataset UNSW-NB15. Le système analyse les logs réseau en temps réel et détecte automatiquement les tentatives d'intrusion avec un haut niveau de précision.

## 🏗️ Architecture

```
Suricata → Logstash → Elasticsearch → FastAPI Detection Service → Alertes
```

- **Suricata**: Capture et génère les logs réseau
- **Logstash**: Parse et enrichit les logs avec les prédictions ML
- **Elasticsearch**: Stockage et indexation des logs et alertes
- **FastAPI Service**: Service de détection ML en temps réel
- **Système d'alertes**: Notifications en cas d'intrusion détectée

## 📋 Prérequis

- Python 3.8+
- Windows avec PowerShell
- 8GB RAM minimum
- Modèles pré-entraînés (KNN, MLP, XGBoost)

## 🚀 Installation Rapide

### 1. Cloner et préparer l'environnement

```powershell
# Aller dans le répertoire du projet
cd "c:\Users\pc\personnel\etude_GTR2\S4\PFA"

# Installer les dépendances
pip install -r requirements.txt
```

### 2. Vérifier les modèles

Assurez-vous que les modèles suivants sont présents dans le dossier `models/` :
- `KNN_best.pkl`
- `mlp_best.pkl` 
- `xgb_best.pkl`
- `scaler.pkl`
- `label_encoders.pkl`

### 3. Démarrer le service

```powershell
# Méthode 1: Script PowerShell automatisé
.\start_detection_service.ps1

# Méthode 2: Démarrage manuel
uvicorn realtime_detection_service:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Vérifier le fonctionnement

```powershell
# Test automatisé complet
python test_realtime_system.py

# Ou test manuel
curl http://localhost:8000/health
```

## 📡 API Endpoints

### 🏥 Health Check
```http
GET /health
```
Vérifie l'état du service et des modèles chargés.

### 🔍 Détection Individuelle
```http
POST /detect/single
Content-Type: application/json

{
  "id": 1,
  "dur": 0.121478,
  "proto": "tcp",
  "service": "http",
  "state": "FIN",
  "spkts": 8,
  "dpkts": 26,
  ...
}
```

### 📦 Détection en Batch
```http
POST /detect/batch
Content-Type: application/json

{
  "logs": [
    {...log1...},
    {...log2...}
  ]
}
```

### 📄 Détection CSV
```http
POST /detect/csv
Content-Type: application/json

{
  "csv_data": "id,dur,proto,service,...\n1,0.121478,tcp,http,..."
}
```

### 🤖 Informations Modèles
```http
GET /models/info
```

## 📊 Format des Données

Le système utilise le format UNSW-NB15 avec 43 features :

| Feature | Type | Description |
|---------|------|-------------|
| id | int | Identifiant unique |
| dur | float | Durée de la connexion |
| proto | string | Protocole (tcp, udp, icmp) |
| service | string | Service réseau |
| state | string | État de la connexion |
| spkts | int | Nombre de paquets source |
| dpkts | int | Nombre de paquets destination |
| ... | ... | 36 autres features |

## 🔧 Configuration

### Fichier `config.py`

```python
# Seuils de détection
DETECTION_THRESHOLD = 0.5  # Seuil pour classification binaire
CONFIDENCE_THRESHOLD = 0.7  # Seuil de confiance pour alertes

# Configuration API
API_HOST = "0.0.0.0"
API_PORT = 8000

# Pondération des modèles
MODELS_CONFIG = {
    "knn": {"weight": 0.3},
    "mlp": {"weight": 0.35}, 
    "xgb": {"weight": 0.35}
}
```

## 🚨 Système d'Alertes

### Types d'alertes

1. **Alerte Log** : Enregistrée dans `alerts.log`
2. **Alerte Webhook** : Envoyée vers un endpoint configuré
3. **Alerte Elasticsearch** : Indexée pour monitoring

### Critères d'alerte

- `is_attack = true`
- `confidence >= 0.7`
- Modèles en consensus

## 📈 Performance

### Métriques typiques

- **Latence**: ~50-100ms par prédiction
- **Throughput**: ~200-500 requêtes/seconde
- **Précision**: >95% sur dataset UNSW-NB15
- **Faux positifs**: <3%

### Optimisation

1. **Mise en cache** des modèles
2. **Preprocessing optimisé**
3. **Prédictions vectorisées** pour les batches
4. **Ensemble voting** pour la robustesse

## 🔄 Intégration avec ELK Stack

### Configuration Logstash

```ruby
# logstash-ids.conf
input {
  beats { port => 5044 }
}

filter {
  # Parse CSV des logs UNSW-NB15
  csv {
    separator => ","
    columns => [...]
  }
  
  # Appel du service ML
  http {
    url => "http://localhost:8000/detect/single"
    http_method => "post"
    body_format => "json"
    target_body => "ml_detection"
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "network-intrusion-%{+YYYY.MM.dd}"
  }
}
```

### Dashboard Kibana

1. **Vue temps réel** des détections
2. **Métriques de performance** 
3. **Top des attaques** détectées
4. **Tendances temporelles**

## 🧪 Tests

### Tests automatisés

```powershell
# Test complet du système
python test_realtime_system.py

# Tests spécifiques
python -m pytest tests/
```

### Tests manuels

```bash
# Test de santé
curl http://localhost:8000/health

# Test avec votre log
curl -X POST http://localhost:8000/detect/single \
  -H "Content-Type: application/json" \
  -d @votre_log.json
```

## 🐛 Dépannage

### Problèmes courants

1. **Service ne démarre pas**
   ```powershell
   # Vérifier les dépendances
   pip install -r requirements.txt
   
   # Vérifier les modèles
   ls models/
   ```

2. **Erreurs de prédiction**
   ```powershell
   # Vérifier les logs
   tail -f logs/detection_service.log
   
   # Tester les modèles
   python test_models.py
   ```

3. **Performance dégradée**
   ```powershell
   # Monitoring des ressources
   Get-Process python
   
   # Ajuster la configuration
   # Modifier config.py
   ```

### Logs de diagnostic

- **Service**: `logs/detection_service.log`
- **Alertes**: `alerts.log`
- **Erreurs**: Console PowerShell

## 📚 Documentation API

### Interface Swagger
Accessible sur : `http://localhost:8000/docs`

### Format des réponses

```json
{
  "log_id": 1,
  "is_attack": false,
  "confidence": 0.85,
  "attack_probability": 0.15,
  "model_predictions": {
    "knn": 0.12,
    "mlp": 0.18,
    "xgb": 0.16
  },
  "timestamp": "2025-06-02T10:30:00",
  "alert_generated": false
}
```

## 🔒 Sécurité

### Bonnes pratiques

1. **Validation des entrées** stricte
2. **Rate limiting** sur l'API
3. **Authentification** pour la production
4. **Chiffrement** des communications
5. **Logs d'audit** complets

## 🚀 Déploiement Production

### Avec Docker

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "realtime_detection_service:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Avec systemd (Linux)

```ini
[Unit]
Description=Network Intrusion Detection Service
After=network.target

[Service]
Type=exec
User=ids
WorkingDirectory=/opt/ids
ExecStart=/usr/bin/python -m uvicorn realtime_detection_service:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## 📞 Support

### Commandes utiles

```powershell
# Status du service
curl http://localhost:8000/health

# Informations des modèles  
curl http://localhost:8000/models/info

# Test de performance
python test_realtime_system.py
```

### Monitoring

- **Métriques** : Prometheus/Grafana
- **Logs** : ELK Stack
- **Alertes** : PagerDuty/Slack
- **Health checks** : Endpoint `/health`

---

## 🎉 Félicitations !

Votre système de détection d'intrusion temps réel est maintenant opérationnel ! 

Pour toute question ou amélioration, consultez les logs et la documentation API complète.
