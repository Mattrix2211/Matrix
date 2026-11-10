# O. Lot L05 — compte rendu de livraison (AUD-010, AUD-017)

**Branche** : `claude/l05-config-production-v11`, commit `517a2ce`, **empilée sur la branche L01** (`8e60fee`, issue de la V1.1 `1c37f22`) : elle contient donc les deux lots, à fusionner dans cet ordre. `main` non modifiée, aucune PR. **Statut : livré, en attente de validation du PO.**

## 1. Risques constatés avant modification

| Constat | Détail |
|---|---|
| Clé secrète d'exemple acceptée (AUD-017) | `.env.example` contenait `DJANGO_SECRET_KEY=change-me` ; le démarrage en production ne refusait que `dev-secret-key`. Un `.env` copié tel quel passait. Aucune exigence de longueur |
| Mot de passe de base par défaut (AUD-010) | `DB_HOST` défini sans `DB_PASSWORD` : repli silencieux sur `matrix`, valeur aussi présente en commentaire dans `.env.example` et dans le README |
| Docker | `POSTGRES_PASSWORD=change-me` accepté par `docker-compose.yml` (variable seulement exigée non vide) ; port lié à `127.0.0.1` |
| Déjà correct | Développement local en SQLite ; instance de démonstration qui ignore le `.env` du poste |

## 2. Modifications

- **`matrix/settings.py`** : fonction `erreurs_secrets_production(env, cle)`. Hors DEBUG, refus au démarrage (`ImproperlyConfigured`, message en français, toutes les raisons cumulées) si la clé est absente, vide, de moins de 32 caractères ou égale à une valeur d'exemple (`dev-secret-key`, `change-me`, `changeme`, `secret`, `password`, `matrix`, `postgres`, `admin`, `pass`, casse ignorée), ou si `DB_HOST` est défini (sans `MATRIX_SQLITE_PATH`) avec un `DB_PASSWORD` absent, vide ou de cette liste. Une variable `DJANGO_SECRET_KEY` vide équivaut à absente (clé de développement en DEBUG).
- **`.env.example`** : `DJANGO_SECRET_KEY` vide avec la commande de génération ; `DB_PASSWORD` sans valeur d'exemple ; précision que `POSTGRES_PASSWORD=change-me` est pour le développement local.
- **`README.md`** : règles de production, génération d'une clé, `DB_PASSWORD` du développement renvoyé vers `POSTGRES_PASSWORD`.
- **`docs/recette/L01_recette_windows.md`** : l'étape 11 utilise une clé de plus de 32 caractères (sinon l'erreur de clé masquerait `matrix.E001`).
- **Aucune migration, aucun nouveau système de configuration.** Développement inchangé : l'installation locale fonctionne avec le `.env.example` tel quel.

## 3. Résultats

| Vérification | Résultat |
|---|---|
| Suite complète SQLite (`test --parallel 4`) sur `517a2ce` | **3 895 tests OK, 20 ignorés** (3 884 de L01 + 11 nouveaux) |
| Nouveaux tests (`test_configuration_production`) : fonction pure et démarrage réel dans un processus neuf (`.env` absent, environnement filtré) | OK ; 5 des 6 tests de démarrage échouent sur l'ancien code, ce qui prouve qu'ils testent le défaut |
| `test_core_checks` (recharge de `matrix.settings` hors DEBUG) | OK |
| Le fichier `.env.example` lui-même | démarre en développement ; refusé en production |
| Relecture indépendante | ✅ validé, aucun point bloquant |

**Non exécuté** : PostgreSQL (non disponible ; seul le contrôle du mot de passe est testé comme fonction et au démarrage, sans connexion réelle) ; Windows (inchangé par ce lot).

## 4. Risques résiduels (non bloquants, documentés)

1. Une clé triviale d'au moins 32 caractères (`aaaa…`) est acceptée : la longueur ne mesure pas l'entropie.
2. La liste de valeurs refusées est courte (`changeme123` passe) ; pour `DB_PASSWORD`, seule cette liste compte (`abc` est accepté).
3. Les valeurs d'environnement ne sont pas nettoyées (une clé de 32 espaces fournie par une vraie variable serait acceptée ; le fichier `.env` est nettoyé).
4. Le chargeur de `.env` ne gère pas les commentaires en fin de ligne (comportement préexistant ; `.env.example` le signale). Conséquence sûre : `DJANGO_DEBUG=1 # dev` vaut faux et la production est alors refusée.
5. Les autres secrets ne sont pas contrôlés (`EMAIL_HOST_PASSWORD`, `VAPID_PRIVATE_KEY`, mot de passe Redis) : à traiter avec la dette « settings ».
6. `POSTGRES_PASSWORD=change-me` reste dans `.env.example` pour le développement local ; à changer hors poste local.
7. Le repli `matrix` de `DB_PASSWORD` reste actif en DEBUG (voulu).

## 5. Suite recommandée

L02 (archivage effectif), puis L03 (suppression sûre des unités) et L04 (désactivation des comptes) : ils touchent aux périmètres et exigent des migrations ; chacun sera lancé séparément sur votre accord. Aucun n'est démarré.
