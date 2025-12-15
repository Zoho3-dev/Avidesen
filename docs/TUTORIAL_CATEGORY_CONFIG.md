# Configuration de la Catégorie Tutoriels

## Problème Résolu

Les tutoriels sont maintenant publiés dans une catégorie séparée "Tutoriels" dans Zoho Desk.

## Configuration

### 1. Ajouter la ligne dans `config.txt`

```
ZOHO_TUTORIAL_CATEGORY_ID=603196000009391009
```

### 2. Structure Complète de config.txt

```
# Identifiants API
ZOHO_CLIENT_ID=votre_client_id
ZOHO_CLIENT_SECRET=votre_client_secret
GRANTED_CODE=votre_granted_code

# Organisation
ZOHO_ORG_ID=votre_org_id

# Catégorie pour les PRODUITS (notices PDF)
ZOHO_PRODUCT_CATEGORY_ID=votre_category_id_produits

# Catégorie pour les TUTORIELS
ZOHO_TUTORIAL_CATEGORY_ID=603196000009391009

# Tokens (générés automatiquement)
ZOHO_ACCESS_TOKEN=...
ZOHO_REFRESH_TOKEN=...
```

## Résultat

- **Produits** (via `python main.py`) → Catégorie définie par `ZOHO_PRODUCT_CATEGORY_ID`
- **Tutoriels** (via `python scrape_tutorials.py`) → Catégorie "Tutoriels" (603196000009391009)

## Vérification

Après avoir lancé `python scrape_tutorials.py`, vérifiez ici :
```
https://desk.zoho.com/agent/demoaltais/avidsen/kb/page?categoryId=603196000009391009#Solutions/list/fr
```

Vous devriez voir tous les tutoriels dans cette catégorie !
