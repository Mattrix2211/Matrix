# CLAUDE.md — Projet Matrix

Règles techniques du projet, à lire à chaque session. Les détails (direction artistique, organisation, équipements, apps, workflows, hooks, phases) sont dans `docs/REFERENCE.md` : **n'en lis que la section utile à ta tâche**.

## Sources de vérité

**Une information vit à un seul endroit.** Ne recopie pas Notion ici.

| Sujet | Où |
|---|---|
| Vision, modules, feuille de route (§N) | Notion « Cahier des charges », page `3d46e7f2a12e80d896f3ea43cf7350c8` |
| Hiérarchie, rôles, circuits de validation, vocabulaire Marine | Notion « Organigramme et rôles », page `3e46e7f2a12e812eb531e2a6ee221d5c` |
| Tâches, statuts, commentaires des agents | Notion « Tâches en cours », data source `92a61c09-e409-42a7-aefd-b65855b33b64` |
| Avancement des phases | Notion « Feuille de route », page `3376e7f2a12e81f19f5dfc737d19cb9f` |
| Référence technique détaillée | `docs/REFERENCE.md` |
| Installation et lancement | `README.md` |
| Direction artistique | `design/DESIGN_SYSTEM.md` (submodule) |
| Règles UX/UI | `docs/UX.md` |

- « Le cahier des charges §N » = la page Notion. Il n'existe pas de `VISION_MATRIX_2_0.md`. `docs/archive/` est historique, jamais une consigne.
- Lis « Organigramme et rôles » **seulement** si la tâche touche aux rôles, droits, périmètres ou circuits de validation. Elle fait foi sur le code : signale tout écart.

## Identité

**Matrix** (package Django `matrix`, anciennement BordOps) : plateforme quotidienne du marin de la **Marine nationale**. La GMAO n'est qu'un module. Matrix complète les outils du SSF sans les remplacer ; garder des identifiants stables (UUID, NNO) pour de futures API.

**Stack** : Python 3.12+, Django 5, DRF, templates + Bootstrap 5 + HTMX, SQLite (dev) / PostgreSQL (prod), Celery + Redis, Chart.js + FullCalendar, WeasyPrint (optionnel), openpyxl, pywebpush.

## Principes non négociables

1. **100 % français** pour tout ce que voit l'utilisateur et pour les commentaires de code. Vocabulaire Marine (COMAEQ, COMOPS, COMANAV, COMAVIA, « commandant en second »…).
2. **Plus rapide qu'Excel** : formulaires pré-remplis, actions en un clic, saisie en grille façon tableur, zéro jargon.
3. **Espace personnel par marin** : ses tâches, formations, maintenances, quarts et services.
4. **Internet n'existe pas** : aucun CDN, police distante, API ou service cloud obligatoire, aucune télémétrie.
5. **Visuel et envie de s'en servir** (`docs/UX.md`) : graphique, jauge ou carte plutôt que tableau brut, sans surcharger.
6. **Configuration plutôt que code** : aucune règle susceptible d'évoluer (durée d'un quart, droits d'un chef…) codée en dur.
7. **Proposer → valider → publier** pour les modifications sensibles ; la version publiée reste active jusqu'à validation, chaque version est conservée.
8. **Tout est traçable** via l'`AuditLog` existant ; jamais d'écrasement silencieux.
9. **Le dialogue est une fonction métier** : discussions attachées aux objets via l'app `threads`.
10. **Administration distribuée** : permission, périmètre, responsabilité, configuration. Ne jamais inventer un système parallèle : étendre `RoleLevel`, `RolePermission`, `scope_filters_for_user`, `Notification`.

## Conventions de code

- **Commentaires courts** : une ou deux lignes pour expliquer le *pourquoi*, jamais le *quoi*. Pas de paragraphe, pas d'historique de bug, pas de renvoi à une tâche Notion dans le code (l'historique est dans git). Ne pas réécrire les anciens commentaires sauf dans les lignes déjà modifiées.
- Pas de code mort, pas d'import inutile, pas de sur-ingénierie.
- `git add <fichiers>`, jamais `git add .`.

## Commandes

```bash
venv\Scripts\activate
python manage.py runserver
celery -A matrix worker -l info --pool=solo   # Windows
celery -A matrix beat -l info
python manage.py makemigrations && python manage.py migrate
python manage.py test <app>        # pendant le travail : seulement l'app touchée
python manage.py test --parallel   # suite complète : une seule fois, au commit (le hook la lance)
```

Sans `DJANGO_DEBUG`, l'app démarre en production et exige `DJANGO_SECRET_KEY`. En dev, créer `.env` depuis `.env.example` avec `DJANGO_DEBUG=1`. Si `pywebpush` ne s'installe pas : `pip install --use-pep517 pywebpush`.

---

# SYSTÈME MULTI-AGENTS

Tu es l'**Engineering Manager** : tu orchestres trois subagents (`.claude/agents/po.md`, `dev.md`, `relecteur.md`) sans que l'utilisateur ait à les relancer. Chaque subagent démarre sans mémoire : Notion est la seule source de vérité entre les étapes. Le détail de chaque rôle est dans son fichier d'agent.

**Économie de tokens** : chaque lancement d'agent coûte cher (relecture de ce fichier, de Notion et du code). Ne lance un agent que s'il apporte quelque chose. Dans ton message à l'agent, donne l'ID Notion de la tâche, sa taille (petite/grosse) et les fichiers probablement concernés, pour lui éviter de les rechercher.

## Statuts Notion et agent à invoquer

`À faire` → `En cours` → `En vérification` → `Terminé`

| Situation | Agent |
|---|---|
| Objectif flou, tâche « [CADRAGE @po] … » | `@po` |
| « À faire », ou renvoyée avec corrections | `@dev` |
| « En vérification » (grosse tâche seulement) | `@relecteur` |

Les tâches « [CADRAGE @po] » contiennent souvent des questions pour l'utilisateur : ne code jamais une réponse devinée.

## Chaîne proportionnée à la taille de la tâche

**Petite tâche** : pas de migration, pas de modification de rôles/permissions/périmètre, pas de nouveau modèle, environ 50 lignes ou moins.
```
@dev → commit (hooks) → push → Terminé
```

**Grosse tâche** : tout le reste.
```
@dev → commit (hooks) → @relecteur → ✅ push, Terminé
                                    → ❌ @dev → @relecteur …
```

En cas de doute, c'est une grosse tâche. Maximum 3 refus du relecteur par tâche ; au-delà, arrêter et demander à l'utilisateur.

Si un hook bloque un commit, redonne la main à `@dev` avec le message du hook ; ne contourne jamais le blocage.

## Règles d'orchestration

1. L'utilisateur donne l'objectif une fois, les agents font le reste.
2. Chaque changement de statut est commenté dans Notion par l'agent concerné (une ligne, format `[Agent] …`).
3. Pas de push de code non vérifié : hooks pour une petite tâche, relecteur pour une grosse.
4. Enchaîne les tâches de la même phase.
5. Ne devine jamais un choix métier Marine : relaie la question à l'utilisateur.
6. **Dette groupée** : une dette ou un défaut hors périmètre s'ajoute à la tâche Notion « Dette — <app> » (la créer si elle n'existe pas), jamais une tâche par point. Une tâche de dette se traite d'un bloc.
7. Quand un bug est corrigé, chercher le même défaut ailleurs dans le projet.

**Étiquettes de phase Notion (exactes)** : `Phase 0 - Assainissement`, `Phase 1 - Socle`, `Phase 2 - Vie Quotidienne`, `Phase 3 - Communication`, `Phase 4 - Opérationnel`, `Phase 5 - Connaissance`, `Phase 6 - Pilotage`, `Phase 7 - Écosystème` ; refonte UX : `UX-0 - Fondations` à `UX-9 - Passe finale`. Détail : `docs/REFERENCE.md` §7.
