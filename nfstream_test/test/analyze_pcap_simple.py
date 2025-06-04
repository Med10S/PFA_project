#!/usr/bin/env python3
"""
Analyse simplifiée du processus d'agrégation des paquets PCAP en flows
Utilise seulement les protocoles disponibles dans Scapy
"""

import pandas as pd
from scapy.all import rdpcap, IP, TCP, UDP, ICMP, IPv6, Raw, Ether, ARP
from collections import defaultdict, Counter
from nfstream import NFStreamer
import os

def get_protocol_name(pkt):
    """Identifie le protocole du paquet avec les protocoles disponibles"""
    if IP in pkt:
        protocol_num = pkt[IP].proto
        
        # Protocoles communs disponibles
        if TCP in pkt:
            return "TCP"
        elif UDP in pkt:
            return "UDP"
        elif ICMP in pkt:
            return "ICMP"
        
        # Protocoles basés sur le numéro de protocole IP
        protocol_map = {
            1: "ICMP",
            2: "IGMP", 
            4: "IP-in-IP",
            6: "TCP",
            8: "EGP",
            12: "PUP",
            17: "UDP", 
            27: "RDP",
            41: "IPv6",
            43: "IPv6-Route",
            44: "IPv6-Frag", 
            47: "GRE",
            50: "ESP",
            51: "AH",
            58: "ICMPv6",
            89: "OSPF",
            103: "PIM"
        }
        
        return protocol_map.get(protocol_num, f"Proto-{protocol_num}")
    
    elif IPv6 in pkt:
        # Pour IPv6, utiliser le next header
        next_header = pkt[IPv6].nh
        if next_header == 6:
            return "TCP"
        elif next_header == 17:
            return "UDP"
        elif next_header == 58:
            return "ICMPv6"
        else:
            return f"IPv6-{next_header}"
    
    elif ARP in pkt:
        return "ARP"
    
    return "Unknown"

def get_connection_info(pkt, proto):
    """Extrait les informations de connexion selon le protocole"""
    if IP in pkt:
        src_ip = pkt[IP].src
        dst_ip = pkt[IP].dst
        
        if proto in ["TCP", "UDP"]:
            if TCP in pkt:
                return src_ip, dst_ip, pkt[TCP].sport, pkt[TCP].dport, str(pkt[TCP].flags)
            elif UDP in pkt:
                return src_ip, dst_ip, pkt[UDP].sport, pkt[UDP].dport, "UDP"
        elif proto == "ICMP" and ICMP in pkt:
            return src_ip, dst_ip, pkt[ICMP].type, pkt[ICMP].code, "ICMP"
        else:
            return src_ip, dst_ip, 0, 0, proto
    
    elif IPv6 in pkt:
        src_ip = pkt[IPv6].src
        dst_ip = pkt[IPv6].dst
        
        if TCP in pkt:
            return src_ip, dst_ip, pkt[TCP].sport, pkt[TCP].dport, str(pkt[TCP].flags)
        elif UDP in pkt:
            return src_ip, dst_ip, pkt[UDP].sport, pkt[UDP].dport, "UDP"
        else:
            return src_ip, dst_ip, 0, 0, proto
    
    else:
        return "unknown", "unknown", 0, 0, proto

def analyze_pcap_packets(pcap_file):
    """Analyse les paquets bruts du fichier PCAP"""
    print("=" * 60)
    print("ANALYSE DES PAQUETS BRUTS PCAP")
    print("=" * 60)
    
    try:
        packets = rdpcap(pcap_file)
        print(f"Nombre total de paquets: {len(packets)}")
        
        # Statistiques par protocole
        protocols = Counter()
        connections = defaultdict(list)
        
        for i, pkt in enumerate(packets):
            # Détection du protocole
            proto = get_protocol_name(pkt)
            protocols[proto] += 1
            
            # Obtenir les informations de connexion
            src_ip, dst_ip, src_port, dst_port, flags = get_connection_info(pkt, proto)
            
            # Clé de connexion (bidirectionnelle pour TCP/UDP, directionnelle pour les autres)
            if proto in ["TCP", "UDP"]:
                conn_key = tuple(sorted([
                    (src_ip, src_port),
                    (dst_ip, dst_port)
                ]))
            else:
                conn_key = ((src_ip, src_port), (dst_ip, dst_port))
            
            connections[conn_key].append({
                'packet_num': i + 1,
                'src': f"{src_ip}:{src_port}" if src_port != 0 else src_ip,
                'dst': f"{dst_ip}:{dst_port}" if dst_port != 0 else dst_ip,
                'proto': proto,
                'size': len(pkt),
                'flags': flags,
                'timestamp': float(pkt.time) if hasattr(pkt, 'time') else 0
            })
        
        print(f"\nRépartition par protocole:")
        for proto, count in sorted(protocols.items()):
            print(f"  {proto}: {count} paquets")
        
        print(f"\nNombre de connexions uniques détectées: {len(connections)}")
        
        # Analyse détaillée des connexions
        print(f"\nDétail des connexions:")
        for i, (conn_key, pkts) in enumerate(connections.items(), 1):
            first_pkt = pkts[0]
            print(f"\nConnexion {i}:")
            print(f"  Endpoints: {conn_key[0]} <-> {conn_key[1]}")
            print(f"  Protocole: {first_pkt['proto']}")
            print(f"  Nombre de paquets: {len(pkts)}")
            print(f"  Taille totale: {sum(p['size'] for p in pkts)} bytes")
            
            # Afficher quelques paquets pour illustration
            if len(pkts) <= 5:
                for pkt in pkts:
                    print(f"    Paquet #{pkt['packet_num']}: {pkt['src']} -> {pkt['dst']} ({pkt['size']} bytes)")
            else:
                print(f"    Premiers paquets:")
                for pkt in pkts[:3]:
                    print(f"      Paquet #{pkt['packet_num']}: {pkt['src']} -> {pkt['dst']} ({pkt['size']} bytes)")
                print(f"    ... et {len(pkts) - 3} autres paquets")
        
        return connections
        
    except Exception as e:
        print(f"Erreur lors de l'analyse PCAP: {e}")
        return {}

def analyze_nfstream_flows(pcap_file):
    """Analyse les flows générés par NFStream"""
    print("\n" + "=" * 60)
    print("ANALYSE DES FLOWS NFSTREAM")
    print("=" * 60)
    
    try:
        # Créer un streamer NFStream sans statistical_analysis
        streamer = NFStreamer(source=pcap_file)
        flows = []
        
        for flow in streamer:
            flows.append({
                'id': flow.id,
                'src_ip': flow.src_ip,
                'src_port': flow.src_port,
                'dst_ip': flow.dst_ip,
                'dst_port': flow.dst_port,
                'protocol': flow.protocol,
                'bidirectional_packets': flow.bidirectional_packets,
                'bidirectional_bytes': flow.bidirectional_bytes,
                'src2dst_packets': flow.src2dst_packets,
                'dst2src_packets': flow.dst2src_packets,
                'bidirectional_duration_ms': flow.bidirectional_duration_ms
            })
        
        print(f"Nombre de flows NFStream: {len(flows)}")
        
        total_packets = sum(f['bidirectional_packets'] for f in flows)
        print(f"Total des paquets dans les flows: {total_packets}")
        
        print(f"\nDétail des flows NFStream:")
        for i, flow in enumerate(flows, 1):
            duration_sec = flow['bidirectional_duration_ms'] / 1000 if flow['bidirectional_duration_ms'] else 0
            proto_name = {6: "TCP", 17: "UDP"}.get(flow['protocol'], f"Proto-{flow['protocol']}")
            
            print(f"\nFlow {i} (ID: {flow['id']}):")
            print(f"  {flow['src_ip']}:{flow['src_port']} <-> {flow['dst_ip']}:{flow['dst_port']}")
            print(f"  Protocole: {proto_name} (#{flow['protocol']})")
            print(f"  Durée: {duration_sec:.3f} secondes")
            print(f"  Paquets: {flow['bidirectional_packets']} ({flow['src2dst_packets']} -> + {flow['dst2src_packets']} <-)")
            print(f"  Bytes: {flow['bidirectional_bytes']}")
        
        return flows
        
    except Exception as e:
        print(f"Erreur lors de l'analyse NFStream: {e}")
        return []

def analyze_csv_output(csv_file):
    """Analyse le fichier CSV de sortie s'il existe"""
    print("\n" + "=" * 60)
    print("ANALYSE DU FICHIER CSV DE SORTIE")
    print("=" * 60)
    
    if not os.path.exists(csv_file):
        print(f"Fichier CSV non trouvé: {csv_file}")
        print("Exécutez d'abord unsw_nb15_feature_extractor.py pour le générer")
        return None
    
    try:
        df = pd.read_csv(csv_file)
        print(f"Nombre de lignes dans le CSV: {len(df)}")
        print(f"Nombre de colonnes: {len(df.columns)}")
        
        print(f"\nRésumé des flows dans le CSV:")
        for i, row in df.iterrows():
            print(f"\nFlow {i+1}:")
            print(f"  Protocole: {row['proto']}")
            print(f"  Service: {row['service']}")
            print(f"  État: {row['state']}")
            print(f"  Durée: {row['dur']:.3f} secondes")
            print(f"  Paquets: src={row['spkts']}, dst={row['dpkts']}, total={row['spkts'] + row['dpkts']}")
            print(f"  Bytes: src={row['sbytes']}, dst={row['dbytes']}, total={row['sbytes'] + row['dbytes']}")
            print(f"  Rate: {row['rate']:.2f}")
        
        total_packets_csv = df['spkts'].sum() + df['dpkts'].sum()
        print(f"\nTotal paquets CSV: {total_packets_csv}")
        
        return df
        
    except Exception as e:
        print(f"Erreur lors de l'analyse CSV: {e}")
        return None

def main():
    """Fonction principale"""
    pcap_file = "trafic.pcap"
    csv_file = "unsw_nb15_features.csv"
    
    print("ANALYSE SIMPLIFIÉE DU PROCESSUS D'AGRÉGATION PCAP -> CSV")
    print("Fichier PCAP:", pcap_file)
    print("Fichier CSV:", csv_file)
    
    # Analyse des paquets bruts
    pcap_connections = analyze_pcap_packets(pcap_file)
    
    # Analyse des flows NFStream
    nfstream_flows = analyze_nfstream_flows(pcap_file)
    
    # Analyse du CSV de sortie
    csv_df = analyze_csv_output(csv_file)
    
    # Résumé
    print("\n" + "=" * 60)
    print("RÉSUMÉ DU PROCESSUS D'IDENTIFICATION DES FLUX")
    print("=" * 60)
    
    pcap_packets = sum(len(pkts) for pkts in pcap_connections.values()) if pcap_connections else 0
    nf_packets = sum(f['bidirectional_packets'] for f in nfstream_flows) if nfstream_flows else 0
    csv_packets = csv_df['spkts'].sum() + csv_df['dpkts'].sum() if csv_df is not None else 0
    
    print(f"ÉTAPES D'AGRÉGATION:")
    print(f"1. Paquets bruts PCAP: {pcap_packets}")
    print(f"2. Connexions détectées (Scapy): {len(pcap_connections) if pcap_connections else 0}")
    print(f"3. Flows NFStream: {len(nfstream_flows) if nfstream_flows else 0}")
    print(f"4. Total paquets NFStream: {nf_packets}")
    print(f"5. Flows CSV final: {len(csv_df) if csv_df is not None else 0}")
    print(f"6. Total paquets CSV: {csv_packets}")
    
    print(f"\nPRINCIPE D'IDENTIFICATION:")
    print(f"• Un flux = ensemble de paquets avec même 5-tuple")
    print(f"• 5-tuple = (src_ip, dst_ip, src_port, dst_port, protocol)")
    print(f"• TCP/UDP : clé bidirectionnelle (symétrique)")
    print(f"• ICMP/autres : clé directionnelle")
    print(f"• NFStream applique des timeouts pour fermer les flux")
    
    print(f"\n" + "=" * 60)
    print("ANALYSE TERMINÉE")
    print("=" * 60)

if __name__ == "__main__":
    main()
