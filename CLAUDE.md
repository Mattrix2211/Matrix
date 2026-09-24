# CLAUDE.md — Projet Matrix

Ce fichier est la référence technique pour Claude Code. Lis-le intégralement à chaque session.

## Sources de vérité — où se trouve chaque information

**Règle : une information vit à un seul endroit.** Ce fichier contient les règles techniques du projet et renvoie vers Notion pour tout ce qui relève du métier et des décisions de l'utilisateur. Ne recopie pas le contenu des pages Notion ici : il deviendrait vite faux.

| Sujet | Où | Référence |
|---|---|---|
| Vision, modules cibles, principes, feuille de route (Phases 0 à 7) | Notion — page **« Cahier des charges »** (Matrix 2.0) | page `3d46e7f2a12e80d896f3ea43cf7350c8` |
| Hiérarchie à bord et à terre, rôles, circuits de validation, vocabulaire Marine | Notion — page **« Organigramme et rôles »**, tenue par l'utilisateur | page `3e46e7f2a12e812eb531e2a6ee221d5c` |
| Tâches, statuts, commentaires des agents | Notion — base **« Tâches en cours »** | data source `92a61c09-e409-42a7-aefd-b65855b33b64` |
| État d'avancement des phases | Notion — page **« Feuille de route »** | page `3376e7f2a12e81f19f5dfc737d19cb9f` |
| Règles techniques, conventions de code, architecture | Ce fichier (`CLAUDE.md`) | — |
| Installation et lancement de l'application | `README.md` | — |
| Direction artistique | `design/DESIGN_SYSTEM.md` (submodule) | — |

Quand une tâche Notion cite « le cahier des charges §N », il s'agit de la page Notion « Cahier des charges ». Les anciennes références à « `VISION_MATRIX_2_0.md` §N » désignent un condensé de cette page rédigé par l'agent le 06/09/2026, désormais archivé dans `docs/archive/VISION_MATRIX_2_0.md` : sa numérotation diffère de celle de Notion, une table de correspondance figure en tête du fichier. `docs/archive/` contient des documents historiques, à ne pas suivre comme consignes actuelles : en cas de différence, la page Notion fait foi.

Avant toute décision sur les rôles, les droits, les périmètres ou un circuit de validation, lis la page « Organigramme et rôles ». Si le code et cette page divergent, c'est la page qui fait foi : signale l'écart à l'utilisateur.

## Identité du projet

**Matrix** — plateforme numérique opérationnelle quotidienne du marin, pour la **Marine nationale française**. Le package Django s'appelle `matrix`, le projet s'appelle **Matrix** (anciennement BordOps).

**Matrix n'est pas une GMAO : la GMAO est un module de Matrix.** L'objectif est que chaque marin ouvre Matrix tous les jours (sa journée, ses quarts, ses services, ses tâches, ses formations), et que Matrix serve pendant son travail (fiches de maintenance, comptes rendus).

**Place face au SSF** (Service de soutien de la flotte, qui gère le maintien en condition opérationnelle des bâtiments avec ses propres outils) : Matrix est leur « frère » côté marin embarqué, et donne au SSF une vision simple et à jour de sa flotte. Il ne remplace pas leurs outils. Des API d'échange viendront bien plus tard : garder dès maintenant des identifiants stables (UUID, NNO).

## Stack technique

- Python 3.12+, Django 5, Django REST Framework
- Frontend : Django Templates + Bootstrap 5 + HTMX
- Base de données : SQLite (dev), PostgreSQL (prod)
- Tâches asynchrones : Celery + Redis
- Graphiques : Chart.js + FullCalendar
- Export : PDF (WeasyPrint, optionnel), CSV/Excel (openpyxl) ; Web Push (pywebpush, clé VAPID auto-hébergée)

## Principes fondamentaux — NON NÉGOCIABLES

1. **100 % français** — tout ce que voit l'utilisateur : labels, boutons, messages, statuts, placeholders, tooltips, titres, commentaires dans le code. Utiliser le **vocabulaire de la Marine** (sigles COMAEQ, COMOPS, COMANAV, COMAVIA, « commandant en second »…) : voir la section Vocabulaire de la page « Organigramme et rôles ».
2. **Plus rapide qu'Excel** — si une action prend plus de clics que dans un tableau Excel, c'est un échec. Formulaires pré-remplis, actions en un clic, saisie en grille façon tableur (recopie vers le bas, « tout conforme », navigation au clavier), zéro jargon informatique.
3. **Espace personnel par marin** — chaque marin voit SES tâches, SES formations, SES maintenances, SES quarts et services.
4. **Internet n'existe pas** — Matrix fonctionne sur le réseau du bâtiment (et l'intranet Défense), jamais sur Internet : aucun CDN, aucune police distante, aucune API ou service cloud obligatoire, aucune télémétrie. Une coupure avec la terre ne doit pas rendre le bâtiment inutilisable.
5. **Priorité au visuel et envie de s'en servir** — dès qu'un schéma, un graphique, une jauge, une frise ou une carte peut remplacer du texte ou un tableau brut, l'utiliser. Les écrans doivent être beaux et donner envie aux marins de les ouvrir (cartes avec photos, badges d'état colorés), sans jamais surcharger l'écran : le marin voit ce qui lui est utile maintenant.
6. **Configuration plutôt que code** (cahier des charges §4 et §33) — ne jamais coder en dur une règle susceptible d'évoluer selon le bâtiment, le service, la Marine ou l'organisation (durée d'un quart, nombre de services, droits d'un chef, types de garde…). Ces règles sont des données configurables par les utilisateurs habilités.
7. **Proposer → valider → publier** (§34) — pour les modifications sensibles (fiches de maintenance, catalogue de matériel, listes de service…), un utilisateur peut avoir le droit de proposer sans avoir le droit de publier. La version publiée précédente reste active tant que la nouvelle n'est pas validée, et chaque version est conservée.
8. **Tout est traçable** (§30, §41) — qui a fait quoi, quand, sur quelle donnée, quelle était la valeur précédente. Une modification n'écrase jamais silencieusement l'ancienne valeur : s'appuyer sur l'`AuditLog` unifié existant.
9. **Le dialogue est une fonction métier** (§16) — la communication est attachée aux objets de travail (tâche, équipement, anomalie, ticket), via l'app `threads` existante.
10. **Administration distribuée** (§5) — distinguer permission (que puis-je faire ?), périmètre (sur quoi ?), responsabilité (que dois-je gérer ?) et configuration (que puis-je adapter ?). Les chefs gèrent leur périmètre ; l'administrateur technique gère la plateforme, pas le fonctionnement métier.
11. **Aucune fonctionnalité en silo** (§41) — avant tout développement, identifier les objets métier concernés, les rôles et périmètres impactés, le workflow complet déclenché (pas seulement l'action demandée), les notifications à envoyer, l'historique à conserver et les modules existants à réutiliser plutôt qu'à dupliquer. Exemple : une « demande de matériel » implique la demande, la notification du chef, la validation, la vérification du stock, le mouvement de stock, la notification du marin et l'historique. Une tâche n'est faite que si elle respecte les permissions, ne casse rien d'existant, est testée et reste utilisable hors ligne.

## Direction artistique

La DA de Matrix suit le **MK Design System** (submodule `design/`, source de vérité : `design/DESIGN_SYSTEM.md`). Lis ce fichier en entier avant toute décision visuelle ou tout template.

**Config Matrix / Naval** (voir tableau "Contextes par projet" du design system) :
- **Mode Light** — pas de dark mode ici (le light est réservé aux contextes naval/pro)
- Typo : `Space Grotesk` (titres de section, cards, nav) + `Inter` (corps de texte) + `JetBrains Mono` (données techniques, dates, codes, labels) — **jamais `Syncopate`** (réservé hero/sport)
- **Pas d'Ember** (`--ember` réservé au sport)
- Vert unique : `--green-tech` (statuts systèmes/validations navales) — jamais `--green-sport`
- Accent unique : `--signal` (#00B4D8), une seule action principale par vue
- Logo : `design/assets/IMG_5292.PNG` (requin marteau), pictogramme ancre en overlay bas-droite pour Matrix
- Espacement base 4px strict, radius/shadows/composants (cards, badges, progress bars) : voir `design/DESIGN_SYSTEM.md` §4 à §8

**Conflit avec le principe hors-ligne (à respecter) :** le design system référence les polices via Google Fonts CDN — **auto-héberger** `Space Grotesk`, `Inter` et `JetBrains Mono` dans `static/fonts/` plutôt que d'utiliser le lien CDN, conformément au principe fondamental n°4.

## Organisation et rôles (résumé — la page Notion « Organigramme et rôles » fait foi)

**À bord** (organisation configurable par navire) : Commandant → Commandant en second (même vision globale que le commandant) → commandants adjoints **COMAEQ** (équipage), **COMOPS** (opérations), **COMANAV** (navire), et **COMAVIA** (aviation, seulement sur les bâtiments avec une capacité aviation) → chefs de service → chefs de secteur → chefs de section → opérateurs. Chaque service dépend d'un commandant adjoint. Dans l'interface, afficher le sigle, jamais « chef de groupement ».

**Double équipage** (FREMM, PSP, BSAM uniquement) : deux équipages à l'organisation en miroir sur le même bâtiment ; l'équipage à terre garde un accès en lecture seule. Le bâtiment porte installations, matériel, fiches, historique et stock ; l'équipage porte les personnes, quarts, services, assignations et l'espace personnel.

**À terre** : ALFAN → division Exploitation → spécialités (Mécan, Sécu, Élec, SIC, Artilleur). Chaque spécialité a un **responsable de spécialité** (`accounts.ResponsableSpecialite`) ; au-dessus, un **chef du responsable de spécialité**, qui peut encadrer plusieurs responsables mais pas tous. Le **SSF** suit une classe entière ou une liste de bâtiments et peut agir (commenter un ticket…).

**Codes techniques des rôles** (inchangés dans le code) : `MASTER_ADMIN → ADMIN_NAVIRE → COMMANDANT → ETAT_MAJOR → CHEF_SERVICE → CHEF_SECTEUR → CHEF_SECTION → EQUIPIER`. Chaque rôle ne voit que ce qui le concerne. Ne jamais inventer un système de rôles, de permissions, de périmètre ou de notification parallèle : étendre `RoleLevel`, `RolePermission`, `scope_filters_for_user`, `Notification`.

## Deux types d'équipements

- **Installations** : équipements fixes du navire (propulseurs, pompes, circuits électriques). Propres à chaque bâtiment. Modèle `Installation` dans l'app `assets`. Mesures techniques associées : heures de marche, vibrations (A/B/C), isolement (Ohms) — avec détection de dérive (régression linéaire simple) avant franchissement de seuil, et champ `critique` déclenchant une signature de validation (mot de passe) sur les transitions sensibles.
- **Matériel mobile** : équipements transverses (extincteurs, EPI, multimètres, élingues). Modèle `Asset` dans l'app `assets`, toujours rattaché à un navire. Suivi par catégorie avec fiche individuelle (numéro de série, date de contrôle, péremption).
- Les deux modèles supportent une hiérarchie parent/enfant (rattachement, protection anti-cycle).

**Décisions métier en cours de cadrage** (détail et questions ouvertes dans les tâches Notion « [CADRAGE @po] … ») :
- **Catalogue de matériel flotte** : géré à terre par les responsables de spécialité ; le bord choisit un article et une quantité, puis complète le suivi de chaque exemplaire.
- **Fiches de maintenance** : une fiche par gamme (calendaire ou heures de marche, gammes non cumulatives), contenant checklist et/ou relevés. Matériel : une fiche par catégorie du catalogue, toujours flotte, publiée par le responsable de spécialité (le bord peut seulement proposer). Installations : fiches bord, validées par le chef de service puis le commandant adjoint du service.
- **Comptes rendus d'intervention** : générés depuis les fiches, saisie en série façon tableur pour le matériel, historique et suivi des relevés automatiques, notifiés au chef de secteur (modification possible et tracée).

## Architecture Django — 14 modules

| App | Rôle |
|-----|------|
| `accounts` | Utilisateurs, profils, rôles, grades, spécialités, responsables de spécialité |
| `org` | Unités (typées : navire, école, centre de formation, bureau) → Service → Secteur → Section ; classes de navire, seuils de rôle et modules activables par bâtiment |
| `assets` | Installations fixes + matériel mobile, checklists, documents, mesures techniques, détection de dérive, plan du navire |
| `maintenance` | Plans préventifs, occurrences, exécutions, checklists guidées, signature de validation sur transitions critiques |
| `logistics` | Tickets correctifs, anomalies, demandes de pièces, stock, retours d'expérience (REX) |
| `training` | Formations, prérequis, catégories, arbre de compétences, référents, sessions, circuits de candidature |
| `quarts` | Quarts, services à quai et gardes, listes (chef de liste), échanges, équité, génération assistée |
| `absences` | Absences et indisponibilités des marins, prises en compte par les échanges, la génération des listes et le calendrier |
| `rondes` | Rondes de contrôle : modèles, points de contrôle configurables, exécutions |
| `threads` | Discussions génériques (attachées à n'importe quel objet) |
| `notifications` | Alertes in-app (info/warning/danger), Web Push pour le niveau danger |
| `dashboard` | Tableau de bord personnel, vues par périmètre, tableaux de bord par spécialité et par classe de navire |
| `calendar_app` | Calendrier central (colonne vertébrale), vue globale + personnelle, export iCal |
| `reports` | Bilans instantané/période, export PDF / CSV / Excel |

## Structure des URLs

- `/api/*` — API REST (DRF)
- `/` — Interface web (templates Django)
- Chaque app a `views.py` (API) et `web_views.py` (templates)

## Workflows clés

### Maintenance préventive (Celery)
- `generate_occurrences` quotidien : crée les occurrences 90 jours à l'avance
- `compute_overdue` horaire : marque les retards
- Cycle : `PLANNED → ASSIGNED → IN_PROGRESS → WAITING_VALIDATION → DONE`

### Inspection QR → ticket correctif
1. Scan QR → occurrence du jour
2. Checklist remplie → `MaintenanceExecution`
3. Si `NON_CONFORME` → création auto d'un `CorrectiveTicket`

### Ticket correctif
`REPORTED → DIAGNOSED → WAITING_PARTS → IN_REPAIR → TESTING → RETURNED_TO_SERVICE → CLOSED` (mot de passe requis sur `RETURNED_TO_SERVICE` si l'installation est `critique` ; REX obligatoire à `CLOSED`)

### Formations
1. Prérequis entre formations (protection anti-cycle, réutilisée du parent/enfant `assets`)
2. Validation d'une formation réservée aux référents habilités pour CETTE formation précise (indépendant du rang hiérarchique) — ou aux rôles de supervision globale (COMMANDANT+)
3. Arbre de compétences visuel par secteur/catégorie (niveaux, code couleur validé/disponible/verrouillé), 100% CSS/HTML/SVG sans dépendance externe
4. Réservation self-service d'une place sur une session (distincte de la validation), avec notification et intégration au calendrier personnel

## Commandes de développement

```bash
# Lancer le serveur
venv\Scripts\activate
python manage.py runserver

# Celery (Windows)
celery -A matrix worker -l info --pool=solo
celery -A matrix beat -l info

# Migrations
python manage.py makemigrations
python manage.py migrate

# Tests — pendant le développement, ne lancer QUE les apps modifiées (retour rapide) :
python manage.py test <app_modifiee> <autre_app_modifiee>

# Tests — suite complète en parallèle (nécessite tblib), avant commit / QA :
python manage.py test --parallel auto
```

**Environnement de développement :** sans variable `DJANGO_DEBUG`, l'application démarre en mode production et exige une vraie `DJANGO_SECRET_KEY`. En développement (y compris dans une session Claude Code dans le cloud), créer un fichier `.env` local (jamais commité) à partir de `.env.example`, avec au minimum `DJANGO_DEBUG=1`. Si l'installation de `pywebpush` échoue (dépendance `http-ece` qui ne compile pas), essayer `pip install --use-pep517 pywebpush` : sans elle, 16 tests de notifications échouent.

---

# SYSTÈME MULTI-AGENTS AUTONOME

## Philosophie

Tu es un **Engineering Manager** qui dirige une équipe de 4 agents spécialisés — de vrais subagents Claude Code (`.claude/agents/po.md`, `dev.md`, `tech-lead.md`, `qa.md`), pas des rôles joués dans une seule conversation. Quand l'utilisateur donne un objectif, tu orchestres toute la chaîne **sans intervention humaine** jusqu'à ce que le résultat soit validé. L'utilisateur ne doit PAS relancer les agents un par un.

Chaque subagent tourne dans son propre contexte isolé et **n'a aucune mémoire des invocations précédentes** — c'est pour ça que la base Notion "Tâches en cours" est la seule source de vérité entre les étapes. Le détail complet de ce que fait chaque rôle (format des commentaires, critères de vérification, actions précises) vit dans son fichier `.claude/agents/*.md` — ce document ne garde que la boucle globale, pour ne pas dupliquer l'information à deux endroits.

## Notion — source de vérité entre les agents

Base **"Tâches en cours"**, data source ID `92a61c09-e409-42a7-aefd-b65855b33b64`.

**Colonnes :** Tâche (titre) · Phase (Phase 0 à Phase 7, voir la table plus bas) · Statut (`À faire` → `En cours` → `En vérification` → `En test` → `Terminé`) · Priorité (Haute/Moyenne/Basse) · Commentaires (chaque agent y écrit ce qu'il a fait, format `[Nom de l'agent] ...`). Une tâche peut aussi porter une spécification détaillée dans le **contenu de sa page** : lis-le en entier, pas seulement la colonne Commentaires.

Les tâches intitulées **« [CADRAGE @po] … »** sont des objectifs à découper par `@po` en tâches concrètes avant tout développement. Elles contiennent souvent des questions à poser à l'utilisateur : ne code jamais une réponse devinée.

## Invocation des agents

Invoque chaque agent explicitement (`@po`, `@dev`, `@tech-lead`, `@qa`) selon le statut de la tâche dans Notion :

| Statut Notion | Agent à invoquer |
|---|---|
| Objectif flou, tâche « [CADRAGE @po] », pas encore de tâche | `@po` |
| "À faire" | `@dev` |
| "En vérification" | `@tech-lead` |
| "En test" | `@qa` |

À chaque retour d'un agent, lis son résumé (pas le détail de son travail interne, qu'il n'expose pas), identifie le nouveau statut de la tâche, et invoque immédiatement l'agent suivant — sans attendre de confirmation de l'utilisateur.

## Garde-fous automatiques (hooks)

En plus de ce que chaque agent vérifie lui-même, quatre hooks (`.claude/hooks/`) font respecter mécaniquement des règles non négociables, indépendamment de la discipline de l'agent :
- `verifier-tests-avant-commit.sh` — bloque tout `git commit` si `python manage.py test` échoue
- `verifier-francais-avant-commit.sh` — bloque tout `git commit` si du texte anglais suspect apparaît dans le diff
- `verifier-migration-retrocompatible.sh` — alerte si une migration ajoute un champ sans valeur par défaut (rétrocompatibilité du schéma)
- `verifier-migrations-appliquees-avant-commit.sh` — bloque tout `git commit` si des migrations Django ne sont pas appliquées à la base de développement locale (`db.sqlite3`), distinct du précédent qui contrôle le schéma et non l'application effective. Un garde-fou complémentaire (`matrix/core/checks.py`, système de checks Django) avertit aussi au démarrage de `python manage.py runserver` si des migrations restent en attente, pour couvrir le cas d'un poste qui récupère du code déjà commité par quelqu'un d'autre

Si un commit est bloqué par un hook, traite-le comme un refus du Tech Lead : redonne la main à `@dev` avec le message d'erreur du hook, ne contourne jamais le blocage.

## Boucle de correction (automatique)

```
@dev → @tech-lead → ❌ → @dev → @tech-lead → @qa → ❌ → @dev → @tech-lead → @qa → ✅ Terminé
```

Maximum 3 boucles de correction par tâche (cette limite est appliquée par l'agent `qa` lui-même). Au-delà, arrêter et demander à l'utilisateur.

## Règles d'orchestration

1. **L'utilisateur ne doit intervenir qu'une fois** — il donne l'objectif, les agents font le reste
2. **Chaque transition de statut = un commentaire Notion**, posté par l'agent concerné, pas par toi directement
3. **Git commit uniquement quand le QA valide** — pas de code non vérifié sur GitHub
4. **Enchaîner les tâches** — quand une tâche est terminée, invoque `@dev` sur la suivante si la même phase en contient d'autres à faire
5. **Jamais sauter d'étape** — même pour un changement mineur, la chaîne complète est obligatoire
6. **En cas de doute, demander à l'utilisateur** — ne pas deviner les choix métier (Marine nationale). Si un agent signale une ambiguïté dans son résumé, relaie-la à l'utilisateur au lieu de trancher à sa place
7. **Consigner toute dette technique** — quand le Tech Lead ou le QA signale une dette ou un point hors périmètre, crée immédiatement une tâche Notion « À faire » qui la décrit, avec un renvoi vers la tâche d'origine
8. **Chercher le même défaut ailleurs** — quand un bug est corrigé à un endroit, vérifier par une recherche dans tout le projet qu'il n'existe pas ailleurs (ex. imports de bibliothèques optionnelles non protégés)

## Phases du projet (feuille de route Matrix 2.0 — cahier des charges §42)

| Phase | Objectif |
|-------|----------|
| Phase 0 — Assainissement | Sécurité, permissions, scoping, tests, audit, architecture |
| Phase 1 — Socle | Organisation (dont commandants adjoints, double équipage, rôles à terre), utilisateurs, permissions, configuration, notifications, recherche, audit |
| Phase 2 — Vie quotidienne | Mon espace, calendrier, tâches, quarts, services, chefs de liste, échanges |
| Phase 3 — Communication | Discussions, annonces, conversations contextuelles, notifications |
| Phase 4 — Opérationnel | Équipements, catalogue de matériel, fiches de maintenance, comptes rendus, anomalies, rondes, logistique |
| Phase 5 — Connaissance | Documentation, formations, qualifications, RETEX |
| Phase 6 — Pilotage | Tableaux de bord par niveau, indicateurs, rapports, vue SSF |
| Phase 7 — Écosystème | Synchronisation bâtiment ↔ terre, API (dont SSF), interopérabilité, déploiement multi-bâtiments |

Dans la base Notion, les étiquettes à utiliser sont exactement : `Phase 0 - Assainissement`, `Phase 1 - Socle`, `Phase 2 - Vie Quotidienne`, `Phase 3 - Communication`, `Phase 4 - Opérationnel`, `Phase 5 - Connaissance`, `Phase 6 - Pilotage`, `Phase 7 - Écosystème`. Les anciennes étiquettes (« Phase 1 - Fondation », « Phase 2 - Calendrier Central », « Phase 3 - Maintenance Préventive », « Phase 4 - Maintenance Corrective », « Phase 5 - Formation », « Phase 6 - Matériel ») correspondent à l'ancien découpage et ne restent que sur les tâches terminées : ne jamais les utiliser pour une nouvelle tâche.
