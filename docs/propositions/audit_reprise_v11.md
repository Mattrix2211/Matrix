# Audit de reprise V1.1 — phase 1

Statut : **audit et propositions**. Les correctifs déjà appliqués sont signalés ; rien n'est mergé ni déployé.
Les données de démonstration ne sont pas modifiées avant validation du §3.

## 1. Permissions du chef de secteur

### Diagnostic

Avec `chef_secteur_a` (niveau secteur : Propulsion / Moteurs), les listes de **services, secteurs et sections**
proposées dans les filtres montraient tout le bâtiment. Cause : `referentiel_organisation()`
(`matrix/core/contexte_batiment.py`) limitait les listes au bâtiment, jamais à la hiérarchie du compte.
Les **données** (matériels, installations, tickets, occurrences) étaient en revanche déjà bornées par
`build_scope_q`.

### Correctif appliqué

`referentiel_organisation()` applique maintenant le périmètre du compte (section, secteur, service ou
bâtiment) aux trois listes. Le chef de secteur ne voit plus que son service, son secteur et ses sections.
Un rôle de niveau « bâtiment » (commandant, état-major, administrateur d'unité) garde toute l'organisation
de son bâtiment.

### Matrice mesurée sur la base de démonstration (accès direct par URL)

Lecture : chaque objet du jeu de démo est ouvert par URL avec chaque compte ; « dans » = objet de son
périmètre, « hors » = hors périmètre.

| Compte (périmètre) | Matériel | Installation | Ticket | Occurrence de maintenance |
|---|---|---|---|---|
| `chef_secteur_a` (secteur) | hors : 404 | dans : 200 ; hors : 404 | dans : 200 ; hors : refusé | dans : 200 ; hors : refusé |
| `chef_section_a` (section) | hors : 404 | dans : 200 ; hors : 404 | dans : 200 ; hors : refusé | dans : 200 ; hors : refusé |
| `equipier_a` (section) | hors : 404 | dans : 200 ; hors : 404 | dans : 200 ; hors : refusé | dans : 200 ou 403 ; hors : refusé |

Aucun accès hors périmètre n'a abouti : les droits sont tenus côté serveur. Le défaut observé était donc
un défaut d'**affichage des sélecteurs**, plus un défaut de **réponse** (voir §2).

### Reste à faire pour clore l'audit

- Rejouer la matrice avec les profils COMAEQ, chef de service, commandant, équipages A et B.
- API (`/api/…`) : même matrice, avec lecture et écriture.
- Recherche globale et pages de détail Tâches et Anomalies.
- Écritures hors périmètre (création, modification, suppression) : tests automatisés permanents.

### Question d'arbitrage

Un COMAEQ est une responsabilité transversale : doit-il voir **tous** les services du bâtiment, ou
seulement ceux dont il est l'adjoint responsable (`Service.commandant_adjoint`) ? Le comportement actuel
est « tout le bâtiment ». La réponse change le périmètre de son calendrier, de ses tâches et de ses listes.

## 2. Ticket « introuvable »

### Cause

Ce n'est ni une route cassée ni une erreur de données : `TicketDetailView` répond
`HttpResponseBadRequest('Ticket introuvable')` quand le ticket est absent **ou hors périmètre**
(volontairement indiscernable, pour ne pas révéler l'existence de l'objet). Cette réponse est un code 400
en texte brut, sans gabarit : d'où la page blanche. Le même défaut touchait l'ouverture d'une occurrence
de maintenance.

L'identifiant `8dc69cd1-…` vient de **votre** base locale (port 8800) : je ne peux pas la consulter. Dans
ma base de démonstration, les trois tickets hors du secteur de `chef_secteur_a` produisent la même réponse.
Si ce ticket existe bien pour un chef de service, c'est qu'il est hors du secteur du compte testé.

### Correctif appliqué

- Ticket et occurrence absents ou hors périmètre : vraie page 404 de Matrix, au même gabarit dans les deux
  cas, sans révéler l'existence de l'objet.
- Texte de la page 404 : « n'existe pas, a été déplacée ou n'est pas accessible avec votre compte ».

### À traiter ensuite

Les autres `HttpResponseBadRequest` « introuvable » (actions POST, une vingtaine) : message contextuel
dans la page plutôt qu'une réponse brute. Je les convertirai avec le composant de dialogues.

## 3. Organisation fictive proposée pour la démonstration (à valider)

Les données actuelles portent des noms de test (« Coma Comops », « Equipier A2 »…) qui apparaissent dans le
bandeau et les listes. Je propose de reconstruire la base de démonstration **isolée** autour de trois unités.

### Unités

| Unité | Type | Équipages | Rôle dans la démo |
|---|---|---|---|
| Bretagne (D 655) | FREMM | A et B | Unité complète : toutes les fonctions, tous les scénarios |
| Jacques Chevallier (A 725) | BRF | un seul | Unité légère : isole les droits d'un autre bâtiment, silhouette BRF |
| Auguste Bénébig (P 779) | POM | un seul | Unité légère : silhouette POM |

### Bretagne — organisation

- **Commandement** : un commandant et un commandant en second par équipage.
- **Commandants adjoints** : COMOPS, COMANAV, COMAEQ, chacun avec un titulaire par équipage.
- **Services** : Opérations (COMOPS), Navigation (COMANAV), Propulsion et Énergie, Sécurité (COMAEQ).
- **Secteurs et sections** : deux secteurs par service au plus, une à deux sections par secteur.
- **Personnel** : environ 25 marins fictifs, grade et fonction cohérents, noms vraisemblables (aucun nom
  de rôle dans le nom de famille).
- **Cas particuliers** : un poste de COMAEQ vacant (équipage B) pour le visa exceptionnel du commandant ;
  un marin désactivé ; un marin passé d'un équipage à l'autre (désignation inopérante) ; un BSC et un
  rédacteur délégué.

### Profils de recette (identifiants fictifs)

| Profil | Équipage | Sert à tester |
|---|---|---|
| Marin (matelot) | A | Espace personnel, refus hors secteur |
| BSC rédacteur | A | Rédaction de la feuille de service |
| Chef de section | A | Périmètre section |
| Chef de secteur | A | Périmètre secteur (le cas signalé) |
| Chef de service | A | Visa service, périmètre service |
| COMAEQ | A | Visa final, correction, renvoi |
| Commandant | A | Vue bâtiment, visa exceptionnel |
| Chef de secteur | B | Séparation stricte des équipages |
| COMAEQ | B | Poste vacant |
| Marin | Jacques Chevallier | Isolement entre bâtiments |

### Scénarios de bout en bout

1. Anomalie signalée par un marin, convertie en ticket correctif, affectée, réalisée, validée par son chef.
2. Maintenance préventive prévue, fiche imprimée, exécution, compte rendu, validation.
3. Feuille de service : rédaction, visa secteur, visa service, renvoi par le COMAEQ, correction, publication,
   rectificatif.
4. Quarts à la mer et tours de service à quai publiés, échange de service.
5. Refus : accès par URL à un ticket d'un autre secteur, d'un autre équipage, d'un autre bâtiment.
6. Notifications et historique cohérents avec ces étapes.

Contrainte de qualité : tous les liens générés pointent vers des objets existants ; un test parcourt la
base de démonstration et ouvre chaque lien.

## 4. Module Rondes — inventaire des dépendances

Le module est branché à ces endroits (hors application `rondes` elle-même) :

| Domaine | Fichiers |
|---|---|
| Installation et routes | `matrix/settings.py` (application et deux tâches planifiées), `matrix/urls.py` |
| Navigation et modules | `matrix/core/navigation.py`, `matrix/core/modules.py`, `matrix/core/icones.py`, `matrix/core/role_thresholds.py` |
| Recherche | `matrix/views.py`, `matrix/templates/search.html` |
| Accueil et tableaux de bord | `dashboard/aujourdhui.py`, `dashboard/a_faire_presentation.py`, `dashboard/comanav.py`, `dashboard/pret_appareillage.html`, `dashboard/detail_session_appareillage.html` |
| Calendrier | `calendar_app/sources.py`, `evenements_sources.py`, `api_views.py`, `views.py`, `calendar/index.html` |
| Notifications | `notifications/liens.py`, `notifications/tasks.py` |
| Droits et équipages | `matrix/core/scopes.py` |
| Données de démo et documents | `seed_demo.py`, `README.md`, `docs/REFERENCE.md`, `RECETTE.md`, `UX.md`, `DEMO.md` |

Plan de retrait : retirer routes, navigation, intégrations, tâches planifiées, gabarits et données de démo ;
**conserver** l'application `rondes` réduite à ses modèles et ses migrations, pour garder les données
historiques jusqu'à votre autorisation de suppression définitive.

## 5. Harmonisation des intitulés

| Raccourci de l'accueil | Page atteinte | Intitulé du menu latéral | Titre de la page | Recommandé |
|---|---|---|---|---|
| Mon quotidien | Aujourd'hui | Aujourd'hui | « Bonjour … » | **Aujourd'hui** partout |
| Mon équipe | Calendrier filtré sur l'équipe | Calendrier | Calendrier | **Calendrier de l'équipe** |
| Suivi | Difficultés signalées | Difficultés signalées | (sous-titre) | **Difficultés signalées** |
| Synthèse | Tâches (ancre synthèse) | Tâches | Tâches | **Synthèse des tâches** ou onglet « Synthèse » dans Tâches |

À arbitrer : garder « Mon quotidien » comme libellé du groupe de menu, mais pas comme nom de page.

### Terminologie « COMA »

« COMA » désigne un commandant adjoint sans préciser lequel. Occurrences visibles à reprendre :

- **RETEX** : « COMA référent » (liste des domaines, détail, formulaire, notification).
- **Organisation d'alerte** : « COMA responsable », « COMA par défaut », message « COMA responsable inconnu ».
- **Modèle `Service`** : nom de champ technique à conserver ; seul le libellé visible change.

Proposition : « commandant adjoint » quand la fonction n'est pas précisée, la fonction exacte (COMANAV,
COMOPS, COMAEQ) quand elle l'est. Les identifiants techniques et les permissions ne sont pas touchés.
Le glossaire du Guide du marin 2023 n'est pas disponible dans mon environnement : j'applique les
intitulés déjà arbitrés dans Notion et j'attends le guide pour valider la liste complète.

## 6. Impression de la fiche de maintenance

La fonction **existe** et n'a pas été oubliée : « Imprimer la fiche » figure dans le menu discret de la
fiche d'exécution (icône ⋯) et sur chaque ligne de la liste des occurrences. Elle n'est pas visible sur la
page d'exécution elle-même, d'où votre recherche.

Correctif prévu : bouton « Imprimer la fiche » visible dans l'en-tête de la page d'exécution, avant le
début de l'intervention, et rappel après la clôture. La mise en page A4 compacte est déjà livrée (565f6d7).

## 7. Référentiel des bâtiments et silhouettes

### État du modèle

`org.Ship` porte nom, code, type d'unité (navire, école…), classe (texte libre), double équipage et
archivage. Il ne porte ni numéro de coque, ni trigramme, ni port-base, ni statut, ni silhouette.

### Plan d'intégration

1. Nouveau modèle `TypeBatiment` : code, libellé, ordre, silhouette (fichier), actif. Modifiable en
   administration, sans code.
2. Nouveau modèle `ReferenceBatiment` : catalogue importable de la circulaire 2025 (nom, coque, trigramme,
   type, classe, port-base, statut, date du statut, source). Séparé de `Ship` : seules les unités
   réellement utilisées dans Matrix deviennent des `Ship`.
3. `Ship` reçoit un lien facultatif vers sa référence et un type, plus le numéro de coque.
4. Import idempotent depuis le référentiel Notion, avec les statuts `référence 2025 / à vérifier`,
   `confirmé`, `essais`, `retiré`. Jamais « actif 2026 » par défaut.
5. Administration : ajout, modification, archivage d'un bâtiment, ajout d'un type, remplacement d'une
   silhouette. Repli neutre si le type n'a pas de silhouette.
6. Bandeau : silhouette du type à côté du nom du bâtiment (Bretagne, Jacques Chevallier, Auguste Bénébig),
   en bureau et en mobile.

### Blocage

Les fichiers du **Guide du marin 2023** (pages 60 à 63) ne sont pas dans mon environnement : le dossier
de référence ne contient que sa notice. Je n'intègre aucune silhouette tant que je n'ai pas les originaux.
Il faut aussi confirmer le droit de reproduire ces illustrations dans le dépôt. En attendant, le bandeau
garde son pictogramme actuel.

### À vérifier avant import

- Graphie « Jacques Chevallier » (la circulaire imprime « Chevalier ») : retenue d'après le référentiel.
- Numéro de coque du SNA De Grasse : non fourni, à ne pas inventer.
- Unités à ne pas doter d'équipage ni de feuille de service : drone Canopus, gendarmerie maritime.
- Types sans silhouette vérifiée : SNA et SNLE.
