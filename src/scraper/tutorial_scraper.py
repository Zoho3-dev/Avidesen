"""
Module de scraping des tutoriels Avidsen.
Extrait les tutoriels et les lie aux produits.
"""

import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional

from src.config.settings import HEADERS


# URL de base pour les tutoriels
TUTORIAL_BASE_URL = "https://www.avidsen.com/fr/assistance/tutoriel-sav"
TUTORIAL_CATEGORIES_URL = f"{TUTORIAL_BASE_URL}"


def get_tutorial_categories() -> List[str]:
    """
    Récupère la liste des catégories de tutoriels depuis la page principale.
    
    Returns:
        Liste des catégories (ex: ['motorisation', 'visiophone', 'solaire'])
    """
    try:
        response = requests.get(TUTORIAL_CATEGORIES_URL, headers=HEADERS, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        categories = []
        
        # Chercher les liens de catégories
        # Format: /fr/assistance/tutoriel-sav/{categorie}
        links = soup.find_all('a', href=re.compile(r'/fr/assistance/tutoriel-sav/[^/]+$'))
        
        for link in links:
            href = link.get('href', '')
            match = re.search(r'/tutoriel-sav/([^/]+)$', href)
            if match:
                category = match.group(1)
                if category not in categories:
                    categories.append(category)
        
        print(f"[OK] Catégories trouvées : {categories}")
        return categories
        
    except Exception as e:
        print(f"[ERROR] Erreur lors de la récupération des catégories : {e}")
        # Fallback sur des catégories connues
        return ['motorisation', 'visiophone', 'solaire', 'alarme', 'domotique']


def get_product_tutorials(product_ref: str, categories: List[str] = None) -> List[Dict]:
    """
    Récupère les tutoriels associés à un produit en testant toutes les catégories.
    
    Args:
        product_ref: Référence du produit (ex: '127100')
        categories: Liste des catégories à tester (optionnel)
        
    Returns:
        Liste de dictionnaires contenant les informations des tutoriels
    """
    if categories is None:
        categories = get_tutorial_categories()
    
    tutorials = []
    
    for category in categories:
        # Construire l'URL de la page produit
        url = f"{TUTORIAL_BASE_URL}/{category}/ref/{product_ref}"
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=20)
            
            # Si la page existe (status 200)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Chercher les liens vers les tutoriels
                # Format: /fr/assistance/tutoriel-sav/tuto/{slug}
                tutorial_links = soup.find_all('a', href=re.compile(r'/tutoriel-sav/tuto/[^/]+$'))
                
                for link in tutorial_links:
                    tutorial_url = link.get('href', '')
                    if tutorial_url.startswith('/'):
                        tutorial_url = f"https://www.avidsen.com{tutorial_url}"
                    
                    tutorial_title = link.get_text(strip=True)
                    
                    if tutorial_url and tutorial_title:
                        tutorials.append({
                            'url': tutorial_url,
                            'title': tutorial_title,
                            'category': category
                        })
                
                if tutorial_links:
                    print(f"[OK] Trouvé {len(tutorial_links)} tutoriel(s) pour {product_ref} dans {category}")
                
        except Exception as e:
            # Ignorer les erreurs 404 (page n'existe pas pour cette catégorie)
            if response.status_code != 404:
                print(f"[WARNING] Erreur pour {product_ref} dans {category}: {e}")
    
    return tutorials


def scrape_tutorial_content(tutorial_url: str) -> Optional[Dict]:
    """
    Extrait le contenu d'un tutoriel Avidsen.
    Approche ultra-simple: prendre tout le body, nettoyer navigation.
    
    Args:
        tutorial_url: URL du tutoriel
        
    Returns:
        Dictionnaire contenant le contenu du tutoriel
    """
    try:
        response = requests.get(tutorial_url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Titre
        title_elem = soup.find('h1')
        title = title_elem.get_text(strip=True) if title_elem else "Tutoriel"
        
        # 2. APPROCHE SIMPLE: Prendre le body entier
        body = soup.find('body')
        if not body:
            print(f"[ERROR] Pas de body trouvé pour {tutorial_url}")
            return None
        
        # 3. Supprimer SEULEMENT les éléments de navigation évidents
        # (garder tout le contenu)
        for tag in body.find_all(['nav', 'header', 'footer']):
            tag.decompose()
        
        for tag in body.find_all('script'):
            tag.decompose()
        
        for tag in body.find_all('style'):
            tag.decompose()
        
        # Supprimer les divs de menu/navigation par classe
        for tag in body.find_all('div', class_=re.compile(r'menu|navigation|nav-', re.I)):
            tag.decompose()
            
        # Supprimer les iframes/embeds qui pourraient poser problème (optionnel, mais souvent mieux pour KB)
        # On garde les iframes Youtube si besoin, mais ici on veut surtout nettoyer
        # for tag in body.find_all('iframe'):
        #     tag.decompose() 
        
        # 4. FIX TOUTES LES IMAGES (Critique pour lazy loading)
        for img in body.find_all('img'):
            # Chercher l'URL réelle (lazy loading)
            # Priorité: data-lazy-src > data-src > data-original > src
            real_url = (img.get('data-lazy-src') or 
                       img.get('data-src') or 
                       img.get('data-original') or 
                       img.get('src'))
            
            if real_url:
                # Rendre absolu
                if real_url.startswith('/'):
                    real_url = f"https://www.avidsen.com{real_url}"
                img['src'] = real_url
            
            # Supprimer attributs lazy loading qui peuvent confliter
            for attr in ['data-lazy-src', 'data-src', 'data-original', 'srcset', 'data-srcset', 'loading', 'sizes', 'data-lazy-srcset']:
                if img.get(attr):
                    del img[attr]
            
            # Style inline minimal pour responsive sans casser le layout original
            # On n'écrase plus le style existant, on ajoute juste max-width
            current_style = img.get('style', '')
            new_style = 'max-width: 100%; height: auto;'
            
            if current_style:
                img['style'] = f"{current_style}; {new_style}"
            else:
                img['style'] = new_style
        
        # 5. Fix liens
        for link in body.find_all('a'):
            href = link.get('href')
            if href and href.startswith('/'):
                link['href'] = f"https://www.avidsen.com{href}"
            link['style'] = 'color: #2E86C1;'
        
        # 6. Styles pour headings
        for h3 in body.find_all('h3'):
            h3['style'] = 'color: #2E86C1; font-size: 1.25em; margin: 1.5em 0 0.5em 0; font-weight: 600;'
        
        for h2 in body.find_all('h2'):
            h2['style'] = 'color: #2E86C1; font-size: 1.5em; margin: 1.5em 0 0.5em 0; font-weight: 600;'
        
        # 7. Paragraphes
        for p in body.find_all('p'):
            p['style'] = 'margin: 1em 0; line-height: 1.6;'
        
        # 8. Extraire HTML
        html_content = str(body)
        
        tutorial_data = {
            'url': tutorial_url,
            'title': title,
            'html_content': html_content,
            'steps': []  # Compatibilité
        }
        
        print(f"[OK] Tutoriel extrait : {title} (Version Body Clean)")
        return tutorial_data
        
    except Exception as e:
        print(f"[ERROR] Erreur extraction {tutorial_url}: {e}")
        return None

