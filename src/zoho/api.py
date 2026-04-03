"""
Module d'interaction avec l'API Zoho Desk.
Gère la création d'articles tutoriels dans la base de connaissances.
"""

import json
import time
import unicodedata
import requests
from typing import Dict, List, Optional

from src.config.settings import get_zoho_config, get_zoho_tutorial_category_id
from src.utils.text_utils import sanitize_permalink, clean_product_name

ZOHO_BASE_URL = "https://desk.zoho.com/api/v1"
ZOHO_ARTICLES_URL = f"{ZOHO_BASE_URL}/articles"
ZOHO_ROOT_CATEGORIES_URL = f"{ZOHO_BASE_URL}/kbRootCategories"
ZOHO_SECTIONS_URL = f"{ZOHO_BASE_URL}/kbSections"


# ---------------------------------------------------------------------------
# Normalisation des noms de sous-catégories
# ---------------------------------------------------------------------------

def _normalize_name(name: str) -> str:
    """Normalise un nom de sous-catégorie pour comparaison sans doublons.

    - Supprime les suffixes WordPress (N) — ex: « (1) », « (13) »
    - Supprime les espaces en début/fin
    - Met en minuscules
    - Normalise les caractères unicode (accents)
    - Réduit les espaces multiples en un seul
    """
    if not name:
        return ""
    # Supprimer les suffixes WordPress avant toute normalisation
    name = clean_product_name(name)
    name = name.strip().lower()
    name = unicodedata.normalize("NFC", name)
    # Réduire les espaces multiples
    return " ".join(name.split())


# ---------------------------------------------------------------------------
# Registre global des sous-catégories (singleton)
# ---------------------------------------------------------------------------

class SubcategoryRegistry:
    """Cache global et source unique de vérité pour les sous-catégories Zoho KB.

    Garanties :
    - Chaque sous-catégorie n'est créée qu'une seule fois par catégorie parente.
    - Les noms sont normalisés pour éviter les doublons (casse, espaces, accents).
    - Les permalinks sont résolus et mis en cache.
    - Le registre est préchargé depuis l'API lors du premier accès à une catégorie.
    """

    def __init__(self):
        # {parent_category_id: {normalized_name: {"id": str, "name": str, "permalink": str|None}}}
        self._cache: Dict[str, Dict[str, Dict]] = {}
        # Catégories parentes dont le cache a été initialisé depuis l'API
        self._loaded_parents: set = set()

    # -- Chargement initial ------------------------------------------------

    def _ensure_loaded(self, parent_category_id: str) -> None:
        """Charge les sous-catégories existantes depuis l'API si pas encore fait."""
        if parent_category_id in self._loaded_parents:
            return

        self._cache.setdefault(parent_category_id, {})

        existing = get_subcategories(parent_category_id)
        for cat in existing:
            name = cat.get("name", "")
            norm = _normalize_name(name)
            if not norm:
                continue
            # Extraire le permalink depuis translations si disponible
            permalink = None
            for t in cat.get("translations", []):
                if t.get("permalink"):
                    permalink = t["permalink"]
                    break
            self._cache[parent_category_id][norm] = {
                "id": str(cat["id"]),
                "name": name,
                "permalink": permalink,
            }

        self._loaded_parents.add(parent_category_id)
        count = len(self._cache[parent_category_id])
        print(f"[REGISTRY] {count} sous-catégorie(s) chargée(s) pour parent {parent_category_id}")

    # -- Accès public ------------------------------------------------------

    def get_or_create(self, parent_category_id: str, name: str) -> Optional[str]:
        """Retourne l'ID de la sous-catégorie, en la créant si nécessaire.

        Args:
            parent_category_id: ID de la catégorie parente.
            name: Nom de la sous-catégorie (sera normalisé pour la recherche).

        Returns:
            ID de la sous-catégorie, ou None en cas d'erreur.
        """
        self._ensure_loaded(parent_category_id)
        norm = _normalize_name(name)
        if not norm:
            return None

        # Déjà en cache ?
        entry = self._cache[parent_category_id].get(norm)
        if entry:
            print(f"[REGISTRY] Sous-catégorie existante: {entry['name']} (ID: {entry['id']})")
            return entry["id"]

        # Nettoyer le nom avant création (supprimer suffixes WordPress)
        clean_name = clean_product_name(name).strip()
        subcat_id = _create_subcategory_api(parent_category_id, clean_name)
        if subcat_id:
            self._cache[parent_category_id][norm] = {
                "id": subcat_id,
                "name": clean_name,
                "permalink": None,  # sera résolu paresseusement
            }
        return subcat_id

    def get_id(self, parent_category_id: str, name: str) -> Optional[str]:
        """Retourne l'ID d'une sous-catégorie existante, ou None."""
        self._ensure_loaded(parent_category_id)
        norm = _normalize_name(name)
        entry = self._cache[parent_category_id].get(norm)
        return entry["id"] if entry else None

    def get_permalink(self, parent_category_id: str, name: str) -> Optional[str]:
        """Retourne le permalink complet (parent/subcat) d'une sous-catégorie.

        Résout et met en cache le permalink depuis l'API si nécessaire.
        """
        self._ensure_loaded(parent_category_id)
        norm = _normalize_name(name)
        entry = self._cache[parent_category_id].get(norm)
        if not entry:
            return None

        # Permalink déjà connu ?
        if entry.get("permalink"):
            # Résoudre le permalink complet avec le parent
            parent_permalink = self._get_parent_permalink(parent_category_id)
            if parent_permalink:
                return f"{parent_permalink}/{entry['permalink']}"
            return entry["permalink"]

        # Résoudre via l'API
        full_permalink = get_subcategory_permalink(parent_category_id, entry["id"])
        if full_permalink:
            # Extraire la partie sous-catégorie pour le cache
            parts = full_permalink.split("/", 1)
            if len(parts) == 2:
                entry["permalink"] = parts[1]
            else:
                entry["permalink"] = full_permalink
        return full_permalink

    def list_all(self, parent_category_id: str) -> List[Dict]:
        """Liste toutes les sous-catégories connues pour un parent."""
        self._ensure_loaded(parent_category_id)
        return [
            {"id": v["id"], "name": v["name"], "permalink": v.get("permalink")}
            for v in self._cache.get(parent_category_id, {}).values()
        ]

    def clear(self) -> None:
        """Vide le cache (utile pour les tests)."""
        self._cache.clear()
        self._loaded_parents.clear()

    # -- Helpers internes --------------------------------------------------

    _parent_permalinks: Dict[str, Optional[str]] = {}

    def _get_parent_permalink(self, parent_category_id: str) -> Optional[str]:
        """Récupère et cache le permalink de la catégorie parente."""
        if parent_category_id in self._parent_permalinks:
            return self._parent_permalinks[parent_category_id]

        zoho_config = get_zoho_config()
        headers = _build_zoho_headers(zoho_config["access_token"], zoho_config["org_id"])
        url = f"{ZOHO_ROOT_CATEGORIES_URL}/{parent_category_id}/categoryTree"
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                for t in data.get("translations", []):
                    if t.get("permalink"):
                        self._parent_permalinks[parent_category_id] = t["permalink"]
                        return t["permalink"]
        except requests.RequestException:
            pass
        self._parent_permalinks[parent_category_id] = None
        return None


# Instance globale unique
_registry = SubcategoryRegistry()


def get_subcategory_registry() -> SubcategoryRegistry:
    """Retourne le registre global des sous-catégories."""
    return _registry


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


# ---------------------------------------------------------------------------
# Gestion des sous-catégories Zoho KB
# ---------------------------------------------------------------------------

def get_subcategories(parent_category_id: str) -> List[Dict]:
    """
    Récupère les sous-catégories (sections) d'une catégorie parente Zoho KB
    en utilisant l'endpoint categoryTree.

    Args:
        parent_category_id: ID de la catégorie parente (root category).

    Returns:
        Liste de sous-catégories (dictionnaires avec 'id', 'name', etc.).
    """
    zoho_config = get_zoho_config()
    headers = _build_zoho_headers(zoho_config["access_token"], zoho_config["org_id"])

    url = f"{ZOHO_ROOT_CATEGORIES_URL}/{parent_category_id}/categoryTree"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # categoryTree retourne la catégorie racine avec ses enfants
            return data.get("children", [])
        elif response.status_code == 204:
            return []
        else:
            print(f"[WARNING] Impossible de lister les sous-catégories: {response.status_code} - {response.text[:200]}")
            return []
    except requests.RequestException as e:
        print(f"[ERROR] Erreur listing sous-catégories: {e}")
        return []


def get_or_create_subcategory(parent_category_id: str, name: str) -> Optional[str]:
    """
    Trouve ou crée une sous-catégorie dans Zoho KB.
    Délègue au registre global pour garantir l'unicité.

    Args:
        parent_category_id: ID de la catégorie parente.
        name: Nom de la sous-catégorie à trouver ou créer.

    Returns:
        ID de la sous-catégorie, ou None en cas d'erreur.
    """
    return _registry.get_or_create(parent_category_id, name)


def _create_subcategory_api(parent_category_id: str, name: str) -> Optional[str]:
    """Crée une sous-catégorie via l'API Zoho (appel interne, sans vérification de doublon).

    Args:
        parent_category_id: ID de la catégorie parente.
        name: Nom de la sous-catégorie.

    Returns:
        ID de la sous-catégorie créée, ou None en cas d'erreur.
    """
    zoho_config = get_zoho_config()
    headers = _build_zoho_headers(zoho_config["access_token"], zoho_config["org_id"])

    body = {
        "name": name,
        "parentCategoryId": int(parent_category_id),
        "status": "SHOW_IN_HELPCENTER",
        "visibility": "ALL_USERS",
        "translations": [
            {
                "name": name,
                "locale": "fr",
                "description": f"Sous-catégorie pour {name}"
            }
        ]
    }

    try:
        response = requests.post(
            ZOHO_SECTIONS_URL, headers=headers, data=json.dumps(body), timeout=30
        )
        if response.status_code in (200, 201):
            data = response.json()
            cat_id = str(data.get("id"))
            print(f"[OK] Sous-catégorie créée: {name} (ID: {cat_id})")
            return cat_id
        else:
            print(f"[ERROR] Création sous-catégorie '{name}': {response.status_code} - {response.text[:200]}")
            return None
    except requests.RequestException as e:
        print(f"[ERROR] Création sous-catégorie '{name}': {e}")
        return None


def get_subcategory_permalink(parent_category_id: str, subcategory_id: str) -> Optional[str]:
    """
    Retourne le permalink complet d'une sous-catégorie : {parent-permalink}/{subcat-permalink}.
    Essaye de trouver le permalink exact avec suffixe numérique si nécessaire.

    Args:
        parent_category_id: ID de la catégorie parente (root category).
        subcategory_id: ID de la sous-catégorie.

    Returns:
        Chemin permalink (ex: "motorisations-de-portail/avidsen-114375-kit-solaire-universel-pour-motorisation-de-portail-2"), ou None.
    """
    zoho_config = get_zoho_config()
    headers = _build_zoho_headers(zoho_config["access_token"], zoho_config["org_id"])
    url = f"{ZOHO_ROOT_CATEGORIES_URL}/{parent_category_id}/categoryTree"
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            return None
        data = response.json()
        # Permalink de la catégorie parente
        parent_permalink = None
        for t in data.get("translations", []):
            if t.get("permalink"):
                parent_permalink = t["permalink"]
                break
        if not parent_permalink:
            return None
        
        # Chercher la sous-catégorie par ID
        for child in data.get("children", []):
            if str(child.get("id")) == str(subcategory_id):
                for t in child.get("translations", []):
                    if t.get("permalink"):
                        return f"{parent_permalink}/{t['permalink']}"
        
        # Si non trouvé, essayer de deviner le permalink avec suffixe
        # Récupérer le nom de la sous-catégorie via API
        try:
            subcat_url = f"{ZOHO_ROOT_CATEGORIES_URL}/{parent_category_id}/sections/{subcategory_id}"
            subcat_response = requests.get(subcat_url, headers=headers, timeout=30)
            if subcat_response.status_code == 200:
                subcat_data = subcat_response.json()
                for t in subcat_data.get("translations", []):
                    if t.get("permalink"):
                        return f"{parent_permalink}/{t['permalink']}"
        except:
            pass
            
        return None
    except requests.RequestException:
        return None


def get_or_create_product_subcategory(parent_category_id: str, product_name: str) -> Optional[str]:
    """
    Crée ou retrouve une sous-catégorie pour un produit spécifique.
    Utilise le nom complet du produit tel qu'il apparaît sur le site officiel
    (marque + référence + nom) pour nommer la sous-catégorie.

    Ex: "Extel - 720293 - Contact (1)" → sous-catégorie "Extel - 720293 - Contact (1)"

    Args:
        parent_category_id: ID de la catégorie parente (ex: visiophone).
        product_name: Nom complet du produit (depuis le site officiel).

    Returns:
        ID de la sous-catégorie produit.
    """
    subcat_name = product_name.strip()

    return get_or_create_subcategory(parent_category_id, subcat_name)


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

    # Inclure category_id dans le permalink pour garantir l'unicité
    # quand le même tutoriel est publié dans plusieurs sous-catégories
    base_permalink = sanitize_permalink(title)
    permalink = f"{base_permalink}-{str(category_id)[-6:]}"

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
