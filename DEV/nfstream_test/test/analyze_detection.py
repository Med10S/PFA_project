#!/usr/bin/env python3
"""
Script d'analyse pour comprendre pourquoi un flux a été détecté comme suspect
"""

import pandas as pd
import numpy as np
import sys
import os

# Ajouter le répertoire parent au path pour importer config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def analyze_suspicious_flow():
    """Analyser le flux détecté comme suspect"""
    
    # Charger les données extraites
    features_file = "unsw_nb15_features.csv"
    
    if not os.path.exists(features_file):
        print(f"Erreur: Le fichier {features_file} n'existe pas")
        return
    
    # Lire les données
    df = pd.read_csv(features_file)
    
    print("=== ANALYSE DU FLUX SUSPECT ===")
    print(f"Nombre total de flux extraits: {len(df)}")
    print()
    
    # Le flux suspect est le dernier (index 6, row 7)
    suspicious_flow = df.iloc[-1]  # Dernier flux
    
    print("=== PARAMÈTRES DU FLUX SUSPECT ===")
    print(f"Durée: {suspicious_flow['dur']:.6f} secondes")
    print(f"Protocole: {suspicious_flow['proto']}")
    print(f"Service: {suspicious_flow['service']}")
    print(f"État: {suspicious_flow['state']}")
    print(f"Paquets source→dest: {suspicious_flow['spkts']}")
    print(f"Paquets dest→source: {suspicious_flow['dpkts']}")
    print(f"Bytes source→dest: {suspicious_flow['sbytes']}")
    print(f"Bytes dest→source: {suspicious_flow['dbytes']}")
    print(f"TTL source: {suspicious_flow['sttl']}")
    print(f"TTL destination: {suspicious_flow['dttl']}")
    print(f"Fenêtre TCP source: {suspicious_flow['swin']}")
    print(f"Fenêtre TCP dest: {suspicious_flow['dwin']}")
    print()
    
    print("=== INDICATEURS SUSPECTS ===")
    
    # 1. Analyse de l'état de connexion
    if suspicious_flow['state'] == 'INT':
        print("⚠️  CONNEXION INTERROMPUE (state=INT)")
        print("   → Connexion TCP non complétée, potentiel scan de port")
    
    # 2. Analyse des TTL
    if suspicious_flow['sttl'] != suspicious_flow['dttl']:
        print(f"⚠️  TTL DIFFÉRENTS: source={suspicious_flow['sttl']}, dest={suspicious_flow['dttl']}")
        print("   → Peut indiquer du spoofing IP ou routing inhabituel")
    
    # 3. Analyse de la durée vs paquets
    packets_total = suspicious_flow['spkts'] + suspicious_flow['dpkts']
    if suspicious_flow['dur'] < 0.1 and packets_total < 5:
        print(f"⚠️  CONNEXION TRÈS COURTE: {suspicious_flow['dur']:.3f}s avec {packets_total} paquets")
        print("   → Tentative de connexion avortée rapidement")
    
    # 4. Analyse des fenêtres TCP
    if suspicious_flow['swin'] < 50 or suspicious_flow['dwin'] < 300:
        print(f"⚠️  FENÊTRES TCP PETITES: source={suspicious_flow['swin']}, dest={suspicious_flow['dwin']}")
        print("   → Potentiel indicateur de scan ou connexion anormale")
    
    # 5. Analyse des temps de réponse
    if (suspicious_flow['tcprtt'] == 0 and suspicious_flow['synack'] == 0 and 
        suspicious_flow['ackdat'] == 0):
        print("⚠️  TEMPS DE RÉPONSE TCP TOUS À ZÉRO")
        print("   → Connexion TCP incomplète ou analyse de timing échouée")
    
    # 6. Analyse de l'asymétrie des paquets
    if suspicious_flow['spkts'] > suspicious_flow['dpkts'] * 2:
        print(f"⚠️  ASYMÉTRIE FORTE DES PAQUETS: {suspicious_flow['spkts']} vs {suspicious_flow['dpkts']}")
        print("   → Communication unidirectionnelle, potentiel scan")
    
    print()
    
    # Comparaison avec les autres flux
    print("=== COMPARAISON AVEC LES AUTRES FLUX ===")
    
    # Statistiques des autres flux HTTPS
    https_flows = df[df['service'] == 'https']
    other_https = https_flows[https_flows.index != suspicious_flow.name]
    
    if len(other_https) > 0:
        print("Flux HTTPS normaux dans le même PCAP:")
        print(f"  Durée moyenne: {other_https['dur'].mean():.6f}s")
        print(f"  Paquets moyens source: {other_https['spkts'].mean():.1f}")
        print(f"  Paquets moyens dest: {other_https['dpkts'].mean():.1f}")
        print(f"  États: {other_https['state'].unique()}")
        print(f"  TTL source moyen: {other_https['sttl'].mean():.1f}")
        print(f"  TTL dest moyen: {other_https['dttl'].mean():.1f}")
        print()
        
        # Comparaison directe
        print("Comparaison avec la moyenne des flux HTTPS normaux:")
        if suspicious_flow['dur'] < other_https['dur'].mean() / 2:
            print(f"  ⚠️  Durée anormalement courte: {suspicious_flow['dur']:.6f} vs {other_https['dur'].mean():.6f}")
        
        if suspicious_flow['spkts'] < other_https['spkts'].mean() / 2:
            print(f"  ⚠️  Très peu de paquets source: {suspicious_flow['spkts']} vs {other_https['spkts'].mean():.1f}")
        
        if suspicious_flow['swin'] < other_https['swin'].mean() / 2:
            print(f"  ⚠️  Fenêtre TCP source très petite: {suspicious_flow['swin']} vs {other_https['swin'].mean():.1f}")
    
    print()
    
    print("=== CONCLUSION ===")
    score = 0
    reasons = []
    
    if suspicious_flow['state'] == 'INT':
        score += 2
        reasons.append("Connexion interrompue")
    
    if suspicious_flow['sttl'] != suspicious_flow['dttl']:
        score += 1
        reasons.append("TTL différents")
    
    if suspicious_flow['dur'] < 0.1 and (suspicious_flow['spkts'] + suspicious_flow['dpkts']) < 5:
        score += 2
        reasons.append("Connexion très courte avec peu de paquets")
    
    if suspicious_flow['swin'] < 50:
        score += 1
        reasons.append("Fenêtre TCP source très petite")
    
    if (suspicious_flow['tcprtt'] == 0 and suspicious_flow['synack'] == 0):
        score += 1
        reasons.append("Temps de réponse TCP anormaux")
    
    print(f"Score de suspicion: {score}/7")
    print(f"Probabilité détectée: 0.5312 (53.12%)")
    print()
    
    if score >= 4:
        print("✅ DÉTECTION JUSTIFIÉE")
        print("Ce flux présente plusieurs indicateurs suspects typiques d'un scan de port ou d'une tentative de connexion malveillante.")
    elif score >= 2:
        print("⚠️ DÉTECTION BORDERLINE")
        print("Ce flux présente quelques indicateurs suspects, la détection est raisonnable mais pourrait être un faux positif.")
    else:
        print("❌ PROBABLE FAUX POSITIF")
        print("Ce flux ne présente pas assez d'indicateurs suspects pour justifier la détection.")
    
    print("\nRaisons de la suspicion:")
    for reason in reasons:
        print(f"  - {reason}")
    
    print("\nRecommandations:")
    if score >= 4:
        print("  - Maintenir le seuil de détection actuel")
        print("  - Investiguer la source de ce type de trafic")
    else:
        print("  - Considérer ajuster le seuil de détection")
        print("  - Améliorer l'entraînement du modèle sur des connexions HTTPS légitimes courtes")

if __name__ == "__main__":
    analyze_suspicious_flow()
