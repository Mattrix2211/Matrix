# Limites de l'audit et preuves

## 1. Environnement d'audit

- Dépôt cloné dans un conteneur éphémère (Linux, Python 3.13). Environnement virtuel créé **hors du dépôt**, dépendances de `requirements.txt` installées.
- Aucune base existante n'a été touchée : les tests utilisent des bases de test temporaires créées et détruites par Django ; aucune migration n'a été appliquée à une base réelle.
- Variables : `DJANGO_DEBUG=1`, clé secrète factice. Rien n'a été déployé ni fusionné ; seule la branche de travail de l'audit a été déplacée sur 1c37f22.
- Sous-module `design` (`78060c5`) : non initialisé ; les règles de direction artistique n'ont pas été lues à la source.
- **PostgreSQL non disponible** : aucune vérification sur PostgreSQL n'a été faite ici. Les 3 829 tests « OK sur PostgreSQL » du dossier de recette sont **repris comme déclarations, non comme preuves**.
- **Navigateur** : non utilisé à ce stade (Chromium et Playwright sont disponibles ; les parcours seront rejoués dans les audits 04, 05 et 09).

## 2. Sources non accessibles ou partielles

| Source | État |
|---|---|
| Conversations ChatGPT | Non disponibles |
| Notion : pages 01 à 05, 07 à 12 de « Organigramme et rôles » | Non lues (liens connus) |
| Notion : Ordre de travail V1.1 | Lu partiellement (titres et passage Rondes) |
| Notion : 380 tâches | Décompte seulement |
| Descriptions des PR | Non lues |
| Documents FANLAB | Non retrouvés dans le dépôt à ce stade |
| Guide du marin 2023 | Non disponible (cité par les propositions du dépôt comme absent) |
| Sources publiques Marine nationale | Non consultées (audit 19) |
| `MATRIX_V11_AUDIT_INDEPENDANT.md` | Cité par `phase1_bilan_apres_audit.md` comme non transmis à l'environnement qui l'a rédigé ; non retrouvé non plus ici |

## 3. Résultat de la suite de tests complète

*À compléter dès la fin de l'exécution (en cours à la rédaction de cette page).*

## 4. Règle d'emploi des preuves

- Une preuve est un fichier, une fonction, un test ou une sortie de commande citée avec son emplacement.
- Les déclarations du dossier de recette du dépôt (`docs/recette/`) ne sont pas des preuves de l'audit tant qu'elles n'ont pas été rejouées.
- « Lecture de code » ne vaut pas « fonctionne » : le registre le précise à chaque fois.
