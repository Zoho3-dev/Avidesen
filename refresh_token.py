"""
Script de rafraîchissement du token Zoho.
Utilise le refresh token pour obtenir un nouveau access token.
"""

from src.zoho.auth import ZohoAuth


def main():
    """
    Rafraîchit le token Zoho et le sauvegarde dans config.txt.
    """
    print("=" * 60)
    print("Rafraîchissement du Token Zoho")
    print("=" * 60)

    zoho_auth = ZohoAuth()

    if not zoho_auth.client_id or not zoho_auth.client_secret:
        print("Erreur : ZOHO_CLIENT_ID ou ZOHO_CLIENT_SECRET manquant dans config.txt")
        return

    print("\nEtat actuel :")
    print(f"   - Access Token : {'Present' if zoho_auth.access_token else 'Absent'}")
    print(f"   - Refresh Token : {'Present' if zoho_auth.refresh_token else 'Absent'}")
    print(f"   - Granted Code : {'Present' if zoho_auth.granted_code else 'Absent'}")

    print("\nRafraichissement en cours...")
    token = zoho_auth.get_valid_access_token()

    if token:
        print(f"\n[OK] Token rafraichi avec succes : {token[:20]}...")
        print("Le token a ete sauvegarde dans config.txt")
    else:
        print("\n[ERROR] Echec du rafraichissement du token")
        print("\nSolutions possibles :")
        print("   1. Verifiez que ZOHO_CLIENT_ID et ZOHO_CLIENT_SECRET sont corrects")
        print("   2. Si vous n'avez pas de REFRESH_TOKEN, generez un nouveau GRANTED_CODE")
        print("   3. Consultez la documentation Zoho OAuth pour obtenir un nouveau code")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
