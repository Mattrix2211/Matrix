<!-- retire: diffusable/01_vision.md | Chapitre 1 — Vision, philosophie et principes de Matrix | Le résumé reprend la valeur ; la vision détaillée est la section « Vision » de ce référentiel -->
<!-- partie: Résumé -->
# Résumé pour le décideur

<div class="ligne-public"><b>Public :</b> commandement, responsables métier, décideur · <b>À lire en 2 pages</b> · <b>Ce que vous y trouverez :</b> la valeur de Matrix, la maturité de chaque module, les limites à connaître et les décisions qui attendent le PO</div>

## En une phrase

Matrix est la plateforme quotidienne du marin de la Marine nationale : chacun y retrouve **ses tâches, ses quarts et services, ses maintenances, ses formations et ses échanges** au même endroit, sur le réseau du bord, **sans Internet**. La gestion de maintenance n'en est qu'un module. Matrix complète les outils du soutien (SSF) sans les remplacer.

## Ce que Matrix apporte aujourd'hui 🟢

- **Une journée lisible** : la page « Aujourd'hui » classe les actions à faire par urgence et affiche les quarts, services, tâches et formations du jour ; le calendrier réunit tout ce qui a une date.
- **Des droits par rôle et par périmètre** : neuf niveaux, réglables par bâtiment ; l'écran masque, c'est toujours le serveur qui décide.
- **Des circuits qui laissent des traces** : tâches, maintenances, anomalies, tickets correctifs, échanges de tours, annonces à accuser. Une correction n'écrase jamais la saisie d'origine.
- **Un fonctionnement hors ligne** : aucune dépendance à un service extérieur.

## Maturité par module

Les étiquettes sont celles du dossier : 🟢 existe et vérifié dans l'état B du 11/11/2026 ; 🔵 cible validée par le PO, pas développée ; 🟣 proposition non arbitrée, jamais une décision (elle ne le devient que sur mention expresse du PO) ; ⚪ non vérifié. « Écart » renvoie au registre des écarts et décisions ([[RE:01_lire_ce_registre]]).

| Module | Disponible 🟢 | Manque, à décider ou à confirmer |
|---|---|---|
| Organisation et rôles | Hiérarchie bâtiment → service → secteur → section ; neuf rôles ; double équipage et relève | 🔵 Suppléance générale (B1, B2) ; écarts de droits A1 et A4 |
| Accueil et pilotage | Page « Aujourd'hui », tableaux de bord par niveau, passation | Écart A14 (confidentialité de la synthèse de passation) |
| Calendrier | Calendrier central, export personnel | — |
| Quarts, services, feuille de service | Listes, publication, échanges de tours à quai, feuille de service | 🔵 Circuit d'échange décidé par le COMAEQ (A2) ; écarts A3, A12 ; points B1, B3, B4, B5 |
| Communication | Discussions attachées aux objets, annonces à accuser, notifications | — |
| Tâches, demandes, programme, postes | Tâches avec compte rendu, blocage, difficultés signalées, programme, postes | 🔵 Trois niveaux de priorité (A13) ; point B6 |
| Matériel et installations | Fiches, catalogue, plan du navire, relevés, validation des fiches | 🔵 Circuit d'approbation des transferts (A18) |
| Maintenance, anomalies, tickets | Échéances générées, exécution guidée, anomalie, ticket correctif en sept étapes | Règle de sortie de « En validation » à décider (A20, 🟣 D2) ; 🔵 périodicités nommées, outillage, durée (A21) ; message de fin inexact pour une installation (NE-07) |
| Logistique | Stock de pièces, demandes de pièces | — |
| Formations | Formations, qualifications, demandes de places | 🔵 Dossier vivant de demande de places (A19) |
| Documentation et RETEX | Versions applicables, RETEX en une étape | 🔵 Circuit hiérarchique et diffusion « flotte » (A15, A16 ; 🟣 D3) |
| Préparation à l'appareillage | Prêt à appareiller, session ouverte, signature | 🔵 Fiche de référence et circuit COMANAV (A17 ; 🟣 D4) |

## Les limites à connaître

1. **Matrix n'est pas déployé ni validé en l'état.** Le dossier décrit un état de développement non fusionné dans la branche de référence ; il ne vaut ni validation du logiciel ni autorisation de diffusion.
2. **Sécurité d'accès, sauvegarde et supervision** ne sont pas traitées avec les SIC (A23, A24) : l'architecture de mise en service reste à définir.
3. **Un module désactivé reste actif par certains chemins** (interface de programmation, tâches planifiées, accueil) : la règle attendue est à décider (A25).
4. **Une maintenance « En validation » peut rester sans suite ni alerte** (A20) : seul un chef de secteur ou plus peut corriger le compte rendu.
5. **Le registre central** liste {{fait:n_ecarts_registre}} écarts, {{fait:n_points_a_confirmer}} points à confirmer, {{fait:n_propositions}} propositions, sept nouveaux écarts et {{fait:n_decisions_v12}} décisions du PO avec leur état ; aucun n'est une autorisation de modifier le logiciel.

## Ce qui attend le PO

| Sujet | Nature | Voir |
|---|---|---|
| Règle de sortie de « En validation » et alerte de retard | 🟣 proposition D2 | Fiche Maintenance |
| Ticket pour une installation non conforme | 🟣 proposition D1 | Fiche Maintenance |
| Transmission d'un RETEX à un organisme | 🟣 proposition D3 | Fiche Documentation et RETEX |
| Autorité de classification « critique » d'un contrôle d'appareillage | 🟣 proposition D4 | Fiche Préparation à l'appareillage |
| Procédures de suppléance, ordre des grades, conservation des journaux | Points à confirmer B1 à B8 | Registre |
| Sauvegarde, restauration, supervision | 🟣 proposition D7 et écart A24 | Registre |
