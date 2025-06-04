#!/usr/bin/env python3
"""
Service de backup pour le système IDS distribué
Gère la sauvegarde et la restauration des données critiques
"""

import json
import logging
import os
import shutil
import threading
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import redis
from flask import Flask, jsonify, request, send_file

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/backup.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class BackupManager:
    """Gestionnaire principal des sauvegardes"""
    
    def __init__(self, backup_dir: str = "/app/backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.retention_days = 30
        self.max_backup_size_gb = 10
        
        # Types de données à sauvegarder
        self.backup_types = {
            'alerts': self.backup_alerts,
            'metrics': self.backup_metrics,
            'logs': self.backup_logs,
            'configs': self.backup_configs,
            'pcap': self.backup_pcap_files
        }
        
        # Statistiques
        self.stats = {
            'total_backups': 0,
            'successful_backups': 0,
            'failed_backups': 0,
            'total_size_gb': 0,
            'last_backup': None,
            'last_cleanup': None
        }
    
    def create_backup(self, backup_type: str = 'full', include_types: List[str] = None) -> Dict:
        """Crée une sauvegarde"""
        try:
            backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path = self.backup_dir / backup_id
            backup_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Démarrage de la sauvegarde {backup_id}")
            
            # Déterminer les types à sauvegarder
            if backup_type == 'full':
                types_to_backup = list(self.backup_types.keys())
            else:
                types_to_backup = include_types or [backup_type]
            
            backup_info = {
                'id': backup_id,
                'type': backup_type,
                'started_at': datetime.now().isoformat(),
                'status': 'in_progress',
                'included_types': types_to_backup,
                'files': [],
                'size_bytes': 0,
                'errors': []
            }
            
            # Exécution des sauvegardes
            for backup_type_name in types_to_backup:
                if backup_type_name in self.backup_types:
                    try:
                        result = self.backup_types[backup_type_name](backup_path)
                        backup_info['files'].extend(result.get('files', []))
                        backup_info['size_bytes'] += result.get('size_bytes', 0)
                    except Exception as e:
                        error_msg = f"Erreur lors de la sauvegarde {backup_type_name}: {e}"
                        backup_info['errors'].append(error_msg)
                        logger.error(error_msg)
            
            # Compression de la sauvegarde
            compressed_path = self.compress_backup(backup_path)
            if compressed_path:
                # Suppression du dossier non compressé
                shutil.rmtree(backup_path)
                backup_info['compressed_file'] = str(compressed_path)
                backup_info['compressed_size'] = compressed_path.stat().st_size
            
            # Finalisation
            backup_info['completed_at'] = datetime.now().isoformat()
            backup_info['status'] = 'completed' if not backup_info['errors'] else 'completed_with_errors'
            backup_info['duration_seconds'] = (
                datetime.fromisoformat(backup_info['completed_at']) - 
                datetime.fromisoformat(backup_info['started_at'])
            ).total_seconds()
            
            # Sauvegarde des métadonnées
            self.save_backup_metadata(backup_info)
            
            # Mise à jour des statistiques
            self.update_stats(backup_info)
            
            logger.info(f"Sauvegarde {backup_id} terminée: {backup_info['status']}")
            return backup_info
            
        except Exception as e:
            logger.error(f"Erreur fatale lors de la sauvegarde: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def backup_alerts(self, backup_path: Path) -> Dict:
        """Sauvegarde les alertes"""
        try:
            alerts_dir = backup_path / 'alerts'
            alerts_dir.mkdir(exist_ok=True)
            
            redis_host = os.getenv('REDIS_HOST', 'redis')
            redis_port = int(os.getenv('REDIS_PORT', '6379'))
            redis_db = int(os.getenv('REDIS_DB', '0'))
            redis_password = os.getenv('REDIS_PASSWORD', None)
            redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True
            )            
            # Sauvegarde des alertes actives
            alert_ids = redis_client.lrange("alerts:all", 0, -1)
            alerts_data = []
            
            for alert_id in alert_ids:
                alert_data = redis_client.hgetall(f"alert:{alert_id}")
                if alert_data:
                    alerts_data.append(alert_data)
            
            alerts_file = alerts_dir / 'alerts.json'
            with open(alerts_file, 'w') as f:
                json.dump(alerts_data, f, indent=2)
            
            # Sauvegarde des statistiques d'alertes
            stats_keys = redis_client.keys("stats:alerts:*")
            stats_data = {}
            for key in stats_keys:
                stats_data[key] = redis_client.get(key)
            
            stats_file = alerts_dir / 'alert_stats.json'
            with open(stats_file, 'w') as f:
                json.dump(stats_data, f, indent=2)
            
            total_size = alerts_file.stat().st_size + stats_file.stat().st_size
            
            return {
                'files': [str(alerts_file), str(stats_file)],
                'size_bytes': total_size,
                'count': len(alerts_data)
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des alertes: {e}")
            raise
    
    def backup_metrics(self, backup_path: Path) -> Dict:
        """Sauvegarde les métriques"""
        try:
            metrics_dir = backup_path / 'metrics'
            metrics_dir.mkdir(exist_ok=True)
            
            redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
            
            # Sauvegarde de l'historique de monitoring
            monitoring_history = redis_client.lrange("monitoring:history", 0, -1)
            metrics_data = [json.loads(entry) for entry in monitoring_history]
            
            metrics_file = metrics_dir / 'monitoring_history.json'
            with open(metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2)
            
            # Sauvegarde des métriques globales
            global_metrics = {}
            metric_keys = redis_client.keys("metrics:*")
            for key in metric_keys:
                global_metrics[key] = redis_client.get(key)
            
            global_file = metrics_dir / 'global_metrics.json'
            with open(global_file, 'w') as f:
                json.dump(global_metrics, f, indent=2)
            
            total_size = metrics_file.stat().st_size + global_file.stat().st_size
            
            return {
                'files': [str(metrics_file), str(global_file)],
                'size_bytes': total_size,
                'count': len(metrics_data)
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des métriques: {e}")
            raise
    
    def backup_logs(self, backup_path: Path) -> Dict:
        """Sauvegarde les fichiers de logs"""
        try:
            logs_dir = backup_path / 'logs'
            logs_dir.mkdir(exist_ok=True)
            
            log_files = []
            total_size = 0
            
            # Répertoires de logs à sauvegarder
            log_dirs = ['/app/logs', '/app/shared/logs']
            
            for log_dir in log_dirs:
                if os.path.exists(log_dir):
                    for log_file in Path(log_dir).glob('*.log'):
                        if log_file.is_file():
                            dest_file = logs_dir / log_file.name
                            shutil.copy2(log_file, dest_file)
                            log_files.append(str(dest_file))
                            total_size += dest_file.stat().st_size
            
            return {
                'files': log_files,
                'size_bytes': total_size,
                'count': len(log_files)
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des logs: {e}")
            raise
    
    def backup_configs(self, backup_path: Path) -> Dict:
        """Sauvegarde les fichiers de configuration"""
        try:
            configs_dir = backup_path / 'configs'
            configs_dir.mkdir(exist_ok=True)
            
            config_files = []
            total_size = 0
            
            # Fichiers de configuration à sauvegarder
            config_paths = [
                '/app/docker-compose.yml',
                '/app/.env',
                '/app/nginx.conf'
            ]
            
            for config_path in config_paths:
                if os.path.exists(config_path):
                    config_file = Path(config_path)
                    dest_file = configs_dir / config_file.name
                    shutil.copy2(config_file, dest_file)
                    config_files.append(str(dest_file))
                    total_size += dest_file.stat().st_size
            
            return {
                'files': config_files,
                'size_bytes': total_size,
                'count': len(config_files)
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des configs: {e}")
            raise
    
    def backup_pcap_files(self, backup_path: Path) -> Dict:
        """Sauvegarde les fichiers PCAP récents"""
        try:
            pcap_dir = backup_path / 'pcap'
            pcap_dir.mkdir(exist_ok=True)
            
            pcap_files = []
            total_size = 0
            
            # Répertoires PCAP à sauvegarder
            pcap_dirs = ['/app/shared/pcap', '/app/buffer']
            
            # Sauvegarder seulement les fichiers des dernières 24h
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            for pcap_source_dir in pcap_dirs:
                if os.path.exists(pcap_source_dir):
                    for pcap_file in Path(pcap_source_dir).glob('*.pcap'):
                        if pcap_file.is_file():
                            # Vérifier l'âge du fichier
                            file_time = datetime.fromtimestamp(pcap_file.stat().st_mtime)
                            if file_time >= cutoff_time:
                                dest_file = pcap_dir / pcap_file.name
                                shutil.copy2(pcap_file, dest_file)
                                pcap_files.append(str(dest_file))
                                total_size += dest_file.stat().st_size
            
            return {
                'files': pcap_files,
                'size_bytes': total_size,
                'count': len(pcap_files)
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des fichiers PCAP: {e}")
            raise
    
    def compress_backup(self, backup_path: Path) -> Optional[Path]:
        """Compresse une sauvegarde"""
        try:
            compressed_path = backup_path.with_suffix('.zip')
            
            with zipfile.ZipFile(compressed_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in backup_path.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(backup_path)
                        zipf.write(file_path, arcname)
            
            logger.info(f"Sauvegarde compressée: {compressed_path}")
            return compressed_path
            
        except Exception as e:
            logger.error(f"Erreur lors de la compression: {e}")
            return None
    
    def save_backup_metadata(self, backup_info: Dict):
        """Sauvegarde les métadonnées d'une sauvegarde"""
        try:
            metadata_file = self.backup_dir / f"{backup_info['id']}.json"
            with open(metadata_file, 'w') as f:
                json.dump(backup_info, f, indent=2)
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des métadonnées: {e}")
    
    def update_stats(self, backup_info: Dict):
        """Met à jour les statistiques"""
        self.stats['total_backups'] += 1
        
        if backup_info['status'] in ['completed', 'completed_with_errors']:
            self.stats['successful_backups'] += 1
        else:
            self.stats['failed_backups'] += 1
        
        if 'compressed_size' in backup_info:
            size_gb = backup_info['compressed_size'] / (1024**3)
            self.stats['total_size_gb'] += size_gb
        
        self.stats['last_backup'] = backup_info['completed_at']
    
    def cleanup_old_backups(self):
        """Nettoie les anciennes sauvegardes"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            cleaned_count = 0
            freed_space = 0
            
            for backup_file in self.backup_dir.glob('backup_*.zip'):
                if backup_file.is_file():
                    file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        file_size = backup_file.stat().st_size
                        backup_file.unlink()
                        
                        # Supprimer aussi le fichier de métadonnées
                        metadata_file = backup_file.with_suffix('.json')
                        if metadata_file.exists():
                            metadata_file.unlink()
                        
                        cleaned_count += 1
                        freed_space += file_size
            
            self.stats['last_cleanup'] = datetime.now().isoformat()
            
            if cleaned_count > 0:
                freed_gb = freed_space / (1024**3)
                logger.info(f"Nettoyage terminé: {cleaned_count} sauvegardes supprimées, {freed_gb:.2f} GB libérés")
            
            return {
                'cleaned_count': cleaned_count,
                'freed_space_gb': freed_space / (1024**3)
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")
            return {'error': str(e)}
    
    def list_backups(self) -> List[Dict]:
        """Liste les sauvegardes disponibles"""
        backups = []
        
        for metadata_file in self.backup_dir.glob('backup_*.json'):
            try:
                with open(metadata_file, 'r') as f:
                    backup_info = json.load(f)
                    
                # Ajouter des informations sur le fichier
                backup_file = metadata_file.with_suffix('.zip')
                if backup_file.exists():
                    backup_info['file_exists'] = True
                    backup_info['file_size_gb'] = backup_file.stat().st_size / (1024**3)
                else:
                    backup_info['file_exists'] = False
                
                backups.append(backup_info)
                
            except Exception as e:
                logger.error(f"Erreur lors de la lecture des métadonnées {metadata_file}: {e}")
        
        # Tri par date décroissante
        backups.sort(key=lambda x: x.get('started_at', ''), reverse=True)
        return backups

class BackupService:
    """Service principal de backup"""
    
    def __init__(self):
        self.backup_manager = BackupManager()
        
        # Flask app
        self.app = Flask(__name__)
        self.setup_routes()
        
        # Thread de sauvegarde automatique
        self.auto_backup_thread = threading.Thread(target=self.auto_backup_loop, daemon=True)
        self.running = False
        
        # Configuration de la sauvegarde automatique
        self.auto_backup_interval_hours = 6
        self.auto_cleanup_interval_hours = 24
        
    def setup_routes(self):
        """Configuration des routes Flask"""
        
        @self.app.route('/health')
        def health():
            return jsonify({
                "status": "healthy",
                "service": "backup-service",
                "stats": self.backup_manager.stats
            })
        
        @self.app.route('/backup', methods=['POST'])
        def create_backup():
            """Crée une nouvelle sauvegarde"""
            data = request.get_json() or {}
            backup_type = data.get('type', 'full')
            include_types = data.get('include_types')
            
            result = self.backup_manager.create_backup(backup_type, include_types)
            return jsonify(result)
        
        @self.app.route('/backups')
        def list_backups():
            """Liste les sauvegardes disponibles"""
            backups = self.backup_manager.list_backups()
            return jsonify({
                'backups': backups,
                'count': len(backups),
                'stats': self.backup_manager.stats
            })
        
        @self.app.route('/backups/<backup_id>/download')
        def download_backup(backup_id):
            """Télécharge une sauvegarde"""
            backup_file = self.backup_manager.backup_dir / f"{backup_id}.zip"
            
            if backup_file.exists():
                return send_file(
                    backup_file,
                    as_attachment=True,
                    download_name=f"{backup_id}.zip"
                )
            else:
                return jsonify({'error': 'Sauvegarde non trouvée'}), 404
        
        @self.app.route('/cleanup', methods=['POST'])
        def cleanup_backups():
            """Lance le nettoyage des anciennes sauvegardes"""
            result = self.backup_manager.cleanup_old_backups()
            return jsonify(result)
        
        @self.app.route('/stats')
        def get_stats():
            """Récupère les statistiques de sauvegarde"""
            return jsonify(self.backup_manager.stats)
    
    def auto_backup_loop(self):
        """Boucle de sauvegarde automatique"""
        logger.info("Démarrage de la sauvegarde automatique")
        
        last_backup = datetime.now()
        last_cleanup = datetime.now()
        
        while self.running:
            try:
                current_time = datetime.now()
                
                # Sauvegarde automatique
                if (current_time - last_backup).total_seconds() >= self.auto_backup_interval_hours * 3600:
                    logger.info("Démarrage de la sauvegarde automatique")
                    result = self.backup_manager.create_backup('full')
                    
                    if result.get('status') in ['completed', 'completed_with_errors']:
                        logger.info("Sauvegarde automatique terminée avec succès")
                    else:
                        logger.error(f"Erreur lors de la sauvegarde automatique: {result}")
                    
                    last_backup = current_time
                
                # Nettoyage automatique
                if (current_time - last_cleanup).total_seconds() >= self.auto_cleanup_interval_hours * 3600:
                    logger.info("Démarrage du nettoyage automatique")
                    cleanup_result = self.backup_manager.cleanup_old_backups()
                    logger.info(f"Nettoyage automatique terminé: {cleanup_result}")
                    last_cleanup = current_time
                
                time.sleep(300)  # Vérification toutes les 5 minutes
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de sauvegarde automatique: {e}")
                time.sleep(60)
    
    def start(self):
        """Démarre le service"""
        self.running = True
        self.auto_backup_thread.start()
        logger.info("Service de backup démarré")
        
        # Démarrage du serveur Flask
        self.app.run(host='0.0.0.0', port=9004, debug=False)
    
    def stop(self):
        """Arrête le service"""
        self.running = False
        logger.info("Service de backup arrêté")

if __name__ == "__main__":
    service = BackupService()
    
    try:
        service.start()
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")
        service.stop()
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        service.stop()
