import os
import re
import requests
import json
from pathlib import Path
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
import unicodedata

# ---------------- Config ----------------
BASE_URL_TEMPLATE = "https://www.avidsen.com/fr/produit/page/{page}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
OUTPUT_FOLDER = Path("notices")
OUTPUT_FOLDER.mkdir(exist_ok=True)

# ---------------- Utilities ----------------
def load_config():
    """Charge la configuration depuis config.txt"""
    config = {}
    try:
        with open('config.txt', 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    config[key.strip()] = value.strip().strip('"\'')
    except FileNotFoundError:
        print("Erreur : Le fichier config.txt est introuvable.")
        print("Veuillez créer un fichier config.txt sur la base de config.example.txt")
        exit(1)
    return config

# Load config
config = load_config()
ACCESS_TOKEN_ZOHO = config.get("ZOHO_ACCESS_TOKEN")
ZOHO_ORG_ID = config.get("ZOHO_ORG_ID")
ZOHO_CATEGORY_ID = config.get("ZOHO_CATEGORY_ID")

if not all([ACCESS_TOKEN_ZOHO, ZOHO_ORG_ID, ZOHO_CATEGORY_ID]):
    print("Erreur: Des variables de configuration Zoho sont manquantes dans config.txt")
    exit(1)

# PDF footer ignore threshold (bottom fraction of page to ignore)
FOOTER_BOTTOM_FRAC = 0.15

# Table detection tolerances
Y_TOLERANCE = 3  # pixels tolerance for grouping same row
X_GAP_TOLERANCE = 8  # allowed small gaps

def download_file(url, filename):
    """Download file to filename (streamed)."""
    r = requests.get(url, stream=True, headers=HEADERS, timeout=60)
    r.raise_for_status()
    with open(filename, "wb") as f:
        for chunk in r.iter_content(8192):
            if chunk:
                f.write(chunk)
    print(f"Downloaded: {filename}")
    return filename

def clean_title(raw_title: str) -> str:
    """
    Turn:
    "Notice à télécharger – 107253 – Station météo ... – Avidsen – 107253"
    into:
    "Station météo ... – Notice-107253"
    """
    parts = [p.strip() for p in raw_title.split("–")]
    # heuristic: often parts: ["Notice à télécharger", "107253", "Station ...", "Avidsen", "107253"]
    if len(parts) >= 3:
        # prefer the long human readable part (choose part containing letters beyond code)
        # Try to find the part that is not purely numeric and not company name
        code = None
        main_text = None
        for p in parts:
            if re.fullmatch(r"\d{3,}", p):
                if not code:
                    code = p
        # pick longest non-numeric part as main_text
        non_numeric = [p for p in parts if not re.fullmatch(r"\d{1,}", p) and len(p) > 2]
        if non_numeric:
            # choose longest element not equal to "Notice à télécharger" or "Avidsen"
            candidates = [p for p in non_numeric if "notice" not in p.lower() and "avidsen" not in p.lower()]
            if candidates:
                main_text = max(candidates, key=len)
            else:
                main_text = max(non_numeric, key=len)
        if main_text and code:
            return f"{main_text} – Notice-{code}"
        if main_text:
            return main_text
    return raw_title.strip()

def is_toc_block(text: str) -> bool:
    txt = text.strip().lower()
    if not txt:
        return False
    if any(k in txt for k in ("sommaire", "table des matières", "table of contents", "contents")):
        return True
    # if block is mostly numbers like "1", "1.1", "2.3" lines many times -> toc
    # simple heuristic: many tokens that look like section numbers
    tokens = re.findall(r"[\d\.]{1,}", txt)
    if len(tokens) >= max(1, len(txt.split()) // 2) and len(txt) < 200:
        return True
    return False

def clean_section_text(text: str) -> str:
    """Remove lines with 1-2 chars and return a justified HTML paragraph(s)."""
    lines = [ln.strip() for ln in text.splitlines()]
    good = [ln for ln in lines if len(ln) > 2]
    if not good:
        return ""
    # Join into paragraphs roughly by blank lines - here simply join with <br>
    joined = "<br>".join(good)
    return f"<p style='text-align:justify; line-height:1.5; margin:0 0 12px 0;'>{joined}</p>"

# ---------------- PDF parsing with footer & table detection ----------------
def extract_pdf_structure_keep_tables(pdf_path: Path):
    """
    Extract sections (title -> content) and tables from pdf_path using PyMuPDF (fitz).
    - ignore footer blocks located in bottom FOOTER_BOTTOM_FRAC of page
    - ignore TOC-like blocks (more robust)
    - detect "tables" by grouping text spans that share same y coordinate lines and multiple columns
    - remove repeated headers appearing on multiple pages
    Returns:
      cleaned_sections: list of dict { "title": str, "content": str }
    """
    import re
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

# ---------------- Zoho article creation ----------------
def create_zoho_article(title_raw: str, main_image_path_or_url: str, sections, pdf_url: str):
    if not pdf_url:
        print(f"PDF manquant, l'article '{title_raw}' ne sera pas créé.")
        return
    
    def sanitize_permalink(title: str, max_length=100):
        # Normaliser accents
        title = unicodedata.normalize('NFKD', title)
        title = title.encode('ascii', 'ignore').decode('ascii')
        # Minuscules
        title = title.lower()
        # Remplacer tout ce qui n'est pas lettre/chiffre par un tiret
        title = re.sub(r'[^a-z0-9]+', '-', title)
        # Supprimer tirets multiples
        title = re.sub(r'-{2,}', '-', title)
        # Supprimer tirets début/fin
        title = title.strip('-')
        # Limiter longueur
        if len(title) > max_length:
            title = title[:max_length].rstrip('-')
        # fallback si vide
        if not title:
            title = f"article-{int(time.time())}"
        return title

    title = clean_title(title_raw)

    # --- Construire le HTML ---
    html = []
    if main_image_path_or_url:
        img_src = main_image_path_or_url if str(main_image_path_or_url).startswith("http") else main_image_path_or_url
        html.append(f"<div style='text-align:center;'><img src='{img_src}' alt='{title}' style='display:block; margin:12px auto; max-width:800px; border:1px solid #ddd; padding:5px;'/></div>")

    html.append(f"<h1 style='text-align:center; color:#2E86C1; margin-top:10px;'>{title}</h1>")

    for sec in sections:
        sec_title = sec.get("title", "")
        sec_content = sec.get("content", "")
        if sec_title:
            html.append(f"<h2 style='color:#2874A6;margin-top:14px;'>{sec_title}</h2>")
        if sec_content:
            if "<table" in sec_content:
                parts = re.split(r"(<table.*?>.*?</table>)", sec_content, flags=re.DOTALL)
                for p in parts:
                    if p.strip().startswith("<table"):
                        html.append(p)
                    else:
                        cleaned = clean_section_text(p)
                        if cleaned:
                            html.append(cleaned)
            else:
                cleaned = clean_section_text(sec_content)
                if cleaned:
                    html.append(cleaned)

    if pdf_url:
        html.append(f"""
<div style='text-align:center; margin:20px 0;'>
  <a href='{pdf_url}' style='background-color:#2E86C1; color:white; padding:10px 20px; text-decoration:none; border-radius:5px; display:inline-block;'>Télécharger la notice PDF</a>
</div>
""")

    final_html = "\n".join(html)

    # --- Préparer payload Zoho ---
    zoho_headers = {
        "Authorization": f"Zoho-oauthtoken {ACCESS_TOKEN_ZOHO}",
        "orgId": ZOHO_ORG_ID,
        "Content-Type": "application/json"
    }

    zoho_body = {
        "title": title,
        "permalink": sanitize_permalink(title),
        "answer": final_html,
        "categoryId": ZOHO_CATEGORY_ID,
        "status": "Published"
    }

    # --- Poster sur Zoho ---
    try:
        r = requests.post("https://desk.zoho.com/api/v1/articles", headers=zoho_headers, data=json.dumps(zoho_body), timeout=30)
        if r.status_code in (200, 201):
            print(f"✅ Zoho article created: {title}")
        else:
            print(f"❌ Zoho error ({r.status_code}): {r.text}")
    except Exception as e:
        print(f"❌ Zoho request failed: {e}")
# ---------------- Scraper ----------------
def scrape_product_page(product_url: str, title_text: str, img_url: str):
    """Download PDF + product image, extract PDF text/tables and publish to Zoho."""
    try:
        r = requests.get(product_url, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"Error fetching product page {product_url}: {e}")
        return

    soup = BeautifulSoup(r.text, "html.parser")
    # find PDF link
    pdf_tag = soup.find("a", id="cta-pdf-technical-sheet")
    pdf_url = None
    pdf_filename = None
    if pdf_tag and pdf_tag.get("href"):
        pdf_url = pdf_tag["href"]
        pdf_filename = OUTPUT_FOLDER / os.path.basename(pdf_url)
        try:
            download_file(pdf_url, pdf_filename)
        except Exception as e:
            print(f"Failed to download PDF {pdf_url}: {e}")
            pdf_filename = None

    # download main image into notice/
    main_image_local = ""
    if img_url:
        try:
            img_name = os.path.basename(img_url.split("?")[0])
            local_img_path = OUTPUT_FOLDER / img_name
            if not local_img_path.exists():
                download_file(img_url, local_img_path)
            main_image_local = str(local_img_path.as_posix())
        except Exception as e:
            print(f"Failed to download image {img_url}: {e}")
            main_image_local = img_url  # fallback to URL

    # extract pdf structure (text + tables), ignoring images
    sections = []
    if pdf_filename and pdf_filename.exists():
        sections = extract_pdf_structure_keep_tables(pdf_filename)
    else:
        sections = []

    # publish to Zoho (we pass local image path or remote URL)
    create_zoho_article(title_text, main_image_local or img_url, sections, pdf_url)

def scrape_all_pages():
    page = 1
    while True:
        url = BASE_URL_TEMPLATE.format(page=page)
        print(f"\nScraping page {page} -> {url}")
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                print("No more pages or network error (status)", r.status_code)
                break
        except Exception as e:
            print("Network error:", e)
            break

        soup = BeautifulSoup(r.text, "html.parser")
        articles = soup.find_all("article", class_="post")
        if not articles:
            print("No articles found on page, stopping.")
            break

        for article in articles:
            h2 = article.find("h2", class_="entry-title")
            if not h2:
                continue
            title_text = h2.get_text(strip=True)
            link_tag = h2.find("a")
            # only take image inside the same <article> with the exact class
            img_tag = article.find("img", class_="attachment-large size-large wp-post-image entered lazyloaded")
            img_url = img_tag.get("src") if img_tag and img_tag.get("src") else ""

            if link_tag and link_tag.get("href"):
                product_url = link_tag.get("href")
                print(f"\nProcessing product: {title_text}")
                scrape_product_page(product_url, title_text, img_url)

        page += 1

# ---------------- Main ----------------
if __name__ == "__main__":
    scrape_all_pages()