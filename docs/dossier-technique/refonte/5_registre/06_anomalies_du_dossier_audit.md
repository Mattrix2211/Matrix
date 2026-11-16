# Anomalies du dossier (audit)

> Une fiche par anomalie : constat, document et page, preuve, gravité, traitement prévu et statut sont séparés. Les niveaux de preuve [C] [N] [T] [V] [A] [R] [?] sont définis en début de registre.

## AUD-001 — L'en-tête de chaque page de l'ancien PDF portait une mention de large diffusion contradictoire avec la classification non validée

| Rubrique | Contenu |
|---|---|
| **Constat** | L'en-tête de chaque page dit [citation d'un document antérieur : « DIFFUSION GÉNÉRALE »] et le fichier s'appelle [citation du nom d'un fichier antérieur : « DIFFUSABLE »], alors que la couverture et le chapitre 3 disent que la classification n'est pas validée. La couverture annonce « Aucune référence de code » alors que le texte contient 39 chemins de fichiers `.py` (12 pages), 8 noms de branches internes `claude/…` (7 pages), 9 chemins `docs/…` |
| **Document et page concernés** | PDF [citation du nom d'un fichier antérieur : « diffusable »] |
| **Page, chapitre ou capture** | Couverture p.1 et en-tête des 108 pages |
| **Preuve** | [A][V] `pdf_controles.md` §3 ; p.1, 14, 20, 24 |
| **Conséquence pour le lecteur** | Le PDF peut être pris pour autorisé à la [ancienne mention de large diffusion] ; le critère de séparation annoncé n'est pas celui qui a été contrôlé (« fichier:ligne » seulement) |
| **Correction recommandée** | Remplacer l'en-tête par « DIFFUSION RESTREINTE PROVISOIRE — classification à valider » (comme le guide visuel) ; aligner la couverture sur la réalité ou retirer chemins et branches ; décision de l'autorité sur ce qu'est une « référence de code » |
| **Gravité** | Bloquante (diffusion) |
| **Priorité** | P0 |
| **Traitement prévu** | P0-1 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-002 — Impression de la feuille de service : le dossier la disait introuvable alors qu'un bouton « Imprimer » existe

| Rubrique | Contenu |
|---|---|
| **Constat** | « Le rendu imprimable de la feuille de service n'a pas été trouvé dans le code » ; A12 : « aucune page imprimable » — `matrix/templates/quarts/feuille_service_detail.html:18` contient un bouton « Imprimer » (`window.print()`, classe `no-print`) ; le guide visuel p.25 le montre |
| **Document et page concernés** | Chap. 8 §8.13 (l.184) ; registre A12 |
| **Preuve** | [C][N][V] |
| **Conséquence pour le lecteur** | Faux : une impression navigateur existe ; seules l'impression A4 dédiée et l'alerte de réimpression (DEC-FDS-04/06) manquent |
| **Correction recommandée** | Corriger §8.13 et A12 : « impression par le navigateur disponible ; mise en page A4 dédiée et alerte de réimpression non développées » |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-003 — Écrans décrits comme « non rejoués » alors que le guide visuel et l'audit les ont rejoués dans un navigateur

| Rubrique | Contenu |
|---|---|
| **Constat** | « Les écrans n'ont pas été rejoués dans un navigateur » (au moins 11 occurrences) — Le guide visuel (64 captures, 5 parcours) et cet audit ont rejoué ces écrans |
| **Document et page concernés** | Chap. 2, 6 (§6.11), 7, 9, 10, 11, 12, 15, 16, 17 ; annexe F ; compléments 11T, 12T, 15T… |
| **Preuve** | [?] grep ; [N] |
| **Conséquence pour le lecteur** | Contradiction entre documents : le lecteur ne sait pas si les écrans sont vérifiés. Les étiquettes ⚪ ne reflètent plus l'état de la preuve |
| **Correction recommandée** | Réviser ces phrases : « rejoué sur instance de démonstration le 12/11/2026 pour les écrans du guide visuel ; non rejoué pour … » |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-4 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-004 — Le premier chapitre promettait les rondes de contrôle, module retiré de l'interface

| Rubrique | Contenu |
|---|---|
| **Constat** | « Que dois-je faire ? → les tâches, la maintenance, les rondes de contrôle » — Le module `rondes` n'a aucune vue et a été retiré de l'interface (chap. 2, 12 ; A8 ; `rondes/models.py` seul) |
| **Document et page concernés** | Chap. 1 §1.1 (l.18) |
| **Preuve** | [C] `matrix/tests/test_module_rondes_retire.py` cité en 12T |
| **Conséquence pour le lecteur** | Le premier chapitre promet une fonction qui n'existe pas |
| **Correction recommandée** | Retirer les rondes de la réponse ou les marquer « retirées de l'interface » |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-005 — La barre de parcours du quotidien (Mon quotidien, Mon équipe, Suivi, Synthèse) n'est décrite nulle part

| Rubrique | Contenu |
|---|---|
| **Constat** | La page « Aujourd'hui » est décrite en blocs ; la barre de parcours du quotidien (« Mon quotidien · Mon équipe · Suivi · Synthèse ») n'est décrite nulle part (« Mon équipe » : 0 occurrence dans les chapitres [ancien qualificatif de large diffusion]) — `matrix/templates/components/parcours.html` ; visible sur toutes les captures d'accueil du guide |
| **Document et page concernés** | Chap. 6, 10, 17 |
| **Preuve** | [C][N][V] |
| **Conséquence pour le lecteur** | Un chef cherche « le bloc Supervision » ; il trouve des onglets qui ne portent pas ce nom. Le fil central de navigation du chef est absent |
| **Correction recommandée** | Documenter la barre (quatre vues, onglets réservés aux chefs, ce que contient chacun) au chapitre 6 et 17 |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-006 — Schémas : légende séparée de sa figure et schéma S10 illisible (5,0 pt)

| Rubrique | Contenu |
|---|---|
| **Constat** | Détection : légende dans les 6 % supérieurs de la page. S10 vu : illisible (5,0 pt), diagramme en pelote |
| **Document et page concernés** | PDF restreint p.4–5 ; PDF [ancien qualificatif de large diffusion] p.99–100 |
| **Page, chapitre ou capture** | Schéma S10 : image p.4, légende en haut de p.5 ; S40 idem |
| **Preuve** | [A][V] `schemas_lisibilite.csv` |
| **Conséquence pour le lecteur** | Légende séparée de sa figure ; S10 inutilisable à 100 % |
| **Correction recommandée** | Garder figure et légende ensemble (`break-inside: avoid`) ; relayouter S10 (deux schémas) |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-6 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-007 — Le bouton « Exécuter » est affiché sans droit d'exécution, mais c'est le serveur qui décide (refus 403)

| Rubrique | Contenu |
|---|---|
| **Constat** | « L'écran peut masquer un bouton, mais c'est toujours le serveur qui décide » — La liste de maintenance affiche « Exécuter » sur toutes les lignes pour un équipier ; `/maintenance/occurrences/4/execute/` répond 403 pour lui. Le guide p.13 montre ces boutons sans explication |
| **Document et page concernés** | Chap. 5 §5.4 ; guide visuel p.13 |
| **Preuve** | [N] `navigateur_droits.md` |
| **Conséquence pour le lecteur** | Le marin croit pouvoir exécuter des maintenances d'autrui ; le guide visuel risque de l'enseigner |
| **Correction recommandée** | Ajouter un constat au chapitre 12 ; nouvel écart candidat NE-01 (hors décision) ; annoter la capture p.13 du guide |
| **Gravité** | Majeure (précisée en phase 2 : le bouton « M'assigner » existe aussi dans la liste) |
| **Priorité** | P0 |
| **Traitement prévu** | P0-2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-008 — « Vérifié par test » : les fichiers de test n'étaient conservés dans aucun dépôt

| Rubrique | Contenu |
|---|---|
| **Constat** | « Vérifié par test (12/11/2026) » — Les fichiers de test ne sont dans aucun dépôt (rapport de qualification : « non conservés ») ; une copie est maintenant archivée dans `audit_preuves/tests_verification/` et relancée : 29 tests OK |
| **Document et page concernés** | Registre A14, A20, A25 ; chap. 6 §6.6, 6 §6.9, 12 ; `RAPPORT_QUALIFICATION_FINALE_G0.md` |
| **Preuve** | [T] `audit_preuves/tests_verification/` |
| **Conséquence pour le lecteur** | Une preuve non rejouable n'en est pas une pour un futur mainteneur |
| **Correction recommandée** | Citer ces fichiers dans le registre ; décider avec le PO s'ils entrent dans le dépôt applicatif (hors de cette mission) |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-5 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-009 — Pages portant 1 à 5 lignes, que le rapport de clôture disait absentes (fusionnée dans AUD-034)

| Rubrique | Contenu |
|---|---|
| **Constat** | Pages portant 1 à 5 lignes (« Limites », « Sources », une ligne de tableau) — `RAPPORT_CLOTURE_G0.md` §3 : « Pages quasi vides : Aucune dans les deux PDF » |
| **Document et page concernés** | PDF restreint p.39, 41, 45 ; [ancien qualificatif de large diffusion] p.14, 82, 93, 106 |
| **Preuve** | [A][V] `pdf_controles.md` §2 |
| **Conséquence pour le lecteur** | Impression d'inachevé ; le rapport de clôture est inexact sur ce point |
| **Correction recommandée** | Ne plus forcer un saut de page avant la dernière section des chapitres courts ; corriger le rapport |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | AUD-034 |
| **Statut** | fusionnée dans AUD-034 |

## AUD-010 — Rapport du guide visuel : « 25 captures non retenues » et lien de ligne des tickets, deux affirmations inexactes

| Rubrique | Contenu |
|---|---|
| **Constat** | §3 « 25 captures non retenues » ; §5 « la liste des tickets n'a pas de lien de ligne visible » — 29 captures non utilisées (64 − 35). Les lignes de tickets sont cliquables (`onclick`, `matrix/templates/logistics/ticket_list.html:28`) : ma capture automatique cherchait un lien `<a>` |
| **Document et page concernés** | `guide-visuel/RAPPORT_GUIDE_VISUEL_G0.md` |
| **Preuve** | [C][A] |
| **Conséquence pour le lecteur** | Erreurs de mon propre rapport |
| **Correction recommandée** | Corriger le rapport (affirmation retirée) |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-011 — Aucun document court pour un décideur

| Rubrique | Contenu |
|---|---|
| **Constat** | Aucun document court pour un décideur — Les PDF ne contiennent ni synthèse de 2 pages (valeur, maturité, limites, risques) ni lecture de la `SYNTHESE_ECARTS_PAR_CRITICITE.md` (fichier restreint hors PDF) |
| **Document et page concernés** | Ensemble |
| **Preuve** | [V] sommaires |
| **Conséquence pour le lecteur** | Le commandement doit lire 108 pages pour comprendre l'intérêt et les limites |
| **Correction recommandée** | Ajouter un « Résumé pour décideur » en tête du PDF [ancien qualificatif de large diffusion] (valeur, maturité par module, limites, décisions en attente) |
| **Gravité** | Majeure |
| **Priorité** | P1 |
| **Traitement prévu** | P1-1 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-012 — Sommaires sans numéros de page et deux parcours « marin » contradictoires dans les guides de lecture

| Rubrique | Contenu |
|---|---|
| **Constat** | Sommaires des deux PDF sans numéros de page ; `00_LISEZ-MOI.md` et `GUIDE_DE_LECTURE.md` indiquent deux parcours « marin » différents (ch. 1–2 contre ch. 1, 6, 8, 12 + annexe A) ; le guide visuel n'est cité ni dans le LISEZ-MOI, ni dans le guide de lecture, ni dans le chapitre 3 ; la numérotation saute de 17 à 25 sans explication dans le sommaire [ancien qualificatif de large diffusion] |
| **Document et page concernés** | Sommaires, guides |
| **Preuve** | [V] p.2 ; [A] grep |
| **Conséquence pour le lecteur** | Le lecteur retrouve difficilement l'information ; les trois documents ne forment pas un ensemble |
| **Correction recommandée** | Numéroter les sommaires ; un seul parcours par profil ; référencer le guide visuel ; expliquer la numérotation |
| **Gravité** | Majeure |
| **Priorité** | P1 |
| **Traitement prévu** | P0-4 / P1-2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-013 — 35 captures sur 64 utilisées : des écrans importants manquaient

| Rubrique | Contenu |
|---|---|
| **Constat** | 35 captures sur 64 utilisées — Écrans importants absents : accusé de réception d'une annonce, fiche d'installation (relevés, entretien), échange de tour, Documentation/RETEX, bas de l'accueil (indicateurs, bloc Supervision), prêt à appareiller avec session ouverte, vue mobile (le chapitre 17 en parle) |
| **Document et page concernés** | Guide visuel |
| **Preuve** | [V] `captures_audit.csv` |
| **Conséquence pour le lecteur** | Des parcours promis (annonces à accuser, RETEX) ne sont pas illustrés ; des doublons occupent la place de ces écrans |
| **Correction recommandée** | Ajouter 6 à 8 captures et en retirer 4 doublons |
| **Gravité** | Majeure |
| **Priorité** | P1 |
| **Traitement prévu** | P1-3 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-014 — Textes anglais du navigateur dans une interface française (dates, boutons de fichier, heures)

| Rubrique | Contenu |
|---|---|
| **Constat** | Textes anglais du navigateur dans une interface française : « mm/dd/yyyy », « Choose File / No file chosen », « 08:00 AM » |
| **Document et page concernés** | Guide visuel p.15, 19, 30 |
| **Preuve** | [V] captures `p_maintenance_1_saisie`, `p_anomalie_3_description`, `parametres` |
| **Conséquence pour le lecteur** | Le lecteur croit que Matrix affiche de l'anglais |
| **Correction recommandée** | Relancer Chromium en langue française |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-015 — Messages de confirmation superposés et mention « Brouillon abandonné » sur des captures

| Rubrique | Contenu |
|---|---|
| **Constat** | Messages de confirmation superposés, mention « Brouillon abandonné. » |
| **Document et page concernés** | Guide visuel p.11, 12, 17, 21, 22, 23 |
| **Preuve** | [V] |
| **Conséquence pour le lecteur** | Le regard est détourné ; une capture semi-transparente (p.23) |
| **Correction recommandée** | Attendre la disparition des messages avant capture ; abandonner le brouillon avant la session |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-016 — Captures en doublon exact ou quasi exact dans le guide visuel

| Rubrique | Contenu |
|---|---|
| **Constat** | 4 doublons exacts (`tache_detail`=`p_tache_1_ouverte`, `occurrences`=`p_maintenance_3_liste`, `execution_saisie`=`p_maintenance_1_saisie`) et 4 quasi-doublons |
| **Document et page concernés** | Captures sources |
| **Preuve** | [A] différence de pixels 0,0 à 4,6 % |
| **Conséquence pour le lecteur** | 21 Mo d'images dont une part redondante |
| **Correction recommandée** | Supprimer ou fusionner |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P1-3 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-017 — Formule répétée : « dans la partie restreinte du dossier et la partie restreinte du dossier »

| Rubrique | Contenu |
|---|---|
| **Constat** | « …dans la partie restreinte du dossier et la partie restreinte du dossier » |
| **Document et page concernés** | Chap. 5, en-tête (l.3) |
| **Preuve** | [V] p.21 ; [A] grep |
| **Conséquence pour le lecteur** | Faute visible dès la première page du chapitre le plus consulté |
| **Correction recommandée** | Corriger la phrase |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-018 — Identifiants coupés en milieu de mot dans les cellules des tableaux

| Rubrique | Contenu |
|---|---|
| **Constat** | Identifiants coupés en milieu de mot dans les cellules (« SynthesePassati / on », « ReferenceBatime / nt »), régression de la correction de l'ensemble précédent |
| **Document et page concernés** | PDF restreint p.4 |
| **Preuve** | [V] ; étendue non mesurée [?] |
| **Conséquence pour le lecteur** | Illisibilité des noms de modèles |
| **Correction recommandée** | Largeur minimale de colonne ou césure autorisée avant les parenthèses |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-019 — Le symbole ⚪ se rendait en petit cercle alors que 🟢, 🔵 et 🟣 sont des pastilles

| Rubrique | Contenu |
|---|---|
| **Constat** | Le symbole ⚪ se rend en petit cercle « ◦ » alors que 🟢🔵🟣 sont des pastilles |
| **Document et page concernés** | Deux PDF du dossier |
| **Preuve** | [V] p.1, 14, 82 |
| **Conséquence pour le lecteur** | La légende n'est pas reconnaissable |
| **Correction recommandée** | Même traitement que le guide visuel (pastille dessinée) |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-020 — Texte de schémas trop petit (5,8 à 6,2 pt) (fusionnée dans AUD-036)

| Rubrique | Contenu |
|---|---|
| **Constat** | S04, S13, S28 : 5,8 pt ; S09, S15 : 6,0 pt ; S01, S21 : 6,2 pt (libellés minimaux) ; S09 : flèches enchevêtrées |
| **Document et page concernés** | Schémas |
| **Preuve** | [A][V] `schemas_lisibilite.csv` |
| **Conséquence pour le lecteur** | Lecture pénible à 100 % ; S09/S13 « déjà signalés » restent petits |
| **Correction recommandée** | Relayouter ou doubler le corps de police ; S10 prioritaire (AUD-006) |
| **Gravité** | Mineure |
| **Priorité** | P1 |
| **Traitement prévu** | AUD-036 |
| **Statut** | fusionnée dans AUD-036 |

## AUD-021 — Trois chiffres différents pour le nombre de tests (≈ 3 950 fonctions, 3 963 tests)

| Rubrique | Contenu |
|---|---|
| **Constat** | « ≈ 3 950 fonctions de test » ; « 3 963 tests » |
| **Document et page concernés** | Chap. 24 §24.8 ; rapports |
| **Preuve** | Recomptage `def test_` indenté : 3 912 [C] ; 3 963 exécutés non rejoués [R] |
| **Conséquence pour le lecteur** | Trois chiffres différents pour une même notion |
| **Correction recommandée** | Un seul chiffre, avec méthode |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-022 — Recherche de personnes classée cible alors que la catégorie « Marins » existe

| Rubrique | Contenu |
|---|---|
| **Constat** | « Recherche de personnes » classée cible (DEC-UX-09 / PO-18) alors que la catégorie « Marins » existe (`matrix/core/recherche.py:193`, chap. 9 §77, captures p.8) |
| **Document et page concernés** | Chap. 6 §6.10, 9, 17 |
| **Preuve** | [C][N][V] |
| **Conséquence pour le lecteur** | Ambiguïté : existant ou cible ? |
| **Correction recommandée** | Préciser : « recherche par nom et grade existante ; informations professionnelles étendues : cible » |
| **Gravité** | Amélioration |
| **Priorité** | P1 |
| **Traitement prévu** | P1-6 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-023 — Les chapitres techniques renvoyaient à des chapitres absents du PDF restreint

| Rubrique | Contenu |
|---|---|
| **Constat** | Les chapitres techniques renvoient aux chapitres [ancien qualificatif de large diffusion] « à lire d'abord » mais le PDF restreint ne contient pas les chapitres 1 à 17 |
| **Document et page concernés** | PDF restreint |
| **Preuve** | [A] S02… absents de la liste des schémas ; [V] |
| **Conséquence pour le lecteur** | Le développeur doit détenir deux PDF ; l'ordre n'est dit nulle part sur la couverture |
| **Correction recommandée** | Dire sur la couverture et le sommaire que le PDF restreint complète le [ancien qualificatif de large diffusion] ; ou proposer une édition « intégrale » |
| **Gravité** | Amélioration |
| **Priorité** | P1 |
| **Traitement prévu** | P1-2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-024 — Pas de recette du premier jour pour un développeur ni de mise en garde sur la redirection HTTPS derrière un proxy

| Rubrique | Contenu |
|---|---|
| **Constat** | Pas de recette du premier jour pour un développeur (installer, lancer, tester, ajouter une action de seuil ou un module), pas de glossaire du code ; conséquence pratique de `SECURE_SSL_REDIRECT` sans `SECURE_PROXY_SSL_HEADER` non dite (risque de redirection en boucle derrière un proxy TLS [?]) |
| **Document et page concernés** | Chap. 23, 24 |
| **Preuve** | [C] `matrix/settings.py:422-424` ; plan des chapitres |
| **Conséquence pour le lecteur** | Reprise difficile sans l'auteur |
| **Correction recommandée** | Ajouter une « Prise en main développeur » d'une page et une « Recette de déploiement » |
| **Gravité** | Amélioration |
| **Priorité** | P1 |
| **Traitement prévu** | P1-4 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-025 — Écart A20 : le texte ne précisait pas que l'exécutant et le chef de section ne voient pas le bouton de correction

| Rubrique | Contenu |
|---|---|
| **Constat** | A20 : le texte dit « seul “Enregistrer la correction” est offert » sans préciser que l'exécutant et le chef de section ne voient pas ce bouton ; A14 : la raison de la non-capture (relève validée requise) est exacte mais non démontrée à l'écran |
| **Document et page concernés** | Guide visuel p.36–37 |
| **Preuve** | [N] `navigateur_droits.md` |
| **Conséquence pour le lecteur** | Lecture trop courte du circuit |
| **Correction recommandée** | Ajouter la phrase et une capture « profil équipier » |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P1-3 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-026 — Les décisions DEC-… renvoient à une branche et à Notion, non joignables depuis le dossier

| Rubrique | Contenu |
|---|---|
| **Constat** | Les `DEC-*` renvoient à une branche (`claude/eager-hopper-2cbcqh`) et à Notion, non joignables dans le dossier |
| **Document et page concernés** | Registre, chap. 5 |
| **Preuve** | [?] |
| **Conséquence pour le lecteur** | Un futur mainteneur ne peut pas retrouver la décision |
| **Correction recommandée** | Annexe « Décisions citées » avec texte et date, sans inventer |
| **Gravité** | Amélioration |
| **Priorité** | P1 |
| **Traitement prévu** | P1-6 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-027 — Lignes de la liste des tickets cliquables à la souris seulement, non accessibles au clavier

| Rubrique | Contenu |
|---|---|
| **Constat** | Les lignes de la liste de tickets sont cliquables par `onclick` seulement (non accessibles au clavier) |
| **Document et page concernés** | Chap. 11, 13, 15 (hors périmètre du dossier) |
| **Preuve** | [C] `matrix/templates/logistics/ticket_list.html:28` |
| **Conséquence pour le lecteur** | Accessibilité ; nouvel écart candidat NE-02 |
| **Correction recommandée** | Le noter dans les limites du chapitre 17 |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-028 — Rapports précédents aux chiffres d'origine contradictoires ; 11 fichiers de pilotage à la racine

| Rubrique | Contenu |
|---|---|
| **Constat** | Les rapports précédents conservent leurs chiffres d'origine (105/142 pages, 1 093 références) ; plusieurs rapports se contredisent légèrement ; 11 fichiers de pilotage à la racine du dossier pour 3 lecteurs |
| **Document et page concernés** | Annexe F, rapports E1–E4, BILAN |
| **Preuve** | [V] listing |
| **Conséquence pour le lecteur** | Bruit pour un nouveau lecteur |
| **Correction recommandée** | Ranger les rapports de livraison dans `rapports/` et ne garder à la racine que LISEZ-MOI, guide, synthèse |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-029 — Deux personnages différents portent le nom « Durand » dans le chapitre 6 ; noms des captures non repris

| Rubrique | Contenu |
|---|---|
| **Constat** | « Un exemple : le maître Durand » et le « matelot Durand » (chap. 6) sont des personnages différents sous le même nom ; « personnage fictif » non repris dans les captures (noms « Karim Equipier A ») |
| **Document et page concernés** | Chap. 5 |
| **Preuve** | [V] |
| **Conséquence pour le lecteur** | Deux jeux de personnages fictifs non reliés |
| **Correction recommandée** | Un seul fil rouge de personnages (ceux du guide visuel) |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-030 — Chemin erroné du scan web : « assets/scan/<uuid>/ » au lieu de « /scan/<uuid>/ »

| Rubrique | Contenu |
|---|---|
| **Constat** | « scan web `assets/scan/<uuid>/` » : le chemin réel est `/scan/<uuid>/` (`assets/web_urls.py:72` ; annexe C correcte) |
| **Document et page concernés** | Ch. 20 §20.5 |
| **Preuve** | [C] |
| **Conséquence pour le lecteur** | Voir le constat. |
| **Correction recommandée** | Corriger le chemin |
| **Gravité** | Mineure |
| **Priorité** | P0 (erreur factuelle) |
| **Traitement prévu** | P0-2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-031 — Annexe générée : lignes tronquées, fragments de tableau et symboles Markdown bruts

| Rubrique | Contenu |
|---|---|
| **Constat** | Annexe générée de 4 900 mots (79 % de l'annexe F) : lignes tronquées par « … » (« Une correcti… », « L… »), fragments de tableau (« / Tâches (ch. 10) / »), les astérisques et les accents graves bruts (p.130, 131, 134, 135), « ◦ ◦ » doublés, numérotation orpheline (« 2. L'API… »), et reprise d'énoncés périmés (« n'ont pas été rejoués ») |
| **Document et page concernés** | Annexe F §F.5, PDF restreint p.127–135 |
| **Preuve** | [V] p.127, 130, 131 |
| **Conséquence pour le lecteur** | Voir le constat. |
| **Correction recommandée** | Régénérer F.5 par chapitre sans tronquer, ou le remplacer par un tableau (chapitre, point, étiquette) |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-6 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-032 — Tableaux Markdown non rendus (barres verticales brutes) dans le PDF restreint

| Rubrique | Contenu |
|---|---|
| **Constat** | Tableaux Markdown non rendus : p.37 (« Routes web », source `restreint/13_logistique_technique.md:20-22`) et p.79 (§23.9, source `restreint/23_configuration_deploiement_exploitation.md:119-123`, tableau collé au paragraphe) apparaissent en barres verticales brutes |
| **Document et page concernés** | PDF restreint p.37 et p.79 |
| **Preuve** | [V][A] |
| **Conséquence pour le lecteur** | Voir le constat. |
| **Correction recommandée** | Ligne vide avant le tableau ; compléter l'en-tête |
| **Gravité** | Mineure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-6 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-033 — Des plages de décisions présentées comme « cible, non développée » alors que certaines sont réalisées

| Rubrique | Contenu |
|---|---|
| **Constat** | Des plages de décisions sont citées comme « cible, non développée » alors que certaines sont déjà réalisées : `DEC-PER-01` (tâches périodiques générées depuis les fiches) et `DEC-PER-04` (historiques conservés) vs `maintenance/tasks.py:66` et `OccurrenceStatusLog` ; `DEC-UX-01` (accueil) vs `aujourdhui.html`. Aucune phrase ne dit que 51 décisions sur 125 ne sont pas traitées |
| **Document et page concernés** | Ch. 6 §6.10, 12 (tableau cible), 17, 25 ; registre partie C |
| **Preuve** | [C] ; source v1.2 `A1_DECISIONS_S1_S2.md` |
| **Conséquence pour le lecteur** | Voir le constat. |
| **Correction recommandée** | Citer les décisions une à une avec état (réalisée, partielle, non développée) ; ne pas utiliser de plage |
| **Gravité** | Majeure |
| **Priorité** | P0 |
| **Traitement prévu** | P0-3 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-034 — Densité des pages : trop de pages remplies à moins de 70 % et compléments techniques répétitifs

| Rubrique | Contenu |
|---|---|
| **Constat** | Densité : 18 pages du [ancien qualificatif de large diffusion] et 26 du restreint sont remplies à moins de 70 % (11 et 15 à moins de 50 %) ; les compléments techniques (1 à 3 pages par chapitre) répètent chacun un cartouche de 5 lignes ; le restreint ne contient pas les chapitres de base qu'il complète ; 3 pages ≤ 5 lignes (p.39, 41, 45) |
| **Document et page concernés** | Deux PDF ; fusionne AUD-009 |
| **Preuve** | [A] `pages_remplissage.csv` ; [V] |
| **Conséquence pour le lecteur** | Voir le constat. |
| **Correction recommandée** | Voir §J (refonte de l'architecture) |
| **Gravité** | Majeure |
| **Priorité** | P1 (P0 pour les 3 pages) |
| **Traitement prévu** | P1-8 (architecture) |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-035 — Les schémas de circuit cible ne se distinguent pas des schémas de fonctionnement réel

| Rubrique | Contenu |
|---|---|
| **Constat** | Les schémas de circuit cible ne se distinguent pas des schémas de fonctionnement réel : seule la légende dit « cible » ; l'image seule (cadre, couleur, mention) est identique à S16, S20, S30, S32 |
| **Document et page concernés** | S17, S21, S31, S33 ([ancien qualificatif de large diffusion] p.42, 52, 80, 86) |
| **Preuve** | [V] |
| **Conséquence pour le lecteur** | Voir le constat. |
| **Correction recommandée** | Cadre pointillé bleu + mention « 🔵 CIBLE — non développé » dans l'image |
| **Gravité** | Majeure |
| **Priorité** | P0 (règle de distinction) |
| **Traitement prévu** | P0-7 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-036 — Qualité des 42 schémas : listes de cases sans information relationnelle, un schéma difficile, un illisible

| Rubrique | Contenu |
|---|---|
| **Constat** | Sur 42 schémas : 22 bons, 7 moyens, 10 faibles (listes de cases sans information relationnelle : S02, S14, S22, S24, S27, S36, S37, S38, S40, S42), 1 difficile (S09), 1 illisible (S10) ; S02 montre 6 groupes quand le tableau juste dessous en compte 11 |
| **Document et page concernés** | Schémas ; fusionne AUD-020 |
| **Preuve** | [V][A] `schemas_verdicts.csv` |
| **Conséquence pour le lecteur** | Voir le constat. |
| **Correction recommandée** | Remplacer les listes par des tableaux ; garder les schémas à circuit (S04, S05, S06, S07, S11, S12, S15, S16, S18, S20, S23, S25, S26, S29, S30, S32) |
| **Gravité** | Mineure |
| **Priorité** | P1 |
| **Traitement prévu** | P1-5 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-037 — Rubriques « bis » : traces d'édition d'insertions tardives

| Rubrique | Contenu |
|---|---|
| **Constat** | Rubriques « bis » : traces d'édition (insertions tardives) |
| **Document et page concernés** | Ch. 5 §5.4 bis, ch. 11 T2 bis, 12 T2 bis, 13 §13.9 bis |
| **Preuve** | [V] |
| **Conséquence pour le lecteur** | Voir le constat. |
| **Correction recommandée** | Renumérotation |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

## AUD-038 — Deux chiffres pour le même inventaire ; annexe F.4 datée de l'ensemble 4

| Rubrique | Contenu |
|---|---|
| **Constat** | Deux chiffres pour le même inventaire ; l'annexe F.4 est datée de l'ensemble 4 et n'est plus à jour (la branche compte d'autres commits) |
| **Document et page concernés** | Ch. 26 §26.4 (« 52 branches distantes ») et annexe F.4, p.125 (« 53 branches ») ; F.4 donne `f960c84` comme tête de la branche documentaire |
| **Preuve** | [V] p.125 ; [A] grep |
| **Conséquence pour le lecteur** | Voir le constat. |
| **Correction recommandée** | Un seul chiffre, avec date ; ne pas citer la tête d'une branche vivante |
| **Gravité** | Mineure |
| **Priorité** | P2 |
| **Traitement prévu** | P2 |
| **Statut** | ouverte — à traiter par la refonte |

