# Configuration du système de détection temps réel
import os
from pathlib import Path

# Chemins des modèles
BASE_DIR = Path(__file__).parent
MODELS_DIR = BASE_DIR / "models"

# Modèles disponibles
MODELS_CONFIG = {
    "knn": {
        "path": MODELS_DIR / "KNN_best.pkl",
        "weight": 0.3
    },
    "mlp": {
        "path": MODELS_DIR / "mlp_best.pkl", 
        "weight": 0.35
    },
    "xgb": {
        "path": MODELS_DIR / "xgb_best.pkl",
        "weight": 0.35
    }
}

# Préprocesseurs
SCALER_PATH = MODELS_DIR / "scaler.pkl"
LABEL_ENCODERS_PATH = MODELS_DIR / "label_encoders.pkl"

# Configuration API
API_HOST = "0.0.0.0"
API_PORT = 8000
API_TITLE = "Système de Détection d'Intrusion Temps Réel"
API_VERSION = "1.0.0"

# Configuration des seuils
DETECTION_THRESHOLD = 0.5  # Seuil pour classification binaire
CONFIDENCE_THRESHOLD = 0.7  # Seuil de confiance pour alertes

# Features du dataset UNSW-NB15 (dans l'ordre exact)
FEATURE_NAMES = [
    "dur", "proto", "service", "state", "spkts", "dpkts", "sbytes", "dbytes", 
    "rate", "sttl", "dttl", "sload", "dload", "sloss", "dloss", "sinpkt", "dinpkt", 
    "sjit", "djit", "swin", "stcpb", "dtcpb", "dwin", "tcprtt", "synack", "ackdat", 
    "smean", "dmean", "trans_depth", "response_body_len", "ct_srv_src", "ct_state_ttl", 
    "ct_dst_ltm", "ct_src_dport_ltm", "ct_dst_sport_ltm", "ct_dst_src_ltm", "is_ftp_login", 
    "ct_ftp_cmd", "ct_flw_http_mthd", "ct_src_ltm", "ct_srv_dst", "is_sm_ips_ports"
]

# Features numériques (pour le preprocessing) - SANS 'id' car non utilisé pour prédiction
NUMERIC_FEATURES = [
    "dur", "spkts", "dpkts", "sbytes", "dbytes", "rate", "sttl", "dttl", 
    "sload", "dload", "sloss", "dloss", "sinpkt", "dinpkt", "sjit", "djit", 
    "swin", "stcpb", "dtcpb", "dwin", "tcprtt", "synack", "ackdat", "smean", 
    "dmean", "trans_depth", "response_body_len", "ct_srv_src", "ct_state_ttl", 
    "ct_dst_ltm", "ct_src_dport_ltm", "ct_dst_sport_ltm", "ct_dst_src_ltm", 
    "is_ftp_login", "ct_ftp_cmd", "ct_flw_http_mthd", "ct_src_ltm", "ct_srv_dst", 
    "is_sm_ips_ports"
]

# Features utilisées pour la modélisation (SANS 'id')
MODEL_FEATURES = [
    "dur", "proto", "service", "state", "spkts", "dpkts", "sbytes", "dbytes", 
    "rate", "sttl", "dttl", "sload", "dload", "sloss", "dloss", "sinpkt", "dinpkt", 
    "sjit", "djit", "swin", "stcpb", "dtcpb", "dwin", "tcprtt", "synack", "ackdat", 
    "smean", "dmean", "trans_depth", "response_body_len", "ct_srv_src", "ct_state_ttl", 
    "ct_dst_ltm", "ct_src_dport_ltm", "ct_dst_sport_ltm", "ct_dst_src_ltm", "is_ftp_login", 
    "ct_ftp_cmd", "ct_flw_http_mthd", "ct_src_ltm", "ct_srv_dst", "is_sm_ips_ports"
]

# Features catégorielles 
CATEGORICAL_FEATURES = ["proto", "service", "state"]

# Configuration des logs
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Configuration des alertes
ALERT_CONFIG = {
    "enable_logging": True,
    "enable_webhooks": False,
    "webhook_url": None,
    "log_file": "alerts.log"
}
