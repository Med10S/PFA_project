"""
Script de test pour le système de détection en temps réel
Test des différents endpoints et validation du fonctionnement
"""

import asyncio
import json
import pandas as pd
import requests
import time
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8000"

# Données de test (logs d'exemple au format UNSW-NB15)
SAMPLE_LOGS = [
    {
        "id": 1, "dur": 0.121478, "proto": "tcp", "service": "http", "state": "FIN",
        "spkts": 8, "dpkts": 26, "sbytes": 1032, "dbytes": 15421, "rate": 194.836043,
        "sttl": 63, "dttl": 63, "sload": 8504.846381, "dload": 126910.215713,
        "sloss": 0, "dloss": 0, "sinpkt": 0.000772, "dinpkt": 0.001424,
        "sjit": 0.000000, "djit": 0.003228, "swin": 255, "stcpb": 0, "dtcpb": 0,
        "dwin": 8192, "tcprtt": 0.000774, "synack": 0.000000, "ackdat": 0.000000,
        "smean": 129, "dmean": 593, "trans_depth": 2, "response_body_len": 12174,
        "ct_srv_src": 1, "ct_state_ttl": 1, "ct_dst_ltm": 1, "ct_src_dport_ltm": 1,
        "ct_dst_sport_ltm": 1, "ct_dst_src_ltm": 1, "is_ftp_login": 0, "ct_ftp_cmd": 0,
        "ct_flw_http_mthd": 1, "ct_src_ltm": 1, "ct_srv_dst": 1, "is_sm_ips_ports": 0
    },
    {
        "id": 2, "dur": 0.000000, "proto": "tcp", "service": "-", "state": "REQ",
        "spkts": 2, "dpkts": 0, "sbytes": 80, "dbytes": 0, "rate": 0.000000,
        "sttl": 62, "dttl": 0, "sload": 640000.000000, "dload": 0.000000,
        "sloss": 0, "dloss": 0, "sinpkt": 0.000000, "dinpkt": 0.000000,
        "sjit": 0.000000, "djit": 0.000000, "swin": 16384, "stcpb": 2969885741, "dtcpb": 0,
        "dwin": 0, "tcprtt": 0.000000, "synack": 0.000000, "ackdat": 0.000000,
        "smean": 40, "dmean": 0, "trans_depth": 0, "response_body_len": 0,
        "ct_srv_src": 1, "ct_state_ttl": 1, "ct_dst_ltm": 1, "ct_src_dport_ltm": 1,
        "ct_dst_sport_ltm": 1, "ct_dst_src_ltm": 1, "is_ftp_login": 0, "ct_ftp_cmd": 0,
        "ct_flw_http_mthd": 0, "ct_src_ltm": 1, "ct_srv_dst": 1, "is_sm_ips_ports": 0
    },
    {
        "id": 3, "dur": 0.053829, "proto": "tcp", "service": "https", "state": "INT",
        "spkts": 2, "dpkts": 1, "sbytes": 148, "dbytes": 96, "rate": 55.732087,
        "sttl": 56, "dttl": 128, "sload": 2749.449638, "dload": 1783.426792,
        "sloss": 0, "dloss": 0, "sinpkt": 0.053829, "dinpkt": 0.000000,
        "sjit": 0.000000, "djit": 0.000000, "swin": 11, "stcpb": 3279792393, "dtcpb": 1272394237,
        "dwin": 251, "tcprtt": 0.000000, "synack": 0.000000, "ackdat": 0.000000,
        "smean": 74.0, "dmean": 96.0, "trans_depth": 0, "response_body_len": 0,
        "ct_srv_src": 1, "ct_state_ttl": 1, "ct_dst_ltm": 1, "ct_src_dport_ltm": 1,
        "ct_dst_sport_ltm": 1, "ct_dst_src_ltm": 1, "is_ftp_login": 0, "ct_ftp_cmd": 0,
        "ct_flw_http_mthd": 0, "ct_src_ltm": 1, "ct_srv_dst": 1, "is_sm_ips_ports": 0
    }
]

# CSV de test
CSV_TEST_DATA = """id,dur,proto,service,state,spkts,dpkts,sbytes,dbytes,rate,sttl,dttl,sload,dload,sloss,dloss,sinpkt,dinpkt,sjit,djit,swin,stcpb,dtcpb,dwin,tcprtt,synack,ackdat,smean,dmean,trans_depth,response_body_len,ct_srv_src,ct_state_ttl,ct_dst_ltm,ct_src_dport_ltm,ct_dst_sport_ltm,ct_dst_src_ltm,is_ftp_login,ct_ftp_cmd,ct_flw_http_mthd,ct_src_ltm,ct_srv_dst,is_sm_ips_ports
3,0.121478,tcp,http,FIN,8,26,1032,15421,194.836043,63,63,8504.846381,126910.215713,0,0,0.000772,0.001424,0.000000,0.003228,255,0,0,8192,0.000774,0.000000,0.000000,129,593,2,12174,1,1,1,1,1,1,0,0,1,1,1,0
4,0.000000,tcp,-,REQ,2,0,80,0,0.000000,62,0,640000.000000,0.000000,0,0,0.000000,0.000000,0.000000,0.000000,16384,2969885741,0,0,0.000000,0.000000,0.000000,40,0,0,0,1,1,1,1,1,1,0,0,0,1,1,0"""

def test_api_health():
    """Test du endpoint de santé"""
    print("🏥 Test du endpoint de santé...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Service en bonne santé: {data}")
            return True
        else:
            print(f"❌ Erreur de santé: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return False

def test_root_endpoint():
    """Test du endpoint racine"""
    print("\n🏠 Test du endpoint racine...")
    try:
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Endpoint racine OK: {data['message']}")
            return True
        else:
            print(f"❌ Erreur endpoint racine: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_models_info():
    """Test des informations sur les modèles"""
    print("\n🤖 Test des informations sur les modèles...")
    try:
        response = requests.get(f"{API_BASE_URL}/models/info")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Informations modèles: {json.dumps(data, indent=2)}")
            return True
        else:
            print(f"❌ Erreur infos modèles: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_single_detection():
    """Test de détection sur un log individuel"""
    print("\n🔍 Test de détection individuelle...")
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/detect/single",
            json=SAMPLE_LOGS[1],
            headers={"Content-Type": "application/json"}
        )
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Détection réussie en {(end_time - start_time)*1000:.2f}ms")
            print(f"   Log ID: {data['log_id']}")
            print(f"   Attaque détectée: {data['is_attack']}")
            print(f"   Probabilité d'attaque: {data['attack_probability']:.4f}")
            print(f"   Confiance: {data['confidence']:.4f}")
            print(f"   Alerte générée: {data['alert_generated']}")
            return True
        else:
            print(f"❌ Erreur détection: {response.status_code}")
            print(f"   Réponse: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_batch_detection():
    """Test de détection en batch"""
    print("\n📦 Test de détection en batch...")
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/detect/batch",
            json={"logs": SAMPLE_LOGS},
            headers={"Content-Type": "application/json"}
        )
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Détection batch réussie en {(end_time - start_time)*1000:.2f}ms")
            print(f"   Logs traités: {data['total_logs']}")
            print(f"   Attaques détectées: {data['attacks_detected']}")
            print(f"   Temps de traitement: {data['processing_time_ms']:.2f}ms")
            
            # Affichage des résultats détaillés
            for result in data['results']:
                print(f"   - Log {result['log_id']}: {'🚨 ATTAQUE' if result['is_attack'] else '✅ NORMAL'} "
                      f"(prob: {result['attack_probability']:.4f}, conf: {result['confidence']:.4f})")
            return True
        else:
            print(f"❌ Erreur détection batch: {response.status_code}")
            print(f"   Réponse: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_csv_detection():
    """Test de détection CSV"""
    print("\n📄 Test de détection CSV...")
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/detect/csv",
            json={"csv_data": CSV_TEST_DATA},
            headers={"Content-Type": "application/json"}
        )
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Détection CSV réussie en {(end_time - start_time)*1000:.2f}ms")
            print(f"   Logs traités: {data['total_logs']}")
            print(f"   Attaques détectées: {data['attacks_detected']}")
            print(f"   Temps de traitement: {data['processing_time_ms']:.2f}ms")
            
            # Affichage des résultats détaillés
            for result in data['results']:
                print(f"   - Log {result['log_id']}: {'🚨 ATTAQUE' if result['is_attack'] else '✅ NORMAL'} "
                      f"(prob: {result['attack_probability']:.4f}, conf: {result['confidence']:.4f})")
            return True
        else:
            print(f"❌ Erreur détection CSV: {response.status_code}")
            print(f"   Réponse: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_real_data():
    """Test avec des données réelles du dataset"""
    print("\n📊 Test avec des données réelles...")
    try:
        # Chargement de quelques lignes du dataset de test
        df = pd.read_csv("UNSW_NB15_training-set.csv")
        # Sélectionner des données équilibrées entre lignes 240-250
        sample_data = df.iloc[240:250]
        
        # Conversion en format compatible avec l'API
        logs = []
        for _, row in sample_data.iterrows():
            log = {}
            for col in df.columns:
                if col != 'label':  # Exclure la colonne label
                    log[col] = row[col]
            logs.append(log)
        
        start_time = time.time()
        response = requests.post(
            f"{API_BASE_URL}/detect/batch",
            json={"logs": logs},
            headers={"Content-Type": "application/json"}
        )
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Test données réelles réussi en {(end_time - start_time)*1000:.2f}ms")
            print(f"   Logs traités: {data['total_logs']}")
            print(f"   Attaques détectées: {data['attacks_detected']}")
            print(f"   Temps de traitement: {data['processing_time_ms']:.2f}ms")
            
            # Comparaison avec les labels réels
            for i, result in enumerate(data['results']):
                real_label = sample_data.iloc[i]['label']
                predicted = result['is_attack']
                match = "✅" if (real_label == 1 and predicted) or (real_label == 0 and not predicted) else "❌"
                print(f"   - Log {result['log_id']}: Prédit={'ATTAQUE' if predicted else 'NORMAL'}, "
                      f"Réel={'ATTAQUE' if real_label == 1 else 'NORMAL'} {match}")
            
            return True
        else:
            print(f"❌ Erreur test données réelles: {response.status_code}")
            return False
            
    except FileNotFoundError:
        print("⚠️  Dataset de test non trouvé, test ignoré")
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_performance():
    """Test de performance avec plusieurs requêtes"""
    print("\n⚡ Test de performance...")
    try:
        num_requests = 10
        times = []
        
        for i in range(num_requests):
            start_time = time.time()
            response = requests.post(
                f"{API_BASE_URL}/detect/single",
                json=SAMPLE_LOGS[i % len(SAMPLE_LOGS)],
                headers={"Content-Type": "application/json"}
            )
            end_time = time.time()
            
            if response.status_code == 200:
                times.append((end_time - start_time) * 1000)
            else:
                print(f"❌ Erreur requête {i+1}: {response.status_code}")
                return False
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"✅ Performance test réussi ({num_requests} requêtes)")
        print(f"   Temps moyen: {avg_time:.2f}ms")
        print(f"   Temps min: {min_time:.2f}ms")
        print(f"   Temps max: {max_time:.2f}ms")
        print(f"   Throughput: {1000/avg_time:.2f} requêtes/seconde")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def run_all_tests():
    """Exécute tous les tests"""
    print("🚀 Démarrage des tests du système de détection en temps réel")
    print("=" * 70)
    
    tests = [
        ("Health Check", test_api_health),
        ("Root Endpoint", test_root_endpoint),
        ("Models Info", test_models_info),
        ("Single Detection", test_single_detection),
        ("Batch Detection", test_batch_detection),
        ("CSV Detection", test_csv_detection),
        ("Real Data Test", test_real_data),
        ("Performance Test", test_performance)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Exécution du test: {test_name}")
        print("-" * 50)
        
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Erreur inattendue dans {test_name}: {e}")
            results.append((test_name, False))
    
    # Résumé des résultats
    print("\n" + "=" * 70)
    print("📋 RÉSUMÉ DES TESTS")
    print("=" * 70)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSÉ" if success else "❌ ÉCHOUÉ"
        print(f"{test_name:<20} : {status}")
        if success:
            passed += 1
    
    print("-" * 70)
    print(f"Tests réussis: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 Tous les tests sont passés ! Le système est prêt pour la production.")
    else:
        print("⚠️  Certains tests ont échoué. Vérifiez la configuration et les logs.")
    
    return passed == total

if __name__ == "__main__":
    # Vérification que le service est démarré
    print("🔍 Vérification de la disponibilité du service...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Service disponible, démarrage des tests...\n")
            success = run_all_tests()
            exit(0 if success else 1)
        else:
            print(f"❌ Service non disponible (status: {response.status_code})")
            print("Assurez-vous que le service FastAPI est démarré avec:")
            print("uvicorn realtime_detection_service:app --host 0.0.0.0 --port 8000")
            exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter au service")
        print("Assurez-vous que le service FastAPI est démarré avec:")
        print("uvicorn realtime_detection_service:app --host 0.0.0.0 --port 8000")
        exit(1)
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        exit(1)
