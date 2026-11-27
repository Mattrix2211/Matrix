# L30 — Confidentialité et cloisonnement des passations

Branche `claude/l30-passations-cloisonnement-v11`, créée à partir de `58691cc` (L06 clos). Code final testé et relu : `53bffa5` (voir §10). Décisions : ARB-01, ARB-02, ARB-06, AC-03, AC-15 (`docs/DECISIONS_PO.md`). Écarts traités : A14, NE-06, vérification V01 de L29.

## 1. État initial

La synthèse de passation (`org.SynthesePassation`) est un instantané JSON du bâtiment figé à la relève (`dashboard/passation.py`). Avant L30 :
- `syntheses_visibles` bornait par bâtiment et par équipage : le commandement lisait tout, les chefs (`peut_superviser`) des deux équipages de la relève lisaient **tout le bâtiment** (A14, NE-06) ; un marin sans fonction de chef, un administrateur technique et tout chef d'un troisième équipage étaient exclus ;
- le contenu ne portait aucune information d'appartenance : chaque ligne était une simple légende (titre, détail, lien), et des compteurs (totaux, « … et N autres », accusés manquants) étaient calculés sur tout le bâtiment ;
- aucun partage n'existait.

## 2. Cartographie des surfaces

| Surface | Expose du contenu de passation ? | Traitement L30 |
|---|---|---|
| Page `/dashboard/passation/<id>/` | Oui | contenu **filtré à la lecture** par périmètre, partage et totaux recalculés |
| Export PDF et impression (`…/pdf/`, bouton Imprimer) | Oui | même filtre (même gabarit, même contexte) |
| Accès direct par identifiant | Oui | 404 hors du bâtiment ; 200 filtré dans le bâtiment ; ligne inconnue ou hors portée : 404 |
| Réglages (liste des synthèses) | Métadonnées (équipages, date) | pas de contenu ; visible de tout marin du bâtiment ; l'administrateur général sans fonction n'a pas de bâtiment : rien |
| Notifications | Verbe sans contenu ; lien | le lien n'est résolu que pour un utilisateur autorisé (`syntheses_visibles`) ; la notification de partage ne cite pas la ligne |
| Recherche globale (`/search/`) | Non (la synthèse n'est pas indexée) | test : aucune ligne de passation renvoyée |
| API REST | Non (aucun point d'entrée `passation`) | test d'absence ; l'API des tableaux (`/api/dashboard/`) est prouvée (V34) |
| Calendrier | Non | — |
| Administration Django | Non (`SynthesePassation` et `PartagePassation` non enregistrées) | test d'absence |
| Pièces jointes et médias | La synthèse **ne contient aucun fichier** ; ses liens mènent à des objets qui gardent leurs propres droits | les médias sont servis par `matrix/core/medias.py` avec la règle de l'objet porteur ; preuve exécutée V35 |
| Liens de la synthèse vers les objets | Oui (titre, lien) | lire une ligne ne confère aucun droit sur l'objet (test : la tâche reste inaccessible au destinataire d'un partage) |
| Partage / révocation (nouveau) | Oui | `dashboard/passation_partage.py`, routes `…/partage/` et `…/revoquer/`, preuve V36 |
| Tâches planifiées | Génération à la relève (`generer_passation`) | contenu enrichi de la portée de chaque ligne ; aucune diffusion |

## 3. Architecture retenue

Aucun contrôle d'accès parallèle : le périmètre de responsabilité est celui du profil (`UserProfile` : bâtiment, service, secteur, section, fonction de commandant adjoint rattachée à `Service.commandant_adjoint`) et le registre de L29 (règle `WEB-PASSATION`).

1. **Génération** (`contenu_passation`, version 2 du contenu) : chaque ligne porte une **clé stable** (`tache:12`, `anomalie:7`, …), sa **portée** (service, secteur, section résolus en remontant la hiérarchie, marins concernés) et un indicateur `partageable`. Toutes les lignes sont conservées (plus de totaux agrégés recalculés sur le bâtiment) ; le plafond d'affichage (30 lignes par groupe) s'applique à la lecture.
2. **Lecture** (`dashboard/passation_perimetre.py`, `contenu_visible`) : le serveur calcule la **couverture** de l'utilisateur et ne rend que les lignes qui la rencontrent ou qui lui sont partagées. Totaux, groupes et compteurs sont **recalculés sur le visible** : rien n'est masqué par l'interface, rien ne se déduit par un chiffre.
3. **Contenu antérieur** (version 1, figé avant L30) : les lignes n'ont pas de portée ; il reste intégralement lisible du commandement et du second, et n'est plus rendu aux autres (message explicite). Rien n'est réécrit ni recalculé.
4. **Partage** : table `org.PartagePassation` (migration `org.0019`), évaluée à la lecture.
5. **Équipage** : n'est pas un critère de lecture. L'équipage à terre garde la consultation de son périmètre, sans limite de durée. **Aucune exception nouvelle au régime d'écriture de l'équipage à terre** : le partage et la révocation sont des écritures ; ils sont donc refusés à l'équipage à terre (middleware existant, et règle reprise par `peut_partager` et `peut_revoquer` sans dépendre du middleware). Une autorité de l'équipage à bord les exerce ; un partage consenti par une autorité alors qu'elle était à bord reste révocable par l'autorité à bord de rang suffisant. Toute écriture sur les activités de l'équipage embarqué reste refusée.

## 4. Matrice des droits de consultation

| Fonction | Lit |
|---|---|
| Marin (équipier) | les lignes qui le concernent (tâche qui lui est assignée, maintenance ou ticket qui lui est confié, anomalie ou demande dont il est l'auteur ou le responsable, sa qualification) |
| Chef de section | sa section |
| Chef de secteur | son secteur (ses sections comprises) |
| Chef de service | son service (secteurs et sections compris) |
| Commandant adjoint (état-major avec fonction) | les services dont `commandant_adjoint` est sa fonction |
| Commandant en second, commandant | tout le bâtiment |
| Administrateur technique | aucun droit supplémentaire : il lit comme un équipier |
| Administrateur général sans fonction métier | aucun (aucun bâtiment) |
| Fonction métier cumulée explicitement | applicable dans son périmètre |
| Autre bâtiment | rien (404) |

Une ligne rattachée au seul bâtiment (anomalie ou annonce sans service, par exemple) n'est lue que du commandement et du second. Les lignes de **qualification** (dossiers individuels de formation) suivent les habilitations de leur propre module : elles se lisent par périmètre mais **ne se partagent pas**.

## 5. Partage ciblé (AC-03)

- **Qui partage** : l'**autorité hiérarchique** dont le propre périmètre couvre la ligne (chef de section, de secteur, de service ; commandant adjoint ; commandement : le bâtiment), ou le **marin pour ses propres contributions** (ce qu'il a lui-même produit : tâche créée, anomalie ou demande déclarée…). Une information qui **concerne** le marin mais a été produite par un autre (tâche assignée par un chef, qualification) lui est consultable, jamais diffusable : consulter, ou recevoir un partage, ne confère aucun droit de diffusion. Ni un partage reçu (pas de partage transitif), ni un statut d'administration ne confèrent ce droit ; une ligne non partageable (qualification) ne se partage pas.
- **Quoi** : une information individuelle désignée par sa clé ; jamais la passation entière ; **lecture seule**.
- **Avec qui** : un marin, une fonction (commandant adjoint ou fonction de service), une section, un secteur ou un service du **même bâtiment**. Les marins proposés (et acceptés par le serveur) sont ceux que l'**annuaire** de l'émetteur lui montre : le formulaire ne révèle aucun nom supplémentaire ; le partage transversal vers un ensemble se fait par section, secteur, service ou fonction. Le destinataire est évalué à chaque lecture : une mutation, un changement de fonction ou de bâtiment joue immédiatement.
- **Historique** : auteur, destinataire, date, titre de la ligne ; chaque partage et chaque révocation sont tracés dans l'`AuditLog` ; rien n'est supprimé.
- **Révocation** : par l'auteur du partage, ou par l'**autorité hiérarchique** (chef, commandant adjoint, second, commandant) dont le périmètre couvre la ligne et dont le rang n'est pas inférieur à celui de l'auteur : un subordonné ne défait pas le partage de son supérieur, un marin simplement concerné par la ligne ne révoque pas celui de sa hiérarchie, un statut d'administration ne confère rien. Une révocation retire tous les partages équivalents (même information, même destinataire) que le réviseur a le droit de retirer ; si un partage d'un rang supérieur subsiste, l'interface le dit. Effective à la lecture suivante.
- **Un partage par émetteur** : deux responsables qui partagent la même information avec la même cible ont chacun leur ligne d'historique et leur trace ; le partage simultané d'un même émetteur (double clic) est sérialisé par un verrou de la synthèse (PostgreSQL) et ne crée qu'un partage actif.
- **Historique** : visible de l'auteur du partage et de l'autorité hiérarchique de la ligne seulement ; le destinataire et le marin concerné voient « Partagé avec vous » ou leurs propres partages. La suppression d'un compte ou d'une unité laisse le partage inerte, avec le libellé figé du destinataire.
- **Notification** : le destinataire est prévenu sans que le titre de la ligne figure dans la notification.
- **Interface** : lien « Partager » sur chaque ligne partageable, page de la ligne (formulaire, historique, bouton « Révoquer »), mention « Partagé avec vous » côté destinataire et « Partagé (n) » côté autorité. Aucune refonte graphique : mêmes composants que le reste de Matrix.
- **Limite documentée** : ce qui a déjà été consulté, imprimé ou exporté avant une révocation reste chez son lecteur.

## 6. Anomalies A14 et NE-06

| Écart | État |
|---|---|
| A14 : un chef de section lit une tâche d'une autre section | **corrigé** (V01 et `test_passation_cloisonnement`) |
| A14 : un chef de service d'un autre service lit le même contenu | **corrigé** |
| A14 : un commandant adjoint lit hors de ses services | **corrigé** |
| NE-06 : le chef de l'équipage sortant lit la synthèse figée du bâtiment | **corrigé** : plus de lecture par équipage ; périmètre de responsabilité |
| ARB-01/02 : l'administrateur technique lit la passation | **corrigé** : il lit comme un équipier |
| « L'équipage montant lit tout » | **remplacé** par le périmètre de responsabilité |
| V01 de L29 | les trois écarts connus sont retirés ; les profils sans fonction de chef ouvrent la page (200) et ne lisent que ce qui les concerne ; témoins positifs ajoutés |

Modification de comportement attendue (documentée) : un marin du bâtiment ouvre désormais la page (auparavant 404) mais n'y lit que ce qui le concerne ; un chef d'un autre équipage du même secteur lit comme les autres chefs de ce secteur. Les tests existants `test_equipier_et_anonyme_exclus` et `test_chef_hors_des_deux_equipages_exclu` ont été remplacés par leurs équivalents au nouveau comportement (`test_equipier_ne_lit_que_ce_qui_le_concerne_et_anonyme_exclu`, `test_l_equipage_n_est_pas_un_critere_de_lecture`), plus stricts.

## 7. Critères d'acceptation et preuves

| Critère | Preuve |
|---|---|
| CA-L30-1 Chaque échelon ne lit que son périmètre | `test_passation_cloisonnement.MatriceDesEchelonsTests` (15 profils × 8 marqueurs, témoins positifs), V01 |
| CA-L30-2 Administrateurs sans droit supplémentaire | `test_l_administrateur_technique_n_a_pas_de_droit_metier_supplementaire`, `test_administrateur_general_sans_fonction…`, V01 |
| CA-L30-3 Partage ciblé sans ouvrir la passation | `PartageCibleTests`, V36 |
| CA-L30-4 Équipage à terre : lecture de son périmètre, aucune écriture (ni partage, ni révocation, ni modification de l'embarqué), sans limite de durée | `test_l_equipage_n_est_pas_un_critere…`, `test_equipage_a_terre_consulte_sans_partager_ni_revoquer`, `test_aucune_modification_des_activites_embarquees…`, V36 |
| CA-L30-5 Autre bâtiment invisible | `test_administrateur_general_sans_fonction_n_a_aucun_droit_et_autre_batiment_exclu`, V01 (équipier de l'autre bâtiment) |
| CA-L30-6 Informations indirectes (titres, compteurs, notifications, exports, métadonnées) | `test_les_totaux_et_compteurs_ne_comptent_que_le_visible`, `test_pdf_et_impression…`, `test_notification_du_destinataire_sans_fuite_du_contenu`, `test_aucune_recherche_ni_notification…` |
| CA-L30-7 Révocation, changement d'affectation, bénéficiaire en lecture seule, information confidentielle | `test_revocation…`, `test_changement_d_affectation…`, `test_le_beneficiaire_ne_peut_ni_modifier_ni_repartager`, `test_information_confidentielle_non_partageable` |
| CA-L30-8 Preuves héritées de L29 : `API-TABLEAUX`, `WEB-TABLEAUX`, `WEB-MEDIA` | V32 à V35 (retirées de `SANS_PREUVE_EXECUTEE`) |
| CA-L30-9 Non-régression du socle L06 | suites complètes, `matrix.tests.habilitation` |
| CA-L30-10 Le marin ne diffuse que ses contributions ; consulter ou recevoir un partage ne donne aucun droit de diffusion ; les autorités gardent le leur | `DiffusionEtAnnuaireTests`, V36, V37 |
| CA-L30-11 Les marins proposés et acceptés comme destinataires suivent l'annuaire de l'émetteur | `test_les_marins_proposes_et_acceptes_suivent_l_annuaire` |
| CA-L30-12 Aucune exception nouvelle au régime d'écriture de l'équipage à terre | `test_equipage_a_terre_consulte_sans_partager_ni_revoquer`, V36 (profils à terre) |

## 8. Écarts découverts hors passation et risques résiduels

- **Lecture des tableaux par un compte rattaché au bâtiment sans fonction** (V34) : l'API des tableaux de bord borne selon le rattachement du profil, non la fonction ; un administrateur technique rattaché au bâtiment lit les agrégats de tout le bâtiment. Hors passation ; consigné (`ecarts_connus`), à traiter avec le bornage de lecture par périmètre (rattaché à L32 « à confirmer »). Rattaché formellement à **L32** (CA-L32-7), exigence de confidentialité avant déploiement ; ne bloque pas L30.
- **Commandant adjoint et pièces jointes de tâches** (V35) : le droit de consulter une tâche suit le bâtiment, non les services de rattachement (écart V10 de L29). Rattaché formellement à **L32** (CA-L32-8), exigence de confidentialité avant déploiement ; ne bloque pas L30.
- **Contenu antérieur** : les synthèses figées avant L30 ne sont lues en détail que du commandement ; elles ne sont pas recalculées.
- **Lignes rattachées au seul bâtiment** : lues du commandement seul ; un chef de service n'y accède que par un partage.
- **Plafond de stockage** : 2 000 lignes par groupe dans le contenu figé (garde-fou) ; l'affichage reste plafonné à 30 par groupe après filtrage.
- **Consultation par l'équipage à terre** : la synthèse n'est pas filtrée par équipage. Les feuilles de service (exception ARB-05) restent propres à chaque équipage et hors de la synthèse.
- Les relations `partages_passation_*` vers `User` ne confèrent aucune autorité (lecture d'une ligne) : classées examinées (`relations_utilisateur_examinees.txt`).

## 9. Migration

`org.0019_partage_passation` : crée `PartagePassation` (table neuve, aucune donnée existante modifiée ; contrainte de cohérence « un seul destinataire »). Aucune donnée de `SynthesePassation` n'est migrée ni réécrite.

## 10. Résultats, relectures, archive

Le code final testé et relu est **`53bffa5`** (vérification terminale du PO, 27/11/2026) ; les commits suivants ne modifient que `docs/` et l'archive de preuves (`git diff --name-only 53bffa5..HEAD`). Le code du rapport précédent, accepté par le PO, était `3761fe9`.

**Vérification terminale (PO)** : (1) le droit de diffusion du marin se limite à ses contributions : l'information qui le concerne sans être sa production, et celle qui lui est partagée, se consultent sans se diffuser ; les autorités hiérarchiques gardent leurs droits (AC-03) ; (2) l'équipage à terre ne reçoit **aucune exception nouvelle** : l'exception ajoutée au middleware est retirée, partage et révocation lui sont refusés (middleware existant et règle reprise dans les services), sa consultation est conservée ; (3) les marins proposés et acceptés comme destinataires suivent l'annuaire de l'émetteur. Ces trois points ont nécessité une correction de code, d'où nouvelles suites complètes et nouvelle relecture.

| Exécution | Moteur | Tests | Résultat | Ignorés |
|---|---|---|---|---|
| Référence L06 `e94e186` | SQLite / PostgreSQL 16 | 4174 / 4174 | OK / OK | 22 / 22 |
| Rapport L30 accepté `3761fe9` | SQLite / PostgreSQL 16 | 4213 / 4213 | OK / OK | 23 / 22 |
| **Final `53bffa5`** | SQLite / PostgreSQL 16 | **4218 / 4218** | **OK / OK** | 23 / 22 |

+44 tests par rapport à la référence L06 (+5 depuis `3761fe9`) ; aucun test supprimé ni affaibli. Le test d'équipage à terre a été **remplacé par son contraire** conformément à la décision (« consulte sans partager ni révoquer »), et les destinataires de plusieurs tests sont passés de « marin » à « section » ou « service » parce que l'annuaire d'un chef ne montre pas les marins des autres unités. Le scénario de concurrence du partage ne s'exécute que sur PostgreSQL.

| # | Code relu | Verdict | Suite donnée |
|---|---|---|---|
| 1 | `04b817e` | À corriger : doublons de partage sous concurrence ; marin concerné révoquant sa hiérarchie ; mineurs | verrou, un partage par émetteur, rang de révocation, historique restreint (`71c7c7d`) |
| 2 | `71c7c7d` | À corriger : erreur 500 si l'auteur d'un partage est supprimé | gabarit robuste, message fidèle, compte sans profil (`0f19776`) |
| 3 | `0f19776` | Favorable ; deux tests de vocabulaire en échec aux suites complètes | libellés, second clic neutre, ligne partagée sans lien (`3761fe9`) |
| 4 | `3761fe9` | Favorable, aucun bloquant ni important | rapport accepté par le PO ; vérification terminale |
| 5 | `53bffa5` | **Favorable, aucun bloquant ni important** | code final |

**Mineurs consignés** (ne bloquent pas la clôture ; le PO accepte les mineurs de performance et de message de révocation simultanée) : un contenu corrompu où `auteurs` n'est pas une liste donnerait une erreur 500 à un marin non autorité (la génération produit toujours une liste) ; un auteur sorti du périmètre ou supprimé peut encore partager par appel direct au service, la voie web étant fermée par la lecture de la ligne (404) : défense en profondeur possible ; le message de la page de partage d'un marin à terre ayant reçu une ligne hors de son niveau est inexact ; requêtes supplémentaires de `peut_revoquer` et de la validation d'une fonction.

Migration `org.0019` rejouée sur SQLite et PostgreSQL 16 : mise à niveau, `makemigrations --check`, retour arrière à `org.0018`, restauration ; contenu antérieur inchangé.

Archive des preuves : `docs/recette/preuves/L30_preuves.tar.gz` (empreinte SHA-256 dans `L30_preuves.tar.gz.sha256`).
