<!-- retire: diffusable/01_vision.md | 1.1 À quoi sert Matrix | Repris dans « Matrix en une page » et dans le référentiel fonctionnel -->
<!-- partie: Prendre en main -->
# Matrix en une page

<div class="ligne-public"><b>Public :</b> marins, chefs de section, de secteur et de service · <b>Ce que vous y trouverez :</b> ce que Matrix fait pour vous, comment lire ce guide et où trouver chaque parcours · <b>Règles complètes :</b> [[RF:02_vision]]</div>

## Ce que fait Matrix

Matrix est la plateforme quotidienne du marin : **vos tâches, vos quarts et services, vos maintenances, vos formations et vos échanges au même endroit**, sur le réseau du bord, **sans Internet**. Il vous dit ce qui vous attend, vous guide pas à pas et garde une trace de ce qui a été fait. Il complète les outils du soutien sans les remplacer.

| Je veux… | Je vais dans… | Parcours |
|---|---|---|
| Voir ma journée | « Aujourd'hui » | [[GU:02_parcours_ma_journee]] |
| Accuser réception d'une annonce, retrouver une information | « Annonces », barre de recherche | [[GU:03_parcours_annonces_et_recherche]] |
| Faire une tâche et rendre compte | « Tâches » | [[GU:04_parcours_tache]] |
| Connaître mes quarts et mes services, échanger un tour | « Quarts et tours de service », « Feuille de service » | [[GU:05_parcours_tour_de_service]] |
| Réaliser une maintenance, signaler une anomalie, suivre un ticket | « Maintenance », « Anomalies », « Tickets correctifs » | [[GU:12_maintenance]] |
| Préparer l'appareillage | « Prêt à appareiller » | [[GU:13_parcours_appareillage]] |

## Comment lire ce guide

Les pages à fond clair montrent **un écran réel** de Matrix. Chaque légende donne le profil utilisé, le chemin dans le menu et le renvoi vers les règles du référentiel. Les captures ont été prises le **16/11/2026** sur une **instance de démonstration isolée**, avec des **données fictives** (personnages, bâtiment, dates) et un navigateur en français. Les deux vues de téléphone sont des **émulations** : aucun appareil réel n'a été essayé.

Chaque affirmation du guide porte une étiquette quand elle n'est pas évidente :

| Étiquette | Sens dans ce guide |
|---|---|
| 🟢 | **Existe aujourd'hui** : comportement réellement implémenté et vérifié ; seules ces lignes décrivent ce que Matrix fait |
| 🔵 | **Cible validée** par le PO, pas nécessairement développée : jamais présentée comme disponible |
| 🟣 | **Proposition non arbitrée** : ce n'est pas une fonctionnalité disponible et pas encore une décision |
| ⚪ | **Non vérifié** : information issue d'une seule source ou parcours non rejoué |

Les écrans visibles à l'écran ne sont **pas** la règle : un bouton affiché ne vaut pas un droit. C'est toujours le serveur qui décide ; un refus s'affiche alors comme une erreur d'accès (écart NE-01).

## Les limites à connaître dès maintenant

- Une maintenance non conforme sur une **installation** ne crée **pas** de ticket automatique, alors que l'écran de fin le laisse croire (écart NE-07).
- Une maintenance « En validation » ne se débloque que par la correction du compte rendu, réservée au chef de secteur ou plus (écart A20).
- La **synthèse de passation** est lisible par un chef de section pour tout son bâtiment et non pour sa seule section (écart A14) : à garder en tête avant de la diffuser.
- 🔵 Les périodicités nommées, les remarques d'outillage et la durée indicative actualisée sont des **cibles non développées** (écart A21).

Toutes les limites sont rassemblées dans [[GU:18_limites_visibles]].
