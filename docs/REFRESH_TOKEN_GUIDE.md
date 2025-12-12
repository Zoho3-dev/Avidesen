# Guide de Rafraîchissement du Token Zoho

## Script de Rafraîchissement

Le script `refresh_token.py` permet de rafraîchir automatiquement votre token d'accès Zoho.

## Utilisation

### Méthode Simple

```bash
python refresh_token.py
```

Le script va :
1. ✅ Charger votre configuration depuis `config.txt`
2. 🔍 Vérifier l'état de vos tokens
3. 🔄 Rafraîchir automatiquement le token
4. 💾 Sauvegarder le nouveau token dans `config.txt`

## Prérequis dans config.txt

Votre fichier `config.txt` doit contenir :

```
ZOHO_CLIENT_ID=votre_client_id
ZOHO_CLIENT_SECRET=votre_client_secret
ZOHO_REFRESH_TOKEN=votre_refresh_token
```

### Si vous n'avez pas de REFRESH_TOKEN

Si c'est la première fois, vous devez également avoir :

```
GRANTED_CODE=votre_granted_code
```

Le script utilisera le `GRANTED_CODE` pour obtenir un `REFRESH_TOKEN` la première fois.

## Cas d'Usage

### 1. Rafraîchissement Automatique

Le token est automatiquement rafraîchi quand vous lancez `main.py`, mais vous pouvez le faire manuellement :

```bash
python refresh_token.py
```

### 2. Token Expiré

Si votre token a expiré :

```bash
python refresh_token.py
```

### 3. Première Configuration

Si c'est votre première utilisation :

1. Obtenez un `GRANTED_CODE` depuis la console Zoho
2. Ajoutez-le dans `config.txt`
3. Lancez :
   ```bash
   python refresh_token.py
   ```

## Messages du Script

### ✅ Succès
```
✅ Token rafraîchi avec succès !
   Nouveau token : AbCdEf1234567890...
💾 Le token a été sauvegardé dans config.txt
```

### ❌ Erreur
```
❌ Échec du rafraîchissement du token

💡 Solutions possibles :
   1. Vérifiez que ZOHO_CLIENT_ID et ZOHO_CLIENT_SECRET sont corrects
   2. Si vous n'avez pas de REFRESH_TOKEN, générez un nouveau GRANTED_CODE
   3. Consultez la documentation Zoho OAuth pour obtenir un nouveau code
```

## Intégration dans le Code

Le rafraîchissement est également intégré dans le code principal. La classe `ZohoAuth` gère automatiquement :

- ✅ Vérification de l'expiration du token
- 🔄 Rafraîchissement automatique si nécessaire
- 💾 Sauvegarde automatique dans `config.txt`

Vous n'avez donc pas besoin de lancer manuellement `refresh_token.py` à chaque fois, sauf si vous voulez forcer un rafraîchissement.

## Obtenir un GRANTED_CODE

1. Allez sur [Zoho API Console](https://api-console.zoho.com/)
2. Sélectionnez votre application
3. Générez un nouveau code d'autorisation
4. Copiez le code dans `config.txt` sous `GRANTED_CODE`
5. Lancez `python refresh_token.py`

## Dépannage

### Token toujours invalide

1. Vérifiez que `ZOHO_CLIENT_ID` et `ZOHO_CLIENT_SECRET` sont corrects
2. Générez un nouveau `GRANTED_CODE`
3. Supprimez `ZOHO_REFRESH_TOKEN` de `config.txt`
4. Relancez `python refresh_token.py`
