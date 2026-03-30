# Avidsen Tutorials — Zoho Desk Publisher

Outil Python qui scrape les tutoriels du site **avidsen.com** et les publie automatiquement dans la base de connaissances **Zoho Desk**, chaque tutoriel étant classé dans sa catégorie correspondante.

---

## Fonctionnalités

- **Découverte automatique** des tutoriels par catégorie (motorisation, visiophone, sécurité, solaire, domotique) et par produit
- **Extraction fidèle du contenu** : images produit, icônes inline, tableaux, listes, layouts 2 colonnes (image | texte)
- **Scraping haute fidélité** : couleurs, polices (Poppins), fonds gris, tailles de police identiques au site original
- **Publication par catégorie** : chaque tutoriel est publié dans sa catégorie Zoho correspondante (Portail, Visiophone, Caméra, Solaire, Domotique)
- **Dédoublonnage** : les tutoriels ne sont jamais publiés en double
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
│   └── TUTORIAL_SCRAPING_GUIDE.md  # Guide technique du scraping
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
1. **Découverte** des tutoriels sur avidsen.com (5 catégories)
2. **Extraction** du contenu HTML fidèle au site (images, couleurs, polices)
3. **Sauvegarde** locale dans `tutorials_data/all_tutorials.json`
4. **Publication** dans Zoho Desk par catégorie (token rafraîchi automatiquement)

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
│  Découverte  │──▶│Extraction│──▶│   Publication     │
│  5 catégories│   │  contenu │   │   par catégorie   │
│  + produits  │   │  HTML    │   │   (auto-token)    │
└──────────────┘   └────┬─────┘   └──────────────────┘
                        │          motorisation → Portail
                        ▼          visiophone → Visiophone
                 tutorials_data/   securite → Caméra
                 all_tutorials.json solaire → Solaire
                                   domotique → Domotique
```

---

## Notes techniques

- Le token est **rafraîchi automatiquement** avant chaque appel API et en cas d'erreur 401, avec fallback sur le `GRANTED_CODE` (domaine COM : `accounts.zoho.com`, `desk.zoho.com`)
- Le scraping utilise les **couleurs réelles du site** (`#334956` pour les titres, `#e5e5e5` pour les fonds gris, police Poppins 15px)
- Les images produit sont incluses **à côté du texte** dans un layout table 2 colonnes
- Les permalinks sont **générés automatiquement** avec retry sur un permalink de fallback en cas d'erreur 422
- Les tutoriels sont **dédoublonnés** par URL lors de la découverte
- Les tutoriels sont **sauvegardés localement** en JSON avant publication
- Le fichier `config.txt` n'est **jamais versionné** (contient des secrets)

---

## Dépannage

| Problème | Solution |
|---|---|
| `ZOHO_ACCESS_TOKEN manquant` | Lancez `python refresh_token.py` |
| Erreur 401 (token invalide) | Géré automatiquement ; sinon `python refresh_token.py` |
| Erreur 422 (permalink) | Géré automatiquement avec un permalink de fallback |
| Erreur 422 (orgId invalide) | Vérifiez `ZOHO_ORG_ID` dans `config.txt` |
| Erreur 422 (categoryId invalide) | Vérifiez les IDs de catégorie dans `config.txt` |
| `config.txt introuvable` | Copiez `config.example.txt` vers `config.txt` |
| `GRANTED_CODE invalide` | Générez un nouveau code sur [api-console.zoho.com](https://api-console.zoho.com/) |
| Tutoriel publié sans contenu | Relancez — le scraping détecte maintenant les sections non standard |
