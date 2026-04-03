"""
Module d'authentification Zoho.
Gère l'obtention et le rafraîchissement des tokens d'accès.
"""

import time
import requests

from src.config.settings import load_config, save_config

ZOHO_TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"


class ZohoAuth:
    """Gère l'authentification OAuth avec Zoho."""

    def __init__(self):
        config = load_config()
        self.client_id = config.get("ZOHO_CLIENT_ID", "")
        self.client_secret = config.get("ZOHO_CLIENT_SECRET", "")
        self.granted_code = config.get("GRANTED_CODE", "")
        self.refresh_token = config.get("ZOHO_REFRESH_TOKEN")
        self.access_token = config.get("ZOHO_ACCESS_TOKEN")
        self.expires_in = config.get("ACCESS_TOKEN_EXPIRES_IN")
        self.token_timestamp = config.get("ACCESS_TOKEN_TAMESTAMP")

    def _save_token_data(self, access_token, expires_in, refresh_token=None):
        """Sauvegarde toutes les données du token en une seule écriture."""
        config = load_config()
        config["ZOHO_ACCESS_TOKEN"] = access_token
        config["ACCESS_TOKEN_EXPIRES_IN"] = str(expires_in)
        config["ACCESS_TOKEN_TAMESTAMP"] = str(time.time())
        if refresh_token:
            config["ZOHO_REFRESH_TOKEN"] = refresh_token
        save_config(config)

        self.access_token = access_token
        self.expires_in = expires_in
        self.token_timestamp = time.time()
        if refresh_token:
            self.refresh_token = refresh_token

    def _is_token_valid(self) -> bool:
        """Vérifie si le token actuel est encore valide (avec 5 min de marge)."""
        if not self.access_token or not self.token_timestamp or not self.expires_in:
            return False
        try:
            elapsed = time.time() - float(self.token_timestamp)
            return elapsed < float(self.expires_in) - 300
        except (ValueError, TypeError):
            return False

    def get_access_token(self):
        """Obtenir un nouvel access token avec le granted_code."""
        if not self.granted_code:
            print("[ERROR] Aucun granted_code disponible !")
            return None

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": self.granted_code,
        }

        response = requests.post(ZOHO_TOKEN_URL, data=data)
        token_data = response.json()

        if response.status_code == 200 and "access_token" in token_data:
            refresh_token = token_data.get("refresh_token")
            if not refresh_token:
                print("[WARNING] Aucun refresh_token dans la réponse. Regenerez le granted_code avec access_type=offline")
            self._save_token_data(
                token_data["access_token"],
                token_data["expires_in"],
                refresh_token,
            )
            print("[OK] Access token généré avec succès.")
            return self.access_token

        print(f"[ERROR] Récupération du token : {token_data}")
        return None

    def refresh_access_token(self):
        """Rafraîchir l'access token à l'aide du refresh token."""
        if not self.refresh_token:
            print("[ERROR] Aucun refresh_token disponible.")
            return None

        print("[INFO] Rafraîchissement du token...")

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
        }

        response = requests.post(ZOHO_TOKEN_URL, data=data)
        token_data = response.json()

        if response.status_code == 200 and "access_token" in token_data:
            self._save_token_data(
                token_data["access_token"],
                token_data["expires_in"],
                token_data.get("refresh_token"),
            )
            print("[OK] Token rafraîchi avec succès.")
            return self.access_token

        print(f"[ERROR] Rafraîchissement du token : {token_data}")
        # Supprimer le refresh_token invalide
        config = load_config()
        config.pop("ZOHO_REFRESH_TOKEN", None)
        save_config(config)
        self.refresh_token = None
        return None

    def get_valid_access_token(self):
        """Retourne un access token valide, en le rafraîchissant si nécessaire."""
        if self._is_token_valid():
            return self.access_token

        # Essayer le refresh_token d'abord
        if self.refresh_token:
            token = self.refresh_access_token()
            if token:
                return token
            print("[INFO] Refresh échoué, tentative avec granted_code...")

        # Fallback sur le granted_code
        if self.granted_code:
            return self.get_access_token()

        print("[ERROR] Aucun refresh_token ni granted_code disponible.")
        return None
