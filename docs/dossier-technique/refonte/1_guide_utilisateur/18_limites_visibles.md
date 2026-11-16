<!-- partie: Limites et références -->
# Les limites visibles de l'état B

<div class="ligne-public"><b>Public :</b> tous · <b>Ce que vous y trouverez :</b> ce que Matrix ne fait pas encore ou fait autrement que prévu, avec l'écran qui le montre · <b>Registre complet :</b> [[RE:01_lire_ce_registre]]</div>

Cette page rassemble les écarts qu'un utilisateur peut **rencontrer à l'écran**. Chaque écart est un **constat documenté**, pas une autorisation de modifier le logiciel ni une décision. Les statuts sont ceux du registre central.

| Écart | Ce que vous voyez | Ce qu'il faut savoir | Étiquette |
|---|---|---|---|
| **NE-01** | Le bouton « Exécuter » apparaît dans la liste des maintenances, même pour une échéance qui n'est pas à vous | Si vous n'y avez pas droit, Matrix refuse l'ouverture (erreur d'accès). Utilisez « M'assigner » ou demandez à un chef | 🟢 |
| **NE-07** | L'écran de fin d'un compte rendu non conforme annonce qu'un ticket sera ouvert | Pour une **installation**, aucun ticket n'est créé : signalez vous-même une anomalie (menu « Anomalies ») | 🟢 |
| **A20** | Une maintenance reste « En validation » | Il n'existe pas de bouton « Valider » ; seul un chef de secteur ou plus corrige le compte rendu ; rien ne relance l'échéance | 🟢 ; règle de sortie à décider par le PO |
| **A14** | La synthèse de passation | Un chef de section la lit pour tout son bâtiment et non pour sa seule section ; vérifié par test sur comptes fictifs | 🟢 |
| **A25** | Un module désactivé par le bâtiment | Ses pages disparaissent du menu ; certains chemins (interface de programmation, tâches planifiées, accueil, calendrier) restent actifs | 🟢 ; règle attendue à décider |
| **A12** | « Imprimer » sur la feuille de service | L'impression passe par le navigateur ; la mise en page A4 dédiée et la réimpression versionnée ne sont pas développées | 🔵 |
| **A13** | Deux niveaux de priorité de tâche | Le PO a décidé trois niveaux ; pas de règle d'abaissement | 🔵 |
| **A21** | Périodicités nommées, remarques d'outillage, durée indicative | Les échéances se génèrent par intervalle en jours ; les périodicités nommées et la durée actualisée sont une cible non développée | 🔵 |
| **NE-02** | Les lignes de la liste des tickets | Elles s'ouvrent à la souris mais pas au clavier | 🟢 |
| **D1, D2** | Ticket pour une installation non conforme ; règle de sortie de « En validation » | **Propositions** non arbitrées, jamais des règles | 🟣 |

@capture h2="Écart NE-01 — Un bouton affiché sans droit" titre="La liste des maintenances vue par un marin" texte="Le bouton « Exécuter » est affiché sur toutes les lignes, y compris sur celles qui ne sont pas assignées au marin. Si le marin n'a pas le droit, l'ouverture de la fiche est refusée par le serveur." c1="occurrences" nav="Maintenance › Maintenance" renvoi="Écart NE-01 : voir le registre"

@capture h2="Écart A20 — Une maintenance « En validation »" titre="La liste filtrée sur l'état « En validation »" texte="L'échéance est « En validation » depuis son compte rendu non conforme. Elle reste visible dans « À traiter » sans échéance de sortie et sans notification." c1="en_validation_liste" nav="Maintenance › Maintenance (filtre « En validation »)" renvoi="Écart A20 : voir le registre"
