# E.2 Catalogue des tests d'acceptation

Types : N nominal · R refus d'accès · L cas limite · H historique · G non-régression. Ces tests sont des **scénarios d'acceptation à écrire** ; aucun n'existe encore sous cet identifiant (certains sont déjà couverts par des tests de la suite actuelle, à identifier lors de la phase de développement).

| ID | Rôle | Type | Scénario |
|---|---|---|---|
| T-SEC-01 | Exploitant | R | Lancer `seed_demo*` sans variable d'activation explicite : refus avec message, aucune donnée écrite. |
| T-SEC-02 | Exploitant | R | Lancer `seed_demo*` avec la variable mais sur une base sans marqueur « démonstration » : refus. |
| T-SEC-03 | Exploitant | R | Instance en production (DEBUG absent) avec marqueur de démonstration en base : démarrage refusé. |
| T-SEC-04 | Exploitant | L | Compte existant homonyme : ni mot de passe ni profil modifiés ; la commande s'arrête avec la liste des collisions. |
| T-SEC-05 | Exploitant | R | Production avec `DJANGO_SECRET_KEY=change-me` (valeur de `.env.example`) : démarrage refusé. |
| T-SEC-06 | Exploitant | R | `DB_HOST` défini sans `DB_PASSWORD` : démarrage refusé. |
| T-SEC-07 | Tout marin | R | 25 mots de passe erronés : délai croissant journalisé (paramètres configurables), compte légitime récupérable. |
| T-ORG-01 | Chef de service habilité | R | Supprimer une section/secteur/service portant marins, listes, annonces ou documents : refus, proposition d'archivage, aucun effet de cascade. |
| T-ORG-02 | Chef de service habilité | N | Archiver puis réactiver une section : disparaît des sélecteurs, historique intact, marins non détachés. |
| T-ORG-03 | Chef de service habilité | L | Service/secteur portant du matériel ou des stocks : message clair, jamais d'erreur 500. |
| T-ORG-04 | Chef de secteur | N | Secteur sans section : le chef de secteur est l'échelon responsable ; ses marins voient et agissent dans le secteur. |
| T-ORG-05 | Marin transversal | R | Un marin rattaché à un secteur ne reçoit pas les droits des autres secteurs par effet de bord (sondes sections2/structure). |
| T-ORG-06 | Fonction « gestion de la structure » | N | Renommer/archiver/réactiver une entité de structure ; refus pour un équipier ; trace AuditLog avant/après. |
| T-ORG-07 | Gestionnaire matériel | R | Créer un matériel sans entité responsable : refusé. |
| T-CPT-01 | Commandant / admin d'unité | R | Supprimer un compte ayant tâches, difficultés ou traçabilité : refus, bascule vers désactivation. |
| T-CPT-02 | Admin d'unité | H | Désactiver un compte : tâches, anomalies, audits conservés et consultables ; auteur toujours affiché. |
| T-CPT-03 | Marin désactivé | R | Connexion refusée ; sessions ouvertes invalidées. |
| T-CPT-04 | Compte sans rattachement complet | R | Aucun accès aux listes, tâches, feuilles ou maintenance du secteur ; accueil neutre expliquant la démarche. |
| T-CPT-05 | Autorité habilitée | N | Autorisation explicite et tracée sur un compte incomplet : accès limité à ce qui est autorisé. |
| T-CPT-06 | Nouveau bâtiment / ancien bâtiment | N | Demande de rattachement, information de l'ancien bâtiment, confirmation du départ. |
| T-CPT-07 | Autorité habilitée | L | Pas de réponse de l'ancien bâtiment : régularisation avec justification obligatoire et trace. |
| T-CPT-08 | Marin muté | H | À la date effective : anciens droits retirés, nouveaux droits selon l'affectation d'accueil ; historique conservé. |
| T-CPT-09 | Chef de secteur | N | Tâches ouvertes d'un marin muté : réattribuées ou marquées « non affectée à un responsable » (jamais perdues). |
| T-DRT-01 | Admin technique | R | Ne peut ni viser, ni publier, ni valider un acte métier (feuille, liste, RETEX, fiche) sans fonction correspondante. |
| T-DRT-02 | Équipier | R | Consulte les documents de maintenance autorisés d'une autre section de son secteur ; ne peut ni modifier ni clôturer. |
| T-DRT-03 | Équipier | R | Accès à un autre secteur ou à un document sensible sans droit : refus côté serveur (UI, POST, API). |
| T-DRT-04 | Tous profils | G | Matrice de droits (sonde `matrice_droits`) : aucune cellule plus permissive qu'en V1.1. |
| T-TAC-01 | Chef | N | Créer une tâche en priorité normale, haute ou urgente. |
| T-TAC-02 | Chef de section | R | Abaisser une priorité imposée par le chef de secteur : refusé, message explicite. |
| T-TAC-03 | Chef de section | R | Attribuer une tâche hors de sa section : refusé. |
| T-TAC-04 | Chef de secteur | N | Attribuer directement et réaffecter ; ancien et nouvel assigné notifiés, changement tracé. |
| T-TAC-05 | Chef de section | N | Case « Validation du responsable requise » cochée : l'équipier déclare terminé, statut « À valider ». |
| T-TAC-06 | Chef de secteur | N | Approuver, ou demander une correction avec motif obligatoire ; la tâche repasse « En cours ». |
| T-TAC-07 | Chef de secteur | L | Chef de section absent, aucune suppléance activée : le chef de secteur valide directement. |
| T-TAC-08 | Équipier | N | Sans l'option : l'équipier termine directement, la réalisation est enregistrée (qui, quand, compte rendu). |
| T-TAC-09 | Chef | N | Tâche collective : coordinateur proposé = participant du grade le plus élevé. |
| T-TAC-10 | Chef | L | Égalité de grade : aucune proposition automatique, le chef choisit ; il peut aussi désigner un autre participant. |
| T-TAC-11 | Coordinateur | R | Peut déclarer le travail réalisé ; ne remplace pas un visa technique obligatoire. |
| T-TAC-12 | Équipier | N | Déclarer « Bloquée » : motif obligatoire, responsable notifié. |
| T-TAC-13 | Chef | N | Débloquer et reprogrammer sans créer d'anomalie ; le chef de secteur peut en ouvrir une. |
| T-TAC-14 | Équipier | L | Tâche non terminée en fin de journée : état explicite « Non réalisée — À reprogrammer », jamais reportée en silence. |
| T-TAC-15 | Chef | N | Attribuer à un marin dont la qualification est absente ou périmée : possible ; l'information est affichée à titre indicatif. |
| T-MNT-01 | Chef de secteur | N | Tâches générées depuis fiches et matériels ; occurrences visibles. |
| T-MNT-02 | Chef de secteur | N | Les six périodicités (hebdo, mensuelle, trimestrielle, annuelle, biennale, quinquennale) produisent la bonne échéance. |
| T-MNT-03 | Équipier | N | Réalisation effective en retard : prochaine échéance calculée à partir de la réalisation. |
| T-MNT-04 | Chef de secteur | L | Fiche à calendrier fixe réglementaire : l'échéance suivante ne dérive pas. |
| T-MNT-05 | Chef de secteur | H | Les retards sont conservés dans l'historique de la fiche. |
| T-MNT-06 | Équipier | N | Signaler outil manquant, inutile, inadapté, instruction ambiguë, information manquante. |
| T-MNT-07 | Chef de secteur | N | Les remarques sont visibles et conservées ; la liste d'outillage n'est jamais modifiée seule. |
| T-MNT-08 | Chef de secteur | N | Modifier la fiche de référence suite à une remarque, via le circuit de validation applicable. |
| T-DUR-01 | Chef de secteur | H | Durée initiale et historique des estimations conservés à chaque actualisation. |
| T-DUR-02 | Système | N | Avec ≥ 3 mesures valides : durée indicative = médiane des N dernières (hypothèse de travail). |
| T-DUR-03 | Système | L | Mesure aberrante (hors médiane ± k·MAD), attente ou interruption : exclue du calcul. |
| T-DUR-04 | Système | N | Temps écoulé et charge en heures-personnes mesurés séparément pour une tâche à plusieurs intervenants. |
| T-DUR-05 | Chef de secteur | N | Correction manuelle de la durée : prime, tracée, non écrasée silencieusement. |
| T-DUR-06 | Système | R | L'actualisation ne modifie jamais consignes techniques ni consignes de sécurité. |
| T-DUR-07 | Système | L | Moins de 3 mesures : la durée n'est pas modifiée. |
| T-ANO-01 | Chef de secteur | N | Une anomalie reçoit deux interventions successives ; liens conservés avec tâches, matériel, historique. |
| T-ANO-02 | Équipier | N | Clôturer une intervention : l'anomalie reste ouverte. |
| T-ANO-03 | Chef de secteur | N | Décider de la suite : intervention supplémentaire, demande d'information, ouverture d'anomalie ou clôture justifiée. |
| T-ANO-04 | Réparateur | R | Statut de ticket inconnu rejeté ; sauts de statut selon la décision PO à venir (F-04). |
| T-FDS-01 | Matelot | R | Lit la feuille publiée de son équipage ; ne peut ni créer, ni modifier, ni viser, ni publier (UI, POST, API). |
| T-FDS-02 | BSC | N | Prépare la feuille de service de son équipage. |
| T-FDS-03 | COMAEQ | N | Approuve ; la feuille est publiée numériquement. |
| T-FDS-04 | Suppléant COMAEQ habilité | N | Approuve pendant une suppléance active ; l'acte reste attribué au suppléant. |
| T-FDS-05 | BSC | H | Modification après publication : nouvelle version officielle, ancienne conservée. |
| T-FDS-06 | BSC | N | Après nouvelle version : alerte « réimprimer et remplacer la feuille affichée ». |
| T-FDS-07 | COMAEQ ou suppléant habilité | N | Échange de tours : décision finale du COMAEQ ou de son suppléant officiellement habilité. |
| T-FDS-12 | BSC / chef de liste | R | Instruit une demande d'échange mais ne peut pas la valider seul (UI, POST, API) ; le COMAEQ ou son suppléant décide. |
| T-FDS-08 | BSC | N | Fraction de service à quai configurable par bâtiment ; vacances signalées. |
| T-FDS-09 | BSC | L | Écart de composition : signalé et justifié, pas de blocage automatique injustifié. |
| T-FDS-10 | Équipage B à terre | R | Feuille propre à chaque équipage ; aucune validation ou modification croisée par le seul grade. |
| T-FDS-11 | Admin technique | R | Ne publie ni ne vise une feuille de service. |
| T-APP-01 | Chef de secteur | N | Un départ génère les contrôles à partir des fiches de référence applicables. |
| T-APP-02 | Section → Service → COMANAV | N | Circuit de validation complet avec trace de chaque signataire. |
| T-APP-03 | Chef de service | R | Contrôle obligatoire non vérifié : validation refusée. |
| T-APP-04 | Chef de secteur | N | Réserve justifiée possible sur un contrôle non critique ; motif obligatoire, visible à la validation. |
| T-APP-05 | Chef de service | R | Point critique non dérogeable : aucune réserve acceptée. |
| T-APP-06 | Chef de secteur | H | Référence approuvée modifiée : préparations ouvertes actualisées, réponses toujours valables conservées. |
| T-APP-07 | Chef de secteur | H | Contrôles modifiés ou ajoutés rouverts ; supprimés archivés ; signatures affectées invalidées. |
| T-APP-08 | Chef de service | H | Préparation clôturée : conserve sa version historique, non retouchée par une évolution ultérieure. |
| T-APP-09 | Tout marin | G | Aucun écran ne présente Matrix comme délivrant l'autorisation d'appareiller. |
| T-RTX-01 | Auteur | N | RETEX : auteur → chef de section (si présent) → chef de secteur → chef de service ; trace de chaque étape. |
| T-RTX-02 | Auteur | L | Secteur sans section : l'étape section est sautée sans blocage. |
| T-RTX-03 | Chef de secteur | N | Correction demandée sans motif : refusée ; avec motif : nouvelle version et revalidations nécessaires. |
| T-RTX-04 | Responsable qualité | H | On sait qui a proposé, modifié, validé ou rejeté, et quand. |
| T-RTX-05 | Chef d'un autre secteur | R | Un habilité hors circuit ne peut pas valider (régression d'AUD-045). |
| T-SUP-01 | Autorité compétente | N | Activer une suppléance explicite, temporaire, limitée à une fonction et un périmètre. |
| T-SUP-02 | Suppléant | R | Aucun droit hors de la fonction et du périmètre suppléés ; fin automatique à l'échéance. |
| T-SUP-03 | Système | L | Deux suppléances simultanées sur le même périmètre : refusées (un seul responsable actif). |
| T-SUP-04 | Suppléant | H | Les actes du suppléant restent attribués à leur auteur dans l'historique. |
| T-SUP-05 | Titulaire | N | Au retour : récapitulatif des actions réalisées pendant son absence. |
| T-SUP-06 | Titulaire | L | Retour anticipé ou fin de suppléance : règles de validation retenues appliquées. |
| T-SUP-07 | Suppléant | R | Visa dont l'exigence réglementaire est configurée et non satisfaite : refus explicite ; sans exigence configurée : aucun contrôle. |
| T-QUA-01 | Chef / titulaire de visa | R | Visa technique, fonction de service ou signature officielle avec exigence réglementaire configurée non satisfaite : refus explicite ; tâche ordinaire : jamais bloquée. |
| T-MAT-01 | Chef de service | N | Transfert entre secteurs du même service approuvé par le chef de service. |
| T-MAT-02 | Deux chefs de service | N | Transfert entre services : deux approbations puis application par l'administrateur habilité. |
| T-MAT-03 | Chef de secteur | N | Tâches ouvertes suivent le matériel ; réattribuées si nécessaire. |
| T-MAT-04 | Auditeur | H | Interventions et tâches clôturées restent accessibles après transfert ; trace avant/après. |
| T-MAT-05 | Admin habilité | R | N'applique pas un transfert non approuvé par les deux parties. |
| T-UX-01 | Marin | N | Accueil : tâches du jour, tours de service, actions en attente, urgences, infos utiles, sans défilement inutile. |
| T-UX-02 | Marin | N | Recherche globale centrée ; résultats limités aux droits d'accès. |
| T-UX-03 | Marin | N | Épingler et désépingler des entrées du menu ; préférence conservée par compte. |
| T-UX-04 | Marin | N | Tours à venir, à valider et effectués clairement distincts ; libellé « Mes tours de service(s) » conforme à la décision F-09. |
| T-UX-05 | Marin | N | Notification lue : retirée de la liste principale, conservée dans le centre de notifications ; « lue » ≠ « traitée ». |
| T-UX-06 | Tous | G | Aucun bouton inactif ni lien mort (sonde `liens_morts`) ; reprise de brouillon fonctionnelle. |
| T-UX-07 | Chef | N | Recherche de personnes : informations professionnelles pertinentes, sous réserve des droits. |
| T-UX-08 | Marin | N | Calendrier central : quarts, services, tâches, formations, maintenance dans une seule vue. |
| T-REG-01 | Développeur | G | Suite complète SQLite (3 829 tests V1.1 + nouveaux) verte. |
| T-REG-02 | Développeur | G | Suite PostgreSQL verte. |
| T-REG-03 | Développeur | G | Sondes `docs/audit-general-v11/sondes/rejouer_tout.sh` rejouées sur les deux moteurs. |
| T-REG-04 | Exploitant | G | Migration d'une base peuplée sans perte (comparaison avant/après). |
| T-REG-05 | Chef | G | Exports PDF, Excel et CSV de pilotage conservés et inchangés en contenu. |
| T-REG-06 | Équipier | G | Module d'absences : seules les corrections nécessaires, comportement existant préservé. |
| T-REG-07 | Tout marin | G | Route QR existante conservée, non étendue (DEC-PRE-04). |
