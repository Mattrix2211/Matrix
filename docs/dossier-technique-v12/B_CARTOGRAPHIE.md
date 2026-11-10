# B. Cartographie fonctionnelle

Base : V1.1 (`1c37f22`). Les modules et leur taille viennent de l'inventaire de l'audit (`02_INVENTAIRE_FONCTIONNEL.md`, comptage mécanique) ; les rôles décrits viennent des pages Notion et des sondes citées. **La présence d'un module ne le déclare pas conforme** : l'état par décision est dans `C_MATRICE_TRACABILITE.md`.

## B.1 Modules (22 paquets applicatifs)

| Module | Rôle fonctionnel | Décisions PO concernées | Lacunes connues |
|---|---|---|---|
| `org` | Bâtiment, service, secteur, section, équipage, double équipage | DEC-ORG-*, DEC-DRT-05, DEC-MUT-* | Archivage sans effet (AUD-028), suppression destructrice (AUD-020) |
| `accounts` | Comptes, profils (grade, fonction, spécialité), rôles, journal d'audit | DEC-ORG-04, DEC-MUT-*, DEC-DRT-06 | Suppression de compte (AUD-034), pas d'import (AUD-012), pas de mutation |
| `taches` | Tâches, participants, checklist, pièces jointes | DEC-TAC-*, DEC-COL-*, DEC-CLO-*, DEC-BLQ-* | 2 priorités, pas de « À valider », pas de coordinateur |
| `maintenance` / `assets` | Installations, fiches, occurrences, périodicité, circuits de fiches, QR | DEC-PER-*, DEC-DUR-*, DEC-OUT-*, DEC-MAT-* | Pas de durée dynamique, pas de transfert |
| `logistics` | Tickets correctifs, anomalies, pièces, stocks | DEC-ANO-* | Déroulé libre du ticket (AUD-043) |
| `quarts` | Listes de quarts et de gardes, feuille de service, échanges, remplacement du chef de liste | DEC-FDS-*, DEC-SUP-* | Droits par niveau (AUD-014/015), doublon de créneau |
| `postes`, `programme` | Postes, programme du bâtiment | DEC-FDS-08 | Peu testés (AUD-030) |
| `dashboard` | Accueil « Aujourd'hui », session d'appareillage | DEC-UX-01, DEC-APP-* | Signature simple (AUD-047) |
| `calendar_app` | Calendrier central | DEC-UX-11 | Vue personnelle par défaut (AUD-025) |
| `notifications` | Centre de notifications, Web Push | DEC-UX-06 | Deux états (AUD-038), rappels à la lecture (AUD-039) |
| `annonces` | Annonces avec accusé | — | Niveaux de vocabulaire (AUD-041) |
| `threads` | Discussions attachées aux objets | CLAUDE.md principe 9 | — |
| `training` | Formations, qualifications, portabilité | DEC-ORG-05, DEC-QUA-* | Référentiel BHT/C-CDM non vérifié |
| `retex` | Retours d'expérience | DEC-RTX-* | Circuit absent (AUD-045) |
| `documentation` | Bibliothèque documentaire | — | Peu testée |
| `demandes` | Demandes | — | Peu testée |
| `absences` | Absences et indisponibilités | DEC-PRE-01 | Corrections seulement |
| `reports` | Exports PDF, Excel, CSV, bilan | DEC-PRE-03 | Durée du bilan (AUD-013) |
| `rondes` | Résidu du module retiré | NOT-11 | Code et migrations conservés (AUD-007) |
| `matrix` (cœur) | Réglages, vues d'administration, permissions, périmètres, recherche | DEC-DRT-*, DEC-UX-03 | Structure du bord (AUD-019), 55 niveaux en dur (AUD-022) |

## B.2 Acteurs (fonctions, pas seulement grades)

| Acteur | Source | Rôle dans Matrix |
|---|---|---|
| Équipier / marin | S1 | Exécute, déclare terminé, bloqué, signale outillage et anomalies |
| Chef de section | S1, N1 | Attribue les tâches de sa section ; valide ou demande une correction (option) ; étape RETEX |
| Chef de secteur | S1, S2 | Supervise, attribue, réaffecte, valide directement, décide des anomalies, corrige les durées, étape RETEX |
| Chef de service | S1 | Supervision de sa fonction ; approuve un transfert ; étape RETEX et appareillage |
| Commandant adjoint (COMAEQ, COMOPS, COMANAV, COMAVIA) | N2, N3 | Compétent par service ; COMAEQ approuve la feuille de service ; COMANAV signe l'appareillage |
| Commandant, commandant en second | N3 | Vision globale ; exception de la feuille si COMAEQ vacant |
| BSC | S1, N8 | Prépare et imprime la feuille de service |
| Chef de liste | N3 | Listes de service et de garde |
| Administrateur technique (MASTER_ADMIN, ADMIN_NAVIRE) | S1, N3 | Plateforme ; désigne les titulaires ; applique un transfert approuvé ; **aucun visa métier** |
| Responsable de spécialité / de classe (ALFAN, IRB) | N2 | Étapes finales du circuit de fiche flotte |
| Équipage à terre / équipage B | N3 | Feuille propre à son équipage ; lecture seule ailleurs |
| Autorité habilitée | S1 §4 | Régularise une mutation (non définie, IM-03) |
| Suppléant | S1 §10 | Exerce une fonction bornée, temporaire |

Distinction à respecter (N5) : **grade ≠ fonction exercée ≠ habilitation logicielle ≠ périmètre ≠ brevet**.

## B.3 Périmètres

Bâtiment → équipage (A/B) → service → secteur → section facultative. Le **secteur** est l'échelon responsable quand il n'a pas de section (DEC-ORG-02). Les droits d'écriture sont vérifiés au serveur (RT-01). Les accès intersectoriels exigent un droit explicite (DEC-DRT-04).

## B.4 Circuits de validation

| Circuit | Étapes (décision) | État dans la V1.1 |
|---|---|---|
| Feuille de service | BSC (rédacteur désigné) → COMAEQ ou suppléant habilité → publication ; modification = nouvelle version ; alerte de réimpression | Rédaction, visa et versions : existent ; suppléant officiel et alerte : absents |
| Échange de tours | Examen → décision finale COMAEQ (S1) ou chef de liste (N7) | Existe ; autorité finale : contradiction CT-01 |
| Validation de tâche | Option du chef : équipier → « À valider » → chef de section ou chef de secteur (correction motivée possible) | Absent |
| Visa technique | Distinct de la validation de tâche | Existe (fiches) |
| RETEX | Auteur → chef de section si présent → chef de secteur → chef de service | Absent (seuil de niveau) |
| Fiche installation | Section/secteur → chef de service → commandant adjoint | Existe |
| Fiche matériel flotte | 7 étapes jusqu'au catalogue flotte | Existe |
| Préparation à l'appareillage | Section/secteur → service → COMANAV ; contrôles obligatoires ; réserves ; points critiques | Partiel (signature simple) |
| Transfert intra-service | Chef de service | Absent |
| Transfert inter-services | Deux chefs de service → administrateur habilité applique | Absent |
| Mutation | Nouveau bâtiment demande → ancien informé et confirme (ou autorité régularise) | Absent |
| Suppléance | Autorité compétente active, durée bornée, récapitulatif au retour | Seul le chef de liste est suppléable |
| Clôture de tâche (ordinaire) | Équipier termine directement | Existe |

## B.5 Dépendances entre modules

- `accounts`/`org` → tout le reste : périmètres, désactivation, mutation (étapes 1.3, 2.5, 6).
- Suppléance (`quarts` aujourd'hui) → feuille de service, RETEX, appareillage, tâches validées par un supérieur.
- `taches` ↔ `maintenance`/`assets` ↔ `logistics` : tâche périodique, anomalie, intervention ; le transfert de matériel déplace les tâches ouvertes.
- `taches` → durée estimée : périodes « En cours » et « Bloquée » alimentent la mesure du travail effectif.
- `notifications` + Celery : état « Non réalisée », rappels, alertes de réimpression.
- `training` → affichage informatif des qualifications dans `taches` (jamais bloquant).
- `threads` : dialogue attaché à tâche, anomalie, équipement, document (CLAUDE.md principe 9).
- `reports` : exports de pilotage alimentés par tâches, maintenance, logistique.

## B.6 Contraintes transverses

Fonctionnement sans Internet (DEC-PRE-05) ; configuration plutôt que code (DEC-ORG-06) ; traçabilité par `AuditLog` (RT-02) ; proposer → valider → publier pour les modifications sensibles ; double équipage sans dupliquer le bâtiment (DEC-FDS-12).
