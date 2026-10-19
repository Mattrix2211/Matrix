# Bilan UX des 18 missions de recette (passage B) — entrée du futur plan de refonte

Source : `2026-10-13-B-synthese.md`, `2026-10-13-B-observateur.md` et les 18 comptes rendus `B-M01` à `B-M18`. Passage B joué au SHA `5ea072d`, **avant** les corrections (PR #9 à #15).

**Réserve.** Les « marins » sont des agents IA qui simulent des profils : ce ne sont ni de vrais marins ni une homologation SSI. Les notes (0 à 4) sont indicatives. Aucune durée par action n'a été mesurée. Toutes les observations ci-dessous restent des hypothèses à confirmer en contre-recette avec les mêmes missions.

## 1. Résultat global

- 18 missions sur 18 jouées. Moyenne indicative **2,3 sur 4** (« acceptable avec friction »). Aucune mission n'est « naturelle ».
- Les mieux notées : M05 (3,5, attribution d'une tâche), M11 (3,0, refus clair), M01 et M02 (2,8).
- Les plus faibles : **M14 (1,0, visa COMAEQ introuvable)**, **M10 (1,3, liste de quarts)**, M03 et M04 (1,8, maintenance), M13 (1,9, relève entre équipages).
- Critères les plus faibles sur l'ensemble : découvrabilité (critère 6), confirmation après action, états et responsabilités. Les critères temps (2) et conservation du contexte (9) n'ont pas été mesurés.

## 2. Difficultés de navigation

| Constat | Missions | Effet observé |
|---|---|---|
| **Parcours importants introuvables** : visa COMAEQ (le bouton « Valider » de l'accueil ouvre « Enregistrer la correction »), relève entre équipages (cachée dans Paramètres › Utilisateurs, introuvable pour `cdt_b` et `second_a`), affectation d'un créneau existant d'une liste de quarts | M14, M13, M10 | Mission échouée ou non jouable. Ce sont les trois parcours de découvrabilité à rejouer sans assistance. |
| **Menu trop large**, entrées d'administration visibles par presque tous les rôles ; pages jamais ouvertes par les marins alors qu'elles sont au menu (Paramètres, Flotte, Plan du navire, Prêt à appareiller) | M18, M13, plusieurs | Le marin ne sait pas ce qui le concerne. Note « navigation stable » : 2/4. |
| **Documentation à 4 clics** de l'écran d'exécution (« Autres actions » → « Historique et relevés » → retour → « Documents associés »), cul-de-sac « Aucun compte rendu » | M03 | Une procédure doit être à un clic. « Autres actions » est une icône sans libellé. |
| **Points d'entrée peu clairs** : « Synthèse » mène à `/taches/#synthese`, « Mon équipe », « Suivi » désigne à la fois un menu et des lignes du fil | M06, M08 | Hésitation. |
| **Réglage des droits d'un chef** : Paramètres › « Seuils de rôle » ; le menu « Utilisateurs et droits » ne contient que « Utilisateurs » | M18 | Il faut déjà connaître le mot. |
| **Liste des installations** sans criticité, statut ni retard, sans filtre « critique » ou « en retard » ; le lien de la Vue COMANAV mène à la liste complète | M09, M15 | Il faut croiser l'accueil et la fiche. |

## 3. Difficultés de compréhension

| Constat | Missions | Effet observé |
|---|---|---|
| **Circuits de remontée ambigus** : « Signaler une difficulté », « Je suis bloqué », « Signaler une anomalie », « Discussion ». Aucun guide pour savoir lequel prévient le responsable. Défaut structurel. | M02, M03, M06, M09 | Mauvais choix de circuit, ou doute sur la prise en compte. |
| **Étiquette « Demande bord–terre »** pour un sujet interne au bâtiment | M02, M03, M09 | Trompeur. |
| **Pas de confirmation après action** : attribution, publication dans un fil, annonce, ajout d'un créneau, « Sélectionner » / « Affecter ». Défaut structurel. | M02, M05, M06, M09, M10, M12, M13, M16, M17 | « Je ne sais pas si c'est parti. » Les bonnes confirmations existent ailleurs (clôture de maintenance, création d'utilisateur). |
| **« Qui est prévenu » invisible** alors que la notification circule (prouvée en base) | M02, M06, M09 | Les marins « le disent de vive voix ». |
| **Jargon** : « interlocuteur », « Actions décidées », « Responsable du dossier », « Public visé », « Seuils de rôle », « RETEX » non expliqué ; jargon développeur affiché (« CLAUDE.md §6 » sur Feuille de service › Réglages) | M01, M03, M05, M06, M07, M09, M13, M16, M18 | Contraire au principe « zéro jargon ». |
| **États contradictoires** : « Assignée » après clôture, « En validation » alors que c'est terminé, « Bloquées 0 » contredit par le tableau, chiffres de retard divergents entre accueil et Vue COMANAV | M03, M04, M14, M12, M15 | Perte de confiance dans les chiffres. |
| **Lecture seule d'un équipage à terre** : boutons affichés mais refusés (403 clair), le bandeau ne dit pas ce qui reste permis | M12, M13 | Un clic de trop et un doute. |
| **Résultat vide ou accès restreint non expliqué** (« Aucun » sans distinguer « n'existe pas » et « non visible pour vous ») | M07, M11 | Le marin ne sait pas vers qui se tourner. |
| **Message « Mot de passe incorrect » trompeur** à la clôture, conformité remise à « — » | M03, M04 | Deux marins bloqués ou ralentis. Ce point sera réglé par le chantier validations critiques, à rejouer. |

## 4. Difficultés de réalisation des tâches

- **Quarts (M10, la plus faible)** : impossible d'affecter un créneau existant (suppression puis recréation), saisie créneau par créneau, aucun avertissement d'absence ou de qualification, « None » affiché dans les listes. Publication et échange non testables.
- **Conflits de planning (M08)** : aucune alerte absences / quarts / gardes. Les conflits ont été trouvés à la main sur trois écrans. À confronter à la liste « À faire plus tard ».
- **Maintenance (M03, M04)** : pas de champ de relevé de mesure (texte libre), « Points à contrôler » vide alors que la procédure en liste 4, début et fin non pré-remplis pour un compte rendu rétroactif, pas d'impression du compte rendu saisi. Le marin n'y gagne pas face au cahier.
- **Ressaisie** : formulaire de création d'utilisateur vidé après rejet (M18), conformité perdue au rechargement (M03, M04).
- **Formation (M17)** : pas de vue des qualifications proches de l'échéance, pas de liste des inscrits ni d'annulation après « Sélectionner ».
- **Soutien à terre (M16)** : aucun signal de la demande, qui apparaît en « Dossiers suivis » et non en « À traiter ».
- **Correction d'erreur** : on ne peut ni corriger un message de fil, ni défaire un blocage, une sélection ou une affectation. La traçabilité peut justifier ce choix, il faut le dire à l'écran.
- **Annonces (M13)** : pas de relance des non-lecteurs, l'administrateur compte parmi les « non lus », la différence « accusé » / « lu » n'est pas expliquée.

## 5. Surcharge visuelle et hiérarchie (convergent avec les 10 captures)

- **Accueil** : « À faire » mélange 11 lignes (tâches, annonces, tickets, maintenance, formation, ronde) sans priorité hors « en retard ». L'« accusé requis » est noyé. La pastille « 18 notifications non lues » n'informe pas.
- **Calendrier** : 6 à 9 pastilles par jour, libellés tronqués, icônes sans nom, repère « cette semaine » à deviner.
- **Boutons d'écriture** visibles sans que la portée soit établie (M03, M08, M15, M17).
- **Mot de passe de signature** qui n'apparaît qu'après le choix de la conformité (M03, M04) : dévoilement progressif réussi à moitié.

## 6. Ce qui fonctionne et doit survivre à la refonte

- **Page Tâches** : charge par marin, absences, retards, blocages et échéances en un coup d'œil. C'est le point d'entrée le plus utile des chefs.
- **Blocage remonté seul** sur l'accueil du chef, avec le nom du marin.
- **Fils de discussion attachés à l'objet**, avec notification orientée et réponse en un clic.
- **Clôture de maintenance** claire (statut, nom, horodatage) et audit prouvé.
- **Consigne publiée en un formulaire** avec suivi de lecture nominatif et versions conservées.
- **Refus 403 clair** et motivé ; périmètre bien tenu.
- **Vue COMANAV** : dérives, indisponibilités, chaîne sécurité et logistique en une page.
- **Brouillon enregistré automatiquement**, durée calculée seule, « Sélectionner » / « Refuser » en un clic.

## 7. Grille des principes UX (notes observateur, 0 à 4)

| Principe | Note |
|---|---|
| Action avant statistiques | 3 |
| Discussion attachée à l'objet | 3 |
| Navigation stable | 2 |
| Dévoilement progressif | 2 |
| Saisie une fois, réutilisée partout | 2 |
| Peu de ressaisies | 2 |
| Cohérence visuelle stricte | 2 |
| États et responsabilités compréhensibles | 2 |
| Dense mais calme | 2 |

## 8. Pistes pour le plan UX (à valider ensemble, rien n'est lancé)

1. **Navigation** : un menu par rôle et par métier, avec une entrée « Ce que je dois faire » ; déplacer l'administration hors du menu courant ; libellés Marine et sans anglicisme ; point d'entrée unique et explicite pour la relève, le visa et les quarts.
2. **Accueil « Aujourd'hui »** : une priorité nette (retards, blocages, accusés requis), le reste replié ; notifications résumées plutôt que listées.
3. **Fiche de tâche** : l'action principale et la discussion d'abord, les actions secondaires, la checklist et les pièces jointes vides repliées.
4. **Transverse** : une confirmation uniforme après chaque action, avec « qui est prévenu » ; états cohérents d'un écran à l'autre ; un seul circuit de remontée expliqué ; messages d'état vide qui disent pourquoi.

## 9. Corrections déjà apportées depuis le passage B (à vérifier en contre-recette)

- Visa COMAEQ et feuille de service par équipage (PR #12, #15) ; lien d'évitement, bouton « Attribuer une tâche » en tête, contrastes (PR #14).
- Chantier validations critiques en cours : la ressaisie du mot de passe est remplacée par une confirmation explicite, ce qui devrait lever le message trompeur de M03 et M04.
- **Non corrigés** : relève (découvrabilité), affectation d'un créneau, « None », alertes de conflit, circuits de remontée, confirmations après action.
