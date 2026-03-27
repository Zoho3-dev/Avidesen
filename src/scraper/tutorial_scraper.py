"""
Module de scraping des tutoriels Avidsen.
Extrait les tutoriels et les lie aux produits.
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional

from src.config.settings import HEADERS


# URL de base pour les tutoriels
TUTORIAL_BASE_URL = "https://www.avidsen.com/fr/assistance/tutoriel-sav"
TUTORIAL_CATEGORIES_URL = f"{TUTORIAL_BASE_URL}"


def get_tutorial_categories() -> List[str]:
    """
    Récupère la liste des catégories de tutoriels depuis la page principale.
    Returns:
        Liste des catégories (ex: ['motorisation', 'visiophone', 'solaire'])
    """
    try:
        response = requests.get(TUTORIAL_CATEGORIES_URL, headers=HEADERS, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        categories = []
        # Chercher les liens de catégories
        # Format: /fr/assistance/tutoriel-sav/{categorie}
        links = soup.find_all('a', href=re.compile(r'/fr/assistance/tutoriel-sav/[^/]+$'))
        for link in links:
            href = link.get('href', '')
            match = re.search(r'/tutoriel-sav/([^/]+)$', href)
            if match:
                category = match.group(1)
                if category not in categories:
                    categories.append(category)
        print(f"[OK] Catégories trouvées : {categories}")
        return categories
    except Exception as e:
        print(f"[ERROR] Erreur lors de la récupération des catégories : {e}")
        # Fallback sur des catégories connues
        return ['motorisation', 'visiophone', 'solaire', 'alarme', 'domotique']


def get_product_tutorials(product_ref: str, categories: List[str] = None) -> List[Dict]:
    """
    Récupère les tutoriels associés à un produit en testant toutes les catégories.
    Args:
        product_ref: Référence du produit (ex: '127100')
        categories: Liste des catégories à tester (optionnel)
    Returns:
        Liste de dictionnaires contenant les informations des tutoriels
    """
    if categories is None:
        categories = get_tutorial_categories()
    tutorials = []
    for category in categories:
        # Construire l'URL de la page produit
        # Cas spécial pour domotique qui utilise un format d'URL différent
        if category == 'domotique':
            url = f"https://www.avidsen.com/fr/categorie_tutoriel_domotique/{product_ref}"
        else:
            url = f"{TUTORIAL_BASE_URL}/{category}/ref/{product_ref}"
        response = None
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
            # Si la page existe (status 200)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Chercher les liens vers les tutoriels
                # Format: /fr/assistance/tutoriel-sav/tuto/{slug}
                tutorial_links = soup.find_all('a', href=re.compile(r'/tutoriel-sav/tuto/[^/]+$'))
                for link in tutorial_links:
                    tutorial_url = link.get('href', '')
                    if tutorial_url.startswith('/'):
                        tutorial_url = f"https://www.avidsen.com{tutorial_url}"
                    tutorial_title = link.get_text(strip=True)
                    if tutorial_url and tutorial_title:
                        tutorials.append({
                            'url': tutorial_url,
                            'title': tutorial_title,
                            'category': category
                        })
                if tutorial_links:
                    print(f"[OK] Trouvé {len(tutorial_links)} tutoriel(s) pour {product_ref} dans {category}")
        except Exception as e:
            # Ignorer les erreurs 404 (page n'existe pas pour cette catégorie)
            if response is not None and response.status_code != 404:
                print(f"[WARNING] Erreur pour {product_ref} dans {category}: {e}")
            elif response is None:
                print(f"[WARNING] Erreur pour {product_ref}: {e}")
    return tutorials


# ── Seuil de taille pour distinguer les images principales des icônes inline ──
INLINE_ICON_MAX_SIZE = 100  # pixels (largeur ou hauteur)


def _resolve_img_src(img) -> Optional[str]:
    """Résout l'URL réelle d'une image (gestion du lazy loading)."""
    real_url = (img.get('data-lazy-src') or
                img.get('data-src') or
                img.get('data-original') or
                img.get('src'))
    # Ignorer les placeholders SVG data-uri
    if real_url and real_url.startswith('data:'):
        real_url = None
    if real_url and real_url.startswith('/'):
        real_url = f"https://www.avidsen.com{real_url}"
    return real_url


def _is_inline_icon(img) -> bool:
    """Détermine si une balise <img> est une icône inline (petite image dans le texte)."""
    try:
        w = int(img.get('width', 9999))
        h = int(img.get('height', 9999))
    except (ValueError, TypeError):
        return False
    return w <= INLINE_ICON_MAX_SIZE and h <= INLINE_ICON_MAX_SIZE


def _is_standalone_image_wrapper(element) -> bool:
    """Vérifie si un élément ne contient qu'une image principale (pas d'icône inline)."""
    if not element.find('img'):
        return False
    text = element.get_text(strip=True)
    if text:
        return False
    imgs = element.find_all('img')
    return all(not _is_inline_icon(img) for img in imgs)


def _extract_youtube_html(element) -> str:
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


def _fix_lazy_images(soup) -> None:
    """Pré-traitement : résout les images lazy-loaded et supprime les <noscript> dupliqués."""
    # 1. Supprimer les <noscript> contenant des <img> (doublons)
    #    Mais préserver ceux contenant des <iframe> (YouTube fallback)
    for noscript in soup.find_all('noscript'):
        if noscript.find('img') and not noscript.find('iframe'):
            noscript.decompose()
    # 2. Résoudre les src lazy-loaded
    for img in soup.find_all('img'):
        real_src = _resolve_img_src(img)
        if real_src:
            img['src'] = real_src
        # Nettoyer les attributs de lazy loading
        for attr in ['data-lazy-src', 'data-src', 'data-original']:
            if img.has_attr(attr):
                del img[attr]


def _style_content_table(table) -> None:
    """Ajoute bordures et couleurs alternées gris/blanc à un tableau de contenu."""
    table['style'] = (
        'border-collapse: collapse; width: 100%; margin: 0.5em 0; '
        f'font-size: {SITE_FONT_SIZE}; font-family: {SITE_FONT_FAMILY};'
    )
    for i, tr in enumerate(table.find_all('tr')):
        bg = '#f2f2f2' if i % 2 == 0 else '#ffffff'
        tr['style'] = f'background-color: {bg};'
        for cell in tr.find_all(['td', 'th']):
            cell['style'] = (
                'border: 1px solid #ddd; padding: 8px 12px; '
            )


def _extract_section_text(section, skip_title: bool = True) -> str:
    """Extrait le contenu HTML nettoyé d'une colonne texte Elementor.

    Préserve les icônes inline (<img> de petite taille mélangées au texte)
    tout en ignorant les blocs d'images principales (déjà gérés séparément).

    Args:
        section: Élément BeautifulSoup (colonne ou section).
        skip_title: Si True, ignore les h3 (titres d'étape déjà gérés séparément).

    Returns:
        HTML nettoyé contenant paragraphes, listes, tableaux et icônes inline.
    """
    html_parts = []
    widgets = section.find_all('div', class_='elementor-widget-container')
    top_level_widgets = []
    for widget in widgets:
        parent_widget = widget.find_parent('div', class_='elementor-widget-container')
        if parent_widget not in widgets:
            top_level_widgets.append(widget)
    for widget in top_level_widgets:
        for child in widget.children:
            if not hasattr(child, 'name') or child.name is None:
                continue
            # Ignorer les wrappers qui ne contiennent QUE des images principales
            if _is_standalone_image_wrapper(child):
                continue
            # Ignorer les titres h3 (déjà extraits séparément)
            if skip_title and child.name == 'h3':
                continue
            # Ignorer les wrappers qui ne contiennent qu'un h3
            if child.name == 'div' and child.find('h3') and not child.find(['p', 'ul', 'ol', 'li', 'table']):
                continue
            # Résoudre les icônes inline dans cet élément
            for img in child.find_all('img'):
                if _is_inline_icon(img):
                    real_src = img.get('src', '')
                    if real_src:
                        img['style'] = 'vertical-align: middle; max-height: 40px; display: inline;'
            # Styler les tableaux de contenu (bordures + couleurs alternées)
            if child.name == 'table':
                _style_content_table(child)
            # Extraire le contenu utile (p, ul, ol, table, div avec du texte)
            if child.name in ('p', 'ul', 'ol', 'table'):
                html_parts.append(str(child))
            else:
                inner = child.find_all(['p', 'ul', 'ol', 'table'], recursive=False)
                if inner:
                    for elem in inner:
                        if elem.name == 'table':
                            _style_content_table(elem)
                        html_parts.append(str(elem))
                elif child.get_text(strip=True):
                    html_parts.append(str(child))
    return '\n'.join(html_parts)


# Couleurs du site Avidsen
SITE_HEADING_COLOR = '#334956'  # --e-global-color-primary
SITE_ACCENT_COLOR = '#00AEDD'   # --e-global-color-secondary
SITE_GREY_BG = '#e5e5e5'        # --e-global-color-3e84a7e
SITE_FONT_FAMILY = "'Poppins', 'Helvetica Neue', Arial, sans-serif"
SITE_FONT_SIZE = '15px'


def _has_grey_background(section) -> bool:
    """Vérifie si une section Elementor a un fond gris."""
    data_settings = section.get('data-settings', '')
    if 'background_background' in data_settings:
        return True
    # Vérifier aussi dans les div enfants directs
    for div in section.find_all('div', class_=True, recursive=False):
        ds = div.get('data-settings', '')
        if 'background_background' in ds:
            return True
    return False


def _build_step_html(img_urls: list, step_title: str, step_body: str, grey_bg: bool = False) -> str:
    """Construit le HTML d'une étape avec layout image gauche / texte droite.

    Args:
        img_urls: Liste d'URLs d'images principales (peut être vide).
        step_title: Titre de l'étape.
        step_body: HTML du corps de l'étape (peut contenir des icônes inline).
        grey_bg: Si True, ajoute un fond gris à la section.
    """
    bg_style = f'background-color: {SITE_GREY_BG}; padding: 15px; border-radius: 6px; word-wrap: break-word; overflow-wrap: break-word; ' if grey_bg else 'word-wrap: break-word; overflow-wrap: break-word; '
    border_style = 'border: 1px solid #ddd; border-radius: 6px; '
    
    # Construire le contenu HTML
    imgs_html = ''
    if img_urls:
        for url in img_urls:
            imgs_html += (
                f'<img src="{url}" alt="{step_title}" '
                f'style="width: 100%; height: auto; '
                f'border-radius: 4px; margin-bottom: 8px; display: block;" />'
            )
    
    title_html = ''
    if step_title:
        title_html = (
            f'<h3 style="color: {SITE_HEADING_COLOR}; font-size: 18px; '
            f'font-family: {SITE_FONT_FAMILY}; margin: 0 0 0.5em 0; font-weight: 600;">'
            f'{step_title}</h3>'
        )
    
    # Contenu texte + tables (gardé intact, comme sur le site)
    text_content = f'{title_html}{step_body}'
    
    if img_urls:
        # Layout flexbox responsive (image 40% gauche, texte 60% droite)
        layout = (
            f'<div style="width: 100%; margin: 1em 0; {border_style}{bg_style}">'
            f'<div style="display: flex; flex-wrap: wrap; gap: 0;">'
            f'<div style="flex: 0 0 40%; max-width: 40%; padding: 12px; border-right: 1px solid #ddd; box-sizing: border-box;">'
            f'{imgs_html}'
            f'</div>'
            f'<div style="flex: 0 0 60%; max-width: 60%; padding: 12px 16px; font-size: {SITE_FONT_SIZE}; '
            f'font-family: {SITE_FONT_FAMILY}; word-wrap: break-word; overflow-wrap: break-word; box-sizing: border-box;">'
            f'{text_content}'
            f'</div>'
            f'</div>'
            f'</div>'
        )
        return layout
    else:
        # Pas d'image : simple div
        return (
            f'<div style="margin: 1em 0; {border_style}{bg_style} padding: 12px;">'
            f'{text_content}'
            f'</div>'
        )


def _collect_main_images(element) -> List[str]:
    """Collecte toutes les URLs d'images principales (non-icônes) dans un élément."""
    urls = []
    for img in element.find_all('img'):
        if _is_inline_icon(img):
            continue
        url = img.get('src') or _resolve_img_src(img)
        if url and not url.startswith('data:'):
            urls.append(url)
    return urls


def _build_content_section_html(section) -> str:
    """Construit le HTML d'une section de contenu Elementor.

    Gère automatiquement les layouts :
      - 2 colonnes (image | texte) → table avec images à gauche, texte + icônes à droite
      - 1 colonne ou sans colonnes → contenu séquentiel
    Préserve les icônes inline dans le texte et capture TOUTES les images principales.
    """
    grey_bg = _has_grey_background(section)
    # Chercher les colonnes Elementor (col-50, col-33, etc.)
    cols = section.find_all('div', class_=re.compile(r'elementor-col-\d+'))
    # Dédupliquer : garder seulement les colonnes de premier niveau
    unique_cols = []
    for col in cols:
        parent_col = col.find_parent('div', class_=re.compile(r'elementor-col-\d+'))
        if parent_col not in cols:
            unique_cols.append(col)
    # Détecter le titre (h3 ou h2) de la section
    heading = section.find(['h3', 'h2'])
    heading_text = heading.get_text(strip=True) if heading else ''
    if len(unique_cols) >= 2:
        # --- Layout 2 colonnes : image | texte ---
        col_a = unique_cols[0]
        col_b = unique_cols[1]
        # Déterminer quelle colonne est la colonne image
        col_a_text = col_a.get_text(strip=True)
        col_b_text = col_b.get_text(strip=True)
        col_a_main_imgs = _collect_main_images(col_a)
        col_b_main_imgs = _collect_main_images(col_b)
        if col_a_main_imgs and not col_b_main_imgs:
            img_col, text_col = col_a, col_b
        elif col_b_main_imgs and not col_a_main_imgs:
            img_col, text_col = col_b, col_a
        elif col_a_main_imgs and len(col_a_main_imgs) > len(col_b_main_imgs):
            img_col, text_col = col_a, col_b
        elif col_b_main_imgs and len(col_b_main_imgs) > len(col_a_main_imgs):
            img_col, text_col = col_b, col_a
        else:
            img_col, text_col = col_a, col_b
        # Collecter TOUTES les images principales de la colonne image
        img_urls = _collect_main_images(img_col)
        # Titre depuis la colonne texte
        col_heading = text_col.find(['h3', 'h2'])
        title = col_heading.get_text(strip=True) if col_heading else heading_text
        # Corps (avec icônes inline préservées)
        body = _extract_section_text(text_col)
        # Vidéos YouTube dans le layout 2 colonnes
        youtube_html = _extract_youtube_html(section)
        if youtube_html:
            body = youtube_html + '\n' + body
        return _build_step_html(img_urls, title, body, grey_bg=grey_bg)
    else:
        # --- Layout sans colonnes : contenu séquentiel ---
        img_urls = _collect_main_images(section)
        body = _extract_section_text(section)
        bg_style = f'background-color: {SITE_GREY_BG}; padding: 15px; border-radius: 6px; word-wrap: break-word; overflow-wrap: break-word; ' if grey_bg else 'word-wrap: break-word; overflow-wrap: break-word; '
        # Gérer les tableaux autonomes
        tables = section.find_all('table')
        if tables and not body.strip():
            for t in tables:
                _style_content_table(t)
            table_html = '\n'.join(str(t) for t in tables)
            if heading_text:
                return (
                    f'<div style="margin: 1.5em 0; {bg_style}">'
                    f'<h3 style="color: {SITE_HEADING_COLOR}; font-size: 18px; '
                    f'font-family: {SITE_FONT_FAMILY}; margin: 0 0 0.5em 0; '
                    f'font-weight: 600;">{heading_text}</h3>'
                    f'{table_html}'
                    f'</div>'
                )
            return f'<div style="margin: 1em 0; {bg_style}">{table_html}</div>'
        # Vidéos YouTube
        youtube_html = _extract_youtube_html(section)
        if youtube_html:
            result = ''
            if heading_text:
                result += (
                    f'<h3 style="color: {SITE_HEADING_COLOR}; font-size: 18px; '
                    f'font-family: {SITE_FONT_FAMILY}; margin: 1em 0 0.5em 0; '
                    f'font-weight: 600;">{heading_text}</h3>'
                )
            result += youtube_html
            if body.strip():
                result += f'<div style="margin: 0.5em 0;">{body}</div>'
            return f'<div style="margin: 1.5em 0; {bg_style}">{result}</div>'
        if heading_text and img_urls:
            return _build_step_html(img_urls, heading_text, body, grey_bg=grey_bg)
        elif heading_text:
            return (
                f'<div style="margin: 1.5em 0; {bg_style}">'
                f'<h3 style="color: {SITE_HEADING_COLOR}; font-size: 18px; '
                f'font-family: {SITE_FONT_FAMILY}; margin: 0 0 0.5em 0; '
                f'font-weight: 600;">{heading_text}</h3>'
                f'{body}'
                f'</div>'
            )
        elif body.strip():
            return f'<div style="margin: 1em 0; {bg_style}">{body}</div>'
        elif img_urls:
            # Images seules sans texte ni titre
            imgs_html = ''
            for url in img_urls:
                imgs_html += (
                    f'<div style="text-align: center; margin: 10px 0;">'
                    f'<img src="{url}" alt="" '
                    f'style="max-width: 600px; width: 100%; height: auto; '
                    f'border-radius: 4px; display: inline-block;" />'
                    f'</div>'
                )
            return f'<div style="margin: 1em 0; {bg_style}">{imgs_html}</div>'
        return ''


def scrape_tutorial_content(tutorial_url: str) -> Optional[Dict]:
    """
    Extrait le contenu complet d'un tutoriel Avidsen.

    Stratégie : parcourir toutes les sections Elementor de la page.
    On identifie d'abord l'intro et les métadonnées, puis on capture
    TOUTES les sections de contenu restantes (pas seulement les "Etape")
    jusqu'au footer. Cela garantit que les sous-étapes et contenus
    intermédiaires sont aussi inclus.

    Args:
        tutorial_url: URL du tutoriel

    Returns:
        Dictionnaire contenant le contenu du tutoriel, ou None en cas d'erreur.
    """
    try:
        response = requests.get(tutorial_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        # --- 0. Pré-traitement : résoudre lazy images + supprimer <noscript> ---
        _fix_lazy_images(soup)
        # --- 1. Titre -----------------------------------------------------------
        title_elem = soup.find('h1')
        title = title_elem.get_text(strip=True) if title_elem else "Tutoriel"
        # --- 2. Parcourir les sections Elementor --------------------------------
        all_sections_raw = soup.find_all('section', class_=True)
        # Classifier chaque section : feuille (leaf) ou parent
        leaf_sections = set()
        for s in all_sections_raw:
            child_sections = s.find_all('section', class_=True, recursive=True)
            is_leaf = not any(cs is not s for cs in child_sections)
            if is_leaf:
                leaf_sections.add(id(s))
        intro_html = ''
        metadata_html = ''
        video_html = ''
        content_html = ''
        in_content_zone = False
        # Mots-clés de sections footer (à ignorer)
        FOOTER_KEYWORDS = ['Restons connectés', 'A propos d']
        # Mots-clés de contenu (activent in_content_zone si on ne l'a pas encore détecté)
        CONTENT_KEYWORDS = ['Etape ', 'ATTENTION', 'RAPPEL', 'Conseil', 'Extra :', 'SOLUTION', 'Methode ']
        # On parcourt TOUTES les sections pour détecter les zones,
        # mais on n'extrait le contenu QUE des sections feuilles
        for section in all_sections_raw:
            text = section.get_text(strip=True)
            is_leaf = id(section) in leaf_sections
            # Ignorer les sections vides (sauf si elles contiennent des images)
            if len(text) < 10 and not _collect_main_images(section):
                continue
            # Arrêter au footer
            if any(kw in text[:60] for kw in FOOTER_KEYWORDS):
                break
            # Ignorer les sections de breadcrumb (Accueil > ...)
            if text.startswith('Accueil'):
                continue
            # --- Introduction (section avec h1) ---------------------------------
            h1 = section.find('h1')
            if h1 and not in_content_zone:
                if not is_leaf:
                    continue
                # Extraire l'image produit de la colonne gauche (col-33)
                intro_img_url = None
                cols = section.find_all('div', class_=re.compile(r'elementor-col-\d+'))
                unique_cols = []
                for col in cols:
                    parent_col = col.find_parent('div', class_=re.compile(r'elementor-col-\d+'))
                    if parent_col not in cols:
                        unique_cols.append(col)
                for col in unique_cols:
                    col_imgs = _collect_main_images(col)
                    col_text = col.get_text(strip=True)
                    if col_imgs and not col_text:
                        intro_img_url = col_imgs[0]
                        break
                desc_parts = []
                for widget in section.find_all('div', class_='elementor-widget-container'):
                    for elem in widget.find_all(['p', 'ul', 'ol']):
                        elem_text = elem.get_text(strip=True)
                        if elem_text and elem_text != title:
                            elem['style'] = (
                                f'margin: 0.5em 0; line-height: 1.6; '
                                f'font-size: {SITE_FONT_SIZE}; font-family: {SITE_FONT_FAMILY};'
                            )
                            desc_parts.append(str(elem))
                # Construire l'intro avec image produit à gauche
                if intro_img_url and desc_parts:
                    intro_html = (
                        f'<table style="width: 100%; border-collapse: collapse; margin-bottom: 1.5em;" '
                        f'cellpadding="0" cellspacing="0"><tr>'
                        f'<td style="width: 120px; vertical-align: top; padding: 10px;">'
                        f'<img src="{intro_img_url}" alt="{title}" '
                        f'style="max-width: 100px; height: auto; border-radius: 4px;" />'
                        f'</td>'
                        f'<td style="vertical-align: top; padding: 10px;">'
                        + '\n'.join(desc_parts)
                        + '</td></tr></table>'
                    )
                elif desc_parts:
                    intro_html = (
                        '<div style="margin-bottom: 1.5em;">'
                        + '\n'.join(desc_parts)
                        + '</div>'
                    )
                continue
            # --- Metadata (difficulté, temps, étapes) ---------------------------
            if 'Difficulté' in text and 'Temps nécessaire' in text:
                # Note: can be leaf OR parent (when it has child Référence sections)
                cols = section.find_all('div', class_=re.compile(r'elementor-col-\d+'))
                unique_cols = []
                for col in cols:
                    pc = col.find_parent('div', class_=re.compile(r'elementor-col-\d+'))
                    if pc not in cols:
                        unique_cols.append(col)
                if len(unique_cols) >= 2:
                    left_col = unique_cols[0]
                    right_col = unique_cols[1]
                    # Left column: metadata items (leaf widgets only)
                    left_items = []
                    for w in left_col.find_all('div', class_='elementor-widget-container'):
                        if w.find('div', class_='elementor-widget-container'):
                            continue
                        t = w.get_text(strip=True)
                        if t and len(t) > 2:
                            t = re.sub(r':(\S)', r': \1', t)
                            t = re.sub(r'(\d+)\s*(minutes|heures?)(minutes|heures?)', r'\1 \2', t)
                            t = re.sub(r'(\d+)(minutes|heures?)', r'\1 \2', t)
                            left_items.append(t)
                    # Right column: pièces détachées / matériel
                    # Use leaf widgets only (no child widget-containers) to avoid merged text
                    right_widgets = right_col.find_all('div', class_='elementor-widget-container')
                    leaf_widgets = []
                    for w in right_widgets:
                        if not w.find('div', class_='elementor-widget-container'):
                            leaf_widgets.append(w)
                    top_widgets = leaf_widgets
                    pieces_heading = ''
                    right_extra = ''
                    ref_rows = []
                    for w in top_widgets:
                        wt = w.get_text(strip=True)
                        if not wt:
                            continue
                        if 'ce(' in wt or 'détach' in wt.lower():
                            pieces_heading = re.sub(r':(\S)', r': \1', wt)
                        elif 'Matériel' in wt and ':' in wt:
                            pieces_heading = re.sub(r':(\S)', r': \1', wt)
                        elif wt.startswith('Référence') or wt.startswith('R\u00e9f'):
                            ref_text = re.sub(r':(\S)', r': \1', wt)
                            ref_rows.append({'ref': ref_text, 'link': None})
                        else:
                            a_tag = w.find('a')
                            if a_tag and ref_rows and ref_rows[-1]['link'] is None:
                                ref_rows[-1]['link'] = (a_tag.get_text(strip=True), a_tag.get('href', ''))
                            elif not ref_rows and pieces_heading:
                                right_extra += f'<div style="margin: 4px 0;">{re.sub(r":([^ ])", r": \\1", wt)}</div>'
                    # Build right column content
                    if pieces_heading or ref_rows or right_extra:
                        right_content = ''
                        if pieces_heading:
                            right_content += (
                                f'<div style="font-weight: 600; color: {SITE_HEADING_COLOR}; '
                                f'margin-bottom: 8px; font-size: 14px;">{pieces_heading}</div>'
                            )
                        right_content += right_extra
                        for row in ref_rows:
                            ref_text = row['ref']
                            if row['link']:
                                lnk_text, lnk_href = row['link']
                                # Ensure full URL for relative paths
                                if lnk_href.startswith('/'):
                                    lnk_href = f'https://www.avidsen.com{lnk_href}'
                                right_content += (
                                    f'<div style="margin: 4px 0;">'
                                    f'<span>{ref_text}</span>'
                                    f'&nbsp;&nbsp;&nbsp;'
                                    f'<a href="{lnk_href}" target="_blank" rel="noopener noreferrer" '
                                    f'style="color: {SITE_ACCENT_COLOR}; '
                                    f'text-decoration: none;">{lnk_text}</a></div>'
                                )
                            else:
                                right_content += f'<div style="margin: 4px 0;">{ref_text}</div>'
                        left_content = ''
                        for item in left_items:
                            left_content += f'<div style="margin: 4px 0;">{item}</div>'
                        metadata_html = (
                            f'<table style="width: 100%; background: {SITE_GREY_BG}; border-radius: 6px; '
                            f'border-collapse: collapse; margin-bottom: 1.5em; font-size: 13px; '
                            f'font-family: {SITE_FONT_FAMILY}; color: #555;" cellpadding="0" cellspacing="0">'
                            f'<tr>'
                            f'<td style="width: 50%; vertical-align: top; padding: 16px;">{left_content}</td>'
                            f'<td style="width: 50%; vertical-align: top; padding: 16px;">{right_content}</td>'
                            f'</tr></table>'
                        )
                    else:
                        metadata_html = (
                            f'<div style="background: {SITE_GREY_BG}; border-radius: 6px; '
                            f'padding: 12px 16px; margin-bottom: 1.5em; font-size: 13px; '
                            f'font-family: {SITE_FONT_FAMILY}; color: #555;">'
                        )
                        for item in left_items:
                            metadata_html += f'<div style="margin: 4px 0;">{item}</div>'
                        metadata_html += '</div>'
                else:
                    # Single column metadata (no pièces détachées)
                    meta_items = []
                    for widget in section.find_all('div', class_='elementor-widget-container'):
                        item_text = widget.get_text(strip=True)
                        if item_text and len(item_text) > 2:
                            item_text = re.sub(r':(\S)', r': \1', item_text)
                            item_text = re.sub(r'(\d+)\s*(minutes|heures?)(minutes|heures?)', r'\1 \2', item_text)
                            item_text = re.sub(r'(\d+)(minutes|heures?)', r'\1 \2', item_text)
                            meta_items.append(item_text)
                    if meta_items:
                        metadata_html = (
                            f'<div style="background: {SITE_GREY_BG}; border-radius: 6px; '
                            f'padding: 12px 16px; margin-bottom: 1.5em; font-size: 13px; '
                            f'font-family: {SITE_FONT_FAMILY}; color: #555;">'
                        )
                        for item in meta_items:
                            metadata_html += f'<div style="margin: 4px 0;">{item}</div>'
                        metadata_html += '</div>'
                in_content_zone = True
                continue
            # --- Skip "Référence" sections (already captured in metadata) ----------
            if text.startswith('Référence') or text.startswith('R\u00e9f\u00e9rence'):
                continue
            # --- "Ce tutoriel est applicable pour" – capturer les produits ------
            if 'Ce tutoriel est applicable' in text[:40]:
                if is_leaf:
                    product_items = []
                    for span in section.find_all('span', class_='ae-term-item'):
                        a_tag = span.find('a')
                        if a_tag:
                            name = a_tag.get_text(strip=True)
                            href = a_tag.get('href', '')
                            if href.startswith('/'):
                                href = f'https://www.avidsen.com{href}'
                            if name and href:
                                product_items.append(
                                    f'<a href="{href}" target="_blank" rel="noopener noreferrer" '
                                    f'style="color: {SITE_ACCENT_COLOR}; text-decoration: none;">{name}</a>'
                                )
                            elif name:
                                product_items.append(name)
                        else:
                            name = span.get_text(strip=True)
                            if name:
                                product_items.append(name)
                    if not product_items:
                        raw = text.replace('Ce tutoriel est applicable pour :', '').strip()
                        if raw:
                            product_items = [p.strip() for p in raw.split(',') if p.strip()]
                    if product_items:
                        applicable_html = (
                            f'<div style="background: #e8f4f8; border-left: 4px solid {SITE_ACCENT_COLOR}; '
                            f'padding: 12px 16px; margin-bottom: 1.5em; border-radius: 4px; '
                            f'font-size: {SITE_FONT_SIZE}; font-family: {SITE_FONT_FAMILY};">'
                            f'<strong>Ce tutoriel est applicable pour :</strong><br/>'
                            + ', '.join(product_items)
                            + '</div>'
                        )
                        intro_html += applicable_html
                continue
            # --- "Les explications en vidéo" – extraire YouTube, ignorer le heading
            if 'Les explications en vid' in text[:40]:
                if is_leaf and not video_html:
                    video_html = _extract_youtube_html(section)
                continue
            # --- "Les étapes du tutoriel" (sommaire global) – ignorer -----------
            if 'Les étapes du tutoriel' in text[:40]:
                in_content_zone = True
                continue
            # --- Activer la zone de contenu si on détecte un mot-clé de contenu
            if not in_content_zone and any(text.startswith(kw) for kw in CONTENT_KEYWORDS):
                in_content_zone = True
            # --- Zone de contenu : capturer uniquement les feuilles -------------
            if in_content_zone and is_leaf:
                section_html = _build_content_section_html(section)
                if section_html:
                    content_html += section_html
        # --- 3. Assembler le HTML final -----------------------------------------
        html_parts = []
        if intro_html:
            html_parts.append(intro_html)
        if metadata_html:
            html_parts.append(metadata_html)
        if video_html:
            html_parts.append(video_html)
        if content_html:
            html_parts.append(
                f'<h2 style="color: {SITE_HEADING_COLOR}; font-size: 22px; '
                f'font-family: {SITE_FONT_FAMILY}; margin: 1.5em 0 0.5em 0; '
                f'font-weight: 600;">Les étapes du tutoriel :</h2>'
            )
            html_parts.append(content_html)
        html_content = '\n'.join(html_parts)
        # Post-traitement : styler les tableaux de contenu (bordures + alternance)
        final_soup = BeautifulSoup(html_content, 'html.parser')
        for tbl in final_soup.find_all('table'):
            # Ignorer nos propres tables de layout (ont "margin: 1em 0" ou "margin-bottom")
            tbl_style = tbl.get('style', '')
            if 'margin: 1em 0' in tbl_style or 'margin-bottom' in tbl_style:
                continue
            _style_content_table(tbl)
        html_content = str(final_soup)
        if not html_content.strip():
            print(f"[WARNING] Aucun contenu extrait pour {tutorial_url}")
            return None
        tutorial_data = {
            'url': tutorial_url,
            'title': title,
            'html_content': html_content,
            'steps': []
        }
        print(f"[OK] Tutoriel extrait : {title}")
        return tutorial_data
    except Exception as e:
        print(f"[ERROR] Erreur extraction {tutorial_url}: {e}")
        return None