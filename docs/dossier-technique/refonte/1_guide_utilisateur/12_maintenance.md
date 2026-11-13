<!-- partie: Parcours et écrans -->
# Maintenance, anomalies et tickets

<div class="ligne-public"><b>Public :</b> marins, chefs de section, de secteur et de service · <b>Ce que vous y trouverez :</b> deux parcours illustrés (réaliser une maintenance ; signaler une anomalie et suivre son ticket) et ce qui se passe quand un contrôle est non conforme · <b>Pour les règles complètes :</b> [[RF 1]]</div>

## En bref

Matrix vous dit **quels contrôles et entretiens vous attendent** et vous guide pas à pas. Si vous voyez quelque chose d'anormal, vous le **signalez** en quelques clics ; un chef le prend en compte et, si un équipement est en cause, le transforme en **ticket de réparation** que vous pouvez suivre.

| Je veux… | Où aller | Ce que je fais |
|---|---|---|
| Voir mes maintenances | « Maintenance » dans le menu, ou « À faire » sur l'accueil | Ouvrir l'échéance, suivre les contrôles |
| Signaler quelque chose d'anormal | « Anomalies » → « Signaler » | Remplir quatre petites étapes |
| Savoir où en est ma demande | « Anomalies » ou « Tickets correctifs » | Lire l'état et l'historique |

## Parcours 1 — Je réalise une maintenance

Chaque échéance a une **fiche** : ce qu'il faut préparer, les consignes de sécurité, puis les contrôles à renseigner. Vous pouvez enregistrer en cours de route et terminer plus tard.

@capture id=occurrences section="Parcours 1 — Je réalise une maintenance" titre="Étape 1 — La liste des maintenances" texte="Les échéances sont classées par état. Les compteurs en haut indiquent ce qui est à traiter. Le bouton « M'assigner » permet de prendre une échéance non assignée." renvoi="Règles : référentiel fonctionnel, fiche Maintenance" provisoire=1

@capture id=execution_fiche section="Parcours 1 — Je réalise une maintenance" titre="Étape 2 — La fiche d'exécution guidée" texte="La fiche rappelle les consignes de sécurité et liste les contrôles. Chaque contrôle se règle d'un clic : conforme, non conforme ou sans objet. La progression indique combien d'opérations sont faites." renvoi="Règles : référentiel fonctionnel, fiche Maintenance" provisoire=1

@capture id=p_maintenance_1_saisie section="Parcours 1 — Je réalise une maintenance" titre="Étape 3 — Renseigner les contrôles" texte="Ici, les quatre contrôles sont marqués « Conforme » ; la progression passe à 4 sur 6. Vous pouvez ajouter une remarque ou une photo à chaque ligne." renvoi="Règles : référentiel fonctionnel, fiche Maintenance" provisoire=1

@capture id=p_maintenance_2_termine section="Parcours 1 — Je réalise une maintenance" titre="Étape 4 — Terminer la maintenance" texte="« Terminer la maintenance » enregistre le compte rendu. L'échéance passe à « Terminée » et un retour à l'accueil est proposé. Un message de confirmation s'affiche brièvement en bas de l'écran." renvoi="Règles : référentiel fonctionnel, fiche Maintenance" provisoire=1

### Si un contrôle est non conforme

Vous pouvez tout de même terminer : l'échéance passe alors **« En validation »**. Pour du **matériel mobile**, Matrix crée automatiquement un **ticket de réparation** et prévient les chefs. Pour une **installation**, aucun ticket n'est créé : pensez à **signaler une anomalie** depuis le compte rendu (parcours 2).

## Parcours 2 — Je signale une anomalie et je suis le ticket

Tout marin peut signaler une anomalie : une fuite, une issue encombrée, un bruit anormal… L'équipement est facultatif. L'assistant tient en quatre étapes.

@capture id=p_anomalie_1_objet section="Parcours 2 — Je signale une anomalie" titre="Étape 1 — Choisir l'objet concerné" texte="Choisissez l'installation ou le matériel concerné s'il est identifié, le secteur et le lieu. Un seul équipement à la fois : une installation ou un matériel." renvoi="Règles : référentiel fonctionnel, fiche Maintenance" provisoire=1

@capture id=p_anomalie_2_nature section="Parcours 2 — Je signale une anomalie" titre="Étape 2 — Dire ce que vous constatez" texte="Un titre court et la gravité, de 1 (mineure) à 5 (critique). Soyez précis : le chef de secteur lira ce titre en premier." renvoi="Règles : référentiel fonctionnel, fiche Maintenance" provisoire=1

@capture id=p_anomalie_3_description section="Parcours 2 — Je signale une anomalie" titre="Étape 3 — Décrire et joindre une photo" texte="Une description libre et une photo, toutes deux facultatives. Plus le signalement est clair, plus la réponse est rapide." renvoi="Règles : référentiel fonctionnel, fiche Maintenance" provisoire=1

@capture id=p_anomalie_4_verification section="Parcours 2 — Je signale une anomalie" titre="Étape 4 — Vérifier avant d'envoyer" texte="Le récapitulatif vous laisse le temps de corriger avant l'envoi." renvoi="Règles : référentiel fonctionnel, fiche Maintenance" provisoire=1

@capture id=p_anomalie_5_suivi section="Parcours 2 — Je signale une anomalie" titre="Étape 5 — Suivre mon signalement" texte="L'anomalie est « Signalée ». Vous voyez son état, son historique et le fil de discussion, où vous pouvez répondre aux questions du chef." renvoi="Règles : référentiel fonctionnel, fiche Maintenance" provisoire=1

@capture id=p_anomalie_7_prise_en_compte section="Parcours 2 — Du côté du chef" titre="Étape 6 — Le chef de secteur prend en compte" texte="Un chef de section ou plus fait avancer l'anomalie (« Prise en compte »). Quand un matériel est identifié, il peut la convertir en ticket correctif." renvoi="Profil chef de secteur" provisoire=1

@capture id=p_anomalie_8_ticket section="Parcours 2 — Du côté du chef" titre="Étape 7 — Le ticket correctif" texte="Le ticket garde le lien avec l'anomalie et suit des étapes : diagnostic, réparation, essais, remise en service, clôture. La remise en service demande une confirmation explicite, la clôture un retour d'expérience." renvoi="Règles : référentiel fonctionnel, fiche Maintenance" provisoire=1

## Quand l'échéance reste « En validation »

Après un compte rendu **non conforme**, l'échéance attend qu'un **chef de secteur** corrige le compte rendu. Vous ne voyez pas de bouton « Valider » : c'est normal, il n'existe pas.

@capture id=en_validation_execution section="Limite actuelle" titre="Une échéance « En validation », vue par le chef de secteur" texte="Seul le chef de secteur (ou plus) voit « Enregistrer la correction ». L'exécutant et le chef de section ne le voient pas. Rien ne relance automatiquement cette échéance : elle peut rester ici longtemps." renvoi="Écart documenté A20 — règle de sortie non décidée par le PO" provisoire=1

## À savoir

- Le bouton **« Exécuter »** apparaît parfois dans la liste pour une échéance qui n'est pas à vous : si vous n'y avez pas droit, Matrix refuse l'ouverture. Utilisez « M'assigner » ou demandez à un chef.
- Les **alertes sur l'appareil** (notifications poussées) ne sont pas actives sur l'instance de démonstration ayant servi aux captures ; les notifications dans l'application le sont.
- Ce guide décrit **ce que fait Matrix aujourd'hui**. Les périodicités nommées, les remarques d'outillage ou le ticket automatique pour une installation sont **prévus ou proposés**, pas disponibles.
