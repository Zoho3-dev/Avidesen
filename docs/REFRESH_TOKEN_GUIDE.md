# Guide de Rafraîchissement du Token Zoho

## Fonctionnement

Le token Zoho est **rafraîchi automatiquement** par le pipeline (`main.py` / `gui.py`). Le script `refresh_token.py` permet de forcer un rafraîchissement manuel si nécessaire.

## Rafraîchissement automatique

Lors de chaque appel API, le système :

1. Vérifie si le token est encore valide (avec 5 minutes de marge)
2. Le rafraîchit automatiquement s'il est expiré
3. Réessaie la requête en cas d'erreur 401
4. Sauvegarde le nouveau token dans `config.txt`

**Aucune intervention manuelle n'est nécessaire en fonctionnement normal.**

## Rafraîchissement manuel

```bash
python refresh_token.py
```

Utile si vous voulez vérifier l'état de vos tokens ou forcer un rafraîchissement.

## Prérequis dans config.txt

```ini
ZOHO_CLIENT_ID=votre_client_id
ZOHO_CLIENT_SECRET=votre_client_secret
```

### Première utilisation (pas de REFRESH_TOKEN)

Ajoutez un `GRANTED_CODE` obtenu depuis la console Zoho :

```ini
GRANTED_CODE=votre_granted_code
```

Le script échangera ce code contre un `REFRESH_TOKEN` (sauvegardé automatiquement).

## Obtenir un GRANTED_CODE

1. Allez sur [Zoho API Console](https://api-console.zoho.com/)
2. Sélectionnez votre application (Self Client)
3. Scope : `Desk.articles.ALL`
4. Générez un code d'autorisation
5. Copiez-le dans `config.txt` sous `GRANTED_CODE`
6. Lancez `python refresh_token.py`

> **Note :** Le `GRANTED_CODE` est à usage unique et expire en quelques minutes.

## Dépannage

| Problème | Solution |
|---|---|
| Token toujours invalide | Vérifiez `ZOHO_CLIENT_ID` et `ZOHO_CLIENT_SECRET` |
| Refresh token invalide | Générez un nouveau `GRANTED_CODE`, supprimez `ZOHO_REFRESH_TOKEN` de `config.txt`, relancez `python refresh_token.py` |
| Erreur réseau | Vérifiez votre connexion internet |
