# Audit global du dossier technique G0 — phases 1 et 2

> **Diffusion restreinte.** Date : 12/11/2026. Branche : `claude/fervent-wright-kl6gtx`. Référence applicative : état B (`6d6d0be`, non fusionné dans `main`), relu sur une extraction propre du commit (`git archive`) et rejoué sur une copie isolée avec comptes fictifs.
> **Nature du document** : audit, pas correction. Aucun PDF, aucun chapitre, aucun code applicatif n'a été modifié. Seuls ce rapport et le dossier `audit_preuves/` sont ajoutés.
> **Ce rapport ne valide rien.** Il distingue validation documentaire, validation logicielle et autorisation de diffusion (voir §F).
> **Portée réelle** : phase 1 (échantillon) puis **phase 2 (reprise des points du §0.3)**. L'audit n'est toujours **pas exhaustif mot à mot** ; la couverture exacte est au §0.2 et au §G. **Statut : audit achevé, en attente de validation PO** ; aucune correction n'est lancée.

---

## 0. Ce qui a été fait, et ce qui ne l'a pas été

### 0.1 Niveaux de preuve utilisés
| Sigle | Signification |
|---|---|
| **[C]** | Vérifié par lecture du code de l'état B |
| **[N]** | Vérifié dans le navigateur (instance isolée, comptes fictifs) |
| **[T]** | Vérifié par test exécuté pendant l'audit |
| **[V]** | Vérifié visuellement (page de PDF ou capture regardée) |
| **[A]** | Mesure automatique (texte du PDF, pixels, SVG) |
| **[R]** | Simplement rapporté par une source antérieure |
| **[?]** | Non vérifié |

### 0.2 Couverture réelle
| Élément | Couverture | Détail |
|---|---|---|
| Chiffres clés (modèles, routes, migrations, tâches, paquets, actions, commandes) | **Complète** [C][T] | 135 modèles, 721 routes (185 + 171 API + 365 admin), 190 migrations, 20 tâches Celery Beat, 22 paquets, registre de 35 actions, 18 commandes, 14 modules : **tous exacts** |
| Registre des écarts A1–A26 | **Lu à 70 %** [C] | A1 à A21 relus ; A14, A20, A25 rejoués par test [T] ; A22 à A26 et partie B relues, vérifications code sur A1, A6, A9, A12, A13, A22, A23, A24 |
| Chapitres diffusables | **Lus en entier : 6 ; en partie : 1, 2, 3, 5, 8, 12, 16, 17 ; non lus ligne à ligne : 4, 7, 9, 10, 11, 13, 14, 15, 25, 26** | Les affirmations précises des chapitres non lus ont été recoupées par recherche ciblée (§C.1) |
| Chapitres restreints et compléments | **Lus : 11T, 12T, 23 (en partie), 22 (en partie), 18 (plan)** ; autres non relus | |
| Annexes | B, C : en-têtes et totaux [C] ; D, E, F, G : non relues | |
| PDF diffusable (108 p.) | **108/108 pages vues** (phase 1 : 9 ; phase 2 : 99, en paires de pages à 80 dpi) + mesures automatiques | §D, §G.2 |
| PDF restreint (143 p.) | **108/143 pages vues** (phase 1 : 13 ; phase 2 : 95) ; **25 des 55 pages paysage** ; 35 pages non vues listées au §G.2 | Aucune page vue à 100 % : résolution de 78 à 110 dpi |
| Guide visuel (39 p.) | **39 pages vues à ~90 dpi** | Dont 7 revues après la dernière régénération |
| 64 captures | **64 vues** (planches 683 px puis pages du guide) [V] | Table complète : `audit_preuves/captures_audit.csv` |
| 42 schémas | **42 mesurés** [A] ; **S09, S10, S11, S13 vus dans le PDF** [V] | |
| Parcours rejoués dans le navigateur | Droits par profil (5 profils × 16 adresses), A20, tentative A14, exécution de maintenance | `audit_preuves/navigateur_droits.md` |

**Aucune page n'a été inspectée à 100 %** (taille réelle de l'écran) : la résolution maximale est 110 dpi, la plupart à 78–80 dpi. **35 pages du PDF restreint n'ont pas été vues** (§G.2) : l'inspection n'est donc **pas complète**. Elle suffit pour juger la structure, la densité, les schémas et les défauts visibles, pas pour une relecture mot à mot.

### 0.3 Points de reprise de la phase 1 — état après la phase 2
| # | Point | État |
|---|---|---|
| 1 | Relire les chapitres diffusables 4, 7, 9, 10, 11, 13, 14, 15, 25, 26 et recouper leurs affirmations | **Fait par recoupement ciblé** (toutes les affirmations chiffrées ou normatives, pas la lecture de chaque phrase) : voir §G.1 |
| 2 | Relire compléments 5T à 10T, 13T à 17T, chap. 19 à 21, 24, annexes D à G | **Fait en partie** : pages vues, 27/27 références symbole↔ligne recoupées, 31/31 variables d'environnement, 135 modèles ; annexes C/D non recoupées ligne à ligne |
| 3 | Inspecter les ~190 pages restantes à 100 % | **Fait à ~80–110 dpi pour 108/108 pages du diffusable et 108/143 du restreint** (35 pages du restreint non vues, listées au §G.2) ; **pas à 100 %** |
| 4 | Rejouer relève A/B → passation dans le navigateur | **Fait** (§G.3) |
| 5 | Vérifier les `DEC-*` contre leurs sources | **Fait** : la branche `claude/eager-hopper-2cbcqh` est accessible (§G.4) |

---

## A. Synthèse exécutive

### A.1 État général
Le dossier est **sérieux, honnête sur ses limites et factuellement fiable dans ce qui a été recoupé** : tous les chiffres vérifiés sont exacts, les références de code recoupées disent bien ce que le texte prétend, la distinction 🟢🔵🟣⚪ est tenue, et le registre d'écarts distingue la règle validée, le comportement constaté, les conséquences et le lot prévu sans présenter une solution non arbitrée comme définitive. Les écarts A14, A20, A25 se **rejouent** (29 tests OK).

Mais il ne se lit pas comme une documentation professionnelle de référence : il se lit comme une **compilation rigoureuse de rapports**. Cinq défauts pèsent le plus :
1. une **étiquette de diffusion contradictoire** dans le PDF « diffusable » ;
2. **trois erreurs factuelles** que seule une vérification dans le navigateur a révélées (impression de la feuille de service, rondes, barre de parcours du quotidien) ;
3. une **contradiction entre documents** : au moins onze endroits disent que les écrans n'ont « pas été rejoués dans un navigateur » alors que le guide visuel les montre ;
4. des **défauts de mise en page** non détectés par les contrôles précédents (légendes séparées, pages presque vides, schéma S10 illisible), alors que le rapport de clôture les déclarait absents ;
5. une **navigation pauvre** : sommaires sans numéro de page, guide visuel non référencé, deux « parcours marin » différents, aucune synthèse pour un décideur dans les PDF.

### A.2 Principales qualités
- Exactitude chiffrée (inventaire généré depuis le code).
- Discipline des étiquettes et du vocabulaire « cible / actuel ».
- Registre d'écarts structuré (règle, constat, sources, conséquences, lot).
- Honnêteté sur ce qui n'existe pas (sauvegarde, journalisation, limitation de connexions, HSTS : tous confirmés absents) [C].
- Mise en page typographique propre des chapitres courants (tableaux à en-tête répétée, hiérarchie claire).
- Le guide visuel apporte une valeur réelle : 5 parcours rejoués sur l'application.

### A.3 Principales faiblesses
Voir le tableau §B : **1 bloquante** (pour la diffusion), **12 majeures**, **12 mineures**, **4 améliorations**.

### A.4 Niveau de confiance
| Domaine | Confiance | Pourquoi |
|---|---|---|
| Chiffres, structure du code, droits par rôle (échantillon) | **Élevée** | recoupés [C][N][T] |
| Registre A1–A26 | **Élevée** pour A1, A2, A3, A6, A9, A12 (partiel), A13, A14, A20, A22–A25 | recoupés ; **A12 est partiellement faux** (AUD-002) |
| Comportements d'écran décrits dans les chapitres | **Moyenne** | décrits « d'après le code » ; trois erreurs trouvées sur un échantillon limité : le taux d'erreur réel est probablement non nul sur les chapitres non rejoués |
| Présentation PDF | **Moyenne à faible** | défauts non détectés par les contrôles automatiques précédents |
| Décisions du PO (`DEC-*`) | **Non vérifiée** [R] | source hors de portée |

### A.5 Aptitude à servir de référence documentaire
**Pas encore, mais proche pour le contenu.** Après correction des points P0 (§E), le dossier serait une référence solide pour le développeur et le responsable métier. Pour le marin et le décideur, il faudra des documents d'entrée (P1) : le dossier actuel suppose que le lecteur sait déjà où aller.

---

## B. Tableau des anomalies

Gravités : **bloquante** (empêche la validation ou crée un risque de diffusion non autorisée), **majeure** (erreur factuelle, contradiction, défaut de lecture sérieux), **mineure**, **amélioration**. Preuves : voir §0.1. Les fichiers de preuve sont dans `audit_preuves/`.

| ID | Gravité | Document | Où | Constat précis | Preuve | Conséquence pour le lecteur | Correction recommandée | Prio |
|---|---|---|---|---|---|---|---|---|
| AUD-001 | **Bloquante** (diffusion) | PDF diffusable | Couverture p.1 et en-tête des 108 pages | L'en-tête de **chaque page** dit « DIFFUSION GÉNÉRALE » et le fichier s'appelle « DIFFUSABLE », alors que la couverture et le chapitre 3 disent que la classification n'est pas validée. La couverture annonce « **Aucune référence de code** » alors que le texte contient **39 chemins de fichiers `.py` (12 pages), 8 noms de branches internes `claude/…` (7 pages), 9 chemins `docs/…`** | [A][V] `pdf_controles.md` §3 ; p.1, 14, 20, 24 | Le PDF peut être pris pour autorisé à la diffusion générale ; le critère de séparation annoncé n'est pas celui qui a été contrôlé (« fichier:ligne » seulement) | Remplacer l'en-tête par « DIFFUSION RESTREINTE PROVISOIRE — classification à valider » (comme le guide visuel) ; aligner la couverture sur la réalité ou retirer chemins et branches ; décision de l'autorité sur ce qu'est une « référence de code » | **P0** |
| AUD-002 | Majeure | Chap. 8 §8.13 (l.184) ; registre A12 | « Le rendu imprimable de la feuille de service n'a pas été trouvé dans le code » ; A12 : « aucune page imprimable » | `matrix/templates/quarts/feuille_service_detail.html:18` contient un bouton **« Imprimer »** (`window.print()`, classe `no-print`) ; le guide visuel p.25 le montre | [C][N][V] | Faux : une impression navigateur existe ; seules l'impression A4 dédiée et l'alerte de réimpression (DEC-FDS-04/06) manquent | Corriger §8.13 et A12 : « impression par le navigateur disponible ; mise en page A4 dédiée et alerte de réimpression non développées » | **P0** |
| AUD-003 | Majeure | Chap. 2, 6 (§6.11), 7, 9, 10, 11, 12, 15, 16, 17 ; annexe F ; compléments 11T, 12T, 15T… | « Les écrans n'ont pas été rejoués dans un navigateur » (au moins 11 occurrences) | Le guide visuel (64 captures, 5 parcours) et cet audit ont rejoué ces écrans | [?] grep ; [N] | Contradiction entre documents : le lecteur ne sait pas si les écrans sont vérifiés. Les étiquettes ⚪ ne reflètent plus l'état de la preuve | Réviser ces phrases : « rejoué sur instance de démonstration le 12/11/2026 pour les écrans du guide visuel ; non rejoué pour … » | **P0** |
| AUD-004 | Majeure | Chap. 1 §1.1 (l.18) | « Que dois-je faire ? → les tâches, la maintenance, **les rondes de contrôle** » | Le module `rondes` n'a **aucune vue** et a été retiré de l'interface (chap. 2, 12 ; A8 ; `rondes/models.py` seul) | [C] `matrix/tests/test_module_rondes_retire.py` cité en 12T | Le premier chapitre promet une fonction qui n'existe pas | Retirer les rondes de la réponse ou les marquer « retirées de l'interface » | **P0** |
| AUD-005 | Majeure | Chap. 6, 10, 17 | La page « Aujourd'hui » est décrite en blocs ; la **barre de parcours du quotidien** (« Mon quotidien · Mon équipe · Suivi · Synthèse ») n'est décrite nulle part (« Mon équipe » : 0 occurrence dans les chapitres diffusables) | `matrix/templates/components/parcours.html` ; visible sur toutes les captures d'accueil du guide | [C][N][V] | Un chef cherche « le bloc Supervision » ; il trouve des onglets qui ne portent pas ce nom. Le fil central de navigation du chef est absent | Documenter la barre (quatre vues, onglets réservés aux chefs, ce que contient chacun) au chapitre 6 et 17 | **P0** |
| AUD-006 | Majeure | PDF restreint p.4–5 ; PDF diffusable p.99–100 | Schéma S10 : image p.4, légende en haut de p.5 ; S40 idem | Détection : légende dans les 6 % supérieurs de la page. S10 vu : illisible (**5,0 pt**), diagramme en pelote | [A][V] `schemas_lisibilite.csv` | Légende séparée de sa figure ; S10 inutilisable à 100 % | Garder figure et légende ensemble (`break-inside: avoid`) ; relayouter S10 (deux schémas) | **P0** |
| AUD-007 | Majeure (précisée en phase 2 : le bouton « M'assigner » existe aussi dans la liste) | Chap. 5 §5.4 ; guide visuel p.13 | « L'écran peut masquer un bouton, mais c'est toujours le serveur qui décide » | La liste de maintenance affiche **« Exécuter » sur toutes les lignes** pour un équipier ; `/maintenance/occurrences/4/execute/` répond **403** pour lui. Le guide p.13 montre ces boutons sans explication | [N] `navigateur_droits.md` | Le marin croit pouvoir exécuter des maintenances d'autrui ; le guide visuel risque de l'enseigner | Ajouter un constat au chapitre 12 ; **nouvel écart candidat NE-01** (hors décision) ; annoter la capture p.13 du guide | **P0** |
| AUD-008 | Majeure | Registre A14, A20, A25 ; chap. 6 §6.6, 6 §6.9, 12 ; `RAPPORT_QUALIFICATION_FINALE_G0.md` | « Vérifié par test (12/11/2026) » | Les fichiers de test ne sont dans **aucun dépôt** (rapport de qualification : « non conservés ») ; une copie est maintenant archivée dans `audit_preuves/tests_verification/` et **relancée : 29 tests OK** | [T] `audit_preuves/tests_verification/` | Une preuve non rejouable n'en est pas une pour un futur mainteneur | Citer ces fichiers dans le registre ; décider avec le PO s'ils entrent dans le dépôt applicatif (hors de cette mission) | **P0** |
| AUD-009 | Majeure | PDF restreint p.39, 41, 45 ; diffusable p.14, 82, 93, 106 | Pages portant 1 à 5 lignes (« Limites », « Sources », une ligne de tableau) | `RAPPORT_CLOTURE_G0.md` §3 : « Pages quasi vides : **Aucune** dans les deux PDF » | [A][V] `pdf_controles.md` §2 | Impression d'inachevé ; le rapport de clôture est inexact sur ce point | Ne plus forcer un saut de page avant la dernière section des chapitres courts ; corriger le rapport | **P0** |
| AUD-010 | Majeure | `guide-visuel/RAPPORT_GUIDE_VISUEL_G0.md` | §3 « 25 captures non retenues » ; §5 « la liste des tickets n'a pas de lien de ligne visible » | **29** captures non utilisées (64 − 35). Les lignes de tickets **sont cliquables** (`onclick`, `ticket_list.html:28`) : ma capture automatique cherchait un lien `<a>` | [C][A] | Erreurs de mon propre rapport | Corriger le rapport (affirmation retirée) | **P0** |
| AUD-011 | Majeure | Ensemble | Aucun document court pour un décideur | Les PDF ne contiennent ni synthèse de 2 pages (valeur, maturité, limites, risques) ni lecture de la `SYNTHESE_ECARTS_PAR_CRITICITE.md` (fichier restreint hors PDF) | [V] sommaires | Le commandement doit lire 108 pages pour comprendre l'intérêt et les limites | Ajouter un « Résumé pour décideur » en tête du PDF diffusable (valeur, maturité par module, limites, décisions en attente) | P1 |
| AUD-012 | Majeure | Sommaires, guides | Sommaires des deux PDF **sans numéros de page** ; `00_LISEZ-MOI.md` et `GUIDE_DE_LECTURE.md` indiquent deux parcours « marin » différents (ch. 1–2 contre ch. 1, 6, 8, 12 + annexe A) ; **le guide visuel n'est cité ni dans le LISEZ-MOI, ni dans le guide de lecture, ni dans le chapitre 3** ; la numérotation saute de 17 à 25 sans explication dans le sommaire diffusable | [V] p.2 ; [A] grep | Le lecteur retrouve difficilement l'information ; les trois documents ne forment pas un ensemble | Numéroter les sommaires ; un seul parcours par profil ; référencer le guide visuel ; expliquer la numérotation | P1 |
| AUD-013 | Majeure | Guide visuel | 35 captures sur 64 utilisées | **Écrans importants absents** : accusé de réception d'une annonce, fiche d'installation (relevés, entretien), échange de tour, Documentation/RETEX, bas de l'accueil (indicateurs, bloc Supervision), prêt à appareiller avec session ouverte, vue mobile (le chapitre 17 en parle) | [V] `captures_audit.csv` | Des parcours promis (annonces à accuser, RETEX) ne sont pas illustrés ; des doublons occupent la place de ces écrans | Ajouter 6 à 8 captures et en retirer 4 doublons | P1 |
| AUD-014 | Mineure | Guide visuel p.15, 19, 30 | Textes anglais du navigateur dans une interface française : « mm/dd/yyyy », « Choose File / No file chosen », « 08:00 AM » | [V] captures `p_maintenance_1_saisie`, `p_anomalie_3_description`, `parametres` | Le lecteur croit que Matrix affiche de l'anglais | Relancer Chromium en langue française | P2 |
| AUD-015 | Mineure | Guide visuel p.11, 12, 17, 21, 22, 23 | Messages de confirmation superposés, mention « Brouillon abandonné. » | [V] | Le regard est détourné ; une capture semi-transparente (p.23) | Attendre la disparition des messages avant capture ; abandonner le brouillon avant la session | P2 |
| AUD-016 | Mineure | Captures sources | 4 doublons exacts (`tache_detail`=`p_tache_1_ouverte`, `occurrences`=`p_maintenance_3_liste`, `execution_saisie`=`p_maintenance_1_saisie`) et 4 quasi-doublons | [A] différence de pixels 0,0 à 4,6 % | 21 Mo d'images dont une part redondante | Supprimer ou fusionner | P2 |
| AUD-017 | Mineure | Chap. 5, en-tête (l.3) | « …dans la partie restreinte du dossier et la partie restreinte du dossier » | [V] p.21 ; [A] grep | Faute visible dès la première page du chapitre le plus consulté | Corriger la phrase | P2 |
| AUD-018 | Mineure | PDF restreint p.4 | Identifiants coupés en milieu de mot dans les cellules (« SynthesePassati / on », « ReferenceBatime / nt »), régression de la correction de l'ensemble précédent | [V] ; étendue non mesurée [?] | Illisibilité des noms de modèles | Largeur minimale de colonne ou césure autorisée avant les parenthèses | P2 |
| AUD-019 | Mineure | Deux PDF du dossier | Le symbole ⚪ se rend en petit cercle « ◦ » alors que 🟢🔵🟣 sont des pastilles | [V] p.1, 14, 82 | La légende n'est pas reconnaissable | Même traitement que le guide visuel (pastille dessinée) | P2 |
| AUD-020 | Mineure | Schémas | S04, S13, S28 : 5,8 pt ; S09, S15 : 6,0 pt ; S01, S21 : 6,2 pt (libellés minimaux) ; S09 : flèches enchevêtrées | [A][V] `schemas_lisibilite.csv` | Lecture pénible à 100 % ; S09/S13 « déjà signalés » restent petits | Relayouter ou doubler le corps de police ; S10 prioritaire (AUD-006) | P1 |
| AUD-021 | Mineure | Chap. 24 §24.8 ; rapports | « ≈ 3 950 fonctions de test » ; « 3 963 tests » | Recomptage `def test_` indenté : **3 912** [C] ; 3 963 exécutés non rejoués [R] | Trois chiffres différents pour une même notion | Un seul chiffre, avec méthode | P2 |
| AUD-022 | Amélioration | Chap. 6 §6.10, 9, 17 | « Recherche de personnes » classée cible (DEC-UX-09 / PO-18) alors que la catégorie **« Marins » existe** (`recherche.py:193`, chap. 9 §77, captures p.8) | [C][N][V] | Ambiguïté : existant ou cible ? | Préciser : « recherche par nom et grade existante ; informations professionnelles étendues : cible » | P1 |
| AUD-023 | Amélioration | PDF restreint | Les chapitres techniques renvoient aux chapitres diffusables « à lire d'abord » mais le PDF restreint **ne contient pas les chapitres 1 à 17** | [A] S02… absents de la liste des schémas ; [V] | Le développeur doit détenir deux PDF ; l'ordre n'est dit nulle part sur la couverture | Dire sur la couverture et le sommaire que le PDF restreint complète le diffusable ; ou proposer une édition « intégrale » | P1 |
| AUD-024 | Amélioration | Chap. 23, 24 | Pas de **recette du premier jour** pour un développeur (installer, lancer, tester, ajouter une action de seuil ou un module), pas de glossaire du code ; conséquence pratique de `SECURE_SSL_REDIRECT` sans `SECURE_PROXY_SSL_HEADER` non dite (risque de redirection en boucle derrière un proxy TLS [?]) | [C] `settings.py:422-424` ; plan des chapitres | Reprise difficile sans l'auteur | Ajouter une « Prise en main développeur » d'une page et une « Recette de déploiement » | P1 |
| AUD-025 | Mineure | Guide visuel p.36–37 | A20 : le texte dit « seul “Enregistrer la correction” est offert » sans préciser que l'exécutant et le chef de section ne voient pas ce bouton ; A14 : la raison de la non-capture (relève validée requise) est exacte mais non démontrée à l'écran | [N] `navigateur_droits.md` | Lecture trop courte du circuit | Ajouter la phrase et une capture « profil équipier » | P2 |
| AUD-026 | Amélioration | Registre, chap. 5 | Les `DEC-*` renvoient à une branche (`claude/eager-hopper-2cbcqh`) et à Notion, non joignables dans le dossier | [?] | Un futur mainteneur ne peut pas retrouver la décision | Annexe « Décisions citées » avec texte et date, sans inventer | P1 |
| AUD-027 | Mineure | Chap. 11, 13, 15 (hors périmètre du dossier) | Les lignes de la liste de tickets sont cliquables par `onclick` seulement (non accessibles au clavier) | [C] `ticket_list.html:28` | Accessibilité ; **nouvel écart candidat NE-02** | Le noter dans les limites du chapitre 17 | P2 |
| AUD-028 | Mineure | Annexe F, rapports E1–E4, BILAN | Les rapports précédents conservent leurs chiffres d'origine (105/142 pages, 1 093 références) ; plusieurs rapports se contredisent légèrement ; 11 fichiers de pilotage à la racine du dossier pour 3 lecteurs | [V] listing | Bruit pour un nouveau lecteur | Ranger les rapports de livraison dans `rapports/` et ne garder à la racine que LISEZ-MOI, guide, synthèse | P2 |
| AUD-029 | Mineure | Chap. 5 | « Un exemple : le maître Durand » et le « matelot Durand » (chap. 6) sont des personnages différents sous le même nom ; « personnage fictif » non repris dans les captures (noms « Karim Equipier A ») | [V] | Deux jeux de personnages fictifs non reliés | Un seul fil rouge de personnages (ceux du guide visuel) | P2 |

**Nouveaux écarts candidats (non décidés, à faire arbitrer, aucune règle inventée)**
- **NE-01** 🟢 [N] : la liste de maintenance propose « Exécuter » à qui le serveur refuse (403).
- **NE-02** 🟢 [C] : lignes de tickets cliquables sans lien ni focus clavier.
- **NE-03** ⚪ [?] : `SECURE_SSL_REDIRECT` actif en production sans réglage de proxy inverse : comportement derrière un proxy TLS non testé.

---

## C. Analyse détaillée par domaine

### C.1 Fonctionnel et métier
**Ce qui a été confronté** (chapitre → code ou navigateur) :

| Chapitre | Affirmation | Résultat |
|---|---|---|
| 5 | 9 rôles, niveaux 1 à 9 | ✔ [C] `matrix/core/roles.py` |
| 5 | Registre de 35 actions ; seuils par défaut (matériel : chef de section ; suppression : chef de service ; correction de CR : chef de secteur ; annonce : chef de service ; module : commandant en second ; mot de passe : admin d'unité) | ✔ [C] `role_thresholds.py` |
| 5 | Mot de passe provisoire de 14 caractères ; identifiant `prenom.nom` accents retirés | ✔ [C] `accounts/services.py:13`, `web_views.py:420` |
| 5, 6, 17 | Accès par rôle à Vue flotte, Vue COMANAV, plan du navire, modules, annuaire | ✔ [N] tableau `navigateur_droits.md` |
| 6 | « Passation activée par défaut », lecteurs, génération manuelle | ✔ [C][N] ; génération manuelle **refusée sans relève validée** |
| 6 | 261 fonctions de test `dashboard` | ✔ [C] |
| 8 | Alertes d'activation : rappel 30 min, alerte à l'heure, escalade 15 min, réglables | ✔ [C] `quarts/models.py:2266-2268` |
| 8 | Feuille de service : impression « non trouvée » | ✘ **faux** (AUD-002) |
| 12 | Occurrences générées sur 90 jours ; ticket automatique gravité 3, une fois par occurrence, matériel mobile seulement ; retard calculé sur PLANNED/ASSIGNED | ✔ [C] `maintenance/tasks.py`, `models.py:213-235` |
| 12 | A20 : sorties de « En validation » ; correction réservée chef de secteur et plus | ✔ [T][N] |
| 6 | Écart A14 : un chef de section lit tout le bâtiment | ✔ [T] (8 tests) ; **non rejoué en navigateur** (AUD-008) |
| 2 | 14 modules activables, 18 commandes, 20 tâches, 22 paquets | ✔ [C] |
| 1 | Rondes de contrôle comme fonction | ✘ **faux** (AUD-004) |
| 6 | Structure de l'accueil | **Incomplète** : barre de parcours absente (AUD-005) |
| 16 | « Prêt à appareiller » ouvert à tout marin ; ouverture et signature réservées | ✔ [N] (menu pour l'équipier, bouton « Ouvrir une session » pour le chef de service) |

**Fonctionnalités présentées comme opérationnelles alors qu'incomplètes** : aucune trouvée sur l'échantillon, hormis AUD-004 (rondes).
**Fonctionnalités existantes insuffisamment documentées** : barre de parcours (AUD-005), impression de la feuille (AUD-002), catégorie « Marins » de la recherche (AUD-022), alerte rouge de retard en tête de l'accueil du chef (visible sur les captures du chef, non décrite au chapitre 6 §6.3), boutons « Mouvements du bâtiment » et « Délais d'alerte » (concepts décrits, libellés absents du dossier).

**Revue du registre A1–A26** (critères demandés) :

| Critère | Résultat |
|---|---|
| Problème décrit correctement | ✔ pour A1–A4, A6, A9, A13, A14, A20, A22–A25 [C] ; **A12 inexact** (AUD-002) |
| Conséquences expliquées | ✔ : colonne « Conséquences » avec volet fonctionnel et sécurité pour A1 à A4 ; plus brève pour A5 à A13 |
| **Utilisateurs concernés identifiés** | **Partiel** : il n'y a pas de colonne « profils concernés » ; ils se déduisent du texte (ex. A14 : chef de section ; A20 : chef de secteur, exécutant). Recommandation P1 |
| Faits vérifiés / hypothèses séparés | ✔ (étiquettes, « confirmé par test », « à confirmer ») |
| Solution non arbitrée présentée comme définitive | **Non** : la règle « validée » est celle du PO ; les lots sont « non lancés » ; la partie B porte les points à confirmer (B1 suppléance, B2 commandant en second…) |
| Gravité | Portée par `SYNTHESE_ECARTS_PAR_CRITICITE.md` (hors PDF) |

Rien n'indique que le registre « transforme une proposition en décision ». Le seul point d'attention est la phrase du chapitre 12 sur le ticket de suivi d'une installation non conforme : correctement marquée 🟣 « proposition à valider par le PO ».

### C.2 Technique et maintenabilité
- **Architecture, modèles, routes** : fiables [C]. L'annexe C est cohérente avec le total de 721 routes (185 + 171 + 365).
- **Sécurité (chap. 22)** : les constats d'absence (journalisation, HSTS, limitation de tentatives, proxy) sont exacts [C] ; l'ordre des middlewares (p.67) est cohérent avec `settings.py:115-135` à une simplification près (le tableau omet `MessageMiddleware` et `CommonMiddleware`).
- **Exploitation (chap. 23)** : honnête sur l'absence de sauvegarde, de restauration et de journalisation ; elle ne donne cependant **aucune recette** à appliquer en attendant les SIC (AUD-024).
- **Celery/Redis** : décrits exactement (`CELERY_BROKER_URL` par défaut sur Redis ; `start.bat` ne lance pas le worker si Redis est absent) [C]. L'effet d'une perte de Redis reste ⚪ non testé (déjà dit).
- **Preuves de test** : voir AUD-008 ; le chiffre du nombre de tests varie (AUD-021).
- **Reprise sans l'auteur** : le dossier décrit *ce qui est*, pas *comment faire* (AUD-024). Les `DEC-*` renvoient à des sources externes au dossier (AUD-026).
- **Références de code** : une référence valide peut cautionner un énoncé faux (AUD-002 en est un exemple : les références de l'ensemble 2 concernaient l'absence d'une vue imprimable dédiée, pas du bouton du gabarit).

### C.3 Visuel (PDF et guide)
Voir §D. Défauts : AUD-006, 009, 014 à 016, 018 à 020.

### C.4 Pédagogique
Voir §E.1 et §F. Défauts : AUD-005, 011, 012, 013, 022, 023, 024, 029.
Points de contenu à améliorer :
- **Là où une capture serait plus utile qu'un paragraphe** : ch. 6 §6.2 (description des cinq blocs : renvoyer à la figure 5 du guide) ; ch. 8 §8.4 (feuille de service et son circuit : renvoyer à la page 25 du guide) ; ch. 12 §12.2 (exécution guidée : renvoyer aux pages 13–16) ; ch. 17 (menu : page 4 du guide).
- **Là où le schéma est meilleur que la capture** : circuits de validation (S06, S23, S25), relève (S08 restreint), cartes de dépendances (S09) : à conserver.
- **Termes métier** : COMAEQ, COMOPS, COMANAV, COMAVIA, BSC, DEC-*, lots Lnn sont définis au glossaire (annexe A) mais apparaissent sans rappel dans les chapitres 5, 6, 8 ; un chapitre de vocabulaire en tête de partie éviterait de basculer vers l'annexe (p.102).
- **Répétitions** : l'avertissement « n'est pas une autorisation de diffusion » et le rappel de l'état B (6d6d0be, non fusionné) figurent dans chaque en-tête de chapitre ; utile pour un extrait lu seul, lourd à la lecture continue.

### C.5 Sécurité (du dossier et de l'application, au regard de ce qui a été vu)
- Le dossier **ne cache pas** les lacunes de sécurité (A23, A24, A14, A1).
- **Cohérence d'étiquetage** : AUD-001 (en-tête « DIFFUSION GÉNÉRALE »).
- Aucune donnée réelle repérée : texte extrait du guide et des 64 captures sans adresse électronique, nom réel ou mot de passe [A][V] ; mot de passe de démonstration absent du dépôt [A].
- Les comptes fictifs affichent des identifiants de connexion (`equipier_a`, `equipier_a2`) dans les listes de maintenance : sans risque ici, à surveiller si une capture était un jour faite sur une autre instance.

### C.6 Cohérence documentaire (trois PDF et sources)
| Point | Verdict |
|---|---|
| Terminologie (COMAEQ, états B, étiquettes) | ✔ cohérente |
| Statut d'une fonction (tableau chapitre 5 / guide visuel) | ✔ sauf AUD-002, 004, 007 |
| Écrans « non rejoués » | ✘ contradiction (AUD-003) |
| Classification | ✘ en-tête « générale » (diffusable) / « restreinte » (restreint) / « restreinte provisoire » (guide) : trois formulations (AUD-001) |
| Renvois de pages du guide de lecture | ✔ **vérifiés** : chapitres 3, 5, 6, 8, 12, 14, 15, 16, 25, 26, 18–24, registre, annexes B, C, E, F, G tous aux pages annoncées [A] |
| Liens Markdown internes | ✔ 0 lien cassé [A] |
| Guide visuel dans l'arborescence | ✘ non référencé (AUD-012) |
| Rapports de livraison | Plusieurs chiffres historiques non alignés (AUD-028) |

---

## D. Évaluation des trois PDF

**Méthode** : voir §0.2 et `audit_preuves/pdf_controles.md`. Notes sur 10, critères : contenu (3), lisibilité (2), navigation (2), cohérence graphique (1), conformité aux consignes d'étiquetage (2).

### D.1 PDF diffusable — **6,5 / 10**
- **Contenu 2,5/3** : fiable, étiqueté, mais trois erreurs (AUD-002, 004, 005).
- **Lisibilité 1,5/2** : texte courant très lisible (vu p.21–22) ; schémas S04, S13, S28 petits ; sept pages presque vides.
- **Navigation 0,5/2** : sommaire sans numéros de page, pas d'index, numérotation 17 → 25 inexpliquée.
- **Graphique 0,5/1** : sobre, cohérent, couverture austère sans date ni version.
- **Étiquetage 1,5/2** : ⚪ illisible ; en-tête contradictoire (AUD-001).
Points retirés : navigation (1,5), en-tête et chemins (0,5), pages vides et schémas (1), erreurs (0,5).

### D.2 PDF restreint — **6,5 / 10**
- **Contenu 3/3** : dense, précis, honnête (registre, annexes générées).
- **Lisibilité 1/2** : tableaux paysage à environ 6 pt (vus p.88–89 : lisibles mais serrés), S10 illisible, identifiants coupés, trois pages presque vides, légende séparée.
- **Navigation 0,5/2** : même sommaire sans pages ; chapitres techniques sans les chapitres de base (AUD-023).
- **Graphique 0,5/1.**
- **Étiquetage 1,5/2.**
Points retirés : navigation (1,5), lisibilité (1), graphique (0,5), étiquetage (0,5).
*Limite* : 13 pages vues sur 143, dont 2 paysage ; 55 pages paysage non revues individuellement.

### D.3 Guide visuel — **7 / 10**
- **Contenu 2,5/3** : parcours réels, légendes, profil, limites ; manques (AUD-013), erreur de rapport (AUD-010).
- **Lisibilité 2/2** : une capture de 247 mm de large par page ; texte d'interface de 6 à 8 pt.
- **Navigation 1/2** : sommaire paginé ; non relié au dossier (AUD-012).
- **Graphique 1/1.**
- **Étiquetage 1/2** : ⚪ correct, mention « provisoire » exemplaire ; légendes parfois trop brèves sur le droit (AUD-025), artefacts anglais, messages parasites (AUD-014, 015).
Points retirés : manques (0,5), navigation (1), étiquetage (1), capture trompeuse p.13 (0,5).
*Inspection* : 39 pages vues à ~90 dpi.

---

## E. Plan d'amélioration (aucune correction faite)

### E.1 Évaluation par profil de lecteur
| Profil | Note | Critères (sur 2 points chacun) | Points retirés |
|---|---|---|---|
| **Marin utilisateur** | **6,5 / 10** | Comprendre Matrix 1,5 ; usage quotidien illustré 1,5 ; langage 1,5 ; retrouver l'information 0,5 ; limites visibles 1,5 | Navigation inexistante pour le marin (le guide de lecture est un fichier restreint) ; jargon (« seuils », « DEC-… », « paquets ») dans les chapitres 5 et 6 ; rondes (AUD-004) ; annonce à accuser non illustrée |
| **Responsable métier** | **6,5 / 10** | Circuits 1,7 ; responsabilités 1,5 ; visuels 1 ; décisions en attente 1 ; fiabilité 1,3 | Pas de « fiche rôle » d'une page ; peu de captures côté responsable (4 pages) ; synthèse des écarts en fichier restreint ; AUD-005 |
| **Commandement / décideur** | **5 / 10** | Intérêt compris vite 1 ; maturité et limites 1,5 ; risques visibles 1 ; densité 0,5 ; confiance 1 | Aucune synthèse de 2 pages ; 108 + 143 pages ; risques de sécurité seulement dans le PDF restreint |
| **Développeur / mainteneur** | **7 / 10** | Architecture 1,8 ; données et routes 1,8 ; lacunes honnêtes 1,7 ; prise en main 0,8 ; lisibilité 0,9 | Pas de recette du premier jour ; preuves non versionnées (AUD-008) ; DEC-* non joignables ; S10 ; tableaux coupés |

### E.2 Recommandations

**P0 — Indispensable avant validation documentaire** (effort total estimé : 1 à 2 jours, sans développement)

| # | Action | Anomalies | Effort | Dépendances |
|---|---|---|---|---|
| P0-1 | Harmoniser l'étiquetage de classification sur les trois PDF (en-tête, couverture) ; décider avec l'autorité du statut des chemins de fichiers et noms de branches dans le diffusable | AUD-001 | 0,5 j | Décision de l'autorité (non mienne) |
| P0-2 | Corriger les trois erreurs factuelles (impression de la feuille, rondes, barre de parcours) et ajouter le constat NE-01 | AUD-002, 004, 005, 007 | 0,5 j | — |
| P0-3 | Mettre à jour les phrases « non rejoué dans un navigateur » ; référencer le guide visuel | AUD-003, 012 (partie) | 0,5 j | AUD-002/004/005 |
| P0-4 | Légende de S10 et S40 ; relayouter S10 | AUD-006 | 0,5 j | Régénération PDF |
| P0-5 | Citer les fichiers de preuve A14/A20/A25 dans le registre | AUD-008 | 0,25 j | Décision PO sur leur sort |
| P0-6 | Supprimer les pages presque vides ; corriger le rapport de clôture | AUD-009 | 0,5 j | Régénération PDF |
| P0-7 | Corriger `RAPPORT_GUIDE_VISUEL_G0.md` | AUD-010 | 0,1 j | — |

**P1 — Améliorations importantes**
| # | Action | Anomalies | Effort | Dépendances |
|---|---|---|---|---|
| P1-1 | Résumé pour décideur (2 pages) et « fiche rôle » pour le responsable | AUD-011 | 1 j | validation du ton par le PO |
| P1-2 | Sommaires paginés ; un parcours par profil ; expliquer la numérotation | AUD-012, 023 | 0,5 j | P0-3 |
| P1-3 | Compléter le guide visuel : 6 à 8 captures (annonce accusée, installation, échange de tour, Documentation/RETEX, bas d'accueil, mobile) ; retirer les doublons | AUD-013, 016 | 1 j | instance de démonstration |
| P1-4 | Prise en main développeur et recette de déploiement | AUD-024 | 1 j | — |
| P1-5 | Relayouter les schémas ≤ 6,2 pt | AUD-020 | 1 j | — |
| P1-6 | Préciser « recherche de personnes » (existant / cible) ; annexe des `DEC-*` | AUD-022, 026 | 0,5 j | accès aux sources |
| P1-7 | Colonne « profils concernés » dans le registre | §C.1 | 0,5 j | — |
| P1-8 | Phase 2 de l'audit (§0.3) | — | 2 à 3 j | — |

**P2 — Finitions**
Anglais dans les captures (AUD-014), messages parasites (015), doublons (016), faute du chapitre 5 (017), identifiants coupés (018), symbole ⚪ (019), chiffres de tests (021), compléments A20 (025), accessibilité (027), rangement des rapports (028), personnages fictifs (029). Effort global : 1 j.

---

## F. Conclusion

### Recommandation (phase 1, remplacée par le §L) : **corrections indispensables avant validation documentaire**, limitées aux sept actions P0 initiales (la liste P0 consolidée est au §K).
Elles ne remettent pas en cause la structure ni le fond du dossier ; elles corrigent trois erreurs, une contradiction, une étiquette de classification et des défauts de mise en page que les contrôles précédents n'avaient pas vus. Après P0, la recommandation deviendrait **validable avec réserves** (réserves : P1 et phase 2 de l'audit).

### Trois validations à ne pas confondre
| Validation | État après cet audit |
|---|---|
| **Documentaire** (le dossier décrit fidèlement l'état B) | **Non prononcée** : corrections P0 puis relecture du PO |
| **Logicielle** (l'état B est apte à l'usage) | **Hors de cette mission** ; les écarts A1–A26 et NE-01 à NE-03 restent à arbitrer ; la suite complète de 3 963 tests n'a pas été rejouée |
| **Autorisation de diffusion** | **Non accordée** : la mention « diffusable » d'un nom de fichier n'en est pas une ; l'en-tête « DIFFUSION GÉNÉRALE » (AUD-001) doit être corrigé avant toute lecture hors de l'équipe |

### Ce que cet audit ne permet pas d'affirmer
- Que les chapitres non relus ne contiennent pas d'erreur du même type que AUD-002, 004, 005 (trois erreurs sur environ un tiers du texte relu : un risque réel).
- Que les ~190 pages non vues des PDF sont exemptes de défauts de mise en page.
- Que la règle A14 se reproduit dans le navigateur (testée seulement par test unitaire).
- La véracité des décisions du PO citées (`DEC-*`).

*Aucune correction n'est commencée. J'attends la validation de ce rapport.*

---
---

# PARTIE II — Phase 2 (reprise exhaustive des points du §0.3)

> Date : 12/11/2026. Mêmes contraintes : aucune modification du code, des PDF ni des chapitres. Preuves ajoutées dans `audit_preuves/`.

## G. Couverture exacte de la phase 2

### G.1 Lecture des chapitres et annexes (confrontation au code de l'état B)
| Élément | Méthode | Résultat |
|---|---|---|
| Ch. 4 (organisation) | Lecture intégrale + code : 14 modules, 3 types d'unité, message de lecture seule, `org/archivage.py` absent de `main` | **Exact** [C] |
| Ch. 6, 7 | Lecture intégrale ; iCal (`calendar_app/ical_views.py`) : 401 anonyme, tâches et programme absents ; 9 sources | **Exact** [C] |
| Ch. 9, 10, 11, 13, 14, 15 | **Toutes les affirmations chiffrées ou normatives** recoupées (grep ciblé + code) : niveau Urgent seul pousse (`NotificationLevel.DANGER`), 72 h, 365 jours de validité, vibration 180 j, mouvements de stock immuables (`logistics/models.py:259-265`), deux priorités de tâche, 10/7/94/41 tests par paquet, domaines RETEX | **Exactes** [C] ; lecture phrase à phrase **non faite** [?] |
| Ch. 16 | Parcours rejoué dans le navigateur : équipier sans bouton, chef de secteur ouvre une session (10 points, 0/10, « Valider et clôturer »), pas de seconde ouverture | **Exact** [N] |
| Ch. 25, 26 | 24 empreintes de commit citées : **24/24 résolues** ; 127 commits entre A et B ; schémas S38/S39 non revérifiés contre le plan en 28 lots | Exact pour les commits [C] ; S38/S39 [?] |
| Compléments 4T à 12T, 17T | Pages vues ; 27/27 références `symbole`↔`ligne` des compléments 6T, 7T, 11T recoupées | **Exactes** [C][V] |
| Ch. 18 à 24 | Pages vues ; 135 modèles ; 448 relations (PROTECT 115, SET_NULL 216, CASCADE 102, M2M 15) ; 15 signaux ; 20 tâches planifiées ; 12 champs UUID ; 21 applications | **Exacts** [C] ; 3 erreurs documentaires mineures (AUD-030, 037 et liste de tests AUD-021) |
| Annexe E | 31/31 variables d'environnement et 18 commandes confrontées à `settings.py` | **Exactes** [C] |
| Annexes B, C, D, G | Pages vues ; totaux (721 routes, 135 modèles, 35 actions) exacts ; lignes non recoupées une à une | Totaux [C] ; détail [V] |
| Annexe F §F.5 | Pages 127–135 vues | **Défauts de génération** (AUD-031) |
| Chap. 1, 2, 3, 5, 8, 12, 17 | Recoupement ciblé de ce qui est vérifiable dans le navigateur (droits par profil, tâche personnelle, assignation) | Exact sauf AUD-002, 004, 005 (phase 1) |

### G.2 Inspection des PDF (aucune page à 100 %)
| PDF | Pages vues | Résolution | Pages non vues |
|---|---|---|---|
| Diffusable (108) | **108** | 80 dpi (paires), 62–110 dpi en phase 1 | aucune |
| Restreint (143, dont 55 paysage) | **108** (dont 25 paysage) | 78–90 dpi | **35 pages** : 69, 70, 73, 74, 92, 93, 96, 97, 100, 101, 104–107, 110–113, 116, 117, 120, 121, 124, 125, 128, 129, 132–135, 138–141, 143 (corps des annexes C, D, E, F, G : tableaux générés) |
| Guide visuel (39) | 39 (phase 1) | ~90 dpi | aucune |
Mesure automatique complémentaire : taux de remplissage de **chaque** page (`audit_preuves/pages_remplissage.csv`).

### G.3 Parcours rejoués dans le navigateur (instance isolée, comptes fictifs)
| Parcours | Résultat | Preuve |
|---|---|---|
| **Relève A→B puis passation** | `cdt_a` propose ; `cdt_b` valide ; la synthèse `/dashboard/passation/1/` est créée automatiquement. Avant relève : « Aucune relève validée… rien à passer » | `scripts_navigateur/rel2.js`, `rel3.js` |
| **A14 en navigateur** | `chef_section_a` (équipage sortant, désormais à terre) **200**, lit « Tâches ouvertes et bloquées : 28 » dont **12 sur 28 appartiennent à d'autres sections ou à aucune** ; `chef_secteur_a`, `chef_service_a`, `cdt_b` 200 ; `equipier_a` **404** ; `cdt_abe` (autre bâtiment) **404** | `a14_navigateur_chef_section.png`, `a14_text.txt` |
| Tâche personnelle non partagée (ch. 5, 10) | Case « partagée » décochée par défaut ; chef de section, de secteur, de service et commandant : **404** | `priv2.js` |
| Appareillage | Voir G.1 | `app.js`, `appareillage_session_ouverte.png` |
| « M'assigner » | Présent sur les occurrences non assignées ; les non assignées exposent aussi « Exécuter » (403 à l'ouverture) | `assign.js` |
| Synthèse du chef de section | Aucun bloc « Supervision » sur l'accueil d'un chef de section (conforme ch. 6 §6.3 : seuil chef de secteur) ; charge par marin et « échéances pendant une absence » présentes | `syn.js` |

### G.4 Vérification des décisions `DEC-*`
- La branche `claude/eager-hopper-2cbcqh` (dossier V1.2) est **accessible** : 125 décisions, **toutes « Confirmée PO »** à la source (`audit_preuves/decisions_dec_verification.csv`).
- **74 identifiants distincts** sont cités dans les chapitres et annexes ; **tous existent** à la source et **aucun n'est cité avec un statut supérieur à celui de la source**. 12 énoncés comparés mot à mot au texte source (FDS-04/06/07/14, DRT-02, TAC-04/05, RTX-01, UX-08, SUP-01, PRE-02/03/04, APP-14, MAT-01, PER-01, OUT-03) : **conformes**.
- **51 décisions sur 125 ne sont jamais citées** (ANO-02 à 05, DUR-02 à 07, MUT-02 à 05, SUP-03/06, UX-02/03/07/10…) : le dossier ne revendique pas de couverture complète des décisions ; ce n'est pas écrit explicitement (AUD-033).
- **La validité des décisions elles-mêmes** (Notion, PO) reste **non vérifiable** [?].

## H. Anomalies nouvelles de la phase 2

| ID | Gravité | Nature | Document / lieu | Constat | Preuve | Correction recommandée | Prio |
|---|---|---|---|---|---|---|---|
| AUD-030 | Mineure | Doc. | Ch. 20 §20.5 | « scan web `assets/scan/<uuid>/` » : le chemin réel est `/scan/<uuid>/` (`assets/web_urls.py:72` ; annexe C correcte) | [C] | Corriger le chemin | P0 (erreur factuelle) |
| AUD-031 | Majeure | Doc. + présentation | Annexe F §F.5, PDF restreint p.127–135 | Annexe **générée** de 4 900 mots (79 % de l'annexe F) : lignes tronquées par « … » (« Une correcti… », « L… »), fragments de tableau (« \| Tâches (ch. 10) \| »), `**` et `` ` `` bruts (p.130, 131, 134, 135), « ◦ ◦ » doublés, numérotation orpheline (« 2. L'API… »), et reprise d'énoncés **périmés** (« n'ont pas été rejoués ») | [V] p.127, 130, 131 | Régénérer F.5 par chapitre sans tronquer, ou le remplacer par un tableau (chapitre, point, étiquette) | P0 |
| AUD-032 | Mineure | Présentation | PDF restreint p.37 et p.79 | Tableaux Markdown **non rendus** : p.37 (« Routes web », source `restreint/13_logistique_technique.md:20-22`) et p.79 (§23.9, source `23_configuration_deploiement_exploitation.md:119-123`, tableau collé au paragraphe) apparaissent en barres verticales brutes | [V][A] | Ligne vide avant le tableau ; compléter l'en-tête | P0 |
| AUD-033 | Majeure | Doc. | Ch. 6 §6.10, 12 (tableau cible), 17, 25 ; registre partie C | Des **plages** de décisions sont citées comme « cible, non développée » alors que certaines sont déjà réalisées : `DEC-PER-01` (tâches périodiques générées depuis les fiches) et `DEC-PER-04` (historiques conservés) vs `maintenance/tasks.py:66` et `OccurrenceStatusLog` ; `DEC-UX-01` (accueil) vs `aujourdhui.html`. Aucune phrase ne dit que **51 décisions sur 125 ne sont pas traitées** | [C] ; source v1.2 `A1_DECISIONS_S1_S2.md` | Citer les décisions une à une avec état (réalisée, partielle, non développée) ; ne pas utiliser de plage | P0 |
| AUD-034 | Majeure | Architecture | Deux PDF ; **fusionne AUD-009** | **Densité** : 18 pages du diffusable et 26 du restreint sont remplies à moins de 70 % (11 et 15 à moins de 50 %) ; les compléments techniques (1 à 3 pages par chapitre) répètent chacun un cartouche de 5 lignes ; le restreint **ne contient pas les chapitres de base** qu'il complète ; 3 pages ≤ 5 lignes (p.39, 41, 45) | [A] `pages_remplissage.csv` ; [V] | Voir §J (refonte de l'architecture) | P1 (P0 pour les 3 pages) |
| AUD-035 | Majeure | Pédagogie | S17, S21, S31, S33 (diffusable p.42, 52, 80, 86) | Les schémas de **circuit cible** ne se distinguent **pas des schémas de fonctionnement réel** : seule la légende dit « cible » ; l'image seule (cadre, couleur, mention) est identique à S16, S20, S30, S32 | [V] | Cadre pointillé bleu + mention « 🔵 CIBLE — non développé » dans l'image | P0 (règle de distinction) |
| AUD-036 | Mineure | Pédagogie | Schémas ; **fusionne AUD-020** | Sur 42 schémas : **22 bons, 7 moyens, 10 faibles** (listes de cases sans information relationnelle : S02, S14, S22, S24, S27, S36, S37, S38, S40, S42), 1 difficile (S09), 1 illisible (S10) ; S02 montre 6 groupes quand le tableau juste dessous en compte 11 | [V][A] `schemas_verdicts.csv` | Remplacer les listes par des tableaux ; garder les schémas à circuit (S04, S05, S06, S07, S11, S12, S15, S16, S18, S20, S23, S25, S26, S29, S30, S32) | P1 |
| AUD-037 | Mineure | Doc. | Ch. 5 §5.4 bis, ch. 11 T2 bis, 12 T2 bis, 13 §13.9 bis | Rubriques « bis » : traces d'édition (insertions tardives) | [V] | Renumérotation | P2 |

**Nouveaux défauts du logiciel (non documentaires), à arbitrer — jamais décidés ici**
| ID | Constat | Preuve | Gravité probable |
|---|---|---|---|
| NE-01 | La liste de maintenance affiche « Exécuter » pour des occurrences que l'utilisateur ne peut pas exécuter (403) | [N] | mineure (fonctionnelle) |
| NE-02 | Lignes de la liste des tickets cliquables par `onclick` seulement | [C] `ticket_list.html:28` | mineure (accessibilité) |
| NE-03 | `SECURE_SSL_REDIRECT` sans `SECURE_PROXY_SSL_HEADER` : comportement derrière un proxy TLS non testé | [C] ; [?] | à évaluer (déploiement) |
| NE-04 | Les QR codes encodent `build_absolute_uri` (nom d'hôte de la requête) : un QR imprimé depuis un autre nom d'hôte ou une adresse temporaire pointe vers une adresse erronée ; non documenté | [C] `assets/views.py:140-152, 195-208` | à évaluer (déploiement, exploitation) |
| NE-05 | Réponses **404** pour l'équipier sur `/documentation/nouveau/` et `/dashboard/passation/<id>/` mais **403** sur la plupart des autres pages : masquage volontaire ou incohérence non documentée | [N] | mineure |
| NE-06 | Synthèse de passation lisible par les chefs de l'équipage **sortant** passé à terre (conforme au code ; l'écart A14 s'applique donc aussi à eux) | [N] | à confirmer par le PO (A14) |

## I. Registre consolidé et dédupliqué

### I.1 Fusions
- AUD-009 (pages presque vides) → **AUD-034** ; AUD-020 (schémas ≤ 6,2 pt) → **AUD-036** ; la répétition des bandeaux et des renvois « partie restreinte du dossier » (40 occurrences sans cible, 41 cartouches « Pour qui », 45 rappels « 6d6d0be ») → **AUD-012** ; AUD-024 (prise en main développeur) absorbe NE-03/NE-04 pour la partie documentaire ; AUD-021 absorbe le recomptage des tests.
- **Total : 37 anomalies enregistrées (29 + 8), 2 fusionnées, 35 actives** : 1 bloquante, 15 majeures, 15 mineures, 4 améliorations.

### I.2 Répartition par nature
| Nature | Identifiants | Nombre |
|---|---|---|
| **Erreur documentaire factuelle** | AUD-002, 004, 005, 010, 030, 033 | 6 |
| **Contradiction entre documents** | AUD-003, 012 (partiel), 021 | 3 |
| **Classification / diffusion** | AUD-001 | 1 |
| **Preuve et traçabilité** | AUD-008, 026 | 2 |
| **Mise en page et lisibilité (PDF, captures, schémas)** | AUD-006, 014, 015, 016, 018, 019, 031, 032, 034, 035, 036 | 11 |
| **Pédagogie, navigation, contenu manquant** | AUD-011, 012, 013, 022, 023, 024, 025, 028, 029, 037, 017, 007 | 12 |
| *Total actif* | | *35* |
| **Défauts du logiciel (hors dossier)** | NE-01 à NE-06 (+ A1–A26 du registre existant) | 6 nouveaux |
> AUD-007 et AUD-027 mêlent une observation du logiciel (NE-01, NE-02) et une erreur de description : le **dossier** doit être corrigé indépendamment du logiciel.

### I.3 Ce que le dossier décrit de façon fiable (confirmé en phase 2)
Structure organisationnelle et relève (ch. 4) ; droits par rôle, vues de pilotage et accès (ch. 5, 6, 17) ; tâche personnelle privée (ch. 5, 10) ; passation (ch. 6 : réelle, générée à la relève, lisible par les chefs des deux équipages) ; appareillage (ch. 16) ; stock, formations, RETEX (ch. 13 à 15) ; architecture, données, API, sécurité, exploitation (ch. 18 à 24) ; historique des branches (ch. 26) ; variables d'environnement et commandes (annexe E).

## J. Structure, pagination et architecture documentaire

### J.1 Constat sur les PDF actuels
| Mesure | Diffusable (108 p.) | Restreint (143 p.) |
|---|---|---|
| Mots par page (médiane) | 401 | 290 |
| Pages < 50 % remplies | 11 (5, 6, 10, 14, 20, 46, 61, 82, 83, 93, 106) | 15 (8, 18, 24, 39, 41, 45, 52, 57, 61, 77, 85, 99, 113, 119, 142) |
| Pages de 50 à 70 % | 7 | 11 |
| Pages paysage | 0 | 55 (annexes générées) |

**Causes identifiées** : (1) chaque chapitre commence sur une nouvelle page et se termine par « Limites » et « Sources » qui laissent un blanc ; (2) un schéma qui ne tient pas est repoussé à la page suivante (p.6 → 7 du diffusable : 80 % de vide) ; (3) les compléments techniques sont des chapitres à part de 1 à 3 pages ; (4) les annexes générées sont des listes de 700 à 1 100 lignes sans filtre, adaptées à une base de données plus qu'à un PDF.

### J.2 Appréciation éditoriale
- **Ce qui fonctionne** : titres explicites, tableaux à en-tête répétée, hiérarchie typographique sobre, couleurs retenues, cohérence des cartouches d'ouverture.
- **Ce qui donne l'impression de « compilation »** : (a) un même cartouche en tête des 41 chapitres (diffusion, état, « Pour qui », « Ce que vous y trouverez ») au lieu d'un en-tête courant ; (b) chaque chapitre refait l'historique de l'état B, des étiquettes et du renvoi à une « partie restreinte » **sans page** ; (c) l'ordre de lecture est celui de la rédaction (par ensemble E1 à E4), non celui d'un lecteur ; (d) les chapitres métier mélangent en un seul bloc **mode d'emploi**, **règles**, **limites** et **cible** (une même page peut contenir un parcours de marin et une décision de gouvernance) ; (e) aucune capture dans les chapitres, alors que les captures existent dans un autre PDF ; (f) deux PDF qui ne se lisent pas séparément (le restreint complète le diffusable sans le contenir).
- **Capacité à servir de manuel de référence** : bonne pour la précision, **insuffisante pour la consultation** (pas d'index, pas de numéros de page au sommaire, pas de fiche par module, pas de renvois croisés cliquables entre PDF).

### J.3 Recommandation sur l'architecture finale
**Recommandation : garder trois PDF comme *formats de livraison*, mais les recomposer par public (réorganisation), plus des documents complémentaires courts — plutôt que de simplement corriger les trois PDF actuels.**

| Livrable proposé | Public | Contenu | Taille cible |
|---|---|---|---|
| **1. Guide de Matrix (utilisateur)** | marin, chef | Guide visuel étendu : parcours, écrans, capture + règle + limite, par module ; glossaire minimal ; reprend les ch. 1, 2, 6, 8, 10, 12, 17 en version courte | 50 à 70 p. |
| **2. Référentiel fonctionnel et gouvernance** | responsable, commandement, décideur | **Résumé de 2 pages**, fiche de rôle, un chapitre par module (fonctionnement actuel / cible / limites), registre des écarts simplifié, décisions en attente | 80 à 100 p. |
| **3. Dossier technique de reprise** (restreint) | développeur, mainteneur, exploitant | Les ch. 18 à 24 **fusionnés** avec les compléments techniques par module (un seul chapitre par module avec encadré technique), recette de prise en main, sécurité, exploitation | 100 à 120 p. |
| **Annexes consultables** (hors PDF) | développeur | Annexes B, C, D, E, G et F.5 en **tableaux filtrables** (HTML/XLSX/CSV générés) ; le PDF ne garde que les totaux et la méthode | — |
| **Registre des écarts et décisions** (document vivant) | PO, mainteneur | A1–A26, NE, B, D, plus tableau des décisions avec état de réalisation | 15 à 20 p. |

**Règles de conception à adopter** : en-tête courant au lieu du cartouche ; sommaire avec numéros de page et renvois cliquables entre documents ; une page de garde avec classification, version, date et périmètre ; saut de page seulement avant un grand chapitre ; schémas ≥ 8 pt à la largeur de page ; schémas de circuit cible visuellement marqués ; captures intégrées aux chapitres d'usage ; un index des termes métier.

**Ce qu'il ne faut pas faire** : fusionner tout en un document unique (les publics et classifications diffèrent) ; supprimer les compléments techniques (leur contenu est vérifié et utile) ; remplacer les schémas de circuit par des captures.

## K. Plan de correction global (aucune correction lancée)

Efforts en jours-personne, hors décisions du PO. Dépendance « DA » = décision sur l'architecture documentaire (§J.3).

### P0 — Indispensable avant validation documentaire (≈ 4 j)
| # | Action | Anomalies | Effort | Dépendances |
|---|---|---|---|---|
| P0-1 | Classification : harmoniser en-têtes et couvertures ; trancher le sort des chemins `.py`, branches et `docs/` dans le « diffusable » | AUD-001 | 0,5 | **Décision de l'autorité** |
| P0-2 | Corriger les erreurs factuelles : impression de la feuille (ch. 8, A12), rondes (ch. 1), barre de parcours (ch. 6, 17), chemin du scan (ch. 20), rapport du guide visuel | AUD-002, 004, 005, 010, 030 | 1 | — |
| P0-3 | Reclasser les plages de décisions (réalisée / partielle / non développée) | AUD-033 | 0,5 | P0-2 |
| P0-4 | Mettre à jour les mentions « non rejoué » ; référencer le guide visuel et l'audit | AUD-003, 012 | 0,5 | P0-2 |
| P0-5 | Citer et archiver les preuves A14/A20/A25 ; décider de leur sort | AUD-008 | 0,25 | **Décision du PO** |
| P0-6 | Mise en page bloquante : légendes S10/S40, tableaux cassés p.37 et p.79, annexe F.5, pages ≤ 5 lignes | AUD-006, 009, 031, 032 | 1 | Régénération PDF |
| P0-7 | Marquer visuellement les schémas de circuit cible | AUD-035 | 0,25 | — |

### P1 — Améliorations importantes (≈ 14 j, dont la refonte)
| # | Action | Anomalies | Effort | Dépendances |
|---|---|---|---|---|
| P1-1 | Résumé de 2 pages pour le décideur ; fiche de rôle | AUD-011 | 1 | ton validé par le PO |
| P1-2 | Sommaires paginés, un seul parcours par profil, index des termes | AUD-012, 023 | 1 | P0-4 |
| P1-3 | Compléter le guide visuel (annonce accusée, installation, échange de tour, RETEX, appareillage avec session, bas d'accueil, vue mobile) ; retirer 8 doublons | AUD-013, 016, 025 | 1,5 | instance de démonstration |
| P1-4 | Prise en main développeur, recette de déploiement, QR et hôte | AUD-024, NE-03, NE-04 | 1,5 | — |
| P1-5 | Remplacer les schémas faibles par des tableaux ; relayouter S09, S10, S13, S28 | AUD-036 | 1,5 | — |
| P1-6 | « Recherche de personnes » (existant / cible) ; annexe des décisions avec état | AUD-022, 026 | 1 | accès à la branche V1.2 |
| P1-7 | Colonne « profils concernés » dans le registre | §C.1 | 0,5 | — |
| P1-8 | **Refonte de l'architecture documentaire (§J.3)** | AUD-034 | 6 à 8 | **DA** |
| P1-9 | Inspecter à 100 % les 35 pages restreintes non vues et relire phrase à phrase les chapitres 9 à 11, 13 à 15 | §G | 2 | — |

### P2 — Finitions (≈ 1,5 j)
Anglais dans les captures (AUD-014), messages parasites (015), doublons de captures (016), faute du chapitre 5 (017), identifiants coupés (018), symbole ⚪ (019), nombre de tests (021), accessibilité (027), rangement des rapports (028), personnages fictifs (029), numérotation « bis » (037), cohérence 403/404 (NE-05).

### Défauts du logiciel (hors campagne de correction documentaire)
NE-01, NE-02, NE-03, NE-04, NE-06 et A1–A26 relèvent d'**arbitrages et de lots** décidés par le PO. **Aucun n'est traité par le plan ci-dessus.**

## L. Conclusion révisée (remplace la recommandation de phase 1)

**Recommandation : corrections indispensables avant validation documentaire.** La liste est le P0 du §K (≈ 4 jours, aucun code applicatif) ; **la décision sur l'architecture documentaire (§J.3) doit être prise avant la campagne**, car elle change l'ordre des corrections P1 mais pas les P0.

**Appréciation** : le *contenu* est fiable et sourcé (tout ce qui a été recoupé en phase 2 est exact, hormis six erreurs mineures ou majeures listées) ; la *forme* ne permet pas d'en faire un manuel de référence professionnel sans recomposition.

### Trois validations à ne pas confondre (inchangé)
| Validation | État |
|---|---|
| Documentaire | **Non prononcée** (P0 à traiter, puis relecture du PO) |
| Logicielle | **Hors mission** ; A1–A26 et NE-01 à NE-06 à arbitrer ; suite complète de 3 963 tests non rejouée |
| Autorisation de diffusion | **Non accordée** ; en-tête « DIFFUSION GÉNÉRALE » à corriger (AUD-001) |

### Limites finales de l'audit
- **35 pages du PDF restreint non vues** ; **aucune page vue à 100 %** (résolution maximale 110 dpi).
- Chapitres 9 à 11 et 13 à 15 recoupés par affirmations, **non relus phrase à phrase**.
- Annexes C, D, G non recoupées ligne à ligne (totaux exacts).
- Schémas S38/S39 non revérifiés contre le plan en 28 lots.
- Validité des décisions `DEC-*` : existence et libellé vérifiés, **bien-fondé non vérifiable**.
- Deux navigateurs réels, Windows, PostgreSQL, Redis/Celery réels : non essayés.

*Aucune correction n'est commencée. J'attends la validation PO de ce rapport.*
