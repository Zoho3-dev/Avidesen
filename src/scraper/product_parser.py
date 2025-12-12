"""
Module de parsing des pages produits.
Gère le téléchargement et le traitement des informations produit.
"""

import os
import requests
from bs4 import BeautifulSoup

from src.config.settings import HEADERS, OUTPUT_FOLDER
from src.utils.file_utils import download_file
from src.pdf.pdf_parser import extract_pdf_structure_keep_tables
from src.zoho.api import create_zoho_article


def scrape_product_page(product_url: str, title_text: str, img_url: str):
    """
    Télécharge le PDF et l'image du produit, extrait le contenu et publie sur Zoho.
    
    Args:
        product_url: URL de la page produit
        title_text: Titre du produit
        img_url: URL de l'image du produit
    """
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
