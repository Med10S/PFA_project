#!/usr/bin/env python3
"""
Script de test simple pour vérifier le système
"""

import sys
import os
import traceback

# Ajouter le répertoire parent au path pour importer les modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

def test_imports():
    """Test des imports"""
    print("🔍 Test des imports...")
    try:
        import DEV.config as config
        print("✅ Config importé")
        
        import functions.preprocessing as preprocessing
        print("✅ Preprocessing importé")
        
        import functions.ensemble_models as ensemble_models
        print("✅ Ensemble models importé")
        
        import functions.model_loader as model_loader
        print("✅ Model loader importé")
        
        return True
    except Exception as e:
        print(f"❌ Erreur d'import: {e}")
        traceback.print_exc()
        return False

def test_model_loading():
    """Test du chargement des modèles"""
    print("\n🤖 Test du chargement des modèles...")
    try:
        from functions.model_loader import ModelLoader
        
        ml = ModelLoader()
        print("✅ Instance ModelLoader créée")
        
        success = ml.load_all_models()
        if success:
            print("✅ Modèles chargés avec succès")
            return True
        else:
            print("❌ Échec du chargement des modèles")
            return False
            
    except Exception as e:
        print(f"❌ Erreur de chargement: {e}")
        traceback.print_exc()
        return False

def test_prediction():
    """Test d'une prédiction simple"""
    print("\n🔮 Test de prédiction...")
    try:
        from functions.model_loader import ModelLoader
        import pandas as pd
        
        # Données de test
        test_data = {
           "dur": 0.121478, "proto": "tcp", "service": "http", "state": "FIN",
            "spkts": 8, "dpkts": 26, "sbytes": 1032, "dbytes": 15421, "rate": 194.836043,
            "sttl": 63, "dttl": 63, "sload": 8504.846381, "dload": 126910.215713,
            "sloss": 0, "dloss": 0, "sinpkt": 0.000772, "dinpkt": 0.001424,
            "sjit": 0.000000, "djit": 0.003228, "swin": 255, "stcpb": 0, "dtcpb": 0,
            "dwin": 8192, "tcprtt": 0.000774, "synack": 0.000000, "ackdat": 0.000000,
            "smean": 129, "dmean": 593, "trans_depth": 2, "response_body_len": 12174,
            "ct_srv_src": 1, "ct_state_ttl": 1, "ct_dst_ltm": 1, "ct_src_dport_ltm": 1,
            "ct_dst_sport_ltm": 1, "ct_dst_src_ltm": 1, "is_ftp_login": 0, "ct_ftp_cmd": 0,
            "ct_flw_http_mthd": 1, "ct_src_ltm": 1, "ct_srv_dst": 1, "is_sm_ips_ports": 0
        }
        
        ml = ModelLoader()
        ml.load_all_models()
        
        df = pd.DataFrame([test_data])
        result = ml.predict(df)
        
        print(f"✅ Prédiction réussie: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur de prédiction: {e}")
        traceback.print_exc()
        return False

def main():
    """Fonction principale"""
    print("🚀 Test du système de détection d'intrusion")
    print("=" * 50)
    
    # Test 1: Imports
    if not test_imports():
        print("❌ Échec des imports")
        return False
    
    # Test 2: Chargement des modèles
    if not test_model_loading():
        print("❌ Échec du chargement des modèles")
        return False
    
    # Test 3: Prédiction
    if not test_prediction():
        print("❌ Échec de la prédiction")
        return False
    
    print("\n🎉 Tous les tests sont passés !")
    print("Le système est prêt pour le démarrage du service FastAPI.")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
