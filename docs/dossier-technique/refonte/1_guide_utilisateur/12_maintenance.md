<!-- partie: Parcours et écrans -->
# Maintenance, anomalies et tickets

<div class="ligne-public"><b>Public :</b> marins, chefs de section, de secteur et de service · <b>Ce que vous y trouverez :</b> deux parcours illustrés (réaliser une maintenance ; signaler une anomalie et suivre son ticket), ce que Matrix fait seul, ce que vous pouvez faire et ce qui reste ouvert · <b>Règles complètes :</b> [[RF 1]]</div>

## En bref

Matrix vous dit **quels contrôles et entretiens vous attendent** et vous guide pas à pas. Si vous voyez quelque chose d'anormal, vous le **signalez** en quelques clics ; un chef le prend en compte et, si un équipement est en cause, le transforme en **ticket de réparation** que vous pouvez suivre.

| Je veux… | Où aller | Ce que je fais |
|---|---|---|
| Voir mes maintenances | « Maintenance » dans le menu, ou « À faire » sur l'accueil | Ouvrir l'échéance, suivre les contrôles |
| Signaler quelque chose d'anormal | « Anomalies » → « Signaler » | Remplir quatre petites étapes |
| Savoir où en est ma demande | « Anomalies » ou « Tickets correctifs » | Lire l'état et l'historique |

## Après un contrôle non conforme : ce que Matrix fait, ce que vous pouvez faire

Les étiquettes disent la nature de chaque ligne : 🟢 **comportement actuel**, vérifié ; 🟣 **proposition**, non arbitrée par le PO, donc **non disponible**. Aucune règle de ce tableau n'est nouvelle : ce sont celles de l'état actuel de Matrix.

| Situation | Ce que Matrix fait seul | Ce que vous pouvez faire | Limite ou statut |
|---|---|---|---|
| Tous les contrôles sont conformes | L'échéance passe à **« Terminée »** ; le compte rendu est archivé ; les chefs de secteur sont informés | Rien d'autre | 🟢 |
| Un contrôle est **non conforme**, sur un **matériel mobile** | L'échéance passe à **« En validation »** ; Matrix **crée un ticket de réparation** (gravité 3) et alerte les chefs | Terminer le compte rendu ; suivre le ticket dans « Tickets correctifs » | 🟢 L'échéance reste « En validation » (voir la dernière ligne) |
| Un contrôle est **non conforme**, sur une **installation** | L'échéance passe à **« En validation »** ; les chefs de secteur sont informés ; **aucun ticket n'est créé** | **Signaler vous-même une anomalie** (menu « Anomalies », parcours 2). C'est une action **manuelle et facultative** : elle n'est ni automatique, ni une validation | 🟢 L'écran de fin annonce pourtant « un ticket correctif sera (ou a été) ouvert » : c'est inexact pour une installation (écart NE-07). 🟣 Créer un ticket automatiquement pour une installation est une **proposition** (D1), pas une règle |
| Un relevé chiffré est **hors plage** | L'écran de fin propose un lien **« signaler une anomalie »** pré-rempli | Cliquer pour signaler | 🟢 Ce lien n'apparaît **que** pour un relevé hors plage, pas pour un simple contrôle non conforme |
| L'échéance est **« En validation »** | **Rien de plus** : pas de bouton de validation, pas de notification, pas de relance ; pour une installation, l'entretien récurrent est suspendu | Rien : seul un **chef de secteur ou plus** peut corriger le compte rendu | 🟢 Limite connue **A20** : la règle de sortie reste **à décider par le PO** (proposition D2) |

## À savoir avant de commencer

- Le bouton **« Exécuter »** apparaît parfois dans la liste pour une échéance qui n'est pas à vous : si vous n'y avez pas droit, Matrix refuse l'ouverture (écart NE-01). Utilisez « M'assigner » ou demandez à un chef.
- Les **alertes sur l'appareil** (notifications poussées) ne sont pas actives sur l'instance de démonstration ayant servi aux captures ; les notifications dans l'application le sont.
- Ce guide décrit **ce que fait Matrix aujourd'hui**. Les périodicités nommées, les remarques d'outillage ou le ticket automatique pour une installation sont **prévus ou proposés**, pas disponibles.
- Les captures qui suivent sont **recadrées** sur la zone utile ; le menu de gauche n'est pas reproduit : la ligne « Navigation » de chaque légende dit où se trouve l'écran.

@capture h2="Parcours 1 — Je réalise une maintenance" titre="Étape 1 — La liste des maintenances" texte="Les échéances sont classées par état. Le bloc « À traiter » donne les compteurs ; le bouton « M'assigner » permet de prendre une échéance non assignée." c1="occurrences|222,85,1366,768" nav="Maintenance › Maintenance" renvoi="Règles : RF §1" provisoire=1 dispo=124

@capture section="Parcours 1 — Je réalise une maintenance" titre="Étape 2 — La fiche d'exécution guidée" texte="La fiche rappelle les consignes de sécurité et liste les contrôles. Chaque contrôle se règle d'un clic : conforme, non conforme ou sans objet. La progression indique combien d'opérations sont faites." c1="execution_fiche|222,85,1366,768" nav="bouton « Exécuter » de la liste" renvoi="Règles : RF §1" provisoire=1 dispo=132

@capture section="Parcours 1 — Je réalise une maintenance" titre="Étape 3 — Renseigner les contrôles, puis terminer" texte="Ici, les quatre contrôles sont marqués « Conforme » ; la barre du bas affiche la progression et les trois boutons Annuler, Enregistrer (en cours de route) et Terminer. Après « Terminer la maintenance », l'échéance passe à « Terminée » et le bouton devient « Maintenance terminée »." c1="p_maintenance_1_saisie|245,410,985,768|Avant : contrôles renseignés, boutons Enregistrer et Terminer" c2="p_maintenance_2_termine|245,85,1320,150|Après : l'état de l'échéance devient « Terminée »" c3="p_maintenance_2_termine|245,712,985,768|Après : le bouton devient « Maintenance terminée »" nav="bouton « Exécuter » de la liste" renvoi="Règles : RF §1" provisoire=1 dispo=128

@capture h2="Parcours 2 — Je signale une anomalie et je suis le ticket" titre="Étape 1 — Choisir l'objet concerné" texte="Un assistant en quatre étapes. Choisissez l'installation ou le matériel concerné s'il est identifié (un seul des deux), le secteur et le lieu." c1="p_anomalie_1_objet|235,106,1030,600" nav="Maintenance › Anomalies › Signaler" renvoi="Règles : RF §1" provisoire=1 dispo=124

@capture section="Parcours 2 — Je signale une anomalie" titre="Étape 2 — Dire ce que vous constatez" texte="Un titre court et la gravité, de 1 (mineure) à 5 (critique). Le chef de secteur lira d'abord ce titre." c1="p_anomalie_2_nature|235,135,1030,455" nav="Maintenance › Anomalies › Signaler" renvoi="Règles : RF §1" provisoire=1 dispo=124

@capture section="Parcours 2 — Je signale une anomalie" titre="Étape 3 — Décrire et joindre une photo" texte="Une description libre et une photo, toutes deux facultatives. Plus le signalement est clair, plus la réponse est rapide." c1="p_anomalie_3_description|235,135,1030,515" nav="Maintenance › Anomalies › Signaler" renvoi="Règles : RF §1" provisoire=1 dispo=124

@capture section="Parcours 2 — Je signale une anomalie" titre="Étape 4 — Vérifier avant d'envoyer" texte="Le récapitulatif vous laisse le temps de corriger avant l'envoi : « Précédent » revient en arrière, « Signaler l'anomalie » envoie." c1="p_anomalie_4_verification|235,135,1030,470" nav="Maintenance › Anomalies › Signaler" renvoi="Règles : RF §1" provisoire=1 dispo=124

@capture section="Parcours 2 — Je signale une anomalie" titre="Étape 5 — Suivre mon signalement" texte="L'anomalie est « Signalée ». Vous voyez son état, son historique et le fil de discussion, où vous pouvez répondre aux questions du chef. Le message vert en bas de l'écran d'origine n'est pas repris ici." c1="p_anomalie_5_suivi|245,90,1366,500" nav="Maintenance › Anomalies" renvoi="Règles : RF §1" provisoire=1 dispo=124

@capture section="Parcours 2 — Du côté du chef" titre="Étape 6 — Le chef de secteur prend en compte" texte="Un chef de section ou plus fait avancer l'anomalie (« Prise en compte »). Quand un matériel ou une installation est identifié, il peut la convertir en ticket correctif : c'est une décision du chef, jamais automatique." c1="p_anomalie_7_prise_en_compte|245,90,1366,545" nav="Maintenance › Anomalies" renvoi="Profil chef de secteur" provisoire=1 dispo=124

@capture section="Parcours 2 — Du côté du chef" titre="Étape 7 — Le ticket correctif" texte="Le ticket garde le lien avec l'anomalie d'origine et suit sept étapes : signalé, diagnostiqué, pièces, réparation, essais, remise en service, clôture. La remise en service demande une confirmation explicite, la clôture un retour d'expérience." c1="p_anomalie_8_ticket|245,85,1366,590" nav="Maintenance › Tickets correctifs" renvoi="Règles : RF §1" provisoire=1 dispo=124

@capture h2="Quand l'échéance reste « En validation »" titre="Limite actuelle (écart A20) — vue du chef de secteur" texte="Après un compte rendu non conforme, l'échéance attend qu'un chef de secteur corrige le compte rendu. Vous ne voyez pas de bouton « Valider » : il n'existe pas. Seul le chef de secteur (ou plus) voit « Enregistrer la correction » ; l'exécutant et le chef de section ne le voient pas. Rien ne relance automatiquement cette échéance." c1="en_validation_execution|245,85,1320,150|L'échéance est « En validation »" c2="en_validation_execution|245,410,985,768|Le bouton « Enregistrer la correction » est réservé au chef de secteur ou plus" nav="Maintenance › Maintenance (filtre « En validation ») › Exécuter" renvoi="Écart A20 : RF §1, RE §2" provisoire=1 dispo=112
