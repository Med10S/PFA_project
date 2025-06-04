#!/usr/bin/env python3
"""
Script pour tester et générer des clés Fernet valides
"""
import base64
from cryptography.fernet import Fernet
import os

def analyze_key(key_string):
    """Analyse une clé donnée"""
    print(f"Clé fournie: {key_string}")
    print(f"Longueur de la chaîne: {len(key_string)} caractères")
    
    try:
        # Essayer de décoder en base64
        decoded = base64.urlsafe_b64decode(key_string + '==')  # Ajouter padding si nécessaire
        print(f"Longueur décodée: {len(decoded)} octets")
        print(f"Octets décodés: {decoded.hex()}")
        
        if len(decoded) == 32:
            print("✓ La longueur est correcte (32 octets)")
            try:
                # Tester si la clé fonctionne avec Fernet
                f = Fernet(key_string.encode())
                print("✓ Clé Fernet valide!")
                return True
            except Exception as e:
                print(f"✗ Erreur Fernet: {e}")
        else:
            print(f"✗ Longueur incorrecte: {len(decoded)} octets (doit être 32)")
            
    except Exception as e:
        print(f"✗ Erreur de décodage base64: {e}")
    
    return False

def generate_valid_key():
    """Génère une clé Fernet valide"""
    key = Fernet.generate_key()
    return key.decode()

def main():
    print("=== ANALYSE DE LA CLÉ FERNET ===")
    
    # Votre clé actuelle
    current_key = "POEAC3/m1cICZq526WTuSXAOWjy4vtifUhPXcUDn+9icidCO5fPS7pUL8GbfrOnm"
    
    print("\n1. Analyse de votre clé actuelle:")
    is_valid = analyze_key(current_key)
    
    print("\n2. Génération d'une nouvelle clé valide:")
    new_key = generate_valid_key()
    print(f"Nouvelle clé: {new_key}")
    
    print("\n3. Vérification de la nouvelle clé:")
    analyze_key(new_key)
    
    print("\n4. Test de chiffrement/déchiffrement:")
    try:
        f = Fernet(new_key.encode())
        test_message = b"Test message for encryption"
        encrypted = f.encrypt(test_message)
        decrypted = f.decrypt(encrypted)
        print(f"✓ Message original: {test_message}")
        print(f"✓ Message chiffré: {encrypted}")
        print(f"✓ Message déchiffré: {decrypted}")
        print("✓ Test de chiffrement réussi!")
    except Exception as e:
        print(f"✗ Erreur de test: {e}")
    
    print(f"\n=== RÉSUMÉ ===")
    print(f"Clé actuelle valide: {'✓ OUI' if is_valid else '✗ NON'}")
    print(f"Nouvelle clé générée: {new_key}")
    print(f"À utiliser comme: ENCRYPTION_KEY={new_key}")

if __name__ == "__main__":
    main()
