"""
Script pour tester le scraping d'un seul tutoriel et le publier dans Zoho KB.
Usage:
  python test_single_tuto.py <URL_DU_TUTO>                     # scrape + preview
  python test_single_tuto.py <URL_DU_TUTO> --publish            # scrape + publish
  python test_single_tuto.py <URL_DU_TUTO> --publish motorisation  # scrape + publish dans catégorie
"""
import sys
import re
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.scraper.tutorial_scraper import scrape_tutorial_content
from src.scraper.tutorial_formatter import format_tutorials_section
from src.zoho.api import create_tutorial_article_with_check
from bs4 import BeautifulSoup


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_single_tuto.py <URL>                        # scrape + preview")
        print("  python test_single_tuto.py <URL> --publish              # scrape + publier")
        print("  python test_single_tuto.py <URL> --publish motorisation # scrape + publier dans catégorie")
        print("\nCatégories: motorisation, visiophone, securite, solaire, domotique")
        sys.exit(1)

    url = sys.argv[1]
    do_publish = '--publish' in sys.argv
    category = None
    if do_publish and len(sys.argv) > 3:
        category = sys.argv[3]

    print(f"Scraping: {url}\n")

    result = scrape_tutorial_content(url)
    if not result:
        print("ERREUR: Aucun résultat retourné.")
        sys.exit(1)

    html = result['html_content']
    soup = BeautifulSoup(html, 'html.parser')
    imgs = soup.find_all('img')
    tables = soup.find_all('table')

    print(f"Titre: {result['title']}")
    print(f"Images: {len(imgs)}")
    print(f"Tables: {len(tables)}")
    print(f"Blocs image|texte (40%%): {html.count('width: 40%')}")
    print(f"Taille HTML: {len(html)} caractères")

    # Sauvegarder le HTML pour inspection locale
    output_file = "test_output.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{result['title']}</title>
<style>body {{ max-width: 900px; margin: 20px auto; font-family: Poppins, Arial, sans-serif; }}</style>
</head><body>
<h1>{result['title']}</h1>
{html}
</body></html>""")
    print(f"\nHTML sauvegardé dans: {output_file}")

    if do_publish:
        print("\n--- Publication sur Zoho KB ---")
        formatted_html = format_tutorials_section([result])
        cat_label = category or "défaut"
        print(f"Catégorie: {cat_label}")
        response = create_tutorial_article_with_check(result['title'], formatted_html, category=category)
        if response:
            article_id = response.get('id', '?')
            print(f"\nArticle publié avec succès! ID: {article_id}")
        else:
            print("\nEchec de la publication.")
    else:
        print("\nAjoutez --publish pour publier dans Zoho KB:")
        print(f"  python test_single_tuto.py {url} --publish")
        print(f"  python test_single_tuto.py {url} --publish motorisation")


if __name__ == '__main__':
    main()
