#!/usr/bin/env python3
"""
Validation du système étape par étape
"""

print("🔍 Étape 1: Test des imports de base...")

try:
    import pandas as pd
    print("✅ pandas")
    
    import numpy as np
    print("✅ numpy")
    
    import sklearn
    print("✅ scikit-learn")
    
    import fastapi
    print("✅ fastapi")
    
    import uvicorn
    print("✅ uvicorn")
    
    print("\n🔍 Étape 2: Test des modules du projet...")
    
    import config
    print("✅ config")
    print(f"   - Modèles configurés: {list(config.MODELS_CONFIG.keys())}")
    print(f"   - Features: {len(config.FEATURE_NAMES)}")
    
    import functions.preprocessing as preprocessing
    print("✅ preprocessing")
    
    import ensemble_models
    print("✅ ensemble_models")
    
    import functions.model_loader as model_loader
    print("✅ model_loader")
    
    print("\n🔍 Étape 3: Test du chargement des modèles...")
    
    # Test des fichiers modèles
    import os
    models_dir = "models"
    required_models = ["KNN_best.pkl", "mlp_best.pkl", "xgb_best.pkl", "scaler.pkl", "label_encoders.pkl"]
    
    for model_file in required_models:
        path = os.path.join(models_dir, model_file)
        if os.path.exists(path):
            print(f"✅ {model_file}")
        else:
            print(f"❌ {model_file} manquant")
    
    print("\n🔍 Étape 4: Test d'instanciation...")
    
    ml = model_loader.ModelLoader()
    print("✅ ModelLoader instancié")
    
    preprocessor = preprocessing.RealtimePreprocessor()
    print("✅ RealtimePreprocessor instancié")
    
    print("\n🎉 Validation basique réussie!")
    print("Le système semble correctement configuré.")
    
except ImportError as e:
    print(f"❌ Erreur d'import: {e}")
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
