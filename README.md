# Avidsen Tutorials — Zoho Desk Publisher

Outil Python qui scrape les tutoriels du site **avidsen.com** et les publie automatiquement dans la base de connaissances **Zoho Desk EU**.

---

## Fonctionnalités

- **Découverte automatique** des tutoriels par catégorie et par produit
- **Extraction fidèle du contenu** : images, icônes inline, tableaux, listes, layouts 2 colonnes
- **Dédoublonnage** : les tutoriels et sections de contenu ne sont jamais publiés en double
- **Nettoyage HTML** : suppression du sommaire, navigation, scripts — conservation du contenu utile
- **Publication automatique** via l'API Zoho Desk EU (OAuth 2.0)
- **Rafraîchissement automatique du token** (aucune intervention manuelle nécessaire)
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
    │   └── settings.py           # Chargement de config.txt + auto-refresh token
    ├── scraper/
    │   ├── tutorial_scraper.py   # Scraping du site Avidsen
    │   └── tutorial_formatter.py # Nettoyage HTML pour Zoho Desk
    ├── utils/
    │   └── text_utils.py         # Génération de permalinks
    └── zoho/
        ├── auth.py               # Authentification OAuth 2.0
        └── api.py                # Création d'articles Zoho Desk EU
```

---

## Installation

### Prérequis

- **Python 3.10+**
- Un compte **Zoho Desk EU** avec accès API

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

---

## Configuration

### 1. Créer le fichier `config.txt`

```bash
copy config.example.txt config.txt
```

### 2. Remplir les valeurs

```ini
# Identifiants API Zoho (depuis https://api-console.zoho.eu/)
ZOHO_CLIENT_ID=votre_client_id
ZOHO_CLIENT_SECRET=votre_client_secret
GRANTED_CODE=votre_granted_code

# Organisation Zoho Desk (visible dans Zoho Desk > Paramètres > Organisation)
ZOHO_ORG_ID=votre_org_id

# ID de la catégorie KB où publier les tutoriels
ZOHO_TUTORIAL_CATEGORY_ID=votre_category_id
```

### 3. Obtenir les identifiants Zoho

| Paramètre | Où le trouver |
|---|---|
| `ZOHO_CLIENT_ID` / `ZOHO_CLIENT_SECRET` | [Zoho API Console EU](https://api-console.zoho.eu/) → Self Client |
| `GRANTED_CODE` | Zoho API Console EU → Generate Code (scope : `Desk.articles.ALL`) |
| `ZOHO_ORG_ID` | Zoho Desk EU → Paramètres → Organisation → Identificateur |
| `ZOHO_TUTORIAL_CATEGORY_ID` | Zoho Desk EU → Base de connaissances → Catégorie → ID dans l'URL |

> **Note :** Le `GRANTED_CODE` est à usage unique. Au premier lancement, il est échangé contre un `ZOHO_REFRESH_TOKEN` sauvegardé automatiquement. Les lancements suivants utilisent ce refresh token.

Pour plus de détails : [docs/REFRESH_TOKEN_GUIDE.md](docs/REFRESH_TOKEN_GUIDE.md)

---

## Utilisation

### Option 1 : Ligne de commande

```bash
python main.py
```

Le pipeline s'exécute automatiquement :
1. **Découverte** des tutoriels sur avidsen.com
2. **Extraction** du contenu HTML (dédoublonné)
3. **Sauvegarde** locale dans `tutorials_data/all_tutorials.json`
4. **Publication** dans Zoho Desk EU (token rafraîchi automatiquement)

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
avidsen.com                    Zoho Desk EU
    │                               ▲
    ▼                               │
┌──────────────┐   ┌──────────┐   ┌─────────────┐
│  Découverte  │──▶│Extraction│──▶│ Publication  │
│  catégories  │   │  contenu │   │  articles    │
│  + produits  │   │  HTML    │   │  (auto-token)│
└──────────────┘   └────┬─────┘   └─────────────┘
                        │
                        ▼
                 tutorials_data/
                 all_tutorials.json
```

Pour le détail technique du scraping : [docs/TUTORIAL_SCRAPING_GUIDE.md](docs/TUTORIAL_SCRAPING_GUIDE.md)

---

## Notes techniques

- Le token est **rafraîchi automatiquement** avant chaque appel API et en cas d'erreur 401
- Les tutoriels sont **dédoublonnés** par URL lors de la découverte et par contenu lors de l'extraction
- Les tutoriels sont **sauvegardés localement** en JSON avant publication
- Le fichier `config.txt` n'est **jamais versionné** (contient des secrets)

---

## Dépannage

| Problème | Solution |
|---|---|
| `ZOHO_ACCESS_TOKEN manquant` | Lancez `python refresh_token.py` |
| Erreur 401 (token invalide) | Géré automatiquement ; sinon `python refresh_token.py` |
| Erreur 422 (orgId invalide) | Vérifiez `ZOHO_ORG_ID` dans `config.txt` |
| Erreur 422 (categoryId invalide) | Vérifiez `ZOHO_TUTORIAL_CATEGORY_ID` dans `config.txt` |
| `config.txt introuvable` | Copiez `config.example.txt` vers `config.txt` |
| `GRANTED_CODE invalide` | Générez un nouveau code sur [api-console.zoho.eu](https://api-console.zoho.eu/) |
