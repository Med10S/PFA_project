"""
Pipeline de preprocessing pour le traitement des données temps réel
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Union, Any
from DEV.config import FEATURE_NAMES, NUMERIC_FEATURES, CATEGORICAL_FEATURES, MODEL_FEATURES

logger = logging.getLogger(__name__)

class RealtimePreprocessor:
    """
    Préprocesseur pour les données temps réel
    Doit reproduire exactement le preprocessing de l'entraînement
    """
    def __init__(self, scaler=None, label_encoders=None):
        self.scaler = scaler
        self.label_encoders = label_encoders or {}
        self.feature_names = FEATURE_NAMES
        self.model_features = MODEL_FEATURES  # Features utilisées pour la prédiction (sans 'id')
        self.numeric_features = NUMERIC_FEATURES
        self.categorical_features = CATEGORICAL_FEATURES
        
    def parse_log_line(self, log_line: str) -> Dict[str, Any]:
        """
        Parse une ligne de log au format CSV
        Format attendu: id,dur,proto,service,state,spkts,dpkts,sbytes,...
        """
        try:
            # Supprimer les espaces et caractères de fin de ligne
            log_line = log_line.strip()
            
            # Séparer par virgules
            values = log_line.split(',')
            
            # Vérifier le nombre de valeurs
            expected_features = len(self.feature_names)
            if len(values) != expected_features:
                logger.warning(f"Nombre de features incorrect: {len(values)} vs {expected_features} attendus")
                # Compléter ou tronquer si nécessaire
                if len(values) < expected_features:
                    values.extend(['0'] * (expected_features - len(values)))
                else:
                    values = values[:expected_features]
            
            # Créer le dictionnaire
            data = {}
            for i, feature in enumerate(self.feature_names):
                data[feature] = values[i]
            
            return data
            
        except Exception as e:
            logger.error(f"Erreur parsing log: {e}")
            raise ValueError(f"Impossible de parser la ligne de log: {log_line}")
    
    def parse_json_data(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse des données JSON (venant d'Elasticsearch par exemple)
        """
        try:
            # Vérifier que toutes les features nécessaires sont présentes
            data = {}
            for feature in self.feature_names:
                if feature in json_data:
                    data[feature] = json_data[feature]
                else:
                    logger.warning(f"Feature manquante: {feature}, utilisation valeur par défaut")
                    data[feature] = 0 if feature in self.numeric_features else ""
            
            return data
            
        except Exception as e:
            logger.error(f"Erreur parsing JSON: {e}")
            raise ValueError(f"Impossible de parser les données JSON")
    
    def preprocess(self, data: Union[Dict[str, Any], pd.DataFrame, str]) -> Union[np.ndarray, pd.DataFrame]:
        """
        Méthode principale de preprocessing - accepte différents types d'entrée
        """
        try:
            if isinstance(data, str):
                # Parse d'une ligne de log CSV
                parsed_data = self.parse_log_line(data)
                return self.preprocess_single_sample(parsed_data)
            elif isinstance(data, dict):
                # Données JSON ou dictionnaire
                return self.preprocess_single_sample(data)
            elif isinstance(data, pd.DataFrame):
                # DataFrame complet
                processed_array = self.preprocess_dataframe(data)
                # Retourner un DataFrame avec les mêmes index pour compatibilité
                return pd.DataFrame(processed_array, index=data.index)
            else:
                raise ValueError(f"Type de données non supporté: {type(data)}")
                
        except Exception as e:
            logger.error(f"Erreur preprocessing: {e}")
            raise

    def preprocess_single_sample(self, data: Dict[str, Any]) -> np.ndarray:
        """
        Préprocess un échantillon unique pour la prédiction
        """
        try:
            # Créer un DataFrame avec un seul échantillon
            df = pd.DataFrame([data])
            
            # Appliquer le preprocessing
            processed_data = self.preprocess_dataframe(df)
            
            return processed_data[0]  # Retourner le premier (et seul) échantillon
            
        except Exception as e:
            logger.error(f"Erreur preprocessing échantillon: {e}")
            raise
    
    def preprocess_dataframe(self, df: pd.DataFrame) -> np.ndarray:
        """
        Préprocess un DataFrame complet
        """
        try:
            # Copier le DataFrame
            df_processed = df.copy()
              # 1. Supprimer la colonne id si présente (pas utilisée pour la prédiction)
            if 'id' in df_processed.columns:
                df_processed = df_processed.drop('id', axis=1)
            
            # Utiliser les MODEL_FEATURES (sans 'id') pour la prédiction
            features_for_prediction = self.model_features
            
            # 2. Traiter les variables catégorielles
            for col in self.categorical_features:
                if col in df_processed.columns:
                    if col in self.label_encoders:
                        le = self.label_encoders[col]
                        # Gérer les valeurs inconnues
                        df_processed[col] = df_processed[col].astype(str)
                        unique_values = set(df_processed[col].unique())
                        known_values = set(le.classes_)
                        unknown_values = unique_values - known_values
                        
                        if unknown_values:
                            logger.warning(f"Valeurs inconnues pour {col}: {unknown_values}")
                            # Remplacer par la classe la plus fréquente (première classe)
                            most_frequent = le.classes_[0]
                            for unknown_val in unknown_values:
                                df_processed.loc[df_processed[col] == unknown_val, col] = most_frequent
                        
                        df_processed[col] = le.transform(df_processed[col])
                    else:
                        logger.warning(f"Pas d'encodeur pour {col}, conversion en numérique")
                        df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce').fillna(0)
            
            # 3. Convertir toutes les colonnes en numérique
            for col in df_processed.columns:
                df_processed[col] = pd.to_numeric(df_processed[col], errors='coerce')
            
            # 4. Gérer les valeurs manquantes
            df_processed = df_processed.fillna(0)
            
            # 5. Assurer l'ordre des colonnes (important pour les modèles)
            available_features = [f for f in features_for_prediction if f in df_processed.columns]
            df_processed = df_processed[available_features]
            
            # 6. Normalisation avec le scaler d'entraînement
            if self.scaler is not None:
                try:
                    processed_array = self.scaler.transform(df_processed)
                except Exception as e:
                    logger.warning(f"Erreur normalisation: {e}, utilisation données brutes")
                    processed_array = df_processed.values
            else:
                logger.warning("Aucun scaler disponible, utilisation données brutes")
                processed_array = df_processed.values
            
            logger.info(f"Preprocessing réussi: {processed_array.shape}")
            return processed_array
            
        except Exception as e:
            logger.error(f"Erreur preprocessing DataFrame: {e}")
            raise
    
    def validate_input(self, data: Dict[str, Any]) -> bool:
        """
        Valide que les données d'entrée sont correctes
        """
        try:
            # Vérifier les features obligatoires
            required_features = ['dur', 'proto', 'service', 'state']
            for feature in required_features:
                if feature not in data:
                    logger.error(f"Feature obligatoire manquante: {feature}")
                    return False
              # Vérifier les types de données (exclure 'id' de la validation numérique)
            for feature in self.numeric_features:
                if feature in data and feature != 'id':
                    try:
                        float(data[feature])
                    except (ValueError, TypeError):
                        logger.error(f"Feature {feature} n'est pas numérique: {data[feature]}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur validation: {e}")
            return False
    def get_feature_info(self) -> Dict[str, Any]:
        """
        Retourne des informations sur les features attendues
        """
        return {
            "total_features": len(self.feature_names),
            "model_features": len(self.model_features),  # Features pour prédiction (sans 'id')
            "feature_names": self.feature_names,
            "model_feature_names": self.model_features,
            "numeric_features": self.numeric_features,
            "categorical_features": self.categorical_features,
            "scaler_available": self.scaler is not None,
            "encoders_available": list(self.label_encoders.keys())
        }
