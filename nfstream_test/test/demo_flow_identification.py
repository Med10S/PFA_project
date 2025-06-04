#!/usr/bin/env python3
"""
Script de démonstration : Comment les flux sont identifiés
=========================================================
Ce script accompagne le Guide Flow_Identification_Guide.md
"""

import pandas as pd
from scapy.all import rdpcap, IP, TCP, UDP, ICMP
from collections import defaultdict, Counter
import json

def demonstrate_flow_identification():
    """
    Démonstration interactive de l'identification des flux
    """
    print("🎯 DÉMONSTRATION : IDENTIFICATION DES FLUX RÉSEAU")
    print("=" * 60)
    
    # Charger le PCAP
    try:
        packets = rdpcap("trafic.pcap")
        print(f"📁 Fichier chargé: trafic.pcap ({len(packets)} paquets)")
    except:
        print("❌ Erreur: fichier trafic.pcap non trouvé")
        return
    
    # Structures pour l'analyse
    flows = defaultdict(list)
    protocols = Counter()
    
    print(f"\n🔍 ANALYSE PAQUET PAR PAQUET (10 premiers):")
    print("-" * 60)
    
    for i, pkt in enumerate(packets[:10]):
        if IP not in pkt:
            continue
            
        # Extraire les informations
        src_ip = pkt[IP].src
        dst_ip = pkt[IP].dst
        protocol = pkt[IP].proto
        
        if TCP in pkt:
            src_port = pkt[TCP].sport
            dst_port = pkt[TCP].dport
            proto_name = "TCP"
        elif UDP in pkt:
            src_port = pkt[UDP].sport
            dst_port = pkt[UDP].dport
            proto_name = "UDP"
        elif ICMP in pkt:
            src_port = pkt[ICMP].type
            dst_port = pkt[ICMP].code
            proto_name = "ICMP"
        else:
            src_port = 0
            dst_port = 0
            proto_name = f"Proto-{protocol}"
        
        protocols[proto_name] += 1
        
        # Créer la clé de flux
        if proto_name in ["TCP", "UDP"]:
            # Bidirectionnel : trier les endpoints
            flow_key = tuple(sorted([
                (src_ip, src_port),
                (dst_ip, dst_port)
            ]))
            direction = "↔"
        else:
            # Directionnel pour ICMP/autres
            flow_key = ((src_ip, src_port), (dst_ip, dst_port))
            direction = "→"
        
        flows[flow_key].append({
            'packet_num': i + 1,
            'src': f"{src_ip}:{src_port}",
            'dst': f"{dst_ip}:{dst_port}",
            'proto': proto_name,
            'size': len(pkt)
        })
        
        print(f"📦 Paquet #{i+1:2d}: {src_ip}:{src_port} {direction} {dst_ip}:{dst_port} ({proto_name})")
        print(f"   🔑 Clé de flux: {flow_key}")
        print(f"   📏 Taille: {len(pkt)} bytes")
        print()
    
    print(f"📊 RÉSULTATS DE L'AGRÉGATION:")
    print("-" * 60)
    print(f"Total paquets analysés: {len([p for p in packets[:10] if IP in p])}")
    print(f"Flux uniques identifiés: {len(flows)}")
    print(f"Protocoles détectés: {dict(protocols)}")
    
    print(f"\n🌊 DÉTAIL DES FLUX:")
    print("-" * 60)
    for i, (flow_key, pkts) in enumerate(flows.items(), 1):
        first_pkt = pkts[0]
        print(f"Flux {i}: {flow_key}")
        print(f"├── Protocole: {first_pkt['proto']}")
        print(f"├── Paquets: {len(pkts)}")
        print(f"├── Taille totale: {sum(p['size'] for p in pkts)} bytes")
        print(f"└── Numéros: {[p['packet_num'] for p in pkts]}")
        print()

def compare_with_csv():
    """
    Compare avec le résultat final CSV
    """
    print(f"📋 COMPARAISON AVEC LE CSV FINAL:")
    print("-" * 60)
    
    try:
        df = pd.read_csv("unsw_nb15_features.csv")
        packets = rdpcap("trafic.pcap")
        
        print(f"Paquets PCAP: {len(packets)}")
        print(f"Flux CSV: {len(df)}")
        print(f"Paquets CSV: {df['spkts'].sum() + df['dpkts'].sum()}")
        
        print(f"\n📈 FLUX FINAUX:")
        for i, row in df.iterrows():
            print(f"Flux {i+1}:")
            print(f"├── Protocole: {row['proto']}")
            print(f"├── Service: {row['service']}")
            print(f"├── État: {row['state']}")
            print(f"├── Durée: {row['dur']:.3f}s")
            print(f"├── Paquets: {row['spkts']} → + {row['dpkts']} ← = {row['spkts'] + row['dpkts']}")
            print(f"├── Bytes: {row['sbytes']} → + {row['dbytes']} ← = {row['sbytes'] + row['dbytes']}")
            print(f"└── Rate: {row['rate']:.2f}")
            print()
            
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du CSV: {e}")

def explain_aggregation_rules():
    """
    Explique les règles d'agrégation avec des exemples
    """
    print(f"📚 RÈGLES D'AGRÉGATION DÉTAILLÉES:")
    print("=" * 60)
    
    rules = {
        "TCP/UDP": {
            "description": "Agrégation bidirectionnelle",
            "rule": "Même flux pour A→B et B→A",
            "example": """
            Paquet 1: 192.168.1.2:20103 → 172.65.251.78:443 (TCP)
            Paquet 2: 172.65.251.78:443 → 192.168.1.2:20103 (TCP)
            → MÊME FLUX car endpoints identiques""",
            "key_format": "tuple(sorted([(src_ip, src_port), (dst_ip, dst_port)]))"
        },
        "ICMP": {
            "description": "Agrégation directionnelle",
            "rule": "Flux séparés par direction et type",
            "example": """
            Ping Request:  192.168.1.1 → 8.8.8.8 (Type 8, Code 0)
            Ping Reply:    8.8.8.8 → 192.168.1.1 (Type 0, Code 0)
            → FLUX DIFFÉRENTS car types ICMP différents""",
            "key_format": "((src_ip, icmp_type), (dst_ip, icmp_code))"
        },
        "Autres": {
            "description": "Agrégation simplifiée",
            "rule": "Pas de ports, juste les IPs",
            "example": """
            IGMP/OSPF/GRE: Protocoles de contrôle
            → Flux basés uniquement sur les IPs""",
            "key_format": "((src_ip, 0), (dst_ip, 0))"
        }
    }
    
    for proto, info in rules.items():
        print(f"\n🔷 {proto}:")
        print(f"├── Description: {info['description']}")
        print(f"├── Règle: {info['rule']}")
        print(f"├── Format clé: {info['key_format']}")
        print(f"└── Exemple:{info['example']}")

def analyze_suspicious_flow():
    """
    Analyse détaillée du flux suspect détecté
    """
    print(f"\n🚨 ANALYSE DU FLUX SUSPECT:")
    print("=" * 60)
    
    suspicious = {
        'flow_id': 7,
        'src': '192.168.1.2:19010',
        'dst': '104.16.103.112:443',
        'proto': 'tcp',
        'service': 'https',
        'state': 'INT',
        'spkts': 2,
        'dpkts': 1,
        'dur': 0.054,
        'rate': 55.73,
        'detection_probability': 0.5312
    }
    
    print(f"🎯 Flux détecté comme suspect:")
    print(f"├── Source: {suspicious['src']}")
    print(f"├── Destination: {suspicious['dst']} (Cloudflare)")
    print(f"├── Protocole: {suspicious['proto'].upper()}")
    print(f"├── Service: {suspicious['service'].upper()}")
    print(f"├── État: {suspicious['state']} (connexion interrompue)")
    print(f"├── Paquets: {suspicious['spkts']} → + {suspicious['dpkts']} ←")
    print(f"├── Durée: {suspicious['dur']}s")
    print(f"└── Probabilité d'attaque: {suspicious['detection_probability']:.4f}")
    
    print(f"\n🔍 Pourquoi ce flux est-il suspect ?")
    reasons = [
        "⚠️  Asymétrie des paquets (2:1 ratio)",
        "⚠️  Durée très courte (54ms pour HTTPS)",
        "⚠️  Connexion interrompue (état INT)",
        "⚠️  Pattern inhabituel pour du trafic HTTPS normal",
        "⚠️  Serveur Cloudflare (peut héberger du contenu malveillant)"
    ]
    
    for reason in reasons:
        print(f"  {reason}")
    
    print(f"\n💡 Évaluation finale:")
    print(f"  Ce flux pourrait être un faux positif car:")
    print(f"  • Cloudflare est un CDN légitime")
    print(f"  • Connexions HTTPS courtes sont normales")
    print(f"  • Asymétrie peut être due à des timeouts réseau")

if __name__ == "__main__":
    demonstrate_flow_identification()
    explain_aggregation_rules()
    compare_with_csv()
    analyze_suspicious_flow()
    
    print(f"\n📖 Pour plus de détails, consultez Flow_Identification_Guide.md")
