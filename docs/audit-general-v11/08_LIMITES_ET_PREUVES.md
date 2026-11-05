# Limites de l'audit et preuves

## 1. Environnement d'audit

- Dépôt cloné dans un conteneur éphémère (Linux, Python 3.13). Environnement virtuel créé **hors du dépôt**, dépendances de `requirements.txt` installées.
- Aucune base existante n'a été touchée : les tests utilisent des bases de test temporaires créées et détruites par Django ; aucune migration n'a été appliquée à une base réelle.
- Variables : `DJANGO_DEBUG=1`, clé secrète factice. Rien n'a été déployé ni fusionné ; seule la branche de travail de l'audit a été déplacée sur 1c37f22.
- Sous-module `design` (`78060c5`) : non initialisé ; les règles de direction artistique n'ont pas été lues à la source.
- **PostgreSQL** : indisponible à la 1ʳᵉ passe ; **disponible à la 2ᵉ** (cluster jetable local) : voir §3 ter. Les chiffres du dossier de recette sont désormais confirmés par rejeu pour ce commit.
- **Navigateur** : utilisé à la 2ᵉ passe (Chromium via Playwright, un seul navigateur, Linux) : voir `audits/AUDIT_05.md`. Sous-module `design`, maquettes, impression, mode sombre, tablette tactile, lecteur d'écran : non testés.

## 2. Sources non accessibles ou partielles

| Source | État |
|---|---|
| Conversations ChatGPT | Non disponibles |
| Notion : hub « Organigramme et rôles » et ses 13 sous-pages (01 à 13) | **Lues en entier** le 2026-11-05 (2ᵉ passe) ; pages datées du 29/09 au 31/10 ; statut « non vérifié » côté Notion |
| Notion : Ordre de travail V1.1 | Lu partiellement (titres et passage Rondes) |
| Notion : 380 tâches | Décompte seulement |
| Descriptions des PR | Non lues |
| Documents FANLAB | Non retrouvés dans le dépôt à ce stade |
| Guide du marin 2023 | Non disponible (cité par les propositions du dépôt comme absent) |
| Sources publiques Marine nationale | Non consultées (audit 19) |
| `MATRIX_V11_AUDIT_INDEPENDANT.md` | Cité par `phase1_bilan_apres_audit.md` comme non transmis à l'environnement qui l'a rédigé ; non retrouvé non plus ici |

## 3. Résultat de la suite de tests complète

Commande : `python manage.py test --parallel` sur le commit `1c37f22`, SQLite, base de test temporaire, 2026-11-05.

Résultat : **3 829 tests exécutés en 792 s, OK, 20 ignorés** (les 20 ignorés sont, d'après le dossier de recette, des tests propres à PostgreSQL ; non vérifié ici). Cela confirme le chiffre annoncé par `docs/recette/00_SYNTHESE.md` pour SQLite, sur un commit postérieur de 2 commits.

Portée : ce résultat prouve que les tests existants passent, pas que les parcours métier sont conformes (voir audit 16).

## 3 ter. Suite complète sous PostgreSQL (2ᵉ passe)

`manage.py test --parallel 4` sur **PostgreSQL 16.15** (cluster jetable local créé par `initdb`, port 54329, mot de passe jetable) : **3 829 tests, OK, 0 ignoré**, 899 s, 2026-11-05, commit `1c37f22`. Les 20 tests ignorés sous SQLite s'exécutent et passent. Limites : un seul poste, mono-version de PostgreSQL, aucune charge réelle.

## 3 bis. Vérifications dynamiques de la reprise (2026-11-05)

Base SQLite temporaire hors dépôt (`MATRIX_SQLITE_PATH`), `migrate` puis `seed_demo`, client de test Django avec connexion forcée, transactions annulées pour les écritures. Les scripts de sonde sont dans le répertoire temporaire de l'audit, **non versionnés** (le dépôt ne doit pas recevoir de code ; à joindre à la demande). Résultats : `audits/AUDIT_06.md`, `AUDIT_15.md`, `AUDIT_03.md`. Limites : un seul navigateur jamais lancé, SQLite uniquement, mono-processus, données de démonstration fictives, mesures de durée indicatives.

## 4. Règle d'emploi des preuves

- Une preuve est un fichier, une fonction, un test ou une sortie de commande citée avec son emplacement.
- Les déclarations du dossier de recette du dépôt (`docs/recette/`) ne sont pas des preuves de l'audit tant qu'elles n'ont pas été rejouées.
- « Lecture de code » ne vaut pas « fonctionne » : le registre le précise à chaque fois.
