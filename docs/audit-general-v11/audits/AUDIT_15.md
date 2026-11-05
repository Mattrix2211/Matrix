# Audit 15 — Sécurité et résilience (rapport partiel, 2ᵉ passe)

**Statut : Clôturé avec réserves** (voir « Clôture » en bas du rapport)..

## 1. Constats vérifiés (inchangés depuis la 1ʳᵉ passe)

Aucune ressource externe active (principe « Internet n'existe pas » : conforme pour le code statique et pour 7 profils en navigateur réel, aucune requête externe) ; `check` propre ; migrations à jour ; 227 routes sans paramètre fermées aux anonymes hors connexion ; clé de développement refusée en production.

## 2. AUD-009 — comptes de démonstration : isolement strict (défaut confirmé + proposition)

**Constat** (`matrix/core/management/commands/seed_demo.py:2-4,95`, `seed_demo_dense.py:146`, `seed_demo_mer_quai.py:53`) : les quatre commandes `seed_demo*` créent des comptes aux mots de passe `pass` et `admin`, **sans aucun refus conditionnel** : elles s'exécutent sur n'importe quelle base. Seul le script `scripts/preparer_instance_test.py` pose des garde-fous (base SQLite dédiée, `DEBUG` actif, hôtes locaux, courtier isolé, refus de lien symbolique), mais **un opérateur peut appeler `manage.py seed_demo` directement** : la protection tient à une convention, pas au code.

**Proposition de correction (non réalisée, pour accord du PO)**, par couches, de la plus sûre à la plus simple :
1. **Refus par défaut dans chaque commande `seed_demo*`** (une seule fonction commune) : exécution autorisée uniquement si `DEBUG` est actif **et** `MATRIX_INSTANCE_DEMO=1` explicitement posé **et** moteur SQLite **et** (base vide **ou** marqueur de démonstration présent). Jamais sur PostgreSQL, jamais si des comptes non fictifs existent.
2. **Marqueur persistant** : une ligne en base « instance de démonstration » écrite au premier remplissage. Au démarrage en production (`DEBUG=0`), un contrôle système de niveau *erreur* (`matrix/core/checks.py`) refuse de démarrer si le marqueur est présent : une base de démo ne peut pas devenir une base de production par oubli.
3. **Mots de passe** : jamais le même mot de passe pour tous les comptes sans l'option explicite de démonstration ; le compte `admin` ne reçoit pas `admin`.
4. **Test automatique** qui échoue si une commande `seed_demo*` s'exécute avec `DEBUG=0`.
5. **Documentation** : `lancer_demo.bat` reste la seule voie présentée.

## 3. AUD-010 — mot de passe PostgreSQL par défaut : risque réel selon l'environnement

Faits : `matrix/settings.py:186` retombe sur `matrix` si `DB_PASSWORD` est absent ; `README.md` et `.env.example` donnent `matrix` en exemple ; `docker-compose.yml` **exige** `POSTGRES_PASSWORD` (aucune valeur par défaut) et lie la base à `127.0.0.1`.

| Environnement | Risque réel |
|---|---|
| Poste de développement mono-utilisateur | Négligeable. |
| Serveur du bord avec la base Docker du dépôt (loopback seul) | Faible : l'attaquant doit déjà avoir un accès local à la machine. **Moyen si le serveur est un poste partagé** (tout compte local peut ouvrir la base avec `matrix/matrix` et lire toutes les données). |
| PostgreSQL séparé, joignable par le réseau, mot de passe par défaut | **Critique**, mais c'est une erreur d'exploitation, non une configuration livrée par le dépôt (aucun `pg_hba.conf` n'est fourni). |
| Redis sans mot de passe, loopback | Hypothèse : un compte local peut poser des tâches Celery ; sérialiseur à vérifier (non audité). |

Verdict : **durcissement de P2** (valeur par défaut faible, documentée comme exemple), pas une vulnérabilité exploitable à distance dans la configuration livrée. Correction proposée : exiger `DB_PASSWORD` dès que `DB_HOST` est défini et `DEBUG=0` ; ne plus donner `matrix` en exemple.

## 4. AUD-011 — HTTPS : contrainte de déploiement ou vulnérabilité ?

**Position conforme à la consigne** : HTTPS n'est pas à désactiver ; la question est de savoir **comment** le fournir sur un réseau de bord. Rejeu en mode production (`DJANGO_DEBUG=0`, base temporaire) avec le client de test, commande `sondes/prod_proxy.py` :

| Architecture simulée | Résultat |
|---|---|
| HTTP direct (réseau de bord sans TLS) | 301 vers HTTPS : inutilisable, comme attendu |
| **Reverse proxy qui termine TLS et transmet `X-Forwarded-Proto: https`** | **301 vers HTTPS en boucle** (Django ne lit pas l'en-tête : `SECURE_PROXY_SSL_HEADER` vaut `None`, non réglable par variable d'environnement) ; le POST de connexion subit la même redirection |
| TLS terminé par le serveur d'application lui-même | 200 ; POST de connexion avec `Origin` cohérent : 200 |

Conclusions établies :
- **Ce n'est pas une vulnérabilité** : les cookies de session et CSRF sont sécurisés, la redirection est le comportement voulu.
- **C'est un manque de configuration** (défaut confirmé de déploiement) : l'architecture la plus courante, *reverse proxy avec terminaison TLS*, **ne fonctionne pas telle que livrée** ; il faudrait soit un réglage `SECURE_PROXY_SSL_HEADER` piloté par l'environnement, soit re-chiffrer entre le proxy et l'application, soit faire terminer le TLS par le serveur d'application. Aucun serveur d'application (gunicorn, waitress, uvicorn) n'est dans `requirements.txt` : le mode de service en production n'est pas défini.
- `CSRF_TRUSTED_ORIGINS` est figé sur `http://localhost:8000` et `http://127.0.0.1:8000` (`matrix/settings.py:399-404`) : à compléter selon le nom interne du serveur (**non vérifié** avec un vrai proxy).
- HTTPS est aussi **requis fonctionnellement** : le service worker et le Web Push exigent un contexte sécurisé hors `localhost` (README, section Web Push).

Architectures possibles pour un réseau de bord (à arbitrer avec le PO et l'autorité SSI compétente ; je n'invente aucune règle de sécurité militaire) :

| Option | Description | Points d'attention |
|---|---|---|
| **1. Reverse proxy TLS devant l'application** (nginx, Apache ou équivalent) | Le proxy porte le certificat et protège l'écoute réseau ; l'application écoute sur la boucle locale ou un socket | Exige le réglage de l'en-tête de confiance **uniquement** si le proxy réécrit cet en-tête et si l'application n'est pas joignable directement ; certificat émis par une autorité interne (pas de Let's Encrypt : « Internet n'existe pas ») ; déjà le montage supposé pour les médias (`X-Accel-Redirect`, `docs/REFERENCE.md`) |
| **2. TLS porté par le serveur d'application** | Le serveur WSGI charge certificat et clé | Aucun réglage de proxy ; rotation des certificats plus manuelle ; pas de décharge des fichiers statiques |
| **3. TLS bout en bout (re-chiffrement proxy → application)** | Proxy et application en HTTPS | Plus de composants ; aucun changement de code |
| **4. Poste serveur unique, accès uniquement local** | Pas d'accès réseau, `localhost` | Contradictoire avec « postes du bord » multiples ; à écarter hors démonstration |

À trancher : l'**autorité de certification interne** et la **durée de vie des certificats** (hors compétence de l'audit).

## 5. AUD-017 — clé secrète « change-me » acceptée en production (défaut confirmé, P2)

`.env.example` propose `DJANGO_SECRET_KEY=change-me`. Le garde-fou de démarrage (`matrix/settings.py:53-57`) ne refuse que la valeur de développement `dev-secret-key` : `DJANGO_DEBUG=0 DJANGO_SECRET_KEY=change-me manage.py check` répond « no issues » ; seul `check --deploy` émet `security.W009`. Conséquence : une valeur publique copiée du dépôt signe les jetons de la plateforme. Correction proposée : refuser aussi les valeurs d'exemple et les clés trop courtes en production.

## 6. Non audité

Politique de mots de passe (validateurs listés, non évalués), verrouillage après échecs, journalisation (`AuditLog` : couverture non mesurée), sauvegarde et restauration (aucune procédure dans le dépôt), téléversement (registre des fichiers testé par le projet : non rejoué), injections et XSS, sérialiseur Celery, en-têtes de sécurité de réponse.

## Clôture (4ᵉ passe)

**Statut : Clôturé avec réserves.** « Avec réserves » signifie que l'analyse technique est achevée sur le périmètre décrit ; **les éléments listés ci-dessous restent non vérifiés et ne doivent pas être lus comme conformes**.

### Contrôles ajoutés à la 4ᵉ passe

Compléments : **aucun verrouillage après 25 échecs de connexion** (AUD-035) ; validateurs de mot de passe présents (4) ; seuils modifiables seulement dans son bâtiment ; proxy TLS : paramètres validés par simulation (`propositions/P03`).

### Non vérifié ou dépendant d'une validation externe

Injections et XSS, en-têtes de sécurité de réponse, téléversement de fichiers, sérialiseur Celery, politique SSI.
