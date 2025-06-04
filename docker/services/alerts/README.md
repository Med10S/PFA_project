# Service de Gestion d'Alertes IDS

## Vue d'ensemble

Le service de gestion d'alertes (`alert_manager_service.py`) est un composant central du système IDS distribué. Il traite, classe, enrichit et notifie les alertes de sécurité en temps réel.

## Architecture

Le service est composé de trois classes principales :

### 1. AlertProcessor
Processeur principal pour le traitement et l'enrichissement des alertes.

### 2. NotificationManager
Gestionnaire des notifications multi-canaux (email, SMS, dashboard).

### 3. AlertManagerService
Service principal qui coordonne tous les composants et expose l'API REST.

## Fonctionnalités

### Traitement des Alertes
- **Validation** : Vérification de la structure des données d'alerte
- **Enrichissement** : Ajout d'informations contextuelles
- **Classification** : Attribution automatique de scores de sévérité
- **Déduplication** : Détection des alertes répétées

### Types d'Alertes Supportés
- `intrusion` : Tentative d'intrusion détectée
- `anomaly` : Comportement anormal détecté
- `system` : Problème système
- `network` : Anomalie réseau
- `malware` : Malware potentiel détecté

### Niveaux de Sévérité
1. **Low** (1) : Alertes de faible priorité
2. **Medium** (2) : Alertes de priorité normale
3. **High** (3) : Alertes de haute priorité
4. **Critical** (4) : Alertes critiques nécessitant une action immédiate

### Calcul du Score de Sévérité
Le score est calculé en fonction de :
- Niveau de sévérité de base
- Type d'alerte (+1 pour les intrusions)
- Niveau de confiance (+1 si > 90%)
- Répétition d'alertes (+1 si répétée)
- Score maximum : 5

## API REST

### Endpoints Disponibles

#### GET /health
Vérification de l'état du service
```json
{
  "status": "healthy",
  "service": "alert-manager",
  "stats": {
    "total_alerts": 150,
    "critical_alerts": 5,
    "high_alerts": 12,
    "medium_alerts": 100,
    "low_alerts": 33,
    "false_positives": 8,
    "acknowledged": 45
  }
}
```

#### GET /alerts
Récupération de la liste des alertes avec pagination et filtrage
```
Paramètres :
- page (int) : Numéro de page (défaut: 1)
- per_page (int) : Nombre d'alertes par page (défaut: 50)
- severity (string) : Filtrer par sévérité (low, medium, high, critical)
- status (string) : Filtrer par statut (new, acknowledged, false_positive)
```

#### POST /alerts/{alert_id}/acknowledge
Marquer une alerte comme acquittée
```json
{
  "user": "admin@company.com"
}
```

#### POST /alerts/{alert_id}/false-positive
Marquer une alerte comme faux positif
```json
{
  "user": "analyst@company.com"
}
```

#### GET /stats
Récupération des statistiques globales

## Stockage et Persistance

### Redis
Le service utilise Redis pour :
- **Écoute d'alertes** : Souscription aux canaux `alerts:ml`, `alerts:monitoring`, `alerts:network`
- **Stockage des alertes** : Sauvegarde structurée avec indexation
- **Statistiques** : Cache des métriques en temps réel
- **Configuration** : Paramètres de service

### Structure des Données Redis
```
alert:{alert_id}           # Hash contenant tous les détails de l'alerte
alerts:all                 # Liste des IDs d'alertes (10 000 max)
alerts:severity:{level}    # Listes par niveau de sévérité (1 000 max)
stats:alerts:{metric}      # Statistiques individuelles
```

## Notifications

### Règles de Notification
- **Critical** : Email + SMS
- **High** : Email uniquement
- **Medium** : Dashboard uniquement
- **Low** : Dashboard uniquement

### Configuration Email
```python
email_config = {
    'smtp_server': 'localhost',
    'smtp_port': 587,
    'username': '',
    'password': '',
    'from_email': 'ids-alerts@company.com'
}
```

## Enrichissement des Alertes

### Informations Ajoutées
- **ID unique** : Timestamp + compteur
- **Métadonnées temporelles** : processed_at, timestamp
- **Statut** : new, acknowledged, false_positive
- **Score de sévérité** : Calcul algorithmique
- **Informations IP** : Géolocalisation et classification (privée/publique)
- **Contexte** : Description du type d'alerte

### Exemple d'Alerte Enrichie
```json
{
  "id": "alert_1733234567_42",
  "type": "intrusion",
  "type_description": "Tentative d'intrusion détectée",
  "message": "Tentative de connexion SSH suspecte",
  "severity": "high",
  "severity_score": 4,
  "confidence": 0.95,
  "timestamp": "2024-12-03T15:30:00Z",
  "processed_at": "2024-12-03T15:30:01Z",
  "status": "new",
  "acknowledged": false,
  "false_positive": false,
  "source_ip": "192.168.1.100",
  "source_info": {
    "ip": "192.168.1.100",
    "is_private": true,
    "country": "Unknown",
    "organization": "Unknown"
  }
}
```

## Configuration et Déploiement

### Variables d'Environnement
- `REDIS_HOST` : Adresse du serveur Redis (défaut: redis)
- `REDIS_PORT` : Port Redis (défaut: 6379)
- `SMTP_SERVER` : Serveur SMTP pour les emails
- `ALERT_RETENTION` : Durée de rétention des alertes

### Docker
Le service est containerisé et s'exécute sur le port 9003.

### Logging
- **Fichier** : `/app/logs/alerts.log`
- **Console** : Sortie standard
- **Niveau** : INFO par défaut

## Métriques et Monitoring

### Statistiques Trackées
- Total des alertes traitées
- Répartition par niveau de sévérité
- Nombre d'alertes acquittées
- Nombre de faux positifs identifiés

### Performance
- **Mémoire** : Conservation des 1 000 dernières alertes
- **Redis** : Limitation à 10 000 alertes stockées
- **Déduplication** : Fenêtre de 5 minutes pour détecter les répétitions

## Utilisation

### Démarrage du Service
```python
service = AlertManagerService()
service.start()
```

### Envoi d'une Alerte
Publication sur un canal Redis :
```python
import redis
import json

r = redis.Redis(host='redis', port=6379)
alert = {
    "type": "intrusion",
    "message": "Tentative de connexion suspecte",
    "severity": "high",
    "timestamp": "2024-12-03T15:30:00Z",
    "source_ip": "10.0.0.100",
    "confidence": 0.92
}
r.publish('alerts:ml', json.dumps(alert))
```

## Sécurité

### Considérations
- Validation stricte des données d'entrée
- Authentification requise pour les actions administratives
- Chiffrement des communications (à implémenter)
- Audit des actions utilisateur

### Limitations Actuelles
- Pas d'authentification sur l'API REST
- Configuration email en dur
- Pas de chiffrement des données stockées

## Maintenance

### Nettoyage Automatique
- Limitation automatique des alertes en mémoire
- Rotation des logs (à configurer)
- Purge automatique des anciennes alertes dans Redis

### Monitoring du Service
- Endpoint `/health` pour les checks de santé
- Métriques exposées via `/stats`
- Logs structurés pour le debugging

## Extensions Possibles

### Améliorations Futures
- Intégration avec des services de géolocalisation IP
- Machine learning pour la classification automatique
- Interface web pour la gestion des alertes
- Intégration avec des systèmes SIEM externes
- Authentification et autorisation robustes
- Chiffrement des données sensibles

### Intégrations
- **Elasticsearch** : Pour l'indexation et la recherche avancée
- **Grafana** : Pour la visualisation des métriques
- **Slack/Teams** : Pour les notifications collaboratives
- **JIRA** : Pour la création automatique de tickets

## Dépannage

### Problèmes Courants
1. **Service ne démarre pas** : Vérifier la connexion Redis
2. **Alertes non traitées** : Vérifier les souscriptions aux canaux
3. **Notifications non envoyées** : Vérifier la configuration SMTP
4. **Performance dégradée** : Vérifier l'utilisation mémoire et les logs

### Logs Utiles
```bash
# Logs du service
tail -f /app/logs/alerts.log

# Logs de conteneur Docker
docker logs alert-manager

# Status Redis
redis-cli info
```

## Contact et Support

Pour toute question ou problème concernant le service de gestion d'alertes, consultez :
- Documentation technique complète
- Logs de débogage
- Métriques de performance via l'API `/stats`
