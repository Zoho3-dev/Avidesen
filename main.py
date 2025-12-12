"""
Point d'entrée principal de l'application Avidsen.
Lance le scraping des produits et la création d'articles Zoho.
"""

from src.scraper.web_scraper import scrape_all_pages


def main():
    """
    Fonction principale qui lance le processus de scraping.
    """
    print("=" * 60)
    print("Démarrage du scraping Avidsen")
    print("=" * 60)
    
    scrape_all_pages()
    
    print("\n" + "=" * 60)
    print("Scraping terminé")
    print("=" * 60)


if __name__ == "__main__":
    main()
