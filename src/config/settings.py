"""
Module de gestion de la configuration.
Charge et sauvegarde les paramètres depuis/vers config.txt.
"""

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


def get_zoho_tutorial_category_id():
    """
    Récupère l'ID de la catégorie Zoho pour les tutoriels.

    Returns:
        ID de la catégorie pour les tutoriels.
    """
    config = load_config()
    category_id = config.get("ZOHO_TUTORIAL_CATEGORY_ID")

    if not category_id:
        print("Erreur : ZOHO_TUTORIAL_CATEGORY_ID manquant dans config.txt")
        exit(1)

    return category_id


def get_valid_access_token():
    """
    Obtient un access token valide, en le rafraîchissant automatiquement si expiré.

    Returns:
        Access token valide.
    """
    from src.zoho.auth import ZohoAuth

    auth = ZohoAuth()
    token = auth.get_valid_access_token()

    if not token:
        print("[ERROR] Impossible d'obtenir un token valide.")
        exit(1)

    return token

