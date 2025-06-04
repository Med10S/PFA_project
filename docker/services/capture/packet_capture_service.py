#!/usr/bin/env python3
"""
Service de Capture de Paquets Sécurisé
=====================================
Capture les paquets réseau et les envoie via Redis vers le service d'extraction
"""

import os
import sys
import json
import time
import redis
import logging
import hashlib
import threading
from datetime import datetime, timedelta
from scapy.all import sniff, AsyncSniffer, PcapWriter
from cryptography.fernet import Fernet
import signal
import psutil
from pathlib import Path

# Configuration
INTERFACE = os.getenv('INTERFACE', 'eth0')
CAPTURE_INTERVAL = int(os.getenv('CAPTURE_INTERVAL', '10'))  # secondes
BUFFER_SIZE = int(os.getenv('BUFFER_SIZE', '1000'))
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key())
REDIS_DB = int(os.getenv('REDIS_DB', '0'))

# Sécurité
PACKET_QUEUE = 'packet_queue'
STATUS_QUEUE = 'capture_status'
BACKUP_DIR = Path('/app/buffer')
SHARED_DIR = Path('/app/shared')

# Configuration logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/packet_capture.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SecurePacketCapture:
    """Service de capture de paquets sécurisé avec backup et chiffrement"""
    
    def __init__(self):
        self.redis_client = None
        self.cipher = Fernet(ENCRYPTION_KEY)
        self.is_running = True
        self.packet_buffer = []
        self.stats = {
            'packets_captured': 0,
            'packets_sent': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        self.backup_writer = None
        self.current_backup_file = None
        
        # Créer les répertoires
        BACKUP_DIR.mkdir(exist_ok=True)
        SHARED_DIR.mkdir(exist_ok=True)
        
        # Gestionnaire de signaux
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Gestionnaire d'arrêt propre"""
        logger.info(f"Signal {signum} reçu, arrêt en cours...")
        self.is_running = False
        
    def connect_redis(self):
        """Connexion sécurisée à Redis avec retry"""
        max_retries = 5
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                self.redis_client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    decode_responses=False,  # Pour les données binaires
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    password=REDIS_PASSWORD ,
                    retry_on_timeout=True,
                    health_check_interval=30,
                    db=REDIS_DB
                )
                
        
       
                
                # Test de connexion
                self.redis_client.ping()
                logger.info("Connexion Redis établie")
                return True
                
            except Exception as e:
                logger.error(f"Tentative {attempt + 1} - Erreur Redis: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    
        logger.error("Impossible de se connecter à Redis")
        return False
        
    def create_backup_file(self):
        """Crée un nouveau fichier de backup PCAP"""
        try:
            if self.backup_writer:
                self.backup_writer.close()
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.current_backup_file = BACKUP_DIR / f"capture_backup_{timestamp}.pcap"
            self.backup_writer = PcapWriter(str(self.current_backup_file))
            logger.info(f"Nouveau fichier backup: {self.current_backup_file}")
            
        except Exception as e:
            logger.error(f"Erreur création backup: {e}")
            
    def encrypt_packet_data(self, packet_data):
        """Chiffre les données de paquet"""
        try:
            packet_bytes = bytes(packet_data)
            encrypted = self.cipher.encrypt(packet_bytes)
            return encrypted
        except Exception as e:
            logger.error(f"Erreur chiffrement: {e}")
            return None
            
    def packet_handler(self, packet):
        """Traite chaque paquet capturé"""
        try:
            self.stats['packets_captured'] += 1
            
            # Backup local
            if self.backup_writer:
                self.backup_writer.write(packet)
                
            # Sérialisation du paquet
            packet_data = {
                'timestamp': time.time(),
                'length': len(packet),
                'raw_data': bytes(packet),
                'summary': packet.summary(),
                'capture_id': hashlib.md5(f"{time.time()}{len(packet)}".encode()).hexdigest()
            }
            
            # Chiffrement
            encrypted_data = self.encrypt_packet_data(json.dumps(packet_data, default=str).encode())
            if not encrypted_data:
                return
                
            # Ajout au buffer
            self.packet_buffer.append({
                'data': encrypted_data,
                'timestamp': packet_data['timestamp'],
                'size': len(encrypted_data)
            })
            
            # Envoi par batch
            if len(self.packet_buffer) >= BUFFER_SIZE:
                self.send_batch()
                
        except Exception as e:
            logger.error(f"Erreur traitement paquet: {e}")
            self.stats['errors'] += 1
            
    def send_batch(self):
        """Envoie un batch de paquets vers Redis"""
        if not self.packet_buffer or not self.redis_client:
            return
            
        try:
            batch_data = {
                'packets': self.packet_buffer,
                'batch_id': hashlib.md5(f"{time.time()}".encode()).hexdigest(),
                'timestamp': time.time(),
                'count': len(self.packet_buffer),
                'capture_node': os.getenv('HOSTNAME', 'unknown')
            }
            
            # Sérialisation et envoi
            batch_json = json.dumps(batch_data, default=str)
            
            # Envoi avec retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.redis_client.lpush(PACKET_QUEUE, batch_json)
                    self.stats['packets_sent'] += len(self.packet_buffer)
                    logger.info(f"Batch envoyé: {len(self.packet_buffer)} paquets")
                    break
                    
                except redis.ConnectionError as e:
                    logger.warning(f"Tentative {attempt + 1} - Erreur envoi: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        self.connect_redis()  # Reconnexion
                    else:
                        # Sauvegarde locale en cas d'échec
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
                
            logger.warning(f"Batch sauvegardé localement: {failed_file}")
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde locale: {e}")
            
    def send_status_update(self):
        """Envoie un update de statut"""
        try:
            status = {
                'node_id': os.getenv('HOSTNAME', 'capture-node'),
                'timestamp': time.time(),
                'stats': self.stats.copy(),
                'health': {
                    'cpu_percent': psutil.cpu_percent(),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_usage': psutil.disk_usage('/app').percent
                },
                'interface': INTERFACE,
                'buffer_size': len(self.packet_buffer)
            }
            
            # Calculer le débit
            uptime = (datetime.now() - self.stats['start_time']).total_seconds()
            if uptime > 0:
                status['packets_per_second'] = self.stats['packets_captured'] / uptime
                
            status_json = json.dumps(status, default=str)
            
            if self.redis_client:
                self.redis_client.lpush(STATUS_QUEUE, status_json)
                self.redis_client.expire(STATUS_QUEUE, 300)  # TTL 5 minutes
                
        except Exception as e:
            logger.error(f"Erreur envoi statut: {e}")
            
    def rotate_backup_files(self):
        """Rotation des fichiers de backup"""
        try:
            # Créer nouveau fichier backup toutes les heures
            self.create_backup_file()
            
            # Nettoyer les anciens fichiers (> 24h)
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            for backup_file in BACKUP_DIR.glob("capture_backup_*.pcap"):
                try:
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_time < cutoff_time:
                        backup_file.unlink()
                        logger.info(f"Ancien backup supprimé: {backup_file}")
                except Exception as e:
                    logger.error(f"Erreur suppression {backup_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Erreur rotation backup: {e}")
            
    def monitor_and_status(self):
        """Thread de monitoring et envoi de statut"""
        status_interval = 30  # secondes
        backup_rotation_interval = 3600  # 1 heure
        last_backup_rotation = time.time()
        
        while self.is_running:
            try:
                # Envoi statut
                self.send_status_update()
                
                # Rotation backup
                if time.time() - last_backup_rotation > backup_rotation_interval:
                    self.rotate_backup_files()
                    last_backup_rotation = time.time()
                    
                # Envoi buffer restant
                if self.packet_buffer:
                    self.send_batch()
                    
                time.sleep(status_interval)
                
            except Exception as e:
                logger.error(f"Erreur thread monitoring: {e}")
                time.sleep(5)
                
    def start_capture(self):
        """Démarre la capture de paquets"""
        logger.info(f"Démarrage capture sur interface {INTERFACE}")
        
        # Connexion Redis
        if not self.connect_redis():
            logger.error("Impossible de démarrer sans Redis")
            return False
            
        # Création fichier backup initial
        self.create_backup_file()
        
        # Thread de monitoring
        monitor_thread = threading.Thread(target=self.monitor_and_status)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        try:
            # Démarrage de la capture
            logger.info("Capture de paquets démarrée")
            sniff(
                iface=INTERFACE,
                prn=self.packet_handler,
                store=0,  # Ne pas stocker en mémoire
                stop_filter=lambda p: not self.is_running
            )
            
        except PermissionError:
            logger.error("Permissions insuffisantes pour la capture")
            return False
        except Exception as e:
            logger.error(f"Erreur capture: {e}")
            return False
        finally:
            self.cleanup()
            
        return True
        
    def cleanup(self):
        """Nettoyage avant arrêt"""
        logger.info("Nettoyage en cours...")
        
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
                
        logger.info("Nettoyage terminé")

def main():
    """Point d'entrée principal"""
    logger.info("=== SERVICE DE CAPTURE DE PAQUETS ===")
    logger.info(f"Interface: {INTERFACE}")
    logger.info(f"Intervalle: {CAPTURE_INTERVAL}s")
    logger.info(f"Buffer: {BUFFER_SIZE} paquets")
    
    # Vérification privilèges
    if os.geteuid() != 0:
        logger.error("Ce service nécessite des privilèges root")
        sys.exit(1)
        
    # Vérification interface
    import netifaces
    if INTERFACE not in netifaces.interfaces():
        logger.error(f"Interface {INTERFACE} non trouvée")
        logger.info(f"Interfaces disponibles: {netifaces.interfaces()}")
        sys.exit(1)
        
    # Démarrage service
    capture_service = SecurePacketCapture()
    
    try:
        success = capture_service.start_capture()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
