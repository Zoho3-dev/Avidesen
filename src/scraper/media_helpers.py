"""
Helpers pour le traitement des images et vidéos dans les pages Avidsen.
Gère le lazy loading, la détection d'icônes inline et l'extraction YouTube.
"""

from typing import List, Optional

from src.scraper.styles import AVIDSEN_BASE_URL, INLINE_ICON_MAX_SIZE


def resolve_img_src(img) -> Optional[str]:
    """Résout l'URL réelle d'une image (gestion du lazy loading)."""
    real_url = (img.get('data-lazy-src') or
                img.get('data-src') or
                img.get('data-original') or
                img.get('src'))
    # Ignorer les placeholders SVG data-uri
    if real_url and real_url.startswith('data:'):
        real_url = None
    if real_url and real_url.startswith('/'):
        real_url = f"{AVIDSEN_BASE_URL}{real_url}"
    return real_url


def is_inline_icon(img) -> bool:
    """Détermine si une balise <img> est une icône inline (petite image dans le texte)."""
    try:
        w = int(img.get('width', 9999))
        h = int(img.get('height', 9999))
    except (ValueError, TypeError):
        return False
    return w <= INLINE_ICON_MAX_SIZE and h <= INLINE_ICON_MAX_SIZE


def is_standalone_image_wrapper(element) -> bool:
    """Vérifie si un élément ne contient qu'une image principale (pas d'icône inline)."""
    if not element.find('img'):
        return False
    text = element.get_text(strip=True)
    if text:
        return False
    imgs = element.find_all('img')
    return all(not is_inline_icon(img) for img in imgs)


def collect_main_images(element) -> List[str]:
    """Collecte toutes les URLs d'images principales (non-icônes) dans un élément."""
    urls = []
    for img in element.find_all('img'):
        if is_inline_icon(img):
            continue
        url = img.get('src') or resolve_img_src(img)
        if url and not url.startswith('data:'):
            urls.append(url)
    return urls


def extract_youtube_html(element) -> str:
    """Extrait le HTML des vidéos YouTube intégrées dans un élément.

    Cherche les divs rll-youtube-player (lazy YouTube) ou les iframes YouTube.
    Retourne un iframe responsive prêt à afficher.
    """
    parts = []
    # 1. Divs rll-youtube-player (lazy-loaded YouTube)
    for div in element.find_all('div', class_='rll-youtube-player'):
        video_id = div.get('data-id', '')
        if video_id:
            title = div.get('data-alt', 'Vidéo YouTube')
            parts.append(
                f'<div style="margin: 1.5em 0; width: 100%; text-align: center;">'
                f'<iframe width="100%" height="600" '
                f'src="https://www.youtube.com/embed/{video_id}" '
                f'title="{title}" frameborder="0" '
                f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
                f'gyroscope; picture-in-picture; web-share" '
                f'allowfullscreen style="aspect-ratio: 16/9; border-radius: 6px;"></iframe></div>'
            )
    # 2. Iframes YouTube directes (hors noscript, déjà gérées par rll-youtube-player)
    if not parts:
        for iframe in element.find_all('iframe'):
            src = iframe.get('src', '') or iframe.get('data-src', '')
            if 'youtube' in src or 'youtu.be' in src:
                title = iframe.get('title', 'Vidéo YouTube')
                parts.append(
                    f'<div style="margin: 1.5em 0; width: 100%; text-align: center;">'
                    f'<iframe width="100%" height="600" '
                    f'src="{src}" title="{title}" frameborder="0" '
                    f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
                    f'gyroscope; picture-in-picture; web-share" '
                    f'allowfullscreen style="aspect-ratio: 16/9; border-radius: 6px;"></iframe></div>'
                )
    return '\n'.join(parts)


def fix_lazy_images(soup) -> None:
    """Pré-traitement : résout les images lazy-loaded et supprime les <noscript> dupliqués."""
    # 1. Supprimer les <noscript> contenant des <img> (doublons)
    #    Mais préserver ceux contenant des <iframe> (YouTube fallback)
    for noscript in soup.find_all('noscript'):
        if noscript.find('img') and not noscript.find('iframe'):
            noscript.decompose()
    # 2. Résoudre les src lazy-loaded
    for img in soup.find_all('img'):
        real_src = resolve_img_src(img)
        if real_src:
            img['src'] = real_src
        # Nettoyer les attributs de lazy loading
        for attr in ['data-lazy-src', 'data-src', 'data-original']:
            if img.has_attr(attr):
                del img[attr]
