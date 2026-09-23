# MATRIX 2.0 — Plateforme numérique opérationnelle quotidienne du marin

> Cahier des charges fonctionnel et architectural — Version 2.0 (06/09/2026)
>
> Document de référence stratégique, complémentaire à `CLAUDE.md` (qui reste la référence absolue pour les règles non négociables au quotidien). Ce document décrit **où le projet va** ; `CLAUDE.md` décrit **comment on y travaille**. Toute décision d'architecture ou de nouveau module doit être confrontée à ce document avant d'être lancée en développement.
>
> `SPEC_BORDOPS.md` (patch-list tactique Atlas CMMS) est antérieur à ce document et partiellement déjà implémenté (hiérarchie parent/enfant, mapping des rôles) — à considérer comme historique/à revalider plutôt que comme backlog actif.

---

## 1. Vision

Matrix doit devenir l'application que les marins ouvrent chaque jour. Elle doit centraliser dans une seule plateforme les informations, activités, tâches, responsabilités, communications et ressources nécessaires à la vie quotidienne du marin et au fonctionnement du bâtiment.

**Matrix n'est pas une GMAO à laquelle on ajoute des fonctionnalités. La GMAO est un module de Matrix.**

Matrix doit couvrir : la vie quotidienne du marin, les quarts, les services à quai, les tâches, le planning, la maintenance, la logistique, la formation, la documentation, les anomalies, la communication, le suivi du personnel, la vie du bâtiment, le pilotage par les responsables.

## 2. Principe fondamental — les 5 questions

Chaque marin doit pouvoir répondre rapidement à :

1. **Où dois-je être ?** — planning, quart, service, formation, réunion
2. **Qu'est-ce que je dois faire ?** — tâches, rondes, maintenance, inspections
3. **Qu'est-ce que je dois savoir ?** — consignes, procédures, messages, documentation
4. **Avec qui dois-je travailler ?** — équipe, responsable, collègue, relève
5. **Qu'est-ce que je dois signaler ?** — anomalie, incident, problème matériel, événement

## 3. Une application modulaire, pas 40 menus

```
MATRIX
├── 🏠 ACCUEIL
├── 👤 MOI              (profil, tâches, formations, qualifications)
├── 📅 ACTIVITÉS        (calendrier, quarts, services, gardes, échanges)
├── 🔧 MATÉRIEL         (équipements, maintenance, anomalies, rondes)
├── 📦 LOGISTIQUE       (stocks, matériel, demandes, inventaires)
├── 📚 CONNAISSANCES    (documents, procédures, formations, RETEX)
├── 💬 COMMUNICATION    (discussions, annonces, notifications)
└── 📊 PILOTAGE         (personnel, activités, maintenance, logistique, indicateurs)
```

Les modules affichés dépendent du rôle, de la fonction, du niveau hiérarchique, du périmètre, des responsabilités et des modules activés pour le bâtiment. **Aucun utilisateur ne doit voir un module qui ne le concerne pas.**

## 4. Évolutivité — Matrix doit évoluer avec la Marine

Principe architectural obligatoire : une modification organisationnelle ou métier courante ne doit **jamais** nécessiter de modifier le code. Doivent être configurables par les utilisateurs autorisés : bâtiments, services, secteurs, sections, fonctions, responsabilités, types de tâches/services/gardes, workflows, checklists, formulaires, catégories, qualifications, documents, règles de planification.

## 5. Administration distribuée

Distinguer quatre notions :
- **Permission** — qu'est-ce que je peux faire ?
- **Périmètre** — sur quoi puis-je agir ?
- **Responsabilité** — qu'est-ce que je suis chargé de gérer ?
- **Configuration** — qu'est-ce que je peux adapter ?

Chaque niveau hiérarchique (chef de section → chef de secteur → chef de service → état-major) gère une portion croissante de ces quatre axes. L'administrateur technique gère la plateforme, pas le fonctionnement métier quotidien.

## 6. Module 👤 MOI

Tableau de bord quotidien personnel : programme du jour (rassemblement, service, maintenance, formation), tâches en retard/du jour, notifications.

## 7. Module 📅 ACTIVITÉS — cœur de Matrix

Regroupe calendrier, quarts, services, gardes, permanences, activités, échanges, absences, remplacements. **Tout alimente un calendrier unique** — le marin ne doit pas consulter cinq systèmes différents pour savoir où il doit être.

### 7.1 Gestion des quarts

Le chef de liste peut créer une liste, définir période/postes/horaires, affecter les marins, générer automatiquement les tours, modifier une affectation, gérer les indisponibilités, effectuer des remplacements, publier la liste. **Aucun rythme de quart ne doit être codé en dur** — le système doit gérer différents systèmes de quart selon le bâtiment.

### 7.2 Service à quai / gardes

Traité comme une activité spécifique et configurable (garde 24h, garde de nuit, permanence, service, poste particulier) — pas un cas particulier codé en dur des quarts.

### 7.3 Génération intelligente

Le moteur de planification prend en compte disponibilité, absences, permissions, formations, autres services, quarts, règles de rotation, historique récent, contraintes particulières — et **propose** une répartition que le chef de liste accepte, modifie ou refuse. Matrix ne doit jamais imposer aveuglément une affectation.

### 7.4 Échange de service

Workflow : marin A demande un échange → marin B accepte/refuse → si accepté, validation du chef de liste → si validé, les deux calendriers sont modifiés, les deux marins et le chef de liste sont notifiés, l'historique conserve l'échange. **Une modification ne doit jamais simplement écraser l'ancienne affectation.**

Le système doit détecter et expliquer (pas juste bloquer) les situations impossibles : conflit d'affectation, habilitation manquante, absence.

## 8. Communication — le dialogue est une fonction métier

La communication doit être **contextuelle**, attachée aux objets métier : une tâche, un équipement, une anomalie, une intervention, une formation, un événement, un document peuvent chacun porter leur propre fil de discussion (`threads`, déjà générique dans l'app existante — s'appuyer dessus, ne pas créer de système parallèle).

En complément, des espaces de communication de groupe (section/secteur/service/bâtiment/équipe/groupe temporaire) et des annonces à 3 niveaux de diffusion (information/important/critique), respectant les périmètres organisationnels.

## 9. Module 🔧 MATÉRIEL

Équipements (installations, sous-équipements, localisation), maintenance (préventive, corrective, contrôles, compteurs, échéances), anomalies (signalement → qualification → affectation → correction → validation), rondes (parcours, points de contrôle, checklist, mesures, photos).

## 10. Module 📦 LOGISTIQUE

Stocks, pièces, consommables, outillage, EPI, demandes, prêts, retours, inventaires.

## 11. Module 📚 CONNAISSANCES

Documentation (procédures, notices, plans, consignes, formulaires), formation (formations, qualifications, recyclages, échéances), RETEX (événements, analyses, actions, recommandations).

## 12. Module 📊 PILOTAGE

Vue adaptée par niveau : marin (moi) → chef de section (ma section) → chef de secteur (mon secteur) → chef de service (mon service) → état-major (mon bâtiment) → commandement (situation générale). **Même donnée, vue différente selon le rôle.**

## 13. Architecture réseau — non négociable

Matrix ne doit **jamais** communiquer directement avec Internet.

```
INTERNET ── X (aucun accès)
RÉSEAU INTRANET DÉFENSE
  ├── Infrastructure à terre
  └── Bâtiment → Serveur Matrix local → PC / tablette / mobile
```

Principe : **Internet n'existe pas.** Aucune API Internet obligatoire, aucune dépendance cloud, aucune télémétrie externe, aucun CDN, aucune police distante, aucun service SaaS nécessaire au fonctionnement, aucune remontée de données externe. Cohérent avec le principe fondamental n°4 déjà en place dans `CLAUDE.md` — ce document le renforce et le précise (distinction LAN-bâtiment vs infrastructure à terre).

### 13.1 Tolérance aux coupures

- Connexion au serveur local → fonctionnement normal
- Liaison bâtiment ↔ infrastructure à terre coupée → Matrix continue localement
- Réseau totalement indisponible → seules les fonctions hors-ligne prévues par l'architecture restent disponibles

Reconnexion : événements locaux → synchronisation → infrastructure à terre, avec gestion des conflits.

## 14. Sécurité, historisation, versioning

- Authentification, contrôle d'accès, segmentation, chiffrement adapté, journalisation, audit, gestion des sessions, contrôle des fichiers, sauvegardes
- Toute donnée importante doit pouvoir répondre à : qui, quand, sur quoi, dans quel contexte, quelle était la valeur précédente (personnel, planning, services, échanges, maintenance, documents, configuration, permissions, workflows)
- Toute configuration importante (ex. liste de service) doit être **versionnée** : le système doit savoir quelle version était active à une date donnée

## 15. Architecture technique

Backend Django/Python, API DRF, Frontend HTMX + JS ciblé, Base PostgreSQL, Async Celery+Redis — **stack déjà en place, pas de changement**, ce document cadre l'usage, pas la stack.

## 16. Principe « configuration > code »

**Règle à appliquer systématiquement, y compris par les agents dev/tech-lead/qa :** ne jamais coder en dur une règle susceptible d'évoluer selon le bâtiment, le service, la Marine ou l'organisation.

❌ « Les quarts sont toujours de 4 heures. » ❌ « Une garde dure toujours 24 heures. » ❌ « Chaque bâtiment possède 5 services. » ❌ « Le chef de secteur possède toujours tel droit. »

✅ Configuration → Règles → Moteur Matrix.

## 17. Principe « proposer → valider → publier »

Pour les modifications sensibles (listes de service, règles d'organisation) : Brouillon → Proposition → Validation → Publication → Version active. Un utilisateur peut avoir le droit de proposer sans avoir le droit de publier.

## 18. Permissions — RBAC + ABAC + Scope + Responsibility

Le système doit combiner rôle (RBAC), attributs (ABAC), périmètre (scope) et responsabilité assignée. Exemple : un chef de secteur propulsion peut gérer tâches + équipements + personnels + services, de son secteur — pas par un simple seuil de rôle global, mais par la combinaison rôle × périmètre × responsabilité assignée.

## 19. UX

Rapide, lisible, utilisable PC/tablette/mobile, utilisable avec peu de réseau, utilisable par un non-technicien. **Le marin ne doit jamais avoir besoin de connaître l'architecture interne de Matrix.**

- Recherche universelle unique (marin, équipement, tâche, service, document, anomalie, formation, événement, discussion)
- Notifications intelligentes et contextuelles, jamais génériques
- Principe de non-surcharge : jamais 150 informations simultanées — contexte, rôle, priorité, responsabilité et personnalisation filtrent ce qui est affiché

## 20. Les 7 principes non négociables de Matrix

1. 🧠 **Cohérent** — une fonctionnalité n'est jamais un silo
2. 🔄 **Évolutif** — la Marine évolue → Matrix évolue (configuration > code)
3. 👥 **Administration distribuée** — les responsables peuvent adapter leur environnement
4. 💬 **Le dialogue est une fonction métier** — communication intégrée aux activités, pas un canal séparé
5. 📅 **Le calendrier reflète la réalité du marin** — quarts + services + tâches + formations + activités = une seule vision
6. 📴 **Internet n'existe pas** — fonctionnement exclusif sur l'infrastructure réseau autorisée
7. 🧾 **Tout est traçable** — une information importante ne disparaît jamais sans laisser de trace

## 21. Règle de développement dérivée (pour les agents dev/tech-lead/qa)

Avant tout développement d'une fonctionnalité, identifier explicitement : quels objets métier sont concernés, quels utilisateurs/rôles/périmètres sont impactés, quel workflow complet est déclenché (pas seulement l'action demandée), quelles notifications doivent partir, quel audit/historique doit être conservé, quels modules existants sont concernés ou risquent d'être dupliqués.

Exemple donné : une fonctionnalité « demande de matériel » ne se limite pas à une table `DemandeMateriel` — elle implique la création de la demande, la notification du chef, la validation, la vérification du stock, l'attribution, le mouvement de stock, la notification du marin, l'historique, et potentiellement l'équipement concerné.

## 22. Roadmap de développement

```
Phase 0 — Assainissement   : sécurité, permissions, scoping, tests, audit, architecture
Phase 1 — Socle            : organisation, utilisateurs, permissions, configuration, notifications, recherche, audit
Phase 2 — Vie quotidienne  : Mon espace, calendrier, tâches, quarts, services, chefs de liste, échanges
Phase 3 — Communication    : discussions, annonces, conversations contextuelles, notifications
Phase 4 — Opérationnel     : équipements, maintenance, anomalies, rondes, logistique
Phase 5 — Connaissance     : documentation, formation, qualifications, RETEX
Phase 6 — Pilotage         : dashboards, KPI, rapports, commandement
Phase 7 — Écosystème       : synchronisation, API, interopérabilité, déploiement multi-bâtiments
```

**Note explicite de l'utilisateur :** la fonctionnalité chef de liste + quarts + services + échanges (Phase 2) est identifiée comme potentiellement décisive — c'est ce qui peut faire que le marin ouvre Matrix tous les matins même sans maintenance à effectuer. Priorité forte dès que le socle (Phase 0-1) est assez solide.

---

*Ce document remplace la vision précédente centrée GMAO. Les 11 modules Django actuels listés dans `CLAUDE.md` restent la base technique — ce document cadre comment ils doivent s'articuler et ce qui doit encore être construit autour (quarts, services, gardes, échanges, communication contextuelle, administration distribuée, configuration au lieu du code en dur).*
