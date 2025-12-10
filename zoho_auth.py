#zoho_auth.py

import json
import requests
import os
import time

# Charger les variables d'environnement depuis le fichier config.txt
CONFIG_FILE = "config.txt"  # Le fichier de configuration pour stocker les variables

def load_config():
    """Charger les variables depuis le fichier config.txt"""
    config = {}
    try:
        with open(CONFIG_FILE, 'r') as file:
            for line in file.readlines():
                key, value = line.strip().split('=')
                config[key] = value
    except FileNotFoundError:
        print(f"{CONFIG_FILE} non trouvé.")
    return config

def save_config(config):
    """Sauvegarder les variables dans le fichier config.txt"""
    with open(CONFIG_FILE, 'w') as file:
        for key, value in config.items():
            file.write(f"{key}={value}\n")
    print("Configuration sauvegardée avec succès.")

class ZohoAuth:
    def __init__(self, client_id, client_secret, granted_code):
        self.client_id = client_id
        self.client_secret = client_secret
        self.granted_code = granted_code
        self.access_token = None
      
        # Charger les variables depuis config.txt
        config = load_config()
        self.refresh_token = config.get("ZOHO_REFRESH_TOKEN")  # Récupérer le refresh_token
        self.expires_in = config.get("ACCESS_TOKEN_EXPIRES_IN")
        self.token_timestamp = config.get("ACCESS_TOKEN_TAMESTAMP")
        self.access_token = config.get("ZOHO_ACCESS_TOKEN")

    def save_access_token(self, access_token):
        """Enregistrer l'access_token dans le fichier config.txt"""
        if access_token:
            config = load_config()
            config["ZOHO_ACCESS_TOKEN"] = access_token
            save_config(config)
            self.access_token = access_token
            print("Access token enregistré avec succès.")

    def save_expire_access_token(self, expires_in):
        """Enregistrer l'access_token dans le fichier config.txt"""
        if expires_in:
            config = load_config()
            config["ACCESS_TOKEN_EXPIRES_IN"] = expires_in
            save_config(config)
            self.expires_in = expires_in
            #print("Access token enregistré avec succès.")

    def save_access_token_timestamp(self, token_timestamp):
        """Enregistrer l'access_token dans le fichier config.txt"""
        if token_timestamp:
            config = load_config()
            config["ACCESS_TOKEN_TAMESTAMP"] = token_timestamp
            save_config(config)
            self.token_timestamp = token_timestamp

    def save_refresh_token(self, refresh_token):
        """Enregistrer le refresh_token dans le fichier config.txt"""
        if refresh_token:
            config = load_config()
            config["ZOHO_REFRESH_TOKEN"] = refresh_token
            save_config(config)
            self.refresh_token = refresh_token
            print("Refresh token enregistré avec succès.")

    def delete_refresh_token(self):
        """Supprimer le refresh_token du fichier config.txt uniquement s'il existe"""
        config = load_config()
        if "ZOHO_REFRESH_TOKEN" in config:
            del config["ZOHO_REFRESH_TOKEN"]
            save_config(config)
            self.refresh_token = None
            print("ZOHO_REFRESH_TOKEN supprimé du fichier config.txt !")

    def get_access_token(self):
        """Obtenir un nouvel access token et un refresh token avec le granted_code"""
        if self.refresh_token:
            print("Un refresh_token existe déjà, essayons de rafraîchir le token...")
            return self.refresh_access_token()

        if not self.granted_code:
            print("Aucun granted_code disponible !")
            return None

        # Demande un nouvel access_token avec le granted code
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": self.granted_code
        }

        response = requests.post("https://accounts.zoho.com/oauth/v2/token", data=data)
        token_data = response.json()

        if response.status_code == 200 and "access_token" in token_data:
            self.access_token = token_data["access_token"]
            self.expires_in = token_data["expires_in"]
            self.token_timestamp = time.time()

            self.save_access_token(self.access_token)
            self.save_expire_access_token(self.expires_in)
            self.save_access_token_timestamp(self.token_timestamp)

            if "refresh_token" in token_data:
                self.refresh_token = token_data["refresh_token"]
                self.save_refresh_token(self.refresh_token)
                print("Nouveau Refresh Token reçu et enregistré.")
            else:
                print("ATTENTION : Aucun refresh_token renvoyé !")
                self.delete_refresh_token()  # Supprimer si pas de refresh_token

            print("Access token généré avec succès !")
            return self.access_token
        else:
            print("Erreur lors de la récupération du token :", token_data)
            return None

    def refresh_access_token(self):
        """Rafraîchir l'access token à l'aide du refresh token"""
        if not self.refresh_token:
            print("Aucun refresh_token disponible pour rafraîchir le token.")
            return None

        print("Rafraîchissement du access token en cours...")

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }

        response = requests.post("https://accounts.zoho.com/oauth/v2/token", data=data)
        token_data = response.json()

        if response.status_code == 200 and "access_token" in token_data:
            self.access_token = token_data["access_token"]
            self.expires_in = token_data["expires_in"]
            self.token_timestamp = time.time()

            self.save_access_token(self.access_token)
            self.save_expire_access_token(self.expires_in)
            self.save_access_token_timestamp(self.token_timestamp)

            # Si un nouveau refresh_token est renvoyé, on l'enregistre
            new_refresh_token = token_data.get("refresh_token")
            if new_refresh_token:
                self.refresh_token = new_refresh_token
                self.save_refresh_token(new_refresh_token)
                print(f"Nouveau Refresh Token reçu et enregistré : {self.refresh_token}")
            else:
                print("Aucun nouveau refresh_token reçu.")

            print("Access token rafraîchi avec succès !")
            return self.access_token
        else:
            print("Erreur lors du rafraîchissement du token :", token_data)
            # Supprimer le refresh_token en cas d'erreur
            self.delete_refresh_token()
            return None

    def get_valid_access_token(self):
        
        if not self.refresh_token:
            print("generation refresh token depuis granted token!")
            return self.get_access_token()
       
        """Retourne un access token valide, en le rafraîchissant si nécessaire"""
        if not self.access_token or (time.time() - float(self.token_timestamp)) >= float(self.expires_in):
            print("Token expiré ou inexistant. Récupération en cours...")
            return self.refresh_access_token()
        return self.access_token
    
def main():
    # Charger les informations depuis config.txt
    config = load_config()
    CLIENT_ID = config.get("ZOHO_CLIENT_ID")
    CLIENT_SECRET = config.get("ZOHO_CLIENT_SECRET")
    GRANTED_CODE = config.get("GRANTED_CODE")

    # Créer une instance de ZohoAuth avec les informations de votre config.txt
    zoho_auth = ZohoAuth(CLIENT_ID, CLIENT_SECRET, GRANTED_CODE)

    # Récupérer un access token initial ou le rafraîchir avec le refresh token
    #token = zoho_auth.get_access_token()
    #print("Access Token :", token)

    '''# Simuler un accès après expiration
    time.sleep(2)  # Simuler un délai'''
    valid_token = zoho_auth.get_valid_access_token()
    #print("Token valide :", valid_token)

# ---- Test du programme ----
if __name__ == "__main__":
    main()
