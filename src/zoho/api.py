"""
Module d'interaction avec l'API Zoho Desk.
Gère la création d'articles dans la base de connaissances.
"""

import json
import requests
import re

from src.config.settings import get_zoho_config
from src.utils.text_utils import clean_title, sanitize_permalink, clean_section_text
from src.scraper.tutorial_formatter import format_tutorials_section, create_tutorial_summary


def create_zoho_article(title_raw: str, main_image_path_or_url: str, sections, pdf_url: str, tutorials=None):
    """
    Crée un article dans Zoho Desk avec le contenu extrait du PDF et les tutoriels.
    
    Args:
        title_raw: Titre brut du produit
        main_image_path_or_url: Chemin ou URL de l'image principale
        sections: Liste de sections extraites du PDF
        pdf_url: URL du PDF original
        tutorials: Liste de tutoriels associés au produit (optionnel)
    """
    if not pdf_url:
        print(f"PDF manquant, l'article '{title_raw}' ne sera pas créé.")
        return
    
    # Récupérer la configuration Zoho
    zoho_config = get_zoho_config()
    
    title = clean_title(title_raw)

    # --- Construire le HTML ---
    html = []
    if main_image_path_or_url:
        img_src = main_image_path_or_url if str(main_image_path_or_url).startswith("http") else main_image_path_or_url
        html.append(f"<div style='text-align:center;'><img src='{img_src}' alt='{title}' style='display:block; margin:12px auto; max-width:800px; border:1px solid #ddd; padding:5px;'/></div>")

    html.append(f"<h1 style='text-align:center; color:#2E86C1; margin-top:10px;'>{title}</h1>")
    
    # Add tutorial summary if tutorials exist
    if tutorials:
        tutorial_summary = create_tutorial_summary(tutorials)
        if tutorial_summary:
            html.append(tutorial_summary)

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
    
    # Add full tutorials section
    if tutorials:
        tutorials_html = format_tutorials_section(tutorials)
        if tutorials_html:
            html.append(tutorials_html)

    if pdf_url:
        html.append(f"""
<div style='text-align:center; margin:20px 0;'>
  <a href='{pdf_url}' style='background-color:#2E86C1; color:white; padding:10px 20px; text-decoration:none; border-radius:5px; display:inline-block;'>Télécharger la notice PDF</a>
</div>
""")

    final_html = "\n".join(html)

    # --- Préparer payload Zoho ---
    zoho_headers = {
        "Authorization": f"Zoho-oauthtoken {zoho_config['access_token']}",
        "orgId": zoho_config['org_id'],
        "Content-Type": "application/json"
    }

    zoho_body = {
        "title": title,
        "permalink": sanitize_permalink(title),
        "answer": final_html,
        "categoryId": zoho_config['category_id'],
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


def create_kb_article(title: str, answer_text: str):
    """
    Crée un article KB dans Zoho Desk.
    Version simplifiée pour compatibilité avec zoho_api.py.
    
    Args:
        title: Titre de l'article
        answer_text: Contenu HTML de l'article
        
    Returns:
        Réponse JSON de l'API
    """
    zoho_config = get_zoho_config()
    
    headers = {
        "Authorization": f"Zoho-oauthtoken {zoho_config['access_token']}",
        "orgId": zoho_config['org_id'],
        "Content-Type": "application/json"
    }
    
    body = {
        "title": title,
        "permalink": sanitize_permalink(title),
        "answer": answer_text,
        "categoryId": zoho_config['category_id'],
        "status": "Published"
    }
    
    try:
        response = requests.post(
            "https://desk.zoho.com/api/v1/articles",
            headers=headers,
            data=json.dumps(body),
            timeout=30
        )
        return response.json()
    except Exception as e:
        print(f"Erreur lors de la création de l'article : {e}")
        return None
