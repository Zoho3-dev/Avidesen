# Tests et Utilitaires

Ce dossier contient les scripts de test et utilitaires pour le projet Avidsen.

## Fichiers

### `analyze_tuto.py`
Utilitaire pour vérifier si un tutoriel existe déjà dans Zoho KB.

**Usage :**
```bash
python -m tests.analyze_tuto "Titre de l'article"
```

**Exemple :**
```bash
python -m tests.analyze_tuto "Prédiagnostic CAB9SL24V"
```

### `test_single_tuto.py`
Script pour tester le scraping et la publication d'un seul tutoriel.

**Usage :**
```bash
# Scraping uniquement
python -m tests.test_single_tuto https://www.avidsen.com/fr/assistance/tutoriel-sav/tuto/prediagnostic-cab9sl24v

# Scraping + publication
python -m tests.test_single_tuto https://www.avidsen.com/fr/assistance/tutoriel-sav/tuto/prediagnostic-cab9sl24v --publish

# Scraping + publication avec catégorie
python -m tests.test_single_tuto https://www.avidsen.com/fr/assistance/tutoriel-sav/tuto/prediagnostic-cab9sl24v --publish motorisation
```

## Important

Tous les tests doivent être lancés depuis le dossier racine du projet avec la syntaxe `python -m tests.nom_du_fichier` pour assurer que les imports fonctionnent correctement.
