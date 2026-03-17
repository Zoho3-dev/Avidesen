"""
Module d'interaction avec l'API Zoho Desk.
Gère la création d'articles tutoriels dans la base de connaissances.
"""

import json
import requests
from typing import Dict, Optional

from src.config.settings import get_zoho_config, get_zoho_tutorial_category_id
from src.utils.text_utils import sanitize_permalink

ZOHO_ARTICLES_URL = "https://desk.zoho.com/api/v1/articles"


def _build_zoho_headers(access_token: str, org_id: str) -> Dict[str, str]:
    """Construit les headers d'authentification pour l'API Zoho."""
    return {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "orgId": org_id,
        "Content-Type": "application/json",
    }


def create_tutorial_article(title: str, html_content: str, category_id: str = None) -> Optional[Dict]:
    """
    Crée un article tutoriel dans Zoho Desk.
    Rafraîchit automatiquement le token en cas de 401.

    Args:
        title: Titre de l'article.
        html_content: Contenu HTML de l'article.
        category_id: ID de la catégorie Zoho (utilise la config par défaut si non fourni).

    Returns:
        Réponse JSON de l'API en cas de succès, None sinon.
    """
    if not category_id:
        category_id = get_zoho_tutorial_category_id()

    permalink = sanitize_permalink(title)
    print(f"[DEBUG] Permalink for '{title[:50]}...': {permalink}")
    
    body = {
        "title": title,
        "permalink": permalink,
        "answer": html_content,
        "categoryId": category_id,
        "status": "Published",
    }

    result = _zoho_request("POST", ZOHO_ARTICLES_URL, body, title)
    
    # Si erreur de permalink, essayer avec un permalink généré par timestamp
    if result is None:
        # Réessayer avec un permalink simple basé sur le timestamp
        import time
        fallback_permalink = f"tutorial-{int(time.time())}"
        body["permalink"] = fallback_permalink
        print(f"[INFO] Retrying with fallback permalink: {fallback_permalink}")
        result = _zoho_request("POST", ZOHO_ARTICLES_URL, body, title, is_permalink_retry=True)
    
    return result


def _zoho_request(method: str, url: str, body: dict, label: str = "", is_permalink_retry: bool = False) -> Optional[Dict]:
    """
    Exécute une requête Zoho avec retry automatique sur 401 (token expiré).

    Args:
        method: Méthode HTTP (GET, POST, etc.).
        url: URL de l'API.
        body: Corps de la requête.
        label: Label pour les logs.
        is_permalink_retry: True si c'est un retry avec permalink fallback.

    Returns:
        Réponse JSON en cas de succès, None sinon.
    """
    for attempt in range(2):
        zoho_config = get_zoho_config()
        headers = _build_zoho_headers(zoho_config["access_token"], zoho_config["org_id"])

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                data=json.dumps(body),
                timeout=30,
            )

            if response.status_code in (200, 201):
                print(f"[OK] Article cree : {label}")
                return response.json()

            # Token expiré → rafraîchir et réessayer
            if response.status_code == 401 and attempt == 0:
                print("[INFO] Token expiré, rafraîchissement automatique...")
                from src.zoho.auth import ZohoAuth
                auth = ZohoAuth()
                auth.refresh_access_token()
                continue

            # Erreur de permalink → retry avec fallback si ce n'est pas déjà un retry
            if (response.status_code == 422 and 
                not is_permalink_retry and 
                "permalink" in response.text):
                print(f"[ERROR] Permalink invalide: {body.get('permalink', 'N/A')}")
                return None  # Signal pour retry avec permalink fallback

            print(f"[ERROR] Zoho ({response.status_code}): {response.text[:200]}")
            return None

        except requests.RequestException as e:
            print(f"[ERROR] Echec de la requete Zoho : {e}")
            return None

    return None
