"""
Chargeur de modèles pour le système de détection temps réel
"""

import joblib
import pickle
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from sklearn.ensemble import IsolationForest

from config import MODELS_CONFIG, SCALER_PATH, LABEL_ENCODERS_PATH
from ensemble_models import AdvancedEnsembleClassifier, HybridDetectionSystem
from functions.preprocessing import RealtimePreprocessor

logger = logging.getLogger(__name__)

class ModelLoader:
    """
    Classe pour charger tous les modèles et préprocesseurs
    """
    
    def __init__(self):
        self.models = {}
        self.scaler = None
        self.label_encoders = {}
        self.ensemble_classifier = None
        self.hybrid_system = None
        self.preprocessor = None
        self.is_loaded = False
        
    def load_all_models(self) -> bool:
        """
        Charge tous les modèles et préprocesseurs
        """
        try:
            logger.info("🔄 Chargement des modèles...")
            
            # 1. Charger les modèles individuels
            self._load_individual_models()
            
            # 2. Charger les préprocesseurs
            self._load_preprocessors()
            
            # 3. Créer l'ensemble classifier
            self._create_ensemble_classifier()
            
            # 4. Créer le système hybride
            self._create_hybrid_system()
            
            # 5. Initialiser le preprocessor
            self._initialize_preprocessor()
            
            self.is_loaded = True
            logger.info("✅ Tous les modèles chargés avec succès")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur chargement des modèles: {e}")
            return False
    
    def _load_individual_models(self):
        """Charge les modèles individuels"""
        logger.info("📂 Chargement des modèles individuels...")
        
        for model_name, config in MODELS_CONFIG.items():
            model_path = config["path"]
            
            if model_path.exists():
                try:
                    model = joblib.load(model_path)
                    self.models[model_name] = model
                    logger.info(f"  ✅ {model_name} chargé depuis {model_path}")
                except Exception as e:
                    logger.warning(f"  ⚠️ Erreur chargement {model_name}: {e}")
            else:
                logger.warning(f"  ⚠️ Fichier modèle introuvable: {model_path}")
        
        logger.info(f"📊 Modèles chargés: {list(self.models.keys())}")
    
    def _load_preprocessors(self):
        """Charge les préprocesseurs (scaler et encodeurs)"""
        logger.info("🔧 Chargement des préprocesseurs...")
        
        # Charger le scaler
        if SCALER_PATH.exists():
            try:
                self.scaler = joblib.load(SCALER_PATH)
                logger.info(f"  ✅ Scaler chargé depuis {SCALER_PATH}")
            except Exception as e:
                logger.warning(f"  ⚠️ Erreur chargement scaler: {e}")
        else:
            logger.warning(f"  ⚠️ Fichier scaler introuvable: {SCALER_PATH}")
        
        # Charger les label encoders
        if LABEL_ENCODERS_PATH.exists():
            try:
                self.label_encoders = joblib.load(LABEL_ENCODERS_PATH)
                logger.info(f"  ✅ Label encoders chargés depuis {LABEL_ENCODERS_PATH}")
                logger.info(f"  📋 Encodeurs disponibles: {list(self.label_encoders.keys())}")
            except Exception as e:
                logger.warning(f"  ⚠️ Erreur chargement label encoders: {e}")
        else:
            logger.warning(f"  ⚠️ Fichier label encoders introuvable: {LABEL_ENCODERS_PATH}")
    
    def _create_ensemble_classifier(self):
        """Crée le classificateur d'ensemble"""
        logger.info("🎯 Création du classificateur d'ensemble...")
        
        if not self.models:
            logger.error("Aucun modèle disponible pour l'ensemble")
            return
        
        # Créer l'ensemble
        self.ensemble_classifier = AdvancedEnsembleClassifier()
        
        # Ajouter tous les modèles chargés
        for model_name, model in self.models.items():
            self.ensemble_classifier.add_model(model_name, model)
        
        # Définir les poids des modèles (depuis la configuration)
        weights = {}
        for model_name in self.models.keys():
            if model_name in MODELS_CONFIG:
                weights[model_name] = MODELS_CONFIG[model_name]["weight"]
        
        if weights:
            self.ensemble_classifier.set_model_weights(weights)
            logger.info(f"  ⚖️ Poids définis: {weights}")
        
        # Marquer comme fitted (modèles pré-entraînés)
        self.ensemble_classifier.is_fitted = True
        
        logger.info("  ✅ Ensemble classifier créé")
    
    def _create_hybrid_system(self):
        """Crée le système hybride"""
        logger.info("🔬 Création du système hybride...")
        
        if not self.ensemble_classifier:
            logger.error("Ensemble classifier non disponible pour le système hybride")
            return
        
        # Créer un détecteur d'anomalies simple (peut être amélioré)
        anomaly_detector = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_jobs=-1
        )
        
        # Note: Dans un vrai système, ce détecteur devrait être pré-entraîné
        # Pour l'instant, il sera entraîné à la volée avec les données normales
        
        # Créer le système hybride
        self.hybrid_system = HybridDetectionSystem(
            ensemble_classifier=self.ensemble_classifier,
            anomaly_detector=anomaly_detector,
            threshold=0.6
        )
        
        logger.info("  ✅ Système hybride créé")
    
    def _initialize_preprocessor(self):
        """Initialise le préprocesseur temps réel"""
        logger.info("⚙️ Initialisation du préprocesseur...")
        
        self.preprocessor = RealtimePreprocessor(
            scaler=self.scaler,
            label_encoders=self.label_encoders
        )
        
        logger.info("  ✅ Préprocesseur initialisé")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Retourne des informations sur les modèles chargés"""
        return {
            "models_loaded": list(self.models.keys()),
            "models_count": len(self.models),
            "scaler_available": self.scaler is not None,
            "label_encoders_available": list(self.label_encoders.keys()),
            "ensemble_available": self.ensemble_classifier is not None,
            "hybrid_available": self.hybrid_system is not None,
            "preprocessor_available": self.preprocessor is not None,
            "is_ready": self.is_loaded
        }
    
    def predict(self, data, strategy: str = "ensemble") -> Dict[str, Any]:
        """
        Méthode principale de prédiction - compatible avec le format attendu par FastAPI
        """
        if not self.is_loaded:
            raise RuntimeError("Modèles non chargés")
        
        try:
            # Si c'est un DataFrame d'une seule ligne
            if hasattr(data, 'shape') and data.shape[0] == 1:
                # Convertir en array numpy
                if hasattr(data, 'values'):
                    processed_data = data.values[0]
                else:
                    processed_data = data[0]
            else:
                processed_data = data
            
            # Faire la prédiction avec l'ensemble
            if strategy == "ensemble" and self.ensemble_classifier:
                prediction = self.ensemble_classifier.predict([processed_data])[0]
                probabilities = self.ensemble_classifier.predict_proba([processed_data])[0]
                
                # Obtenir les prédictions individuelles
                individual_predictions = {}
                for model_name, model in self.models.items():
                    try:
                        pred = model.predict([processed_data])[0]
                        individual_predictions[model_name] = float(pred)
                    except Exception as e:
                        logger.warning(f"Erreur prédiction {model_name}: {e}")
                        individual_predictions[model_name] = 0.0
                
            elif strategy == "hybrid" and self.hybrid_system:
                prediction = self.hybrid_system.predict([processed_data], strategy="hybrid")[0]
                probabilities = self.ensemble_classifier.predict_proba([processed_data])[0] if self.ensemble_classifier else [0.5, 0.5]
                individual_predictions = {"hybrid": float(prediction)}
            else:
                raise ValueError(f"Stratégie inconnue ou non disponible: {strategy}")
            
            # Calculer les métriques
            attack_probability = float(probabilities[1]) if len(probabilities) > 1 else 0.5
            confidence = max(probabilities) if probabilities is not None else 0.5
            is_attack = bool(prediction == 1)
            
            return {
                "is_attack": is_attack,
                "confidence": float(confidence),
                "attack_probability": attack_probability,
                "individual_predictions": individual_predictions,
                "prediction": int(prediction)
            }
            
        except Exception as e:
            logger.error(f"Erreur prédiction: {e}")
            return {
                "is_attack": False,
                "confidence": 0.0,
                "attack_probability": 0.0,
                "individual_predictions": {},
                "prediction": 0,
                "error": str(e)
            }

    def predict_single(self, log_data: str, strategy: str = "hybrid") -> Dict[str, Any]:
        """
        Fait une prédiction sur une ligne de log
        """
        if not self.is_loaded:
            raise RuntimeError("Modèles non chargés")
        
        try:
            # 1. Parser les données
            parsed_data = self.preprocessor.parse_log_line(log_data)
            
            # 2. Valider les données
            if not self.preprocessor.validate_input(parsed_data):
                raise ValueError("Données d'entrée invalides")
            
            # 3. Préprocesser
            processed_data = self.preprocessor.preprocess_single_sample(parsed_data)
            
            # 4. Faire la prédiction
            if strategy == "ensemble":
                prediction = self.ensemble_classifier.predict([processed_data])[0]
                probabilities = self.ensemble_classifier.predict_proba([processed_data])[0]
            elif strategy == "hybrid":
                prediction = self.hybrid_system.predict([processed_data], strategy="hybrid")[0]
                probabilities = self.ensemble_classifier.predict_proba([processed_data])[0]
            else:
                raise ValueError(f"Stratégie inconnue: {strategy}")
            
            # 5. Calculer la confiance
            confidence = max(probabilities) if probabilities is not None else 0.5
            
            # 6. Déterminer le label
            label = "Attack" if prediction == 1 else "Normal"
            
            return {
                "prediction": int(prediction),
                "label": label,
                "confidence": float(confidence),
                "probabilities": {
                    "normal": float(probabilities[0]) if probabilities is not None else 0.5,
                    "attack": float(probabilities[1]) if probabilities is not None else 0.5
                },
                "strategy": strategy,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Erreur prédiction: {e}")
            return {
                "prediction": -1,
                "label": "Error",
                "confidence": 0.0,
                "error": str(e),
                "status": "error"
            }
    
    def predict_batch(self, log_data_list: list, strategy: str = "hybrid") -> list:
        """
        Fait des prédictions sur un batch de données
        """
        results = []
        for log_data in log_data_list:
            result = self.predict_single(log_data, strategy)
            results.append(result)
        return results
