"""
Service de détection d'intrusion en temps réel
API FastAPI pour analyser les logs réseau et détecter les attaques
"""

import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Union
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import pandas as pd

from DEV.config import (
    API_HOST, API_PORT, API_TITLE, API_VERSION,
    DETECTION_THRESHOLD, CONFIDENCE_THRESHOLD,
    FEATURE_NAMES, LOG_LEVEL, LOG_FORMAT, ALERT_CONFIG
)
from functions.model_loader import ModelLoader
from functions.preprocessing import RealtimePreprocessor

# Configuration du logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# Modèles Pydantic pour l'API
class NetworkLog(BaseModel):
    """Modèle pour un log réseau individuel"""
    id: int
    dur: float
    proto: str
    service: str
    state: str
    spkts: int
    dpkts: int
    sbytes: int
    dbytes: int
    rate: float
    sttl: int
    dttl: int
    sload: float
    dload: float
    sloss: int
    dloss: int
    sinpkt: float
    dinpkt: float
    sjit: float
    djit: float
    swin: int
    stcpb: int
    dtcpb: int
    dwin: int
    tcprtt: float
    synack: float
    ackdat: float
    smean: float
    dmean: float
    trans_depth: int
    response_body_len: int
    ct_srv_src: int
    ct_state_ttl: int
    ct_dst_ltm: int
    ct_src_dport_ltm: int
    ct_dst_sport_ltm: int
    ct_dst_src_ltm: int
    is_ftp_login: int
    ct_ftp_cmd: int
    ct_flw_http_mthd: int
    ct_src_ltm: int
    ct_srv_dst: int
    is_sm_ips_ports: int

class LogBatch(BaseModel):
    """Modèle pour un batch de logs"""
    logs: List[NetworkLog]

class CSVLogRequest(BaseModel):
    """Modèle pour les logs en format CSV"""
    csv_data: str = Field(..., description="Données CSV avec headers ou lignes de données")

class DetectionResult(BaseModel):
    """Résultat de détection"""
    log_id: int
    is_attack: bool
    confidence: float
    attack_probability: float
    ml_predictions: Dict[str, float]  # Renommé pour éviter le conflit Pydantic
    timestamp: str
    alert_generated: bool

class BatchDetectionResult(BaseModel):
    """Résultat de détection pour un batch"""
    total_logs: int
    attacks_detected: int
    results: List[DetectionResult]
    processing_time_ms: float

class HealthStatus(BaseModel):
    """Status de santé du service"""
    status: str
    models_loaded: bool
    models_info: Dict[str, Any]
    timestamp: str

# Initialisation de l'application FastAPI
app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description="API de détection d'intrusion réseau en temps réel utilisant des modèles ML pré-entraînés"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables globales pour les modèles
model_loader = None
preprocessor = None

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    global model_loader, preprocessor
    
    try:
        logger.info("Initialisation du service de détection...")
        
        # Chargement des modèles
        model_loader = ModelLoader()
        model_loader.load_all_models()
        logger.info("Modèles chargés avec succès")
        
        # Utiliser le preprocesseur du model_loader (qui a le scaler et les encoders)
        preprocessor = model_loader.preprocessor
        logger.info("Preprocesseur initialisé depuis le model_loader")
        
        logger.info("Service de détection prêt !")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation: {e}")
        raise

def generate_alert(result: DetectionResult, background_tasks: BackgroundTasks):
    """Génère une alerte si une attaque est détectée"""
    if result.is_attack and result.confidence >= CONFIDENCE_THRESHOLD:
        alert_data = {
            "timestamp": result.timestamp,
            "log_id": result.log_id,            "attack_probability": result.attack_probability,
            "confidence": result.confidence,
            "models": result.ml_predictions
        }
        
        # Log de l'alerte
        if ALERT_CONFIG["enable_logging"]:
            background_tasks.add_task(log_alert, alert_data)
        
        # Webhook (si configuré)
        if ALERT_CONFIG["enable_webhooks"] and ALERT_CONFIG["webhook_url"]:
            background_tasks.add_task(send_webhook_alert, alert_data)
        
        return True
    return False

def log_alert(alert_data: Dict):
    """Log une alerte dans le fichier de logs"""
    try:
        alert_logger = logging.getLogger("alerts")
        handler = logging.FileHandler(ALERT_CONFIG["log_file"])
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        alert_logger.addHandler(handler)
        alert_logger.warning(f"INTRUSION DETECTEE: {json.dumps(alert_data)}")
    except Exception as e:
        logger.error(f"Erreur lors du logging de l'alerte: {e}")

def send_webhook_alert(alert_data: Dict):
    """Envoie une alerte via webhook (à implémenter selon vos besoins)"""
    try:
        # Ici vous pouvez implémenter l'envoi vers votre système d'alertes
        logger.info(f"Webhook alert envoyé: {alert_data}")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du webhook: {e}")

@app.get("/", response_model=Dict[str, str])
async def root():
    """Endpoint racine"""
    return {
        "message": "Service de Détection d'Intrusion Temps Réel",
        "version": API_VERSION,
        "status": "active"
    }

@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Vérification de l'état du service"""
    try:
        models_info = {}
        if model_loader:
            models_info = {
                "ensemble_loaded": model_loader.ensemble_classifier is not None,
                "hybrid_loaded": model_loader.hybrid_system is not None,
                "models_count": len(model_loader.models) if model_loader.models else 0
            }
        
        return HealthStatus(
            status="healthy" if model_loader and preprocessor else "unhealthy",
            models_loaded=model_loader is not None and preprocessor is not None,
            models_info=models_info,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Erreur lors du health check: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/detect/single", response_model=DetectionResult)
async def detect_single_log(log: NetworkLog, background_tasks: BackgroundTasks):
    """Analyse un log réseau individuel"""
    if not model_loader or not preprocessor:
        raise HTTPException(status_code=503, detail="Service non initialisé")
    
    try:
        start_time = datetime.now()
        
        # Conversion en DataFrame
        log_dict = log.dict()
        df = pd.DataFrame([log_dict])
        
        # Preprocessing 
        processed_data = preprocessor.preprocess(df)
        
        # Prédiction
        prediction_result = model_loader.predict(processed_data,)
          # Création du résultat
        result = DetectionResult(
            log_id=log.id,
            is_attack=prediction_result["is_attack"],
            confidence=prediction_result["confidence"],
            attack_probability=prediction_result["attack_probability"],
            ml_predictions=prediction_result["individual_predictions"],
            timestamp=start_time.isoformat(),
            alert_generated=False
        )
        
        # Génération d'alerte si nécessaire
        result.alert_generated = generate_alert(result, background_tasks)
        
        return result
        
    except Exception as e:
        logger.error(f"Erreur lors de la détection: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur de détection: {str(e)}")

@app.post("/detect/batch", response_model=BatchDetectionResult)
async def detect_batch_logs(batch: LogBatch, background_tasks: BackgroundTasks):
    """Analyse un batch de logs réseau"""
    if not model_loader or not preprocessor:
        raise HTTPException(status_code=503, detail="Service non initialisé")
    
    try:
        start_time = datetime.now()
        
        # Conversion en DataFrame
        logs_data = [log.dict() for log in batch.logs]
        df = pd.DataFrame(logs_data)
        
        # Preprocessing
        processed_data = preprocessor.preprocess(df)
        
        # Prédictions
        results = []
        attacks_detected = 0
        
        for i, row in processed_data.iterrows():
            single_prediction = model_loader.predict(pd.DataFrame([row]))
            
            result = DetectionResult(
                log_id=int(df.iloc[i]['id']),
                is_attack=single_prediction["is_attack"],
                confidence=single_prediction["confidence"],
                attack_probability=single_prediction["attack_probability"],
                ml_predictions=single_prediction["individual_predictions"],
                timestamp=start_time.isoformat(),
                alert_generated=False
            )
            
            # Génération d'alerte si nécessaire
            result.alert_generated = generate_alert(result, background_tasks)
            
            if result.is_attack:
                attacks_detected += 1
            
            results.append(result)
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return BatchDetectionResult(
            total_logs=len(batch.logs),
            attacks_detected=attacks_detected,
            results=results,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la détection batch: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur de détection batch: {str(e)}")

@app.post("/detect/csv", response_model=BatchDetectionResult)
async def detect_csv_logs(csv_request: CSVLogRequest, background_tasks: BackgroundTasks):
    """Analyse des logs au format CSV"""
    if not model_loader or not preprocessor:
        raise HTTPException(status_code=503, detail="Service non initialisé")
    
    try:
        start_time = datetime.now()
        
        # Parse du CSV
        from io import StringIO
        csv_data = StringIO(csv_request.csv_data)
        df = pd.read_csv(csv_data)
        
        # Vérification des colonnes
        if not all(col in df.columns for col in FEATURE_NAMES):
            missing_cols = [col for col in FEATURE_NAMES if col not in df.columns]
            raise HTTPException(
                status_code=400, 
                detail=f"Colonnes manquantes: {missing_cols}"
            )
          # Preprocessing
        processed_data = preprocessor.preprocess(df[FEATURE_NAMES])
        
        # Prédictions
        results = []
        attacks_detected = 0
        
        for i, row in processed_data.iterrows():
            single_prediction = model_loader.predict(pd.DataFrame([row]))
            
            result = DetectionResult(
                log_id=int(df.iloc[i]['id']),
                is_attack=single_prediction["is_attack"],
                confidence=single_prediction["confidence"],
                attack_probability=single_prediction["attack_probability"],
                ml_predictions=single_prediction["individual_predictions"],
                timestamp=start_time.isoformat(),
                alert_generated=False
            )
            
            # Génération d'alerte si nécessaire
            result.alert_generated = generate_alert(result, background_tasks)
            
            if result.is_attack:
                attacks_detected += 1
            
            results.append(result)
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return BatchDetectionResult(
            total_logs=len(df),
            attacks_detected=attacks_detected,
            results=results,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la détection CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur de détection CSV: {str(e)}")

@app.get("/models/info")
async def get_models_info():
    """Informations sur les modèles chargés"""
    if not model_loader:
        raise HTTPException(status_code=503, detail="Service non initialisé")
    
    try:
        return {
            "models_loaded": list(model_loader.models.keys()) if model_loader.models else [],
            "ensemble_available": model_loader.ensemble_classifier is not None,
            "hybrid_available": model_loader.hybrid_system is not None,
            "feature_count": len(FEATURE_NAMES),
            "detection_threshold": DETECTION_THRESHOLD,
            "confidence_threshold": CONFIDENCE_THRESHOLD
        }
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des infos modèles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "realtime_detection_service:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
        log_level=LOG_LEVEL.lower()
    )
