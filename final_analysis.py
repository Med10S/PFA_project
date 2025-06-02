#!/usr/bin/env python3
"""
Analyse complète du système de détection d'intrusion avec modèles existants
"""

import pandas as pd
import numpy as np
import joblib
import pickle
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Imports ML
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score
)
from sklearn.ensemble import VotingClassifier, RandomForestClassifier, IsolationForest
from sklearn.linear_model import LogisticRegression

def load_data_and_preprocess():
    """Charge et préprocess les données UNSW-NB15"""
    print("📂 Chargement et preprocessing des données UNSW-NB15...")
    
    try:
        # Chargement des données
        data = pd.read_csv("UNSW_NB15_training-set.csv")
        print(f"✅ Données chargées: {data.shape}")
        
        # Préparation des features numériques
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        print(f"📊 Colonnes numériques: {len(numeric_cols)}")
        
        # Préparation X et y
        if 'label' in data.columns:
            # Features (toutes les colonnes numériques sauf label)
            feature_cols = [col for col in numeric_cols if col != 'label']
            X = data[feature_cols].copy()
            
            # Target binaire (0: Normal, 1: Attack)
            y = (data['label'] != 0).astype(int)
            
            # Gestion des valeurs manquantes
            X = X.fillna(X.median())
            
            print(f"✅ Features: {X.shape}")
            print(f"✅ Target: {y.shape}")
            print(f"📊 Répartition: Normal={sum(y==0)}, Attack={sum(y==1)}")
            
            return X, y, feature_cols
        else:
            print("❌ Colonne 'label' non trouvée")
            return None, None, None
            
    except Exception as e:
        print(f"❌ Erreur chargement: {e}")
        return None, None, None

def load_existing_models():
    """Charge les modèles existants"""
    print("🔄 Chargement des modèles existants...")
    
    models = {}
    model_files = {
        'knn': 'models/KNN_best.pkl',
        'mlp': 'models/mlp_best.pkl',
        'xgb': 'models/xgb_best.pkl',
        'scaler': 'models/scaler.pkl'
    }
    
    for name, path in model_files.items():
        if os.path.exists(path):
            try:
                model = joblib.load(path)
                models[name] = model
                print(f"✅ {name} chargé: {type(model).__name__}")
            except Exception as e:
                print(f"❌ Erreur {name}: {e}")
        else:
            print(f"⚠️ {path} non trouvé")
    
    return models

def create_ensemble_system(existing_models, X_train, y_train):
    """Crée un système d'ensemble avec les modèles existants"""
    print("🔄 Création du système d'ensemble...")
    
    # Préparation des estimateurs pour l'ensemble
    estimators = []
    
    # Ajout des modèles existants
    for name, model in existing_models.items():
        if name != 'scaler' and hasattr(model, 'predict'):
            estimators.append((name, model))
            print(f"  ✅ {name} ajouté à l'ensemble")
    
    # Ajout d'un Random Forest comme modèle supplémentaire
    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    estimators.append(('rf_new', rf))
    print("  ✅ Random Forest ajouté")
    
    if len(estimators) < 2:
        print("❌ Pas assez de modèles pour créer un ensemble")
        return None
    
    # Création du voting classifier
    ensemble = VotingClassifier(
        estimators=estimators,
        voting='soft',  # Vote pondéré par probabilités
        n_jobs=-1
    )
    
    print(f"🎯 Entraînement de l'ensemble avec {len(estimators)} modèles...")
    
    try:
        ensemble.fit(X_train, y_train)
        print("✅ Ensemble entraîné avec succès")
        return ensemble
    except Exception as e:
        print(f"❌ Erreur entraînement ensemble: {e}")
        return None

def create_hybrid_system(ensemble_model, X_train, y_train):
    """Crée un système hybride avec détection d'anomalies"""
    print("🔄 Création du système hybride...")
    
    # Détecteur d'anomalies
    anomaly_detector = IsolationForest(
        contamination=0.1,  # 10% d'anomalies attendues
        random_state=42,
        n_jobs=-1
    )
    
    # Entraînement sur les données normales
    normal_indices = (y_train == 0)
    if np.sum(normal_indices) > 0:
        X_normal = X_train[normal_indices]
        anomaly_detector.fit(X_normal)
        print(f"✅ Détecteur d'anomalies entraîné sur {len(X_normal)} échantillons normaux")
    else:
        anomaly_detector.fit(X_train)
        print(f"⚠️ Détecteur d'anomalies entraîné sur tous les échantillons")
    
    return {
        'ensemble': ensemble_model,
        'anomaly_detector': anomaly_detector
    }

def predict_hybrid(hybrid_system, X, strategy='hybrid'):
    """Fait des prédictions avec le système hybride"""
    ensemble = hybrid_system['ensemble']
    anomaly_detector = hybrid_system['anomaly_detector']
    
    if strategy == 'ensemble_only':
        return ensemble.predict(X)
    
    elif strategy == 'anomaly_only':
        anomaly_scores = anomaly_detector.predict(X)
        return (anomaly_scores == -1).astype(int)
    
    else:  # strategy == 'hybrid'
        # Prédictions de l'ensemble
        ensemble_pred = ensemble.predict(X)
        ensemble_proba = ensemble.predict_proba(X)
        
        # Prédictions d'anomalies
        anomaly_pred = anomaly_detector.predict(X)
        
        # Combinaison hybride
        hybrid_pred = []
        for i in range(len(X)):
            # Confiance de l'ensemble
            confidence = np.max(ensemble_proba[i])
            
            # Si l'ensemble est peu confiant ET détection d'anomalie
            if confidence < 0.7 and anomaly_pred[i] == -1:
                hybrid_pred.append(1)  # Prédiction d'attaque
            else:
                hybrid_pred.append(ensemble_pred[i])  # Prédiction de l'ensemble
        
        return np.array(hybrid_pred)

def evaluate_model(y_true, y_pred, model_name):
    """Évalue les performances d'un modèle"""
    metrics = {
        'accuracy': accuracy_score(y_true, y_pred),
        'precision': precision_score(y_true, y_pred, average='weighted', zero_division=0),
        'recall': recall_score(y_true, y_pred, average='weighted', zero_division=0),
        'f1_score': f1_score(y_true, y_pred, average='weighted', zero_division=0)
    }
    
    print(f"📊 {model_name}:")
    print(f"  Accuracy:  {metrics['accuracy']:.4f}")
    print(f"  Precision: {metrics['precision']:.4f}")
    print(f"  Recall:    {metrics['recall']:.4f}")
    print(f"  F1-Score:  {metrics['f1_score']:.4f}")
    
    return metrics

def main():
    """Fonction principale d'analyse"""
    print("🚀 ANALYSE COMPLÈTE DU SYSTÈME DE DÉTECTION D'INTRUSION")
    print("=" * 60)
    print(f"📅 Début: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Chargement et preprocessing des données
    X, y, feature_cols = load_data_and_preprocess()
    if X is None:
        return
    
    # 2. Division des données
    print(f"\n🔄 Division des données...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    print(f"📊 Train: {X_train.shape}, Test: {X_test.shape}")
    
    # 3. Normalisation
    print(f"\n🔄 Normalisation des données...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    print("✅ Normalisation terminée")
    
    # 4. Chargement des modèles existants
    existing_models = load_existing_models()
    
    # 5. Test des modèles individuels existants
    print(f"\n📊 ÉVALUATION DES MODÈLES INDIVIDUELS")
    print("-" * 40)
    
    individual_results = {}
    
    for name, model in existing_models.items():
        if name != 'scaler' and hasattr(model, 'predict'):
            try:
                # Utilisation du scaler existant si disponible
                if 'scaler' in existing_models:
                    X_test_for_model = existing_models['scaler'].transform(X_test)
                else:
                    X_test_for_model = X_test_scaled
                
                y_pred = model.predict(X_test_for_model)
                metrics = evaluate_model(y_test, y_pred, f"{name.upper()} (existant)")
                individual_results[name] = metrics
                
            except Exception as e:
                print(f"❌ Erreur test {name}: {e}")
    
    # 6. Création et test de l'ensemble
    print(f"\n📊 CRÉATION ET TEST DE L'ENSEMBLE")
    print("-" * 40)
    
    # Préparation des données pour l'ensemble
    if 'scaler' in existing_models:
        X_train_for_ensemble = existing_models['scaler'].transform(X_train)
        X_test_for_ensemble = existing_models['scaler'].transform(X_test)
    else:
        X_train_for_ensemble = X_train_scaled
        X_test_for_ensemble = X_test_scaled
    
    ensemble_model = create_ensemble_system(existing_models, X_train_for_ensemble, y_train)
    
    ensemble_results = {}
    
    if ensemble_model:
        try:
            y_pred_ensemble = ensemble_model.predict(X_test_for_ensemble)
            metrics = evaluate_model(y_test, y_pred_ensemble, "ENSEMBLE (Voting)")
            ensemble_results['ensemble'] = metrics
        except Exception as e:
            print(f"❌ Erreur test ensemble: {e}")
    
    # 7. Création et test du système hybride
    print(f"\n📊 CRÉATION ET TEST DU SYSTÈME HYBRIDE")
    print("-" * 40)
    
    hybrid_results = {}
    
    if ensemble_model:
        hybrid_system = create_hybrid_system(ensemble_model, X_train_for_ensemble, y_train)
        
        # Test des différentes stratégies
        strategies = ['ensemble_only', 'anomaly_only', 'hybrid']
        
        for strategy in strategies:
            try:
                y_pred_hybrid = predict_hybrid(hybrid_system, X_test_for_ensemble, strategy)
                metrics = evaluate_model(y_test, y_pred_hybrid, f"HYBRIDE ({strategy})")
                hybrid_results[f"hybrid_{strategy}"] = metrics
            except Exception as e:
                print(f"❌ Erreur stratégie {strategy}: {e}")
    
    # 8. Résumé et comparaison
    print(f"\n🏆 RÉSUMÉ ET COMPARAISON DES RÉSULTATS")
    print("=" * 50)
    
    all_results = {}
    all_results.update(individual_results)
    all_results.update(ensemble_results)
    all_results.update(hybrid_results)
    
    if all_results:
        # Classement par F1-score
        sorted_results = sorted(all_results.items(), key=lambda x: x[1]['f1_score'], reverse=True)
        
        print("🥇 CLASSEMENT PAR F1-SCORE:")
        for i, (name, metrics) in enumerate(sorted_results, 1):
            print(f"  {i}. {name.upper():<20} F1={metrics['f1_score']:.4f} Acc={metrics['accuracy']:.4f}")
        
        # Meilleur modèle
        best_name, best_metrics = sorted_results[0]
        print(f"\n🏆 MEILLEUR MODÈLE: {best_name.upper()}")
        print(f"  🎯 F1-Score:  {best_metrics['f1_score']:.4f}")
        print(f"  🎯 Accuracy:  {best_metrics['accuracy']:.4f}")
        print(f"  🎯 Precision: {best_metrics['precision']:.4f}")
        print(f"  🎯 Recall:    {best_metrics['recall']:.4f}")
        
        # Sauvegarde des résultats
        try:
            os.makedirs('results', exist_ok=True)
            
            results_df = pd.DataFrame(all_results).T
            results_df.to_csv('results/final_analysis_results.csv')
            
            # Sauvegarde du meilleur système
            if 'hybrid' in best_name and ensemble_model:
                joblib.dump(hybrid_system, 'results/best_hybrid_system.pkl')
                joblib.dump(scaler, 'results/final_scaler.pkl')
                print(f"\n💾 Meilleur système sauvegardé dans 'results/'")
            
            print(f"💾 Résultats sauvegardés dans 'results/final_analysis_results.csv'")
            
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde: {e}")
    
    else:
        print("❌ Aucun résultat à afficher")
    
    print(f"\n✅ ANALYSE TERMINÉE")
    print(f"📅 Fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎉 Système de détection d'intrusion analysé avec succès!")

if __name__ == "__main__":
    main()
