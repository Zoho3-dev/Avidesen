"""
Script de rafraîchissement du token Zoho.
Utilise le refresh token pour obtenir un nouveau access token.
"""

from src.config.settings import load_config
from src.zoho.auth import ZohoAuth


def main():
    """
    Rafraîchit le token Zoho et le sauvegarde dans config.txt.
    """
    print("=" * 60)
    print("Rafraîchissement du Token Zoho")
    print("=" * 60)
    
    # Charger la configuration
    config = load_config()
    
    # Récupérer les informations nécessaires
    client_id = config.get("ZOHO_CLIENT_ID")
    client_secret = config.get("ZOHO_CLIENT_SECRET")
    granted_code = config.get("GRANTED_CODE")
    
    if not client_id or not client_secret:
        print("❌ Erreur : ZOHO_CLIENT_ID ou ZOHO_CLIENT_SECRET manquant dans config.txt")
        return
    
    # Créer une instance de ZohoAuth
    zoho_auth = ZohoAuth(client_id, client_secret, granted_code)
    
    print("\n📋 État actuel :")
    print(f"   - Access Token : {'✅ Présent' if zoho_auth.access_token else '❌ Absent'}")
    print(f"   - Refresh Token : {'✅ Présent' if zoho_auth.refresh_token else '❌ Absent'}")
    print(f"   - Granted Code : {'✅ Présent' if granted_code else '❌ Absent'}")
    
    # Obtenir un token valide
    print("\n🔄 Rafraîchissement en cours...")
    token = zoho_auth.get_valid_access_token()
    
    if token:
        print("\n✅ Token rafraîchi avec succès !")
        print(f"   Nouveau token : {token[:20]}...")
        print(f"\n💾 Le token a été sauvegardé dans config.txt")
    else:
        print("\n❌ Échec du rafraîchissement du token")
        print("\n💡 Solutions possibles :")
        print("   1. Vérifiez que ZOHO_CLIENT_ID et ZOHO_CLIENT_SECRET sont corrects")
        print("   2. Si vous n'avez pas de REFRESH_TOKEN, générez un nouveau GRANTED_CODE")
        print("   3. Consultez la documentation Zoho OAuth pour obtenir un nouveau code")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
