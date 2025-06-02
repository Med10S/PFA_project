#!/usr/bin/env python3
"""
Script d'exécution de l'analyse de détection d'intrusion
"""

# Imports essentiels
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
import joblib
import pickle
from pathlib import Path
import os
from datetime import datetime
import time

# Machine Learning
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler, LabelEncoder, MinMaxScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score,
    roc_curve, precision_recall_curve, average_precision_score
)

# Modèles individuels
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

# Ensemble methods
from sklearn.ensemble import VotingClassifier, StackingClassifier, BaggingClassifier

warnings.filterwarnings('ignore')
plt.style.use('default')

class AdvancedEnsembleClassifier:
    """
    Classificateur d'ensemble avancé avec stacking et multiple stratégies
    """
    
    def __init__(self, base_models=None, meta_model=None, voting_strategy='stacking'):
        self.base_models = base_models or {}
        self.meta_model = meta_model or LogisticRegression(random_state=42)
        self.voting_strategy = voting_strategy
        self.fitted_models = {}
        self.stacking_classifier = None
        self.voting_classifier = None
        self.scaler = StandardScaler()
        self.is_fitted = False
        
    def fit(self, X_train, y_train, X_val=None, y_val=None):
        """Entraîne le système d'ensemble"""
        print(f"🔄 Entraînement avec stratégie: {self.voting_strategy}")
        
        # Normalisation des données
        X_train_scaled = self.scaler.fit_transform(X_train)
        if X_val is not None:
            X_val_scaled = self.scaler.transform(X_val)
        
        if self.voting_strategy == 'stacking':
            print("  📊 Configuration du stacking...")
            estimators = [(name, model) for name, model in self.base_models.items()]
            
            self.stacking_classifier = StackingClassifier(
                estimators=estimators,
                final_estimator=self.meta_model,
                cv=3,
                n_jobs=-1
            )
            
            print("  🎯 Entraînement du stacking classifier...")
            self.stacking_classifier.fit(X_train_scaled, y_train)
            
        else:  # voting
            print(f"  🗳️ Configuration du vote {self.voting_strategy}...")
            estimators = [(name, model) for name, model in self.base_models.items()]
            
            self.voting_classifier = VotingClassifier(
                estimators=estimators,
                voting='soft' if self.voting_strategy in ['soft', 'weighted'] else 'hard',
                n_jobs=-1
            )
            
            print("  🎯 Entraînement du voting classifier...")
            self.voting_classifier.fit(X_train_scaled, y_train)
        
        self.is_fitted = True
        print("✅ Ensemble classifier entraîné")
        
    def predict(self, X):
        """Fait des prédictions"""
        if not self.is_fitted:
            raise ValueError("Le modèle doit être entraîné")
        
        X_scaled = self.scaler.transform(X)
        
        if self.voting_strategy == 'stacking':
            return self.stacking_classifier.predict(X_scaled)
        else:
            return self.voting_classifier.predict(X_scaled)
    
    def predict_proba(self, X):
        """Retourne les probabilités de prédiction"""
        if not self.is_fitted:
            raise ValueError("Le modèle doit être entraîné")
        
        X_scaled = self.scaler.transform(X)
        
        if self.voting_strategy == 'stacking':
            return self.stacking_classifier.predict_proba(X_scaled)
        else:
            return self.voting_classifier.predict_proba(X_scaled)

class HybridDetectionSystem:
    """
    Système hybride combinant détection par signature et détection d'anomalies
    """
    
    def __init__(self, ensemble_classifier, anomaly_detector, threshold=0.5):
        self.ensemble_classifier = ensemble_classifier
        self.anomaly_detector = anomaly_detector
        self.threshold = threshold
        self.is_fitted = False
        
    def fit(self, X_train, y_train, X_val=None, y_val=None):
        """Entraîne le système hybride"""
        print("🔄 Entraînement du système hybride...")
        
        # Entraînement du classificateur d'ensemble
        print("  📈 Entraînement du classificateur d'ensemble...")
        self.ensemble_classifier.fit(X_train, y_train, X_val, y_val)
        
        # Entraînement du détecteur d'anomalies
        print("  🔍 Entraînement du détecteur d'anomalies...")
        normal_data = X_train[y_train == 0] if np.any(y_train == 0) else X_train
        
        if len(normal_data) > 0:
            scaler = StandardScaler()
            normal_data_scaled = scaler.fit_transform(normal_data)
            self.anomaly_detector.fit(normal_data_scaled)
            print(f"    ✅ Détecteur d'anomalies entraîné sur {len(normal_data)} échantillons")
        else:
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            self.anomaly_detector.fit(X_train_scaled)
            print(f"    ⚠️ Détecteur d'anomalies entraîné sur {len(X_train)} échantillons")
        
        self.anomaly_scaler = scaler
        self.is_fitted = True
        print("✅ Système hybride entraîné")
        
    def predict(self, X, strategy='hybrid'):
        """Fait des prédictions avec le système hybride"""
        if not self.is_fitted:
            raise ValueError("Le système doit être entraîné")
        
        if strategy == 'ensemble_only':
            return self.ensemble_classifier.predict(X)
        elif strategy == 'anomaly_only':
            X_scaled = self.anomaly_scaler.transform(X)
            anomaly_scores = self.anomaly_detector.predict(X_scaled)
            return (anomaly_scores == -1).astype(int)
        else:  # strategy == 'hybrid'
            return self._predict_hybrid(X)
    
    def _predict_hybrid(self, X):
        """Prédiction hybride"""
        ensemble_pred = self.ensemble_classifier.predict(X)
        try:
            ensemble_proba = self.ensemble_classifier.predict_proba(X)
        except:
            ensemble_proba = None
        
        X_scaled = self.anomaly_scaler.transform(X)
        anomaly_scores = self.anomaly_detector.predict(X_scaled)
        
        hybrid_predictions = []
        
        for i in range(len(X)):
            ensemble_confidence = np.max(ensemble_proba[i]) if ensemble_proba is not None else 0.5
            is_anomaly = anomaly_scores[i] == -1
            
            if is_anomaly and ensemble_confidence < self.threshold:
                hybrid_predictions.append(1)  # Attack détectée
            elif ensemble_pred[i] == 1:
                hybrid_predictions.append(1)  # Ensemble prédit une attaque
            else:
                hybrid_predictions.append(0)  # Normal
                
        return np.array(hybrid_predictions)

def load_unsw_data():
    """Charge les données UNSW-NB15"""
    print("📂 Chargement des données UNSW-NB15...")
    
    # Tentative de chargement du fichier
    data_path = "UNSW_NB15_training-set.csv"
    
    if not os.path.exists(data_path):
        print(f"❌ Fichier {data_path} introuvable")
        return None
    
    try:
        data = pd.read_csv(data_path)
        print(f"✅ Données chargées: {data.shape}")
        print(f"📊 Colonnes: {list(data.columns)}")
        return data
    except Exception as e:
        print(f"❌ Erreur lors du chargement: {e}")
        return None

def preprocess_data(data):
    """Préprocess les données UNSW-NB15"""
    if data is None:
        return None
    
    print("🔄 Préprocessing des données...")
    
    # Copie des données
    df = data.copy()
    
    # Gestion des valeurs manquantes
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    categorical_cols = df.select_dtypes(include=['object']).columns
    
    print(f"  📊 Colonnes numériques: {len(numeric_cols)}")
    print(f"  📊 Colonnes catégorielles: {len(categorical_cols)}")
    
    # Remplacement des valeurs manquantes
    for col in numeric_cols:
        if df[col].isnull().sum() > 0:
            df[col].fillna(df[col].median(), inplace=True)
    
    for col in categorical_cols:
        if df[col].isnull().sum() > 0:
            df[col].fillna(df[col].mode()[0], inplace=True)
    
    # Encodage des variables catégorielles
    label_encoders = {}
    for col in categorical_cols:
        if col not in ['label', 'attack_cat']:  # Éviter d'encoder la variable cible
            le = LabelEncoder()
            try:
                df[col] = le.fit_transform(df[col].astype(str))
                label_encoders[col] = le
            except Exception as e:
                print(f"⚠️ Erreur encodage {col}: {e}")
    
    # Préparation de la variable cible
    if 'label' in df.columns:
        # Conversion de la variable cible en binaire (Normal: 0, Attack: 1)
        y = (df['label'] != 0).astype(int)
        print(f"  🎯 Répartition des classes: Normal={sum(y==0)}, Attack={sum(y==1)}")
    else:
        print("⚠️ Colonne 'label' non trouvée")
        return None
    
    # Sélection des features
    feature_cols = [col for col in df.columns if col not in ['label', 'attack_cat']]
    X = df[feature_cols].select_dtypes(include=[np.number])
    
    print(f"✅ Préprocessing terminé: {X.shape[1]} features, {len(y)} échantillons")
    
    return {
        'X': X,
        'y': y,
        'feature_names': X.columns.tolist(),
        'label_encoders': label_encoders
    }

def split_and_scale_data(X, y, test_size=0.3, val_size=0.2, random_state=42):
    """Divise et normalise les données"""
    print("🔄 Division et normalisation des données...")
    
    # Division train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    
    # Division train/validation
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, test_size=val_size, random_state=random_state, stratify=y_train
    )
    
    print(f"  📊 Train: {X_train.shape}")
    print(f"  📊 Validation: {X_val.shape}")
    print(f"  📊 Test: {X_test.shape}")
    
    return {
        'X_train': X_train, 'X_val': X_val, 'X_test': X_test,
        'y_train': y_train, 'y_val': y_val, 'y_test': y_test
    }

def create_base_models():
    """Crée les modèles de base"""
    print("🔄 Création des modèles de base...")
    
    models = {
        'knn': KNeighborsClassifier(n_neighbors=5, n_jobs=-1),
        'mlp': MLPClassifier(hidden_layer_sizes=(100, 50), max_iter=500, random_state=42),
        'xgb': XGBClassifier(random_state=42, eval_metric='logloss'),
        'rf': RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1),
        'svm': SVC(probability=True, random_state=42),
        'dt': DecisionTreeClassifier(random_state=42),
        'lr': LogisticRegression(random_state=42, max_iter=1000)
    }
    
    print(f"✅ {len(models)} modèles créés")
    return models

def evaluate_model(model, X_test, y_test, model_name="Model"):
    """Évalue un modèle"""
    try:
        predictions = model.predict(X_test)
        
        metrics = {
            'accuracy': accuracy_score(y_test, predictions),
            'precision': precision_score(y_test, predictions, average='weighted', zero_division=0),
            'recall': recall_score(y_test, predictions, average='weighted', zero_division=0),
            'f1_score': f1_score(y_test, predictions, average='weighted', zero_division=0)
        }
        
        try:
            probas = model.predict_proba(X_test)
            metrics['auc'] = roc_auc_score(y_test, probas[:, 1])
        except:
            metrics['auc'] = 0.0
        
        print(f"📊 {model_name}:")
        print(f"  Accuracy: {metrics['accuracy']:.4f}")
        print(f"  Precision: {metrics['precision']:.4f}")
        print(f"  Recall: {metrics['recall']:.4f}")
        print(f"  F1-Score: {metrics['f1_score']:.4f}")
        print(f"  AUC: {metrics['auc']:.4f}")
        
        return metrics
    except Exception as e:
        print(f"❌ Erreur évaluation {model_name}: {e}")
        return None

def run_comprehensive_analysis():
    """Exécute l'analyse complète"""
    print("🚀 Début de l'analyse complète de détection d'intrusion")
    print("=" * 60)
    
    # 1. Chargement des données
    data = load_unsw_data()
    if data is None:
        return None
    
    # 2. Préprocessing
    processed_data = preprocess_data(data)
    if processed_data is None:
        return None
    
    X, y = processed_data['X'], processed_data['y']
    
    # 3. Division des données
    data_splits = split_and_scale_data(X, y)
    X_train, X_val, X_test = data_splits['X_train'], data_splits['X_val'], data_splits['X_test']
    y_train, y_val, y_test = data_splits['y_train'], data_splits['y_val'], data_splits['y_test']
    
    # 4. Création des modèles
    base_models = create_base_models()
    
    # 5. Test des stratégies d'ensemble
    strategies = ['stacking', 'hard', 'soft']
    results = {}
    
    for strategy in strategies:
        print(f"\n🔄 Test de la stratégie: {strategy}")
        print("-" * 30)
        
        try:
            # Création de l'ensemble
            ensemble = AdvancedEnsembleClassifier(
                base_models=base_models,
                voting_strategy=strategy
            )
            
            # Entraînement
            ensemble.fit(X_train, y_train, X_val, y_val)
            
            # Évaluation
            metrics = evaluate_model(ensemble, X_test, y_test, f"Ensemble {strategy}")
            if metrics:
                results[f"ensemble_{strategy}"] = metrics
            
        except Exception as e:
            print(f"❌ Erreur avec stratégie {strategy}: {e}")
    
    # 6. Test du système hybride
    print(f"\n🔄 Test du système hybride")
    print("-" * 30)
    
    try:
        # Meilleur ensemble
        best_ensemble = AdvancedEnsembleClassifier(
            base_models=base_models,
            voting_strategy='stacking'
        )
        
        # Détecteur d'anomalies
        anomaly_detector = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_jobs=-1
        )
        
        # Système hybride
        hybrid_system = HybridDetectionSystem(
            ensemble_classifier=best_ensemble,
            anomaly_detector=anomaly_detector,
            threshold=0.7
        )
        
        # Entraînement
        hybrid_system.fit(X_train, y_train, X_val, y_val)
        
        # Test des différentes stratégies
        hybrid_strategies = ['ensemble_only', 'anomaly_only', 'hybrid']
        
        for strategy in hybrid_strategies:
            try:
                predictions = hybrid_system.predict(X_test, strategy=strategy)
                
                metrics = {
                    'accuracy': accuracy_score(y_test, predictions),
                    'precision': precision_score(y_test, predictions, average='weighted', zero_division=0),
                    'recall': recall_score(y_test, predictions, average='weighted', zero_division=0),
                    'f1_score': f1_score(y_test, predictions, average='weighted', zero_division=0)
                }
                
                results[f"hybrid_{strategy}"] = metrics
                
                print(f"📊 Hybride {strategy}:")
                print(f"  Accuracy: {metrics['accuracy']:.4f}")
                print(f"  Precision: {metrics['precision']:.4f}")
                print(f"  Recall: {metrics['recall']:.4f}")
                print(f"  F1-Score: {metrics['f1_score']:.4f}")
                
            except Exception as e:
                print(f"❌ Erreur stratégie hybride {strategy}: {e}")
    
    except Exception as e:
        print(f"❌ Erreur système hybride: {e}")
    
    # 7. Résumé des résultats
    print(f"\n🏆 RÉSUMÉ DES RÉSULTATS")
    print("=" * 50)
    
    if results:
        # Classement par F1-score
        sorted_results = sorted(results.items(), key=lambda x: x[1]['f1_score'], reverse=True)
        
        print("🥇 Classement par F1-Score:")
        for i, (name, metrics) in enumerate(sorted_results, 1):
            print(f"  {i}. {name}: F1={metrics['f1_score']:.4f}, Acc={metrics['accuracy']:.4f}")
        
        # Meilleur modèle
        best_model_name, best_metrics = sorted_results[0]
        print(f"\n🏆 MEILLEUR MODÈLE: {best_model_name}")
        print(f"  🎯 F1-Score: {best_metrics['f1_score']:.4f}")
        print(f"  🎯 Accuracy: {best_metrics['accuracy']:.4f}")
        print(f"  🎯 Precision: {best_metrics['precision']:.4f}")
        print(f"  🎯 Recall: {best_metrics['recall']:.4f}")
    
    # 8. Sauvegarde des résultats
    try:
        os.makedirs('results', exist_ok=True)
        
        # Sauvegarde des métriques
        results_df = pd.DataFrame(results).T
        results_df.to_csv('results/ensemble_analysis_results.csv')
        print(f"\n💾 Résultats sauvegardés dans 'results/ensemble_analysis_results.csv'")
        
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde: {e}")
    
    print(f"\n✅ Analyse terminée!")
    return results

if __name__ == "__main__":
    # Exécution de l'analyse
    results = run_comprehensive_analysis()
    
    if results:
        print(f"\n🎉 Analyse réussie avec {len(results)} configurations testées")
    else:
        print(f"\n❌ Échec de l'analyse")
