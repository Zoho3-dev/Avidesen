"""
Utilitaires pour la manipulation de texte.
"""

import re
import time
import unicodedata


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
