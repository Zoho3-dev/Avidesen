"""
Module de scraping du site web Avidsen.
Gère la pagination et la récupération des URLs produits.
"""

import requests
from bs4 import BeautifulSoup

from src.config.settings import BASE_URL_TEMPLATE, HEADERS
from src.scraper.product_parser import scrape_product_page


def scrape_all_pages():
    """
    Scrape toutes les pages de produits du site Avidsen.
    Parcourt les pages de manière séquentielle jusqu'à ce qu'il n'y ait plus de produits.
    """
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
