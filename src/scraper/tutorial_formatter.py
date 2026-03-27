"""

Module de formatage des tutoriels pour Zoho Desk.

Nettoie le HTML scrapé et le prépare pour publication.

"""

from typing import List, Dict


def format_tutorials_section(tutorials: List[Dict]) -> str:
    """
    Nettoie et assemble le HTML des tutoriels pour Zoho Desk.

    Args:
        tutorials: Liste de tutoriels avec 'html_content'.

    Returns:
        HTML nettoyé prêt pour publication.
    """
    if not tutorials:
        return ""

    html_parts = []
    for tutorial in tutorials:
        html_content = tutorial.get("html_content", "")
        if html_content:
            html_parts.append(clean_tutorial_html(html_content))

        if len(tutorials) > 1:
            html_parts.append(
                "<hr style='margin:30px 0; border:none; border-top:1px solid #e0e0e0;'/>"
            )

    return "\n".join(html_parts)


def clean_tutorial_html(html_content: str) -> str:
    """
    Nettoie le HTML d'un tutoriel pour enlever les éléments superflus
    tout en préservant les images (principales et icônes inline), tableaux et listes.
    Utilise BeautifulSoup pour un nettoyage précis sans risque de casser le contenu.
    Args:
        html_content: HTML original du tutoriel
    Returns:
        HTML nettoyé
    """
    from bs4 import BeautifulSoup
    import re
    soup = BeautifulSoup(html_content, "html.parser")
    # Mots-clés identifiant les éléments à supprimer
    REMOVE_KEYWORDS = ["sommaire", "📖", "voir sur avidsen.com"]
    # Supprimer les titres contenant "Sommaire"
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        if "sommaire" in heading.get_text(strip=True).lower():
            heading.decompose()
    # Supprimer les <nav> et <script>/<style>
    for tag in soup.find_all(["nav", "script", "style", "noscript"]):
        tag.decompose()
    # Supprimer les blocs contenant des mots-clés indésirables
    # (uniquement les blocs de premier niveau, pas les enfants profonds)
    for div in soup.find_all(["div", "p"]):
        text = div.get_text(strip=True).lower()
        # Ne supprimer que les petits blocs (< 200 caractères) contenant un mot-clé
        if len(text) < 200 and any(kw in text for kw in REMOVE_KEYWORDS):
            # Ne pas supprimer si le bloc contient des images ou tableaux utiles
            if not div.find(["table", "img", "iframe"]):
                div.decompose()

    # Nettoyer les lignes vides multiples

    result = str(soup)

    result = re.sub(r"\n\s*\n\s*\n", "\n\n", result)

    return result.strip()
