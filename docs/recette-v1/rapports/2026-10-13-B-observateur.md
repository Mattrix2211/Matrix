# Passage B — Consolidation de l'observateur UX (agent `observateur-ux`)

| Champ | Valeur |
|---|---|
| SHA testé | `5ea072d897f79955b8d50def62f055a7090ddd5d` (branche `claude/recette-v1-passage-b`) |
| Base | SQLite jetable, `DJANGO_DEBUG=1`, `migrate` + `seed_demo` + `seed_recette` |
| Navigateur | Chromium headless, 1366×768 |
| Date | 2026-10-13 |
| Source | Les 18 comptes rendus `2026-10-13-B-M01` à `M18` de ce dossier |

Sortie de l'agent `observateur-ux`, enregistrée telle que reçue (mise en forme conservée). L'agent n'a ni lu le code ni exécuté de commande.

---

# Rapport de consolidation, passage B de la recette V1 (observateur UX / fonctionnel)

Convention de la colonne « Statut » : « Hypothèse » = hypothèse à confirmer (impression d'agents IA simulant des marins, à confirmer par des marins réels ou par un test technique). Aucune observation n'est « confirmée par test technique » par l'observateur. La mention « preuve coordinateur » indique seulement une lecture de base faite par le coordinateur (notifications, AuditLog). Les missions sont désignées par leur numéro (M05 = `2026-10-13-B-M05-claire.md`).

## 1. Tableau consolidé des observations

### 1.A Périmètre et permissions (fuites signalées : P0 potentiel, jamais confirmé)

| # | Observation | Marins / missions | Catégorie | Impact | Preuves | Priorité | Statut |
|---|---|---|---|---|---|---|---|
| P-1 | **P0 potentiel à confirmer.** Le compte de soutien à terre `terre_classe` voit, sur une tâche et une demande du bord, les formulaires « Réaffecter ou replanifier » (bouton « Modifier »), « Assigner une action », « Confier à un autre responsable », « Ajouter un interlocuteur », « Joindre ». Le marin n'a cliqué sur aucun : l'écriture réelle n'est pas établie. | Tessa, M16 | Permission / périmètre | Si l'écriture est possible : modification de données du bord par un acteur à terre. | M16 « Droits constatés » 1 et 2 (`/demandes/2/`, `/taches/11/`) ; évaluation coordinateur M16 | **P0 potentiel à confirmer** (`qa-securite`) | Hypothèse |
| P-2 | **P0 potentiel à confirmer.** « Ajouter un interlocuteur au fil » propose 19 personnes de tout le bâtiment à une cheffe de section (commandant, chefs de secteur Élec et Incendie, équipiers d'autres sections, « Marin B » de l'équipage B). Peut relever du design des fils. | Claire, M05 et M06 | Permission / périmètre | Exposition de noms hors périmètre | M05 et M06 « Droits constatés » ; évaluation coordinateur M05, M06 | **P0 potentiel à confirmer** | Hypothèse |
| P-3 | **P0 potentiel à confirmer.** Les sélecteurs « Assigner une action » (champ « Marin »), « Responsable du dossier » (13 chefs) et « Marin à affecter » (formation) proposent tout le bâtiment (administrateur, commandants, équipage B) à un chef de section, un chef de service, un équipier, une référente. Le premier élément est présélectionné sur « Paul Admin Navire » (M09). À l'inverse, les sélecteurs de tâche sont bien limités à la section (M05, M07) : incohérence entre sélecteurs. | Claire M06 ; Antoine M09 ; Julien M03 ; Éloïse M14 ; Solène M17 | Permission / périmètre | Fuite de noms hors périmètre ; risque d'erreur par présélection | M06, M09, M03, M14, M17 « Droits constatés » ; M07 « Chemin » 3 | **P0 potentiel à confirmer** (liste « Marin » hors périmètre). Présélection sur l'administrateur : P2 ergonomique | Hypothèse |
| P-4 | **P0 potentiel à confirmer.** Après déconnexion de `cdt_a` et connexion de `cdt_b`, l'accueil a affiché « Bonjour Capitaine de frégate Cdt A », alors que les écrans suivants montraient les droits de B (« Lecture seule — Équipage B à terre »). Le coordinateur a vu `Benoît Cdt B` en base. Causes possibles : cache d'affichage entre deux comptes ou artefact de session lié à l'anomalie de procédure (section 6). | Benoît (`cdt_b`), M13 | Permission / périmètre ; possible bug | Une fuite d'identité entre sessions serait un P0 si avérée | M13 §2 chemin 2 ; note d'anomalie ; évaluation coordinateur M13 | **P0 potentiel à confirmer** | Hypothèse |
| P-5 | Entrées « Administration > Paramètres », « Supervision > Prêt à appareiller », « Flotte », « Configurer le plan du navire » visibles pour équipiers, chefs de section/service/secteur, soutien à terre. Aucune page ouverte : accès réel inconnu. | M01, M02, M03, M04, M05, M06, M07, M08, M09, M10, M11, M12, M16 | Permission / périmètre | Bruit de menu, manque de dévoilement progressif ; fuite de droit si accessible | « Droits constatés » de ces missions ; évaluation coordinateur M01, M08 | P2 ; à réévaluer en P0 si accès réel | Hypothèse (accès non testé) |
| P-6 | Boutons d'écriture visibles à portée non établie : « Modifier » des champs personnalisés pour un équipier (M03) ; « Nouvelle installation », « Ajouter du matériel », « Modifier » pour le COMANAV (M15) ; « Modifier » de la fiche formation pour un chef de service (M08) ; « Valider une formation » pour une référente (M17). | Julien M03 ; Denis M15 ; Antoine M08 ; Solène M17 | Permission / périmètre | Droits d'écriture possibles ou simple affichage ; aucun clic | M03, M15, M08, M17 « Droits constatés » ; évaluation coordinateur M15, M17 | P2, à confirmer avec le PO puis test technique | Hypothèse |
| P-7 | COMAEQ : peut se cocher intervenant sur les maintenances d'autrui, corriger des comptes rendus terminés, attribuer une tâche à tout l'équipage A (commandants et administrateur inclus). | Éloïse, M14 | Permission / périmètre (choix métier PO) | Écart possible avec « Organigramme et rôles » | M14 « Droits constatés » ; évaluation coordinateur M14 | P2 (arbitrage PO) | Hypothèse |
| P-8 | L'administrateur de navire peut créer des comptes Commandant, Commandant en second, État-major ; « Administrateur général » dans les listes de seuils ; rôle par défaut du formulaire « Administrateur d'unité ». | Paul, M18 | Permission / périmètre (arbitrage PO) ; incohérence (valeur par défaut) | Escalade de droits ou saisie par défaut dangereuse | M18 « Droits constatés », « Hésitations » ; évaluation coordinateur M18 | P2 | Hypothèse |
| P-9 | Un blocage notifie 9 destinataires (commandant, second, trois COMA, administrateur, chefs). `chef_secteur_a` et `chef_section_a` en reçoivent chacun une : pas nécessairement un doublon. | Lucas, M02 | Permission / périmètre (choix métier) | Bruit possible | M02 évaluation coordinateur (lecture base, ids 140 et 147) | P3 (arbitrage PO) | Hypothèse (notifications prouvées par le coordinateur ; excès non tranché) |
| P-10 | `second_a` publie à tout le bâtiment, équipage B inclus, et voit 19 destinataires nominatifs dont l'administrateur. | Cécile, M13 | Permission / périmètre (arbitrage PO) | À valider par le PO, pas une fuite avérée | M13 §3 ; évaluation coordinateur M13 | P3 (arbitrage PO) | Hypothèse |

### 1.B Bugs et incohérences techniques probables

| # | Observation | Marins / missions | Catégorie | Impact | Preuves | Priorité | Statut |
|---|---|---|---|---|---|---|---|
| B-1 | **Message « Mot de passe incorrect » trompeur.** Clôturer sans conformité affiche « La conformité finale est à déclarer » puis « Mot de passe incorrect : l'exécution n'a pas été validée », alors qu'aucun mot de passe n'était demandé. La liste de conformité est remise à « — ». Le champ « Mot de passe (signature) » n'apparaît qu'après le choix de la conformité. Le message reste affiché au 2e essai (M04). | Julien, M03 et M04 (2 marins) | Bug fonctionnel (message, valeur perdue) avec composante ergonomique | Perte de confiance, clics inutiles, 2 essais ratés | M03 « Chemin » 8 ; M04 « Chemin » 4 à 6 ; évaluation coordinateur M03, M04 | **P2** | Hypothèse (reproduit sur 2 marins ; cause non établie) |
| B-2 | **« None » affiché.** Sous-titre d'une liste de quarts : « None — Bretagne / Propulsion — 14/10/2026 au 20/10/2026 » ; « None — Bretagne / Propulsion » dans la liste. | Antoine M08 ; Cécile M13 | Bug fonctionnel (valeur nulle rendue) | Défaut visible par tout chef de liste | M08 « Termes » ; M13 §3 « Termes » ; évaluation coordinateur M08, M13 | **P2** (P3 si cosmétique) | Hypothèse (2 marins) |
| B-3 | **Heures incohérentes.** Accueil de Lucas « Quart · Barre 08:00 » contre calendrier « 06 h Barre » (M01) ; chef de service : « 06 h » au calendrier pour 08:00–16:00 en liste (M08). Contre-indice : dans M06, 18:51 pour 16:52 UTC est cohérent avec Europe/Paris ; le calendrier afficherait en UTC. | Lucas M01 ; Antoine M08 ; Claire M06 | Bug fonctionnel probable (fuseau) / incohérence | Le marin ne peut pas se fier à l'heure du calendrier | M01 « Hésitations » ; M08 « Termes » ; M06 « Retour du système » ; évaluation coordinateur M08 | **P2** si confirmé | Hypothèse |
| B-4 | **Chiffres divergents.** « Maintenances en retard » 4 (accueil) contre 3 (Vue COMANAV) ; part 33 % contre 25 % ; « Installations critiques en retard » 2 contre 1 sur 3. En M12, l'accueil affiche « 0 retard / à jour » alors que la page Tâches signale une tâche en retard (périmètres de calcul différents : maintenances contre tâches). | Denis M15 ; Ivan M12 | Incohérence d'interface (cause non établie) | Un chef ne sait pas quel chiffre transmettre | M15 « Retour du système » ; M12 « Retour du système » ; évaluation coordinateur M15 | **P2** | Hypothèse (incohérence relevée, cause non établie) |
| B-5 | « Avancement de l'équipe » indique « Bloquées 0 » alors que le tableau dessous liste une tâche « Bloquée » (compte `chef_secteur_b`). | Ivan, M12 | Bug fonctionnel probable (périmètre de calcul) | Indicateur faux ou mal défini | M12 « Retour du système » ; évaluation coordinateur M12 | P2 | Hypothèse |
| B-6 | Après clôture, le message dit « Statut : Terminée » mais le bandeau garde « Assignée » et « Terminer la maintenance » reste actif ; aucune indication de correction ou réouverture. | Julien, M03 et M04 | Incohérence d'interface | Doute sur l'état réel | M03 « Retour du système » ; M04 « Chemin » 6 ; évaluation coordinateur M04 | P2 | Hypothèse (2 marins) |
| B-7 | Compteurs et listes contradictoires : « Documents 0 » alors que « Documents associés » en liste 1 ; « Non affectés 0 Conforme » qui ignore les marins en permission ; « Mes listes de quarts » vide pour le chef de service créateur avec invitation à « se rapprocher de votre chef de service ». | Julien M03 ; Antoine M08 | Incohérence d'interface (métier pour « Mes listes ») | Indicateur trompeur | M03 « Chemin » 6 ; M08 « Termes », « Retour du système » ; évaluation coordinateur M08 | P2 (« Non affectés ») ; P3 (autres) | Hypothèse |
| B-8 | Boutons sans effet ou libellé trompeur : « Valider » de l'accueil (COMAEQ) mène à un écran de correction sans geste de visa, avec statut « En validation » et texte « Ce compte rendu est déjà terminé » ; « Valider » sur des absences déjà « Validée » (M08, M10) ; « Générer la synthèse de passation » recharge sans retour (M13) ; cloche de notifications sans ouverture pour la référente formation (M17, hypothèse d'artefact : le panneau s'ouvre en M12). | Éloïse M14 ; Antoine M08 ; Hélène M10 ; Anne M13 ; Solène M17 | Bug fonctionnel probable (câblage ou libellé) | Visa non faisable (voir F-1) | M14 §5 à 7 ; M08 « Termes » ; M10 « Chemin » 4 ; M13 §1 chemin 9 ; M17 « Chemin » 3 ; évaluation coordinateur M14, M10, M17 | Visa M14 : **P1**. Autres : P2 à P3 | Hypothèse |

### 1.C Fonctions manquantes ou difficiles à découvrir

| # | Observation | Marins / missions | Catégorie | Impact | Preuves | Priorité | Statut |
|---|---|---|---|---|---|---|---|
| F-1 | **Visa COMAEQ introuvable.** Deux occurrences « En validation » (n°6 et 10) sans bouton « Viser » ni « Valider » exploitable (écrans vus : exécution, gestion de la maintenance, menu « Autres actions »). | Éloïse, M14 | Bug probable ou fonction difficile à découvrir (non tranché) | Parcours « visa » bloqué | M14 §5 à 7 ; évaluation coordinateur M14 (« Échoué ») | **P1** proposé | Hypothèse |
| F-2 | **Relève entre équipages cachée ou introuvable.** Elle est dans « Paramètres > Utilisateurs > Relève — Bretagne » (vue par `cdt_a`). `cdt_b` et `second_a` n'ont trouvé aucun écran (recherche « relève » : 0 résultat). La validation côté B n'a pas pu être jouée. | Anne, Benoît, Cécile, M13 | Fonction difficile à découvrir ; peut-être non exposée à `cdt_b` | Mission « relève » non testée en pratique | M13 §1 chemin 8, §2 chemins 5 à 8, §3 chemin 6 ; évaluation coordinateur M13 | P1 (parcours opérationnel), à confirmer | Hypothèse |
| F-3 | Aucun retour après « Générer la synthèse de passation » ; la rubrique « Synthèses de passation » reste vide. | Anne, M13 | Bug probable ou retour système absent | Résultat impossible à vérifier | M13 §1 chemin 9 | P2 | Hypothèse |
| F-4 | **Quarts : pas de modification d'un créneau existant.** Impossible d'affecter le créneau « Non affecté » : il faut supprimer et recréer. Aucun avertissement d'absence ou de qualification à la saisie. Saisie créneau par créneau (7 créneaux sur 3 jours). | Hélène, M10 | Fonction manquante / difficile à découvrir (non tranché) | Parcours « liste de quarts » lent | M10 « Chemin » 5 à 6, « Hésitations » ; évaluation coordinateur M10 | P1 à P2 si confirmé | Hypothèse |
| F-5 | **Aucune alerte de conflit absences / quarts / gardes.** Trouvés à la main sur 3 écrans : Lina de garde le 13/10 alors qu'en permission du 12 au 14 ; Karim ; Julien le 16/10. Deux listes de quarts se chevauchent du 14 au 18/10. | Antoine, M08 | Fonction manquante ou non découverte | Perte de confiance dans la planification ; à confronter à « À faire plus tard » | M08 « Conflits repérés » ; évaluation coordinateur M08 | P1 si V1, sinon différée | Hypothèse |
| F-6 | Fiche d'installation sans état d'avancement (dernier réalisé, prochain, retard ; « Aucun relevé » ×3 ; onglet Maintenance sans dates). La liste des installations n'affiche ni criticité, ni statut, ni retard, et n'a pas de filtre « critique » ni « en retard » (M15). Le lien de la Vue COMANAV mène à la liste complète de 6 installations sans filtre. | Antoine M09 ; Denis M15 | Fonction difficile à découvrir (ou manquante) | Il faut croiser l'accueil et la fiche | M09 « Chemin » 5, 6 ; M15 « Chemin » 4, « Retour du système » | P2 | Hypothèse |
| F-7 | Documentation à 4 clics de l'écran d'exécution (« Autres actions » → « Historique et relevés » → « Retour à la fiche » → « Documents associés »), avec cul-de-sac « Aucun compte rendu ». | Julien, M03 | Parcours inutilement complexe | Procédure à un clic attendue | M03 « Hésitations » ; évaluation coordinateur M03 | P2 | Hypothèse |
| F-8 | Seule la fiche papier vierge est imprimable (QR code, « à saisir dans Matrix après réalisation ») ; pas d'impression du compte rendu saisi. Le clic sur « Imprimer » n'a pas été fait : « Exécuté, non prouvé ». | Julien, M04 | Fonction manquante (arbitrer, peut être différée) | Ressaisie papier | M04 « Réussite », « Avantage » ; évaluation coordinateur M04 | P2 | Hypothèse |
| F-9 | Pas de champ de relevé de mesure (débit, pression) : tout en texte libre ; « Points à contrôler » vide alors que la procédure en liste 4 ; tâche « consigne » non liée à la maintenance. | Julien, M03 | Fonction manquante (« À faire plus tard » possible) | Pas de gain face au cahier | M03 « Hésitations » ; évaluation coordinateur M03 | P3 (arbitrage PO) | Hypothèse |
| F-10 | Début/Fin non pré-remplis avec la date prévue pour un compte rendu rétroactif ; « 0 / 0 opérations » sans sens pour un essai de pompe. | Julien, M04 | Parcours inutilement complexe | Saisie manuelle de la date d'hier | M04 « Hésitations », « Termes » ; évaluation coordinateur M04 | P3 | Hypothèse |
| F-11 | Aucune relance des non-lecteurs d'une annonce ; l'administrateur compte parmi les « non lus » ; différence « accusé » / « lu » non expliquée. | Anne, Cécile, M13 | Fonction manquante (probablement « À faire plus tard ») | Passage obligé par une tâche | M13 §1 « Suivi », §3 « Correction d'erreur » | P3 | Hypothèse |
| F-12 | Référente formation : pas de vue des qualifications de l'équipage proches de l'échéance (la date du 02/11 de Julien n'est que sur la fiche de formation) ; pas de liste des inscrits ni d'annulation après « Sélectionner » / « Affecter ». | Solène, M17 | Fonction difficile à découvrir ou manquante | Elle garderait un Excel à côté | M17 « Hésitations », « Correction » ; évaluation coordinateur M17 | P2 | Hypothèse |
| F-13 | Soutien à terre sans signal de la demande : centre de notifications vide, demande en « Dossiers suivis » et non en « À traiter ». | Tessa, M16 | Fonction manquante ou donnée de recette (à valider avec le PO) | Il faut aller chercher l'information | M16 « Réussite », « Retour du système » ; évaluation coordinateur M16 | P2 | Hypothèse |
| F-14 | Feuille de service vide pour le navire (aucune rubrique ni fonction configurée dans le jeu de données). | Éloïse, M14 | Donnée de recette absente, pas nécessairement un défaut | Volet non testé de façon significative | M14 §2 ; évaluation coordinateur M14 | Hors défaut (limite de jeu de données) | Voir section 6 |
| F-15 | Aucun moyen de corriger un message de fil publié, ni de défaire un blocage / « Sélectionner » / « Affecter ». | Lucas M02 ; Claire M06 ; Ivan M12 ; Tessa M16 ; Solène M17 | Fonction manquante (arbitrer : la traçabilité peut être préférée à l'effacement) | Un doublon ou une erreur ne se retire pas | M02, M06, M12, M16, M17 « Correction » | P3 | Hypothèse |

### 1.D Libellés, ambiguïtés, retours système

| # | Observation | Marins / missions | Catégorie | Impact | Preuves | Priorité | Statut |
|---|---|---|---|---|---|---|---|
| L-1 | **Chemins de remontée ambigus.** « Signaler une difficulté » (vers « Demandes bord–terre »), « Je suis bloqué » (statut « Bloquée »), « Signaler une anomalie » (fiche installation), « Discussion ». Aucun guide ; les marins ne savent pas lequel prévient réellement le responsable. Défaut structurel. | Lucas M02 ; Julien M03 ; Claire M06 ; Antoine M09 (4 missions) | Libellé incompréhensible / incohérence | Mauvais choix de circuit, doute sur la prise en compte | M02 « Hésitations » ; M03 « Termes » ; M06 « Termes » ; M09 « Hésitations » ; évaluation coordinateur M02, M06, M09 | **P2** | Hypothèse (4 missions) |
| L-2 | Étiquette « Demande bord–terre » pour un sujet interne au bâtiment (fuite signalée par un équipier, retard signalé par un chef de service). | Julien M03 ; Antoine M09 ; Lucas M02 | Libellé incompréhensible | Trompeur | M03, M09, M02 « Termes » | P2 | Hypothèse |
| L-3 | **Absence de confirmation après action.** La page ou le fil sert de confirmation implicite : attribution de tâche (M05), publication dans un fil (M06, M12, M16), publication d'annonce (M13), ajout d'un créneau (M10), « Sélectionner » / « Affecter » (M17), changement d'état de demande (M06). Bonnes confirmations ailleurs : clôture de maintenance et signalement (M03), création d'utilisateur et seuil (M18). Défaut structurel. | M02, M05, M06, M09, M10, M12, M13, M16, M17 | Incohérence d'interface | Doute (« je ne sais pas si c'est parti ») | M05, M06, M09, M10, M12, M13, M16, M17 « Retour du système » | **P2** (structurel) | Hypothèse |
| L-4 | **« Qui est prévenu » invisible.** Le blocage est notifié aux chefs (prouvé en base, M02) et les réponses de fil circulent (prouvé, M06), mais rien à l'écran ne le dit. | Lucas M02 ; Claire M06 ; Antoine M09 | Incohérence d'interface (retour système) | Les marins vont « le dire de vive voix » | M02 et M06 évaluation coordinateur ; M09 « Retour du système » | P2 | Notifications prouvées en base ; absence de retour écran : hypothèse |
| L-5 | Jargon et vocabulaire non Marine : « fils où je suis interlocuteur », « Interlocuteurs », « Actions décidées », « Responsable du dossier », « Ou toute une unité », « Public visé » / « Équipage (facultatif) », « Seuils de rôle », « RETEX » non expliqué, « Veille / Barre / Machine avant / Chef de garde », « Programme du bâtiment », « [Recette] » devant les intitulés, faute d'accord « 2 semaine · 0 vendredi · 0 week-end ». | M01, M03, M05, M06, M07, M09, M13, M16, M18 | Libellé incompréhensible | Ralentit la compréhension (« [Recette] » est une donnée de test) | « Termes » des missions concernées | P3 | Hypothèse |
| L-6 | Jargon de développeur affiché sur Feuille de service › Réglages : « Aucune liste n'est imposée par l'application : configurez ... propres à Bretagne (CLAUDE.md §6) ». | Cécile, M13 | Libellé incompréhensible | Contraire au principe « zéro jargon » | M13 §3 « Termes » ; évaluation coordinateur M13 | P2 à P3 | Hypothèse |
| L-7 | Boutons affichés mais refusés à un équipage à terre (« M'assigner », « Exécuter », « Valider »). Le 403 est clair et motivé, mais le bandeau « Lecture seule » ne dit pas que les réponses de fil restent permises, ni le circuit pour passer une consigne. | Ivan M12 ; Benoît M13 | Incohérence d'interface | Un clic de trop, doute sur ce qui reste possible | M12 « Retour du système », « Droits constatés » ; M13 §2 « Termes » | P2 | Hypothèse |
| L-8 | Aucun message explicatif sur un accès restreint ou un résultat vide (« Aucun » / « Aucune » sans distinguer « n'existe pas » de « non visible pour vous »). | Nora M11 ; Claire M07 | Incohérence d'interface | Le marin ne sait pas vers qui se tourner | M11 « Termes », « Verbatim » ; M07 « Retour du système » | P3 | Hypothèse |
| L-9 | Perte des champs saisis après le rejet « L'équipage est obligatoire sur un bâtiment à double équipage. » : le champ « Équipage » n'est pas marqué obligatoire et le message s'affiche sur l'annuaire. Identifiant généré, non choisissable. | Paul, M18 | Bug fonctionnel / incohérence | Ressaisie complète | M18 « Chemin » 3, « Hésitations » ; évaluation coordinateur M18 | P2 (perte) ; P3 (identifiant, choix possible) | Hypothèse |
| L-10 | Réglage des droits d'un chef difficile à trouver : « Paramètres » puis « Seuils de rôle » ; le menu « Utilisateurs et droits » ne contient que « Utilisateurs » ; « Valeur par défaut » affiché aussi sur les lignes non modifiées. | Paul, M18 | Fonction difficile à découvrir | Il faut déjà connaître le mot | M18 « Hésitations », « Termes » | P3 | Hypothèse |
| L-11 | Accueil chargé sans hiérarchie : « À faire » mélange 11 lignes (tâches, annonces, tickets, maintenance, formation, ronde), sans priorité hors « en retard » ; « accusé requis » noyé ; pastille « 18 notifications non lues » sans information. | Lucas, M01 | Parcours complexe / simple préférence d'un utilisateur simulé | Le marin ne sait pas par quoi commencer | M01 « Hésitations » | P3 | Hypothèse (impression d'agent IA) |
| L-12 | Calendrier dense et peu lisible (6 à 9 pastilles par jour, libellés tronqués, icônes sans nom ; repère « cette semaine » à deviner) ; « Autres actions » est une icône sans libellé (M03, M04). | Lucas M01 ; Antoine M08 ; Julien M03, M04 | Parcours inutilement complexe / fonction difficile à découvrir | Lecture difficile | M01, M08, M03, M04 « Hésitations » | P3 | Hypothèse |
| L-13 | Confusion des noms et titres : « Matelot Karim Equipier A » pour le personnage Lucas Morel ; « Quartier-maître Jade Chef Section A » contre « Bonjour Quartier-maître Chef Section A » ; grade non conforme au profil PM. | M01, M07 | Incohérence (données de recette, pas de droits) | Désorientation | M01 compte rendu ; M07 « Droits constatés » ; évaluation coordinateur M07 | P3 | Hypothèse (donnée de recette) |
| L-14 | « Suivi » désigne à la fois un menu (demandes) et des lignes automatiques du fil ; « Mon équipe » / « Synthèse » : point d'entrée peu clair (« Synthèse » mène à `/taches/#synthese`). | Claire M06 ; Antoine M08 | Libellé incompréhensible | Hésitation | M06 « Termes » ; M08 « Hésitations » | P3 | Hypothèse |

## 2. Classement par nature

Basé sur les comptes rendus et les évaluations du coordinateur, sans lecture du code. La liste « À faire plus tard » n'étant pas fournie, les fonctions marquées « arbitrage » sont à confronter à cette liste avant d'être retenues comme défauts V1.

| Nature | Observations |
|---|---|
| **Défaut technique probable** | B-1, B-2, B-3, B-4, B-5, B-6, B-7, B-8, F-1 (visa COMAEQ), F-3, L-9 (perte de saisie) |
| **Problème ergonomique** | L-1, L-2, L-3 (absence de confirmation, structurel), L-4, L-5, L-6, L-7, L-8, L-10, L-11, L-12, L-14, F-6, F-7, F-10, F-12, présélection sur « Paul Admin Navire » (P-3) |
| **Incohérence métier à arbitrer par le PO** | P-7, P-8, P-9, P-10, remontée au chef de secteur de B ou de A (M06), « Mes listes de quarts » vide pour le chef de service créateur, F-13, F-2 |
| **Fonctionnalité différée ou à confronter à « À faire plus tard »** | F-4, F-5, F-8, F-9, F-11, F-15, choix de l'identifiant (L-9). Ce sont des constats, pas des défauts V1 acquis. |
| **Questions de périmètre non confirmées** | P-1 à P-6 (section 3) |

## 3. Signalements de fuite de périmètre (transmis tels quels)

- **P0 potentiel à confirmer** (`qa-securite`) :
  - P-1 : `terre_classe`, formulaires de modification visibles sur une tâche et une demande du bord (M16).
  - P-2 : liste d'interlocuteurs de 19 personnes pour une cheffe de section (M05, M06).
  - P-3 : sélecteurs « Marin » / « Responsable du dossier » / « Marin à affecter » couvrant tout le bâtiment, équipage B inclus (M06, M09, M03, M14, M17).
  - P-4 : identité « Cdt A » à l'accueil de `cdt_b` après déconnexion de `cdt_a` (M13).
- **P2, à réévaluer si l'accès est réel** : menu d'administration visible pour de nombreux rôles (P-5) ; boutons « Modifier », « Nouvelle installation », « Valider une formation » (P-6).
- **À arbitrer par le PO** : P-7 à P-10.
- **Observations positives sur le périmètre** : M07 (listes de tâches et maintenance limitées à la section), M11 (recherche globale sans fuite sur 10 catégories), M18 (annuaire, création et seuils limités à Bretagne).

## 4. Points forts constatés

| Point fort | Preuve |
|---|---|
| La page Tâches donne en un coup d'œil charge par marin, absences, retards, blocages et échéances pendant une absence : point d'entrée le plus utile des chefs. | M05 « Avantage » ; M07 « Avantage » ; M08 « Avantage perçu » |
| Un blocage remonte seul sur l'accueil du chef avec le nom du marin. | M06 « Hésitations et détours », « Avantage » |
| Fils de discussion attachés à l'objet : historique conservé, notification orientée, réponse en un clic. | M06 ; M12 « Avantage » ; M16 « Avantage » |
| Circulation des notifications prouvée en base (blocage, réponses de fil, ajout d'interlocuteur). | M02 et M06, évaluation coordinateur |
| Clôture de maintenance claire (statut, nom, horodatage), signature par mot de passe sur installation critique, audit prouvé (`occurrence_validation_critique`, `ASSIGNED -> DONE`). | M03 « Retour du système » ; M04 évaluation coordinateur |
| Signalement formalisé : responsable nommé, fil de suivi, arrivée directe sur la demande. | M03 et M09 « Retour du système » |
| Consigne publiée en un formulaire avec suivi de lecture nominatif (accusés / lus / non lus) et versions conservées. | M13 §1 et §3 « Avantage perçu » |
| Refus 403 clair et motivé (« équipage à terre ») avec lien de retour. | M12 « Droits constatés », « Retour du système » |
| Périmètre bien tenu dans ce qui a été observé : listes de tâches limitées à la section, maintenance limitée à Propulsion, recherche globale sans fuite, annuaire et seuils limités à Bretagne. | M07, M11, M18 « Droits constatés » |
| Administration : message de création clair, mot de passe provisoire affiché une fois, seuils réinitialisables ligne à ligne, historisation annoncée. | M18 « Retour du système », « Correction d'erreur » |
| Vue COMANAV : dérives, indisponibilités, chaîne sécurité et logistique en une page ; cas du groupe électrogène (isolement, seuil dans 6 j) invisible sur papier. | M15 « Avantage perçu » |
| Brouillon enregistré automatiquement, durée calculée seule, explication du ticket correctif sur « Non conforme ». | M04 « Retour du système » |
| Formation : « Sélectionner » / « Refuser » en un clic, compteur de places mis à jour. | M17 « Avantage perçu » |
| Aide « Une tâche individuelle est créée pour chaque marin de l'unité, dans votre périmètre. » : claire et utile. | M07 « Termes ambigus » |

## 5. Grille des principes UX

Notes de 0 à 4 par l'observateur. Ce sont des indications fondées sur des agents simulés, pas des mesures d'usage réel.

| Principe | Note | Preuve |
|---|---|---|
| Action avant statistiques | 3 | « À faire » en premier à l'accueil (M01 ; M06 : blocage visible d'emblée). Réserve : « 0 retard » trompeur en M12, chiffres divergents en M15. |
| Navigation stable | 2 | Entrées d'administration visibles pour presque tous (P-5) ; relève cachée dans Paramètres (M13). Les accès par adresse tapée sont un comportement d'agent, non imputé à l'application. |
| Dévoilement progressif | 2 | Mot de passe de signature qui n'apparaît qu'après le choix de la conformité (M03, M04) ; menus trop larges ; accueil chargé (M01). |
| Discussion attachée à l'objet | 3 | Fils sur tâches, demandes, installations (M06, M12, M16). Réserve : qui est prévenu n'est pas dit (M02, M06). |
| Saisie une fois / réutilisée partout | 2 | Relevés de mesure en texte libre sans lien tâche-maintenance (M03) ; date prévue non reprise dans Début/Fin (M04). |
| Peu de ressaisies | 2 | Fiche papier vierge à ressaisir (M04) ; formulaire de création vidé après rejet (M18) ; conformité perdue au rechargement (M03, M04). |
| Cohérence visuelle stricte | 2 | « None » (M08, M13) ; « Valider » sur des absences déjà validées (M08, M10) ; « CLAUDE.md §6 » affiché (M13) ; noms affichés incohérents (M07, M13). |
| États et responsabilités compréhensibles | 2 | Statut « Assignée » après clôture (M03, M04) ; « En validation » contre « déjà terminé » (M14) ; lecture seule non expliquée (M13). Positifs : fiche tâche claire (M05), 403 motivé (M12). |
| Dense mais calme | 2 | Page Tâches efficace (M08) ; mais calendrier à 6-9 pastilles par jour (M08, M01) et accueil à 11 lignes (M01). |

## 6. Limites de l'exercice

1. **Simulation par des agents IA.** Les comptes rendus sont des impressions d'agents, pas des besoins avérés de marins. Aucune note ne vaut mesure d'usage réel ni validation par de vrais marins. Les durées de la rubrique « Mesures » sont « non mesurées » conformément au protocole ; seule la durée globale de l'agent est donnée par l'outil.
2. **Session non fermée entre `cdt_a` et `cdt_b`** (anomalie de procédure du coordinateur, M13). `browser_close` n'a pas été exécuté ; `cdt_b` a trouvé le navigateur connecté en `cdt_a`, s'est déconnecté puis reconnecté. L'isolation n'est pas respectée pour le début de cette exécution, ce qui rend P-4 difficile à interpréter. Les trois exécutions de M13 se sont succédé sans remise à zéro de la base.
3. **Boîtes de confirmation du navigateur non gérables.** Les agents `marin-*` n'ont pas l'outil `browser_handle_dialog`. Les actions protégées par `confirm()` (« Proposer la publication », « Supprimer le créneau », M10) n'ont pas pu être menées à terme : « proposer, contrôler, publier » est Non testé / Impossible à vérifier. D'autres confirmations ont pu être masquées de la même façon.
4. **Jeu de données incomplet.**
   - Échange de quart : aucune demande dans le jeu de données (« Mes échanges » vide), scénario non jouable (M10).
   - Feuille de service : aucune rubrique ni fonction configurée pour Bretagne (M14), volet non testé.
5. **Non testé ou non prouvé.**
   - Profil `terre_securite` non joué : Non testé.
   - Accusé de lecture non enregistré (M01).
   - Impression du compte rendu et clic sur « Imprimer » (M04).
   - Seconde réponse de fil de M12 non relue (« Exécuté, non prouvé »).
   - Connexion du nouveau compte de M18.
   - Pages « Flotte », « Vue COMANAV », « Plan du navire », « Paramètres » jamais ouvertes par les marins qui les signalent comme visibles.
   - Accès direct par identifiant hors périmètre (consigne de M11 de ne pas deviner d'adresse ; non tenté en M07).
   - Refus explicite sur candidature hors ressort (M17).
   - Annulation, modification, suppression non testées sur la plupart des missions.
6. **Autres biais.**
   - Données de recette visibles (« [Recette] », noms de personnages qui ne correspondent pas aux comptes).
   - Beaucoup d'écrans ouverts par URL tapée (comportement d'agent).
   - Captures non toutes relues par les marins.
   - L'observateur n'a pas lu `2026-10-13-B-synthese.md` ni le code.
7. **Aucune correction ni fonction nouvelle n'est proposée.** Les fonctions absentes (F-4, F-5, F-8, F-9, F-11, F-15) sont des constats à rapprocher de la liste « À faire plus tard », pas des défauts V1 acquis.
