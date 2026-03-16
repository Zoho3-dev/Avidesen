"""
Script de débogage pour l'authentification Zoho.
Affiche les détails de la requête et de la réponse.
"""

import requests
import json
from src.config.settings import load_config

def debug_oauth():
    """Test l'authentification OAuth avec débogage détaillé."""
    print("=" * 60)
    print("DÉBOGAGE AUTHENTIFICATION ZOHO")
    print("=" * 60)
    
    # Charger la configuration
    config = load_config()
    
    client_id = config.get("ZOHO_CLIENT_ID")
    client_secret = config.get("ZOHO_CLIENT_SECRET")
    granted_code = config.get("GRANTED_CODE")
    
    print("\n[CONFIGURATION]")
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {'*' * len(client_secret) if client_secret else 'MANQUANT'}")
    print(f"Granted Code: {granted_code[:20]}..." if granted_code else "MANQUANT")
    
    if not all([client_id, client_secret, granted_code]):
        print("\n❌ ERREUR: Paramètres manquants dans config.txt")
        return
    
    # Préparer la requête
    url = "https://accounts.zoho.eu/oauth/v2/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": granted_code
    }
    
    print("\n[REQUÊTE]")
    print(f"URL: {url}")
    print(f"Data: {json.dumps(data, indent=2)}")
    
    # Envoyer la requête
    print("\n[ENVOI DE LA REQUÊTE]...")
    try:
        response = requests.post(url, data=data, timeout=30)
        
        print(f"\n[RÉPONSE HTTP]")
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"\n[CONTENU DE LA RÉPONSE]")
            print(json.dumps(response_json, indent=2))
            
            # Analyse des erreurs spécifiques
            if "error" in response_json:
                error = response_json["error"]
                print(f"\n[ANALYSE D'ERREUR]")
                if error == "invalid_client":
                    print("❌ Client ID ou Client Secret invalide")
                    print("   - Vérifiez qu'il n'y a pas d'espace ou caractère invisible")
                    print("   - Assurez-vous que le client est actif dans la console Zoho")
                elif error == "invalid_grant":
                    print("❌ Granted Code invalide ou expiré")
                    print("   - Le code doit être utilisé dans les 10 minutes")
                    print("   - Générez un nouveau code depuis la console Zoho")
                elif error == "unsupported_grant_type":
                    print("❌ Type de grant non supporté")
                else:
                    print(f"❌ Erreur inconnue: {error}")
        except json.JSONDecodeError:
            print(f"\n[RÉPONSE NON-JSON]")
            print(response.text[:500])
            
    except requests.RequestException as e:
        print(f"\n❌ ERREUR RÉSEAU: {e}")

if __name__ == "__main__":
    debug_oauth()
