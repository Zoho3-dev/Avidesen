"""Utilitaire pour vérifier l'existence d'articles dans Zoho KB."""
import sys
sys.path.insert(0, '..')
from src.zoho.api import check_article_exists, get_zoho_tutorial_category_id

def check_tutorial(title: str, category: str = 'motorisation'):
    """Vérifie si un tutoriel existe dans Zoho KB."""
    cat_id = get_zoho_tutorial_category_id(category)
    result = check_article_exists(title=title, category_id=cat_id)
    
    if result:
        print(f'✅ Article trouvé: {result.get("title")}')
        print(f'   ID: {result.get("id")}')
        print(f'   Permalink: {result.get("permalink")}')
        return result
    else:
        print(f'❌ Article non trouvé: {title}')
        return None

if __name__ == '__main__':
    if len(sys.argv) > 1:
        title = ' '.join(sys.argv[1:])
        check_tutorial(title)
    else:
        print("Usage: python analyze_tuto.py <titre de l'article>")
        print("Exemple: python analyze_tuto.py Prédiagnostic CAB9SL24V")
