# Passage A : QA ergonomie et interface (agent `qa-ergonomie`)

- **SHA** : `59dd2f2`, worktree jetable, base `seed_demo` SQLite, serveur de développement (port 8101), Chromium 1194 piloté par Playwright (utilisable).
- **Traces** : sondes, JSON et captures conservés hors dépôt dans le répertoire temporaire de la session (non versionnés).
- **Limites d'exécution** : (1) le worktree au SHA `59dd2f2` ne contenait pas `docs/recette-v1/` (créé après) : format de rapport et grille reconstitués d'après la consigne ; (2) le sous-module `design/` est vide (non initialisé) : la charte graphique n'a pas pu être vérifiée, seule la cohérence avec `docs/UX.md` l'a été ; (3) Chromium sans locale française affiche des messages natifs en anglais : artefact exclu des défauts.
- **Synthèse** : aucun P1. Points solides : aucune ressource externe (~160 chargements), aucun débordement horizontal (1366×768, 1024×768, 390×844), focus visible, mode sombre cohérent, impression correcte, tiroir mobile conforme.

## Constats

| Id | Constat | Statut | Prio | Catégorie |
|---|---|---|---|---|
| ERG-01 | 1366×768, comptes equipier_a, chef_section_a, chef_service_a, cdt_a, coma_comanav, admin (24 à 30 pages chacun) : aucun débordement, zéro requête hors `127.0.0.1` (polices, icônes, Chart.js, FullCalendar auto-hébergés), seule erreur console = 403 d'ERG-05 | Réussi | — | — |
| ERG-01b | 1024×768 et 390×844 (échantillon) : sans défaut ; tiroir `aria-expanded`, Échap, boutons 44 px. Le fil à 4 pastilles passe sur deux lignes | Réussi | P3 | Ergonomie |
| ERG-02a | Menu cohérent entre rôles (noyau de 22 entrées). Le fil « Mon quotidien · Mon équipe · Suivi · Synthèse » n'apparaît que sur 4 pages (Aujourd'hui, Calendrier, Tâches, Demandes), absent de « Quarts et gardes » alors que `docs/DEMO.md` l'y cite ; « Synthèse » toujours actif sur `/taches/` | Réussi avec réserves | P3 | Ergonomie |
| ERG-02b | Aucun « chef de groupement » ni « CAN » ; `lang="fr"`. Anglicismes courants (« Tickets correctifs », « Checklist ») | Réussi | P3 | Ergonomie |
| ERG-02c | Libellés incohérents menu/titre : « Prêt à appareiller » / « Prêt à appareillage » (`pret_appareillage.html:5`), « Logistique » / « Stock de pièces », « Flotte » / « Vue de ma section », « Maintenance » / « Gestion de la maintenance » ; espace avant « : » manquante ; `<title>` = « Matrix » sur les 160 pages | Échoué | P3 | Ergonomie |
| ERG-03a | Focus : contour 2 px sur tous les éléments testés, clair et sombre, aucun piège, Ctrl+K place le focus dans la recherche | Réussi | — | — |
| ERG-03b | Pas de lien d'évitement : 32 tabulations (equipier_a) et 39 (admin) avant `<main>` sur `/taches/` | Échoué | P2 | Ergonomie |
| ERG-03c | « J'ai pris connaissance » atteint en 14 tabulations et confirmé ; « Signaler une difficulté » atteignable mais focus resté sur `body`, pas d'autofocus ; toast de confirmation de 3,5 s | Réussi avec réserves | P3 | Ergonomie |
| ERG-04a | `/taches/` (chef_section_a) : statistiques d'abord ; « Attribuer une tâche » à y=1660 sur 768 px (1996 pour cdt_a) ; pas de bouton d'action en tête, contre `docs/UX.md` §2.4. L'accueil du chef est correct | Échoué | **P2** | Ergonomie |
| ERG-04b | Autres actions principales dans la fenêtre (y=84 à 683) ; accueil equipier_a de 2 370 px avec graphiques de pilotage en bas : pertinence pour un équipier à poser au PO | Réussi avec réserves | P3 | Ergonomie |
| ERG-05 | **« Feuille de service » donne un 403 à `cdt_a`** alors qu'elle est dans son menu : `/quarts/feuille-service/` redirige vers l'unité id 1 (BordOps I) car `_navires_disponibles_feuille_service` renvoie `Ship.objects.all()` au niveau commandant et `FeuilleServiceIndexView` prend `.first()` (`quarts/feuille_service_views.py:48-56`). `admin` arrive aussi sur l'id 1 ; chef_service_a et COMANAV arrivent sur la Bretagne | Échoué | **P2** | Défaut technique (à recouper avec qa-securite) |
| ERG-05b | `equipier_a` voit « Créer le brouillon » de la feuille de service (`peut_rediger_feuille_service` : tout membre du navire), hypothèse déjà signalée dans `quarts/models.py:1472` | Échoué (écart documenté) | P3 | Incohérence métier à trancher |
| ERG-06a | Contraste clair : `btn-outline-warning` « Signaler une difficulté » = 1,47 ; badge « Terminées (30 j) » (blanc sur vert) = 2,62 ; le reste passe | Échoué | P2 | Défaut technique |
| ERG-06b | Contraste sombre : `text-danger` = 3,4 ; chiffre de la barre `bg-warning text-dark` = 1,39 ; même badge 2,62 | Échoué | P3 | Défaut technique |
| ERG-07a | Impression A4 (émulation) : en-tête bâtiment/date/utilisateur, noir et blanc, 1 page pour Formations, Quarts, Feuille de service, Matériels, Calendrier ; Tâches 3 pages avec pastilles imprimées, barre d'avancement en bloc noir, colonne Statut perdue p. 2 ; filtres imprimés sur Formations ; événements du dimanche rognés au calendrier ; feuille de service vide faute de donnée | Réussi avec réserves | P3 | Défaut technique |
| ERG-07b | Performance sous ralentissement (CPU ×4, 1,5 Mb/s, 150 ms) : 30 à 35 requêtes et ~1,55 Mo par page, FCP ~5,6 s, calendrier DCL 9,9 s ; `chart.umd.js` (205 Ko) chargé partout, logo `IMG_5292.PNG` de 434 Ko affiché en 40×40 ; serveur de développement sans compression : mesure pessimiste, non transposable à la production | Réussi avec réserves | P3 | Défaut technique |
| ERG-07c | Doughnut « Tickets correctifs » de 509×509 px (double du préventif), tout en bas de l'accueil ; « En attente pièces » en vert (UX §15.1 réserve le vert à « OK ») ; déjà déclaré sans correction | Échoué | P3 | Ergonomie |
| ERG-08 | Tablette 1024×768 tactile : liens de lignes de tableau à 17–20 px (sous 44 px), au-delà de l'exception de `docs/RECETTE.md` | Réussi avec réserves | P3 | Ergonomie |
| ERG-09 | Cohérence avec le design system | **Impossible à vérifier** (sous-module vide) | — | — |
| ERG-10 | Attribuer une tâche : échéance et priorité préremplies, toast « Tâche attribuée » ; marin pré-sélectionné sur le premier de la liste ; échéance passée acceptée sans avertissement ; « Signaler une difficulté » : responsable vide sans suggestion (13 chefs listés, admin du navire compris) | Réussi avec réserves | P3 | Ergonomie |

## Déclaré (`docs/RECETTE.md`) contre exécuté

Confirmé : 25 pages du chef de section, tiroir mobile, centre des échéances, graphique trop haut. Étendu : 5 rôles de plus à 1366×768. Rejoué en partie : 1024×768 tactile (liens de tableau à 20 px), 390×844 (2 comptes, clair). **Déclaré, non rejoué** : 375×667 et 768×1024, mobile sombre, recherche en icône, barre latérale à 768 px, filtre « Mon équipe », panneau de détail du calendrier, parcours Formation complet. Impression : émulation seulement, pas d'impression physique.

## Benchmark UX (0 à 4)

Action avant statistiques 2 · navigation stable 3 · dévoilement progressif 3 · discussion attachée à l'objet 3 · saisie une fois 3 · cohérence visuelle 3 · états et responsabilités 3 · dense mais calme 3. Preuves : voir les lignes ERG ci-dessus.

## Non vérifié

Design system, impression physique et feuille de service non vide, erreurs serveur de formulaires, mobile sombre, 375×667 et 768×1024, pièges de focus des modales, performance de production, ANO-001 (SQLite).
