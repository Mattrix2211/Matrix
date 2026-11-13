# Barrière G1a — socle d'outillage (phase 1)

> Document de travail provisoire. Date : 13/11/2026.

## Livré
| Élément | Fichier |
|---|---|
| Constructeur unique (Markdown → HTML → PDF ; numérotation automatique ; sommaire paginé en deux passes ; mention provisoire sur chaque page ; renvois `[[RF 5.2]]` ; faits `{{fait:nom}}` ; directive `@capture`) | `outils/construire.py`, `outils/imprimer.js`, `gabarits/refonte.css` |
| Contrôles C1, C2, C3, C5, C6, C7, C8, C11, C13, C14 | `outils/controles.py`, `config/separation.yaml`, `config/termes.yaml` |
| Identité documentaire commune, sans référence applicative | `config/identite.yaml` |
| Mesure de base sur l'ancien dossier | `baseline/MESURE_DE_BASE_ancien_dossier.md` |

Les contrôles C4 (références de code), C9 (captures, phase 4), C10 (inspection à taille réelle, protocole manuel, phase 11) et C12 (reproductibilité, phase 10) ne sont pas dans ce script : C4 réutilise `outils/verifier_references.py` à la phase 3 sur le chapitre technique pilote ; C9, C10 et C12 appartiennent aux phases suivantes.

## Critère de barrière : les contrôles détectent des défauts connus de l'ancien dossier
| Défaut connu (audit) | Détecté ? | Contrôle |
|---|---|---|
| En-tête « DIFFUSION GÉNÉRALE » et mot « diffusable » (AUD-001) | **Oui** : 113 occurrences dans le PDF | C5 |
| Mention provisoire absente | **Oui** : 108 pages sur 108 | C5 |
| Chemins de code, branches, commits, variables d'environnement dans le « diffusable » | **Oui** : 40 chemins, 9 branches, 38 identifiants de commit, 16 variables (PDF) | C5 |
| Légende séparée de S10, p.5 du restreint | **Oui** | C8 |
| Tableaux cassés p.37 et p.79 du restreint | **Oui** | C8 |
| Annexe F.5 dégradée (`**`, accent grave), p.130, 131, 134, 135 | **Oui** | C8 |
| Pages presque vides (restreint p.39, 41, 45 notamment ; diffusable : 7 pages) | **Oui** : 7 pages < 40 % (diffusable), 11 (restreint) | C8 |
| Chiffres en dur susceptibles de dériver | **Oui** : 5 avertissements | C3 |
| Application intacte depuis `637de94` | **Oui** : 0 fichier hors documentation | C13 |

Limites de cette mesure : le contrôle de petite police ne signale rien sur l'ancien diffusable (corps de 9,6 pt), il signale 1 page du restreint ; les titres orphelins ne sont mesurés que sur les nouveaux PDF (marqueurs de titre).

## Essai du constructeur
Document d'essai de 4 pages (jeté) : couverture avec mention et précaution, sommaire paginé exact (3, 3, 4), mention sur chaque page, faits substitués (135 modèles, 721 routes), renvoi résolu, pastille ⚪ rendue « ◯ ».
