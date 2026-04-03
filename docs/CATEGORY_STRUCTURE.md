# Structure des Catégories et Sous-Catégories

Documentation détaillée de la structure des catégories Zoho Desk créées automatiquement par l'application.

---

## Vue d'ensemble

L'application crée une structure hiérarchique dans Zoho Desk :
- **5 catégories principales** (une par catégorie du site Avidsen)
- **Sous-catégories automatiques** pour chaque produit
- **Articles de tutoriels** publiés dans les sous-catégories correspondantes

---

## Mapping Catégories Site → Zoho

| Catégorie site Avidsen | Clé configuration | Catégorie Zoho Desk |
|---|---|---|
| `motorisation` | `ZOHO_TUTORIAL_CATEGORY_PORTAIL_ID` | Portail |
| `visiophone` | `ZOHO_TUTORIAL_CATEGORY_VISIOPHONE_ID` | Visiophone |
| `securite` | `ZOHO_TUTORIAL_CATEGORY_CAMERA_ID` | Caméra |
| `solaire` | `ZOHO_TUTORIAL_CATEGORY_SOLAIRE_ID` | Solaire |
| `domotique` | `ZOHO_TUTORIAL_CATEGORY_DOMOTIQUE_ID` | Domotique |

---

## Sous-Catégories par Produit

### Création Automatique

Pour chaque produit détecté sur le site Avidsen, une sous-catégorie Zoho est créée :

```
Zoho Desk
├── Portail
│   ├── Avidsen - 114457 - Coulissants 500Kg
│   ├── Avidsen - 127100 - Soria 400W
│   └── ...
├── Visiophone
│   ├── Philips - 531001 - WelcomeEye Touch
│   ├── Philips - 531004 - WelcomeEye Compact
│   └── ...
├── Caméra
│   ├── Avidsen - 123281 - IPC281-Ex
│   ├── Thomson - 512399 - Caméra pour extérieur
│   └── ...
├── Solaire
│   └── Avidsen - 127100 - Soria 400W
└── Domotique
    └── ...
```

### Normalisation des Noms

Les noms des sous-catégories sont normalisés :
- Nettoyage des suffixes numériques entre parenthèses
- Conservation du format : `[Marque] - [Référence] - [Nom du produit]`
- Exemples :
  - `Avidsen - 123281 (1) - IPC281-Ex` → `Avidsen - 123281 - IPC281-Ex`
  - `Philips - 531001 (4) - WelcomeEye Touch` → `Philips - 531001 - WelcomeEye Touch`

---

## Gestion des Doublons

### Tutoriels Partagés

Un tutoriel peut être applicable à plusieurs produits :
- Le même tutoriel URL est publié dans **plusieurs sous-catégories**
- Chaque sous-catégorie reçoit sa propre copie de l'article
- Les permalinks sont uniques grâce à l'ID de sous-catégorie

### Exemple

```
Tutoriel : "Connexion caméra VISIA et AVIWATCH par TENVISTY"
URL : https://www.avidsen.com/fr/assistance/tutoriel-sav/tuto/...

Publié dans :
├── Caméra/Avidsen - 123281 - IPC281-Ex
├── Caméra/Avidsen - 123282 - IPC282-Miw
├── Caméra/Avidsen - 123287 - extérieure 720P
└── Caméra/Avidsen - 123381
```

---

## Cache et Optimisation

### Cache de Contenu par URL

Pour optimiser le scraping :
- Le contenu d'un tutoriel est scrapé **une seule fois par URL**
- Le même contenu est réutilisé pour tous les produits associés
- Réduction significative des requêtes HTTP

### Déduplication par (URL, Produit)

La déduplication s'effectue sur la paire `(url, produit)` :
- Permet à un même tutoriel d'être associé à plusieurs produits
- Évite les entrées en double pour le même produit

---

## Sections Matériel et Pièces Détachées

### Extraction Automatique

Les tutoriels peuvent contenir deux types de sections dans la boîte grise :

1. **Matériel nécessaire** : Outils et équipements requis
   - Exemple : "Clé BTR 5, Tournevis cruciforme"
   
2. **Pièces détachées nécessaires** : Références des pièces avec liens
   - Exemple : "Référence : 531006B → [Lien vers le produit]"

### Gestion des Liens

- Les liens sont inclus **seulement si présents sur le site source**
- Si le site ne fournit pas de lien pour une référence, seule la référence est affichée
- Les liens pointent généralement vers `maisonic.com`

---

## Permalinks Uniques

### Génération

Les permalinks incluent l'ID de la sous-catégorie pour garantir l'unicité :
```
Format : {sanitized-title}-{category-id-hash}
Exemple : connexion-camera-visia-1775148265
```

### Gestion des Collisions

En cas de collision (même titre dans la même sous-catégorie) :
- Un suffixe numérique est ajouté automatiquement
- Exemple : `programmation-clavier (2)`

---

## Erreurs Communes

### Sous-Catégorie Déjà Existante

```
[ERROR] Création sous-catégorie 'Thomson - 512501' : 422 - duplicate name
[WARNING] Sous-catégorie non créée, utilisation de la catégorie parente
```

**Solution** : L'application normalise les noms et réutilise les sous-catégories existantes.

### CategoryID Invalide

```
[ERROR] Zoho (422) : categoryId invalid
```

**Solution** : Vérifiez les IDs de catégorie dans `config.txt`.

---

## Bonnes Pratiques

1. **Vérifiez les IDs de catégorie** avant le premier lancement
2. **Surveillez les logs** pour les sous-catégories non créées
3. **Utilisez l'interface Zoho Desk** pour vérifier la structure après publication
4. **Nettoyez manuellement** les doublons si nécessaire (rare)

---

## Monitoring

### Logs de Publication

Chaque publication affiche :
- La sous-catégorie cible
- Le succès ou l'échec de la création
- Les liens injectés pour les produits applicables

### Structure dans Zoho Desk

Après publication, vérifiez dans Zoho Desk :
1. Base de connaissances
2. Catégorie principale (ex: Caméra)
3. Sous-catégories créées automatiquement
4. Articles publiés avec le contenu complet

---

## Mise à Jour

La structure est automatiquement maintenue :
- Nouveaux produits → nouvelles sous-catégories
- Produits supprimés → sous-catégories orphelines (à nettoyer manuellement si besoin)
- Tutoriels mis à jour → republication automatique
