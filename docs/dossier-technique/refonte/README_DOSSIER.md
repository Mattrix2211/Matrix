# Dossier de documentation Matrix — révision 2 (G0 rév. 2)

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Précaution documentaire : cette mention n'est pas une classification officielle ; la classification et les destinataires restent à valider par l'autorité compétente. Ne pas diffuser.
> **État de ce dossier : sources contrôlées (barrière G1). Les PDF de la révision 2 ne sont pas encore construits.** Le basculement (archivage des anciennes arborescences, retrait des anciens PDF) n'est pas fait.

## Qui lit quoi

| Je suis… | Je lis | Où |
|---|---|---|
| Marin ou chef | Le **guide utilisateur** illustré | `1_guide_utilisateur/` |
| Responsable, commandement, décideur | Le **référentiel fonctionnel et de gouvernance** (commencer par le résumé pour le décideur) | `2_referentiel_fonctionnel/` |
| Développeur, mainteneur, exploitant | Le **dossier technique de reprise** (accès restreint) | `3_dossier_technique/` |
| Quiconque cherche un inventaire (routes, modèles, variables, éléments non vérifiés) | Les **annexes consultables** : ouvrir `4_annexes_consultables/index.html` (hors ligne) ou les CSV | `4_annexes_consultables/` |
| PO, responsable, mainteneur | Le **registre des écarts et décisions** (source unique : `registre.json`) | `5_registre/` |

## Fichiers d'accompagnement

| Fichier | Rôle |
|---|---|
| `MAPPING_ANCIEN_NOUVEAU.csv` | Chaque titre de l'ancienne édition → son emplacement dans la nouvelle structure ou « retiré » avec motif |
| `faits.yaml` | Registre des chiffres (généré depuis l'inventaire du code), injecté dans les documents |
| `config/` | Identité documentaire, séparation, termes, revue manuelle des contrôles |
| `captures/` | Captures d'écran (instance de démonstration isolée, données fictives) et manifeste (profil, statut HTTP, assertions, langue) |
| `schemas/` | Sources Mermaid et exports SVG |
| `outils/` | Constructeur, contrôles C1 à C14, générateurs |
| `REPRISE.md` | Point de reprise : phase en cours, dernière tâche, contrôles |
| `baseline/` | Rapports de barrière |

## Reconstruire et contrôler

```bash
python3 refonte/outils/lancer_controles_sources.py     # aperçus HTML et contrôles sur les sources (barrière G1)
python3 refonte/outils/generer_annexes_consultables.py  # annexes consultables
python3 refonte/outils/generer_registre.py <dossier-technique> <dossier-v12> refonte/5_registre
```

Rien dans ce dossier ne valide le logiciel Matrix ni n'autorise sa diffusion.
