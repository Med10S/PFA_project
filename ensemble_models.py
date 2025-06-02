"""
Classes d'ensemble et de détection extraites du notebook aiModelsSecu.ipynb
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
import logging

logger = logging.getLogger(__name__)

class AdvancedEnsembleClassifier:
    """
    Classificateur d'ensemble avancé avec multiple stratégies de vote et stacking
    """
    
    def __init__(self, base_models=None, meta_model=None, voting_strategy='soft'):
        self.base_models = base_models or {}
        self.meta_model = meta_model or LogisticRegression(random_state=42)
        self.voting_strategy = voting_strategy
        self.is_fitted = False
        self.model_weights = None
        self.stacking_classifier = None
        
    def add_model(self, name, model):
        """Ajoute un modèle à l'ensemble"""
        self.base_models[name] = model
        logger.info(f"Modèle {name} ajouté à l'ensemble")
        
    def set_model_weights(self, weights):
        """Définit les poids des modèles"""
        self.model_weights = weights
        logger.info(f"Poids des modèles définis : {weights}")
        
    def predict(self, X, strategy='weighted_voting'):
        """Fait des prédictions avec la stratégie spécifiée caled from model_loader.py"""
        """Prédit les classes avec la stratégie spécifiée"""
        if not self.is_fitted:
            raise ValueError("L'ensemble doit être chargé avec des modèles pré-entraînés")
            
        if strategy == 'majority_voting':
            return self._predict_majority_voting(X)
        elif strategy == 'weighted_voting':
            return self._predict_weighted_voting(X)
        elif strategy == 'soft_voting':
            return self._predict_soft_voting(X)
        elif strategy == 'stacking' and self.stacking_classifier:
            return self.stacking_classifier.predict(X)
        else:
            return self._predict_weighted_voting(X)  # Par défaut
            
    def predict_proba(self, X, strategy='weighted_voting'):
        """Prédit les probabilités avec la stratégie spécifiée"""
        if not self.is_fitted:
            raise ValueError("L'ensemble doit être chargé avec des modèles pré-entraînés")
            
        if strategy == 'stacking' and self.stacking_classifier:
            return self.stacking_classifier.predict_proba(X)
        else:
            return self._predict_proba_ensemble(X)
            
    def _predict_majority_voting(self, X):
        """Vote majoritaire"""
        logger.info("🔄 Vote majoritaire")
        predictions = []
        for name, model in self.base_models.items():
            try:
                pred = model.predict(X)
                predictions.append(pred)
            except Exception as e:
                logger.warning(f"Erreur prédiction 4 {name}: {e}")
                continue
                
        if predictions:
            predictions = np.array(predictions)
            return np.apply_along_axis(lambda x: np.bincount(x).argmax(), axis=0, arr=predictions)
        else:
            return np.zeros(len(X))
            
    def _predict_weighted_voting(self, X):
        """Vote pondéré"""
        if not self.model_weights:
            return self._predict_majority_voting(X)
            
        weighted_predictions = np.zeros(len(X))
        total_weight = 0
        
        for name, model in self.base_models.items():
            if name in self.model_weights:
                try:
                    pred = model.predict(X)
                    weight = self.model_weights[name]
                    weighted_predictions += pred * weight
                    total_weight += weight
                except Exception as e:
                    logger.warning(f"Erreur prédiction pondérée {name}: {e}")
                    continue
                    
        if total_weight > 0:
            return (weighted_predictions / total_weight > 0.5).astype(int)
        else:
            return self._predict_majority_voting(X)
            
    def _predict_soft_voting(self, X):
        """Vote soft (basé sur les probabilités)"""
        probabilities = self._predict_proba_ensemble(X)
        if probabilities is not None:
            return (probabilities[:, 1] > 0.5).astype(int)
        else:
            return self._predict_majority_voting(X)
            
    def _predict_proba_ensemble(self, X):
        """Calcule les probabilités moyennes de l'ensemble"""
        all_probas = []
        weights = []
        
        for name, model in self.base_models.items():
            if hasattr(model, 'predict_proba'):
                try:
                    proba = model.predict_proba(X)
                    all_probas.append(proba)
                    weight = self.model_weights.get(name, 1.0) if self.model_weights else 1.0
                    weights.append(weight)
                except Exception as e:
                    logger.warning(f"Erreur probabilités {name}: {e}")
                    continue
                    
        if all_probas:
            # Moyenne pondérée des probabilités
            weighted_probas = np.zeros_like(all_probas[0])
            total_weight = sum(weights)
            
            for i, (proba, weight) in enumerate(zip(all_probas, weights)):
                weighted_probas += proba * (weight / total_weight)
                
            return weighted_probas
        else:
            return None

class HybridDetectionSystem:
    """
    Système hybride combinant détection par signature et détection d'anomalies
    """
    
    def __init__(self, ensemble_classifier, anomaly_detector, threshold=0.5):
        self.ensemble_classifier = ensemble_classifier
        self.anomaly_detector = anomaly_detector
        self.threshold = threshold
        self.is_fitted = True  # Pré-entraîné
        
    def predict(self, X, strategy='hybrid'):
        """Fait des prédictions avec le système hybride"""
        if not self.is_fitted:
            raise ValueError("Le système doit être chargé")
        
        if strategy == 'ensemble_only':
            return self.ensemble_classifier.predict(X)
        elif strategy == 'anomaly_only':
            anomaly_scores = self.anomaly_detector.predict(X)
            return (anomaly_scores == -1).astype(int)
        else:  # strategy == 'hybrid'
            return self._predict_hybrid(X)
    
    def _predict_hybrid(self, X):
        """Prédiction hybride"""
        ensemble_pred = self.ensemble_classifier.predict(X)
        ensemble_proba = self.ensemble_classifier.predict_proba(X)
        
        # Gérer le cas où les anomalies ne sont pas disponibles
        try:
            anomaly_scores = self.anomaly_detector.predict(X)
        except:
            logger.warning("Détecteur d'anomalies non disponible, utilisation ensemble uniquement")
            return ensemble_pred
        
        hybrid_predictions = []
        
        for i in range(len(X)):
            ensemble_confidence = np.max(ensemble_proba[i]) if ensemble_proba is not None else 0.5
            is_anomaly = anomaly_scores[i] == -1 if anomaly_scores is not None else False
            
            if ensemble_confidence > self.threshold and not is_anomaly:
                hybrid_predictions.append(ensemble_pred[i])
            elif is_anomaly:
                hybrid_predictions.append(1)  # Attaque
            else:
                hybrid_predictions.append(ensemble_pred[i])
        
        return np.array(hybrid_predictions)
    
    def get_prediction_details(self, X):
        """Retourne les détails de la prédiction pour debugging"""
        ensemble_pred = self.ensemble_classifier.predict(X)
        ensemble_proba = self.ensemble_classifier.predict_proba(X)
        
        try:
            anomaly_scores = self.anomaly_detector.predict(X)
        except:
            anomaly_scores = None
            
        hybrid_pred = self.predict(X, strategy='hybrid')
        
        return {
            'ensemble_prediction': ensemble_pred,
            'ensemble_probabilities': ensemble_proba,
            'anomaly_scores': anomaly_scores,
            'hybrid_prediction': hybrid_pred,
            'confidence': np.max(ensemble_proba, axis=1) if ensemble_proba is not None else None
        }
