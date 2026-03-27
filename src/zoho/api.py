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


def check_article_exists(title: str = None, permalink: str = None, category_id: str = None) -> Optional[Dict]:
    """Vérifie si un article existe déjà dans Zoho KB par titre ou permalink."""
    if not title and not permalink:
        return None
    
    zoho_config = get_zoho_config()
    headers = _build_zoho_headers(zoho_config["access_token"], zoho_config["org_id"])
    
    # Récupérer TOUS les articles (avec pagination)
    all_articles = []
    page_from = 1
    limit = 50
    
    while True:
        url = f"{ZOHO_ARTICLES_URL}?from={page_from}&limit={limit}"
        if category_id:
            url += f"&categoryId={category_id}"
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                break
            
            data = response.json()
            articles = data.get("data", [])
            if not articles:
                break
            
            all_articles.extend(articles)
            
            # Si on a reçu moins que la limite, c'est la dernière page
            if len(articles) < limit:
                break
            page_from += limit
            
        except (requests.RequestException, KeyError):
            break
    
    # Recherche par titre (insensible à la casse)
    if title:
        title_lower = title.lower().strip()
        for article in all_articles:
            article_title = article.get("title", "").lower().strip()
            if article_title == title_lower:
                return article
    
    return None


def create_tutorial_article_with_check(
    title: str, html_content: str, category: str = None, category_id: str = None
) -> Optional[Dict]:
    """Crée un article tutoriel seulement s'il n'existe pas déjà."""
    if not category_id:
        category_id = get_zoho_tutorial_category_id(category)
    
    # Vérifier si l'article existe déjà
    existing = check_article_exists(title=title, category_id=category_id)
    if existing:
        print(f"[SKIP] Article existe déjà: {title} (ID: {existing.get('id')})")
        return existing
    
    # Créer l'article s'il n'existe pas
    return create_tutorial_article(title, html_content, category, category_id)


def _build_zoho_headers(access_token: str, org_id: str) -> Dict[str, str]:
    """Construit les headers d'authentification pour l'API Zoho."""
    return {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "orgId": org_id,
        "Content-Type": "application/json",
    }


def create_tutorial_article(
    title: str, html_content: str, category: str = None, category_id: str = None
) -> Optional[Dict]:
    """
    Crée un article tutoriel dans Zoho Desk.
    Rafraîchit automatiquement le token en cas de 401.

    Args:
        title: Titre de l'article.
        html_content: Contenu HTML de l'article.
        category: Catégorie du tutoriel (motorisation, visiophone, securite, solaire, domotique).
        category_id: ID de la catégorie Zoho (prioritaire sur category si fourni).

    Returns:
        Réponse JSON de l'API en cas de succès, None sinon.
    """
    if not category_id:
        category_id = get_zoho_tutorial_category_id(category)

    permalink = sanitize_permalink(title)

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
        result = _zoho_request("POST", ZOHO_ARTICLES_URL, body, title)

    return result


def _zoho_request(
    method: str, url: str, body: dict, label: str = "", is_permalink_retry: bool = False
) -> Optional[Dict]:
    """
    Exécute une requête Zoho sans retry automatique.

    Args:
        method: Méthode HTTP (GET, POST, etc.).
        url: URL de l'API.
        body: Corps de la requête.
        label: Label pour les logs.
        is_permalink_retry: True si c'est un retry avec permalink fallback.

    Returns:
        Réponse JSON en cas de succès, None sinon.
    """
    zoho_config = get_zoho_config()
    headers = _build_zoho_headers(zoho_config["access_token"], zoho_config["org_id"])
    response = None

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

        # Token expiré → arrêter sans rafraîchissement automatique
        if response.status_code == 401:
            print("[ERROR] Token expiré. Lancez 'py refresh_token.py' manuellement.")
            return None

        # Erreur de permalink → retry avec fallback si ce n'est pas déjà un retry
        if (
            response is not None
            and response.status_code == 422
            and not is_permalink_retry
            and "permalink" in response.text
        ):
            print(f"[ERROR] Permalink invalide: {body.get('permalink', 'N/A')}")
            return None  # Signal pour retry avec permalink fallback

        if response is not None:
            print(f"[ERROR] Zoho ({response.status_code}): {response.text[:200]}")
        else:
            print("[ERROR] Zoho: Pas de réponse du serveur")
        return None

    except requests.RequestException as e:
        print(f"[ERROR] Echec de la requete Zoho : {e}")
        return None
