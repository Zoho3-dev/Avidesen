# Guide de Scraping des Tutoriels Avidsen

## Vue d'ensemble

Ce guide explique comment utiliser le système de scraping des tutoriels Avidsen pour extraire et publier automatiquement les tutoriels dans Zoho Desk.

## Architecture

### Processus Séparés

Le système utilise **deux processus indépendants** pour optimiser les performances :

1. **Scraping des Produits** (`main.py`) - Rapide ⚡
   - Scrape les notices PDF des produits
   - Publie dans la catégorie "Produits"

2. **Scraping des Tutoriels** (`scrape_tutorials.py`) - Complet 📚
   - Scrape tous les tutoriels disponibles
   - Publie dans la catégorie "Tutoriels"

### Flux de Scraping des Tutoriels

```
1. Découverte des catégories
   ↓
2. Pour chaque catégorie → Trouver les produits
   ↓
3. Pour chaque produit → Extraire les tutoriels
   ↓
4. Nettoyage du HTML (suppression navigation/menus)
   ↓
5. Sauvegarde en JSON
   ↓
6. Publication dans Zoho Desk
```

## Utilisation

### Scraping des Tutoriels

```bash
python scrape_tutorials.py
```

**Ce que fait le script** :
1. Découvre automatiquement les catégories (motorisation, visiophone, solaire, etc.)
2. Pour chaque catégorie, trouve tous les produits
3. Pour chaque produit, extrait les tutoriels associés
4. Nettoie le HTML (supprime menus, headers, footers)
5. Préserve la structure HTML originale et les images
6. Sauvegarde dans `tutorials_data/all_tutorials.json`
7. Demande confirmation avant de publier dans Zoho

### Sortie Attendue

```
============================================================
SCRAPING COMPLET DES TUTORIELS AVIDSEN
============================================================

============================================================
DÉCOUVERTE DE TOUS LES TUTORIELS
============================================================

[INFO] 5 catégories à explorer

[CATEGORY] Exploration de 'motorisation'...
[INFO] 8 produit(s) trouvé(s) dans motorisation
  [OK] 1 tutoriel(s) pour Avidsen - 114255 - Clavier à code...
  [OK] 2 tutoriel(s) pour Avidsen - 114375 - Kit solaire...

[SUMMARY] Total : 67 tutoriels uniques découverts

============================================================
EXTRACTION DU CONTENU DES TUTORIELS
============================================================

[1/67] Extraction : Programmation d'un clavier à codes...
[OK] Tutoriel extrait : Programmation d'un clavier à codes (HTML nettoyé et préservé)

[SUMMARY] 65/67 tutoriels extraits avec succès

[OK] Tutoriels sauvegardés dans tutorials_data/all_tutorials.json

============================================================
Voulez-vous créer les articles Zoho maintenant ? (o/n) : o

============================================================
CRÉATION DES ARTICLES ZOHO
============================================================

[INFO] Catégorie cible : 603196000009391009

[1/65] Création article : Programmation d'un clavier à codes...
[OK] Article créé

[SUMMARY] 65/65 articles créés avec succès
[INFO] Articles créés dans la catégorie : 603196000009391009
```

## Configuration

### Catégorie Zoho pour les Tutoriels

Ajoutez cette ligne dans `config.txt` :

```
ZOHO_TUTORIAL_CATEGORY_ID=603196000009391009
```

**Configuration complète** :
```
# Identifiants API
ZOHO_CLIENT_ID=votre_client_id
ZOHO_CLIENT_SECRET=votre_client_secret
ZOHO_ORG_ID=votre_org_id

# Catégorie pour les PRODUITS
ZOHO_PRODUCT_CATEGORY_ID=votre_category_id_produits

# Catégorie pour les TUTORIELS
ZOHO_TUTORIAL_CATEGORY_ID=603196000009391009

# Tokens (générés automatiquement)
ZOHO_ACCESS_TOKEN=...
ZOHO_REFRESH_TOKEN=...
```

## Qualité du Contenu

### HTML Préservé

Le système **préserve la structure HTML originale** du site Avidsen :

✅ **Conservé** :
- Structure HTML exacte du tutoriel
- Images à leurs positions originales
- Mise en page identique
- Étapes avec numérotation
- Descriptions complètes

❌ **Supprimé** :
- Menus de navigation
- Headers (en-têtes)
- Footers (pieds de page)
- Sidebars
- Scripts et styles

### URLs Absolues

Toutes les URLs relatives sont converties en URLs absolues :
- Images : `https://www.avidsen.com/...`
- Liens : `https://www.avidsen.com/...`

## Fichiers Générés

### Structure

```
tutorials_data/
└── all_tutorials.json    # Tous les tutoriels en JSON
```

### Format JSON

```json
[
  {
    "url": "https://www.avidsen.com/fr/assistance/tutoriel-sav/tuto/...",
    "title": "Programmation d'un clavier à codes",
    "category": "motorisation",
    "product": "Avidsen - 114255 - Clavier à code",
    "applicable_products": ["114255"],
    "html_content": "<main>...</main>",
    "steps": []
  }
]
```

## Modules Utilisés

### `src/scraper/` - Package de scraping modulaire

Le package scraper est maintenant organisé en modules spécialisés pour une meilleure maintenabilité :

#### `src/scraper/styles.py`
**Constantes de style partagées** :
- `SITE_HEADING_COLOR`, `SITE_ACCENT_COLOR`, `SITE_GREY_BG` - Couleurs du site
- `SITE_FONT_FAMILY`, `SITE_FONT_SIZE` - Typographie
- `AVIDSEN_BASE_URL` - URL de base du site
- `INLINE_ICON_MAX_SIZE` - Seuil pour distinguer images/icônes

#### `src/scraper/media_helpers.py`
**Traitement des médias** :
- `resolve_img_src(img)` - Résolution des URLs d'images (lazy loading)
- `is_inline_icon(img)` - Détection des icônes inline
- `collect_main_images(element)` - Collecte des images principales
- `extract_youtube_html(element)` - Extraction des vidéos YouTube
- `fix_lazy_images(soup)` - Pré-traitement des images lazy-loaded

#### `src/scraper/html_builder.py`
**Génération HTML** :
- `build_step_html()` - Construction des étapes avec layout image|texte
- `build_content_section_html()` - Génération des sections Elementor
- `style_content_table()` - Style des tableaux (bordures + alternance)
- `extract_section_text()` - Extraction du texte avec icônes préservées
- `get_unique_columns()` - Helper réutilisable pour colonnes Elementor

#### `src/scraper/tutorial_scraper.py`
**Logique de scraping principale** (424 lignes, -46% par rapport à avant) :
- `get_tutorial_categories()` - Découverte des catégories
- `get_product_tutorials(product_ref, categories)` - Tutoriels par produit
- `scrape_tutorial_content(url)` - Extraction complète du tutoriel

#### `src/scraper/tutorial_formatter.py`
**Nettoyage pour Zoho Desk** :
- `format_tutorials_section(tutorials)` - Formatage final pour publication
- `clean_tutorial_html(html_content)` - Nettoyage des éléments superflus

### `main.py` et `gui.py`

**Scripts principaux** qui orchestrent :
1. Découverte des tutoriels
2. Extraction du contenu
3. Sauvegarde JSON
4. Publication Zoho


## Dépannage

### Erreur Zoho

**Causes possibles** :
- Token expiré
- Catégorie ID incorrecte
- Permissions insuffisantes

**Solution** :
```bash
# Rafraîchir le token
python refresh_token.py

# Vérifier config.txt
ZOHO_TUTORIAL_CATEGORY_ID=603196000009391009
```

### HTML incomplet

**Causes possibles** :
- Sélecteur de contenu principal non trouvé
- Structure de page différente

**Solution** :
- Vérifier les logs pour voir quel sélecteur a été utilisé
- Le script utilise plusieurs fallbacks automatiquement

## Avantages de cette Approche

✅ **Exhaustivité** : Récupère TOUS les tutoriels du site
✅ **Qualité** : HTML original préservé
✅ **Flexibilité** : Mise à jour indépendante
✅ **Traçabilité** : Sauvegarde JSON réutilisable
✅ **Propreté** : Suppression automatique des éléments de navigation

## Résumé

**Commande principale** :
```bash
python scrape_tutorials.py
```

**Résultat** :
- Tutoriels extraits avec HTML propre
- Sauvegardés en JSON
- Publiés dans Zoho Desk catégorie "Tutoriels"
- Structure et images préservées
