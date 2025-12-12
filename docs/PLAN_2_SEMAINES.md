# Plan de Projet : Finalisation et Déploiement de l'Importateur Avidsen

**Dernière mise à jour : 11/12/2025**  
**Durée estimée : 2 semaines (10 jours ouvrés)**

## 1. Objectif Global

Développer une solution robuste et automatisée pour l'importation des notices Avidsen vers Zoho Desk, avec une gestion précise de la pagination , des images/schema des PDF dans les articles du Desk.

## 2. État Actuel

-   **✅ Fonctionnel** : Extraction du texte et des tableaux depuis les PDF.
-   **✅ Fonctionnel** : Authentification Zoho et chargement de la configuration et enregistrement des articles.
-   **⚠️ À améliorer** : Structure du code (monolithique dans `final.py`).
-   **❌ Non implémenté** : Gestion de la pagination dans les articles Zoho.
-   **❌ Non implémenté** : Extraction et gestion des images et schémas des PDF.

## 3. Planning Journalier Détaillé

### Semaine 1 : Développement et Tests

**Jour 1-2 : Refactoring du Code**
- [ ] 1.1 Découpage de `final.py` en modules :
  - `pdf_parser.py` : Extraction PDF et gestion de la pagination
  - `zoho_uploader.py` : Communication avec l'API Zoho
  - `main.py` : Point d'entrée principal
- [ ] 1.2 Mise en place du système de logging centralisé
- [ ] 1.3 Documentation technique initiale

**Jour 3-4 : Gestion des Images/schema et Pagination**
- [ ] 2.1 Implémentation de l'extraction d'images/schema PDF
- [ ] 2.2 Gestion des page dans les articles Desk
- [ ] 2.4 Tests d'intégration

**Jour 5 : Améliorations**
- [ ] 2.5 Optimisation des performances
- [ ] 2.6 Tests utilisateur
- [ ] 2.7 Documentation des spécifications

### Semaine 2 : Finalisation et Déploiement

**Jour 6-7 : Packaging**
- [ ] 3.1 Création de l'exécutable avec PyInstaller
- [ ] 3.2 Testing
- [ ] 3.3 Gestion des dépendances

**Jour 8-9 : Installation et Documentation**
- [ ] 3.4 Création de l'installateur Inno Setup
- [ ] 3.5 Documentation utilisateur complète
- [ ] 3.6 Guide d'installation

**Jour 10 : Livraison**
- [ ] 4.1 Tests finaux.
- [ ] 4.2 Préparation du package de livraison
- [ ] 4.3 Documentation finale


