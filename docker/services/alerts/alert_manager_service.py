#!/usr/bin/env python3
"""
Service de gestion d'alertes pour le système IDS distribué
Traite, classe et notifie les alertes de sécurité
"""

import json
import logging
import os
import smtplib
import threading
import time
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List
import redis
from flask import Flask, jsonify, request


# Configuration du logging
log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())
log_file = os.getenv('LOG_FILE', '/app/logs/alerts.log')
log_format = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
redis_host = os.getenv('REDIS_HOST', 'redis')
redis_port = int(os.getenv('REDIS_PORT', '6379'))
redis_db = int(os.getenv('REDIS_DB', '2'))
redis_password = os.getenv('REDIS_PASSWORD', None)

logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class AlertProcessor:
    """Processeur d'alertes avec classification et enrichissement"""
    
    SEVERITY_LEVELS = {
        'low': 1,
        'medium': 2,
        'high': 3,
        'critical': 4
    }
    
    ALERT_TYPES = {
        'intrusion': 'Tentative d\'intrusion détectée',
        'anomaly': 'Comportement anormal détecté',
        'system': 'Problème système',
        'network': 'Anomalie réseau',
        'malware': 'Malware potentiel détecté'
    }
    def __init__(self):
        self.processed_count = 0
        self.alert_history = []
        
        # Configuration des limites via variables d'environnement
        self.max_history = int(os.getenv('ALERT_HISTORY_LIMIT', '1000'))
        self.max_severity_score = int(os.getenv('MAX_SEVERITY_SCORE', '5'))
        self.repeated_alert_window_minutes = int(os.getenv('REPEATED_ALERT_WINDOW_MINUTES', '5'))
        self.repeated_alert_check_count = int(os.getenv('REPEATED_ALERT_CHECK_COUNT', '50'))
        
    def process_alert(self, alert_data: Dict) -> Dict:
        """Traite et enrichit une alerte"""
        try:
            # Validation des données
            if not self.validate_alert(alert_data):
                raise ValueError("Données d'alerte invalides")
            
            # Enrichissement de l'alerte
            enriched_alert = self.enrich_alert(alert_data)
            
            
            # Ajout des métadonnées
            enriched_alert.update({
                'id': f"alert_{int(time.time())}_{self.processed_count}",
                'processed_at': datetime.now().isoformat(),
                'status': 'new',
                'acknowledged': False,
                'false_positive': False
            })
            
            self.processed_count += 1
            self.alert_history.append(enriched_alert)
              # Garde seulement les alertes limitées en mémoire
            if len(self.alert_history) > self.max_history:
                self.alert_history = self.alert_history[-self.max_history:]
            
            logger.info(f"Alerte traitée: {enriched_alert['id']} - {enriched_alert['type']}")
            return enriched_alert
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement de l'alerte: {e}")
            return None
    
    def validate_alert(self, alert_data: Dict) -> bool:
        """Valide les données d'une alerte"""
        required_fields = ['type', 'message', 'timestamp']
        return all(field in alert_data for field in required_fields)
    
    def enrich_alert(self, alert_data: Dict) -> Dict:
        """Enrichit une alerte avec des informations supplémentaires"""
        enriched = alert_data.copy()
        
        # # Ajout de la description du type
        # enriched['type_description'] = self.ALERT_TYPES.get(
        #     alert_data.get('type', 'unknown'), 
        #     'Type d\'alerte inconnu'
        # )
        
        # # Normalisation de la sévérité
        # severity = alert_data.get('severity', 'medium').lower()
        # if severity not in self.SEVERITY_LEVELS:
        #     severity = 'medium'
        # enriched['severity'] = severity
        
        # # Ajout d'informations contextuelles
        # if 'source_ip' in alert_data:
        #     enriched['source_info'] = self.get_ip_info(alert_data['source_ip'])
        
        # if 'destination_ip' in alert_data:
        #     enriched['destination_info'] = self.get_ip_info(alert_data['destination_ip'])
        
        return enriched
    
    def calculate_severity_score(self, alert_data: Dict) -> int:
        """Calcule un score de sévérité basé sur plusieurs facteurs"""
        base_score = self.SEVERITY_LEVELS.get(alert_data.get('severity', 'medium'), 2)
        
        # Facteurs d'augmentation du score
        if alert_data.get('type') == 'intrusion':
            base_score += 1
        
        if alert_data.get('confidence', 0) > 0.9:
            base_score += 1
        
        if self.is_repeated_alert(alert_data):
            base_score += 1
        
        return min(base_score, self.max_severity_score)  # Score maximum configurable
    
    def get_ip_info(self, ip: str) -> Dict:
        """Récupère des informations sur une adresse IP"""
        # Simulation - dans un vrai système, on utiliserait une API de géolocalisation
        return {
            'ip': ip,
            'is_private': self.is_private_ip(ip),
            'country': 'Unknown',
            'organization': 'Unknown'
        }
    
    def is_private_ip(self, ip: str) -> bool:
        """Vérifie si une IP est privée"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            
            first = int(parts[0])
            second = int(parts[1])
            
            # Plages IP privées
            if first == 10:
                return True
            elif first == 172 and 16 <= second <= 31:
                return True
            elif first == 192 and second == 168:
                return True
            
            return False
        except:
            return False
    def is_repeated_alert(self, alert_data: Dict) -> bool:
        """Vérifie si c'est une alerte répétée"""
        current_time = datetime.now()
        time_window = timedelta(minutes=self.repeated_alert_window_minutes)
        
        for alert in self.alert_history[-self.repeated_alert_check_count:]:  # Check les dernières alertes configurables
            try:
                alert_time = datetime.fromisoformat(alert.get('timestamp', ''))
                if current_time - alert_time <= time_window:
                    if (alert.get('type') == alert_data.get('type') and
                        alert.get('source_ip') == alert_data.get('source_ip')):
                        return True
            except:
                continue
        
        return False

class NotificationManager:
    """Gestionnaire de notifications"""
    
    def __init__(self):
        # Configuration email via variables d'environnement
        self.email_config = {
            'smtp_server': os.getenv('SMTP_SERVER', 'localhost'),
            'smtp_port': int(os.getenv('SMTP_PORT', '587')),
            'username': os.getenv('SMTP_USERNAME', ''),
            'password': os.getenv('SMTP_PASSWORD', ''),
            'from_email': os.getenv('SMTP_FROM_EMAIL', 'ids-alerts@company.com'),
            'to_email': os.getenv('ALERT_EMAIL_RECIPIENT', 'admin@company.com')
        }
        
        # Configuration des règles de notification via variables d'environnement
        critical_methods = os.getenv('CRITICAL_NOTIFICATION_METHODS', 'email,sms').split(',')
        high_methods = os.getenv('HIGH_NOTIFICATION_METHODS', 'email').split(',')
        medium_methods = os.getenv('MEDIUM_NOTIFICATION_METHODS', 'dashboard').split(',')
        low_methods = os.getenv('LOW_NOTIFICATION_METHODS', 'dashboard').split(',')
        
        self.notification_rules = {
            'critical': [method.strip() for method in critical_methods],
            'high': [method.strip() for method in high_methods],
            'medium': [method.strip() for method in medium_methods],
            'low': [method.strip() for method in low_methods]
        }
        
    def send_notification(self, alert: Dict):
        """Envoie une notification basée sur la sévérité"""
        severity = alert.get('severity', 'medium')
        methods = self.notification_rules.get(severity, ['dashboard'])
        
        for method in methods:
            try:
                if method == 'email':
                    self.send_email_notification(alert)
                elif method == 'sms':
                    self.send_sms_notification(alert)
                elif method == 'dashboard':
                    self.send_dashboard_notification(alert)
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de notification {method}: {e}")
    
    def send_email_notification(self, alert: Dict):
        """Envoie une notification par email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['from_email']
            msg['To'] = self.email_config['to_email']
            msg['Subject'] = f"[IDS ALERT] {alert['severity'].upper()} - {alert['type']}"
            
            body = f"""
            ALERTE IDS DÉTECTÉE
            
            ID: {alert['id']}
            Type: {alert['type_description']}
            Sévérité: {alert['severity'].upper()}
            Score: {alert['severity_score']}/5
            
            Message: {alert['message']}
            
            Timestamp: {alert['timestamp']}
            Traité le: {alert['processed_at']}
            
            Détails supplémentaires:
            {json.dumps(alert, indent=2)}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Envoi (simulation)
            logger.info(f"Email d'alerte envoyé pour {alert['id']}")

            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['username'], self.email_config['password'])
                server.send_message(msg)

        except Exception as e:
            logger.error(f"Erreur lors de l'envoi d'email: {e}")
    
    def send_sms_notification(self, alert: Dict):
        """Envoie une notification par SMS"""
        # Simulation d'envoi SMS
        message = f"IDS ALERT: {alert['severity'].upper()} - {alert['type']} - {alert['message'][:100]}"
        logger.info(f"SMS d'alerte envoyé: {message}")
    
    def send_dashboard_notification(self, alert: Dict):
        """Envoie une notification vers le dashboard"""
        # Les alertes sont déjà stockées dans Redis, donc juste un log
        logger.info(f"Notification dashboard pour alerte {alert['id']}")

class AlertManagerService:
    """Service principal de gestion d'alertes"""
    
    def __init__(self):
        # Configuration Redis via variables d'environnement
       
        
        self.redis_client = redis.Redis(
            host=redis_host, 
            port=redis_port, 
            db=redis_db,
            password=redis_password,
            decode_responses=True
        )
        
        # Configuration du service via variables d'environnement
        self.flask_host = os.getenv('FLASK_HOST', '0.0.0.0')
        self.flask_port = int(os.getenv('FLASK_PORT', '9003'))
        self.flask_debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        
        # Configuration des limites Redis
        self.redis_alerts_limit = int(os.getenv('REDIS_ALERTS_LIMIT', '10000'))
        self.redis_severity_limit = int(os.getenv('REDIS_SEVERITY_LIMIT', '1000'))
        
        # Canaux d'écoute configurables
        alert_channels = os.getenv('ALERT_CHANNELS', 'ml,monitoring,network').split(',')
        self.alert_channels = [channel.strip() for channel in alert_channels]
        
        # Composants
        self.alert_processor = AlertProcessor()
        self.notification_manager = NotificationManager()
        
        # Flask app
        self.app = Flask(__name__)
        self.setup_routes()
        
        # Threads
        self.listener_thread = threading.Thread(target=self.listen_for_alerts, daemon=True)
        self.running = False
        
        # Statistiques
        self.stats = {
            'total_alerts': 0,
            'critical_alerts': 0,
            'high_alerts': 0,
            'medium_alerts': 0,
            'low_alerts': 0,
            'false_positives': 0,
            'acknowledged': 0
        }
    
    def setup_routes(self):
        """Configuration des routes Flask"""
        
        @self.app.route('/health')
        def health():
            return jsonify({
                "status": "healthy",
                "service": "alert-manager",
                "stats": self.stats
            })
        
        @self.app.route('/alerts')
        def get_alerts():
            """Récupère la liste des alertes"""
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 50)), int(os.getenv('MAX_ALERTS_PER_PAGE', '100')))
            severity = request.args.get('severity')
            status = request.args.get('status')
            
            alerts = self.filter_alerts(severity, status)
            
            # Pagination
            start = (page - 1) * per_page
            end = start + per_page
            
            return jsonify({
                'alerts': alerts[start:end],
                'total': len(alerts),
                'page': page,
                'per_page': per_page,
                'stats': self.stats
            })
        
        @self.app.route('/alerts/<alert_id>/acknowledge', methods=['POST'])
        def acknowledge_alert(alert_id):
            """Marque une alerte comme acquittée"""
            try:
                # Recherche de l'alerte
                for alert in self.alert_processor.alert_history:
                    if alert.get('id') == alert_id:
                        alert['acknowledged'] = True
                        alert['acknowledged_at'] = datetime.now().isoformat()
                        alert['acknowledged_by'] = request.json.get('user', 'unknown')
                        
                        # Mise à jour dans Redis
                        self.redis_client.hset(f"alert:{alert_id}", "acknowledged", "true")
                        self.stats['acknowledged'] += 1
                        
                        return jsonify({'status': 'success', 'message': 'Alerte acquittée'})
                
                return jsonify({'status': 'error', 'message': 'Alerte non trouvée'}), 404
                
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/alerts/<alert_id>/false-positive', methods=['POST'])
        def mark_false_positive(alert_id):
            """Marque une alerte comme faux positif"""
            try:
                for alert in self.alert_processor.alert_history:
                    if alert.get('id') == alert_id:
                        alert['false_positive'] = True
                        alert['marked_fp_at'] = datetime.now().isoformat()
                        alert['marked_fp_by'] = request.json.get('user', 'unknown')
                        
                        self.redis_client.hset(f"alert:{alert_id}", "false_positive", "true")
                        self.stats['false_positives'] += 1
                        
                        return jsonify({'status': 'success', 'message': 'Alerte marquée comme faux positif'})
                
                return jsonify({'status': 'error', 'message': 'Alerte non trouvée'}), 404
                
            except Exception as e:
                return jsonify({'status': 'error', 'message': str(e)}), 500
        
        @self.app.route('/stats')
        def get_stats():
            """Récupère les statistiques des alertes"""
            return jsonify(self.stats)
    
    def filter_alerts(self, severity=None, status=None) -> List[Dict]:
        """Filtre les alertes selon les critères"""
        alerts = self.alert_processor.alert_history.copy()
        
        if severity:
            alerts = [a for a in alerts if a.get('severity') == severity]
        
        if status:
            if status == 'acknowledged':
                alerts = [a for a in alerts if a.get('acknowledged', False)]
            elif status == 'new':
                alerts = [a for a in alerts if not a.get('acknowledged', False)]
            elif status == 'false_positive':
                alerts = [a for a in alerts if a.get('false_positive', False)]
        
        # Tri par timestamp décroissant
        alerts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return alerts
    
    def listen_for_alerts(self):
        """Écoute les alertes sur Redis"""
        logger.info("Démarrage de l'écoute des alertes")
          # Souscription aux canaux d'alertes configurables
        pubsub = self.redis_client.pubsub()
        for channel in self.alert_channels:
            pubsub.subscribe(channel)
        
        for message in pubsub.listen():
            if not self.running:
                break
                
            if message['type'] == 'message':
                try:
                    alert_data = json.loads(message['data'])
                    self.handle_alert(alert_data)
                except Exception as e:
                    logger.error(f"Erreur lors du traitement du message: {e}")
    
    def handle_alert(self, alert_data: Dict):
        """Traite une nouvelle alerte"""
        try:
            # Traitement de l'alerte
            processed_alert = self.alert_processor.process_alert(alert_data)
            
            if processed_alert:
                # Mise à jour des statistiques
                self.update_stats(processed_alert)
                
                # Sauvegarde dans Redis
                self.save_alert_to_redis(processed_alert)
                
                # Envoi de notifications
                self.notification_manager.send_notification(processed_alert)
                
                logger.info(f"Alerte {processed_alert['id']} traitée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement de l'alerte: {e}")
    
    def update_stats(self, alert: Dict):
        """Met à jour les statistiques"""
        self.stats['total_alerts'] += 1
        
        severity = alert.get('severity', 'medium')
        if severity in self.stats:
            self.stats[f'{severity}_alerts'] += 1
        
        # Sauvegarde des stats dans Redis
        for key, value in self.stats.items():
            self.redis_client.set(f"stats:alerts:{key}", value)
    
    def save_alert_to_redis(self, alert: Dict):
        """Sauvegarde une alerte dans Redis"""
        try:
            alert_id = alert['id']
            
            # Sauvegarde des détails
            self.redis_client.hset(f"alert:{alert_id}", mapping=alert)
              # Ajout à la liste des alertes
            self.redis_client.lpush("alerts:all", alert_id)
            self.redis_client.ltrim("alerts:all", 0, self.redis_alerts_limit)  # Garde les alertes configurables
            
            # Index par sévérité
            self.redis_client.lpush(f"alerts:severity:{alert['severity']}", alert_id)
            self.redis_client.ltrim(f"alerts:severity:{alert['severity']}", 0, self.redis_severity_limit)
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde dans Redis: {e}")
    
    def start(self):
        """Démarre le service"""
        self.running = True
        self.listener_thread.start()
        logger.info("Service de gestion d'alertes démarré")
          # Démarrage du serveur Flask
        self.app.run(host=self.flask_host, port=self.flask_port, debug=self.flask_debug)
    
    def stop(self):
        """Arrête le service"""
        self.running = False
        logger.info("Service de gestion d'alertes arrêté")

if __name__ == "__main__":
    service = AlertManagerService()
    
    try:
        service.start()
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")
        service.stop()
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        service.stop()
