# Rapport de livraison — Ensemble 3 (« Équipements, maintenance, savoir »)

> **Diffusion restreinte.** Date : 11/11/2026. Branche documentaire : `claude/fervent-wright-kl6gtx`. État du logiciel décrit : état B, `claude/l03-suppression-sure-v11` @ `6d6d0be`, **non fusionné dans `main`**.
> Aucun code applicatif modifié, aucune fusion dans `main`, aucune PR, aucun nouveau lot. Aucune décision du PO rouverte.

---

## 1. Demandes de revue de l'ensemble 2 : traitement

| Demande | Traitement |
|---|---|
| Valider la méthode de l'ensemble 2 | Reprise à l'identique (inventaire, références vérifiées, étiquettes 🟢/🔵/⚪, séparation actuel/cible) |
| Chapitre 8 : actuel et cible séparés, deux circuits, schémas, tableau comparatif | Conservé ; les décisions du PO restent la référence de la cible |
| Chapitre 5 : BSC et chef de liste | Deux paragraphes, tableau « Qui prépare, qui valide, qui autorise la publication » (feuille, liste de quarts, liste de services à quai, échange ; actuel et cible), section 5.4 bis complétée ; **aucun droit déduit du grade seul** |
| B1 à B8 | Partie B du registre refondue en **points à confirmer** : décision existante appliquée, sinon comportement vérifié conservé et règle cible marquée « à confirmer » |
| A11 à A14 | Restent au registre ; A12 (impression A4, réimpression versionnée) = cible ; A14 reformulé **non vérifié** (limite par section non démontrée) |

## 2. Chapitres rédigés (6 chapitres, 12 fichiers)

| Chapitre | Diffusable | Restreint |
|---|---|---|
| 11 — Matériel et installations | `diffusable/11_materiel_installations.md` | `restreint/11_materiel_installations_technique.md` |
| 12 — Maintenance, anomalies, tickets | `diffusable/12_maintenance_anomalies_tickets.md` | `restreint/12_…_technique.md` |
| 13 — Logistique | `diffusable/13_logistique.md` | `restreint/13_logistique_technique.md` |
| 14 — Formations et qualifications | `diffusable/14_formations.md` | `restreint/14_formations_technique.md` |
| 15 — Documentation et RETEX | `diffusable/15_documentation_retex.md` | `restreint/15_documentation_retex_technique.md` |
| 16 — Préparation à l'appareillage | `diffusable/16_preparation_appareillage.md` | `restreint/16_preparation_appareillage_technique.md` |

Chaque chapitre : marin d'abord, puis responsables ; circuits ; droits en tableau ; interactions ; cas particuliers ; cible séparée (🔵) ; limites ; sources. La page Notion « 03 — Formation, stages, CFPES, FPS et qualification opérationnelle » a été lue avant le chapitre 14 ; elle est traitée comme **état réel au 29/09/2026 + cible**, pas comme preuve du code.

## 3. Points d'attention demandés

- **Circuits de maintenance (ch. 11 et 12).** Du plan à l'exécution (S24), états (S25), verdict conforme / non conforme, **ticket automatique pour le matériel mobile seulement**, clôture d'une installation critique par **confirmation explicite** (le valideur est celui qui clôture, pas une seconde personne), correction avec conservation de la saisie d'origine, circuits de validation des fiches (bord et flotte, S23), ticket (S26) avec REX obligatoire à la clôture.
- **Gestion du matériel (ch. 11 et 13).** Deux familles (mobile / installation), catalogue de la flotte (S22), mouvements de stock immuables et justifiés (S27), alertes de pénurie.
- **Préparation à l'appareillage (ch. 16).** Actuel (S32) et cible (S33) séparés ; Matrix **ne délivre pas** l'autorisation d'appareiller (`DEC-APP-13`).

## 4. Schémas ajoutés (12, soit 33 au total)

S22 équiper depuis le catalogue ; S23 circuits des fiches ; S24 du plan à la réalisation ; S25 états d'une occurrence ; S26 ticket et anomalie ; S27 stock et pièces ; S28 circuits de formation A/B/C ; S29 versions de documents ; S30 RETEX réel ; S31 RETEX cible ; S32 appareillage réel ; S33 appareillage cible. Sources Mermaid conservées, exports SVG lisibles hors ligne ; S26, S28, S31, S32, S33 relus visuellement ; S28 corrigé après relecture (seuils conformes au code).

## 5. Couverture (matrice générée : `restreint/annexes/G_matrice_couverture.md`)

- **Modèles** : 135 sur 135 expliqués ou nommés dans un chapitre de domaine (les modèles secondaires de `assets`, `logistics` et `rondes` sont listés aux sections 11.T2 bis et 12.T2 bis).
- **Circuits** : 12 circuits de l'ensemble 3 (ticket et anomalie, exécution de maintenance, pièces et stock, fiches, catalogue, formation A/B/C, validation de formation, documentation, RETEX actuel et cible, appareillage actuel et cible) ; la matrice vérifie qu'une preuve de chaque circuit figure dans les chapitres.
- Restent pour l'ensemble 4 : chapitres 17, 20, 21, 23 à 26 et annexes C à H, PDF final.

## 6. Contradictions et écarts (détail : `restreint/ECARTS_DECISIONS_CODE.md`, partie A quater)

| # | Sujet | Nature |
|---|---|---|
| A15 | RETEX en une étape (tout habilité) contre circuit hiérarchique et correction motivée (`DEC-RTX-01` à `03`) | Écart d'implémentation (L11) |
| A16 | Diffusion « flotte » sans transmission à l'organisme | Écart ; qui transmet : à confirmer |
| A17 | Appareillage : une signature, pas de fiche de référence ni de classification, contre `DEC-APP-02`, `DEC-APP-10` à `12`, `DEC-APP-14` | Écart d'implémentation (L23, compatibilité avec les procédures du bord à confirmer) |
| A18 | Transfert de matériel sans circuit (`DEC-MAT-01` à `04`) | Cible non développée (L13) |
| A19 | Demande de places : l'organisme est une unité École ou Centre de formation ; pas de dossier vivant, ni timeline, ni transmission formalisée | Écart avec la cible Notion « 03 » (corrigé en E4) |
| A20 | État « En validation » sans sortie trouvée | **Non vérifié** |
| A21 | Périodicités nommées, outillage, durée | Cible non développée |

Observations de lecture, sans écart : une demande de places est ouverte dès **chef de section** (la note Notion parle de chef de secteur) ; les habilitations exigées bloquent un **échange de tour** mais jamais une tâche ordinaire (`DEC-QUA-01` à `04`) ; aucune décision V1.2 ne concerne le stock ni la commande de pièces.

## 7. Éléments non vérifiés (⚪)

- Sortie de l'état « En validation » (A20).
- Notifications (push, e-mail), PDF, écrans : non rejoués dans un navigateur ni sur PostgreSQL ou Windows.
- Couverture de tests très faible pour `documentation` (9 fonctions) et `retex` (5 fonctions) : les règles décrites reposent surtout sur la lecture du code.
- Précision affichée à l'écran de signature d'appareillage ; lien entre mode MER/QUAI et préparation ; libellés et validités des qualifications fines (`IM-01`).
- Rôle exact de l'« organisme » de formation et de l'organisme destinataire du RETEX.

## 8. Contrôles documentaires

| Contrôle | Résultat |
|---|---|
| Références de code vérifiées sur l'état B (fichier, ligne, symbole) | **671 contrôlées, 0 erreur** |
| Cohérence (structure, étiquettes, liens, schémas, chiffres, mentions interdites) | **35 fichiers, 33 schémas, 0 erreur** |
| Identifiants `DEC-…` | Vérifiés contre le registre V1.2 (aucun identifiant inventé ; deux placeholders détectés à la relecture et corrigés) |
| Matrice de couverture | Régénérée ; tous les circuits E3 « rédigés » |

### 8.1 Tests rejoués sur l'état B

`python manage.py test assets maintenance logistics training documentation retex dashboard` : **1 491 tests, OK (1 ignoré)**. La suite complète (3 963 tests) n'a pas été rejouée : ses chiffres viennent des comptes rendus de lots.

## 9. Pour la revue

1. Valider la méthode et les circuits de l'ensemble 3 (pas une relecture ligne à ligne).
2. Trancher, si vous le souhaitez, les points « à confirmer » nouveaux : qui transmet un RETEX à l'organisme ; autorité cible de la classification « critique » des contrôles d'appareillage ; ticket automatique pour une installation non conforme.
3. Autoriser l'ensemble 4 (chapitres 17, 20, 21, 23 à 26, annexes C à H, PDF).
