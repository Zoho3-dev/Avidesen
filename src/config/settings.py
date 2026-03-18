"""
Module de gestion de la configuration.
Charge et sauvegarde les paramètres depuis/vers config.txt.
"""
import time
from pathlib import Path

# Fichier de configuration
CONFIG_FILE = "config.txt"

# Headers HTTP pour les requêtes vers le site Avidsen
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# Dossier de sauvegarde des tutoriels
TUTORIALS_FOLDER = Path("tutorials_data")
TUTORIALS_FOLDER.mkdir(exist_ok=True)


def load_config():
    """Charge la configuration depuis config.txt."""
    config = {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip().strip('"\'')
    except FileNotFoundError:
        print("Erreur : Le fichier config.txt est introuvable.")
        print("Veuillez créer un fichier config.txt sur la base de config.example.txt")
        exit(1)
    return config


def save_config(config):
    """Sauvegarde les variables dans le fichier config.txt."""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        for key, value in config.items():
            f.write(f"{key}={value}\n")


def get_zoho_config():
    """
    Charge et valide la configuration Zoho avec rafraîchissement automatique du token.

    Returns:
        Dictionnaire contenant access_token et org_id.
    """
    config = load_config()
    org_id = config.get("ZOHO_ORG_ID")

    if not org_id:
        print("Erreur : ZOHO_ORG_ID manquant dans config.txt")
        exit(1)

    # Obtenir un token valide (rafraîchissement automatique si expiré)
    access_token = get_valid_access_token()

    return {
        "access_token": access_token,
        "org_id": org_id,
    }


def get_zoho_tutorial_category_id(category: str = None):
    """
    Récupère l'ID de la catégorie Zoho correspondante.

    Args:
        category: Catégorie du tutoriel (motorisation, visiophone, securite, solaire, domotique).
                  Si None, retourne la catégorie par défaut.

    Returns:
        ID de la catégorie Zoho.
    """
    config = load_config()

    # Mapping catégorie site -> clé config Zoho
    CATEGORY_MAP = {
        'motorisation': 'ZOHO_TUTORIAL_CATEGORY_PORTAIL_ID',
        'visiophone': 'ZOHO_TUTORIAL_CATEGORY_VISIOPHONE_ID',
        'securite': 'ZOHO_TUTORIAL_CATEGORY_CAMERA_ID',
        'solaire': 'ZOHO_TUTORIAL_CATEGORY_SOLAIRE_ID',
        'domotique': 'ZOHO_TUTORIAL_CATEGORY_DOMOTIQUE_ID',
    }

    if category and category in CATEGORY_MAP:
        config_key = CATEGORY_MAP[category]
        category_id = config.get(config_key)
        if category_id:
            return category_id
        print(f"[WARNING] {config_key} manquant dans config.txt, utilisation de la catégorie par défaut")

    # Fallback sur la catégorie générique

    # Mapping catégorie site -> clé config Zoho
    CATEGORY_MAP = {
        'motorisation': 'ZOHO_TUTORIAL_CATEGORY_PORTAIL_ID',
        'visiophone': 'ZOHO_TUTORIAL_CATEGORY_VISIOPHONE_ID',
        'securite': 'ZOHO_TUTORIAL_CATEGORY_CAMERA_ID',
        'solaire': 'ZOHO_TUTORIAL_CATEGORY_SOLAIRE_ID',
        'domotique': 'ZOHO_TUTORIAL_CATEGORY_DOMOTIQUE_ID',
    }

    if category and category in CATEGORY_MAP:
        config_key = CATEGORY_MAP[category]
        category_id = config.get(config_key)
        if category_id:
            return category_id
        print(f"[WARNING] {config_key} manquant dans config.txt, utilisation de la catégorie par défaut")

    # Fallback sur la catégorie générique
    category_id = config.get("ZOHO_TUTORIAL_CATEGORY_ID")
    if not category_id:
        # Prendre la première catégorie disponible
        for key in CATEGORY_MAP.values():
            category_id = config.get(key)
            if category_id:
                return category_id
        print("Erreur : Aucune catégorie Zoho configurée dans config.txt")
        exit(1)

    return category_id


def get_valid_access_token():
    """
    Retourne un access token valide en utilisant refresh_token si possible,
    sinon utilise le granted_code.

    Returns:
        Access token valide.
    """
    from src.zoho.auth import ZohoAuth

    config = load_config()
    
    # 1) Essayer avec refresh_token si disponible
    if config.get("ZOHO_REFRESH_TOKEN"):
        try:
            auth = ZohoAuth()
            token = auth.refresh_access_token()
            if token:
                return token
        except Exception as e:
            print(f"[WARNING] Échec refresh_token: {e}")
    
    # 2) Fallback sur granted_code
    if config.get("GRANTED_CODE"):
        try:
    auth = ZohoAuth()
            token = auth.get_access_token()
            if token:
                return token
        except Exception as e:
            print(f"[ERROR] Échec granted_code: {e}")
    
    print("[ERROR] Aucun refresh_token ni granted_code disponible.")
        exit(1)

