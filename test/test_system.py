#!/usr/bin/env python3
"""
Test rapide du système de détection d'intrusion
"""

print("🚀 Test du système de détection d'intrusion")
print("=" * 50)

# Test des imports
print("🔄 Test des imports...")
try:
    import pandas as pd
    import numpy as np
    print("✅ pandas et numpy OK")
except ImportError as e:
    print(f"❌ Erreur pandas/numpy: {e}")
    exit(1)

try:
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import accuracy_score, f1_score
    print("✅ scikit-learn OK")
except ImportError as e:
    print(f"❌ Erreur scikit-learn: {e}")
    exit(1)

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.neighbors import KNeighborsClassifier
    print("✅ Modèles sklearn OK")
except ImportError as e:
    print(f"❌ Erreur modèles sklearn: {e}")
    exit(1)

# Test de chargement des données
print("\n📂 Test de chargement des données...")
try:
    data = pd.read_csv("UNSW_NB15_training-set.csv")
    print(f"✅ Données chargées: {data.shape}")
    print(f"📊 Colonnes: {len(data.columns)}")
    
    # Affichage des premières colonnes
    print("📋 Premières colonnes:", list(data.columns[:10]))
    
    # Vérification de la colonne label
    if 'label' in data.columns:
        print(f"🎯 Colonne 'label' trouvée: {data['label'].value_counts().to_dict()}")
    else:
        print("⚠️ Colonne 'label' non trouvée")
        print("📋 Colonnes disponibles:", list(data.columns))
    
except Exception as e:
    print(f"❌ Erreur chargement données: {e}")
    exit(1)

# Test de preprocessing simple
print("\n🔄 Test de preprocessing...")
try:
    # Sélection des colonnes numériques
    numeric_cols = data.select_dtypes(include=[np.number]).columns
    print(f"📊 Colonnes numériques: {len(numeric_cols)}")
    
    # Préparation des features et target
    if 'label' in data.columns:
        # Features numériques seulement pour ce test
        X = data[numeric_cols].drop('label', axis=1) if 'label' in numeric_cols else data[numeric_cols]
        y = data['label']
        
        # Gestion des valeurs manquantes
        X = X.fillna(X.median())
        
        print(f"✅ Features préparées: {X.shape}")
        print(f"✅ Target préparée: {y.shape}")
        print(f"📊 Répartition target: {y.value_counts().to_dict()}")
        
    else:
        print("❌ Impossible de préparer les données sans colonne 'label'")
        exit(1)
        
except Exception as e:
    print(f"❌ Erreur preprocessing: {e}")
    exit(1)

# Test d'entraînement simple
print("\n🎯 Test d'entraînement simple...")
try:
    # Division des données
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    
    print(f"📊 Train: {X_train.shape}, Test: {X_test.shape}")
    
    # Normalisation
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    print("✅ Normalisation OK")
    
    # Test avec Random Forest (modèle simple et robuste)
    print("🌳 Test Random Forest...")
    rf = RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=-1)
    rf.fit(X_train_scaled, y_train)
    
    # Prédictions
    y_pred = rf.predict(X_test_scaled)
    
    # Métriques
    accuracy = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred, average='weighted')
    
    print(f"✅ Random Forest entraîné")
    print(f"📊 Accuracy: {accuracy:.4f}")
    print(f"📊 F1-Score: {f1:.4f}")
    
except Exception as e:
    print(f"❌ Erreur entraînement: {e}")
    exit(1)

# Test avec KNN
print("\n🔍 Test KNN...")
try:
    knn = KNeighborsClassifier(n_neighbors=5, n_jobs=-1)
    knn.fit(X_train_scaled, y_train)
    
    y_pred_knn = knn.predict(X_test_scaled)
    
    accuracy_knn = accuracy_score(y_test, y_pred_knn)
    f1_knn = f1_score(y_test, y_pred_knn, average='weighted')
    
    print(f"✅ KNN entraîné")
    print(f"📊 Accuracy: {accuracy_knn:.4f}")
    print(f"📊 F1-Score: {f1_knn:.4f}")
    
except Exception as e:
    print(f"❌ Erreur KNN: {e}")

# Résumé
print(f"\n🏆 RÉSUMÉ DU TEST")
print("=" * 30)
print(f"✅ Données chargées: {data.shape}")
print(f"✅ Features: {X.shape[1]}")
print(f"✅ Échantillons train: {X_train.shape[0]}")
print(f"✅ Échantillons test: {X_test.shape[0]}")
print(f"🌳 Random Forest F1: {f1:.4f}")
print(f"🔍 KNN F1: {f1_knn:.4f}")

print(f"\n🎉 Test réussi! Le système fonctionne.")
print("💡 Vous pouvez maintenant exécuter l'analyse complète.")
