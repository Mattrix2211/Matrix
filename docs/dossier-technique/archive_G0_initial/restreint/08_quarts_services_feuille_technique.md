# Chapitre 8 (technique) — Quarts, services, feuille de service, échanges, absences : mécanismes

> **Diffusion restreinte.** Complète `diffusable/08_quarts_services_feuille.md` (à lire d'abord). **État décrit :** état B (`6d6d0be`), non fusionné dans `main`. Les écarts avec les décisions du PO sont dans `ECARTS_DECISIONS_CODE.md`.
> **Pour qui :** développeurs, administrateurs. **Ce que vous y trouverez :** les modèles de `quarts` (22) et `absences` (1), les règles de droits exactes, la mécanique des listes, de l'activation, des échanges et de la feuille de service, les tâches planifiées et les points d'entrée.

---

## 8T.1 Les modèles

| Modèle | Rôle | Particularités |
|---|---|---|
| `ChefDeListe` (`quarts/models.py:174`) | Désignation d'un marin pour **un** périmètre (bâtiment, service, secteur ou section) et un **type** (`QUARTS`, `QUAI`) | Type vide = désignation historique : aucun droit tant qu'elle n'est pas qualifiée ; `origine`, `qualifiee_par`, `qualifiee_le` |
| `Quart` (`:617`), `ServiceGarde` (`:645`) | Les deux listes, qui héritent de `ListeServiceAbstract` (`:423`) | Période, périmètre unique (`_valider_perimetre_unique`), `equipage`, statut `BROUILLON` → `PROPOSEE` → `PUBLIEE`. `ServiceGarde` ajoute : `fonction` (obligatoire), `type_service` (texte libre), `formations_requises`, `delai_minimal_echange_heures`, `application` (`PREVISIONNELLE`, `ACTIVE`, `TERMINEE`), `prise_effet_prevue`, `prise_effet`, `active_par`, `active_en_qualite`, `version_prevision` |
| `CreneauQuart` (`quarts/models.py:765`), `CreneauServiceGarde` (`quarts/models.py:775`), sur `CreneauAbstract` (`quarts/models.py:735`) | Un poste, une plage, un marin facultatif | Un poste à plusieurs marins = plusieurs créneaux |
| `VersionQuart` (`quarts/models.py:837`), `VersionServiceGarde` (`quarts/models.py:846`) | Instantané figé à chaque publication | Jamais réécrit |
| `EchangeService` (`:855`), `EchangeServiceEvenement` (`:926`) | Échange de deux créneaux d'une même liste de gardes et son historique immuable | Statuts `DEMANDE`, `ACCEPTE`, `VALIDE`, `REFUSE`, `REJETE`, `ANNULE` ; libellés des tours **figés** à la création ; `applique_le`, `blocage_application` |
| `FeuilleService` (`:1222`) | Feuille d'une date, d'un bâtiment et d'un équipage | Statuts `BROUILLON`, `VISA_SECTEUR`, `VISA_SERVICE`, `VISA_COMAEQ`, `PUBLIEE` ; `structure_figee`, `empreinte_visee`, `rectificatif_ouvert_par` |
| `VersionFeuilleService` (`:1815`) | Instantané figé à la publication | Principe identique aux versions de liste, contenu différent |
| `RubriqueEnTeteFeuilleService` (`:1018`), `FonctionFeuilleService` (`:1074`) | Structure configurable par bâtiment (rubriques fixes ou saisies chaque jour ; fonctions de service et ordre) | Clés UUID ; `poste_recherche` pour retrouver le titulaire dans les créneaux |
| `RedacteurFeuilleService` (`:1052`) | Désignation nominative d'un rédacteur par bâtiment et équipage | Le droit de rédiger ne découle ni du grade ni du rôle |
| `ScenarioAlerte` (`:1862`), `PosteAlerte` (`:1899`), `ModificationOrganisationAlerte` (`:1922`) | Organisation d'alerte (sécurité, protection-défense) : postes à tenir, modifications proposées puis validées | Un poste dont la fonction est supprimée reste « non armé » |
| `ConfigurationActivation` (`:2261`) | Délais par bâtiment : rappel 30 min, alerte 0 min, escalade 15 min, seuil d'activation anticipée 30 min, durée maximale d'un remplacement 72 h | 1-1 avec le bâtiment |
| `AlerteActivation` (`:2277`) | Alerte persistante d'une liste prévisionnelle non activée | Unicité (liste, étape, version de prévision) : pas de doublon ni d'exécution concurrente ; un report incrémente la version |
| `MouvementBatiment` (`:2299`), `AlerteAccostage` | Accostage ou appareillage déclaré ; alerte « accostage sans liste applicable » | Erreur corrigée par annulation motivée, jamais par effacement |
| `RemplacementChefDeListe` (`:2350`) | Remplacement temporaire explicite d'un chef de liste des services à quai | Borné, tracé, révocable |
| `absences.Absence` (`absences/models.py:29`) | Indisponibilité d'un marin | Statuts `DECLAREE`, `VALIDEE` ; période en jours entiers ; `created_by` ≠ validateur |

## 8T.2 Les droits : fonctions exactes

| Question | Fonction | Règle |
|---|---|---|
| Qui gère une liste (créneaux, proposition) | `utilisateur_autorise_pour_perimetre` (`quarts/models.py:275`) et `peut_gerer_liste` (`:297`) | Désigné chef de liste pour **exactement** le périmètre et le type, ou supervision du commandement sur son bâtiment (`supervision_liste_sur`, niveau commandant et au-dessus). Sur double équipage, toujours dans **son** équipage |
| Qui publie | `peut_publier_liste` (`:355`) | Supervision du commandement, sinon seuil `liste_service_publication` **et** périmètre personnel égal à celui de la liste (`_perimetre_dans_scope_utilisateur`, `:308`) ; le commandant en second est exclu |
| Qui est notifié d'une proposition | `publicateurs_a_notifier` (`:373`) | Tous les utilisateurs actifs pour lesquels `peut_publier_liste` est vrai ; repli sur le créateur |
| Qui désigne un chef de liste | `_perimetre_autorise_pour_designation` (`quarts/listes_views.py:163`) | Supervision, ou niveau chef de service dont le périmètre personnel couvre celui visé : on ne délègue que sur ce qui est sous sa propre autorité |
| Qui active, reporte, retire une prévision | `habilitation_activation` (`quarts/activation.py:65`) | Le chef de liste désigné **pour exactement ce périmètre** (ni la supervision ni un rôle ne le remplacent) ou son remplaçant actif |
| Qui désigne un remplaçant | `designer_remplacant` (`quarts/remplacement.py:27`) | Le contrôle du droit est fait par l'appelant ; motif obligatoire, remplaçant actif du bâtiment, durée bornée (`remplacement_duree_max_heures`), pas de remplacement concurrent du même titulaire |
| Qui déclare un mouvement du bâtiment | `fonction_habilitee` (`quarts/mouvements.py:27`) | Titulaire COMAEQ de l'équipage à bord, ou commandant de cet équipage |
| Qui valide ou rejette un échange | `peut_valider_echange` (`quarts/echanges.py:205`) | `peut_gerer_liste` sur la liste de l'échange |
| Qui rédige la feuille | `peut_rediger_feuille_service` (`quarts/models.py:2065`) | Marin désigné dans `RedacteurFeuilleService` pour son bâtiment et **son** équipage |
| Qui désigne les rédacteurs | `peut_designer_redacteurs` (`:2076`) | Titulaire COMAEQ de l'équipage ; poste vacant : commandant de l'équipage (`_commandant_de_l_equipage`, `:2193`) |
| Qui vise | `peut_viser_secteur` (`:2159`), `peut_viser_service` (`:2170`), `peut_viser_comaeq` (`:2215`) | Paliers secteur et service : supervision du commandement ou seuil (`feuille_service_visa_secteur`, `…_service`) **et** périmètre du rédacteur ; palier COMAEQ : titulaire seulement, secours du commandant si le poste est **vacant** |
| Qui valide une absence | `peut_valider_absence` (`absences/services.py:62`) | Niveau d'écriture chef de section ou plus et marin dans le périmètre ; jamais soi-même |

**Point d'attention (A1).** `supervision_liste_sur` et `_supervision_sur_navire` comparent le **grade** au niveau commandant (7) : l'administrateur d'unité (8) les franchit. C'est le mécanisme de l'écart décrit en A1.

## 8T.3 Mécanique des listes

- **Proposition** : `ListeServiceAbstract.proposer` (`quarts/models.py:488`) passe au statut proposé, trace `liste_service_proposee` et notifie les publicateurs (niveau « Important », régime du type de liste).
- **Publication** : `publier` (`quarts/models.py:515`) fige une `Version…` (`creer_version`, `quarts/models.py:579`), trace `liste_service_publiee` ; seule la **première** publication notifie chaque marin affecté.
- **Modification d'une liste publiée** : `tracer_modification_creneau` trace et notifie le marin (niveau « Important », motif), rien pour un brouillon ou une proposition.
- **Publication à titre prévisionnel** : `publier_a_titre_previsionnel` (`quarts/activation.py:169`) : statut proposé obligatoire, prise d'effet prévue obligatoire, application `PREVISIONNELLE`, réévaluation du bâtiment.
- **Activation** : `activer_liste` (`quarts/activation.py:205`) verrouille la liste, vérifie l'habilitation, le statut (publiée + prévisionnelle), le **mode du bâtiment** (`mode_du_batiment`, `quarts/mouvements.py:41` : dernier mouvement valide ; `None` = non renseigné → refus ; mer → refus), l'activation anticipée (`seuil_activation_anticipee`, `quarts/activation.py:191`), les conflits (`conflits_activation`, `quarts/activation.py:134`), puis passe en `ACTIVE`, ferme les alertes, trace, **applique les échanges préparés**, notifie les marins.
- **Mode du bâtiment** : déduit des `MouvementBatiment` valides ; `intervalles_par_mode` (`quarts/mouvements.py:55`) découpe une plage par mode ; deux mouvements valides consécutifs ne mènent jamais au même mode ; un mode ne s'initialise qu'avant tout autre mouvement.
- **Alertes** : `quarts/alertes_activation.py` (rappel, alerte, escalade, report et retrait motivés) ; tâche planifiée `traiter_echeances_activation_minute` (60 s).
- **Régularisation** d'un quart : `quarts/regularisation.py`, à l'heure effective, motivée.

## 8T.4 Mécanique des échanges

`quarts/echanges.py` — fonctions publiques :

| Fonction | Rôle |
|---|---|
| `proposer_echange` (`:234`) | Le demandeur doit détenir son tour ; tour cible affecté à un autre marin ; aucun échange en cours sur ces créneaux ; `analyser_echange(verifier_delai=True)` ; trace et notification |
| `analyser_echange` (`:112`) | Renvoie la liste des raisons d'impossibilité : même liste, liste publiée et non terminée, même équipage, affectation inchangée, tour non commencé, délai minimal, **conflits** (`conflits_marin`, `:58`), **habilitations** (`habilitations_manquantes`, `:87`), **absences** (`absences_marin`, `:102`) |
| `accepter_echange` (`:268`) | Seul le marin sollicité ; contrôles refaits ; notifie le demandeur et les chefs de liste (`chefs_de_liste_a_notifier`, `:176`) |
| `valider_echange` (`:342`) | `peut_valider_echange` ; contrôles refaits ; liste `PREVISIONNELLE` → validation différée (`validation_differee`) ; sinon `_permuter` (`:372`) |
| `_permuter` | Verrouille les deux créneaux (`select_for_update`), échange les marins, fige une version de la liste, signale les divergences de feuille (`signaler_divergences_apres_echange`), trace et notifie |
| `rejeter_echange` (`:330`), `annuler_echange` (`:314`), `refuser_echange` | Refus du chef de liste ; annulation par le demandeur ; refus du marin |
| `appliquer_echanges_prepares` (`:403`) | À l'activation : revérifie chaque échange validé non appliqué ; un blocage est tracé (`blocage_activation`) et notifié |
| `reappliquer_echange`, `abandonner_echange` (`:446`) | Nouvelle tentative ; abandon motivé (motif obligatoire) |
| `annuler_echanges_du_creneau` | Annule avec explication les demandes en cours quand un créneau est supprimé |

Traces : `EchangeServiceEvenement` + `AuditLog` (`echange_service_<action>`). L'échange est **limité** aux listes de services de garde (docstring du module : non étendu aux quarts).

## 8T.5 Mécanique de la feuille de service

- **Création et circuit** : `proposer` (`quarts/models.py` `FeuilleService.proposer`) fixe `secteur_redacteur` et `service_redacteur` d'après le profil du rédacteur, saute le visa de secteur si son niveau atteint chef de secteur, enregistre l'`empreinte_visee` ; `viser_secteur`, `viser_service` (`:1557`), `viser_comaeq` ; `renvoyer` (`:1687`) remet en brouillon avec motif et **réinitialise tout le circuit** ; transitions protégées par `_transition` (`TransitionDejaEffectuee` en cas de double soumission).
- **Publication** : `_publier` crée une `VersionFeuilleService` ; refus si le contenu (affectations, alertes) a changé depuis le dernier visa (`_refuser_visa_perime`, trace `feuille_service_visa_perime`).
- **Visa exceptionnel** du commandant si le COMAEQ est vacant : version marquée (`visa_exceptionnel`), traces `feuille_service_comaeq_vacant` et `feuille_service_visa_comaeq_exceptionnel`.
- **Correction par le COMAEQ** : `modifier_entete_comaeq` ; `quarts/correction_legere.py` : une correction garde les visas seulement si elle ne change ni le sens ni une information opérationnelle ; sinon `CorrectionTropImportante`.
- **Rectificatif** : `ouvrir_rectificatif` (`quarts/models.py:1670`) repasse en brouillon, conserve la version publiée comme référence, trace les différences ; `quarts/rectificatif.py` calcule les divergences ; tâche planifiée `signaler_divergences_feuilles_15min`.
- **Structure figée** : `structure_figee`, `resynchroniser_structure` ; trace `feuille_service_structure_resynchronisee`.
- **Lecture** : `peut_lire_feuille_service` : tout marin de l'équipage propriétaire dès qu'une version est publiée ; sinon seulement les acteurs du circuit.
- **Double équipage** : `peut_ecrire_pour_equipage`, `_equipage_proprietaire` (défense en profondeur), `EquipageATerreMiddleware` (actions de formulaire exemptées listées au chapitre 4).

## 8T.6 Notifications et régimes

Les notifications des listes portent un **régime** (`QUAI` pour les services, `MER` pour les quarts) et une **catégorie** d'icône (`calendrier`, `terminee`…) ; le régime est une étiquette d'affichage, jamais un filtre (chapitre 9). Les échanges créent des `Notification` à cible générique `EchangeService`.

## 8T.7 Points d'entrée

| Route | Rôle |
|---|---|
| `/quarts/` | Page d'entrée (vue quotidienne et vue responsable, `quarts/entree.py`) |
| `/quarts/creer/`, `/quarts/quart/<id>/`, `/quarts/garde/<id>/` | Création et fiche des listes |
| `/quarts/garde/<id>/echanges/proposer/`, `/quarts/echanges/`, `/quarts/echanges/<id>/<action>/` | Échanges |
| `/quarts/mouvements/` | Mouvements du bâtiment |
| `/quarts/reglages/`, `/quarts/reglages/delais-activation/` | Chefs de liste et délais |
| `/quarts/feuille-service/…` | Feuille, rédacteurs, réglages, organisation d'alerte |
| Absences | `/absences/` (`absences/web_urls.py`) |

Tâches planifiées : `signaler_divergences_feuilles_15min` et `traiter_echeances_activation_minute` (`quarts/tasks.py`).

## 8T.8 Tests

`quarts/tests/` (609 fonctions de test dans le paquet, `absences` : 21). Habilitations historiques : `quarts/tests/test_habilitations_historiques.py` (selon la consolidation `mer_quai`). Échanges : tests des états et blocages à l'activation.

## 8T.9 Limites et éléments non vérifiés

- ⚪ PostgreSQL : les verrous (`select_for_update`) et les unicités partielles ont leur comportement de référence sur ce moteur ; non rejoué.
- ⚪ `peut_publier_liste` itère sur les utilisateurs actifs pour trouver les destinataires (`publicateurs_a_notifier`) : comportement connu ; aucune mesure de performance faite.
- ⚪ Le détail des écrans (vue quotidienne, vue responsable) n'a pas été rejoué dans un navigateur.
- 🔵 L06, L08, L09, L10, L27 non développés ; voir `ECARTS_DECISIONS_CODE.md`.

---

**Sources (état B).** Références en ligne ; `couverture/etat_B/MODELES.md` (22 modèles `quarts`, 1 `absences`) ; comptes rendus de lots `docs/dossier-technique-v12/P_LOT_L02_COMPTE_RENDU.md` (listes de quarts et désignations vis-à-vis de l'archivage) ; propositions `docs/propositions/mer_quai_*.md`.
