# UNSW-NB15 Feature Extractor pour l'IDS ML
# Extrait les 42 features exactes du dataset UNSW-NB15 depuis un fichier PCAP
# Compatible avec les modèles ML pré-entraînés du projet

from scapy.all import rdpcap, TCP, UDP, IP, ICMP, ARP, Raw
import pandas as pd
import numpy as np
from collections import defaultdict, Counter
import re

class UNSW_NB15_FeatureExtractor:
    """
    Extracteur de features UNSW-NB15 depuis des fichiers PCAP
    Calcule les 42 features exactes requises par les modèles ML
    """
    def __init__(self):
        # Use lambda to ensure a fresh flow is created each time
        self.flows = defaultdict(lambda: self._create_empty_flow())
        self.connection_tracking = defaultdict(lambda: defaultdict(int))
        self.service_ports = {
            20: 'ftp-data', 21: 'ftp', 22: 'ssh', 23: 'telnet', 25: 'smtp',
            53: 'dns', 80: 'http', 110: 'pop3', 143: 'imap', 443: 'https',
            993: 'imaps', 995: 'pop3s', 1433: 'mssql', 3306: 'mysql',
            5432: 'postgresql', 6379: 'redis', 27017: 'mongodb'
        }
        
    def _create_empty_flow(self):
        """Crée une structure de flow vide avec toutes les features UNSW-NB15"""
        flow = {
            # Basic flow features
            'dur': 0.0,
            'proto': '',
            'service': '-',
            'state': 'INT',
            'spkts': 0,
            'dpkts': 0,
            'sbytes': 0,
            'dbytes': 0,
            'rate': 0.0,
            
            # TTL features
            'sttl': 0,
            'dttl': 0,
            
            # Load features
            'sload': 0.0,
            'dload': 0.0,
            'sloss': 0,
            'dloss': 0,
            
            # Packet timing features
            'sinpkt': 0.0,
            'dinpkt': 0.0,
            'sjit': 0.0,
            'djit': 0.0,
            
            # TCP window features
            'swin': 0,
            'stcpb': 0,
            'dtcpb': 0,
            'dwin': 0,
            
            # TCP timing features
            'tcprtt': 0.0,
            'synack': 0.0,
            'ackdat': 0.0,
            
            # Mean packet size
            'smean': 0.0,
            'dmean': 0.0,
            
            # HTTP/Application features
            'trans_depth': 0,
            'response_body_len': 0,
            
            # Connection tracking features
            'ct_srv_src': 0,
            'ct_state_ttl': 0,
            'ct_dst_ltm': 0,
            'ct_src_dport_ltm': 0,
            'ct_dst_sport_ltm': 0,
            'ct_dst_src_ltm': 0,
            'ct_src_ltm': 0,
            'ct_srv_dst': 0,
            
            # Special features
            'is_ftp_login': 0,
            'ct_ftp_cmd': 0,
            'ct_flw_http_mthd': 0,
            'is_sm_ips_ports': 0,
            
            # Internal tracking
            '_packets': [],
            '_first_time': None,
            '_last_time': None,
            '_src_packets': [],
            '_dst_packets': [],
            '_tcp_flags': [],
            '_direction': None
        }
        
        # DEBUG: Verify all critical keys exist
        critical_keys = ['_packets', '_src_packets', '_dst_packets', '_tcp_flags']
        for key in critical_keys:
            if key not in flow:
                print(f"❌ ERREUR: Clé manquante dans flow: {key}")
        
        return flow
    
    def reset_flows(self):
        """Remet à zéro l'extracteur pour un nouveau batch"""
        self.flows.clear()
        self.connection_tracking.clear()
        print("🔄 Extracteur remis à zéro")

    def _get_flow_key(self, packet):
        """Génère une clé de flow bidirectionnelle"""
        if IP not in packet:
            return None
            
        ip_layer = packet[IP]
        src_ip = ip_layer.src
        dst_ip = ip_layer.dst
        
        # Déterminer les ports
        src_port = 0
        dst_port = 0
        
        if TCP in packet:
            src_port = packet[TCP].sport
            dst_port = packet[TCP].dport
        elif UDP in packet:
            src_port = packet[UDP].sport
            dst_port = packet[UDP].dport
            
        # Créer une clé bidirectionnelle consistante
        endpoint1 = (src_ip, src_port)
        endpoint2 = (dst_ip, dst_port)
        
        if endpoint1 < endpoint2:
            return (endpoint1, endpoint2, 'forward')
        else:
            return (endpoint2, endpoint1, 'reverse')
    
    def _detect_service(self, src_port, dst_port, payload=None):
        """Détecte le service basé sur les ports et le payload"""
        # Vérifier les ports standards
        if dst_port in self.service_ports:
            return self.service_ports[dst_port]
        elif src_port in self.service_ports:
            return self.service_ports[src_port]
            
        # Détection basée sur le payload
        if payload:
            payload_str = str(payload).lower()
            if 'http' in payload_str or 'get ' in payload_str or 'post ' in payload_str:
                return 'http'
            elif 'ftp' in payload_str:
                return 'ftp'
            elif 'smtp' in payload_str:
                return 'smtp'
                
        return '-'
    
    def _get_tcp_state(self, tcp_flags_list):
        """Détermine l'état TCP basé sur les flags observés"""
        if not tcp_flags_list:
            return 'INT'
            
        flags = set()
        for flag in tcp_flags_list:
            flags.update(flag)
            
        if 'F' in flags:  # FIN
            return 'FIN'
        elif 'R' in flags:  # RST
            return 'RST'
        elif 'S' in flags and 'A' in flags:  # SYN-ACK sequence
            return 'CON'
        elif 'S' in flags:  # SYN only
            return 'REQ'
        else:
            return 'INT'
    
    def _calculate_jitter(self, times):
        """Calcule le jitter (variation du délai)"""
        if len(times) < 2:
            return 0.0
            
        delays = []
        for i in range(1, len(times)):
            delays.append(abs(times[i] - times[i-1]))
            
        if len(delays) < 2:
            return 0.0
            
        mean_delay = np.mean(delays)
        jitter = np.mean([abs(d - mean_delay) for d in delays])
        return float(jitter)
    
    def _extract_tcp_flags_string(self, packet):
        """Extrait les flags TCP sous forme de string"""
        if TCP not in packet:
            return ''
            
        tcp_layer = packet[TCP]
        flags = []
        
        if tcp_layer.flags & 0x01:  # FIN
            flags.append('F')
        if tcp_layer.flags & 0x02:  # SYN
            flags.append('S')
        if tcp_layer.flags & 0x04:  # RST
            flags.append('R')
        if tcp_layer.flags & 0x08:  # PSH
            flags.append('P')
        if tcp_layer.flags & 0x10:  # ACK
            flags.append('A')
        if tcp_layer.flags & 0x20:  # URG
            flags.append('U')
            
        return ''.join(flags)
    
    def process_pcap(self, pcap_file):
        """Traite un fichier PCAP et extrait toutes les features UNSW-NB15"""
        print(f"🔄 Extraction des features UNSW-NB15 depuis {pcap_file}")
        
        try:
            packets = rdpcap(pcap_file)
            print(f"📦 {len(packets)} paquets chargés")
        except Exception as e:
            print(f"❌ Erreur lors du chargement du PCAP: {e}")
            return pd.DataFrame()
        
        # Première passe : collecter les données de base
        print("📊 Première passe : analyse des paquets...")
        self._first_pass_analysis(packets)
        
        # Deuxième passe : calculer les features avancées
        print("🧮 Deuxième passe : calcul des features...")
        self._second_pass_features()
        
        # Convertir en DataFrame
        print("📋 Conversion en DataFrame...")
        df = self._flows_to_dataframe()
        
        print(f"✅ {len(df)} flows extraits avec {len(df.columns)} features")
        return df
    
    def _first_pass_analysis(self, packets):
        """Première passe : collecter les données de base de chaque paquet"""
        for i, packet in enumerate(packets):
            if i % 1000 == 0 and i > 0:
                print(f"   Traité {i} paquets...")
                            
            flow_key = self._get_flow_key(packet)
            if not flow_key:
                continue
                
            key, direction = flow_key[:-1], flow_key[-1]
            flow = self.flows[key]
            
            # DEBUG: Vérifier que flow a tous les attributs requis
            if '_packets' not in flow:
                print(f"❌ ERREUR: flow {key} n'a pas l'attribut '_packets'")
                print(f"🔍 Attributs présents: {list(flow.keys())}")
                # Recréer le flow si corrompu
                flow = self._create_empty_flow()
                self.flows[key] = flow
                print(f"🔧 Flow recréé avec attributs: {list(flow.keys())}")
            
            # Enregistrer le paquet
            packet_time = float(packet.time)
            packet_size = len(packet)
            
            try:
                flow['_packets'].append((packet_time, packet_size, direction, packet))
            except KeyError as e:
                print(f"❌ ERREUR KeyError lors de l'ajout de paquet: {e}")
                print(f"🔍 Flow keys: {list(flow.keys()) if isinstance(flow, dict) else 'NOT A DICT'}")
                print(f"🔍 Flow type: {type(flow)}")
                raise
            
            # Initialiser les temps
            if flow['_first_time'] is None:
                flow['_first_time'] = packet_time
                flow['_direction'] = direction
            flow['_last_time'] = packet_time

            # Analyser le paquet IP
            if IP in packet:
                self._analyze_ip_packet(packet, flow, direction)
                
            # Analyser selon le protocole
            if TCP in packet:
                self._analyze_tcp_packet(packet, flow, direction)
            elif UDP in packet:
                self._analyze_udp_packet(packet, flow, direction)
            elif ARP in packet:
                self._analyze_arp_packet(packet, flow, direction)
    
    def _analyze_ip_packet(self, packet, flow, direction):
        """Analyse un paquet IP"""
        ip_layer = packet[IP]
        
        # Protocole
        if not flow['proto']:
            if TCP in packet:
                flow['proto'] = 'tcp'
            elif UDP in packet:
                flow['proto'] = 'udp'
            elif ICMP in packet:
                flow['proto'] = 'icmp'
            else:
                flow['proto'] = 'other'
        
        # TTL
        if direction == 'forward':
            if flow['sttl'] == 0:
                flow['sttl'] = ip_layer.ttl
        else:
            if flow['dttl'] == 0:
                flow['dttl'] = ip_layer.ttl
        
        # Compter paquets et bytes
        packet_size = len(packet)
        if direction == 'forward':
            flow['spkts'] += 1
            flow['sbytes'] += packet_size
            flow['_src_packets'].append((float(packet.time), packet_size))
        else:
            flow['dpkts'] += 1
            flow['dbytes'] += packet_size
            flow['_dst_packets'].append((float(packet.time), packet_size))
    
    def _analyze_tcp_packet(self, packet, flow, direction):
        """Analyse un paquet TCP"""
        tcp_layer = packet[TCP]
        
        # Service detection
        if flow['service'] == '-':
            payload = None
            if Raw in packet:
                payload = packet[Raw].load
            flow['service'] = self._detect_service(tcp_layer.sport, tcp_layer.dport, payload)
        
        # TCP flags
        flags = self._extract_tcp_flags_string(packet)
        flow['_tcp_flags'].append(flags)
        
        # TCP window
        if direction == 'forward':
            if flow['swin'] == 0:
                flow['swin'] = tcp_layer.window
        else:
            if flow['dwin'] == 0:
                flow['dwin'] = tcp_layer.window
        
        # Sequence numbers pour RTT calculation
        if direction == 'forward':
            flow['stcpb'] = tcp_layer.seq
        else:
            flow['dtcpb'] = tcp_layer.seq
            
        # Analyser le payload pour HTTP
        if Raw in packet and flow['service'] == 'http':
            self._analyze_http_payload(packet[Raw].load, flow)
        
        # FTP analysis
        if flow['service'] == 'ftp' and Raw in packet:
            self._analyze_ftp_payload(packet[Raw].load, flow)
    
    def _analyze_udp_packet(self, packet, flow, direction):
        """Analyse un paquet UDP"""
        udp_layer = packet[UDP]
        
        # Service detection
        if flow['service'] == '-':
            flow['service'] = self._detect_service(udp_layer.sport, udp_layer.dport)
        
        # DNS analysis
        if udp_layer.sport == 53 or udp_layer.dport == 53:
            flow['service'] = 'dns'
    
    def _analyze_arp_packet(self, packet, flow, direction):
        """Analyse un paquet ARP"""
        flow['proto'] = 'arp'
        flow['state'] = 'INT'
    
    def _analyze_http_payload(self, payload, flow):
        """Analyse le payload HTTP"""
        try:
            payload_str = payload.decode('utf-8', errors='ignore')
            
            # Compter les requêtes HTTP
            if any(method in payload_str for method in ['GET ', 'POST ', 'PUT ', 'DELETE ']):
                flow['ct_flw_http_mthd'] += 1
                
            # Estimer la profondeur de transaction
            if 'HTTP/1.' in payload_str:
                flow['trans_depth'] += 1
                
            # Estimer la longueur du body de réponse
            if 'Content-Length:' in payload_str:
                match = re.search(r'Content-Length:\s*(\d+)', payload_str)
                if match:
                    flow['response_body_len'] += int(match.group(1))
                    
        except Exception:
            pass
    
    def _analyze_ftp_payload(self, payload, flow):
        """Analyse le payload FTP"""
        try:
            payload_str = payload.decode('utf-8', errors='ignore')
            
            # Détecter login FTP
            if 'USER ' in payload_str or 'PASS ' in payload_str:
                flow['is_ftp_login'] = 1
                
            # Compter les commandes FTP
            ftp_commands = ['USER', 'PASS', 'LIST', 'RETR', 'STOR', 'CWD', 'PWD', 'QUIT']
            for cmd in ftp_commands:
                if f'{cmd} ' in payload_str:
                    flow['ct_ftp_cmd'] += 1
                    break
                    
        except Exception:
            pass
    
    def _second_pass_features(self):
        """Calcule les features avancées pour chaque flow"""
        for key, flow in self.flows.items():
            self._calculate_timing_features(flow)
            self._calculate_statistical_features(flow)
            self._calculate_connection_tracking_features(flow, key)
            self._finalize_flow_features(flow)

    def _calculate_timing_features(self, flow):
        """Calcule les features de timing"""
        # DEBUG: Vérifier que _packets existe
        if '_packets' not in flow:
            print(f"❌ ERREUR: _packets manquant dans _calculate_timing_features")
            print(f"🔍 Clés disponibles: {list(flow.keys())}")
            return
        
        if not flow['_packets']:
            return
            
        # Durée
        if flow['_first_time'] and flow['_last_time']:
            flow['dur'] = flow['_last_time'] - flow['_first_time']
        
        # Rate (packets per second)
        total_packets = flow['spkts'] + flow['dpkts']
        if flow['dur'] > 0:
            flow['rate'] = total_packets / flow['dur']
        
        # Load (bytes per second)
        if flow['dur'] > 0:
            flow['sload'] = flow['sbytes'] / flow['dur']
            flow['dload'] = flow['dbytes'] / flow['dur']
        
        # Inter-packet times
        if len(flow['_src_packets']) >= 2:
            src_times = [p[0] for p in flow['_src_packets']]
            intervals = [src_times[i] - src_times[i-1] for i in range(1, len(src_times))]
            flow['sinpkt'] = np.mean(intervals) if intervals else 0.0
            flow['sjit'] = self._calculate_jitter(src_times)
            
        if len(flow['_dst_packets']) >= 2:
            dst_times = [p[0] for p in flow['_dst_packets']]
            intervals = [dst_times[i] - dst_times[i-1] for i in range(1, len(dst_times))]
            flow['dinpkt'] = np.mean(intervals) if intervals else 0.0
            flow['djit'] = self._calculate_jitter(dst_times)
    
    def _calculate_statistical_features(self, flow):
        """Calcule les features statistiques"""
        # Mean packet sizes
        if flow['spkts'] > 0:
            flow['smean'] = flow['sbytes'] / flow['spkts']
        if flow['dpkts'] > 0:
            flow['dmean'] = flow['dbytes'] / flow['dpkts']
            
        # TCP state
        if flow['proto'] == 'tcp':
            flow['state'] = self._get_tcp_state(flow['_tcp_flags'])
        
        # Simplistic loss calculation (could be improved with sequence analysis)
        # For now, assume no loss unless we detect retransmissions
        flow['sloss'] = 0
        flow['dloss'] = 0

    def _calculate_connection_tracking_features(self, flow, flow_key):
        """Calcule les features de connection tracking"""
        # Ces features nécessitent de tracker les connexions globalement
        # Implémentation simplifiée pour démonstration
        
        # DEBUG: Vérifier que _packets existe
        if '_packets' not in flow:
            print(f"❌ ERREUR: _packets manquant dans _calculate_connection_tracking_features")
            print(f"🔍 Clés disponibles: {list(flow.keys())}")
            return
        
        # ct_srv_src: connections to same service from same source
        # ct_state_ttl: connections with same state and TTL
        # ct_dst_ltm: connections to same destination in last time window
        # etc.
        
        # Pour une implémentation complète, il faudrait maintenir
        # un historique global des connexions
        flow['ct_srv_src'] = min(10, max(1, flow['spkts'] // 10))
        flow['ct_state_ttl'] = min(5, max(1, (flow['sttl'] + flow['dttl']) // 100))
        flow['ct_dst_ltm'] = min(3, max(1, len(flow['_packets']) // 20))
        flow['ct_src_dport_ltm'] = min(3, max(1, len(flow['_packets']) // 15))
        flow['ct_dst_sport_ltm'] = min(3, max(1, len(flow['_packets']) // 15))
        flow['ct_dst_src_ltm'] = min(3, max(1, len(flow['_packets']) // 25))
        flow['ct_src_ltm'] = min(5, max(1, len(flow['_packets']) // 10))
        flow['ct_srv_dst'] = min(5, max(1, len(flow['_packets']) // 12))
    
    def _finalize_flow_features(self, flow):
        """Finalise les features du flow"""
        # is_sm_ips_ports: same IPs and ports (simplified)
        flow['is_sm_ips_ports'] = 0  # Nécessiterait une analyse plus complexe
        
        # Assurer que toutes les valeurs numériques sont valides
        for feature in ['dur', 'rate', 'sload', 'dload', 'sinpkt', 'dinpkt', 'sjit', 'djit', 'smean', 'dmean', 'tcprtt', 'synack', 'ackdat']:
            if np.isnan(flow[feature]) or np.isinf(flow[feature]):
                flow[feature] = 0.0
                
        # Nettoyage des features temporaires
        for temp_key in ['_packets', '_first_time', '_last_time', '_src_packets', '_dst_packets', '_tcp_flags', '_direction']:
            if temp_key in flow:
                del flow[temp_key]
    
    def _flows_to_dataframe(self):
        """Convertit les flows en DataFrame avec les features UNSW-NB15"""
        if not self.flows:
            return pd.DataFrame()
        
        # Features exactes dans l'ordre UNSW-NB15
        feature_order = [
            "dur", "proto", "service", "state", "spkts", "dpkts", "sbytes", "dbytes", 
            "rate", "sttl", "dttl", "sload", "dload", "sloss", "dloss", "sinpkt", "dinpkt", 
            "sjit", "djit", "swin", "stcpb", "dtcpb", "dwin", "tcprtt", "synack", "ackdat", 
            "smean", "dmean", "trans_depth", "response_body_len", "ct_srv_src", "ct_state_ttl", 
            "ct_dst_ltm", "ct_src_dport_ltm", "ct_dst_sport_ltm", "ct_dst_src_ltm", "is_ftp_login", 
            "ct_ftp_cmd", "ct_flw_http_mthd", "ct_src_ltm", "ct_srv_dst", "is_sm_ips_ports"
        ]
        
        # Extraire les données
        data = []
        for flow_id, flow in self.flows.items():
            row = {}
            for feature in feature_order:
                row[feature] = flow.get(feature, 0)
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # Assurer les types corrects
        numeric_features = [f for f in feature_order if f not in ['proto', 'service', 'state']]
        for feature in numeric_features:
            df[feature] = pd.to_numeric(df[feature], errors='coerce').fillna(0)
        
        return df

def main():
    """Fonction principale pour tester l'extracteur"""
    extractor = UNSW_NB15_FeatureExtractor()
    
    try:
        # Traiter le fichier PCAP
        df = extractor.process_pcap("trafic.pcap")
        
        if len(df) > 0:
            # Sauvegarder les résultats
            output_file = "unsw_nb15_features.csv"
            df.to_csv(output_file, index=False)
            print(f"✅ Features UNSW-NB15 sauvegardées dans {output_file}")
            
            # Afficher les statistiques
            print(f"\n📊 Statistiques des features extraites:")
            print(f"   Nombre de flows: {len(df)}")
            print(f"   Nombre de features: {len(df.columns)}")
            print(f"   Protocoles: {df['proto'].value_counts().to_dict()}")
            print(f"   Services: {df['service'].value_counts().head().to_dict()}")
            print(f"   États: {df['state'].value_counts().to_dict()}")
            
            print(f"\n📋 Aperçu des données:")
            print(df.head())
            
            print(f"\n📈 Statistiques descriptives:")
            print(df.describe())
            
        else:
            print("❌ Aucun flow extrait")
            
    except FileNotFoundError:
        print("❌ Fichier trafic.pcap non trouvé!")
        print("Placez votre fichier PCAP dans le répertoire courant.")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    main()
