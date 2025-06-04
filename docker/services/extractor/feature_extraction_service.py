#!/usr/bin/env python3
"""
Service d'Extraction de Features
===============================
Reçoit les paquets via Redis, utilise unsw_nb15_feature_extractor et envoie vers l'API ML
"""

import os
import sys
import json
import time
import redis
import logging
import requests
import threading
import pandas as pd
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from cryptography.fernet import Fernet
import tempfile
import hashlib
from scapy.all import wrpcap, rdpcap

# Import de votre extracteur
sys.path.append('/app/extractor')
from unsw_nb15_feature_extractor import UNSW_NB15_FeatureExtractor

# Configuration avec gestion d'erreurs pour les types
def safe_int_env(env_var, default_value):
    """Convertit une variable d'environnement en entier de manière sécurisée"""
    try:
        value = os.getenv(env_var, str(default_value))
        return int(value)
    except (ValueError, TypeError):
        logger.warning(f"Variable {env_var} non valide, utilisation de la valeur par défaut: {default_value}")
        return default_value

REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = safe_int_env('REDIS_PORT', 6379)
PROCESSING_WORKERS = safe_int_env('PROCESSING_WORKERS', 4)
BATCH_SIZE = safe_int_env('BATCH_SIZE', 100)
API_ENDPOINT = os.getenv('API_ENDPOINT', 'http://ml-api:8001')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key())
NODE_ID = os.getenv('NODE_ID', 'extractor-node')
REDIS_DB = safe_int_env('REDIS_DB', 0)  # Base par défaut Redis
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'SecureRedisPassword123!')

# Queues Redis
PACKET_QUEUE = 'packet_queue'
FEATURES_QUEUE = 'features_queue'
STATUS_QUEUE = 'extractor_status'
RESULTS_QUEUE = 'detection_results'

# Configuration logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/feature_extractor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FeatureExtractionService:
    """Service d'extraction de features avec traitement parallèle"""
    
    def __init__(self):
        self.redis_client = None
        self.cipher = Fernet(ENCRYPTION_KEY)
        self.is_running = True
        self.feature_extractor = UNSW_NB15_FeatureExtractor()
        self.stats = {
            'batches_processed': 0,
            'packets_processed': 0,
            'features_extracted': 0,
            'api_calls': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        self.temp_dir = Path('/tmp/pcap_processing')
        self.temp_dir.mkdir(exist_ok=True)
    
    def connect_redis(self):
        """Connexion à Redis avec retry et configuration optimisée"""
        max_retries = 5
        retry_delay = 1
        
        # Debug des variables de configuration
        logger.info(f"🔧 Configuration Redis:")
        logger.info(f"   - Host: {REDIS_HOST} (type: {type(REDIS_HOST)})")
        logger.info(f"   - Port: {REDIS_PORT} (type: {type(REDIS_PORT)})")
        logger.info(f"   - DB: {REDIS_DB} (type: {type(REDIS_DB)})")
        logger.info(f"   - Password: {'***' if REDIS_PASSWORD else 'None'}")
        
        for attempt in range(max_retries):
            try:                # Configuration Redis simplifiée sans socket_keepalive_options
                self.redis_client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    decode_responses=False,
                    socket_connect_timeout=15,
                    socket_timeout=60,
                    socket_keepalive=True,
                    health_check_interval=30,
                    db=REDIS_DB,
                    password=REDIS_PASSWORD,
                    max_connections=10
                )

                # Test de connexion avec timeout
                self.redis_client.ping()
                logger.info(f"✅ Connexion Redis établie (tentative {attempt + 1})")
                
                # Vérifier la taille de la queue
                queue_size = self.redis_client.llen(PACKET_QUEUE)
                logger.info(f"📊 Queue '{PACKET_QUEUE}' contient {queue_size} éléments")
                
                return True
                
            except redis.ConnectionError as e:
                logger.error(f"❌ Tentative {attempt + 1} - Erreur connexion Redis: {e}")
            except redis.TimeoutError as e:
                logger.error(f"⏰ Tentative {attempt + 1} - Timeout Redis: {e}")
            except Exception as e:
                logger.error(f"🔥 Tentative {attempt + 1} - Erreur Redis: {e}")
                logger.error(f"🔍 Type d'erreur: {type(e)}")
                import traceback
                logger.error(f"🔍 Traceback: {traceback.format_exc()}")
                
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
                
        logger.error("💥 Impossible d'établir la connexion Redis après tous les essais")
        return False
        
    def decrypt_packet_data(self, encrypted_data):
        """Déchiffre les données de paquet"""
        try:
            decrypted = self.cipher.decrypt(encrypted_data)
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Erreur déchiffrement: {e}")
            return None
            
    def create_temp_pcap(self, packets_data):
        """Crée un fichier PCAP temporaire à partir des données"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            temp_file = self.temp_dir / f"temp_{timestamp}.pcap"
            
            # Reconstruction des paquets Scapy
            from scapy.all import Packet
            scapy_packets = []
            
            for packet_data in packets_data:
                try:
                    # Reconstruction du paquet depuis raw_data
                    raw_bytes = packet_data.get('raw_data')
                    if raw_bytes:
                        if isinstance(raw_bytes, str):
                            raw_bytes = raw_bytes.encode('latin-1')
                        packet = Packet(raw_bytes)
                        packet.time = packet_data.get('timestamp', time.time())
                        scapy_packets.append(packet)
                except Exception as e:
                    logger.warning(f"Erreur reconstruction paquet: {e}")
                    continue
                    
            if scapy_packets:
                wrpcap(str(temp_file), scapy_packets)
                return temp_file
            else:
                logger.warning("Aucun paquet valide pour PCAP")
                return None
                
        except Exception as e:
            logger.error(f"Erreur création PCAP temporaire: {e}")
            return None
            
    def extract_features(self, temp_pcap_file):
        """Extrait les features UNSW-NB15 depuis un fichier PCAP"""
        try:
            # Utiliser votre extracteur
            df = self.feature_extractor.process_pcap(str(temp_pcap_file))
            
            if len(df) > 0:
                self.stats['features_extracted'] += len(df)
                logger.info(f"Features extraites: {len(df)} flows")
                return df
            else:
                logger.warning("Aucune feature extraite")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Erreur extraction features: {e}")
            return pd.DataFrame()
        finally:
            # Nettoyer le fichier temporaire
            try:
                if temp_pcap_file and temp_pcap_file.exists():
                    temp_pcap_file.unlink()
            except:
                pass
                
    def send_to_ml_api(self, features_df):
        """Envoie les features vers l'API ML pour détection"""
        if features_df.empty:
            return
            
        try:
            # Conversion en format API
            features_list = []
            for _, row in features_df.iterrows():
                feature_dict = row.to_dict()
                # Assurer que tous les champs requis sont présents
                feature_dict['id'] = int(feature_dict.get('id', hash(str(row)) % 1000000))
                features_list.append(feature_dict)
                
            # Préparer la requête
            payload = {
                "logs": features_list
            }
            
            # Envoi vers API ML
            response = requests.post(
                f"{API_ENDPOINT}/detect/batch",
                json=payload,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                results = response.json()
                self.stats['api_calls'] += 1
                logger.info(f"Détection API réussie: {results.get('total_logs', 0)} logs, "
                           f"{results.get('attacks_detected', 0)} attaques")
                
                # Envoyer résultats vers Redis pour alertes
                self.send_results_to_redis(results)
                
            else:
                logger.error(f"Erreur API ML: {response.status_code} - {response.text}")
                self.stats['errors'] += 1
                
        except requests.exceptions.Timeout:
            logger.error("Timeout API ML")
            self.stats['errors'] += 1
        except requests.exceptions.ConnectionError:
            logger.error("Erreur connexion API ML")
            self.stats['errors'] += 1
        except Exception as e:
            logger.error(f"Erreur envoi API ML: {e}")
            self.stats['errors'] += 1
            
    def send_results_to_redis(self, detection_results):
        """Envoie les résultats de détection vers Redis"""
        try:
            result_data = {
                'timestamp': time.time(),
                'node_id': NODE_ID,
                'results': detection_results,
                'processing_time': detection_results.get('processing_time_ms', 0)
            }
            
            result_json = json.dumps(result_data, default=str)
            self.redis_client.lpush(RESULTS_QUEUE, result_json)
            
            # Garder seulement les 1000 derniers résultats
            self.redis_client.ltrim(RESULTS_QUEUE, 0, 999)
            
        except Exception as e:
            logger.error(f"Erreur envoi résultats Redis: {e}")
            
    def process_packet_batch(self, batch_data):
        """Traite un batch de paquets"""
        try:
            batch_id = batch_data.get('batch_id', 'unknown')
            packets = batch_data.get('packets', [])
            
            if not packets:
                return
                
            logger.info(f"🔄 Traitement batch {batch_id}: {len(packets)} paquets")
            
            # Déchiffrement des paquets
            decrypted_packets = []
            for packet_info in packets:
                encrypted_data = packet_info.get('data')
                if encrypted_data:
                    decrypted = self.decrypt_packet_data(encrypted_data)
                    if decrypted:
                        decrypted_packets.append(decrypted)
                        
            if not decrypted_packets:
                logger.warning(f"Aucun paquet déchiffré dans batch {batch_id}")
                return
                
            # Création PCAP temporaire
            temp_pcap = self.create_temp_pcap(decrypted_packets)
            if not temp_pcap:
                return
                
            # Extraction features
            features_df = self.extract_features(temp_pcap)
            if not features_df.empty:
                # Envoi vers API ML
                self.send_to_ml_api(features_df)
                
            self.stats['batches_processed'] += 1
            self.stats['packets_processed'] += len(packets)
            
        except Exception as e:
            logger.error(f"Erreur traitement batch: {e}")
            self.stats['errors'] += 1
            
    def send_status_update(self):
        """Envoie un update de statut"""
        try:
            import psutil
            
            status = {
                'node_id': NODE_ID,
                'timestamp': time.time(),
                'stats': self.stats.copy(),
                'health': {
                    'cpu_percent': psutil.cpu_percent(),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_usage': psutil.disk_usage('/app').percent
                },
                'queue_size': self.redis_client.llen(PACKET_QUEUE) if self.redis_client else 0,
                'temp_files': len(list(self.temp_dir.glob('*.pcap')))
            }
            
            # Calculer le débit
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
            if uptime > 0:
                status['batches_per_minute'] = (self.stats['batches_processed'] / uptime) * 60
                status['packets_per_minute'] = (self.stats['packets_processed'] / uptime) * 60
                
            status_json = json.dumps(status, default=str)
            
            if self.redis_client:
                self.redis_client.lpush(STATUS_QUEUE, status_json)
                self.redis_client.expire(STATUS_QUEUE, 300)
                
        except Exception as e:
            logger.error(f"Erreur envoi statut: {e}")
            
    def cleanup_temp_files(self):
        """Nettoie les fichiers temporaires anciens"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=1)
            
            for temp_file in self.temp_dir.glob('*.pcap'):
                try:
                    file_time = datetime.fromtimestamp(temp_file.stat().st_mtime)
                    if file_time < cutoff_time:
                        temp_file.unlink()
                except Exception as e:
                    logger.warning(f"Erreur suppression {temp_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Erreur nettoyage: {e}")
            
    def monitoring_loop(self):
        """Boucle de monitoring"""
        while self.is_running:
            try:
                self.send_status_update()
                self.cleanup_temp_files()
                time.sleep(30)
            except Exception as e:
                logger.error(f"Erreur monitoring: {e}")
                time.sleep(5)
                
    def start_processing(self):
        """Démarre le service de traitement"""
        logger.info("🚀 === SERVICE D'EXTRACTION DE FEATURES ===")
        
        # Connexion Redis
        if not self.connect_redis():
            logger.error("💥 Impossible de démarrer sans Redis")
            return False
            
        # Thread de monitoring
        monitor_thread = threading.Thread(target=self.monitoring_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Pool de workers
        with ThreadPoolExecutor(max_workers=PROCESSING_WORKERS) as executor:
            logger.info(f"⚡ Service démarré avec {PROCESSING_WORKERS} workers")
            
            while self.is_running:
                try:
                    logger.info("👀 En attente de nouveaux paquets...")
                    
                    # Récupération batch depuis Redis (bloquant avec timeout)
                    result = self.redis_client.brpop(PACKET_QUEUE, timeout=10)
                    
                    if result:
                        queue_name, batch_json = result
                        logger.info(f"📦 Batch reçu depuis Redis!")
                        
                        try:
                            batch_data = json.loads(batch_json.decode())
                            
                            # Traitement asynchrone
                            future = executor.submit(self.process_packet_batch, batch_data)
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"Erreur décodage JSON: {e}")
                            self.stats['errors'] += 1
                    else:
                        # Timeout normal - pas d'erreur
                        logger.debug("⏰ Timeout normal - aucun batch en attente")
                        
                except redis.ConnectionError as e:
                    logger.error(f"💔 Connexion Redis perdue: {e}")
                    if not self.connect_redis():
                        time.sleep(5)
                except redis.TimeoutError as e:
                    logger.debug(f"⏰ Timeout Redis normal: {e}")
                    # Continue la boucle sans erreur
                    continue
                except redis.ResponseError as e:
                    logger.error(f"❌ Erreur de réponse Redis: {e}")
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"🔥 Erreur boucle principale: {e}")
                    time.sleep(1)
                    
        return True

def main():
    """Point d'entrée principal"""
    logger.info("🚀 === SERVICE D'EXTRACTION DE FEATURES ===")
    logger.info(f"👷 Workers: {PROCESSING_WORKERS}")
    logger.info(f"📦 Batch size: {BATCH_SIZE}")
    logger.info(f"🤖 API ML: {API_ENDPOINT}")
    logger.info(f"🔐 Redis Host: {REDIS_HOST}:{REDIS_PORT}")
    
    service = FeatureExtractionService()
    
    try:
        service.start_processing()
    except KeyboardInterrupt:
        logger.info("🛑 Arrêt demandé")
        service.is_running = False
    except Exception as e:
        logger.error(f"💥 Erreur fatale: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
