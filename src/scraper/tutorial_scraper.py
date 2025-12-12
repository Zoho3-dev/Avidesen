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
    Extrait le contenu complet d'un tutoriel EN PRÉSERVANT LE HTML ORIGINAL.
    Supprime les menus, headers, footers pour garder uniquement le contenu du tutoriel.
    
    Args:
        tutorial_url: URL du tutoriel
        
    Returns:
        Dictionnaire contenant le contenu du tutoriel avec HTML original nettoyé
    """
    try:
        response = requests.get(tutorial_url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraire le titre
        title_elem = soup.find('h1')
        title = title_elem.get_text(strip=True) if title_elem else "Tutoriel"
        
        # Extraire les produits applicables
        applicable_products = []
        applicable_section = soup.find(string=re.compile(r'Ce tutoriel est applicable pour'))
        if applicable_section:
            parent = applicable_section.find_parent()
            if parent:
                product_links = parent.find_all('a', href=re.compile(r'/ref/\d+'))
                for link in product_links:
                    ref_match = re.search(r'/ref/(\d+)', link.get('href', ''))
                    if ref_match:
                        applicable_products.append(ref_match.group(1))
        
        # EXTRACTION PROPRE DU CONTENU PRINCIPAL
        # Supprimer tous les éléments de navigation et inutiles
        elements_to_remove = [
            'header', 'nav', 'footer',
            {'name': 'div', 'class': re.compile(r'header|navigation|nav|menu|footer|sidebar|cookie|banner', re.I)},
            {'name': 'div', 'id': re.compile(r'header|navigation|nav|menu|footer|sidebar|cookie|banner', re.I)},
            {'name': 'a', 'class': re.compile(r'skip|logo', re.I)},
            'script', 'style', 'noscript'
        ]
        
        for element in elements_to_remove:
            if isinstance(element, dict):
                for tag in soup.find_all(**element):
                    tag.decompose()
            else:
                for tag in soup.find_all(element):
                    tag.decompose()
        
        # Chercher le conteneur principal du tutoriel
        # Essayer plusieurs sélecteurs pour trouver le contenu
        main_content = None
        
        # Essayer de trouver le conteneur principal
        selectors = [
            ('main', {}),
            ('article', {}),
            ('div', {'class': re.compile(r'content|tutorial|main|article', re.I)}),
            ('div', {'id': re.compile(r'content|tutorial|main|article', re.I)}),
        ]
        
        for tag, attrs in selectors:
            main_content = soup.find(tag, attrs)
            if main_content:
                break
        
        # Si aucun conteneur trouvé, prendre le body
        if not main_content:
            main_content = soup.find('body')
        
        if main_content:
            # Supprimer encore les éléments indésirables dans le contenu
            for element in elements_to_remove:
                if isinstance(element, dict):
                    for tag in main_content.find_all(**element):
                        tag.decompose()
                else:
                    for tag in main_content.find_all(element):
                        tag.decompose()
            
            # Convertir les URLs relatives en absolues pour les images
            for img in main_content.find_all('img'):
                # Gérer src et data-src
                for attr in ['src', 'data-src', 'srcset']:
                    src = img.get(attr)
                    if src and src.startswith('/'):
                        img[attr] = f"https://www.avidsen.com{src}"
            
            # Convertir les liens relatifs en absolus
            for link in main_content.find_all('a'):
                href = link.get('href')
                if href and href.startswith('/'):
                    link['href'] = f"https://www.avidsen.com{href}"
            
            # Extraire le HTML nettoyé
            html_content = str(main_content)
        else:
            # Fallback
            html_content = "<p>Contenu non disponible</p>"
        
        tutorial_data = {
            'url': tutorial_url,
            'title': title,
            'applicable_products': applicable_products,
            'html_content': html_content,  # HTML original préservé et nettoyé
            'steps': []  # Vide pour compatibilité
        }
        
        print(f"[OK] Tutoriel extrait : {title} (HTML nettoyé et préservé)")
        return tutorial_data
        
    except Exception as e:
        print(f"[ERROR] Erreur lors de l'extraction du tutoriel {tutorial_url}: {e}")
        return None

