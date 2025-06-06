#!/usr/bin/env python3
"""
Script de test pour l'API de détection d'intrusion
"""

import requests
import json

def test_health():
    """Test de l'endpoint de santé"""
    print("🔍 Test du service de détection d'intrusion...")
    try:
        response = requests.get('http://localhost:8000/health')
        print(f"✅ Status API: {response.status_code}")
        print(f"📊 Santé: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_single_detection():
    """Test de détection sur un log individuel"""
    # Votre exemple de log UNSW-NB15
    log_data = {
        'id': 1,
        'dur': 0.121478,
        'proto': 'tcp',
        'service': 'ftp-data',
        'state': 'INT',
        'spkts': 12,
        'dpkts': 18,
        'sbytes': 1032,
        'dbytes': 1204,
        'rate': 28.15,
        'sttl': 254,
        'dttl': 249,
        'sload': 83.38,
        'dload': 93.18,
        'sloss': 0,
        'dloss': 0,
        'sinpkt': 0.01,
        'dinpkt': 0.007,
        'sjit': 0.003,
        'djit': 0.003,
        'swin': 255,
        'stcpb': 0,
        'dtcpb': 0,
        'dwin': 255,
        'tcprtt': 0.01,
        'synack': 0.003,
        'ackdat': 0.007,
        'smean': 86,
        'dmean': 67,
        'trans_depth': 0,
        'response_body_len': 0,
        'ct_srv_src': 1,
        'ct_state_ttl': 2,
        'ct_dst_ltm': 1,
        'ct_src_dport_ltm': 1,
        'ct_dst_sport_ltm': 1,
        'ct_dst_src_ltm': 1,
        'is_ftp_login': 0,
        'ct_ftp_cmd': 0,
        'ct_flw_http_mthd': 0,
        'ct_src_ltm': 2,
        'ct_srv_dst': 1,
        'is_sm_ips_ports': 0
    }

    log_data = {
        'id': 241,
        'dur': 1.964566,
        'proto': 'tcp', 
        'service': '-',
        'state': 'FIN',
        'spkts': 10,
        'dpkts': 8,
        'sbytes': 2516,
        'dbytes': 354,
        'rate': 8.653311,
        'sttl': 254,
        'dttl': 252,
        'sload': 9223.411133,
        'dload': 1262.365356,
        'sloss': 2,
        'dloss': 1,
        'sinpkt': 218.174222,
        'dinpkt': 270.640719,
        'sjit': 13125.09697,
        'djit': 469.482,
        'swin': 255,
        'stcpb': 1591881928,
        'dtcpb': 2482385855,
        'dwin': 255,
        'tcprtt': 0.159326,
        'synack': 0.07008,
        'ackdat': 0.089246,
        'smean': 252,
        'dmean': 44,
        'trans_depth': 0,
        'response_body_len': 0,
        'ct_srv_src': 8,
        'ct_state_ttl': 1,
        'ct_dst_ltm': 1,
        'ct_src_dport_ltm': 1,
        'ct_dst_sport_ltm': 1,
        'ct_dst_src_ltm': 1,
        'is_ftp_login': 0,
        'ct_ftp_cmd': 0,
        'ct_flw_http_mthd': 0,
        'ct_src_ltm': 1,
        'ct_srv_dst': 1,
        'is_sm_ips_ports': 0
    }

    print("\n🎯 Test de détection sur un log réseau...")
    try:
        response = requests.post('http://localhost:8000/detect/single', json=log_data)
        print(f"✅ Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"🎯 Résultat de détection:")
            print(f"   - Est une attaque: {result['is_attack']}")
            print(f"   - Confiance: {result['confidence']:.3f}")
            print(f"   - Probabilité d'attaque: {result['attack_probability']:.3f}")
            print(f"   - Alerte générée: {result['alert_generated']}")
            print(f"   - Prédictions ML: {result['ml_predictions']}")
            print(f"   - Timestamp: {result['timestamp']}")
            return True
        else:
            print(f"❌ Erreur HTTP: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_csv_detection():
    """Test de détection sur des données CSV"""
    csv_data = """id,dur,proto,service,state,spkts,dpkts,sbytes,dbytes,rate,sttl,dttl,sload,dload,sloss,dloss,sinpkt,dinpkt,sjit,djit,swin,stcpb,dtcpb,dwin,tcprtt,synack,ackdat,smean,dmean,trans_depth,response_body_len,ct_srv_src,ct_state_ttl,ct_dst_ltm,ct_src_dport_ltm,ct_dst_sport_ltm,ct_dst_src_ltm,is_ftp_login,ct_ftp_cmd,ct_flw_http_mthd,ct_src_ltm,ct_srv_dst,is_sm_ips_ports
1,0.121478,tcp,ftp-data,INT,12,18,1032,1204,248.15,254,249,8493.38,9913.18,0,0,0.01,0.007,0.003,0.003,255,0,0,255,0.01,0.003,0.007,86,67,0,0,1,2,1,1,1,1,0,0,0,2,1,0
2,0.649112,tcp,http,CON,19,17,2334,1940,53.13,252,254,3594.27,2986.72,0,0,0.04,0.02,0.006,0.004,255,0,0,255,0.019,0.006,0.024,123,114,2,1940,2,2,1,1,1,1,0,0,2,2,2,0"""

    payload = {"csv_data": csv_data}
    
    print("\n📊 Test de détection sur données CSV...")
    try:
        response = requests.post('http://localhost:8000/detect/csv', json=payload)
        print(f"✅ Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"📊 Résultat batch:")
            print(f"   - Total logs: {result['total_logs']}")
            print(f"   - Attaques détectées: {result['attacks_detected']}")
            print(f"   - Temps de traitement: {result['processing_time_ms']:.2f}ms")
            
            for i, res in enumerate(result['results']):
                print(f"   Log {i+1}: {'🚨 ATTAQUE' if res['is_attack'] else '✅ Normal'} (confiance: {res['confidence']:.3f})")
            return True
        else:
            print(f"❌ Erreur HTTP: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_models_info():
    """Test des informations sur les modèles"""
    print("\n🔧 Test des informations sur les modèles...")
    try:
        response = requests.get('http://localhost:8000/models/info')
        print(f"✅ Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"🔧 Informations modèles:")
            print(f"   - Modèles chargés: {result['models_loaded']}")
            print(f"   - Ensemble disponible: {result['ensemble_available']}")
            print(f"   - Hybride disponible: {result['hybrid_available']}")
            print(f"   - Nombre de features: {result['feature_count']}")
            print(f"   - Seuil de détection: {result['detection_threshold']}")
            print(f"   - Seuil de confiance: {result['confidence_threshold']}")
            return True
        else:
            print(f"❌ Erreur HTTP: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Tests du système de détection d'intrusion en temps réel")
    print("=" * 60)
    
    # Test de santé
    if not test_health():
        print("❌ Service non disponible, arrêt des tests")
        exit(1)
    
    # Test détection individuelle
    test_single_detection()
    
    # Test détection CSV
    test_csv_detection()
    
    # Test informations modèles
    test_models_info()
    
    print("\n🎉 Tests terminés !")
