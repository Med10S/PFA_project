# Guide d'Intégration - Système de Détection d'Intrusion Temps Réel

## Architecture du Système

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────────────┐
│   Suricata  │────│  Logstash   │────│Elasticsearch│────│  Service ML      │
│   (logs)    │    │ (parsing)   │    │ (stockage)  │    │  (FastAPI)       │
└─────────────┘    └─────────────┘    └─────────────┘    └──────────────────┘
                                                                     │
                                                          ┌──────────────────┐
                                                          │    Alertes       │
                                                          │ (Normal/Attaque) │
                                                          └──────────────────┘
```

## 1. Configuration Logstash

### Fichier de configuration Logstash (`logstash-ids.conf`)

```ruby
input {
  # Lecture des logs Suricata
  beats {
    port => 5044
  }
}

filter {
  # Parse des logs au format UNSW-NB15
  if [fields][log_type] == "network" {
    csv {
      separator => ","
      columns => [
        "id", "dur", "proto", "service", "state", "spkts", "dpkts", "sbytes", "dbytes",
        "rate", "sttl", "dttl", "sload", "dload", "sloss", "dloss", "sinpkt", "dinpkt",
        "sjit", "djit", "swin", "stcpb", "dtcpb", "dwin", "tcprtt", "synack", "ackdat",
        "smean", "dmean", "trans_depth", "response_body_len", "ct_srv_src", "ct_state_ttl",
        "ct_dst_ltm", "ct_src_dport_ltm", "ct_dst_sport_ltm", "ct_dst_src_ltm", "is_ftp_login",
        "ct_ftp_cmd", "ct_flw_http_mthd", "ct_src_ltm", "ct_srv_dst", "is_sm_ips_ports"
      ]
    }

    # Conversion des types
    mutate {
      convert => {
        "id" => "integer"
        "dur" => "float"
        "spkts" => "integer"
        "dpkts" => "integer"
        "sbytes" => "integer"
        "dbytes" => "integer"
        "rate" => "float"
        "sttl" => "integer"
        "dttl" => "integer"
        "sload" => "float"
        "dload" => "float"
        "sloss" => "integer"
        "dloss" => "integer"
        "sinpkt" => "float"
        "dinpkt" => "float"
        "sjit" => "float"
        "djit" => "float"
        "swin" => "integer"
        "stcpb" => "integer"
        "dtcpb" => "integer"
        "dwin" => "integer"
        "tcprtt" => "float"
        "synack" => "float"
        "ackdat" => "float"
        "smean" => "float"
        "dmean" => "float"
        "trans_depth" => "integer"
        "response_body_len" => "integer"
        "ct_srv_src" => "integer"
        "ct_state_ttl" => "integer"
        "ct_dst_ltm" => "integer"
        "ct_src_dport_ltm" => "integer"
        "ct_dst_sport_ltm" => "integer"
        "ct_dst_src_ltm" => "integer"
        "is_ftp_login" => "integer"
        "ct_ftp_cmd" => "integer"
        "ct_flw_http_mthd" => "integer"
        "ct_src_ltm" => "integer"
        "ct_srv_dst" => "integer"
        "is_sm_ips_ports" => "integer"
      }
    }

    # Appel du service de détection ML
    http {
      url => "http://localhost:8000/detect/single"
      http_method => "post"
      body_format => "json"
      body => {
        "id" => "%{id}"
        "dur" => "%{dur}"
        "proto" => "%{proto}"
        "service" => "%{service}"
        "state" => "%{state}"
        "spkts" => "%{spkts}"
        "dpkts" => "%{dpkts}"
        "sbytes" => "%{sbytes}"
        "dbytes" => "%{dbytes}"
        "rate" => "%{rate}"
        "sttl" => "%{sttl}"
        "dttl" => "%{dttl}"
        "sload" => "%{sload}"
        "dload" => "%{dload}"
        "sloss" => "%{sloss}"
        "dloss" => "%{dloss}"
        "sinpkt" => "%{sinpkt}"
        "dinpkt" => "%{dinpkt}"
        "sjit" => "%{sjit}"
        "djit" => "%{djit}"
        "swin" => "%{swin}"
        "stcpb" => "%{stcpb}"
        "dtcpb" => "%{dtcpb}"
        "dwin" => "%{dwin}"
        "tcprtt" => "%{tcprtt}"
        "synack" => "%{synack}"
        "ackdat" => "%{ackdat}"
        "smean" => "%{smean}"
        "dmean" => "%{dmean}"
        "trans_depth" => "%{trans_depth}"
        "response_body_len" => "%{response_body_len}"
        "ct_srv_src" => "%{ct_srv_src}"
        "ct_state_ttl" => "%{ct_state_ttl}"
        "ct_dst_ltm" => "%{ct_dst_ltm}"
        "ct_src_dport_ltm" => "%{ct_src_dport_ltm}"
        "ct_dst_sport_ltm" => "%{ct_dst_sport_ltm}"
        "ct_dst_src_ltm" => "%{ct_dst_src_ltm}"
        "is_ftp_login" => "%{is_ftp_login}"
        "ct_ftp_cmd" => "%{ct_ftp_cmd}"
        "ct_flw_http_mthd" => "%{ct_flw_http_mthd}"
        "ct_src_ltm" => "%{ct_src_ltm}"
        "ct_srv_dst" => "%{ct_srv_dst}"
        "is_sm_ips_ports" => "%{is_sm_ips_ports}"
      }
      target_body => "ml_detection"
    }

    # Enrichissement avec les résultats ML
    if [ml_detection] {
      ruby {
        code => '
          detection = event.get("ml_detection")
          if detection.is_a?(Hash)
            event.set("is_attack", detection["is_attack"])
            event.set("attack_probability", detection["attack_probability"])
            event.set("confidence", detection["confidence"])
            event.set("alert_generated", detection["alert_generated"])
          end
        '
      }
    }

    # Ajout de métadonnées temporelles
    mutate {
      add_field => { "detection_timestamp" => "%{@timestamp}" }
    }
  }
}

output {
  # Stockage dans Elasticsearch
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "network-intrusion-%{+YYYY.MM.dd}"
    document_type => "_doc"
  }

  # Alertes pour les attaques détectées
  if [is_attack] == true and [confidence] >= 0.7 {
    elasticsearch {
      hosts => ["localhost:9200"]
      index => "security-alerts-%{+YYYY.MM.dd}"
      document_type => "_doc"
    }
    
    # Log des alertes critiques
    file {
      path => "/var/log/intrusion-alerts.log"
      codec => json_lines
    }
  }

  # Debug (optionnel)
  stdout { codec => rubydebug }
}
```

## 2. Configuration Elasticsearch

### Template de mapping pour les données réseau

```json
{
  "index_patterns": ["network-intrusion-*"],
  "template": {
    "settings": {
      "number_of_shards": 2,
      "number_of_replicas": 1
    },
    "mappings": {
      "properties": {
        "@timestamp": {"type": "date"},
        "id": {"type": "long"},
        "dur": {"type": "float"},
        "proto": {"type": "keyword"},
        "service": {"type": "keyword"},
        "state": {"type": "keyword"},
        "spkts": {"type": "long"},
        "dpkts": {"type": "long"},
        "sbytes": {"type": "long"},
        "dbytes": {"type": "long"},
        "rate": {"type": "float"},
        "is_attack": {"type": "boolean"},
        "attack_probability": {"type": "float"},
        "confidence": {"type": "float"},
        "alert_generated": {"type": "boolean"},
        "detection_timestamp": {"type": "date"}
      }
    }
  }
}
```

### Template pour les alertes de sécurité

```json
{
  "index_patterns": ["security-alerts-*"],
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 1
    },
    "mappings": {
      "properties": {
        "@timestamp": {"type": "date"},
        "id": {"type": "long"},
        "is_attack": {"type": "boolean"},
        "attack_probability": {"type": "float"},
        "confidence": {"type": "float"},
        "proto": {"type": "keyword"},
        "service": {"type": "keyword"},
        "state": {"type": "keyword"},
        "src_ip": {"type": "ip"},
        "dst_ip": {"type": "ip"},
        "severity": {"type": "keyword"}
      }
    }
  }
}
```

## 3. Configuration Suricata

### Exemple de configuration pour l'export des logs

```yaml
# suricata.yaml (extrait)
outputs:
  - eve-log:
      enabled: yes
      filetype: regular
      filename: eve.json
      types:
        - alert:
            payload: yes
            payload-buffer-size: 4kb
            payload-printable: yes
        - http:
            extended: yes
        - dns
        - tls:
            extended: yes
        - files:
            force-magic: no
        - smtp
        - flow
```

## 4. Scripts de Déploiement

### Script de démarrage du service ML

```bash
#!/bin/bash
# start_detection_service.sh

echo "Démarrage du service de détection ML..."

# Activation de l'environnement virtuel
source venv/bin/activate

# Installation des dépendances
pip install -r requirements.txt

# Démarrage du service FastAPI
uvicorn realtime_detection_service:app --host 0.0.0.0 --port 8000 --reload &

echo "Service de détection démarré sur le port 8000"
echo "Documentation API disponible sur http://localhost:8000/docs"
```

### Script de test de l'intégration

```bash
#!/bin/bash
# test_integration.sh

echo "Test de l'intégration complète..."

# Test de santé du service ML
curl -X GET "http://localhost:8000/health"

# Test avec un log d'exemple
curl -X POST "http://localhost:8000/detect/single" \
  -H "Content-Type: application/json" \
  -d '{
    "id": 1,
    "dur": 0.121478,
    "proto": "tcp",
    "service": "http",
    "state": "FIN",
    "spkts": 8,
    "dpkts": 26,
    "sbytes": 1032,
    "dbytes": 15421,
    "rate": 194.836043,
    "sttl": 63,
    "dttl": 63,
    "sload": 8504.846381,
    "dload": 126910.215713,
    "sloss": 0,
    "dloss": 0,
    "sinpkt": 0.000772,
    "dinpkt": 0.001424,
    "sjit": 0.000000,
    "djit": 0.003228,
    "swin": 255,
    "stcpb": 0,
    "dtcpb": 0,
    "dwin": 8192,
    "tcprtt": 0.000774,
    "synack": 0.000000,
    "ackdat": 0.000000,
    "smean": 129,
    "dmean": 593,
    "trans_depth": 2,
    "response_body_len": 12174,
    "ct_srv_src": 1,
    "ct_state_ttl": 1,
    "ct_dst_ltm": 1,
    "ct_src_dport_ltm": 1,
    "ct_dst_sport_ltm": 1,
    "ct_dst_src_ltm": 1,
    "is_ftp_login": 0,
    "ct_ftp_cmd": 0,
    "ct_flw_http_mthd": 1,
    "ct_src_ltm": 1,
    "ct_srv_dst": 1,
    "is_sm_ips_ports": 0
  }'

echo "Test d'intégration terminé"
```

## 5. Monitoring et Métriques

### Dashboard Kibana recommandé

1. **Vue d'ensemble des détections**
   - Nombre total de logs analysés
   - Pourcentage d'attaques détectées
   - Distribution des types d'attaques

2. **Alertes en temps réel**
   - Timeline des alertes
   - Top des IP sources suspectes
   - Top des services ciblés

3. **Performance du système**
   - Temps de réponse de l'API ML
   - Throughput des logs traités
   - Métriques de confiance des modèles

## 6. Commandes de Maintenance

### Redémarrage des services
```bash
# Redémarrage de Logstash
systemctl restart logstash

# Redémarrage du service ML
pkill -f "uvicorn realtime_detection_service"
./start_detection_service.sh

# Redémarrage d'Elasticsearch
systemctl restart elasticsearch
```

### Surveillance des logs
```bash
# Logs du service ML
tail -f logs/detection_service.log

# Logs des alertes
tail -f alerts.log

# Logs Logstash
tail -f /var/log/logstash/logstash-plain.log
```

## 7. Dépannage

### Problèmes courants

1. **Service ML non accessible**
   - Vérifier que le port 8000 est ouvert
   - Vérifier les logs du service FastAPI

2. **Erreurs de parsing dans Logstash**
   - Vérifier le format des logs entrants
   - Vérifier la configuration CSV

3. **Performance dégradée**
   - Monitorer l'utilisation CPU/RAM
   - Ajuster les paramètres de batch processing

Pour plus de détails, consultez la documentation des logs et les endpoints de monitoring du service ML.
