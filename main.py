"""
Point d'entree principal de l'application Avidsen.
Scrape les tutoriels du site Avidsen et les publie sur Zoho Desk.
"""

import json
import re

import requests
from bs4 import BeautifulSoup

from src.config.settings import HEADERS, TUTORIALS_FOLDER, get_zoho_tutorial_category_id, get_zoho_help_center_url
from src.utils.text_utils import clean_product_name, resilient_request
from src.scraper.tutorial_scraper import (
    get_tutorial_categories,
    get_product_tutorials,
    scrape_tutorial_content,
)
from src.scraper.tutorial_formatter import format_tutorials_section
from src.zoho.api import (
    create_tutorial_article_with_check,
    get_or_create_product_subcategory,
    get_subcategory_permalink,
    get_subcategory_registry,
)


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
            response = resilient_request(category_url, headers=HEADERS, timeout=45, max_retries=3)
            if not response:
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
                product_name = clean_product_name(product_link.get_text(strip=True))
                
                # Ignorer les liens sans texte (doublons image-only sur le site)
                if not product_name:
                    continue
                
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
                        # Dédupliquer par (url, product) : un même tuto partagé par
                        # plusieurs produits doit créer une sous-catégorie pour chacun
                        already = any(
                            t["url"] == tuto["url"] and t.get("product") == product_name
                            for t in all_tutorials
                        )
                        if not already:
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
    Cache le contenu par URL pour éviter de scraper plusieurs fois
    le même tutoriel partagé par différents produits.

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
    # Cache par URL pour ne pas scraper plusieurs fois le même tuto
    content_cache = {}

    for idx, info in enumerate(tutorial_list, 1):
        url = info["url"]
        product = info.get("product", "")
        print(f"\n[{idx}/{total}] {info['title'][:60]}... [{product[:40]}]")

        if url in content_cache:
            # Réutiliser le contenu déjà scrapé, copier pour ne pas modifier l'original
            content = dict(content_cache[url])
            print(f"  [CACHE] Contenu réutilisé depuis le cache")
        else:
            content = scrape_tutorial_content(url)
            if content:
                content_cache[url] = content
            else:
                print("  [WARNING] Echec de l'extraction")
                continue

        content = dict(content)  # copie pour chaque produit
        content["category"] = info.get("category")
        content["product"] = product
        full_tutorials.append(content)

    print(f"\n[SUMMARY] {len(full_tutorials)}/{total} tutoriel(s) extrait(s)")
    print(f"[INFO] {len(content_cache)} URL(s) unique(s) scrapée(s)")
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
    Détecte les titres en double AU SEIN D'UN MÊME PRODUIT et ajoute un suffixe.
    Les tutoriels avec le même titre mais pour des produits différents ne sont
    pas renommés (ils iront dans des sous-catégories différentes).

    Args:
        tutorials: Liste de tutoriels.

    Returns:
        Liste de tutoriels avec titres uniques par produit.
    """
    # Compter par (titre, produit)
    key_count = {}
    for tutorial in tutorials:
        title = tutorial.get("title", "Tutoriel")
        product = tutorial.get("product", "")
        key = (title, product)
        key_count[key] = key_count.get(key, 0) + 1

    duplicates = {k for k, count in key_count.items() if count > 1}
    if duplicates:
        print(f"[INFO] {len(duplicates)} titre(s) en double detecte(s) dans le même produit, ajout de suffixes")

    seen = {}
    for tutorial in tutorials:
        title = tutorial.get("title", "Tutoriel")
        product = tutorial.get("product", "")
        key = (title, product)
        if key in duplicates:
            seen[key] = seen.get(key, 0) + 1
            if seen[key] > 1:
                tutorial["title"] = f"{title} ({seen[key]})"
                print(f"  [RENAME] {title} -> {tutorial['title']}")

    return tutorials


def _inject_product_links(html: str, product_links: dict) -> str:
    """
    Remplace les <span data-product="..."> par des <a> pointant vers la sous-catégorie Zoho KB.
    Les liens s'ouvrent dans un nouvel onglet.
    """
    soup = BeautifulSoup(html, 'html.parser')
    for product_name, url in product_links.items():
        for span in soup.find_all('span', attrs={'data-product': product_name}):
            a_tag = soup.new_tag('a', href=url, target='_blank', rel='noopener noreferrer')
            a_tag.string = span.get_text()
            a_tag['style'] = span.get('style', '')
            span.replace_with(a_tag)
    return str(soup)



def publish_tutorials_to_zoho(tutorials):
    """
    Publie chaque tutoriel comme article Zoho Desk.
    Crée les sous-catégories pour les produits si elles n'existent pas.
    Ajoute des liens cliquables pour les produits applicables.

    Utilise le SubcategoryRegistry global pour garantir :
    - Aucun doublon de sous-catégorie (noms normalisés, cache + API).
    - Des liens "Ce tutoriel est applicable pour" validés et corrects.
    """
    tutorials = _deduplicate_titles(tutorials)
    total = len(tutorials)
    success = 0
    help_center_url = get_zoho_help_center_url()
    registry = get_subcategory_registry()

    print(f"\n[INFO] {total} tutoriel(s) à publier")

    for idx, tutorial in enumerate(tutorials, 1):
        title = tutorial.get("title", "Tutoriel")
        category = tutorial.get("category", "")
        product = tutorial.get("product", "")
        
        print(f"\n[{idx}/{total}] {title[:60]}... [{category or '?'}]")

        # Obtenir l'ID de catégorie Zoho (catégorie parente)
        parent_category_id = get_zoho_tutorial_category_id(category)
        
        # Créer ou retrouver la sous-catégorie produit via le registre
        target_category_id = parent_category_id
        if product and product != "_sans_produit":
            subcat_id = registry.get_or_create(parent_category_id, product)
            if subcat_id:
                target_category_id = subcat_id
                print(f"  [OK] Sous-catégorie: {product}")
            else:
                print(f"  [WARNING] Sous-catégorie non créée pour {product}, utilisation de la catégorie parente")
        
        # Formatter le HTML
        html = format_tutorials_section([tutorial])
        
        # Injecter les liens vers les sous-catégories Zoho KB pour les produits applicables
        if help_center_url and tutorial.get("applicable_products"):
            product_links = {}
            link_errors = []
            for ap in tutorial.get("applicable_products", []):
                if not ap or ap == "_sans_produit":
                    continue
                
                # Créer ou retrouver la sous-catégorie pour ce produit applicable
                registry.get_or_create(parent_category_id, ap)
                
                # Résoudre le permalink via le registre (avec cache)
                permalink = registry.get_permalink(parent_category_id, ap)
                if permalink:
                    product_links[ap] = f"{help_center_url}/{permalink}"
                else:
                    # Pas de permalink trouvé → ne pas injecter de lien cassé
                    link_errors.append(ap)
                    print(f"  [WARNING] Permalink introuvable pour '{ap}' — lien non injecté")
            
            if product_links:
                html = _inject_product_links(html, product_links)
                print(f"  [OK] {len(product_links)} lien(s) validé(s) et injecté(s)")
            if link_errors:
                print(f"  [WARNING] {len(link_errors)} produit(s) sans lien: {', '.join(link_errors[:5])}")
        
        # Publier l'article
        result = create_tutorial_article_with_check(
            title, html, category=category, category_id=target_category_id
        )
        
        if result:
            success += 1
            print(f"  [OK] Article publié: {result.get('id', '?')}")
        else:
            print(f"  [ERROR] Echec de la publication")

    # Résumé final avec statistiques du registre
    print(f"\n[SUMMARY] {success}/{total} article(s) publié(s)")


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