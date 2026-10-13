# Démonstration : parcours chef, marin et interlocuteur à terre

Version de démonstration avec données **entièrement fictives**. Elle n'est connectée à aucun système d'information de la Marine et ne constitue pas une solution homologuée (voir « Limites »).

## Préparer

```bash
python manage.py migrate
python manage.py seed_demo      # relançable sans doublon
python manage.py runserver
```

Connexion sur `/login/`. Tous les comptes ont le mot de passe **« pass »**, sauf `admin` : **« admin »**.

| Compte | Rôle fictif | Utilité dans la démonstration |
|---|---|---|
| `chef_service_a` (Gaël) | Chef de service Propulsion, Bretagne, équipage A | A publié le planning de la semaine |
| `chef_section_a` (Jade) | Chef de section, équipage A | Attribue, suit, lève les blocages |
| `chef_secteur_a` (Hélène) | Chef de secteur Moteurs, équipage A | Chef de liste, valide les maintenances |
| `equipier_a` (Karim) | Équipier, équipage A | Reçoit et exécute une tâche, signale la difficulté |
| `equipier_a2` (Lina) | Équipier, équipage A | Tâche en retard et tâche bloquée |
| `chef_secteur_b` (Ivan) | Chef de secteur, équipage B à terre | Répond dans le fil, lecture seule ailleurs |
| `cdt_a` / `cdt_b` | Commandants, équipages A et B | Annonce avec accusé ; validation de la relève |
| `second_a` (Cécile) | Commandant en second | Programme du bâtiment, stock sous le seuil |
| `coma_comanav` (Denis) | État-major COMANAV | Vue COMANAV du bâtiment |
| `terre_classe` (Tessa) | Suivi de la classe FREMM, à terre | Tableaux de bord de classe |
| `admin` | Administrateur général | Réglages (seuils de rôle, annonces, passation) |

Autres comptes : `coma_comaeq`, `coma_comops`, `chef_secteur_elec_a`, `equipier_elec_a`, `equipier_incendie_a`, `marin_b`, `admin_navire`, `terre_securite`, `terre_chef_securite`, ainsi que la frégate Normandie (`cdt_nor`, `chef_secteur_nor`, `equipier_nor`) et l'unité historique BordOps I.

## Les quatre vues du quotidien

Un fil de quatre liens (« Mon quotidien · Mon équipe · Suivi · Synthèse ») s'affiche en haut des pages concernées. « Mon équipe » et « Synthèse » n'apparaissent que pour qui peut attribuer des tâches.

| Vue | Où | Ce qu'on y voit |
|---|---|---|
| **Mon quotidien** | Menu « Mon quotidien » : *Aujourd'hui* et *Calendrier* | Tâches à faire, journée, échéances à traiter, quarts et gardes publiés, annonces à accuser |
| **Mon équipe** | *Calendrier* filtre « Mon équipe », *Quarts et gardes*, *Tâches* (attribution) | Planning publié, absences, tâches de l'équipe, attribution à un marin ou à une unité |
| **Suivi** | *Demandes bord–terre* et fil de chaque tâche, panneau de détail du calendrier | Conversation sur l'objet concerné, réponse du rôle à terre, comptes rendus |
| **Synthèse** | Bloc « Avancement de l'équipe » en haut des *Tâches* | Répartition par statut, retards, blocages à lever, décisions du chef |

Liens croisés : *Aujourd'hui* → calendrier ; synthèse → suivi et planning de l'équipe.

## Scénario principal (une quinzaine de minutes)

1. **Planning publié.** Connecté en `chef_service_a`, ouvrir « Quarts et gardes » : la liste « Planning Propulsion — cette semaine » (trois quarts de 8 h par jour, Veille / Barre / Machine avant) est **publiée**. Elle apparaît au calendrier de Karim et de Lina, et au calendrier du chef (filtre « Mon équipe »). Pour rejouer la publication : créer une liste en brouillon, affecter les créneaux, « Publier » ; avant publication rien n'apparaît au calendrier des marins.
2. **Affecter une tâche.** En `chef_section_a`, page Tâches, « Attribuer une tâche » (titre, marin, échéance, priorité, checklist facultative, pièces jointes sur la fiche). Une tâche peut aussi naître d'une annonce (« Créer une tâche »).
3. **Karim la voit sans ressaisie** dans « Aujourd'hui » (bloc « À faire » et « Ma journée »), au calendrier le jour de l'échéance et dans ses notifications, avec un lien direct. Il la démarre.
4. **Signaler un problème.** Sur la fiche, Karim clique « Signaler une difficulté » (résumé, responsable, priorité) ou « Signaler un blocage » avec motif obligatoire. Dossier déjà présent : « Fuite persistante sur un graisseur ».
5. **Répondre depuis un rôle à terre.** Jade ajoute Ivan (équipage B, à terre) au fil. En `chef_secteur_b`, Ivan lit et répond : c'est la seule écriture que sa lecture seule autorise.
6. **Effectuer l'action.** Jade assigne une action ; elle apparaît chez Karim dans « Aujourd'hui ». Karim coche la checklist et la termine.
7. **Clôturer.** Jade lève le blocage, passe le dossier à « Résolu » ; Karim confirme la clôture et rend compte (tâche « Terminée »).
8. **Constater.** Calendrier (échéances, quarts, programme) et cloche de notifications de chacun ; en `chef_section_a`, la **Synthèse** (avancement, retards, blocages) ; journal d'audit de la tâche.

## Autres fonctions à montrer

- **Checklist et pièces jointes de tâche** : éléments à cocher, avancement visible du chef, documents rattachés à la fiche.
- **Annonce → tâche** : `cdt_a` publie une annonce « Important » avec accusé requis ; Karim clique « J'ai pris connaissance » ; le commandant suit lus / accusés / non-lus, crée une tâche depuis l'annonce, et un **rappel unique d'accusé** relance les non-lus (délai réglable par `admin`).
- **Vue COMANAV** : en `coma_comanav`, menu Supervision : interventions, dérives, indisponibilités et logistique du bâtiment.
- **Prêt à appareiller** : synthèse de l'état du bâtiment pour le commandement.
- **Synthèse de passation** : à la validation de la relève A/B (`cdt_b` valide la relève proposée), une synthèse est générée ; activable ou non dans les Paramètres.
- **Stock avec mouvements** : Logistique, pièces sous le seuil ; la quantité résulte de mouvements tracés (entrée, sortie, inventaire, correction).
- **Programme du bâtiment** : `second_a` saisit un exercice, visible au calendrier du public visé.
- **Mobile** : la barre du haut se simplifie et le menu devient un tiroir sous 768 px ; l'usage de référence reste le poste fixe.
- **Variantes** : réaffecter ou replanifier une tâche (consigné au fil et à l'audit), tâche personnelle privée, relances automatiques, mentions `@identifiant`.

## Données fictives créées

- Frégates Bretagne (double équipage A/B) et Normandie, avec services, secteurs, sections et installations.
- Planning Propulsion publié pour la semaine, brouillon de la semaine suivante, garde de nuit publiée.
- Tâches : à jouer en direct (Karim), en retard (Lina), bloquée avec fil ouvert à l'équipage B (Lina), terminée, plus une tâche personnelle privée de Karim et une permission de Karim le lendemain de l'échéance.
- Demande en traitement avec réponse d'Ivan, annonce « Exercice incendie jeudi 14 h » à accuser, exercice au programme.
- Maintenances, tickets, anomalies, rondes, formations, stock sous le seuil, relève en attente.

## Limites

- **Démonstration, pas solution homologuée** : aucune homologation, aucune évaluation de sécurité.
- **Aucune donnée réelle** : noms, grades, matériels et événements sont fictifs.
- **Aucune connexion au SI de la Marine** : rien n'est échangé avec les outils du SSF ; pas de budget ni d'infrastructure associés.
- Les interlocuteurs d'une tâche sont limités au navire de cette tâche ; les réglages des tâches valent pour toute la flotte.
- Le mobile est dégradé proprement mais l'application vise le poste fixe.

## Grille de retour (étape humaine, marins et responsables)

À poser après la démonstration, en notant les réponses telles quelles :

1. Que faites-vous aujourd'hui pour attribuer une tâche et savoir si elle est faite ? Qu'est-ce qui change ?
2. Le planning de quart publié est-il lisible et fiable pour vous ? Que manque-t-il avant de vous y fier ?
3. Signaler une difficulté et obtenir une réponse de la terre : est-ce plus rapide que votre pratique actuelle ?
4. Parmi « Mon quotidien », « Mon équipe », « Suivi » et « Synthèse », laquelle ouvririez-vous chaque jour ? Laquelle est inutile ?
5. Les termes (COMANAV, quart, garde, relève, accusé) sont-ils ceux de votre service ? Lesquels corriger ?
6. Quelles informations manquent pour décider (chef) ou pour agir (marin) ?
7. Quelle donnée ne devrait jamais figurer dans l'outil, et quelles règles de diffusion attendez-vous ?
8. Seriez-vous prêt à l'utiliser à bord pendant un mois ? Sinon, qu'est-ce qui bloque ?
