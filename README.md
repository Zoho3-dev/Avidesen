# Avidsen Tutorials — Zoho Desk Publisher

Outil Python qui scrape les tutoriels du site **avidsen.com** et les publie automatiquement dans la base de connaissances **Zoho Desk**, chaque tutoriel étant classé dans sa catégorie correspondante.

---

## Fonctionnalités

- **Découverte automatique** des tutoriels par catégorie (motorisation, visiophone, sécurité, solaire, domotique) et par produit
- **Sous-catégories automatiques** : création de sous-catégories Zoho pour chaque produit (ex: "Avidsen - 123281 - IPC281-Ex")
- **Extraction fidèle du contenu** : images produit, icônes inline, tableaux, listes, layouts 2 colonnes (image | texte)
- **Scraping haute fidélité** : couleurs, polices (Poppins), fonds gris, tailles de police identiques au site original
- **Dédoublonnage intelligent** : par (url, produit) pour gérer les tutoriels partagés entre plusieurs produits
- **Cache de contenu** : scraping optimisé par URL pour éviter les requêtes redondantes
- **Publication par catégorie** : chaque tutoriel est publié dans sa sous-catégorie produit Zoho correspondante
- **Nettoyage HTML** : suppression du sommaire, navigation, scripts — conservation du contenu utile
- **Publication automatique** via l'API Zoho Desk (OAuth 2.0)
- **Rafraîchissement automatique du token** avec fallback sur le granted_code
- **Interface graphique** (tkinter) pour lancer le traitement sans ligne de commande
- **Exécutable Windows** (.exe) pour une utilisation sans installation Python

---

## Structure du projet

```
Avidesen/
├── main.py                       # Pipeline principal (CLI)
├── gui.py                        # Interface graphique (tkinter)
├── refresh_token.py              # Rafraîchissement manuel du token
├── config.example.txt            # Modèle de configuration
├── requirements.txt              # Dépendances Python
├── docs/
│   ├── REFRESH_TOKEN_GUIDE.md    # Guide d'authentification OAuth
│   ├── TUTORIAL_CATEGORY_CONFIG.md # Configuration des catégories
│   ├── TUTORIAL_SCRAPING_GUIDE.md  # Guide technique du scraping
│   ├── CATEGORY_STRUCTURE.md     # Structure des catégories et sous-catégories
│   └── INSTALLATION.md           # Guide d'installation complet
└── src/
    ├── config/
    │   └── settings.py           # Chargement config + mapping catégories + auto-refresh token
    ├── scraper/
    │   ├── styles.py            # Constantes de style (couleurs, polices, URLs)
    │   ├── media_helpers.py     # Traitement images/vidéos (lazy loading, YouTube)
    │   ├── html_builder.py      # Génération HTML des sections (layouts, tableaux)
    │   ├── tutorial_scraper.py  # Scraping du site Avidsen (Elementor)
    │   └── tutorial_formatter.py # Nettoyage HTML pour Zoho Desk
    ├── utils/
    │   └── text_utils.py         # Génération de permalinks Zoho-compatible
    └── zoho/
        ├── auth.py               # Authentification OAuth 2.0 (refresh auto + fallback)
        └── api.py                # Création d'articles Zoho Desk
```

---

## Installation rapide

### Prérequis

- **Python 3.10+**
- Un compte **Zoho Desk** avec accès API

### Étapes

```bash
# 1. Cloner le dépôt
git clone https://github.com/Zoho3-dev/Avidesen.git
cd Avidesen

# 2. Créer un environnement virtuel
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# 3. Installer les dépendances
pip install -r requirements.txt
```

> Pour une installation détaillée sur un serveur Windows, voir [INSTALLATION.md](INSTALLATION.md).

---

## Configuration

### 1. Créer le fichier `config.txt`

```bash
copy config.example.txt config.txt
```

### 2. Remplir les valeurs

```ini
# Identifiants API Zoho (depuis https://api-console.zoho.com/)
ZOHO_CLIENT_ID=votre_client_id
ZOHO_CLIENT_SECRET=votre_client_secret
GRANTED_CODE=votre_granted_code

# Organisation Zoho Desk
ZOHO_ORG_ID=votre_org_id

# Catégories Zoho Desk (une par catégorie du site)
ZOHO_TUTORIAL_CATEGORY_PORTAIL_ID=id_categorie_portail
ZOHO_TUTORIAL_CATEGORY_VISIOPHONE_ID=id_categorie_visiophone
ZOHO_TUTORIAL_CATEGORY_CAMERA_ID=id_categorie_camera
ZOHO_TUTORIAL_CATEGORY_SOLAIRE_ID=id_categorie_solaire
ZOHO_TUTORIAL_CATEGORY_DOMOTIQUE_ID=id_categorie_domotique
```

### 3. Mapping des catégories

| Catégorie site Avidsen | Clé config Zoho |
|---|---|
| `motorisation` | `ZOHO_TUTORIAL_CATEGORY_PORTAIL_ID` |
| `visiophone` | `ZOHO_TUTORIAL_CATEGORY_VISIOPHONE_ID` |
| `securite` | `ZOHO_TUTORIAL_CATEGORY_CAMERA_ID` |
| `solaire` | `ZOHO_TUTORIAL_CATEGORY_SOLAIRE_ID` |
| `domotique` | `ZOHO_TUTORIAL_CATEGORY_DOMOTIQUE_ID` |

### 4. Obtenir les identifiants Zoho

| Paramètre | Où le trouver |
|---|---|
| `ZOHO_CLIENT_ID` / `ZOHO_CLIENT_SECRET` | [Zoho API Console](https://api-console.zoho.com/) → Self Client |
| `GRANTED_CODE` | Zoho API Console → Generate Code (scopes : `ZohoCRM.modules.ALL,ZohoCRM.settings.ALL,ZohoCRM.org.ALL,Desk.basic.READ,Desk.basic.CREATE,Desk.settings.ALL,Desk.articles.READ,Desk.articles.CREATE,Desk.articles.UPDATE`) |
| `ZOHO_ORG_ID` | Zoho Desk → Paramètres → Organisation → Identificateur |
| Catégories | Zoho Desk → Base de connaissances → Catégorie → ID dans l'URL |

> **Note :** Le `GRANTED_CODE` est à usage unique. Au premier lancement, il est échangé contre un `ZOHO_REFRESH_TOKEN` sauvegardé automatiquement. Les lancements suivants utilisent ce refresh token.

Pour plus de détails : [docs/REFRESH_TOKEN_GUIDE.md](docs/REFRESH_TOKEN_GUIDE.md)

---

## Utilisation

### Option 1 : Ligne de commande

```bash
python main.py
```

Le pipeline s'exécute automatiquement :
1. **Découverte** des tutoriels sur avidsen.com (5 catégories + produits)
2. **Déduplication** par (url, produit) pour gérer les tutoriels partagés
3. **Extraction** du contenu HTML fidèle au site (images, couleurs, polices, sections matériel/pièces)
4. **Sauvegarde** locale dans `tutorials_data/all_tutorials.json`
5. **Publication** dans Zoho Desk avec création automatique des sous-catégories par produit

### Option 2 : Interface graphique

```bash
python gui.py
```

### Option 3 : Exécutable Windows (.exe)

```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name "Avidsen-Tutoriels" gui.py
```

> **Important :** Placez `config.txt` dans le même dossier que l'exécutable.

---

## Pipeline de traitement

```
avidsen.com                      Zoho Desk
    │                                 ▲
    ▼                                 │
┌──────────────┐   ┌──────────┐   ┌──────────────────┐
│  Découverte  │──▶│Dédupli-   │──▶│   Publication     │
│  5 catégories│   │cation +   │   │   avec sous-cat. │
│  + produits  │   │Extraction│   │   par produit    │
│  (url,prod)  │   │  contenu │   │   (auto-token)    │
└──────────────┘   └────┬─────┘   └──────────────────┘
                        │          motorisation → Portail
                        ▼          → "Avidsen - 123281"
                 tutorials_data/   visiophone → Visiophone
                 all_tutorials.json   → "Philips - 531001"
                                   securite → Caméra
                                   → "Avidsen - IPC281"
                                   solaire → Solaire
                                   → "Avidsen - Soria 400W"
                                   domotique → Domotique
```

---

## Notes techniques

- Le token est **rafraîchi automatiquement** avant chaque appel API et en cas d'erreur 401, avec fallback sur le `GRANTED_CODE` (domaine EU : `accounts.zoho.eu`, `desk.zoho.eu`)
- **Sous-catégories automatiques** : création de sous-catégories Zoho pour chaque produit avec noms normalisés
- **Déduplication par (url, produit)** : un même tutoriel partagé par plusieurs produits crée une sous-catégorie pour chacun
- **Cache de contenu par URL** : optimisation du scraping pour éviter les requêtes redondantes
- Le scraping utilise les **couleurs réelles du site** (`#334956` pour les titres, `#e5e5e5` pour les fonds gris, police Poppins 15px)
- Les permalinks incluent **l'ID de sous-catégorie** pour garantir l'unicité quand le même tutoriel est publié dans plusieurs sous-catégories
- Les tutoriels sont **sauvegardés localement** en JSON avant publication
- Le fichier `config.txt` n'est **jamais versionné** (contient des secrets)

---

## Dépannage

| Problème | Solution |
|---|---|
| `ZOHO_ACCESS_TOKEN manquant` | Lancez `python refresh_token.py` |
| Erreur 401 (token invalide) | Géré automatiquement ; sinon `python refresh_token.py` |
| Erreur 422 (permalink) | Géré automatiquement avec un permalink unique par sous-catégorie |
| Erreur 422 (orgId invalide) | Vérifiez `ZOHO_ORG_ID` dans `config.txt` |
| Erreur 422 (categoryId invalide) | Vérifiez les IDs de catégorie dans `config.txt` |
| Erreur 422 (sous-catégorie dupliquée) | Normalisation des noms automatique ; les sous-catégories existantes sont réutilisées |
| `config.txt introuvable` | Copiez `config.example.txt` vers `config.txt` |
| `GRANTED_CODE invalide` | Générez un nouveau code sur [api-console.zoho.eu](https://api-console.zoho.eu/) |
| Tutoriel publié sans contenu | Relancez — le scraping détecte maintenant les sections non standard |
| Pièces détachées sans lien | Le lien est inclus seulement si présent sur le site source |
