"""
Détection de tableaux dans les PDFs.
"""

import re


def is_toc_block(text: str) -> bool:
    """
    Détecte si un bloc de texte est une table des matières.
    
    Args:
        text: Texte à analyser
        
    Returns:
        True si le texte ressemble à une table des matières
    """
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
