# Guide de recette métier — démonstration Matrix V1.1 (données entièrement fictives)

Tous les comptes ont le mot de passe « pass ». La démonstration est isolée (base séparée, cette machine seulement).
Dates relatives à aujourd'hui : relancer `lancer_demo.bat` applique les migrations et complète les données, sans rien supprimer.

## Lancer
1. Double-clic sur `lancer_demo.bat` (après `setup.bat`). Ouvrir http://127.0.0.1:8800/.
2. Repartir de données neuves (efface uniquement la base de démonstration) : `python scripts\preparer_instance_test.py --reinitialiser`.

## Bâtiments
| Bâtiment | Mode | Particularité |
|---|---|---|
| Bretagne (2 équipages) | QUAI | jeu complet, quarts à la mer et services à quai, maintenance, logistique |
| Auguste Bénébig | QUAI | listes prévisionnelles à activer, alerte en retard, désignation historique à qualifier |
| Jacques Chevallier | MER | liste prévisionnelle activable seulement après l'accostage |

## Scénarios par profil
Chaque scénario : compte → actions → résultat attendu.

### 1. Matelot équipier — `equipier_a`
1. Accueil : « À faire », « Ma journée » (service, quarts, maintenance du jour), « Mes tours de service ». **Attendu** : une journée remplie, une alerte prioritaire (incendie) visible.
2. Menu « Quarts et tours de service » : « Mon prochain tour », « À traiter : 1 échange en attente de votre accord ». **Attendu** : demande d'échange de `equipier_a2` pour le 9 novembre (gradé de coupée 3).
3. Ouvrir l'échange (Plus → Mes échanges), l'accepter. **Attendu** : l'échange passe « en attente du chef de liste » ; `chef_secteur_a` en est notifié.
4. Tâches : cinq tâches dont deux urgentes. Maintenance : « Contrôle et graissage du treuil » en cours, « Graissage des paliers » en retard.
5. **Restriction** : aucune création de feuille de service (refus 403), pas de vue « Par marin (responsables) », pas de bouton Créer une liste.

### 2. Chef de secteur et chef de liste — `chef_secteur_a`
1. Quarts : onglet « Par marin (responsables) » : grille marins × jours, postes à pourvoir, charge de la semaine, « 1 échange à valider ».
2. Onglet « Listes » : listes à tous les états (brouillon avec poste non pourvu, proposée, publiées, effectuée).
3. Valider l'échange accepté (Mes échanges). **Attendu** : tours permutés, nouvelle version de la liste, notifications aux deux marins.
4. Remplaçant : `equipier_a2` est remplaçant temporaire (60 h) : il peut activer, reporter, retirer, rien d'autre.

### 3. BSC / rédacteur — `equipier_a2`
1. Feuille de service : créer, rédiger et proposer la feuille du jour. **Attendu** : seuls les rédacteurs désignés peuvent écrire.
2. **Restriction** : `equipier_a` (même grade) ne peut pas créer la feuille.

### 4. COMAEQ — `coma_comaeq`
1. Liste « Service à quai — proposé, en attente de validation » : « Publier à titre prévisionnel » avec une prise d'effet. **Attendu** : liste publiée mais non applicable.
2. Viser la feuille de service du circuit (colonne de circuit à droite).
3. **Restriction** : ne peut pas activer une liste (réservé au chef de liste désigné ou à son remplaçant).

### 5. Chef de liste, activation — `chef_secteur_a` puis `chef_liste_abe`
1. Bretagne : activer la liste prévisionnelle publiée au point 4. **Attendu** : confirmation si l'heure prévue est lointaine (« prendra effet immédiatement »), liste active.
2. Bénébig : « Permanence en retard » → alerte puis escalade ; « Reporter » ou « Retirer la prévision » (motif obligatoire).

### 6. Commandant — `cdt_a`
1. Mouvements du bâtiment : déclarer un appareillage puis un accostage (mode MER/QUAI, historique conservé).
2. Délais d'alerte (menu Plus) : modifier le seuil d'activation anticipée.
3. Chevallier (`comaeq_jch` déclare l'accostage, puis `chef_liste_jch` active) : l'activation n'est possible qu'à quai.
4. Bénébig (`cdt_abe`) : Plus → Chefs de liste : qualifier la désignation historique de `historique_abe` ; avant cela, `historique_abe` ne peut rien activer.

## Contenu des données
- Calendrier : treize événements sur six semaines (escales, exercices, appareillage et journée de mer fictifs, arrêts techniques, réunions), un annulé, un reporté.
- Maintenance : fiches détaillées (outillage, pièces, EPI, consignes, étapes, points de contrôle) ; occurrences planifiées, assignées, en cours, en validation, terminées, en retard, annulées.
- Anomalies : six signalements avec historique (déclaration, prise en compte, traitement, clôture), dont un urgent ; tickets, dont un en attente de pièces.
- Logistique : stocks avec seuils et ruptures (gants), mouvements, demande de matériel liée à la fiche de ventilation, commande en attente.
- Notifications : dates étalées sur dix jours, anciennes lues, récentes non lues, alertes prioritaires conservées.

## Limites connues
- Matrix n'archive pas les notifications : états « lue » et « non lue » seulement.
- Les rappels d'activation s'évaluent à la lecture des pages (pas de tâche planifiée dans la démonstration).
- Les silhouettes de bâtiments restent en attente du Guide du marin 2023.
