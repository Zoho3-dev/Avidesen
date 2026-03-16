# Avidsen Tutorials — Zoho Desk Publisher

## Objectif

Outil Python qui scrape les tutoriels du site **avidsen.com** et les publie en tant qu'articles dans **Zoho Desk**.

## Fonctionnalites

- **Decouverte automatique** des tutoriels par categorie et par produit
- **Extraction du contenu HTML** avec nettoyage (navigation, lazy-loading images, liens relatifs)
- **Formatage** adapte a Zoho Desk (HTML inline)
- **Publication** via l'API Zoho Desk (OAuth 2.0)
- **Sauvegarde locale** en JSON

## Structure du projet

```
.
├── main.py                        # Point d'entree principal
├── refresh_token.py               # Rafraichissement manuel du token Zoho
├── config.example.txt             # Modele de configuration
├── requirements.txt               # Dependances Python
├── tutorials_data/                # Tutoriels sauvegardes en JSON
├── docs/                          # Documentation complementaire
└── src/
    ├── config/
    │   └── settings.py            # Configuration et constantes
    ├── scraper/
    │   ├── tutorial_scraper.py    # Scraping des tutoriels (categories, contenu)
    │   └── tutorial_formatter.py  # Mise en forme HTML pour Zoho
    ├── utils/
    │   └── text_utils.py          # Utilitaires texte (permalink, etc.)
    └── zoho/
        ├── auth.py                # Authentification OAuth 2.0
        └── api.py                 # Creation d'articles Zoho Desk
```

## Flux de travail

1. **Decouverte** — parcours des categories et produits pour lister les tutoriels
2. **Extraction** — recuperation du contenu HTML de chaque tutoriel
3. **Sauvegarde** — export en `tutorials_data/all_tutorials.json`
4. **Publication** — creation des articles dans Zoho Desk (optionnel, interactif)

## Installation

```bash
git clone <url-du-depot>
cd Avidesen
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
```

## Configuration

1. Copiez `config.example.txt` vers `config.txt`.
2. Remplissez les valeurs :

```ini
ZOHO_CLIENT_ID=votre_client_id
ZOHO_CLIENT_SECRET=votre_client_secret
GRANTED_CODE=votre_granted_code
ZOHO_ORG_ID=votre_org_id
ZOHO_TUTORIAL_CATEGORY_ID=votre_category_id
```

> Le `GRANTED_CODE` est a usage unique. Au premier lancement, il est echange contre un `refresh_token` stocke dans `config.txt`.

Pour obtenir ces valeurs, consultez [docs/REFRESH_TOKEN_GUIDE.md](docs/REFRESH_TOKEN_GUIDE.md).

## Utilisation

```bash
# Lancer le pipeline complet (decouverte + extraction + publication)
python main.py

# Rafraichir manuellement le token Zoho
python refresh_token.py
```

## Notes techniques

- Zoho Desk sert de base de connaissances pour le robot de reponse
- Solution 100% locale, sans serveur dedie
- Les tutoriels sont sauvegardes localement avant publication
