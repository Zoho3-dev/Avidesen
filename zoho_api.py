import json
import requests
import os
import time
import re
import unicodedata

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
        """Enregistrer la durée d'expiration"""
        if expires_in:
            config = load_config()
            config["ACCESS_TOKEN_EXPIRES_IN"] = expires_in
            save_config(config)
            self.expires_in = expires_in

    def save_access_token_timestamp(self, token_timestamp):
        """Enregistrer la date de génération du token"""
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

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": self.granted_code
        }

        response = requests.post("https://accounts.zohoc.com/oauth/v2/token", data=data)
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
                self.delete_refresh_token()

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
            self.delete_refresh_token()
            return None

    def get_valid_access_token(self):
        """Retourne un access token valide, en le rafraîchissant si nécessaire"""
        if not self.refresh_token:
            print("Génération refresh token depuis granted token !")
            return self.get_access_token()
       
        if not self.access_token or (time.time() - float(self.token_timestamp)) >= float(self.expires_in):
            print("Token expiré ou inexistant. Récupération en cours...")
            return self.refresh_access_token()
        return self.access_token

def sanitize_permalink(title: str) -> str:
    """
    Nettoie un titre pour créer un permalink valide pour Zoho Desk.
    - Retire les accents
    - Remplace espaces et caractères invalides par des tirets
    - Transforme en minuscules
    """
    # Convertir les accents en caractères ASCII
    title = unicodedata.normalize('NFKD', title).encode('ASCII', 'ignore').decode('utf-8')
    # Remplacer les caractères non autorisés par des tirets
    title = re.sub(r'[^a-zA-Z0-9\s_-]', '', title)
    # Remplacer les espaces et underscores par un seul tiret
    title = re.sub(r'[\s_]+', '-', title)
    # Supprimer tirets en début/fin
    title = title.strip('-')
    # Limiter la longueur à 50 caractères (Zoho tolère moins de 100)
    return title[:50] or 'article'

def create_kb_article(title: str, answer_text: str) -> dict:
    """
    Crée un article KB dans Zoho Desk.
    Retourne la réponse JSON.
    """
    config = load_config()
    zoho_auth = ZohoAuth(config["ZOHO_CLIENT_ID"], config["ZOHO_CLIENT_SECRET"], config["GRANTED_CODE"])
    token = zoho_auth.get_valid_access_token()

    url = f"{config.get('ZOHO_API_BASE','https://desk.zoho.com/api/v1')}/articles"

    headers = {
        'Authorization': f'Zoho-oauthtoken {token}',
        'orgId': config["ZOHO_ORG_ID"],
        'Content-Type': 'application/json'
    }

    payload = {
        
        'title': title,
        'permalink': sanitize_permalink(title),  # ajouter le permalink correct
        'answer': answer_text,                   # obligatoire
        'categoryId': config["ZOHO_CATEGORY_ID"], # obligatoire
        'status': 'Published'                        # obligatoire: Draft, Published, Review
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print("Erreur création article KB :", response.text)
        response.raise_for_status()

    print("✅ Article KB créé avec succès !")
    return response.json()


def main():
    config = load_config()
    CLIENT_ID = config.get("ZOHO_CLIENT_ID")
    CLIENT_SECRET = config.get("ZOHO_CLIENT_SECRET")
    GRANTED_CODE = config.get("GRANTED_CODE")

    zoho_auth = ZohoAuth(CLIENT_ID, CLIENT_SECRET, GRANTED_CODE)
    valid_token = zoho_auth.get_valid_access_token()

    # Exemple de création d’article :
    create_kb_article("Test API", "<h1>Hello depuis API</h1><p>Ceci est un test.</p>")

if __name__ == "__main__":
    main()
