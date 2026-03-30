"""
Génération du HTML pour les sections de tutoriels Avidsen.
Construit les layouts (image|texte, colonnes, etc.) pour Zoho Desk.
"""

import re
from typing import List

from src.scraper.styles import (
    SITE_HEADING_COLOR,
    SITE_ACCENT_COLOR,
    SITE_GREY_BG,
    SITE_FONT_FAMILY,
    SITE_FONT_SIZE,
)
from src.scraper.media_helpers import (
    is_inline_icon,
    is_standalone_image_wrapper,
    collect_main_images,
    extract_youtube_html,
)


# ── Regex compilée pour détecter les colonnes Elementor ──────────────────
_COL_RE = re.compile(r'elementor-col-\d+')


def get_unique_columns(container) -> list:
    """Retourne les colonnes Elementor de premier niveau dans un conteneur.

    Déduplique en ne gardant que celles dont aucun parent n'est aussi une colonne
    trouvée dans le même conteneur.
    """
    cols = container.find_all('div', class_=_COL_RE)
    unique = []
    for col in cols:
        parent_col = col.find_parent('div', class_=_COL_RE)
        if parent_col not in cols:
            unique.append(col)
    return unique


def style_content_table(table) -> None:
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


def has_grey_background(section) -> bool:
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


def extract_section_text(section, skip_title: bool = True) -> str:
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
            if is_standalone_image_wrapper(child):
                continue
            # Ignorer les titres h3 (déjà extraits séparément)
            if skip_title and child.name == 'h3':
                continue
            # Ignorer les wrappers qui ne contiennent qu'un h3
            if child.name == 'div' and child.find('h3') and not child.find(['p', 'ul', 'ol', 'li', 'table']):
                continue
            # Résoudre les icônes inline dans cet élément
            for img in child.find_all('img'):
                if is_inline_icon(img):
                    real_src = img.get('src', '')
                    if real_src:
                        img['style'] = 'vertical-align: middle; max-height: 40px; display: inline;'
            # Styler les tableaux de contenu (bordures + couleurs alternées)
            if child.name == 'table':
                style_content_table(child)
            # Extraire le contenu utile (p, ul, ol, table, div avec du texte)
            if child.name in ('p', 'ul', 'ol', 'table'):
                html_parts.append(str(child))
            else:
                inner = child.find_all(['p', 'ul', 'ol', 'table'], recursive=False)
                if inner:
                    for elem in inner:
                        if elem.name == 'table':
                            style_content_table(elem)
                        html_parts.append(str(elem))
                elif child.get_text(strip=True):
                    html_parts.append(str(child))
    return '\n'.join(html_parts)


def build_step_html(img_urls: list, step_title: str, step_body: str, grey_bg: bool = False) -> str:
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


def build_content_section_html(section) -> str:
    """Construit le HTML d'une section de contenu Elementor.

    Gère automatiquement les layouts :
      - 2 colonnes (image | texte) → table avec images à gauche, texte + icônes à droite
      - 1 colonne ou sans colonnes → contenu séquentiel
    Préserve les icônes inline dans le texte et capture TOUTES les images principales.
    """
    grey_bg = has_grey_background(section)
    unique_cols = get_unique_columns(section)
    # Détecter le titre (h3 ou h2) de la section
    heading = section.find(['h3', 'h2'])
    heading_text = heading.get_text(strip=True) if heading else ''
    if len(unique_cols) >= 2:
        # --- Layout 2 colonnes : image | texte ---
        col_a = unique_cols[0]
        col_b = unique_cols[1]
        # Déterminer quelle colonne est la colonne image
        col_a_main_imgs = collect_main_images(col_a)
        col_b_main_imgs = collect_main_images(col_b)
        col_a_text_len = len(col_a.get_text(strip=True))
        col_b_text_len = len(col_b.get_text(strip=True))
        if col_a_main_imgs and not col_b_main_imgs:
            img_col, text_col = col_a, col_b
        elif col_b_main_imgs and not col_a_main_imgs:
            img_col, text_col = col_b, col_a
        elif col_a_main_imgs and col_b_main_imgs:
            # Les deux colonnes ont des images : la colonne avec nettement
            # plus de texte est la colonne texte (les images y sont contextuelles)
            if col_b_text_len > col_a_text_len * 2:
                img_col, text_col = col_a, col_b
            elif col_a_text_len > col_b_text_len * 2:
                img_col, text_col = col_b, col_a
            elif len(col_a_main_imgs) > len(col_b_main_imgs):
                img_col, text_col = col_a, col_b
            elif len(col_b_main_imgs) > len(col_a_main_imgs):
                img_col, text_col = col_b, col_a
            else:
                img_col, text_col = col_a, col_b
        else:
            img_col, text_col = col_a, col_b
        # Collecter TOUTES les images principales de la colonne image
        img_urls = collect_main_images(img_col)
        # Titre depuis la colonne texte
        col_heading = text_col.find(['h3', 'h2'])
        title = col_heading.get_text(strip=True) if col_heading else heading_text
        # Corps (avec icônes inline préservées)
        body = extract_section_text(text_col)
        # Vidéos YouTube dans le layout 2 colonnes
        youtube_html = extract_youtube_html(section)
        if youtube_html:
            body = youtube_html + '\n' + body
        return build_step_html(img_urls, title, body, grey_bg=grey_bg)
    else:
        # --- Layout sans colonnes : contenu séquentiel ---
        img_urls = collect_main_images(section)
        body = extract_section_text(section)
        bg_style = f'background-color: {SITE_GREY_BG}; padding: 15px; border-radius: 6px; word-wrap: break-word; overflow-wrap: break-word; ' if grey_bg else 'word-wrap: break-word; overflow-wrap: break-word; '
        # Gérer les tableaux autonomes
        tables = section.find_all('table')
        if tables and not body.strip():
            for t in tables:
                style_content_table(t)
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
        youtube_html = extract_youtube_html(section)
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
            return build_step_html(img_urls, heading_text, body, grey_bg=grey_bg)
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
