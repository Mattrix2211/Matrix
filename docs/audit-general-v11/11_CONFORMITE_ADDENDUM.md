# Conformité du dossier d'audit à l'addendum « 20 audits en 6 phases »

Contrôle réalisé sur le commit `7695fff`, puis complété par cette passe. **État avant** = dossier au commit `7695fff` ; **État après** = dossier à jour. Seules les exigences dont des éléments vérifiables manquaient ont été complétées ; aucun contrôle déjà correctement réalisé n'a été refait.

| N° | Exigence de l'addendum | État avant | Écart constaté | Action de cette passe | État après |
|---|---|---|---|---|---|
| R1 | 20 audits (les 18 du cahier initial + audit 19 + audit 20) | Satisfaite | — | — | Satisfaite |
| R2 | Organisation en 6 phases : 1 (01), 2 (19), 3 (02 à 12), 4 (13 à 17), 5 (20), 6 (18) | Partielle | phases présentes dans `PLAN_AUDITS.md` et `AVANCEMENT.md`, absentes du bilan et de la synthèse | colonne « Phase » ajoutée à `09_BILAN_DES_AUDITS.md` ; phases rappelées dans `00`, `PLAN_AUDITS`, `AUDIT_18` | Satisfaite |
| R3 | Livrable `audits/AUDIT_19_COHERENCE_MARINE.md` | **Absente** (fichier nommé `AUDIT_19.md`) | nom non conforme | fichier renommé | Satisfaite |
| R4 | Audit 19 : organisation hiérarchique et fonctionnelle | Partielle | rubrique non structurée, peu de règles | rubrique A (8 règles) | Satisfaite |
| R5 | Audit 19 : souplesse des structures selon les bâtiments ; adaptabilité à plusieurs organisations réelles | **Absente** | aucune analyse de la diversité des bâtiments ni de variantes | rubrique B (5 règles), mesure des 5 organisations de démonstration, 3 variantes exécutées (`sondes/organisations_reelles.py`) | Satisfaite (réserve : usages réels non validés par un expert) |
| R6 | Audit 19 : rôles, fonctions, responsabilités, permissions | Partielle | traité par renvoi à l'audit 06 | rubrique C (4 règles) | Satisfaite |
| R7 | Audit 19 : processus de travail quotidiens | **Absente** | non traité dans le rapport | rubrique D (3 règles) | Satisfaite |
| R8 | Audit 19 : maintenance et répartition des installations | **Absente** | non traité dans le rapport | rubrique E (6 règles) | Satisfaite (réserve : 2 règles non vérifiées) |
| R9 | Audit 19 : quarts et services MER/QUAI | Partielle | génération automatique et feuille seulement | rubrique F (7 règles, modes des 5 bâtiments) | Satisfaite |
| R10 | Audit 19 : circuits de validation | Partielle | feuille de service seulement | rubrique G (8 circuits) | Satisfaite (réserve : 4 circuits non rejoués) |
| R11 | Audit 19 : terminologie métier | Partielle | vocabulaire du cahier seulement | rubrique H (5 règles) | Satisfaite |
| R12 | Chaque constat distingue règles documentées, usages variables, hypothèses, incohérences, décisions PO | **Absente** | une seule colonne « verdict » | colonne « Nature du constat » (Documentée, Hypothèse, Incohérence…) et colonne « Décision PO nécessaire » | Satisfaite (réserve : aucun **usage variable** n'a pu être établi sans expert du bord ; la catégorie existe, aucune règle n'y est classée) |
| R13 | Matrice règle métier / source / implémentation / conformité / preuve / décision nécessaire | **Absente** | 4 colonnes (point, source, constat, verdict) | matrice à 8 colonnes, 46 règles | Satisfaite |
| R14 | Livrable `audits/AUDIT_20_DONNEES_DEMONSTRATION.md` | **Absente** (fichier nommé `AUDIT_20.md`) | nom non conforme | fichier renommé | Satisfaite |
| R15 | Audit 20 : crédibilité, diversité, cohérence, couverture fonctionnelle, cas limites | Partielle | mesures sans analyse par critère | cinq sections, une par critère | Satisfaite |
| R16 | Audit 20 : matrice de couverture par module et par profil | **Absente** | — | matrice de 13 modules × 16 profils (`sondes/couverture_demo.py`) | Satisfaite |
| R17 | Audit 20 : scénarios manquants | **Absente** | — | 13 scénarios, dérivés des états absents mesurés | Satisfaite |
| R18 | Audit 18 consolide les conclusions des 20 audits | Partielle | rédigé avant les autres audits : 5 problèmes, références périmées | réécrit : tableau des 20 audits (phase, statut, conclusion, anomalies, exigences), 6 problèmes transversaux | Satisfaite |
| R19 | Audit 18 : registre unique des anomalies | Partielle | 35 entrées, aucune pour les audits 10 et 11, limitations connues de la recette absentes | 7 entrées ajoutées (audits 10, 11, 19, 20, UX connues) : **42 entrées dédoublonnées**, chaque audit référencé sauf le 18 | Satisfaite |
| R20 | Audit 18 : matrice unique de conformité | Partielle | seules les exigences du référentiel | `03_MATRICE_CONFORMITE.md` réunit A (48 exigences), B (46 règles Marine), C (couverture de la démonstration) | Satisfaite |
| R21 | Ne modifier aucun code applicatif, aucune donnée de démonstration ; ne rien fusionner dans `main` | Satisfaite | — | contrôle ci-dessous | Satisfaite |

## Contrôle des interdictions

- Fichiers modifiés depuis `1c37f22` hors `docs/audit-general-v11/` : **aucun** (`git diff --name-only 1c37f22..HEAD`).
- Données de démonstration : les générateurs ne sont pas modifiés ; les sondes de cette passe lisent une copie de la base ou annulent leurs écritures par transaction.
- `main` n'est pas touchée ; aucune fusion, aucun déploiement.

## Réserves restantes (le dossier est conforme à l'addendum, sous ces réserves)

1. **Aucun usage variable** n'est classé dans l'audit 19 : distinguer une règle documentée d'un usage propre à une unité exige un expert du bord ; les règles dont la source est le brief du PO sont marquées « Hypothèse ».
2. **9 règles Marine sur 46 restent « non vérifié »** (réaffectation d'installation, fiches d'installation et flotte, essais après intervention, composition de la fraction de service, circuits des fiches, RETEX, relève, prêt à appareiller, vocabulaire du quart non demandé en développement) : vérifiables en technique, non rejouées ; elles ne sont pas réputées conformes.
3. **Sources publiques non consultées** : aucune vérification indépendante de la doctrine.
4. **Audit 20** : fidélité aux usages réels, Windows et comportement des dates relatives dans le temps non vérifiés ; la démonstration n'est pas modifiée (le complément est proposé : AUD-036).
5. Réserves externes déjà listées dans `09_BILAN_DES_AUDITS.md` (SIC, matériel, volumes réels).
