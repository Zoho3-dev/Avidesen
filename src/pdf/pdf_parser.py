"""
Extraction de structure et de contenu depuis les PDFs.
"""

import re
import os
import base64
from pathlib import Path
import fitz  # PyMuPDF

from src.config.settings import FOOTER_BOTTOM_FRAC, Y_TOLERANCE, X_GAP_TOLERANCE
from src.pdf.table_detector import is_toc_block


def image_to_data_uri(image_path: str) -> str:
    """Convertit une image en data URI pour l'intégration dans HTML."""
    try:
        with open(image_path, "rb") as img_file:
            image_data = img_file.read()
        
        # Déterminer le type MIME
        ext = os.path.splitext(image_path)[1].lower()
        mime_type = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp'
        }.get(ext, 'image/png')
        
        # Encoder en base64
        base64_data = base64.b64encode(image_data).decode('utf-8')
        
        return f"data:{mime_type};base64,{base64_data}"
    except Exception as e:
        print(f"Erreur lors de la conversion de l'image {image_path}: {e}")
        return ""


def extract_images_from_pdf(pdf_path: str, output_dir: str):
    """Extrait les images du PDF avec leurs positions exactes et les enregistre dans le dossier de sortie.
    
    Returns:
        Liste de dictionnaires contenant les informations sur les images extraites avec leurs positions
    """
    # Créer le dossier de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    extracted_images = []
    
    for page_num, page in enumerate(doc, 1):
        # Obtenir les dimensions de la page
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height
        
        # Extraire les images avec leurs positions
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list, 1):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            # Déterminer l'extension du fichier
            image_ext = base_image["ext"]
            if not image_ext:
                image_ext = "png"  # Par défaut
            
            # Enregistrer l'image
            image_filename = f"page_{page_num}_img_{img_index}.{image_ext}"
            image_path = os.path.join(output_dir, image_filename)
            
            with open(image_path, "wb") as img_file:
                img_file.write(image_bytes)
            
            # Obtenir la position de l'image dans la page
            # Chercher le rectangle de l'image
            img_rects = page.get_image_rects(xref)
            
            if img_rects:
                # Prendre le premier rectangle (normalement il n'y en a qu'un par image)
                img_rect = img_rects[0]
                
                # Calculer les positions relatives en pourcentage
                x0_percent = (img_rect.x0 / page_width) * 100
                y0_percent = (img_rect.y0 / page_height) * 100
                x1_percent = (img_rect.x1 / page_width) * 100
                y1_percent = (img_rect.y1 / page_height) * 100
                
                # Ajouter les informations sur l'image avec position
                extracted_images.append({
                    'page': page_num,
                    'index': img_index,
                    'filename': image_filename,
                    'path': image_path,
                    'width': base_image.get('width', 0),
                    'height': base_image.get('height', 0),
                    'size': len(image_bytes),
                    'position': {
                        'x0': img_rect.x0,
                        'y0': img_rect.y0,
                        'x1': img_rect.x1,
                        'y1': img_rect.y1,
                        'x0_percent': x0_percent,
                        'y0_percent': y0_percent,
                        'x1_percent': x1_percent,
                        'y1_percent': y1_percent,
                        'page_width': page_width,
                        'page_height': page_height
                    }
                })
            else:
                # Si on ne trouve pas la position, ajouter quand même l'image
                extracted_images.append({
                    'page': page_num,
                    'index': img_index,
                    'filename': image_filename,
                    'path': image_path,
                    'width': base_image.get('width', 0),
                    'height': base_image.get('height', 0),
                    'size': len(image_bytes),
                    'position': None
                })
    
    doc.close()
    
    # Trier les images par position (d'abord par page, puis par position Y)
    extracted_images.sort(key=lambda x: (x['page'], x['position']['y0'] if x['position'] else 0))
    
    return extracted_images


def extract_pdf_structure_keep_tables(pdf_path: Path):
    """
    Extrait les sections (titre -> contenu) et les tableaux d'un PDF avec une meilleure précision.
    
    - Ignore les blocs de footer situés dans la fraction inférieure de la page
    - Ignore les blocs ressemblant à une table des matières
    - Détecte les tableaux en analysant les positions des colonnes
    - Extrait les images du PDF et les intègre à leurs positions exactes
    - Supprime les en-têtes répétés apparaissant sur plusieurs pages
    
    Args:
        pdf_path: Chemin vers le fichier PDF
        
    Returns:
        Liste de dictionnaires { "title": str, "content": str }
    """
    doc = fitz.open(str(pdf_path))
    sections = []

    # For header duplicate detection: store normalized header strings and occurrence counts
    header_counts = {}

    def normalize_for_header(s: str) -> str:
        s2 = re.sub(r'\s+', ' ', s.strip())
        s2 = re.sub(r'[^0-9A-Za-z]+', '', s2).lower()
        return s2[:120]  # truncate to a stable length

    # Extraire les images du PDF d'abord
    output_dir = os.path.join(os.path.dirname(str(pdf_path)), "extracted_images")
    extracted_images = extract_images_from_pdf(str(pdf_path), output_dir)

    for page_index, page in enumerate(doc, start=1):
        page_height = page.rect.height
        page_width = page.rect.width
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_IMAGES)["blocks"]
        
        # Créer une liste de tous les éléments (texte, tableaux, images) avec leurs positions
        all_elements = []
        
        # Ajouter les images de cette page avec leurs positions
        page_images = [img for img in extracted_images if img['page'] == page_index]
        for img in page_images:
            if img['position']:
                all_elements.append({
                    'type': 'image',
                    'y0': img['position']['y0'],
                    'y1': img['position']['y1'],
                    'data': img
                })
        
        # Traiter les blocs de texte pour détecter les tableaux
        potential_table_blocks = []
        text_blocks = []
        
        for b in blocks:
            if b.get("type", 0) != 0:
                continue
            x0, y0, x1, y1 = b["bbox"]

            # ignore footer (bottom fraction)
            if y0 > page_height * (1 - FOOTER_BOTTOM_FRAC):
                continue

            # build block text and track max font size
            block_text = ""
            max_font_size = 0
            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    txt = span.get("text", "")
                    block_text += txt
                    if span.get("size", 0) > max_font_size:
                        max_font_size = span.get("size", 0)
                block_text += "\n"
            block_text = block_text.strip()
            if not block_text:
                continue

            # Normalize small sample for TOC detection and header detection
            short_norm = re.sub(r'\s+', ' ', block_text).strip().lower()

            # If block looks like a TOC / sommaire, skip it
            if is_toc_block(block_text):
                continue

            # Header detection: blocks near top of page (top 12-18%) are candidate headers
            top_threshold = page_height * 0.18
            if y1 < top_threshold:
                norm_h = normalize_for_header(block_text)
                header_counts[norm_h] = header_counts.get(norm_h, 0) + 1
                if header_counts[norm_h] > 1:
                    continue
            
            # Détecter si le bloc pourrait être un tableau
            lines = b.get("lines", [])
            has_multiple_columns = any(len(line.get("spans", [])) > 1 for line in lines)
            
            if has_multiple_columns and len(lines) > 1:
                potential_table_blocks.append({
                    "block": b,
                    "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                    "text": block_text,
                    "max_size": max_font_size
                })
            else:
                text_blocks.append({
                    "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                    "text": block_text,
                    "max_size": max_font_size
                })
        
        # Ajouter les blocs de texte à la liste des éléments
        for block in text_blocks:
            all_elements.append({
                'type': 'text',
                'y0': block['y0'],
                'y1': block['y1'],
                'data': block
            })
        
        # Traiter les blocs de tableau et les ajouter
        for table_block in potential_table_blocks:
            b = table_block["block"]
            lines = b.get("lines", [])
            
            if not lines:
                continue
                
            # Détecter les positions des colonnes
            x_positions = set()
            for line in lines:
                for span in line.get("spans", []):
                    x_positions.add(round(span['origin'][0], 1))
            
            # Trier les positions et regrouper celles qui sont proches
            sorted_x = sorted(x_positions)
            columns = []
            if sorted_x:
                columns.append(sorted_x[0])
                for x in sorted_x[1:]:
                    if x - columns[-1] > X_GAP_TOLERANCE:
                        columns.append(x)
            
            # Si on a au moins 2 colonnes, on considère que c'est un tableau
            if len(columns) >= 2:
                table_data = []
                
                # Pour chaque ligne, extraire le texte par colonne
                for line in lines:
                    row = [""] * len(columns)
                    spans = line.get("spans", [])
                    
                    for span in spans:
                        text = span['text'].strip()
                        if not text:
                            continue
                            
                        # Trouver la colonne correspondante
                        x_pos = round(span['origin'][0], 1)
                        col_idx = 0
                        for i, col_x in enumerate(columns):
                            if x_pos >= col_x:
                                col_idx = i
                        
                        # Ajouter le texte à la cellule appropriée
                        if col_idx < len(row):
                            if row[col_idx]:
                                row[col_idx] += " " + text
                            else:
                                row[col_idx] = text
                    
                    # Nettoyer les cellules vides
                    row = [cell if cell.strip() else "" for cell in row]
                    table_data.append(row)
                
                # Nettoyer les lignes vides
                table_data = [row for row in table_data if any(cell.strip() for cell in row)]
                
                if table_data and len(table_data) > 1:
                    # Créer une représentation HTML du tableau
                    html_table = "<div style='margin: 15px 0; overflow-x: auto;'>\n"
                    html_table += "<table style='width:100%; border-collapse: collapse; border: 1px solid #ddd; font-size: 14px;'>\n"
                    
                    for i, row in enumerate(table_data):
                        # Détecter l'en-tête
                        is_header = (i == 0) or (table_block["max_size"] > 10)
                        
                        if is_header:
                            html_table += "<tr style='background-color: #f5f5f5; font-weight: bold;'>\n"
                        else:
                            bg_color = "#ffffff" if i % 2 == 0 else "#f9f9f9"
                            html_table += f"<tr style='background-color: {bg_color};'>\n"
                        
                        for cell in row:
                            if is_header:
                                html_table += f"<th style='border: 1px solid #ddd; padding: 8px; text-align: left;'>{cell}</th>\n"
                            else:
                                html_table += f"<td style='border: 1px solid #ddd; padding: 8px;'>{cell if cell.strip() else '&nbsp;'}</td>\n"
                        
                        html_table += "</tr>\n"
                    
                    html_table += "</table>\n</div>"
                    
                    # Ajouter le tableau à la liste des éléments
                    all_elements.append({
                        'type': 'table',
                        'y0': table_block['y0'],
                        'y1': table_block['y1'],
                        'data': html_table
                    })
        
        # Trier tous les éléments par position Y
        all_elements.sort(key=lambda x: x['y0'])
        
        # Construire le contenu en assemblant les éléments dans l'ordre
        current_section = None
        
        for element in all_elements:
            if element['type'] == 'image':
                # Convertir l'image en data URI
                img_data = element['data']
                data_uri = image_to_data_uri(img_data['path'])
                
                if data_uri:
                    # Calculer la largeur relative pour l'affichage
                    img_width_percent = ((img_data['position']['x1_percent'] - img_data['position']['x0_percent']))
                    max_width = min(img_width_percent, 80)  # Limiter à 80% de la largeur
                    
                    image_html = f"<div style='margin: 10px 0; text-align: center;'>\n"
                    image_html += f"<img src='{data_uri}' alt='Image page {img_data['page']}' style='max-width: {max_width}%; height: auto; border: 1px solid #ddd; padding: 5px;' />\n"
                    image_html += f"</div>\n"
                    
                    if current_section:
                        current_section['content'] += image_html
                    else:
                        if not sections or sections[-1]['title'] != 'Introduction':
                            sections.append({"title": "Introduction", "content": image_html})
                        else:
                            sections[-1]['content'] += image_html
                            
            elif element['type'] == 'text':
                block = element['data']
                row_text = block["text"]
                if len(row_text.strip()) <= 2:
                    continue
                
                max_size = block["max_size"]
                
                # heuristic for title: uppercase or larger font
                if row_text.isupper() or max_size >= 12:
                    if not is_toc_block(row_text) and len(re.sub(r'[^A-Za-z0-9]', '', row_text)) > 2:
                        current_section = {"title": row_text.strip(), "content": ""}
                        sections.append(current_section)
                    else:
                        if current_section:
                            current_section["content"] += row_text + "\n"
                        else:
                            if not sections or sections[-1]['title'] != 'Introduction':
                                current_section = {"title": "Introduction", "content": row_text + "\n"}
                                sections.append(current_section)
                            else:
                                sections[-1]['content'] += row_text + "\n"
                else:
                    if current_section:
                        current_section["content"] += row_text + "\n"
                    else:
                        if not sections or sections[-1]['title'] != 'Introduction':
                            current_section = {"title": "Introduction", "content": row_text + "\n"}
                            sections.append(current_section)
                        else:
                            sections[-1]['content'] += row_text + "\n"
                            
            elif element['type'] == 'table':
                table_html = element['data']
                if current_section:
                    current_section["content"] += "\n" + table_html
                else:
                    if not sections or sections[-1]['title'] != 'Tableaux':
                        sections.append({"title": "Tableaux", "content": table_html})
                    else:
                        sections[-1]['content'] += table_html

    # Final cleanup: remove TOC-like sections, remove header duplicates, remove tiny content lines
    cleaned_sections = []
    seen_titles = set()
    for sec in sections:
        title_norm = sec.get("title", "").strip()
        if is_toc_block(title_norm):
            continue
        t_norm = re.sub(r'[^0-9A-Za-z]+', ' ', title_norm).strip().lower()
        if not t_norm:
            continue
        if t_norm in seen_titles:
            continue
        content = sec.get("content", "") if isinstance(sec.get("content", ""), str) else ""
        lines = [ln.strip() for ln in content.splitlines() if len(ln.strip()) > 2]
        content_clean = "\n".join(lines).strip()
        if not content_clean and len(re.sub(r'[^0-9A-Za-z]', '', title_norm)) <= 2:
            continue
        cleaned_sections.append({"title": title_norm, "content": content_clean})
        seen_titles.add(t_norm)

    doc.close()
    return cleaned_sections
