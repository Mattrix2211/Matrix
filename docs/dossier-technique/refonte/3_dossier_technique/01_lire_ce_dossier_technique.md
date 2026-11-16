<!-- couvre: diffusable/03_lire_ce_dossier.md | 3.4 Organisation des fichiers -->
<!-- partie: Cadre -->
# Lire ce dossier technique

<div class="ligne-public"><b>Public :</b> développeurs, mainteneurs, exploitants · <b>Accès restreint</b> · <b>Ce que vous y trouverez :</b> l'identifiant exact de l'état décrit, l'organisation du dépôt documentaire, la façon de vérifier une référence de code</div>

## L'état décrit

| | État A | **État B (référence principale)** |
|---|---|---|
| Branche | `main` | `claude/l03-suppression-sure-v11` |
| Commit | `6ef16ad` (28/10/2026) | **`6d6d0be`** (11/11/2026) |
| Contenu | V1 FANLAB (PR n° 16) | V1.1 (interface « Naval Premium », correctifs de recette) **et** lots L01, L05, L02, L03 |
| Statut | publié, point de comparaison historique | **non fusionné dans `main`** |

Tout ce que ce dossier décrit comme « actuel » est ce que contient la branche de l'état B. Ce n'est ni une version déployée ni une version validée. L'état A n'apparaît que lorsqu'il diffère. Les décisions du PO citées (`DEC-…`) viennent du dossier V1.2 (branche `claude/eager-hopper-2cbcqh`, commit `6cc…` non reproduit ici) : elles sont citées, jamais rouvertes.

## Organisation du dépôt documentaire

Le dossier est un ensemble de fichiers Markdown maintenus dans le dépôt, sous `docs/dossier-technique/`.

| Dossier | Contenu |
|---|---|
| `refonte/1_guide_utilisateur/` | Sources du guide utilisateur illustré |
| `refonte/2_referentiel_fonctionnel/` | Sources du référentiel fonctionnel et de gouvernance |
| `refonte/3_dossier_technique/` | Sources du présent dossier |
| `refonte/4_annexes_consultables/` | Annexes en HTML autonome et en CSV |
| `refonte/5_registre/` | Registre central (`registre.json` est la source unique ; les autres fichiers en sont générés) |
| `refonte/captures/` | Captures d'écran et leur manifeste |
| `refonte/schemas/` | Sources Mermaid et exports SVG |
| `refonte/outils/` | Scripts de construction et de contrôle |
| `couverture/` | Inventaires et matrices générés depuis le code de l'état B |
| `audit_preuves/` | Preuves versionnées, dont les tests A14, A20 et A25, **non intégrés au dépôt applicatif** |
| Dossiers de l'édition initiale G0 (chapitres d'usage et techniques, schémas, guide visuel, PDF) | Sources et rendus initiaux, conservés à l'identique jusqu'au basculement |

Aucun mot de passe, clé ou donnée réelle n'est écrit dans le dossier.

## Vérifier une référence de code

Une référence de code s'écrit « fichier:ligne » ; elle est vérifiée par script sur une copie isolée de l'état B (contrôle C4 : toute référence doit exister et pointer le bon symbole). Les chiffres cités viennent du registre des faits, généré depuis l'inventaire du code ; ils sont identiques dans tous les documents (contrôle C3). Reconstruire les contrôles : voir la prise en main développeur ([[DT:02_prise_en_main_developpeur]]).
