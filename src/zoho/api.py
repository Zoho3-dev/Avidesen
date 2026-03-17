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

    Args:
        title: Titre de l'article.
        html_content: Contenu HTML de l'article.
        category_id: ID de la catégorie Zoho (utilise la config par défaut si non fourni).

    Returns:
        Réponse JSON de l'API en cas de succès, None sinon.
    """
    zoho_config = get_zoho_config()

    if not category_id:
        category_id = get_zoho_tutorial_category_id()

    headers = _build_zoho_headers(zoho_config["access_token"], zoho_config["org_id"])

    body = {
        "title": title,
        "permalink": sanitize_permalink(title),
        "answer": html_content,
        "categoryId": category_id,
        "status": "Published",
    }

    try:
        response = requests.post(
            ZOHO_ARTICLES_URL,
            headers=headers,
            data=json.dumps(body),
            timeout=30,
        )

        if response.status_code in (200, 201):
            print(f"[OK] Article cree : {title}")
            return response.json()

        print(f"[ERROR] Zoho ({response.status_code}): {response.text[:200]}")
        return None

    except requests.RequestException as e:
        print(f"[ERROR] Echec de la requete Zoho : {e}")
        return None
