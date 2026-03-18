# Installation sur un serveur Windows

Guide complet pour installer et exécuter l'application **Avidsen Tutorials → Zoho Desk** sur un serveur Windows.

---

## Prérequis

- **Windows Server 2016+** ou **Windows 10/11**
- Accès administrateur sur le serveur
- Connexion Internet (pour accéder à avidsen.com et à l'API Zoho)

---

## Étape 1 : Installer Python

### 1.1 Télécharger Python

Rendez-vous sur [python.org/downloads](https://www.python.org/downloads/) et téléchargez **Python 3.10+** (version Windows installer 64-bit).

### 1.2 Installer Python

Lors de l'installation :
- **Cochez** "Add Python to PATH" (très important !)
- Cliquez sur "Install Now"

### 1.3 Vérifier l'installation

Ouvrez **PowerShell** et tapez :

```powershell
python --version
pip --version
```

Vous devez voir quelque chose comme :
```
Python 3.12.x
pip 24.x.x
```

> Si `python` n'est pas reconnu, ajoutez manuellement le chemin Python au PATH système :
> `Panneau de configuration → Système → Variables d'environnement → Path → Ajouter C:\Python312\ et C:\Python312\Scripts\`

---

## Étape 2 : Récupérer le projet

### Option A : Avec Git

```powershell
# Installer Git si nécessaire : https://git-scm.com/download/win
git clone https://github.com/Zoho3-dev/Avidesen.git
cd Avidesen
```

### Option B : Sans Git

1. Téléchargez le projet en ZIP depuis GitHub
2. Décompressez dans un dossier, par exemple `C:\Avidesen`
3. Ouvrez PowerShell et naviguez :

```powershell
cd C:\Avidesen
```

---

## Étape 3 : Créer un environnement virtuel

```powershell
python -m venv venv
venv\Scripts\activate
```

> Vous devez voir `(venv)` au début de la ligne de commande. Si l'activation échoue avec une erreur de politique d'exécution, exécutez d'abord :
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

---

## Étape 4 : Installer les dépendances

```powershell
pip install -r requirements.txt
```

Dépendances installées :
- `requests` — requêtes HTTP
- `beautifulsoup4` — parsing HTML

---

## Étape 5 : Configurer l'application

### 5.1 Créer le fichier de configuration

```powershell
copy config.example.txt config.txt
```

### 5.2 Remplir les valeurs

Ouvrez `config.txt` avec un éditeur de texte (Notepad, VS Code, etc.) et remplissez :

```ini
# Identifiants API Zoho
ZOHO_CLIENT_ID=votre_client_id
ZOHO_CLIENT_SECRET=votre_client_secret
GRANTED_CODE=votre_granted_code

# Organisation
ZOHO_ORG_ID=votre_org_id

# Catégories Zoho (une par catégorie du site Avidsen)
ZOHO_TUTORIAL_CATEGORY_PORTAIL_ID=id_portail
ZOHO_TUTORIAL_CATEGORY_VISIOPHONE_ID=id_visiophone
ZOHO_TUTORIAL_CATEGORY_CAMERA_ID=id_camera
ZOHO_TUTORIAL_CATEGORY_SOLAIRE_ID=id_solaire
ZOHO_TUTORIAL_CATEGORY_DOMOTIQUE_ID=id_domotique
```

### 5.3 Obtenir les identifiants Zoho

1. **ZOHO_CLIENT_ID / ZOHO_CLIENT_SECRET** :
   - Allez sur [api-console.zoho.eu](https://api-console.zoho.eu/)
   - Créez un "Self Client"
   - Copiez le Client ID et Client Secret

2. **GRANTED_CODE** :
   - Dans la console API Zoho, cliquez "Generate Code"
   - **Scope** : `ZohoCRM.modules.ALL,ZohoCRM.settings.ALL,ZohoCRM.org.ALL,Desk.basic.READ,Desk.basic.CREATE,Desk.settings.ALL,Desk.articles.READ,Desk.articles.CREATE,Desk.articles.UPDATE`
   - Le code est **à usage unique** — il sera automatiquement échangé contre un refresh token

3. **ZOHO_ORG_ID** :
   - Zoho Desk → Paramètres → Organisation → Identificateur

4. **Catégories** :
   - Zoho Desk → Base de connaissances → Cliquez sur une catégorie → L'ID est dans l'URL

---

## Étape 6 : Premier lancement

```powershell
# Assurez-vous que l'environnement virtuel est activé
venv\Scripts\activate

# Lancer le pipeline
python main.py
```

Au premier lancement :
- Le `GRANTED_CODE` est échangé contre un `ACCESS_TOKEN` et un `REFRESH_TOKEN`
- Les tokens sont sauvegardés automatiquement dans `config.txt`
- Les lancements suivants utilisent le `REFRESH_TOKEN` (pas besoin de regénérer le code)

### Vérification

Le pipeline affiche :
```
============================================================
DECOUVERTE DES TUTORIELS
============================================================
[INFO] 5 categorie(s) a explorer
[CATEGORY] motorisation
  [INFO] 12 produit(s) trouve(s)
    [OK] 3 tutoriel(s) pour ...
...
[SUMMARY] 92 tutoriel(s) unique(s) decouvert(s)
...
[1/92] Programmation d'un clavier... [motorisation]
[OK] Article cree : Programmation d'un clavier...
```

---

## Étape 7 : Exécution automatique (Tâche planifiée)

Pour lancer le script automatiquement (par exemple chaque nuit) :

### 7.1 Créer un script batch

Créez un fichier `run_avidsen.bat` dans le dossier du projet :

```batch
@echo off
cd /d C:\Avidesen
call venv\Scripts\activate
python main.py >> logs\execution_%date:~-4%%date:~3,2%%date:~0,2%.log 2>&1
```

> Adaptez `C:\Avidesen` au chemin réel du projet.

### 7.2 Créer le dossier de logs

```powershell
mkdir logs
```

### 7.3 Créer la tâche planifiée

```powershell
# Exécution quotidienne à 2h du matin
schtasks /create /tn "Avidsen-Tutorials" /tr "C:\Avidesen\run_avidsen.bat" /sc daily /st 02:00 /ru SYSTEM
```

Ou via l'interface graphique :
1. Ouvrez le **Planificateur de tâches** (`taskschd.msc`)
2. Action → Créer une tâche
3. Nom : `Avidsen-Tutorials`
4. Déclencheur : Quotidien, 02:00
5. Action : Démarrer un programme → `C:\Avidesen\run_avidsen.bat`
6. Cochez "Exécuter même si l'utilisateur n'est pas connecté"

---

## Étape 8 : Interface graphique (optionnel)

Si le serveur dispose d'un bureau graphique :

```powershell
python gui.py
```

### Créer un exécutable .exe

```powershell
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name "Avidsen-Tutoriels" gui.py
```

L'exécutable est généré dans le dossier `dist/`. Placez `config.txt` dans le même dossier que l'exécutable.

---

## Dépannage

### Le script ne se lance pas

| Erreur | Solution |
|---|---|
| `python n'est pas reconnu` | Ajoutez Python au PATH système |
| `Impossible d'activer le venv` | Exécutez `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `ModuleNotFoundError: requests` | Activez le venv puis `pip install -r requirements.txt` |
| `config.txt introuvable` | Copiez `config.example.txt` vers `config.txt` |

### Erreurs Zoho API

| Erreur | Solution |
|---|---|
| Erreur 401 (token invalide) | Géré automatiquement. Si persistant : `python refresh_token.py` |
| Erreur 422 (permalink) | Géré automatiquement avec fallback |
| Erreur 422 (orgId/categoryId) | Vérifiez les IDs dans `config.txt` |
| `GRANTED_CODE invalide` | Générez un nouveau code sur [api-console.zoho.eu](https://api-console.zoho.eu/) |

### Logs

- Les logs d'exécution sont affichés dans la console
- Si vous utilisez la tâche planifiée, les logs sont dans `logs/execution_YYYYMMDD.log`

---

## Mise à jour du projet

```powershell
cd C:\Avidesen
git pull origin main
venv\Scripts\activate
pip install -r requirements.txt
```

---

## Résumé des fichiers importants

| Fichier | Rôle |
|---|---|
| `main.py` | Pipeline principal (CLI) |
| `gui.py` | Interface graphique |
| `config.txt` | Configuration (secrets, IDs) — **ne jamais partager** |
| `config.example.txt` | Modèle de configuration |
| `refresh_token.py` | Rafraîchissement manuel du token |
| `requirements.txt` | Dépendances Python |
| `tutorials_data/` | Tutoriels sauvegardés en JSON |
| `logs/` | Logs d'exécution (si tâche planifiée) |
