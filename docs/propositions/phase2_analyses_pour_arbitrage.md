# Phase 2 — analyses pour arbitrage (aucune implémentation)

Statut : **propositions**. Rien de ce document n'est implémenté. Chaque section donne les règles existantes (lues dans le code),
les problèmes constatés, deux options, ma recommandation et les impacts techniques. Les décisions attendues sont regroupées en fin de document.

---

## 1. Modèle mer / quai, appareillage, accostage, listes prévisionnelles

### Règle PO (décision)
Le quart concerne la mer, le tour de service le quai. Sur une journée ordinaire, pas de quarts à la mer et de tours à quai applicables simultanément ;
exceptions : jour d'appareillage, jour d'accostage, transition (périodes distinguées dans la journée). Un chef de liste peut préparer des tours à quai alors que
le bâtiment est encore à la mer (retour anticipé) sans que cette préparation soit applicable ni crée de conflit.

### Règles existantes
- Deux types de listes distincts : `Quart` (mer) et `ServiceGarde` (quai), même base `ListeServiceAbstract` : statuts `BROUILLON` → `PROPOSEE` → `PUBLIEE`,
  période `date_debut`–`date_fin`, créneaux horaires, version figée à chaque publication.
- **Aucun état « bâtiment à la mer / à quai »** n'existe. Le programme du bâtiment a des types « Escale, Arrêt technique, Exercice, Réunion » (pas d'appareillage ni d'accostage).
- La seule détection de chevauchement est faite **à l'échange de tours** (`quarts/echanges.py::conflits_marin` : autre garde ou quart *publié* au même moment). Ni la création, ni la publication
  d'une liste ne contrôlent l'exclusivité mer/quai.
- La feuille de service lit les tours **publiés** (`personnel_du_jour`) ; les échanges ne portent que sur les `ServiceGarde` publiés ; le calendrier lit les créneaux publiés.
- Une liste publiée est donc immédiatement **applicable** : il n'existe pas de « publiée mais pas encore applicable ».

### Problèmes
1. Une liste de quai préparée à l'avance et publiée devient aussitôt active (feuille de service, notifications, échanges, calendrier) et peut chevaucher des quarts réels.
2. Aucune garde-fou n'empêche la double affectation mer/quai (la démonstration d'origine en contenait : corrigé dans la démo dense, pas dans le modèle).
3. Les indicateurs de charge du prototype B additionnent heures de quart et jours de service, ce que la décision PO interdit.

### Option A — « mode d'application » sur la liste (recommandée)
Deux champs sur `ListeServiceAbstract` : `mode` ∈ {`PREVISIONNELLE`, `APPLICABLE`} et `applicable_depuis` (date, facultative).
- **Préparation** = `BROUILLON`/`PROPOSEE` (existant). **Publication** = `PUBLIEE` (existant) avec `mode=PREVISIONNELLE` par défaut si la période est à venir et que le bâtiment est à la mer (ou si le chef le demande).
- **Application effective** = action explicite « Appliquer à partir du … » (accostage, retour anticipé) : `mode=APPLICABLE`. Une liste dont la période commence est appliquée automatiquement si aucune liste de l'autre type n'est applicable ce jour-là.
- Une liste `PREVISIONNELLE` : visible des chefs et des marins concernés avec la mention « prévisionnel » ; **exclue** de la feuille de service, des conflits, des échanges, des indicateurs de charge et des notifications de service.
- **Règle d'exclusivité** vérifiée à l'application (et à la publication d'une liste `APPLICABLE`) : pour un équipage et un jour, un quart applicable et un tour applicable ne coexistent que si le jour est marqué **jour de transition** (case sur la liste ou événement de programme « Appareillage » / « Accostage », types à ajouter) et si leurs créneaux ne se chevauchent pas pour un même marin.
- Retour anticipé : « Appliquer » le tour à quai à partir d'une date **clôt** le quart à la mer à cette date (nouvelle version du quart, `date_fin` raccourcie), avec motif et trace.

Transitions : `BROUILLON → PROPOSEE → PUBLIEE(PREVISIONNELLE) → PUBLIEE(APPLICABLE)` ; retour `APPLICABLE → PREVISIONNELLE` possible avant la date d'effet (annulation du retour anticipé) ; rien n'est supprimé, tout est versionné (principe 7 du projet).

**Droits du chef de liste** : prépare (brouillon et prévisionnel) avec ses droits actuels (`peut_gerer_liste`) ; publie selon le seuil existant (`peut_publier_liste`) ; **applique** avec le droit de publier **et** la confirmation du commandant adjoint compétent ou du commandant pour les listes de bâtiment (proposition ; voir section 4).

**Échanges** : seulement sur listes `PUBLIEE` et `APPLICABLE` ; sur une liste prévisionnelle le bouton est absent. À l'application, les demandes d'échange en cours sont revérifiées (conflits).
**Notifications** : prévisionnel → chefs et publicateurs seulement ; application → marins concernés (« votre service à quai s'applique à partir du … »).
**Indicateurs de charge** : deux jauges **séparées** — heures de quart à la mer et jours de service à quai — calculées sur les seules listes `APPLICABLE` ; la charge prévisionnelle est affichée hachurée et jamais cumulée ; pas d'« heures de travail effectif » (non modélisées).

### Option B — régime du bâtiment (calendrier mer/quai)
Entité `RegimeBatiment` (équipage, début, fin, `MER`/`QUAI`/`TRANSITION`) alimentée par le programme ; les listes s'attachent à un régime et ne sont applicables que dans un régime compatible. Plus fidèle à la réalité opérationnelle,
mais impose une saisie du régime (nouvelle donnée à tenir à jour), une dépendance au programme et un nouveau moteur de règles.

### Recommandation
**Option A**, puis Option B plus tard si le besoin d'un calendrier de régimes apparaît. A répond au cas du retour anticipé, ne crée pas de saisie supplémentaire et réutilise les statuts existants.

### Impacts techniques (option A)
Migration (2 champs × 2 modèles) ; `conflits_marin`, `titulaire_du_jour`/`personnel_du_jour`, `echanges`, `calendar_app/evenements_sources`, notifications de publication, indicateurs ; nouveau contrôle d'exclusivité ; types de programme (ajouter Appareillage/Accostage) ;
affichage « prévisionnel » dans les vues ; ~15 fichiers, ~40 tests. Effort : moyen. Risque : régression sur la feuille de service (lit les tours publiés) : à couvrir par les tests de feuille existants.

---

## 2. Matrice des droits des modules sans service

### Règles existantes (mesurées et lues)
Voir `matrice_modules_sans_service.md` (matrice par fonction) et `permissions_appliquees.md`. Constats :
- tâches : attribution par niveau ≥ chef de section dans le **périmètre hiérarchique du marin visé** (un état-major a un périmètre bâtiment) ;
- formations : validation ≥ chef de section sur les marins du périmètre ; création de fiche : administrateur du bâtiment ;
- documents (cible = nœud) : rédaction ≥ chef de section, validation/publication ≥ chef de service, sur toute cible de son périmètre ;
- RETEX : validation ≥ chef de service, tout domaine du bâtiment ; le COMA référent du domaine est seulement trié en tête ;
- programme : état-major ou délégué (délégation existante `DelegationProgramme`) ; absences : validation ≥ chef de section sur le périmètre ; postes : ≥ chef de service sur toute cible.

### Problèmes
Un commandant adjoint agit sur tous ces objets pour **tout le bâtiment** alors que la règle validée limite son écriture à ses services. Le risque est faible pour le programme (objet de coordination) et plus net pour les absences, formations (validation de personnes) et RETEX (autorité de domaine).

### Option A — borner par la **cible** (service du marin ou du nœud) avec les services rattachés (recommandée)
Réutiliser `services_rattaches` : validation d'absences/formations et attribution de tâches limitées aux marins des services rattachés ; documents et postes limités aux nœuds de ces services (+ bâtiment pour la coordination) ;
RETEX validé par le COMA référent du domaine ; programme inchangé. Le reste passe par une **demande** adressée au chef de service concerné ou une délégation.
### Option B — borner par **responsabilité fonctionnelle** (domaine)
Droits dérivés d'une table « module × fonction » configurable par le commandant (ex. COMOPS valide le programme, COMAEQ valide absences et vie à bord). Souple mais crée une **seconde matrice de droits** à côté de `RoleLevel` : contraire au principe 10.

### Recommandation
**Option A**, dans l'ordre : absences et formations (validations de personnes) → documents et postes → RETEX → tâches. Un lot par module, avec tests positifs et négatifs par fonction et par équipage.
### Impacts
`services_rattaches` est déjà le point unique ; ajouter un helper « service de la cible » par module ; ~7 modules ; tests nombreux ; messages d'erreur 404/403 selon la politique harmonisée. **Questions PO** : le COMA voit-il le motif d'absence d'un autre service ? (je propose non) ; le COMA référent est-il seul valideur de son domaine RETEX ?

---

## 3. Délégation explicite aux commandants adjoints

### Règles existantes
Écriture d'un état-major limitée aux services dont `Service.commandant_adjoint` est sa fonction (`matrix/core/ecriture_service.py`). Services sans commandant adjoint : lecture seule pour l'état-major. Seule délégation existante : `DelegationProgramme` (programme du bâtiment).

### Problème
Absence d'un COMA, passation, coordination ponctuelle : aucune voie traçable pour qu'un COMA agisse sur le service d'un collègue, hors modification de la configuration (rattachement) qui change aussi la validation.

### Option A — délégation par marin, service, module et date de fin (recommandée)
Modèle `DelegationEcriture(delegataire, service, module?, debut, fin, accordee_par, motif)`. `services_rattaches(user)` y ajoute les services délégués **non expirés** : un seul point d'application, le bornage existant suit. Accordée par le commandant (ou administrateur du bâtiment) **ou** par le COMA titulaire du service (il délègue à un pair) ; durée maximale configurable ; révocation immédiate ; `AuditLog` + notification au délégataire et au titulaire.
### Option B — rattachement temporaire du service au COMA
Modifier `Service.commandant_adjoint` pendant l'absence : trivial mais change aussi le routage des visas et masque l'intention dans la configuration ; oubli de retour possible.

### Recommandation
**Option A**. Impacts : 1 modèle + migration, extension de `services_rattaches` (et de `niveau_ecriture_ui`), écran dans les réglages, tests par rôle ; les refus existants proposent « demander une délégation ». Effort : faible à moyen.

---

## 4. Publication des listes de quarts et alertes d'organisation

### Règles existantes
- Gérer une liste : chef de liste **désigné** pour le périmètre exact (`ChefDeListe`) ou supervision du commandement (`peut_gerer_liste`).
- Publier : `peut_publier_liste` = supervision (commandant et au-dessus) **ou** rôle ≥ seuil `liste_service_publication` (défaut chef de service) **et** périmètre personnel qui couvre exactement celui de la liste. Un état-major (périmètre bâtiment) ne publie donc que des listes **de bâtiment**.
- Alertes d'organisation : proposer = niveau ≥ `feuille_service_configuration` (chef de service) sur le bâtiment ; valider = niveau ≥ `alerte_organisation_validation` (commandant). Les scénarios portent un `adjoint_sigle` (COMANAV adjoint sécurité, COMAEQ adjoint protection).

### Problèmes
1. Le rattachement service → commandant adjoint n'intervient pas dans la publication : un COMANAV ne publie pas la liste d'un service qui lui est rattaché (sauf liste de bâtiment), alors qu'il en est responsable.
2. Un chef de service **quelconque** peut proposer une modification d'organisation d'alerte du bâtiment, même pour un scénario relevant d'un autre commandant adjoint.
3. La validation unique par le commandant ne reflète pas la répartition sécurité (COMANAV) / protection (COMAEQ) décidée par le PO.
**Mesure à faire** : les droits de publication n'ont pas été mesurés par sondes sur les listes de service ; ce constat est issu de la lecture du code.

### Option A — router par le commandant adjoint compétent (recommandée)
Publier une liste de service : chef de liste **ou** commandant adjoint dont le service est rattaché (en plus du seuil et du périmètre), commandant toujours. Alertes : proposer = chef de service du service concerné ; valider = commandant adjoint dont `adjoint_sigle` correspond au scénario, à défaut le commandant. Application du bornage par `services_rattaches`.
### Option B — conserver les seuils et ajouter la délégation (section 3)
Sans changement de règle : le commandant (ou un délégataire) publie. Plus simple, mais ne résout ni 1, ni 2, ni 3.

### Recommandation
**Option A**, après une mesure par sondes. Impacts : `peut_publier_liste`, `peut_valider_organisation_alerte`, notifications des publicateurs (`publicateurs_a_notifier`), tests de chaque fonction ; effort moyen. Interaction avec la section 1 : « Appliquer » une liste suit la règle de publication.

---

## 5. Organigrammes fictifs en attente (Bretagne scindée, Jacques Chevallier, Auguste Bénébig)

### Règles existantes
`organigrammes_demo_detailles.md` : éléments documentés / décisions PO / hypothèses. La Bretagne actuelle a un service « Sécurité » rattaché au COMAEQ (contraire à la décision PO de scinder en sécurité technique-incendie-avaries (COMANAV, provisoire) et protection-vie à bord (COMAEQ)). Le BRF et le POM n'existent pas dans la démonstration. Le jeu dense **n'ajoute aucun service** : il réutilise la structure existante.

### Problèmes
Générer les structures BRF et POM revient à publier des hypothèses ; sans mention visible, un évaluateur peut les prendre pour des organigrammes officiels. Scinder la Bretagne modifie des données que des tests de démonstration utilisent.

### Option A — générer la scission de la Bretagne seulement, derrière une commande dédiée (recommandée)
`seed_demo_organisation` : scinde « Sécurité », ajoute les marins nécessaires, uniquement sur une base de démonstration ; bandeau « Données fictives — organisation non officielle » visible ; BRF/POM **non générés** tant que les 5 questions (découpage, effectif, COMOPS du BRF, POM sans commandant adjoint, Normandie/BordOps I) ne sont pas tranchées.
### Option B — tout générer maintenant avec la mention « hypothèse »
Plus riche pour les tests d'isolation entre bâtiments, mais publie des hypothèses non validées : contraire à la consigne.

### Recommandation
**Option A**. Impacts : nouvelle commande, migration de données de démonstration (renommer/recréer les services, rattacher les installations), adaptation de tests qui citent « Sécurité » (à recenser), champ ou réglage d'affichage de la mention fictive ; effort moyen.

---

## 6. Intégration des prototypes A + B (quarts et tours de service)

### Règles existantes
Direction UX validée (A pour la lecture quotidienne, B pour les responsables, impression distincte) ; prototypes statiques (`09_PROPOSITIONS_ET_PROTOTYPES/prototype_quarts_A_B`). Les pages actuelles (`quarts/liste_detail.html`, `liste_index.html`) affichent une grille par semaine ; deux types de listes distincts ; impressions séparées.

### Problèmes
Les prototypes mélangent quarts et tours dans un même bloc par jour : correct **en transition seulement** ; sur une journée ordinaire la règle mer/quai (section 1) fait qu'une seule des deux colonnes est applicable. La charge du prototype B somme des heures de quart et de service : à remplacer par deux jauges.

### Option A — intégration progressive derrière une préférence d'affichage (recommandée)
Commencer par la **vue quotidienne A des tours à quai**, puis des quarts à la mer ; onglet B « Par marin » pour les chefs de liste ; l'ancienne grille reste disponible jusqu'à validation ; le jour affiche le bloc applicable (quart **ou** tour, les deux en jour de transition, séparés dans le temps), les listes prévisionnelles en hachuré.
### Option B — remplacement direct de la grille
Plus rapide, mais change d'un coup l'écran le plus utilisé du bord et empêche la comparaison.

### Recommandation
**Option A**, **après** la décision de la section 1 (le contenu du jour en dépend). Impacts : templates, contexte de vue (regroupement par jour et par marin), CSS (réutiliser les composants asymétriques), captures de recette 1920/1366/390, aucune migration propre ; dépend de `mode`/applicabilité si option A de la section 1.

---

## Décisions PO attendues (synthèse)

| # | Décision | Recommandation |
|---|---|---|
| 1 | Modèle mer/quai : mode d'application sur la liste (A) ou régime du bâtiment (B) ; types « Appareillage/Accostage » ; clôture du quart au retour anticipé | A |
| 2 | Modules sans service : bornage par la cible (A) ou par domaine (B) ; ordre de livraison ; motif d'absence visible ou non | A, absences/formations d'abord |
| 3 | Délégation : par marin/service/module/date (A) ou rattachement temporaire (B) ; qui l'accorde ; durée maximale | A, commandant ou COMA titulaire |
| 4 | Publication des listes et validation des alertes : routage par le COMA compétent (A) ou statu quo + délégation (B) | A après mesure |
| 5 | Organigrammes : scission de la Bretagne seule (A) ; réponses aux 5 questions BRF/POM | A |
| 6 | Intégration A + B : progressive (A) ou remplacement (B) ; ordre quai puis mer | A, après la décision 1 |
