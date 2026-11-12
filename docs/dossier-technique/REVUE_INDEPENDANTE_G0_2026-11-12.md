# Relecture indépendante de G0 — 12 novembre 2026

**Statut :** revue partielle fondée sur les sources Markdown et une lecture ciblée du code de l'état B (`6d6d0be`). Ce document n'est ni une recette fonctionnelle ni une autorisation de diffusion ou de mise en production.

**Périmètre :** chapitres 3, 6, 12, 17, 22, 23 et registre des écarts ; code `dashboard/passation.py`, `matrix/core/middleware.py` et `maintenance/models.py`. Le rendu intégral des deux PDF n'a pas été contrôlé.

## Constats confirmés par lecture du code

### A14 — Visibilité des synthèses de passation : risque de périmètre

Dans `dashboard/passation.py`, `syntheses_visibles(user)` filtre par bâtiment et équipage, avec contrôle de niveau de commandement ou de supervision, mais **n'applique aucun filtre par section**. `contenu_passation()` construit des blocs de synthèse au niveau du bâtiment (tâches, maintenances, tickets, anomalies, stock, qualifications, listes, annonces, demandes). La règle PO de limitation à la section ne paraît donc pas implémentée à cet endroit.

**Qualification :** écart de contrôle d'accès étayé par le code, à confirmer par test d'intégration avec un chef de section et des données de deux sections distinctes. Ne pas affirmer qu'une fuite réelle a été observée.

### A25 — Modules désactivés : portée du contrôle

`ModuleActivationMiddleware.process_view` dans `matrix/core/middleware.py` retourne immédiatement pour les chemins `/api/` et `/admin/`. Le commentaire du middleware précise que les tâches Celery et les enchaînements internes continuent malgré la désactivation. La règle « module désactivé » s'applique donc aux vues web prises en charge par ce middleware, **pas à l'ensemble des surfaces d'exécution**.

**Qualification :** comportement confirmé par lecture du code. Le statut de risque dépend de la règle métier attendue ; ne pas modifier sans décision PO. Tester séparément l'API et les tâches.

## Point à vérifier davantage

### A20 — Occurrences en validation

`maintenance/models.py` définit `WAITING_VALIDATION`. Le chapitre 12 décrit l'absence de validation dédiée et une sortie par correction de compte rendu ; ce point reste à vérifier dans les vues, services et tâches concernés ainsi que par un test de transition. Ne pas confondre « non vérifié par la présente revue » et « inexistant ».

## Corrections éditoriales déjà réalisées sur cette branche

- Chapitre 3 : quatre étiquettes documentaires, non trois.
- Chapitre 17 : distinction explicite entre cible validée, proposition et observation de recette.
- Chapitre 6 : mise à jour de la mention de lecture de la recette UX V1.1.

## Réserves avant validation finale

1. Rejouer des tests ciblés A14, A20 et A25 sur une instance de test isolée, avec données fictives.
2. Vérifier la cohérence des renvois et des étiquettes sur l'ensemble des 26 chapitres.
3. Vérifier visuellement les PDF (pagination, sommaire, schémas, tableaux, caractères et séparation de diffusion) puis les régénérer après corrections.
4. Faire relire les circuits métier à un marin et à un responsable habilités.
5. Soumettre la classification et les destinataires des PDF à l'autorité compétente.

**Aucun code applicatif modifié ; aucune décision PO modifiée ; aucune fusion, PR ou lot lancé.**
