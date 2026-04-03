"""
Utilitaires pour la manipulation de texte.
"""

import re
import time
import unicodedata
import requests
from typing import Optional


def clean_product_name(name: str) -> str:
    """Nettoie un nom de produit en supprimant les suffixes WordPress.

    Le site Avidsen ajoute un compteur entre parenthèses à la fin des noms
    de produits (ex: « Avidsen - 114255 - Clavier à code / Digicode (1) »).
    Ce suffixe n'est PAS partie du vrai nom et provoque des doublons de
    sous-catégories dans Zoho KB.

    Supprime :
    - Suffixes de type `` (N)`` où N est un nombre (1 ou plusieurs chiffres)
    - Espaces résiduels en début/fin
    - Tirets ou séparateurs résiduels en fin de chaîne après nettoyage

    Args:
        name: Nom brut du produit (depuis le scraping).

    Returns:
        Nom nettoyé, sans suffixe numérique.
    """
    if not name:
        return ""
    # Supprimer le suffixe (N) en fin de chaîne — ex: " (1)", " (13)", " (102)"
    cleaned = re.sub(r'\s*\(\d+\)\s*$', '', name)
    # Supprimer les espaces / tirets résiduels en fin
    cleaned = cleaned.strip().rstrip('-').rstrip()
    return cleaned


def sanitize_permalink(title: str, max_length: int = 50) -> str:
    """
    Génère un permalink URL-safe compatible Zoho Desk.

    - Retire les accents et caractères spéciaux
    - Remplace les caractères non alphanumériques par des tirets
    - Transforme en minuscules
    - Tronque à *max_length* caractères
    - Évite les tirets consécutifs
    - Longueur plus conservatrice pour Zoho

    Args:
        title: Titre à transformer.
        max_length: Longueur maximale du permalink.

    Returns:
        Permalink valide pour Zoho Desk.
    """
    if not title or not title.strip():
        return f"article-{int(time.time())}"

    # Nettoyer d'abord les caractères problématiques
    cleaned = re.sub(r'[^\w\s\-\'àâäéèêëïîôöùûüÿç]', ' ', title)
    
    # Normaliser et garder seulement les caractères ASCII
    normalized = unicodedata.normalize('NFKD', cleaned)
    ascii_only = normalized.encode('ascii', 'ignore').decode('ascii').lower()
    
    # Remplacer les caractères non alphanumériques par des tirets
    slug = re.sub(r'[^a-z0-9]+', '-', ascii_only)
    
    # Nettoyer les tirets en début/fin et multiples
    slug = slug.strip('-')
    slug = re.sub(r'-{2,}', '-', slug)

    # Tronquer proprement (pas au milieu d'un mot)
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip('-')

    # Fallback si le slug est trop court ou vide
    if not slug or len(slug) < 3:
        slug = f"article-{int(time.time())}"

    # S'assurer qu'il ne commence/termine pas par un tiret
    slug = slug.strip('-')
    
    # Dernière vérification : doit contenir au moins une lettre
    if not re.search(r'[a-z]', slug):
        slug = f"article-{int(time.time())}"
    
    return slug


def resilient_request(url: str, headers: dict, timeout: int = 45, max_retries: int = 3) -> Optional[requests.Response]:
    """Fait une requête HTTP avec retries et backoff exponentiel.

    Args:
        url: URL à requêter.
        headers: Headers HTTP.
        timeout: Timeout par tentative (secondes).
        max_retries: Nombre maximum de tentatives.

    Returns:
        Response en cas de succès, None sinon.
    """
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except (requests.RequestException, requests.HTTPError) as exc:
            if attempt == max_retries:
                print(f"[ERROR] Échec après {max_retries} tentatives pour {url}: {exc}")
                return None
            wait = min(2 ** attempt, 10)  # Exponential backoff, max 10s
            print(f"[WARNING] Tentative {attempt}/{max_retries} échouée pour {url} — retry dans {wait}s...")
            time.sleep(wait)
    return None
