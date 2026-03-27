"""
Point d'entree principal de l'application Avidsen.
Scrape les tutoriels du site Avidsen et les publie sur Zoho Desk.
"""

import json
import re

import requests
from bs4 import BeautifulSoup

from src.config.settings import HEADERS, TUTORIALS_FOLDER
from src.scraper.tutorial_scraper import (
    get_tutorial_categories,
    get_product_tutorials,
    scrape_tutorial_content,
)
from src.scraper.tutorial_formatter import format_tutorials_section
from src.zoho.api import create_tutorial_article_with_check


# ---------------------------------------------------------------------------
# Etape 1 : Decouverte des tutoriels
# ---------------------------------------------------------------------------

def discover_all_tutorials():
    """
    Parcourt toutes les categories du site Avidsen pour decouvrir les tutoriels.

    Returns:
        Liste de dictionnaires {url, title, category, product}.
    """
    print("=" * 60)
    print("DECOUVERTE DES TUTORIELS")
    print("=" * 60)

    all_tutorials = []
    categories = get_tutorial_categories()
    print(f"\n[INFO] {len(categories)} categorie(s) a explorer")

    for category in categories:
        print(f"\n[CATEGORY] {category}")
        category_url = f"https://www.avidsen.com/fr/assistance/tutoriel-sav/{category}"

        try:
            response = requests.get(category_url, headers=HEADERS, timeout=20)
            if response.status_code != 200:
                print(f"  [WARNING] Impossible d'acceder a {category}")
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            
            # Pattern standard pour la plupart des catégories
            pattern = re.compile(r'/tutoriel-sav/' + re.escape(category) + r'/ref/[^/]+$')
            product_links = soup.find_all("a", href=pattern)
            
            # Pattern spécial pour domotique
            if category == 'domotique':
                domotique_pattern = re.compile(r'/categorie_tutoriel_domotique/\d+$')
                domotique_links = soup.find_all("a", href=domotique_pattern)
                product_links.extend(domotique_links)
            
            print(f"  [INFO] {len(product_links)} produit(s) trouve(s)")

            for product_link in product_links:
                product_url = product_link.get("href", "")
                product_name = product_link.get_text(strip=True)
                
                # Extraction de la référence selon le pattern
                ref_match = re.search(r'/ref/([^/]+)$', product_url)
                if not ref_match:
                    # Pattern domotique: /categorie_tutoriel_domotique/{ref}
                    ref_match = re.search(r'/categorie_tutoriel_domotique/(\d+)$', product_url)
                
                if not ref_match:
                    continue

                product_ref = ref_match.group(1)
                try:
                    tutorials = get_product_tutorials(product_ref, [category])
                    for tuto in tutorials:
                        if not any(t["url"] == tuto["url"] for t in all_tutorials):
                            tuto["product"] = product_name
                            all_tutorials.append(tuto)
                    if tutorials:
                        print(f"    [OK] {len(tutorials)} tutoriel(s) pour {product_name[:50]}")
                except Exception as exc:
                    print(f"    [WARNING] Erreur pour {product_ref}: {exc}")

        except Exception as exc:
            print(f"  [ERROR] {category}: {exc}")

    print(f"\n[SUMMARY] {len(all_tutorials)} tutoriel(s) unique(s) decouvert(s)")
    return all_tutorials


# ---------------------------------------------------------------------------
# Etape 2 : Extraction du contenu
# ---------------------------------------------------------------------------

def fetch_tutorials_content(tutorial_list):
    """
    Extrait le contenu HTML complet de chaque tutoriel.

    Args:
        tutorial_list: Liste de tutoriels (issus de *discover_all_tutorials*).

    Returns:
        Liste de tutoriels enrichis avec leur contenu.
    """
    print("\n" + "=" * 60)
    print("EXTRACTION DU CONTENU")
    print("=" * 60)

    full_tutorials = []
    total = len(tutorial_list)

    for idx, info in enumerate(tutorial_list, 1):
        print(f"\n[{idx}/{total}] {info['title'][:60]}...")
        content = scrape_tutorial_content(info["url"])
        if content:
            content["category"] = info.get("category")
            content["product"] = info.get("product")
            full_tutorials.append(content)
        else:
            print("  [WARNING] Echec de l'extraction")

    print(f"\n[SUMMARY] {len(full_tutorials)}/{total} tutoriel(s) extrait(s)")
    return full_tutorials


# ---------------------------------------------------------------------------
# Etape 3 : Sauvegarde locale
# ---------------------------------------------------------------------------

def save_tutorials(tutorials):
    """Sauvegarde les tutoriels dans un fichier JSON."""
    output_file = TUTORIALS_FOLDER / "all_tutorials.json"
    with open(output_file, "w", encoding="utf-8") as fh:
        json.dump(tutorials, fh, ensure_ascii=False, indent=2)
    print(f"\n[OK] Tutoriels sauvegardes dans {output_file}")


# ---------------------------------------------------------------------------
# Etape 4 : Publication sur Zoho Desk
# ---------------------------------------------------------------------------

def _deduplicate_titles(tutorials):
    """
    Détecte les titres en double et ajoute un suffixe pour les différencier.
    Ex: deux tutoriels "Diagnostic résolution de panne SORIA" deviennent
        "Diagnostic résolution de panne SORIA" et
        "Diagnostic résolution de panne SORIA (2)".

    Args:
        tutorials: Liste de tutoriels.

    Returns:
        Liste de tutoriels avec titres uniques.
    """
    title_count = {}
    for tutorial in tutorials:
        title = tutorial.get("title", "Tutoriel")
        title_count[title] = title_count.get(title, 0) + 1

    # Identifier les titres qui apparaissent plus d'une fois
    duplicates = {t for t, count in title_count.items() if count > 1}
    if duplicates:
        print(f"[INFO] {len(duplicates)} titre(s) en double detecte(s), ajout de suffixes")

    # Attribuer un suffixe aux doublons
    seen = {}
    for tutorial in tutorials:
        title = tutorial.get("title", "Tutoriel")
        if title in duplicates:
            seen[title] = seen.get(title, 0) + 1
            if seen[title] > 1:
                tutorial["title"] = f"{title} ({seen[title]})"
                print(f"  [RENAME] {title} -> {tutorial['title']}")

    return tutorials


def publish_tutorials_to_zoho(tutorials):
    """
    Publie chaque tutoriel comme article Zoho Desk.

    Args:
        tutorials: Liste de tutoriels avec contenu HTML.
    """
    tutorials = _deduplicate_titles(tutorials)
    total = len(tutorials)
    success = 0

    for idx, tutorial in enumerate(tutorials, 1):
        title = tutorial.get("title", "Tutoriel")
        category = tutorial.get("category")
        print(f"\n[{idx}/{total}] {title[:60]}... [{category or '?'}]")

        html = format_tutorials_section([tutorial])
        result = create_tutorial_article_with_check(title, html, category=category)
        if result:
            success += 1

    print(f"\n[SUMMARY] {success}/{total} article(s) cree(s)")


# ---------------------------------------------------------------------------
# Point d'entree
# ---------------------------------------------------------------------------

def main():
    """Orchestre le pipeline complet : decouverte -> extraction -> sauvegarde -> publication."""
    print("\n" + "=" * 60)
    print("SCRAPING DES TUTORIELS AVIDSEN")
    print("=" * 60)

    # 1. Decouvrir
    tutorial_list = discover_all_tutorials()
    if not tutorial_list:
        print("\n[ERROR] Aucun tutoriel trouve.")
        return

    # 2. Extraire le contenu
    full_tutorials = fetch_tutorials_content(tutorial_list)
    if not full_tutorials:
        print("\n[ERROR] Aucun contenu extrait.")
        return

    # 3. Sauvegarder en local
    save_tutorials(full_tutorials)

    # 4. Publier sur Zoho Desk (automatique)
    print("\n" + "=" * 60)
    print("PUBLICATION AUTOMATIQUE SUR ZOHO DESK")
    print("=" * 60)
    publish_tutorials_to_zoho(full_tutorials)

    print("\n" + "=" * 60)
    print("TERMINE")
    print("=" * 60)


if __name__ == "__main__":
    main()
