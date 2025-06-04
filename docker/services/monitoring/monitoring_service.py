#!/usr/bin/env python3
"""
Service de monitoring pour le système IDS distribué
Surveille la santé de tous les composants et génère des métriques
"""

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional
import requests
import redis
import psutil
from flask import Flask, jsonify, render_template_string

# Configuration du logging via variables d'environnement
log_level = getattr(logging, os.getenv('LOG_LEVEL', 'INFO').upper())
log_file = os.getenv('LOG_FILE', 'monitoring.log')
log_format = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logging.basicConfig(
    level=log_level,
    format=log_format,
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ServiceMonitor:
    """Moniteur pour un service spécifique"""
    
    def __init__(self, name: str, url: str, port: int, check_interval: int = 30):
        self.name = name
        self.url = url
        self.port = port
        self.check_interval = check_interval
        self.status = "unknown"
        self.last_check = None
        self.response_time = None
        self.error_count = 0
        self.total_checks = 0
        
    def check_health(self) -> Dict:
        """Vérifie la santé du service"""
        start_time = time.time()
        
        try:
            response = requests.get(f"{self.url}:{self.port}/health", timeout=5)
            response_time = (time.time() - start_time) * 1000  # en ms
            
            if response.status_code == 200:
                self.status = "healthy"
                self.response_time = response_time
                data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            else:
                self.status = "unhealthy"
                self.error_count += 1
                data = {"error": f"HTTP {response.status_code}"}
                
        except requests.exceptions.RequestException as e:
            self.status = "unreachable"
            self.error_count += 1
            self.response_time = None
            data = {"error": str(e)}
            
        self.last_check = datetime.now()
        self.total_checks += 1
        
        return {
            "service": self.name,
            "status": self.status,
            "response_time_ms": self.response_time,
            "last_check": self.last_check.isoformat(),
            "error_count": self.error_count,
            "total_checks": self.total_checks,
            "uptime_percentage": ((self.total_checks - self.error_count) / self.total_checks) * 100 if self.total_checks > 0 else 0,
            "data": data
        }

class SystemMonitor:
    """Moniteur système global"""
    
    def __init__(self):
        self.start_time = datetime.now()
        
    def get_system_metrics(self) -> Dict:
        """Collecte les métriques système"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Informations réseau
            net_io = psutil.net_io_counters()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "cpu": {
                    "usage_percent": cpu_percent,
                    "cores": psutil.cpu_count()
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "usage_percent": memory.percent,
                    "available_gb": round(memory.available / (1024**3), 2)
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "usage_percent": (disk.used / disk.total) * 100
                },
                "network": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv
                }
            }
        except Exception as e:
            logger.error(f"Erreur lors de la collecte des métriques système: {e}")
            return {"error": str(e)}

class RedisMonitor:
    """Moniteur Redis"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        
    def get_redis_metrics(self) -> Dict:
        """Collecte les métriques Redis"""
        try:
            info = self.redis_client.info()
            
            return {
                "connected_clients": info.get('connected_clients', 0),
                "used_memory_human": info.get('used_memory_human', '0B'),
                "used_memory_peak_human": info.get('used_memory_peak_human', '0B'),
                "total_commands_processed": info.get('total_commands_processed', 0),
                "instantaneous_ops_per_sec": info.get('instantaneous_ops_per_sec', 0),
                "keyspace_hits": info.get('keyspace_hits', 0),
                "keyspace_misses": info.get('keyspace_misses', 0),
                "uptime_in_seconds": info.get('uptime_in_seconds', 0),
                "redis_version": info.get('redis_version', 'unknown')
            }
        except Exception as e:
            logger.error(f"Erreur lors de la collecte des métriques Redis: {e}")
            return {"error": str(e)}

class MonitoringService:
    """Service principal de monitoring"""
    
    def __init__(self):
        # Configuration
        self.redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)
        self.system_monitor = SystemMonitor()
        self.redis_monitor = RedisMonitor(self.redis_client)
        
        # Services à monitorer
        self.service_monitors = {
            'packet-capture': ServiceMonitor('packet-capture', 'http://packet-capture', 9001),
            'feature-extractor': ServiceMonitor('feature-extractor', 'http://feature-extractor', 9002),
            'ml-api': ServiceMonitor('ml-api', 'http://ml-api', 5000),
            'alert-manager': ServiceMonitor('alert-manager', 'http://alert-manager', 9003),
            'backup-service': ServiceMonitor('backup-service', 'http://backup-service', 9004)
        }
        
        # Métriques globales
        self.global_metrics = {
            "packets_captured": 0,
            "features_extracted": 0,
            "alerts_generated": 0,
            "threats_detected": 0,
            "processing_rate": 0
        }
        
        # Flask app pour l'interface web
        self.app = Flask(__name__)
        self.setup_routes()
        
        # Thread de monitoring
        self.monitoring_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        self.running = False
        
    def setup_routes(self):
        """Configuration des routes Flask"""
        
        @self.app.route('/health')
        def health():
            return jsonify({"status": "healthy", "service": "monitoring"})
            
        @self.app.route('/metrics')
        def metrics():
            """API des métriques au format JSON"""
            return jsonify(self.get_all_metrics())
            
        @self.app.route('/')
        def dashboard():
            """Dashboard web de monitoring"""
            html_template = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>IDS Monitoring Dashboard</title>
                <meta http-equiv="refresh" content="30">
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    .metric-card { 
                        border: 1px solid #ddd; 
                        padding: 15px; 
                        margin: 10px; 
                        border-radius: 5px;
                        display: inline-block;
                        min-width: 200px;
                    }
                    .healthy { background-color: #d4edda; }
                    .unhealthy { background-color: #f8d7da; }
                    .unreachable { background-color: #fff3cd; }
                    .metric-value { font-size: 1.5em; font-weight: bold; }
                    h1, h2 { color: #333; }
                </style>
            </head>
            <body>
                <h1>🛡️ IDS Distributed Monitoring Dashboard</h1>
                
                <h2>Services Status</h2>
                <div id="services">
                    {% for service, status in services.items() %}
                    <div class="metric-card {{ status.status }}">
                        <h3>{{ service }}</h3>
                        <div class="metric-value">{{ status.status|upper }}</div>
                        <p>Response Time: {{ status.response_time_ms or 'N/A' }}ms</p>
                        <p>Uptime: {{ "%.1f"|format(status.uptime_percentage) }}%</p>
                    </div>
                    {% endfor %}
                </div>
                
                <h2>System Metrics</h2>
                <div class="metric-card">
                    <h3>CPU Usage</h3>
                    <div class="metric-value">{{ "%.1f"|format(system.cpu.usage_percent) }}%</div>
                </div>
                <div class="metric-card">
                    <h3>Memory Usage</h3>
                    <div class="metric-value">{{ "%.1f"|format(system.memory.usage_percent) }}%</div>
                    <p>{{ system.memory.used_gb }}GB / {{ system.memory.total_gb }}GB</p>
                </div>
                <div class="metric-card">
                    <h3>Disk Usage</h3>
                    <div class="metric-value">{{ "%.1f"|format(system.disk.usage_percent) }}%</div>
                    <p>{{ system.disk.used_gb }}GB / {{ system.disk.total_gb }}GB</p>
                </div>
                
                <h2>IDS Metrics</h2>
                <div class="metric-card">
                    <h3>Packets Captured</h3>
                    <div class="metric-value">{{ global_metrics.packets_captured }}</div>
                </div>
                <div class="metric-card">
                    <h3>Features Extracted</h3>
                    <div class="metric-value">{{ global_metrics.features_extracted }}</div>
                </div>
                <div class="metric-card">
                    <h3>Threats Detected</h3>
                    <div class="metric-value">{{ global_metrics.threats_detected }}</div>
                </div>
                <div class="metric-card">
                    <h3>Alerts Generated</h3>
                    <div class="metric-value">{{ global_metrics.alerts_generated }}</div>
                </div>
                
                <p><em>Page refreshed automatically every 30 seconds</em></p>
            </body>
            </html>
            '''
            
            metrics = self.get_all_metrics()
            return render_template_string(
                html_template,
                services=metrics['services'],
                system=metrics['system'],
                global_metrics=metrics['global_metrics']
            )
    
    def get_all_metrics(self) -> Dict:
        """Collecte toutes les métriques"""
        # Vérification des services
        service_status = {}
        for name, monitor in self.service_monitors.items():
            service_status[name] = monitor.check_health()
        
        # Métriques système
        system_metrics = self.system_monitor.get_system_metrics()
        
        # Métriques Redis
        redis_metrics = self.redis_monitor.get_redis_metrics()
        
        # Métriques globales depuis Redis
        try:
            self.global_metrics["packets_captured"] = int(self.redis_client.get("metrics:packets_captured") or 0)
            self.global_metrics["features_extracted"] = int(self.redis_client.get("metrics:features_extracted") or 0)
            self.global_metrics["alerts_generated"] = int(self.redis_client.get("metrics:alerts_generated") or 0)
            self.global_metrics["threats_detected"] = int(self.redis_client.get("metrics:threats_detected") or 0)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métriques globales: {e}")
        
        return {
            "timestamp": datetime.now().isoformat(),
            "services": service_status,
            "system": system_metrics,
            "redis": redis_metrics,
            "global_metrics": self.global_metrics
        }
    
    def monitoring_loop(self):
        """Boucle principale de monitoring"""
        logger.info("Démarrage de la boucle de monitoring")
        
        while self.running:
            try:
                # Collecte des métriques
                metrics = self.get_all_metrics()
                
                # Sauvegarde dans Redis pour historique
                self.redis_client.lpush("monitoring:history", json.dumps(metrics))
                self.redis_client.ltrim("monitoring:history", 0, 1000)  # Garde les 1000 dernières entrées
                
                # Publication pour d'autres services
                self.redis_client.publish("monitoring:metrics", json.dumps(metrics))
                
                # Détection d'anomalies
                self.detect_anomalies(metrics)
                
                time.sleep(30)  # Vérification toutes les 30 secondes
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de monitoring: {e}")
                time.sleep(10)
    
    def detect_anomalies(self, metrics: Dict):
        """Détecte les anomalies dans les métriques"""
        alerts = []
        
        # Vérification CPU
        if metrics["system"].get("cpu", {}).get("usage_percent", 0) > 90:
            alerts.append({
                "type": "system",
                "severity": "critical",
                "message": f"CPU usage critical: {metrics['system']['cpu']['usage_percent']}%"
            })
        
        # Vérification mémoire
        if metrics["system"].get("memory", {}).get("usage_percent", 0) > 90:
            alerts.append({
                "type": "system",
                "severity": "critical",
                "message": f"Memory usage critical: {metrics['system']['memory']['usage_percent']}%"
            })
        
        # Vérification services
        for service, status in metrics["services"].items():
            if status["status"] in ["unhealthy", "unreachable"]:
                alerts.append({
                    "type": "service",
                    "severity": "high",
                    "message": f"Service {service} is {status['status']}"
                })
        
        # Publication des alertes
        for alert in alerts:
            alert["timestamp"] = datetime.now().isoformat()
            self.redis_client.lpush("alerts:monitoring", json.dumps(alert))
            self.redis_client.publish("alerts:new", json.dumps(alert))
            logger.warning(f"Alerte générée: {alert['message']}")
    
    def start(self):
        """Démarre le service de monitoring"""
        self.running = True
        self.monitoring_thread.start()
        logger.info("Service de monitoring démarré")
        
        # Démarrage du serveur Flask
        self.app.run(host='0.0.0.0', port=9000, debug=False)
    
    def stop(self):
        """Arrête le service de monitoring"""
        self.running = False
        logger.info("Service de monitoring arrêté")

if __name__ == "__main__":
    service = MonitoringService()
    
    try:
        service.start()
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur")
        service.stop()
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        service.stop()
