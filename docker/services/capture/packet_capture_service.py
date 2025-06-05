#!/usr/bin/env python3
"""
Service de Stockage de Paquets
=============================
Capture les paquets réseau complets et les stocke dans Redis pour traitement ultérieur
"""

import os
import sys
import json
import time
import redis
import logging
import hashlib
import threading
import signal
import psutil
import netifaces
from datetime import datetime, timedelta
from scapy.all import sniff, PcapWriter
from pathlib import Path
import base64
from flask import Flask, jsonify # Added Flask and jsonify

# Configuration
INTERFACE = os.getenv('INTERFACE', 'eth0')
BUFFER_SIZE = int(os.getenv('BUFFER_SIZE', '100'))  # Paquets par batch
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'SecureRedisPassword123!')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
NODE_ID = os.getenv('NODE_ID', 'packet-capture')
HEALTH_CHECK_PORT = int(os.getenv('HEALTH_CHECK_PORT', '9001')) # Added health check port

# Queues Redis
PACKET_QUEUE = 'packet_queue'
STATUS_QUEUE = 'capture_status'

# Répertoires
BACKUP_DIR = Path('/app/backup')

# Configuration logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/packet_storage.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PacketStorageService:
    """Service de stockage de paquets complets"""
    
    def __init__(self):
        self.redis_client = None
        self.is_running = True
        self.packet_buffer = []
        self.stats = {
            'packets_captured': 0,
            'packets_stored': 0,
            'batches_sent': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        self.backup_writer = None
        self.current_backup_file = None
        self.app = Flask(__name__) # Added Flask app initialization
        self._setup_health_check_route() # Added setup for health check route
        
        # Créer les répertoires
        BACKUP_DIR.mkdir(exist_ok=True)
        
        # Gestionnaire de signaux
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Gestionnaire d'arrêt propre"""
        logger.info(f"Signal {signum} reçu, arrêt en cours...")
        self.is_running = False
        
    def connect_redis(self):
        """Connexion à Redis avec retry"""
        max_retries = 5
        retry_delay = 1
        
        logger.info(f"🔧 Configuration Redis:")
        logger.info(f"   - Host: {REDIS_HOST}:{REDIS_PORT}")
        logger.info(f"   - DB: {REDIS_DB}")
        logger.info(f"   - Password: {'***' if REDIS_PASSWORD else 'None'}")
        
        for attempt in range(max_retries):
            try:
                self.redis_client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    decode_responses=False,
                    socket_connect_timeout=15,
                    socket_timeout=30,
                    db=REDIS_DB,
                    password=REDIS_PASSWORD,
                    max_connections=10
                )
                
                # Test de connexion
                self.redis_client.ping()
                logger.info(f"✅ Connexion Redis établie (tentative {attempt + 1})")
                return True
                
            except Exception as e:
                logger.error(f"❌ Tentative {attempt + 1} - Erreur Redis: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    
        logger.error("💥 Impossible de se connecter à Redis")
        return False
        
    def create_backup_file(self):
        """Crée un nouveau fichier de backup PCAP"""
        try:
            if self.backup_writer:
                self.backup_writer.close()
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_backup_file = BACKUP_DIR / f"packets_backup_{timestamp}.pcap"
            self.backup_writer = PcapWriter(str(self.current_backup_file))
            logger.info(f"📁 Nouveau fichier backup: {self.current_backup_file}")
            
        except Exception as e:
            logger.error(f"Erreur création backup: {e}")
            
    def packet_handler(self, packet):
        """Traite chaque paquet capturé - STOCKAGE COMPLET"""
        try:
            self.stats['packets_captured'] += 1
            
            # Backup local PCAP
            if self.backup_writer:
                self.backup_writer.write(packet)
            
            # Conversion complète du paquet pour stockage
            packet_data = {
                'timestamp': time.time(),
                'capture_time': packet.time if hasattr(packet, 'time') else time.time(),
                'length': len(packet),
                'interface': INTERFACE,
                'node_id': NODE_ID,
                
                # DONNÉES COMPLÈTES DU PAQUET
                'raw_bytes': base64.b64encode(bytes(packet)).decode('ascii'),
                'packet_summary': packet.summary(),
                
                # Métadonnées utiles
                'packet_id': hashlib.md5(f"{time.time()}{len(packet)}{packet.summary()}".encode()).hexdigest(),
                'protocol_stack': self._extract_protocol_stack(packet),
                'packet_layers': [layer.name for layer in packet.layers()],
                
                # Informations de base (optionnel pour analyse rapide)
                'basic_info': self._extract_basic_info(packet)
            }
            
            # Ajout au buffer
            self.packet_buffer.append(packet_data)
            
            # Envoi par batch
            if len(self.packet_buffer) >= BUFFER_SIZE:
                self.send_batch()
                
        except Exception as e:
            logger.error(f"Erreur traitement paquet: {e}")
            self.stats['errors'] += 1
            
    def _extract_protocol_stack(self, packet):
        """Extrait la pile de protocoles"""
        try:
            protocols = []
            layer = packet
            while layer:
                protocols.append(layer.__class__.__name__)
                layer = layer.payload if hasattr(layer, 'payload') and layer.payload else None
            return protocols
        except:
            return []
            
    def _extract_basic_info(self, packet):
        """Extrait quelques informations de base pour indexation rapide"""
        try:
            info = {
                'src_ip': None,
                'dst_ip': None,
                'src_port': None,
                'dst_port': None,
                'protocol': None
            }
            
            # IP Layer
            if packet.haslayer('IP'):
                info['src_ip'] = packet['IP'].src
                info['dst_ip'] = packet['IP'].dst
                info['protocol'] = packet['IP'].proto
                
            # TCP/UDP Layer
            if packet.haslayer('TCP'):
                info['src_port'] = packet['TCP'].sport
                info['dst_port'] = packet['TCP'].dport
            elif packet.haslayer('UDP'):
                info['src_port'] = packet['UDP'].sport
                info['dst_port'] = packet['UDP'].dport
                
            return info
        except:
            return {}
            
    def send_batch(self):
        """Envoie un batch de paquets complets vers Redis"""
        if not self.packet_buffer or not self.redis_client:
            return
            
        try:
            batch_data = {
                'batch_id': hashlib.md5(f"{time.time()}{len(self.packet_buffer)}".encode()).hexdigest(),
                'timestamp': time.time(),
                'node_id': NODE_ID,
                'interface': INTERFACE,
                'packet_count': len(self.packet_buffer),
                'packets': self.packet_buffer  # PAQUETS COMPLETS
            }
            
            # Sérialisation et envoi
            batch_json = json.dumps(batch_data, default=str)
            
            # Envoi avec retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.redis_client.lpush(PACKET_QUEUE, batch_json)
                    self.stats['packets_stored'] += len(self.packet_buffer)
                    self.stats['batches_sent'] += 1
                    logger.info(f"📦 Batch envoyé: {len(self.packet_buffer)} paquets complets")
                    break
                    
                except redis.ConnectionError as e:
                    logger.warning(f"Tentative {attempt + 1} - Erreur envoi: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        self.connect_redis()
                    else:
                        self.save_failed_batch(batch_data)
                        
            # Vider le buffer
            self.packet_buffer.clear()
            
        except Exception as e:
            logger.error(f"Erreur envoi batch: {e}")
            self.save_failed_batch({'packets': self.packet_buffer})
            self.packet_buffer.clear()
            
    def save_failed_batch(self, batch_data):
        """Sauvegarde locale en cas d'échec d'envoi"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            failed_file = BACKUP_DIR / f"failed_batch_{timestamp}.json"
            
            with open(failed_file, 'w') as f:
                json.dump(batch_data, f, default=str)
                
            logger.warning(f"⚠️ Batch sauvegardé localement: {failed_file}")
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde locale: {e}")
            
    def send_status_update(self):
        """Envoie un update de statut"""
        try:
            status = {
                'node_id': NODE_ID,
                'timestamp': time.time(),
                'stats': self.stats.copy(),
                'health': {
                    'cpu_percent': psutil.cpu_percent(),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_usage': psutil.disk_usage('/app').percent
                },
                'interface': INTERFACE,
                'buffer_size': len(self.packet_buffer),
                'queue_size': self.redis_client.llen(PACKET_QUEUE) if self.redis_client else 0
            }
            
            # Calculer le débit
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
            if uptime > 0:
                status['packets_per_second'] = self.stats['packets_captured'] / uptime
                status['storage_rate'] = self.stats['packets_stored'] / uptime
                
            status_json = json.dumps(status, default=str)
            
            if self.redis_client:
                self.redis_client.lpush(STATUS_QUEUE, status_json)
                self.redis_client.expire(STATUS_QUEUE, 300)
                
        except Exception as e:
            logger.error(f"Erreur envoi statut: {e}")
            
    def _setup_health_check_route(self):
        @self.app.route('/health', methods=['GET'])
        def health_check():
            # Basic health check: service is running and can connect to Redis
            redis_ok = False
            if self.redis_client:
                try:
                    self.redis_client.ping()
                    redis_ok = True
                except redis.exceptions.ConnectionError:
                    redis_ok = False
            
            status_code = 200 if self.is_running and redis_ok else 503
            return jsonify({
                "status": "healthy" if self.is_running and redis_ok else "unhealthy",
                "service_status": "running" if self.is_running else "stopped",
                "redis_connection": "ok" if redis_ok else "error",
                "node_id": NODE_ID,
                "timestamp": datetime.now().isoformat()
            }), status_code

    def _start_flask_app(self):
        """Starts the Flask app in a separate thread for the health check."""
        flask_thread = threading.Thread(target=lambda: self.app.run(host='0.0.0.0', port=HEALTH_CHECK_PORT, debug=False), daemon=True)
        flask_thread.start()
        logger.info(f"🩺 Health check endpoint running on port {HEALTH_CHECK_PORT}")

    def rotate_backup_files(self):
        """Rotation des fichiers de backup"""
        try:
            self.create_backup_file()
            
            # Nettoyer les anciens fichiers (> 24h)
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            for backup_file in BACKUP_DIR.glob("packets_backup_*.pcap"):
                try:
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_time < cutoff_time:
                        backup_file.unlink()
                        logger.info(f"🗑️ Ancien backup supprimé: {backup_file}")
                except Exception as e:
                    logger.error(f"Erreur suppression {backup_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Erreur rotation backup: {e}")
            
    def monitoring_loop(self):
        """Thread de monitoring"""
        backup_rotation_interval = 3600  # 1 heure
        last_backup_rotation = time.time()
        
        while self.is_running:
            try:
                # Envoi statut toutes les 30 secondes
                self.send_status_update()
                
                # Rotation backup toutes les heures
                if time.time() - last_backup_rotation > backup_rotation_interval:
                    self.rotate_backup_files()
                    last_backup_rotation = time.time()
                    
                # Envoi buffer restant
                if self.packet_buffer:
                    self.send_batch()
                    
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Erreur thread monitoring: {e}")
                time.sleep(5)
                
    def start_capture(self):
        """Démarre la capture et le stockage de paquets"""
        logger.info("🚀 === SERVICE DE STOCKAGE DE PAQUETS ===")
        logger.info(f"📡 Interface: {INTERFACE}")
        logger.info(f"📦 Taille buffer: {BUFFER_SIZE} paquets")
        
        # Connexion Redis
        if not self.connect_redis():
            logger.error("💥 Impossible de démarrer sans Redis")
            return False
            
        # Création fichier backup initial
        self.create_backup_file()
        
        # Thread de monitoring
        monitor_thread = threading.Thread(target=self.monitoring_loop)
        monitor_thread.daemon = True
        monitor_thread.start()

        # Start Flask app for health check
        self._start_flask_app() # Added call to start Flask app
        
        try:
            logger.info("🎯 Capture de paquets démarrée - STOCKAGE COMPLET")
            
            # Démarrage de la capture
            sniff(
                iface=INTERFACE,
                prn=self.packet_handler,
                store=0,  # Ne pas stocker en mémoire
                stop_filter=lambda p: not self.is_running
            )
            
        except PermissionError:
            logger.error("❌ Permissions insuffisantes pour la capture")
            return False
        except Exception as e:
            logger.error(f"❌ Erreur capture: {e}")
            return False
        finally:
            self.cleanup()
            
        return True
        
    def cleanup(self):
        """Nettoyage avant arrêt"""
        logger.info("🧹 Nettoyage en cours...")
        
        # Envoi buffer restant
        if self.packet_buffer:
            self.send_batch()
            
        # Fermeture fichier backup
        if self.backup_writer:
            self.backup_writer.close()
            
        # Fermeture Redis
        if self.redis_client:
            try:
                self.redis_client.close()
            except:
                pass
                
        logger.info("✅ Nettoyage terminé")

def main():
    """Point d'entrée principal"""
    logger.info("🚀 === SERVICE DE STOCKAGE DE PAQUETS ===")
    logger.info(f"📡 Interface: {INTERFACE}")
    logger.info(f"📦 Buffer: {BUFFER_SIZE} paquets")
    logger.info(f"🗄️ Redis: {REDIS_HOST}:{REDIS_PORT}")
    
    # Vérification privilèges
    if os.geteuid() != 0:
        logger.error("❌ Ce service nécessite des privilèges root")
        sys.exit(1)
        
    # Vérification interface
    if INTERFACE not in netifaces.interfaces():
        logger.error(f"❌ Interface {INTERFACE} non trouvée")
        logger.info(f"Interfaces disponibles: {netifaces.interfaces()}")
        sys.exit(1)
        
    # Démarrage service
    storage_service = PacketStorageService()
    
    try:
        success = storage_service.start_capture()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("🛑 Arrêt demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"💥 Erreur fatale: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
