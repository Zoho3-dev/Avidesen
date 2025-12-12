"""
Script séparé pour scraper tous les tutoriels Avidsen.
Fonctionne indépendamment du scraping des produits.
"""

import requests
from bs4 import BeautifulSoup
import re
import os
from pathlib import Path

from src.config.settings import HEADERS, get_zoho_config, get_zoho_tutorial_category_id
from src.scraper.tutorial_scraper import (
    get_tutorial_categories,
    scrape_tutorial_content
)
from src.scraper.tutorial_formatter import format_tutorials_section
from src.utils.text_utils import sanitize_permalink
import json


# Dossier pour sauvegarder les tutoriels
TUTORIALS_FOLDER = Path("tutorials_data")
TUTORIALS_FOLDER.mkdir(exist_ok=True)


def discover_all_tutorials():
    """
    Découvre tous les tutoriels disponibles sur le site Avidsen.
    Utilise les fonctions du module tutorial_scraper pour éviter la redondance.
    
    Returns:
        Liste de tous les tutoriels trouvés
    """
    print("=" * 60)
    print("DÉCOUVERTE DE TOUS LES TUTORIELS")
    print("=" * 60)
    
    all_tutorials = []
    categories = get_tutorial_categories()
    
    print(f"\n[INFO] {len(categories)} catégories à explorer")
    
    for category in categories:
        print(f"\n[CATEGORY] Exploration de '{category}'...")
        category_url = f"https://www.avidsen.com/fr/assistance/tutoriel-sav/{category}"
        
        try:
            # Récupérer la page de catégorie
            response = requests.get(category_url, headers=HEADERS, timeout=20)
            if response.status_code != 200:
                print(f"[WARNING] Impossible d'accéder à {category}")
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Trouver tous les liens vers les produits (/ref/)
            product_links = soup.find_all('a', href=re.compile(r'/tutoriel-sav/' + re.escape(category) + r'/ref/[^/]+$'))
            
            print(f"[INFO] {len(product_links)} produit(s) trouvé(s) dans {category}")
            
            # Pour chaque produit, extraire la référence et trouver ses tutoriels
            for product_link in product_links:
                product_url = product_link.get('href', '')
                product_name = product_link.get_text(strip=True)
                
                # Extraire la référence du produit depuis l'URL
                ref_match = re.search(r'/ref/([^/]+)$', product_url)
                if not ref_match:
                    continue
                
                product_ref = ref_match.group(1)
                
                try:
                    # Utiliser la fonction du module pour récupérer les tutoriels
                    from src.scraper.tutorial_scraper import get_product_tutorials
                    product_tutorials = get_product_tutorials(product_ref, [category])
                    
                    for tutorial in product_tutorials:
                        # Vérifier si déjà ajouté (éviter doublons)
                        if not any(t['url'] == tutorial['url'] for t in all_tutorials):
                            tutorial['product'] = product_name
                            all_tutorials.append(tutorial)
                    
                    if product_tutorials:
                        print(f"  [OK] {len(product_tutorials)} tutoriel(s) pour {product_name[:50]}...")
                    
                except Exception as e:
                    print(f"  [WARNING] Erreur pour produit {product_ref}: {e}")
            
        except Exception as e:
            print(f"[ERROR] Erreur pour {category}: {e}")
    
    print(f"\n[SUMMARY] Total : {len(all_tutorials)} tutoriels uniques découverts")
    return all_tutorials


def scrape_all_tutorials_content(tutorial_list):
    """
    Extrait le contenu complet de tous les tutoriels.
    
    Args:
        tutorial_list: Liste des tutoriels à extraire
        
    Returns:
        Liste des tutoriels avec leur contenu complet
    """
    print("\n" + "=" * 60)
    print("EXTRACTION DU CONTENU DES TUTORIELS")
    print("=" * 60)
    
    full_tutorials = []
    total = len(tutorial_list)
    
    for i, tutorial_info in enumerate(tutorial_list, 1):
        print(f"\n[{i}/{total}] Extraction : {tutorial_info['title'][:60]}...")
        
        tutorial_content = scrape_tutorial_content(tutorial_info['url'])
        
        if tutorial_content:
            # Ajouter la catégorie
            tutorial_content['category'] = tutorial_info.get('category')
            full_tutorials.append(tutorial_content)
        else:
            print(f"[WARNING] Échec de l'extraction")
    
    print(f"\n[SUMMARY] {len(full_tutorials)}/{total} tutoriels extraits avec succès")
    return full_tutorials


def save_tutorials_to_json(tutorials):
    """
    Sauvegarde les tutoriels dans un fichier JSON.
    
    Args:
        tutorials: Liste des tutoriels à sauvegarder
    """
    output_file = TUTORIALS_FOLDER / "all_tutorials.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(tutorials, f, ensure_ascii=False, indent=2)
    
    print(f"\n[OK] Tutoriels sauvegardés dans {output_file}")


def create_zoho_tutorial_articles(tutorials):
    """
    Crée des articles Zoho pour chaque tutoriel dans la catégorie Tutoriels.
    
    Args:
        tutorials: Liste des tutoriels à publier
    """
    print("\n" + "=" * 60)
    print("CRÉATION DES ARTICLES ZOHO")
    print("=" * 60)
    
    zoho_config = get_zoho_config()
    tutorial_category_id = get_zoho_tutorial_category_id()
    
    print(f"\n[INFO] Catégorie cible : {tutorial_category_id}")
    
    zoho_headers = {
        "Authorization": f"Zoho-oauthtoken {zoho_config['access_token']}",
        "orgId": zoho_config['org_id'],
        "Content-Type": "application/json"
    }
    
    total = len(tutorials)
    success_count = 0
    
    for i, tutorial in enumerate(tutorials, 1):
        title = tutorial.get('title', 'Tutoriel')
        print(f"\n[{i}/{total}] Création article : {title[:60]}...")
        
        # Formater le tutoriel en HTML
        html = format_tutorials_section([tutorial])
        
        # Préparer le payload Zoho avec la catégorie Tutoriels
        zoho_body = {
            "title": title,
            "permalink": sanitize_permalink(title),
            "answer": html,
            "categoryId": tutorial_category_id,  # Catégorie Tutoriels
            "status": "Published"
        }
        
        try:
            response = requests.post(
                "https://desk.zoho.com/api/v1/articles",
                headers=zoho_headers,
                data=json.dumps(zoho_body),
                timeout=30
            )
            
            if response.status_code in (200, 201):
                print(f"[OK] Article créé")
                success_count += 1
            else:
                print(f"[ERROR] Zoho error ({response.status_code}): {response.text[:100]}")
                
        except Exception as e:
            print(f"[ERROR] Échec de la requête : {e}")
    
    print(f"\n[SUMMARY] {success_count}/{total} articles créés avec succès")
    print(f"[INFO] Articles créés dans la catégorie : {tutorial_category_id}")


def main():
    """
    Fonction principale du script de scraping des tutoriels.
    """
    print("\n" + "=" * 60)
    print("SCRAPING COMPLET DES TUTORIELS AVIDSEN")
    print("=" * 60)
    
    # Étape 1 : Découvrir tous les tutoriels
    tutorial_list = discover_all_tutorials()
    
    if not tutorial_list:
        print("\n[ERROR] Aucun tutoriel trouvé")
        return
    
    # Étape 2 : Extraire le contenu
    full_tutorials = scrape_all_tutorials_content(tutorial_list)
    
    if not full_tutorials:
        print("\n[ERROR] Aucun contenu extrait")
        return
    
    # Étape 3 : Sauvegarder en JSON
    save_tutorials_to_json(full_tutorials)
    
    # Étape 4 : Créer les articles Zoho
    print("\n" + "=" * 60)
    user_input = input("Voulez-vous créer les articles Zoho maintenant ? (o/n) : ")
    
    if user_input.lower() in ['o', 'oui', 'y', 'yes']:
        create_zoho_tutorial_articles(full_tutorials)
    else:
        print("\n[INFO] Articles Zoho non créés. Vous pouvez les créer plus tard.")
        print(f"[INFO] Les tutoriels sont sauvegardés dans {TUTORIALS_FOLDER / 'all_tutorials.json'}")
    
    print("\n" + "=" * 60)
    print("SCRAPING TERMINÉ")
    print("=" * 60)


if __name__ == "__main__":
    main()
