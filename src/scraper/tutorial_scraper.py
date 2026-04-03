"""
Module de scraping des tutoriels Avidsen.
Extrait les tutoriels et les lie aux produits.
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional

from src.config.settings import HEADERS
from src.utils.text_utils import clean_product_name, resilient_request
from src.scraper.styles import (
    AVIDSEN_BASE_URL,
    SITE_HEADING_COLOR,
    SITE_ACCENT_COLOR,
    SITE_GREY_BG,
    SITE_FONT_FAMILY,
    SITE_FONT_SIZE,
)
from src.scraper.media_helpers import (
    collect_main_images,
    extract_youtube_html,
    fix_lazy_images,
)
from src.scraper.html_builder import (
    get_unique_columns,
    style_content_table,
    build_content_section_html,
)


# URL de base pour les tutoriels
TUTORIAL_BASE_URL = f"{AVIDSEN_BASE_URL}/fr/assistance/tutoriel-sav"


def get_tutorial_categories() -> List[str]:
    """
    Récupère la liste des catégories de tutoriels depuis la page principale.
    Returns:
        Liste des catégories (ex: ['motorisation', 'visiophone', 'solaire'])
    """
    try:
        response = requests.get(TUTORIAL_BASE_URL, headers=HEADERS, timeout=20)
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
            url = f"{AVIDSEN_BASE_URL}/fr/categorie_tutoriel_domotique/{product_ref}"
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
                        tutorial_url = f"{AVIDSEN_BASE_URL}{tutorial_url}"
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
        response = resilient_request(tutorial_url, headers=HEADERS, timeout=45, max_retries=3)
        if not response:
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        # --- 0. Pré-traitement : résoudre lazy images + supprimer <noscript> ---
        fix_lazy_images(soup)
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
        applicable_html = ''
        metadata_html = ''
        video_html = ''
        content_html = ''
        step_titles = []
        applicable_products = []
        in_content_zone = False
        # IDs des sections enfants du bloc metadata (à ignorer dans la zone de contenu)
        metadata_child_ids = set()
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
            if len(text) < 10 and not collect_main_images(section):
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
                unique_cols = get_unique_columns(section)
                for col in unique_cols:
                    col_imgs = collect_main_images(col)
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
                # Marquer toutes les sections enfants pour les ignorer dans la zone contenu
                for child_sec in section.find_all('section', class_=True, recursive=True):
                    if child_sec is not section:
                        metadata_child_ids.add(id(child_sec))
                unique_cols = get_unique_columns(section)
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
                    # Right column: matériel nécessaire + pièces détachées
                    # Use leaf widgets only (no child widget-containers) to avoid merged text
                    right_widgets = right_col.find_all('div', class_='elementor-widget-container')
                    leaf_widgets = []
                    for w in right_widgets:
                        if not w.find('div', class_='elementor-widget-container'):
                            leaf_widgets.append(w)
                    # Parse right column: collect sections with their headings
                    # Supports both "Matériel nécessaire" and "Pièces détachées nécessaires"
                    right_sections = []  # list of {'heading': str, 'items': list}
                    current_section = None
                    for w in leaf_widgets:
                        wt = w.get_text(strip=True)
                        if not wt:
                            continue
                        is_heading = False
                        if 'Matériel' in wt and ('nécessaire' in wt.lower() or ':' in wt):
                            is_heading = True
                        elif 'ce(' in wt or 'détach' in wt.lower():
                            is_heading = True
                        if is_heading:
                            current_section = {'heading': re.sub(r':(\S)', r': \1', wt), 'items': []}
                            right_sections.append(current_section)
                            continue
                        if wt.startswith('Référence') or wt.startswith('Réf'):
                            ref_text = re.sub(r':(\S)', r': \1', wt)
                            if current_section is not None:
                                current_section['items'].append({'type': 'ref', 'text': ref_text, 'link': None})
                            else:
                                current_section = {'heading': '', 'items': [{'type': 'ref', 'text': ref_text, 'link': None}]}
                                right_sections.append(current_section)
                        else:
                            a_tag = w.find('a')
                            if a_tag and current_section and current_section['items']:
                                last = current_section['items'][-1]
                                if last['type'] == 'ref' and last.get('link') is None:
                                    last['link'] = (a_tag.get_text(strip=True), a_tag.get('href', ''))
                                    continue
                            # Texte libre (ex: "Tournevis cruciforme, spatule plastique")
                            if current_section is not None:
                                current_section['items'].append({'type': 'text', 'text': re.sub(r':([^ ])', r': \1', wt)})
                            # Sinon ignorer
                    # Build right column content
                    right_content = ''
                    for rs in right_sections:
                        if rs['heading']:
                            right_content += (
                                f'<div style="font-weight: 600; color: {SITE_HEADING_COLOR}; '
                                f'margin-bottom: 8px; margin-top: 10px; font-size: 14px;">{rs["heading"]}</div>'
                            )
                        for item in rs['items']:
                            if item['type'] == 'text':
                                right_content += f'<div style="margin: 4px 0; padding-left: 8px;">{item["text"]}</div>'
                            elif item['type'] == 'ref':
                                ref_text = item['text']
                                if item.get('link'):
                                    lnk_text, lnk_href = item['link']
                                    if lnk_href.startswith('/'):
                                        lnk_href = f'{AVIDSEN_BASE_URL}{lnk_href}'
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
                    if right_content:
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
            # Les sections "Référence 123XXX" avec contenu (instructions par modèle)
            # --- "Ce tutoriel est applicable pour" – capturer les produits ------
            if 'Ce tutoriel est applicable' in text[:40]:
                if is_leaf:
                    product_items = []
                    for span in section.find_all('span', class_='ae-term-item'):
                        a_tag = span.find('a')
                        if a_tag:
                            name = clean_product_name(a_tag.get_text(strip=True))
                            if name:
                                product_items.append(name)
                                applicable_products.append(name)
                        else:
                            name = clean_product_name(span.get_text(strip=True))
                            if name:
                                product_items.append(name)
                                applicable_products.append(name)
                    if not product_items:
                        raw = text.replace('Ce tutoriel est applicable pour :', '').strip()
                        if raw:
                            product_items = [clean_product_name(p.strip()) for p in raw.split(',') if p.strip()]
                            product_items = [p for p in product_items if p]
                            applicable_products.extend(product_items)
                    if product_items:
                        # Produits affichés en texte simple (pas de lien WordPress)
                        # Les liens Zoho KB seront ajoutés lors de la publication
                        product_display = []
                        for name in product_items:
                            product_display.append(
                                f'<span data-product="{name}" style="color: {SITE_ACCENT_COLOR};">{name}</span>'
                            )
                        applicable_html = (
                            f'<div style="background: #e8f4f8; border-left: 4px solid {SITE_ACCENT_COLOR}; '
                            f'padding: 12px 16px; margin-bottom: 1.5em; border-radius: 4px; '
                            f'font-size: {SITE_FONT_SIZE}; font-family: {SITE_FONT_FAMILY};">'
                            f'<strong>Ce tutoriel est applicable pour :</strong><br/>'
                            + ', '.join(product_display)
                            + '</div>'
                        )
                continue
            # --- "Les explications en vidéo" – extraire YouTube, ignorer le heading
            if 'Les explications en vid' in text[:40]:
                if is_leaf and not video_html:
                    video_html = extract_youtube_html(section)
                continue
            # --- "Les étapes du tutoriel" (sommaire global) – ignorer -----------
            if 'Les étapes du tutoriel' in text[:40]:
                in_content_zone = True
                continue
            # --- Activer la zone de contenu si on détecte un mot-clé de contenu
            if not in_content_zone and any(text.startswith(kw) for kw in CONTENT_KEYWORDS):
                in_content_zone = True
            # --- Zone de contenu : capturer uniquement les feuilles -------------
            # Ignorer les sections enfants du bloc metadata (pièces détachées déjà incluses)
            if id(section) in metadata_child_ids:
                continue
            if in_content_zone and is_leaf:
                # Collecter le titre de l'étape pour le sommaire
                heading = section.find(['h3', 'h2'])
                if heading:
                    heading_text_for_toc = heading.get_text(strip=True)
                    if heading_text_for_toc and any(
                        heading_text_for_toc.startswith(kw) for kw in
                        ['Etape ', 'Étape ', 'ETAPE ', 'étape ']
                    ):
                        step_titles.append(heading_text_for_toc)
                section_html = build_content_section_html(section)
                if section_html:
                    content_html += section_html
        # --- 4. Assembler le HTML final -----------------------------------------
        html_parts = []
        if intro_html:
            html_parts.append(intro_html)
        # Bloc "Ce tutoriel est applicable pour"
        if applicable_html:
            html_parts.append(applicable_html)
        if metadata_html:
            html_parts.append(metadata_html)
        if video_html:
            html_parts.append(video_html)
        if content_html:
            html_parts.append(content_html)
        html_content = '\n'.join(html_parts)
        # Post-traitement : styler les tableaux de contenu (bordures + alternance)
        final_soup = BeautifulSoup(html_content, 'html.parser')
        for tbl in final_soup.find_all('table'):
            # Ignorer nos propres tables de layout (ont "margin: 1em 0" ou "margin-bottom")
            tbl_style = tbl.get('style', '')
            if 'margin: 1em 0' in tbl_style or 'margin-bottom' in tbl_style:
                continue
            style_content_table(tbl)
        html_content = str(final_soup)
        if not html_content.strip():
            print(f"[WARNING] Aucun contenu extrait pour {tutorial_url}")
            return None
        tutorial_data = {
            'url': tutorial_url,
            'title': title,
            'html_content': html_content,
            'steps': step_titles,
            'applicable_products': applicable_products,
        }
        print(f"[OK] Tutoriel extrait : {title}")
        return tutorial_data
    except Exception as e:
        print(f"[ERROR] Erreur extraction {tutorial_url}: {e}")