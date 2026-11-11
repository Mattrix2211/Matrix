# Chapitre 1 — Vision, philosophie et principes de Matrix

> **Pour qui :** marins, responsables, développeurs, administrateurs. **Diffusion :** générale.
> **Ce que vous y trouverez :** à quoi sert Matrix, ce qu'il n'est pas, et les règles qui guident chacune de ses fonctions.
> **État décrit :** état B (`claude/l03-suppression-sure-v11`, commit `6d6d0be`), **non fusionné dans `main`**. Voir le chapitre 3.

---

## 1.1 À quoi sert Matrix

Matrix est une application destinée au marin de la Marine nationale, pour sa journée de travail à bord comme à quai. Elle vise à réunir en un seul endroit ce qui est aujourd'hui dispersé : le planning, les quarts et les services, les tâches, la maintenance, les consignes, les messages, les formations. L'ambition posée dans le cahier des charges est simple : *« Matrix doit devenir l'application que les marins ouvrent chaque jour »*.

La maintenance (GMAO) n'est qu'**un module** parmi d'autres. Matrix n'est pas une GMAO à laquelle on aurait ajouté des fonctions : il est pensé d'abord pour répondre aux questions que se pose le marin en arrivant à bord.

| La question du marin | Où Matrix répond |
|---|---|
| **Où dois-je être ?** | le calendrier, les quarts, les services, les formations |
| **Que dois-je faire ?** | les tâches, la maintenance, les rondes de contrôle |
| **Que dois-je savoir ?** | les annonces, la documentation, les discussions |
| **Avec qui travaille-je ?** | la composition des équipes, les chefs de liste, la relève |
| **Que dois-je signaler ?** | les anomalies, les difficultés, les retours d'expérience |

Tout vient du même système : le marin voit **sa** journée, le chef de section voit **sa** section, le chef de service son service, l'état-major le bâtiment. Chacun voit ce qui relève de son périmètre, pas davantage.

## 1.2 Ce que Matrix n'est pas

Ces limites sont des décisions du Product Owner (PO), reprises telles quelles :

- Matrix **ne remplace pas** les outils du Service de soutien de la flotte (SSF) ni SIGLe, ODIN ou les autres systèmes existants : il les **complète** côté marin embarqué. Un lien futur pourra s'appuyer sur des identifiants techniques stables et des interfaces (API), mais il n'existe pas aujourd'hui. 🔵
- Matrix **n'autorise pas** un appareillage : il aide à le préparer (chapitre 16).
- Matrix **ne bloque pas** une tâche ordinaire faute de qualification : il informe. Les exigences réglementaires restent respectées pour les visas, les fonctions de service et les signatures officielles. 🔵 (mise en œuvre à venir, chapitre 14)
- Matrix n'est **ni un système officiel, ni homologué**. La version actuelle sert à la démonstration et à la recette sur données fictives ; aucun déploiement opérationnel n'est autorisé.

## 1.3 Les principes qui gouvernent le produit

Dix principes figurent dans les règles du projet (`CLAUDE.md`) ; le cahier des charges en retient sept « non négociables ». Les voici regroupés par ce qu'ils changent concrètement.

**Pour le marin**
1. **Tout est en français**, vocabulaire de la Marine (COMAEQ, COMOPS, COMANAV, COMAVIA, commandant en second…). Interface, messages, notifications, documentation.
2. **Plus rapide qu'Excel** : formulaires pré-remplis, actions en un clic, saisie en grille façon tableur, pas de jargon informatique.
3. **Un espace personnel par marin** : ses tâches, formations, maintenances, quarts et services.
4. **Visuel et agréable à utiliser** : un graphique, une jauge ou une carte plutôt qu'un tableau brut, sans surcharge. Le marin voit *ce qui lui est utile maintenant*.

**Pour l'organisation**
5. **Configuration plutôt que code** : rien de ce qui peut changer d'un bâtiment à l'autre n'est figé dans le programme. La durée d'un quart, les droits d'un chef, les modules actifs sont des réglages. *Exemple :* les seuils de rôle d'une action se règlent par bâtiment (chapitre 5).
6. **Administration distribuée** : on distingue *permission* (que puis-je faire ?), *périmètre* (sur quoi ?), *responsabilité* (que dois-je gérer ?) et *configuration* (que puis-je adapter ?). L'administrateur technique gère la plateforme, pas le fonctionnement métier quotidien. Matrix n'invente pas de système parallèle : il étend les rôles, les permissions, les périmètres et les notifications existants.
7. **Proposer, valider, publier** pour les modifications sensibles : la version publiée reste active jusqu'à validation de la suivante, et chaque version est conservée.
8. **Le dialogue est une fonction métier** : une question sur une tâche, un équipement ou une anomalie reste attachée à cet objet (module de discussions).

**Pour la confiance**
9. **Internet n'existe pas** : aucun CDN, aucune police distante, aucun service en ligne, aucune télémétrie. Toutes les bibliothèques de l'interface sont embarquées (chapitre 18).
10. **Tout est traçable** : une information importante ne disparaît jamais sans laisser de trace. Le journal d'audit enregistre qui a fait quoi, quand, avec quelle valeur avant et après (chapitre 22).

## 1.4 Comment ces principes se retrouvent dans l'application

| Principe | Où on le voit dans l'état B | Chapitre |
|---|---|---|
| Configuration plutôt que code | 35 actions dont le niveau de rôle minimal se règle par bâtiment ; 14 modules activables ; double équipage activable | 4, 5 |
| Administration distribuée | Écran Réglages (onglets Sécurité, Modules, Équipage, Journal…) ; l'administrateur d'unité règle son bâtiment | 5 |
| Proposer, valider, publier | Relève d'équipage (proposée par un commandant, validée par l'autre équipage) ; listes et feuilles de service | 4, 8 |
| Traçabilité | Journal d'audit alimenté par une vingtaine de modules du code | 22 |
| Internet n'existe pas | Bibliothèques Bootstrap, HTMX, Chart.js, FullCalendar servies localement | 18 |
| Ne rien supprimer en silence | Archivage des unités, suppression refusée tant que quelque chose les référence | 4 |

## 1.5 Fonctionnement cible : l'ambition à terme

🔵 Le cahier des charges décrit un « système d'exploitation numérique du bord », où le marin dialogue avec ses collègues et la terre, suit ses anomalies jusqu'à leur résolution, consulte les procédures et prépare l'appareillage dans le même outil. Plusieurs briques sont validées mais **pas encore développées** : suppléance explicite, circuit de validation des RETEX, durée estimée des tâches, mutation de personnel, échanges avec la terre par discussion contextuelle, synchronisation entre le bord et la terre. Elles sont rassemblées au chapitre 25, avec leur statut.

Le PO a aussi fixé une directive de méthode (31/10/2026) : Matrix doit être pensé avec une **logique de marin militaire**, c'est-à-dire :
- comprendre le métier avant l'interface (quarts, relève, BSC, COMA, services) ;
- privilégier l'usage en service (fatigue, interruptions, postes partagés, connexion parfois limitée) ;
- respecter la chaîne de responsabilités : **grade, fonction exercée, périmètre, habilitation et autorité de visa sont des notions distinctes** ;
- ne pas sur-automatiser : on ne contrôle automatiquement que ce qui est nécessaire maintenant.

## 1.6 Limites et éléments non vérifiés

- ⚪ Les formulations du cahier des charges (édition du 10/10/2026) ont été relues contre le code ; celles qui décrivent des fonctions non développées sont en 🔵. La génération automatique des tours de quart, décrite aux sections 8, 10 et 11 du cahier, **a été abandonnée** par décision métier : la planification est manuelle, avec contrôle des contraintes.
- ⚪ La page Notion « Cahier des charges » porte l'état « non vérifié » ; elle n'est pas une recette.
- ⚪ Le *Guide du marin 2023* n'a jamais été disponible : le dossier ne s'appuie sur lui pour aucune règle.

---

**Sources (état B).** `CLAUDE.md` (principes), `README.md`, `matrix/core/role_thresholds.py:45` (registre des actions), `matrix/core/modules.py:66` (registre des modules), Notion : « Cahier des charges » (10/10/2026), « 13 — Décisions Matrix et gouvernance fonctionnelle » (directive du 31/10/2026).
