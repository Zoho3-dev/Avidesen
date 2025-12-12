"""
Utilitaires pour la gestion des fichiers.
"""

import requests
from src.config.settings import HEADERS


def download_file(url, filename):
    """
    Télécharge un fichier depuis une URL vers un chemin local.
    
    Args:
        url: URL du fichier à télécharger
        filename: Chemin local où sauvegarder le fichier
        
    Returns:
        Le chemin du fichier téléchargé
    """
    r = requests.get(url, stream=True, headers=HEADERS, timeout=60)
    r.raise_for_status()
    with open(filename, "wb") as f:
        for chunk in r.iter_content(8192):
            if chunk:
                f.write(chunk)
    print(f"Downloaded: {filename}")
    return filename
