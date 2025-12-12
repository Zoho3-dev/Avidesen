"""
Module de gestion de la configuration.
Charge et sauvegarde les paramètres depuis/vers config.txt.
"""

from pathlib import Path

# Fichier de configuration
CONFIG_FILE = "config.txt"

# Configuration du scraping
BASE_URL_TEMPLATE = "https://www.avidsen.com/fr/produit/page/{page}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
OUTPUT_FOLDER = Path("notices")
OUTPUT_FOLDER.mkdir(exist_ok=True)

# Configuration PDF
FOOTER_BOTTOM_FRAC = 0.15  # Fraction du bas de page à ignorer pour les footers

# Configuration de détection de tableaux
Y_TOLERANCE = 3  # Tolérance en pixels pour grouper les lignes
X_GAP_TOLERANCE = 8  # Tolérance pour les petits espaces entre colonnes


def load_config():
    """Charge la configuration depuis config.txt"""
    config = {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    config[key.strip()] = value.strip().strip('"\'')
    except FileNotFoundError:
        print("Erreur : Le fichier config.txt est introuvable.")
        print("Veuillez créer un fichier config.txt sur la base de config.example.txt")
        exit(1)
    return config


def save_config(config):
    """Sauvegarde les variables dans le fichier config.txt"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        for key, value in config.items():
            f.write(f"{key}={value}\n")


def get_zoho_config():
    """
    Charge et valide la configuration Zoho.
    Retourne un dictionnaire avec les clés nécessaires.
    """
    config = load_config()
    access_token = config.get("ZOHO_ACCESS_TOKEN")
    org_id = config.get("ZOHO_ORG_ID")
    category_id = config.get("ZOHO_CATEGORY_ID")
    
    if not all([access_token, org_id, category_id]):
        print("Erreur: Des variables de configuration Zoho sont manquantes dans config.txt")
        exit(1)
    
    return {
        "access_token": access_token,
        "org_id": org_id,
        "category_id": category_id
    }
