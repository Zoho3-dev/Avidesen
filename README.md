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

### Structure du projet
```
.
├── final.py           # Point d'entrée principal
├── zoho_api.py        # Gestion des appels API Zoho
├── zoho_auth.py       # Authentification OAuth 2.0
├── config.txt         # Configuration (à sécuriser)
├── requirements.txt   # Dépendances
└── notices/           # Stockage des PDF et images
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
   ```ini
   ZOHO_CLIENT_ID=votre_client_id
   ZOHO_CLIENT_SECRET=votre_client_secret
   GRANTED_CODE=votre_code_autorisation
   ZOHO_ORG_ID=votre_org_id
   ZOHO_CATEGORY_ID=votre_categorie_id
   ```

### Utilisation
```bash
# Traiter un PDF spécifique
python final.py --pdf chemin/vers/notice.pdf

# Traiter un dossier complet
python final.py --folder chemin/vers/dossier
```

## 📈 Améliorations prévues

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
