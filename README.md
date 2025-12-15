# 📚 Importateur de notices Avidsen pour Zoho Desk

## 🎯 Objectif
Outil Python automatisé pour extraire les manuels produits d'Avidsen et les publier dans Zoho Desk, en préservant la mise en page et le contenu original.

## ✨ Fonctionnalités principales

### 🔍 Récupération du contenu
- Parcours automatisé du catalogue Avidsen
- Téléchargement des manuels PDF et images associées
- Extraction précise du texte et des tableaux

### 🛠 Traitement intelligent
- Nettoyage automatique des en-têtes/pieds de page
- Reconstruction des tableaux en HTML
- Détection des titres de section
- Formatage pour une lecture optimale

### 🔄 Intégration Zoho Desk
- Authentification OAuth 2.0 sécurisée
- Création automatisée d'articles
- Génération de liens internes
- Gestion des mises à jour

## 🏗 Architecture

### Structure du projet (Nouvelle architecture modulaire)
```
.
├── src/
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py        # Configuration centralisée
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── file_utils.py      # Téléchargement de fichiers
│   │   └── text_utils.py      # Manipulation de texte
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── web_scraper.py     # Scraping et pagination
│   │   └── product_parser.py  # Traitement des pages produits
│   ├── pdf/
│   │   ├── __init__.py
│   │   ├── pdf_parser.py      # Extraction de structure PDF
│   │   └── table_detector.py  # Détection de tableaux
│   └── zoho/
│       ├── __init__.py
│       ├── auth.py            # Authentification OAuth 2.0
│       └── api.py             # Gestion des appels API Zoho
├── main.py                    # Point d'entrée principal
├── refresh_token.py           # Script de rafraîchissement du token
├── config.txt                 # Configuration (à sécuriser)
├── requirements.txt           # Dépendances
├── REFRESH_TOKEN_GUIDE.md     # Guide de rafraîchissement du token
└── notices/                   # Stockage des PDF et images
```

### Flux de travail
1. **Extraction** : Récupération des PDF depuis le PIM Avidsen
2. **Traitement** : Conversion en contenu structuré
3. **Publication** : Intégration dans Zoho Desk

## 🚀 Installation & Utilisation

### Prérequis
- Python 3.6+
- Compte développeur Zoho
- Accès au PIM Avidsen

### Configuration
1. Cloner le dépôt
   ```bash
   git clone <url-du-depot>
   cd <dossier-du-projet>
   ```

2. Créer un environnement virtuel
   ```bash
   python -m venv venv
   # Sur Windows :
   venv\Scripts\activate
   # Sur macOS/Linux :
   source venv/bin/activate
   ```

3. Installer les dépendances
   ```bash
   pip install -r requirements.txt
   ```

4. Configurer `config.txt`

   Le fichier `config.txt` centralise toutes vos informations sensibles. Voici comment obtenir chaque valeur :

   #### a. Créer un "Self Client" Zoho

   1.  **Connectez-vous à la console développeur Zoho** : [https://api-console.zoho.com/](https://api-console.zoho.com/)
   2.  Cliquez sur **"Get Started"** ou **"Add Client"**.
   3.  Choisissez **"Self Client"** comme type de client. C'est le type le plus simple pour les scripts internes.

   #### b. Générer le Grant Token (Code d'autorisation)

   1.  Une fois le client créé, allez dans l'onglet **"Generate Code"**.
   2.  Entrez les **scopes** (permissions) suivants, séparés par une virgule. Ces permissions sont nécessaires pour que le script puisse lire et créer des articles dans la base de connaissances :
       ```
       Desk.articles.CREATE,Desk.articles.READ,Desk.articles.WRITE,Desk.settings.READ
       ```
   3.  Choisissez une **durée de validité** (ex: 10 minutes). Ce code est à usage unique.
   4.  Cliquez sur **"Create"** puis copiez le `code` généré. C'est votre **`GRANTED_CODE`**.

   #### c. Obtenir le Client ID et le Client Secret

   1.  Allez dans l'onglet **"Client Secret"**.
   2.  Vous y trouverez le **`Client ID`** et le **`Client Secret`**. Copiez-les.

   #### d. Trouver l'ID de l'Organisation et de la Catégorie

   1.  **`ZOHO_ORG_ID`** : Connectez-vous à Zoho Desk. Allez dans **Setup (⚙️) > APIs**. Votre `organizationId` est affiché ici.
   2.  **`ZOHO_PRODUCT_CATEGORY_ID`** : Allez dans votre base de connaissances Zoho Desk, naviguez jusqu'à la catégorie où les articles doivent être publiés, et regardez l'URL. L'ID de la catégorie s'y trouve (ex: `.../category/603196000008134001`).

   #### e. Remplir le fichier

   Copiez `config.example.txt` vers `config.txt` et remplissez-le avec les valeurs que vous venez de récupérer :

   ```ini
   ZOHO_CLIENT_ID=le_client_id_obtenu
   ZOHO_CLIENT_SECRET=le_client_secret_obtenu
   GRANTED_CODE=le_code_généré_à_l_étape_b
   ZOHO_ORG_ID=votre_id_d_organisation
   ZOHO_PRODUCT_CATEGORY_ID=votre_id_de_catégorie
   # Laissez les autres valeurs telles quelles pour le moment
   ```

   > **Important** : Le `GRANTED_CODE` est à usage unique. La première fois que vous lancerez `zoho_auth.py` ou `refresh_access_token.py`, il sera échangé contre un `refresh_token` qui, lui, sera stocké et réutilisé durablement.

### Utilisation

#### Lancer le scraping complet
```bash
# Nouvelle méthode (recommandée)
python main.py

# Ancienne méthode (toujours fonctionnelle)
python final.py
```

#### Rafraîchir le token Zoho
```bash
# Rafraîchir manuellement le token d'accès
python refresh_token.py
```

> **Note** : Le token est automatiquement rafraîchi lors de l'exécution de `main.py`, mais vous pouvez utiliser `refresh_token.py` pour le faire manuellement.

Pour plus de détails sur la gestion des tokens, consultez [REFRESH_TOKEN_GUIDE.md](REFRESH_TOKEN_GUIDE.md).

## 🎨 Architecture Modulaire

### Avantages de la nouvelle structure

✅ **Séparation des préoccupations** : Chaque module a une responsabilité claire
✅ **Maintenabilité** : Plus facile de trouver et modifier du code spécifique
✅ **Réutilisabilité** : Les modules peuvent être importés et réutilisés
✅ **Testabilité** : Chaque module peut être testé indépendamment
✅ **Lisibilité** : Structure claire et intuitive
✅ **Évolutivité** : Facile d'ajouter de nouvelles fonctionnalités

### Modules principaux

- **config** : Gestion centralisée de la configuration
- **utils** : Fonctions utilitaires (fichiers, texte)
- **scraper** : Scraping du site web et parsing des produits
- **pdf** : Extraction et traitement des PDFs
- **zoho** : Authentification et API Zoho Desk

## 📈 Améliorations prévues

### ✅ Complété
- [x] Refactorisation du code en architecture modulaire
- [x] Script de rafraîchissement de token
- [x] Documentation complète

### Priorité haute 🚨
- [ ] Extraction des images PDF
- [ ] Conservation de la pagination
- [ ] Gestion des schémas techniques

### Priorité moyenne 🔄
- [ ] Refactorisation du code
- [ ] Tests automatisés
- [ ] Meilleure gestion des erreurs


## 📝 Notes techniques
- Les notices restent dans le PIM Avidsen (source de vérité)
- Zoho Desk sert uniquement pour le robot de réponse
- Solution 100% locale, sans serveur dédié
