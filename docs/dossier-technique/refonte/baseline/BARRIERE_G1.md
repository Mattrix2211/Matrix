# Barrière G1 — Sources documentaires contrôlées

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Précaution documentaire, non une classification officielle. Date : 16/11/2026. Branche `claude/fervent-wright-kl6gtx`. Phases 4 à 9 du plan d'exécution (`PLAN_EXECUTION_REFONTE_G0.md`) terminées. **Aucun PDF de la révision 2 n'est construit** (phase 10 non engagée). Ce rapport ne vaut ni validation du logiciel Matrix ni autorisation de diffusion.

## 1. Verdict

Tous les contrôles automatiques applicables aux sources et aux aperçus HTML sont **verts : 0 bloquant, 0 avertissement non justifié**. Les contrôles qui portent sur les PDF (C8 mise en page, C10 inspection à taille réelle, C12 reproductibilité du texte extrait, mention sur chaque page) ne s'appliquent qu'après la phase 10.

Un contrôle automatique ne prouve pas l'exactitude métier : la relecture par le PO reste indispensable (voir §5, limites).

## 2. Inventaire des documents rédigés

| Document | Dossier source | Fichiers | Mots | Sections (niv. 1 / 2) | Pages de capture |
|---|---|---|---|---|---|
| Guide utilisateur illustré (GU) | `1_guide_utilisateur/` | 14 | 7 141 | 14 / 20 | 64 |
| Référentiel fonctionnel et de gouvernance (RF) | `2_referentiel_fonctionnel/` | 24 | 40 448 | 24 / 228 | — |
| Dossier technique de reprise (DT) | `3_dossier_technique/` | 25 | 25 082 | 25 / 174 | — |
| Registre des écarts et décisions (RE) | `5_registre/` | 7 | 13 276 | 7 / 87 | — |
| Annexes consultables (D4) | `4_annexes_consultables/` | `index.html` + 22 CSV + `LISEZ-MOI.txt` | 1 586 lignes de données | 22 tables | — |

Détail par fichier : `baseline/inventaire_g1_fichiers.md`. Point d'entrée : `README_DOSSIER.md`.

- **Captures (phase 4)** : 70 captures au manifeste (`captures/manifeste.json`) prises le 16/11/2026 sur une instance de démonstration isolée recréée de zéro depuis l'état B, données fictives, Chromium en français (date jj/mm/aaaa, « Choisir un fichier », heure 24 h : preuve `captures/_sonde_locale.png`). 2 vues de téléphone **émulées**, signalées comme telles ; 65 captures utilisées, 4 non utilisées (`p_anomalie_6_chef`, `p_anomalie_9_tickets`, `p_maintenance_3_liste`, `tache_detail`). Nouvelles captures : annonce à accuser, fiche d'installation, échange de tour (marin et chef), documentation, RETEX, bas de l'accueil et bloc Supervision, appareillage avec session ouverte, deux vues mobiles. Doublons exacts : 0 (empreintes SHA-256).
- **Guide utilisateur (phase 5)** : « Matrix en une page » ; profils ; parcours « ma journée », « annonces et recherche », « tâche », « tour de service » (échange, absences), « maintenance et anomalie » (chapitre pilote conservé, captures refaites), « appareillage » ; écrans de référence (matériel, installations, stock, supervision, compétences, programme) ; vues mobiles ; limites visibles ; glossaire et index.
- **Référentiel (phase 6)** : résumé pour le décideur ; « lire ce document » ; vision ; vue d'ensemble ; organisation ; rôles et autorisations ; **fiches de rôle** (neuf rôles + soutien à terre) ; **matrice des actions en libellés** ; 12 fiches de module (accueil, calendrier, quarts, communication, tâches, matériel, maintenance, logistique, formations, documentation et RETEX, appareillage, principes d'interface) avec écran de référence, écarts et décisions générés depuis le registre ; cible et feuille de route ; historique ; glossaire ; index des schémas.
- **Dossier technique (phase 7)** : « lire ce dossier technique » (identifiants de version) ; **prise en main développeur** (exécutée, journal `audit_preuves/prise_en_main_developpeur_journal.txt`) ; 14 chapitres de module ; architecture, données, API, interactions, sécurité, exploitation (avec **recette de déploiement**), qualité ; historique des branches ; annexes (totaux, méthode).
- **Annexes consultables (phase 8)** : `index.html` autonome (206 Ko) et 22 CSV : B1–B2 droits (clés de code), C1–C3 routes (185 + 171 + 365 = 721), D1 modèles (135), E1–E3 tâches, commandes, variables, F1–F5 sources, décisions citées, branches, **éléments non vérifiés refaits en tableau (189 passages ⚪ complets, sans troncature ni Markdown)**, G1–G7 couverture, H1 schémas (46).
- **Registre** : source unique `registre.json` ; AUD-001 : formulations historiques conservées comme **citations balisées de documents antérieurs** ; titres des 38 anomalies réécrits en phrases entières ; rubrique « Sources et preuves » ajoutée aux écarts.

## 3. Résultats des contrôles (aperçus HTML et sources)

Commande : `python3 refonte/outils/lancer_controles_sources.py` ; rapports dans `apercus_G1/`.

| Contrôle | Résultat |
|---|---|
| **C1** couverture du mapping | 507 titres de l'ancienne édition (hors schémas) : 507 couverts ou retirés avec motif, **0 orphelin** |
| **C2** étiquettes 🔵🟣⚪ | 0 étiquette changée ou promue ; 8 passages relus à la main et justifiés dans `config/revue_manuelle.yaml` (4 faux positifs lexicaux, 4 passages volontairement corrigés : AUD-002 et AUD-003) |
| **C3** faits chiffrés | 0 écart : chiffres injectés depuis `faits.yaml` (135 modèles, 721 routes, 20 tâches, 18 commandes, 35 actions, 14 modules, 190 migrations, 31 variables, 125 décisions) |
| **C4** références de code | `verifier_references_refonte.py` sur le dossier technique et le registre : **666 références de code vérifiées sur l'état B**, 35 preuves documentaires, 260 clés du registre, **0 erreur** |
| **C5** séparation et classification | Guide et référentiel : 0 chemin de code, 0 branche, 0 empreinte de version, 0 variable d'environnement, 0 port ; 0 occurrence des termes interdits hors citations balisées d'AUD-001 |
| **C6** renvois | 0 renvoi cassé (renvois résolus par fichier et numérotés à la construction) ; sommaire paginé : phase 10 |
| **C7** décisions | 0 plage « DEC-X à Y » ; tous les identifiants existent au registre |
| **C9** captures | 70/70 `ok`, statut HTTP 200, 6 assertions DOM vraies (dont NE-01 présent côté marin, bouton de correction présent côté chef de secteur et absent côté exécutant), 0 problème de langue, 0 motif sensible dans le texte capturé, 0 doublon. **Sonde réseau : 36 écrans chargés, 0 requête vers l'extérieur** |
| **C11** cohérence | 0 variante de terme interdite (une variante justifiée : libellé cible « Mes tours de services », DEC-UX-08) ; matrice des droits : 35 actions identiques entre le référentiel, les annexes et l'inventaire du code ; étiquetage de 14 identifiants comparé entre documents, 0 contradiction non justifiée (DEC-DRT-05 : partielle, justifiée) |
| **C13** application intacte | 0 fichier hors `docs/dossier-technique` modifié depuis `637de94` ; `main` distante inchangée (`6ef16adcfe8e`) |
| **C14** données sensibles | 0 adresse électronique, chemin absolu, jeton ou mot de passe de démonstration dans les sources, les manifestes et les annexes |
| **C12** reproductibilité | Aperçus HTML des quatre documents et annexes : deux constructions successives donnent des fichiers identiques (empreintes égales). Texte extrait des PDF : phase 10 |
| **Non-perte de contenu** (contrôle complémentaire) | 2 136 lignes substantielles des anciens chapitres examinées ; 138 non retrouvées telles quelles et toutes relues : 26 lignes du chapitre « Lire ce dossier » (réécrit, avec l'état et les identifiants de version déplacés dans le dossier technique), 76 lignes du chapitre pilote Maintenance (reformulées dans la maquette validée au jalon V1 ; deux omissions relevées et rétablies), 36 lignes modifiées par les transformations mécaniques (chapitres devenus renvois, clés de rôle devenues libellés, chiffres devenus faits) ; **aucune règle métier perdue constatée** |

Autres vérifications de phase :

| Barrière | Résultat |
|---|---|
| **G4** captures | 0 donnée réelle (jeu de données généré par les commandes de démonstration, identités fictives) ; tous les écrans en 200 ; langue française vérifiée par sonde ; manifeste avec profil, adresse finale, assertions |
| **G7** prise en main | 14 commandes exécutées dans une copie isolée de l'état B, toutes avec succès (code retour 0) ; journal archivé |
| **G8** annexes | Fichier autonome : 0 requête réseau (Playwright en mode hors ligne) ; filtre, tri et page des totaux opérationnels à 1366×768 et 1024×768 ; 6 totaux identiques à `faits.yaml` |

## 4. Écarts par rapport au plan initial

1. **Rédaction par réutilisation** : le référentiel et le dossier technique reprennent le texte validé de l'édition initiale (déplacement, tri, condensation, renvois résolus), comme le prévoit la parade du §11 du plan, plutôt qu'une réécriture intégrale. Seuls sont écrits à neuf : résumé du décideur, « lire ce document », fiches de rôle, matrice en libellés, prise en main, recette de déploiement, annexes, guide utilisateur (hors pilote).
2. **Fiches de rôle** : un tableau de 6 à 8 lignes par rôle (une demi-page environ), non une page pleine par rôle.
3. **Guide utilisateur** : 4 profils réunis dans une section au lieu d'une partie par profil ; les 9 parcours demandés sont présents (journée, annonce, recherche, tâche, maintenance, anomalie et ticket, tour de service, échange de tour, appareillage).
4. **Taille cible** : non mesurable avant la construction des PDF. Estimation sur les mots (≈ 450 mots par page de texte) : guide ≈ 64 pages de capture + ≈ 15 pages de texte (au-dessus de la cible 60 à 75) ; référentiel ≈ 90 à 100 pages (dans la cible) ; dossier technique ≈ 60 à 70 pages (en dessous de la cible 110 à 130, les annexes détaillées étant passées en D4) ; registre ≈ 55 à 65 pages (contrainte de pages levée par le PO).
5. **Contrôle C4 « ≥ 1 105 références »** : non comparable. L'ancien décompte portait sur toute l'édition initiale, y compris les annexes et les chapitres d'usage. À périmètre équivalent (chapitres techniques et registre), l'ancien dossier comptait 644 références de code et le nouveau en compte **666**, sans erreur.
6. **Ordre de rédaction** : référentiel, dossier technique et registre traités avant le guide (le guide cite des fiches existantes) ; le guide a été écrit en dernier, après la reprise des captures.
7. **Captures** : repères numérotés posés sur 8 captures seulement ; les autres sont légendées sans repère. 4 captures du manifeste ne sont pas utilisées.
8. **Corrections de statut du registre** : aucune. Les statuts des 125 décisions, des écarts, des propositions et des anomalies documentaires (AUD) sont inchangés ; les AUD traitées dans les sources seront requalifiées à la barrière G12 sur décision du PO.
9. **Outils ajoutés** (hors liste du plan) : convertisseur de chapitres, nettoyage des sources, rattrapage du préambule, résolution des anciens renvois, complément des fiches, contrôle de non-perte de contenu, inventaire, sonde réseau, vérification des annexes. Un défaut du convertisseur (texte situé avant le premier titre de niveau 2, perdu pour 4 chapitres techniques) a été détecté par le contrôle de non-perte et corrigé.

## 5. Anomalies et limites restantes

1. **Aucune inspection visuelle des PDF** (phase 11) : les aperçus HTML ne prouvent ni la pagination, ni les coupures de tableau, ni la lisibilité des schémas à taille réelle. La mise en page de 12 captures a été contrôlée dans le navigateur à titre d'essai ; le reste attend la phase 11.
2. **Parcours non rejoués** ⚪ : enchaînement complet d'une journée, signalement de blocage d'une tâche, renseignement des contrôles d'appareillage et signature, circuit de validation d'un RETEX, vues jour et semaine du calendrier, notifications poussées et courriel ; les écrans non capturés restent décrits d'après le code. Les limites sont dites dans chaque fiche.
3. **Vues de téléphone émulées** ⚪ : aucun appareil réel. Firefox, Safari, Windows et PostgreSQL non rejoués.
4. **Prise en main** : rejouée sous Python 3.13 et Linux ; les dépendances ne sont vérifiées qu'en simulation (écart `pywebpush` 2.5.0 installé pour 2.4.0 demandé) ; Redis, Celery, planificateur et suite complète de tests non rejoués.
5. **Recette de déploiement** : NE-03 (redirection HTTPS derrière un proxy) et NE-04 (QR et nom d'hôte) documentés comme ⚪ non testés ; sauvegarde et supervision à définir avec les SIC (A23, A24, D7).
6. **Fiches reprises du texte existant** : certaines formulations (par exemple « ensemble 3 », « tests rejoués avec l'ensemble 3 ») sont des traces de l'édition initiale ; le chapitre pilote Maintenance a été reformulé pour la maquette. À arbitrer à la relecture : 55 lignes reformulées du chapitre pilote ont été comparées une à une, deux omissions ont été rétablies.
7. **Statuts AUD** inchangés : AUD-001 est la seule anomalie dont le texte change (citations balisées). Les 38 titres sont réécrits ; aucune anomalie n'est marquée « traitée ».
8. **Identités des captures** : la liste blanche des identités fictives repose sur le jeu de données généré par les commandes de démonstration ; aucun contrôle ne compare chaque nom visible à la liste (le contrôle porte sur les adresses, jetons, chemins et mots de passe).
9. **Matrice de couverture (G6)** : conserve les numéros de chapitre de l'édition initiale (indiqué dans la table).
10. **Statuts AUD, états des décisions et classification** restent à valider par le PO ; la mention « DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE » est une précaution documentaire.

## 6. Décision demandée

La barrière G1 est atteinte : **aucune construction PDF n'a été faite**. Les phases 10 à 13 (construction candidate, inspection à taille réelle, corrections, basculement) ne sont **pas engagées** et attendent l'accord explicite du PO. Le budget de reconstruction (au plus 2 par document après la candidate) reste entier.
