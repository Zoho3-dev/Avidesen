"""
Utilitaires pour la manipulation de texte.
"""

import re
import time
import unicodedata


def sanitize_permalink(title: str, max_length: int = 100) -> str:
    """
    Génère un permalink URL-safe à partir d'un titre.

    - Retire les accents
    - Remplace les caractères non alphanumériques par des tirets
    - Transforme en minuscules
    - Tronque à *max_length* caractères

    Args:
        title: Titre à transformer.
        max_length: Longueur maximale du permalink.

    Returns:
        Permalink valide.
    """
    if not title or not title.strip():
        return f"article-{int(time.time())}"

    normalized = unicodedata.normalize('NFKD', title)
    ascii_only = normalized.encode('ascii', 'ignore').decode('ascii').lower()
    slug = re.sub(r'[^a-z0-9]+', '-', ascii_only)
    slug = slug.strip('-')

    if len(slug) > max_length:
        slug = slug[:max_length].rstrip('-')

    if not slug or len(slug) < 3:
        slug = f"article-{int(time.time())}"

    return slug
