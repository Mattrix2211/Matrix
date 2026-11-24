# Séance d'arbitrage métier — dossier de préparation

Établi sur l'état B (`6d6d0be`). Aucune règle n'est modifiée ; aucune question n'est tranchée. Chaque sujet suit le même ordre : fonctionnement actuel, décision antérieure, problème, exemple, solutions et conséquences, recommandation, question à trancher.
Ordre proposé : d'abord ce qui conditionne toute utilisation avec des données réelles (sujets 1 à 3), puis les règles de travail quotidiennes (4 à 6), puis l'ergonomie (7 à 9). Les références techniques (A1, R1…) ne sont là que pour retrouver les sources.

---

## 1. Écarts de droits de l'administrateur d'unité et des seuils (A1 à A4)

- **Fonctionnement actuel.** L'administrateur d'unité (compte technique) a un niveau supérieur à tous les seuils par défaut : il peut donc valider un échange de tours ou publier une liste. Les seuils de publication sont réglables par bâtiment (un bâtiment peut les abaisser). Le commandant en second : le même acte est refusé par l'API et accepté par l'écran.
- **Décision antérieure.** L'administrateur ne doit pas trancher d'acte métier (séparation entre administration de la plateforme et autorité de commandement). Principe « configuration plutôt que code ».
- **Problème.** Le code ne suit pas cette séparation ; deux canaux d'accès donnent deux réponses différentes pour le second. Rien n'est exploité aujourd'hui, mais la trace montre l'administrateur comme auteur de décisions de commandement.
- **Exemple.** Le matelot A demande un échange de quart ; l'administrateur technique du bâtiment, qui n'est pas dans la chaîne de commandement, clique « Valider » et l'échange est appliqué, tracé à son nom.
- **Solutions.** (a) Retirer aux administrateurs les actes métier (ils gèrent comptes et configuration seulement) : conséquence, un administrateur ne peut plus « dépanner » ; il faut alors un officier présent. (b) Les garder mais exiger une justification tracée : conserve le dépannage, garde le risque. (c) Statu quo documenté : aucun changement, écart assumé. Pour le second : aligner l'écran sur l'API (refus partout) ou l'inverse (autorisation partout).
- **Recommandation.** (a) pour l'administrateur, avec un plancher de seuil non abaissable en dessous du niveau défini ; aligner le second sur la règle de l'API (plus prudente). C'est un correctif borné, testable, sans effet sur l'organisation.
- **Question.** Un administrateur d'unité peut-il, oui ou non, valider ou publier un acte de commandement ? Et le commandant en second : mêmes droits sur l'écran et sur l'API, lesquels ?

## 2. Confidentialité des synthèses de passation (A14 et NE-06)

- **Fonctionnement actuel.** À la relève, la synthèse de passation reprend les tâches ouvertes, anomalies et blocages de tout le bâtiment. Un chef de section de l'équipage sortant (passé à terre) la lit en entier.
- **Décision antérieure.** Recette V1 (Notion « Décisions ») : un chef de section ne consulte que sa propre section.
- **Problème.** Le code filtre par bâtiment et équipage, pas par section. Constaté en navigateur sur comptes fictifs : sur 28 éléments lus, 12 appartenaient à d'autres sections. Aucune fuite réelle alléguée. Pour NE-06 : les chefs de l'équipage sortant gardent la lecture après être passés à terre.
- **Exemple.** Le chef de la section Moteurs ouvre la passation et lit un blocage de la section Pont qui ne le concerne pas ; il sait quelles tâches sont en retard chez les autres.
- **Solutions.** (a) Borner la lecture à la section (règle validée en V1) ; (b) borner au service ; (c) garder la lecture de tout le bâtiment pour la chaîne de commandement seulement ; (d) conserver tel quel, car l'équipage montant « doit tout savoir ». Pour NE-06 : lecture seule limitée dans la durée (par exemple jusqu'à la fin de la relève) ou permanente.
- **Recommandation.** (a) + (c) : chaque chef de section lit sa section, chef de secteur/service leur périmètre, commandement tout ; équipage sortant : lecture de leur seule section et limitée dans le temps. Cela applique la décision déjà validée.
- **Question.** Confirmez-vous que le chef de section ne lit que sa section ? Et l'équipage sortant à terre : combien de temps garde-t-il la lecture, et de quoi ?

## 3. Modules désactivés encore atteignables (A25)

- **Fonctionnement actuel.** Un bâtiment peut désactiver un module : ses pages disparaissent du menu et de la recherche, les pages web sont refusées. L'API (lecture et écriture), l'administration, les tâches planifiées, l'accueil et le calendrier continuent d'y accéder.
- **Décision antérieure.** « Un module désactivé n'existe plus pour le bâtiment » (principe de configuration par bâtiment). Le code actuel est un choix volontaire, non arbitré.
- **Problème.** La désactivation n'est pas étanche : un module « supprimé » peut encore recevoir et exposer des données.
- **Exemple.** Un bâtiment désactive Logistique ; le matelot ne voit plus le menu, mais une application mobile ou un script peut encore créer un ticket Logistique, et l'accueil affiche des alertes de stock.
- **Solutions.** (a) Fermeture complète : API, accueil, calendrier, notifications et tâches planifiées respectent la désactivation ; (b) fermeture web + API, mais l'administration et les données conservées restent en lecture ; (c) statu quo avec « désactivation = masquage ».
- **Recommandation.** (b) : refuser l'écriture et la lecture par API/accueil/calendrier, arrêter la génération planifiée, mais conserver les données (aucune perte à la réactivation).
- **Question.** « Désactivé » veut-il dire « masqué » ou « fermé » ? Et les données existantes doivent-elles rester consultables (par l'administrateur) ?

## 4. Autorité de validation des échanges de garde

- **Fonctionnement actuel.** Le marin sollicité accepte ; l'échange attend alors « le chef de liste ». La validation est ouverte à qui gère la liste (chef de liste désigné, qui peut être un chef de section). Le COMAEQ n'est ni notifié ni habilité. Limité aux services à quai d'une même liste.
- **Décisions antérieures (contradictoires).** Note Notion du 28/10 : le chef de liste habilité valide. Décision ultérieure inscrite au registre (`DEC-FDS-07` et `-13`) : décision finale du COMAEQ ou de son suppléant officiellement habilité ; le BSC ou chef de liste instruit seulement ; elle « remplace » la note du 28/10. Vous avez indiqué que cet écart reste à arbitrer : je ne considère donc aucune des deux comme acquise.
- **Problème.** Le code applique la première, le registre cible la seconde. De plus, la notion de suppléant officiel n'existe pas dans Matrix : la seconde règle ne peut pas s'appliquer telle quelle.
- **Exemple.** Deux matelots permutent un service à quai du samedi. Aujourd'hui, le chef de liste (un chef de section) valide seul. Dans le registre cible, il instruit et le COMAEQ décide, le chef de liste ne pouvant plus clore seul.
- **Solutions.** (a) Chef de liste décide (statu quo, rapide, moins de contrôle). (b) COMAEQ ou suppléant décide, chef de liste instruit (contrôle, mais charge sur le COMAEQ et nécessité de créer la suppléance). (c) Règle paramétrable par bâtiment : le COMAEQ décide, avec délégation explicite au chef de liste pour les échanges simples (par exemple même grade, même poste).
- **Recommandation.** (c) : (b) par défaut, délégation tracée au chef de liste, ce qui respecte « configuration plutôt que code » et la décision la plus récente tout en gardant la fluidité.
- **Question.** Qui a le dernier mot sur un échange de garde : le chef de liste, le COMAEQ, ou le COMAEQ avec délégation possible ? Et qui remplace le COMAEQ absent ?

## 5. Autorité de désignation du BSC et de l'équipage à terre

- **Fonctionnement actuel (état B).** Seuls les rédacteurs désignés (BSC ou délégués) écrivent la feuille de service de leur équipage. Les désigne le COMAEQ titulaire de l'équipage ; poste vacant, le commandant de l'équipage. Ni le grade ni le rôle ne suffisent. Chaque équipage, à bord ou à terre, désigne les siens. L'équipage à terre garde la lecture, et la feuille de service est une exception autorisée par conception (il rédige et vise sa propre feuille).
- **Décision antérieure.** Chaque équipage rédige et vise sa propre feuille (validé) ; lecture seule à terre par ailleurs.
- **Problème.** À confirmer : (1) le COMAEQ seul désigne, sans visa du commandant ; (2) un équipage à terre peut continuer à rédiger sa feuille alors que ses autres droits sont en lecture seule ; (3) sur main, aucune de ces restrictions n'existe (la création était ouverte).
- **Exemple.** Le COMAEQ de l'équipage B (à terre) désigne un matelot BSC pour préparer la prochaine embarquée ; un chef de section ne peut pas s'auto-désigner même s'il est plus gradé.
- **Solutions.** (a) Garder (COMAEQ, secours commandant). (b) Exiger en plus le visa du commandant pour toute désignation. (c) Étendre aux chefs de service/liste.
- **Recommandation.** (a), qui est celle implémentée et tracée, le code sait déjà signaler les équipages sans rédacteur opérant.
- **Question.** Le COMAEQ désigne-t-il seul le BSC ? L'équipage à terre doit-il pouvoir rédiger sa feuille avant l'embarquement ?

## 6. Droits des commandants adjoints et modules sans service (R1)

- **Fonctionnement actuel.** Les commandants adjoints (COMANAV, COMOPS, COMAEQ, COMAVIA) écrivent seulement sur les services qui leur sont rattachés ; sans rattachement configuré : lecture seule. Mais le glisser-déposer du calendrier permet encore à un adjoint de replanifier une occurrence ou un ticket d'un service qui n'est pas le sien (risque R1). Tâches, absences, formations, documents, RETEX : non bornés par service.
- **Décision antérieure.** Écriture bornée aux services rattachés ; lecture seule par défaut sans rattachement (validé). R1 : recommandée, non appliquée en attente de votre accord explicite.
- **Problème.** Le périmètre voulu n'est pas tenu partout.
- **Exemple.** Le COMANAV déplace d'un jour l'entretien du treuil, qui relève du service Propulsion rattaché au COMAEQ.
- **Solutions.** (a) Appliquer R1 maintenant (calendrier seulement) ; (b) appliquer en plus la borne aux autres modules, dans l'ordre proposé (documents, absences, RETEX, tâches) ; (c) autoriser un adjoint à agir hors de son service par délégation tracée (par marin, service, module, date de fin).
- **Recommandation.** (a) tout de suite, (b) par lots, (c) comme complément : une délégation existe pour les absences de collègue.
- **Question.** Appliquez-vous R1 maintenant ? Une délégation hors service est-elle acceptable, accordée par qui ? L'adjoint voit-il le motif des absences des autres services ?

## 7. Classification des notifications (D7)

- **Fonctionnement actuel.** Chaque notification porte un régime (MER, QUAI, COMMUNES, TRANSITION), une icône de catégorie et une gravité ; le panneau affiche d'abord le régime du mode courant, avec « Autres régimes (n) » replié. Une alerte « urgente » (niveau Urgent ou action à traiter) reste toujours en tête.
- **Décision antérieure.** Principe D7 validé : régime = étiquette de priorité, jamais un filtre. Étiquetage proposé : quarts → MER ; services à quai, feuille de service, activation, alertes, échanges → QUAI ; programme, relèves, le reste → COMMUNES. Distinct du « D7 sauvegarde/supervision », lui sans source.
- **Problème.** Le principe est validé et implémenté, mais le classement détaillé n'a pas été passé en revue métier ; il reste à confirmer que rien d'important se retrouve replié.
- **Exemple.** À quai, un matelot reçoit une notification de quart à la mer du prochain appareillage : elle apparaît dans « Autres régimes » et peut passer inaperçue.
- **Solutions.** (a) Garder l'étiquetage actuel ; (b) remonter certains types (par exemple les quarts de l'appareillage prochain) ; (c) rendre le régime paramétrable par type de notification et par bâtiment.
- **Recommandation.** (b) pour les cas de transition, puis (c) si l'usage montre des écarts.
- **Question.** Quelles notifications ne doivent jamais être repliées, quel que soit le mode ? Y a-t-il des types mal rangés ?

## 8. Anomalies d'ergonomie ANO-007 à ANO-010

| N° | Constat | Proposition | À décider |
|---|---|---|---|
| ANO-007 | Barre latérale à 1366 px : « Quarts et tours de service » sur deux lignes | Libellé « Quarts et tours » | Libellé accepté ? |
| ANO-008 | Vue « Par jour » : page d'environ 5 800 px (tous les jours ouverts, ~7 quarts par jour) | Replier les jours futurs au-delà de demain, ou filtre « mes créneaux » par défaut | Quel défaut ? |
| ANO-009 | Calendrier mensuel : créneaux de toute l'équipe (« +12 autres » par jour) | Filtre « mes événements » par défaut | Perso par défaut ou équipe ? |
| ANO-010 | Assistant de signalement : bannière « brouillon existant » encore affichée à l'étape 4 | Masquer la bannière après la saisie (défaut, sans enjeu métier) | Corriger sans autre décision ? |

- **Exemple.** Un matelot ouvre le calendrier du mois : il doit chercher ses créneaux parmi ceux de 30 collègues.
- **Recommandation.** Valider ANO-007, ANO-009 (mes événements par défaut, bascule « équipe » en un clic) et ANO-008 (filtre « mes créneaux » par défaut) ; corriger ANO-010 sans décision.
- **Question.** Pour chaque ligne : accepté / refusé / autre proposition.

## 9. Retrait du module Rondes

- **Fonctionnement actuel (état B).** Les Rondes ne sont plus proposées aux marins (menus, recherche, accueil, calendrier). L'application est réduite à ses modèles et migrations pour préserver les données existantes ; il reste un peu de style orphelin.
- **Décision antérieure.** Rondes retirées de la cible (A8 : « génération abandonnée, rondes retirées ») ; cahier des charges §20 non encore aligné.
- **Problème.** Le retrait est-il définitif ? Les données et les tables restent, sans interface pour les lire ; le cahier des charges décrit encore le module.
- **Exemple.** Un chef de quart cherche l'historique des rondes de la semaine passée : il n'y a plus d'écran, mais les données existent.
- **Solutions.** (a) Retrait définitif : export puis suppression des modèles ; (b) retrait masqué : garder les données sans écran, décision réexaminée plus tard ; (c) réactivation.
- **Recommandation.** (b) pour la recette et la démonstration ; décider (a) ou (c) quand les besoins terrain (suivi de surveillance) seront connus. Mettre le cahier des charges à jour.
- **Question.** Les Rondes sont-elles abandonnées définitivement ? Que fait-on des données déjà saisies ?

---

## Récapitulatif des questions (ordre de séance)

1. Admin d'unité et second : actes de commandement autorisés ou non (A1–A4).
2. Passation : lecture limitée à la section, durée pour l'équipage sortant (A14, NE-06).
3. Modules désactivés : masqués ou fermés, données conservées (A25).
4. Échanges de garde : qui décide, qui supplée le COMAEQ.
5. BSC et équipage à terre : qui désigne, rédaction à terre.
6. R1 et délégation hors service pour les commandants adjoints.
7. Notifications jamais repliées.
8. ANO-007 à ANO-010 : accepter, refuser ou modifier.
9. Rondes : abandon définitif ou masquage, sort des données.

Hors séance, à ne pas oublier : sauvegarde, restauration, supervision et durée de conservation (D7 « exploitation », aucune source), et la rotation éventuelle du mot de passe de l'ancienne note Notion.
