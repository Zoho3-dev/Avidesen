"""
Utilitaires pour la manipulation de texte.
"""

import re
import unicodedata


def clean_title(raw_title: str) -> str:
    """
    Nettoie un titre de produit.
    
    Transforme:
    "Notice à télécharger – 107253 – Station météo ... – Avidsen – 107253"
    en:
    "Station météo ... – Notice-107253"
    
    Args:
        raw_title: Titre brut à nettoyer
        
    Returns:
        Titre nettoyé
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


def sanitize_permalink(title: str, max_length=100) -> str:
    """
    Nettoie un titre pour créer un permalink valide pour Zoho Desk.
    - Retire les accents
    - Remplace espaces et caractères invalides par des tirets
    - Transforme en minuscules
    
    Args:
        title: Titre à transformer
        max_length: Longueur maximale du permalink
        
    Returns:
        Permalink valide
    """
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
        import time
        title = f"article-{int(time.time())}"
    return title


def clean_section_text(text: str) -> str:
    """
    Nettoie le texte d'une section en retirant les lignes trop courtes.
    Retourne un paragraphe HTML justifié.
    
    Args:
        text: Texte à nettoyer
        
    Returns:
        HTML formaté
    """
    lines = [ln.strip() for ln in text.splitlines()]
    good = [ln for ln in lines if len(ln) > 2]
    if not good:
        return ""
    # Join into paragraphs roughly by blank lines - here simply join with <br>
    joined = "<br>".join(good)
    return f"<p style='text-align:justify; line-height:1.5; margin:0 0 12px 0;'>{joined}</p>"
