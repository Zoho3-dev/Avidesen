"""
Extraction de structure et de contenu depuis les PDFs.
"""

import re
from pathlib import Path
import fitz  # PyMuPDF

from src.config.settings import FOOTER_BOTTOM_FRAC, Y_TOLERANCE, X_GAP_TOLERANCE
from src.pdf.table_detector import is_toc_block


def extract_pdf_structure_keep_tables(pdf_path: Path):
    """
    Extrait les sections (titre -> contenu) et les tableaux d'un PDF.
    
    - Ignore les blocs de footer situés dans la fraction inférieure de la page
    - Ignore les blocs ressemblant à une table des matières
    - Détecte les tableaux en groupant les spans de texte partageant les mêmes coordonnées y
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

    for page_index, page in enumerate(doc, start=1):
        page_height = page.rect.height
        blocks = page.get_text("dict")["blocks"]
        text_cells = []

        # first collect blocks into text_cells (skipping footers and TOC)
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
                # increase count
                header_counts[norm_h] = header_counts.get(norm_h, 0) + 1
                # If we've already seen this header once before on earlier page -> skip this block (duplicate header)
                if header_counts[norm_h] > 1:
                    # skip duplicate header block
                    continue
            # store the cell for further processing
            y_center = (y0 + y1) / 2
            text_cells.append({
                "x0": x0, "x1": x1, "y0": y0, "y1": y1, "y_center": y_center,
                "text": block_text, "max_size": max_font_size
            })

        if not text_cells:
            continue

        # Group by approximate y_center into rows
        text_cells.sort(key=lambda c: (c["y_center"], c["x0"]))
        rows = []
        for cell in text_cells:
            placed = False
            for row in rows:
                if abs(row["y_center"] - cell["y_center"]) <= Y_TOLERANCE:
                    row["cells"].append(cell)
                    row["y_center"] = (row["y_center"] * row["count"] + cell["y_center"]) / (row["count"] + 1)
                    row["count"] += 1
                    placed = True
                    break
            if not placed:
                rows.append({"y_center": cell["y_center"], "cells": [cell], "count": 1})

        # Table detection as consecutive rows with multiple cells
        potential_table_rows = [row for row in rows if len(row["cells"]) > 1]
        tables_found = []
        if potential_table_rows:
            i = 0
            while i < len(rows):
                if len(rows[i]["cells"]) > 1:
                    start = i
                    j = i + 1
                    while j < len(rows) and len(rows[j]["cells"]) > 1:
                        j += 1
                    table_rows = rows[start:j]
                    # build column x positions
                    col_positions = []
                    for r in table_rows:
                        for c in r["cells"]:
                            col_positions.append(c["x0"])
                    col_positions_sorted = sorted(col_positions)
                    cols = []
                    for x in col_positions_sorted:
                        if not cols or abs(x - cols[-1]) > X_GAP_TOLERANCE:
                            cols.append(x)
                    # render table html (premium style)
                    html_table = "<table style='width:100%;border-collapse:collapse;border:1px solid #ccc;margin:12px 0;'>"
                    for ridx, r in enumerate(table_rows):
                        bg = " style='background:#f5f5f5;'" if (ridx % 2 == 0) else ""
                        html_table += f"<tr{bg}>"
                        row_cells_map = {}
                        for c in r["cells"]:
                            distances = [abs(c["x0"] - cp) for cp in cols]
                            nearest = distances.index(min(distances))
                            existing = row_cells_map.get(nearest, "")
                            text_val = c["text"].replace("\n", " ").strip()
                            row_cells_map[nearest] = (existing + " " + text_val).strip() if existing else text_val
                        for col_idx in range(len(cols)):
                            cell_text = row_cells_map.get(col_idx, "")
                            html_table += f"<td style='border:1px solid #ddd;padding:8px;vertical-align:top;'>{cell_text}</td>"
                        html_table += "</tr>"
                    html_table += "</table>"
                    tables_found.append({"start_index": start, "end_index": j, "html": html_table})
                    i = j
                else:
                    i += 1

        # Mark rows used by tables
        used_row_idx = set()
        for t in tables_found:
            for idx_row in range(t["start_index"], t["end_index"]):
                used_row_idx.add(idx_row)

        # Convert non-table rows into sections/titles/content
        for ridx, r in enumerate(rows):
            if ridx in used_row_idx:
                continue
            # build row text left->right
            row_text = " ".join([c["text"].replace("\n", " ").strip() for c in sorted(r["cells"], key=lambda x: x["x0"])])
            if len(row_text.strip()) <= 2:
                continue
            max_size = max((c.get("max_size", 0) for c in r["cells"]), default=0)
            # heuristic for title: uppercase or larger font
            if row_text.isupper() or max_size >= 12:
                # avoid numeric-only titles or headers that are likely page headers (very short, numeric or doc name)
                if not is_toc_block(row_text) and len(re.sub(r'[^A-Za-z0-9]', '', row_text)) > 2:
                    sections.append({"title": row_text.strip(), "content": ""})
                else:
                    # treat as small text if not valid title
                    if sections:
                        sections[-1]["content"] += row_text + "\n"
                    else:
                        sections.append({"title": "Introduction", "content": row_text + "\n"})
            else:
                if sections:
                    sections[-1]["content"] += row_text + "\n"
                else:
                    sections.append({"title": "Introduction", "content": row_text + "\n"})

        # Insert table HTML into nearest preceding section (or create one)
        for t in tables_found:
            if sections:
                sections[-1]["content"] += "\n" + t["html"]
            else:
                sections.append({"title": "Tableau", "content": t["html"]})

    # Final cleanup: remove TOC-like sections, remove header duplicates, remove tiny content lines
    cleaned_sections = []
    seen_titles = set()
    for sec in sections:
        title_norm = sec.get("title", "").strip()
        # ignore TOC-like titles
        if is_toc_block(title_norm):
            continue
        # normalize title to detect duplicates (remove punctuation, lowercase)
        t_norm = re.sub(r'[^0-9A-Za-z]+', ' ', title_norm).strip().lower()
        if not t_norm:
            continue
        # skip duplicate titles (exact same normalized title)
        if t_norm in seen_titles:
            # if duplicate but has additional content we might append unique content; for safety skip
            continue
        # clean content: remove tiny lines
        content = sec.get("content", "") if isinstance(sec.get("content", ""), str) else ""
        lines = [ln.strip() for ln in content.splitlines() if len(ln.strip()) > 2]
        content_clean = "\n".join(lines).strip()
        # if this section is empty but title is trivial (numeric), skip
        if not content_clean and len(re.sub(r'[^0-9A-Za-z]', '', title_norm)) <= 2:
            continue
        cleaned_sections.append({"title": title_norm, "content": content_clean})
        seen_titles.add(t_norm)

    return cleaned_sections
