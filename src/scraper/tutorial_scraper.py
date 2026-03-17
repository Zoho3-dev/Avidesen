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
        url = f"{TUTORIAL_BASE_URL}/{category}/ref/{product_ref}"
        
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
            if response.status_code != 404:
                print(f"[WARNING] Erreur pour {product_ref} dans {category}: {e}")
    
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


def _fix_lazy_images(soup) -> None:
    """Pré-traitement : résout les images lazy-loaded et supprime les <noscript> dupliqués."""
    # 1. Supprimer les <noscript> contenant des <img> (doublons)
    for noscript in soup.find_all('noscript'):
        if noscript.find('img'):
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
    for widget in section.find_all('div', class_='elementor-widget-container'):
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

            # Extraire le contenu utile (p, ul, ol, table, div avec du texte)
            inner = child.find_all(['p', 'ul', 'ol', 'table'])
            if inner:
                for elem in inner:
                    html_parts.append(str(elem))
            elif child.get_text(strip=True):
                html_parts.append(str(child))
    return '\n'.join(html_parts)


def _build_step_html(img_urls: list, step_title: str, step_body: str) -> str:
    """Construit le HTML d'une étape avec layout image gauche / texte droite.

    Args:
        img_urls: Liste d'URLs d'images principales (peut être vide).
        step_title: Titre de l'étape.
        step_body: HTML du corps de l'étape (peut contenir des icônes inline).
    """
    img_cell = ''
    if img_urls:
        imgs_html = ''
        for url in img_urls:
            imgs_html += (
                f'<img src="{url}" alt="{step_title}" '
                f'style="max-width: 300px; width: 100%; height: auto; '
                f'border-radius: 4px; margin-bottom: 8px; display: block;" />'
            )
        img_cell = (
            f'<td style="width: 40%; vertical-align: top; padding: 10px;">'
            f'{imgs_html}'
            f'</td>'
        )
    text_cell = (
        f'<td style="vertical-align: top; padding: 10px;">'
        f'<h3 style="color: #2E86C1; font-size: 1.15em; margin: 0 0 0.5em 0; font-weight: 600;">{step_title}</h3>'
        f'{step_body}'
        f'</td>'
    )
    if img_cell:
        return (
            f'<table style="width: 100%; border-collapse: collapse; margin: 1.5em 0;" cellpadding="0" cellspacing="0">'
            f'<tr>{img_cell}{text_cell}</tr></table>'
        )
    return (
        f'<div style="margin: 1.5em 0;">'
        f'<h3 style="color: #2E86C1; font-size: 1.15em; margin: 0 0 0.5em 0; font-weight: 600;">{step_title}</h3>'
        f'{step_body}'
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
        # La colonne image n'a pas de texte significatif (hors alt d'images)
        col_a_text = col_a.get_text(strip=True)
        col_b_text = col_b.get_text(strip=True)
        col_a_main_imgs = _collect_main_images(col_a)
        col_b_main_imgs = _collect_main_images(col_b)

        if col_a_main_imgs and not col_a_text:
            img_col, text_col = col_a, col_b
        elif col_b_main_imgs and not col_b_text:
            img_col, text_col = col_b, col_a
        elif col_a_main_imgs and len(col_a_main_imgs) >= len(col_b_main_imgs):
            img_col, text_col = col_a, col_b
        else:
            img_col, text_col = col_a, col_b

        # Collecter TOUTES les images principales de la colonne image
        img_urls = _collect_main_images(img_col)

        # Titre depuis la colonne texte
        col_heading = text_col.find(['h3', 'h2'])
        title = col_heading.get_text(strip=True) if col_heading else heading_text

        # Corps (avec icônes inline préservées)
        body = _extract_section_text(text_col)

        return _build_step_html(img_urls, title, body)

    else:
        # --- Layout sans colonnes : contenu séquentiel ---
        img_urls = _collect_main_images(section)
        body = _extract_section_text(section)

        # Gérer les tableaux autonomes
        tables = section.find_all('table')
        if tables and not body.strip():
            table_html = '\n'.join(str(t) for t in tables)
            if heading_text:
                return (
                    f'<div style="margin: 1.5em 0;">'
                    f'<h3 style="color: #2E86C1; font-size: 1.15em; margin: 0 0 0.5em 0; '
                    f'font-weight: 600;">{heading_text}</h3>'
                    f'{table_html}'
                    f'</div>'
                )
            return f'<div style="margin: 1em 0;">{table_html}</div>'

        if heading_text and img_urls:
            return _build_step_html(img_urls, heading_text, body)
        elif heading_text:
            return (
                f'<div style="margin: 1.5em 0;">'
                f'<h3 style="color: #2E86C1; font-size: 1.15em; margin: 0 0 0.5em 0; '
                f'font-weight: 600;">{heading_text}</h3>'
                f'{body}'
                f'</div>'
            )
        elif body.strip():
            return f'<div style="margin: 1em 0;">{body}</div>'
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
        all_sections = soup.find_all('section', class_=True)

        intro_html = ''
        metadata_html = ''
        content_html = ''
        in_content_zone = False  # Passe à True après la metadata / sommaire

        # Mots-clés de sections footer (à ignorer, pas le breadcrumb)
        FOOTER_KEYWORDS = ['Restons connectés', 'A propos d']

        for section in all_sections:
            text = section.get_text(strip=True)

            # Ignorer les sections vides
            if len(text) < 10:
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
                desc_parts = []
                for widget in section.find_all('div', class_='elementor-widget-container'):
                    for elem in widget.find_all(['p', 'ul', 'ol']):
                        elem_text = elem.get_text(strip=True)
                        if elem_text and elem_text != title:
                            elem['style'] = 'margin: 0.5em 0; line-height: 1.6;'
                            desc_parts.append(str(elem))
                if desc_parts:
                    intro_html = (
                        '<div style="margin-bottom: 1.5em;">'
                        + '\n'.join(desc_parts)
                        + '</div>'
                    )
                continue

            # --- Metadata (difficulté, temps, étapes) ---------------------------
            if 'Difficulté' in text and 'Temps nécessaire' in text:
                meta_items = []
                for widget in section.find_all('div', class_='elementor-widget-container'):
                    item_text = widget.get_text(strip=True)
                    if item_text and len(item_text) > 2:
                        meta_items.append(item_text)
                if meta_items:
                    metadata_html = (
                        '<div style="background: #f5f7fa; border-radius: 6px; '
                        'padding: 12px 16px; margin-bottom: 1.5em; font-size: 0.9em; '
                        'color: #555;">'
                    )
                    for item in meta_items:
                        metadata_html += f'<span style="margin-right: 20px;">{item}</span>'
                    metadata_html += '</div>'
                in_content_zone = True
                continue

            # --- "Ce tutoriel est applicable pour" – capturer les produits ------
            if 'Ce tutoriel est applicable' in text[:40]:
                product_names = []
                for span in section.find_all('span', class_='ae-term-item'):
                    a_tag = span.find('a')
                    name = a_tag.get_text(strip=True) if a_tag else span.get_text(strip=True)
                    if name:
                        product_names.append(name)
                if not product_names:
                    # Fallback : extraire le texte brut après le titre
                    raw = text.replace('Ce tutoriel est applicable pour :', '').strip()
                    if raw:
                        product_names = [p.strip() for p in raw.split(',') if p.strip()]
                if product_names:
                    applicable_html = (
                        '<div style="background: #e8f4f8; border-left: 4px solid #2E86C1; '
                        'padding: 12px 16px; margin-bottom: 1.5em; border-radius: 4px;">'
                        '<strong>Ce tutoriel est applicable pour :</strong><br/>'
                        + ', '.join(product_names)
                        + '</div>'
                    )
                    intro_html += applicable_html
                continue

            # --- "Les étapes du tutoriel" (sommaire global) – ignorer -----------
            if 'Les étapes du tutoriel' in text[:40]:
                in_content_zone = True
                continue

            # --- Zone de contenu : capturer TOUTE section -----------------------
            if in_content_zone:
                section_html = _build_content_section_html(section)
                if section_html:
                    content_html += section_html

        # --- 3. Assembler le HTML final -----------------------------------------
        html_parts = []

        if intro_html:
            html_parts.append(intro_html)
        if metadata_html:
            html_parts.append(metadata_html)
        if content_html:
            html_parts.append(
                '<h2 style="color: #2E86C1; font-size: 1.4em; margin: 1.5em 0 0.5em 0; '
                'font-weight: 600;">Les étapes du tutoriel :</h2>'
            )
            html_parts.append(content_html)

        html_content = '\n'.join(html_parts)

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

