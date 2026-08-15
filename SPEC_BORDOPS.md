# BordOps — Plan d'amélioration basé sur l'analyse d'Atlas CMMS

> Document de travail pour Claude Code. Analyse comparative entre le projet Matrix/BordOps existant (github.com/Mattrix2211/Matrix) et Atlas CMMS (github.com/Grashjs/cmms), aboutissant à 4 chantiers concrets.

---

## 0. Contexte — à lire avant tout le reste

Le projet Matrix/BordOps **est déjà largement développé**, pas un projet à démarrer de zéro. Toutes les propositions ci-dessous sont des **ajouts/patches sur le code existant**, jamais des remplacements de modèles ou de systèmes déjà en place. Les conventions du projet sont dans `CLAUDE.md` à la racine du dépôt — le lire avant toute intervention.

### Ce qui existe déjà et qu'il ne faut PAS recréer

| Besoin | Déjà en place | Fichier |
|---|---|---|
| Rôles hiérarchiques | `Roles` (8 niveaux MASTER_ADMIN→EQUIPIER) + `RoleLevel` (comparaison numérique) | `accounts/models.py`, `matrix/core/roles.py` |
| Permissions par vue DRF | `RolePermission` (seuil `min_role_level_write` par ViewSet) | `matrix/core/permissions.py` |
| Filtrage par périmètre (scope) | `scope_filters_for_user()` — filtre par ship/service/sector/section selon le profil connecté | `matrix/core/scopes.py` |
| Notifications in-app | Modèle `Notification` générique (GenericForeignKey) + tâches Celery + commande de management | `notifications/models.py`, `notifications/tasks.py`, `notifications/management/commands/generate_installation_notifications.py` |
| Historique/traçabilité par installation | `InstallationEvent` (date, label, notes) — sert déjà d'audit trail pour ce qui touche une installation | `assets/models.py` |
| Relevés compteur (heures de marche) | `InstallationHourReading` — déjà présent, mais pas encore relié à un déclenchement automatique | `assets/models.py` |
| Maintenance calendaire | `InstallationMaintenance.periodicity` — actuellement un simple texte libre, pas structuré, pas de mode compteur | `assets/models.py` |
| Fonctionnement hors-ligne (LAN uniquement) | Déjà un principe non-négociable inscrit dans `CLAUDE.md` (§ Principes fondamentaux, point 4) | `CLAUDE.md` |
| Workflow correctif | `CorrectiveTicket` (10 états : REPORTED→DIAGNOSED→WAITING_PARTS→...→CLOSED) | `logistics/models.py` |
| Checklists avec surcharge par équipement | `ChecklistTemplate`/`ChecklistItemTemplate` + `AssetChecklistOverride` | `assets/models.py` |
| Champs personnalisés | `DynamicFieldDefinition` par secteur | `org/models.py` |

**Rappel important pour Claude Code :** ne jamais inventer un nouveau système de permissions, de scope, ou de notification en parallèle de ceux listés ci-dessus — toujours étendre l'existant.

---

## 1. Comparaison Matrix/BordOps vs Atlas CMMS

| Domaine | Atlas CMMS | Matrix/BordOps (existant) | Verdict |
|---|---|---|---|
| Hiérarchie organisationnelle | Company plate (multi-tenant SaaS) | Ship → Service → Sector → Section (4 niveaux, calqué sur l'organisation navale réelle) | **Matrix supérieur** |
| Rôles/permissions | `Role` + `PermissionEntity` (matrice CRUD par entité) | `RoleLevel` (8 niveaux numériques) + `RolePermission` DRF + scopes hiérarchiques | **Équivalent**, Matrix plus simple à maintenir |
| Équipements — hiérarchie parent/enfant | `Asset.parentAsset` (self-FK) — ex: Propulsion > Moteur bâbord > Turbo | **Absent** — ni `Installation` ni `Asset` n'ont de self-FK parent | **Gap réel → Priorité 2** (retenue pour les deux modèles) |
| Checklists | `Task`/`TaskType` (SUBTASK/NUMBER/TEXT/INSPECTION/MULTIPLE/METER) | `ChecklistTemplate` + `AssetChecklistOverride` (surcharge par équipement) | **Matrix supérieur** |
| Intervention corrective | `WorkOrder` + `Status` (4 états génériques) | `CorrectiveTicket` (10 états) | **Matrix supérieur** |
| Maintenance préventive — déclenchement | `PreventiveMaintenance`+`Schedule` (calendaire) et `WorkOrderMeterTrigger` (compteur), séparés | `MaintenancePlan` (calendaire, pour `Asset` mobile) et `InstallationMaintenance` (texte libre, pour `Installation` fixe) — **aucun mode compteur, aucune génération auto pour les installations** | **Gap réel → Priorité 1** |
| Pièces de rechange / stock | `Part` avec `quantity`+`minQuantity` (alerte de réappro proactive) | `PartRequest`/`PartLineItem` rattachés uniquement à un ticket correctif — pas de stock ni de seuil proactif | **Gap réel → Priorité 3** |
| Notifications | Aucune notification interne native (webhooks externes uniquement) | `Notification` in-app générique + Celery, déjà opérationnel | **Matrix supérieur** |
| Audit trail | Hibernate Envers (versioning automatique sur toutes les entités) | Logs dédiés (`InstallationEvent`, `TicketStatusLog`, `OccurrenceStatusLog`, `AuditLog`) — couvrent déjà les points sensibles | Atlas plus systématique, **mais pas un besoin urgent pour Matrix** |
| Offline / réseau | Pensé cloud/SaaS, dépendances internet multiples | Principe "fonctionne hors-ligne" déjà natif au projet | **Matrix supérieur** |

**Constat :** Matrix n'est pas un projet à rattraper — il est déjà plus abouti qu'Atlas sur plusieurs points pour ce cas d'usage naval précis. Seuls 4 chantiers valent la peine d'être lancés, détaillés ci-dessous.

---

## 2. Priorité 1 — Mode de déclenchement configurable sur `InstallationMaintenance`

**Le vrai trou :** `InstallationMaintenance.periodicity` n'est qu'un champ texte libre — pas de mode compteur, pas de génération automatique d'échéance. Chaque bord doit pouvoir choisir, équipement par équipement, si le suivi se fait au calendrier, au compteur (heures de marche), ou aux deux (le premier des deux critères atteint déclenche).

### 2.1 Champs à ajouter sur `InstallationMaintenance` (`assets/models.py`)

```python
class ModeDeclenchement(models.TextChoices):
    CALENDRIER = "CALENDRIER", "Calendaire"
    COMPTEUR = "COMPTEUR", "Compteur (heures de marche)"
    LES_DEUX = "LES_DEUX", "Le premier des deux"

class InstallationMaintenance(TimeStampedModel, OwnedModel):
    # ... champs existants inchangés (installation, title, description, planned_duration_min, people_count, competence, periodicity) ...

    mode_declenchement = models.CharField(
        max_length=16, choices=ModeDeclenchement.choices, default=ModeDeclenchement.CALENDRIER
    )

    # Branche calendaire — structurée, en plus du champ 'periodicity' texte existant (conservé pour affichage/rétrocompat)
    UNITE_CHOICES = (("J", "Jour(s)"), ("S", "Semaine(s)"), ("M", "Mois"), ("A", "Année(s)"))
    intervalle = models.PositiveIntegerField(null=True, blank=True)          # ex: 3
    unite_intervalle = models.CharField(max_length=1, choices=UNITE_CHOICES, null=True, blank=True)  # "M" + intervalle=3 -> trimestriel

    # Branche compteur — s'appuie sur InstallationHourReading déjà existant, pas de nouveau modèle Compteur nécessaire
    seuil_heures = models.PositiveIntegerField(null=True, blank=True)        # ex: toutes les 250h
    derniere_echeance_heures = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # dernier seuil déclenché
```
Une seule migration (`makemigrations assets`), rétrocompatible : `periodicity` reste affiché tel quel pour les enregistrements existants, `mode_declenchement` par défaut `CALENDRIER` ne casse rien.

### 2.2 Modification du mode après création

Le choix se fait à la création de la fiche, mais reste modifiable. Traçabilité via `InstallationEvent` (déjà existant — pas de nouveau système d'audit) :

```python
def changer_mode_declenchement(maintenance: InstallationMaintenance, nouveau_mode, utilisateur):
    ancien_mode = maintenance.get_mode_declenchement_display()
    maintenance.mode_declenchement = nouveau_mode
    maintenance.save()
    InstallationEvent.objects.create(
        installation=maintenance.installation,
        label="Changement mode de suivi maintenance",
        notes=f"{maintenance.title} : {ancien_mode} → {maintenance.get_mode_declenchement_display()} (par {utilisateur})",
        created_by=utilisateur,
    )
```

### 2.3 Restriction d'accès — réutiliser `RolePermission` existant

```python
class InstallationMaintenanceViewSet(...):
    min_role_level_write = RoleLevel.CHEF_SERVICE  # seuls CHEF_SERVICE et au-dessus peuvent modifier le mode
```
**Décidé :** seuil fixé à `CHEF_SERVICE`. Ce même seuil sera réutilisé pour la modification du rattachement parent/enfant des équipements (Priorité 2), par cohérence.

**⚠️ Point de vigilance signalé lors de la revue d'installation (Claude Code) :** `matrix/core/roles.py` ne définit actuellement que 6 valeurs dans `RoleLevel` (EQUIPIER, CHEF_SECTION, CHEF_SECTEUR, CHEF_SERVICE, COMMANDANT, MASTER_ADMIN) et son dict `ROLE_TO_LEVEL` omet `ETAT_MAJOR`, qui retombe silencieusement au niveau `EQUIPIER`. Avant d'implémenter tout seuil `min_role_level_write` basé sur `RoleLevel`, vérifier ce mapping avec l'utilisateur — sinon un `ETAT_MAJOR` (rôle pourtant supérieur à `CHEF_SERVICE` dans la hiérarchie métier) n'aura pas les droits d'écriture attendus.

### 2.4 Génération des échéances + notifications

Nouvelle commande suivant exactement le même schéma que `generate_installation_notifications.py` (déjà en place pour vibration/isolement), étendue à `InstallationMaintenance` :
- Branche calendaire : calcule la prochaine échéance depuis la dernière réalisation (via `InstallationEvent`) ou la date de création, selon `intervalle`/`unite_intervalle`
- Branche compteur : compare le dernier relevé `InstallationHourReading` à `derniere_echeance_heures + seuil_heures`
- Dans les deux cas, crée une `Notification` in-app selon le pattern déjà existant — aucune notification push/email, uniquement interne à l'app, cohérent avec la contrainte LAN-only

---

## 3. Priorité 2 — Hiérarchie parent/enfant sur les équipements

Aujourd'hui `Installation` et `Asset` sont des fiches "à plat" : impossible de représenter qu'un turbo appartient à un moteur bâbord qui appartient au groupe propulsion. **Décidé : la hiérarchie s'applique aux deux modèles**, `Installation` (fixe) et `Asset` (matériel mobile).

```python
class Installation(TimeStampedModel, OwnedModel):
    # ... champs existants ...
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="sous_ensembles")

class Asset(TimeStampedModel, OwnedModel):
    # ... champs existants ...
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="sous_ensembles")
```

**Règle de saisie et de modification — décidée pour `Installation`, à appliquer de la même façon à `Asset` par cohérence :**
- Le rattachement parent se choisit **à la création** de la fiche (champ optionnel dans le formulaire de création)
- Il reste **modifiable ensuite**, depuis les paramètres de l'installation/de l'actif
- La modification est réservée à la **personne détenant les droits** — même seuil que pour le mode de déclenchement (Priorité 1) : `min_role_level_write = RoleLevel.CHEF_SERVICE`, par cohérence avec le reste du projet plutôt qu'un nouveau seuil dédié

**Bénéfice concret :** un signalement ou une panne sur un sous-ensemble peut remonter visuellement au niveau du groupe parent (ex: "turbo HS" signale aussi que "Propulsion bâbord" est concerné) — utile pour évaluer l'impact opérationnel d'une panne.

---

## 4. Priorité 3 — Stock proactif sur les pièces de rechange

Aujourd'hui `PartLineItem` n'existe que rattaché à un `CorrectiveTicket` — la logistique est purement réactive (on commande une pièce seulement quand un ticket la demande déjà). Il manque un inventaire de stock bord avec seuil d'alerte, indépendant de tout ticket.

**Décidé : le stock doit être scopé par secteur ET par section**, pas seulement par navire. Pour rester cohérent avec `scope_filters_for_user` (qui filtre en cascade ship→service→sector→section selon le profil connecté), on reprend exactement le même quadruplet de champs que `Installation`/`Asset` plutôt qu'un scoping partiel ad hoc :

```python
class StockPiece(TimeStampedModel, OwnedModel):
    reference = models.CharField(max_length=255)
    designation = models.CharField(max_length=255)
    quantite = models.PositiveIntegerField(default=0)
    quantite_minimale = models.PositiveIntegerField(default=0)
    emplacement = models.CharField(max_length=255, blank=True, default="")
    ship = models.ForeignKey(Ship, on_delete=models.PROTECT, related_name="stock_pieces")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="stock_pieces")
    sector = models.ForeignKey(Sector, on_delete=models.PROTECT, related_name="stock_pieces")
    section = models.ForeignKey(Section, null=True, blank=True, on_delete=models.SET_NULL, related_name="stock_pieces")
```
`section` reste optionnel (comme sur `Installation`/`Asset`) — une pièce peut être gérée au niveau secteur sans être rattachée à une section précise, mais doit toujours être rattachée à un secteur pour que le filtrage par périmètre fonctionne correctement à tous les niveaux de la hiérarchie.

Une tâche Celery quotidienne (même pattern que l'existant) compare `quantite` à `quantite_minimale` et crée une `Notification` in-app pour le chef de service/secteur/section concerné dès qu'un seuil est franchi — évite de découvrir une rupture de stock au moment où une pièce est déjà nécessaire d'urgence.

---

## 5. Priorité 4 — Bilan PDF à la demande (rapport de synthèse pour la hiérarchie)

**Besoin :** un chef de secteur/section doit pouvoir générer en un clic un document présentable à sa hiérarchie, compilant l'état de son périmètre. **Deux modes distincts**, car "l'état actuel" et "l'activité sur une période" ne répondent pas à la même question :

- **Mode Instantané** (par défaut, aucune date à saisir) : photo de l'état du périmètre au moment de la génération
- **Mode Période** (date début / date fin) : bilan de l'activité réalisée sur la fenêtre choisie, avec des taux de conformité que le mode instantané ne peut pas montrer

### 5.1 Contenu — Mode Instantané
(scoping via `scope_filters_for_user` existant)
- État des installations du périmètre : statut actuel, dernière visite réalisée, dernier relevé (heures/vibration/isolement)
- Échéances à venir : prochaines maintenances calendaires et compteur (Priorité 1), triées par urgence, retards mis en évidence
- Tickets correctifs actuellement ouverts, avec statut et ancienneté
- Stock de pièces actuellement sous seuil (Priorité 3)
- Qualifications proches d'expiration (`training`)

### 5.2 Contenu — Mode Période
- **Taux de conformité maintenance** : maintenances planifiées vs réellement réalisées à temps sur la fenêtre (ex: "18/20 réalisées ce trimestre, 90%")
- **Tickets correctifs** : nombre ouverts/fermés sur la période, délai moyen de résolution, tickets encore ouverts en fin de période
- **Relevés effectués** : nombre et valeurs des relevés heures/vibration/isolement pris durant la fenêtre (preuve que le suivi a bien été fait, pas juste le dernier chiffre)
- **Consommation de pièces** : `PartLineItem` passées en statut `CONSUMED` sur la période
- **Qualifications obtenues/expirées sur la période** (`training`)

### 5.3 Implémentation — un seul service, deux modes

```python
# reports/services.py
def generer_bilan(scope_type: str, scope_id, utilisateur, date_debut=None, date_fin=None) -> bytes:
    """
    mode INSTANTANE si date_debut/date_fin absents, mode PERIODE sinon.
    Réutilise scope_filters_for_user + RoleLevel existants — pas de nouveau système de permission.
    """
    mode = "PERIODE" if (date_debut and date_fin) else "INSTANTANE"
    filtre_scope = ...  # via scope_filters_for_user, restreint au périmètre demandé

    if mode == "INSTANTANE":
        contexte = {
            "installations": Installation.objects.filter(**filtre_scope).select_related(...),
            "echeances": ...,  # prochaines maintenances, triées par urgence
            "tickets_ouverts": CorrectiveTicket.objects.filter(**filtre_scope).exclude(status__in=["CLOSED", "CANCELLED"]),
            "stock_alerte": StockPiece.objects.filter(**filtre_scope, quantite__lt=F("quantite_minimale")),
        }
    else:
        contexte = {
            "maintenances_planifiees": ...,  # échéances tombant dans [date_debut, date_fin]
            "maintenances_realisees": ...,   # InstallationEvent liés, filtrés par date dans la fenêtre
            "taux_conformite": maintenances_realisees_a_temps / maintenances_planifiees if maintenances_planifiees else None,
            "tickets_ouverts_periode": CorrectiveTicket.objects.filter(**filtre_scope, reported_at__range=(date_debut, date_fin)),
            "tickets_fermes_periode": CorrectiveTicket.objects.filter(**filtre_scope, status="CLOSED", updated_at__range=(date_debut, date_fin)),
            "delai_moyen_resolution": ...,
            "releves_periode": {
                "heures": InstallationHourReading.objects.filter(installation__in=..., date__range=(date_debut, date_fin)),
                "vibration": InstallationVibrationReading.objects.filter(..., date__range=(date_debut, date_fin)),
                "isolement": InstallationIsolationReading.objects.filter(..., date__range=(date_debut, date_fin)),
            },
            "pieces_consommees": PartLineItem.objects.filter(..., status="CONSUMED", received_at__range=(date_debut, date_fin)),
        }

    contexte.update({
        "mode": mode, "date_debut": date_debut, "date_fin": date_fin,
        "genere_par": utilisateur, "genere_le": timezone.now(),
    })
    template = "reports/bilan_instantane.html" if mode == "INSTANTANE" else "reports/bilan_periode.html"
    html = render_to_string(template, contexte)
    return weasyprint.HTML(string=html).write_pdf()
```

**Interface :** sur la page de tableau de bord du secteur/section, un bouton "Générer le bilan" avec un sélecteur de date optionnel — par défaut sans date (mode instantané), avec des raccourcis si une date est choisie ("Ce mois-ci", "Ce trimestre", "Cette année", ou plage personnalisée).

**Pourquoi WeasyPrint plutôt qu'une lib JS de génération PDF côté navigateur :** génération côté serveur Django à partir d'un template HTML classique — zéro dépendance internet au moment de la génération, cohérent avec la contrainte LAN-only. Une solution JS nécessiterait souvent des polices/scripts chargés depuis un CDN, ce qui casserait le fonctionnement hors-ligne.

---

## 6. Non retenu / pas prioritaire pour l'instant

- **Audit trail générique (django-simple-history)** : Atlas est plus systématique via Hibernate Envers, mais les points sensibles de Matrix sont déjà couverts par des logs dédiés (`InstallationEvent`, `TicketStatusLog`, `OccurrenceStatusLog`, `AuditLog`). Ajouter un système générique en plus créerait de la redondance sans bénéfice immédiat.
- **Unification `MaintenancePlan`/`InstallationMaintenance` en un seul modèle** (comme Atlas unifie via `WorkOrderBase`) : refactor plus lourd pour un gain surtout esthétique côté code — à envisager seulement si la duplication devient un vrai problème de maintenance.

---

## 7. Décisions validées — prêt pour Claude Code

1. **Priorité 1, seuil de permission :** `CHEF_SERVICE` peut modifier le `mode_declenchement` d'une `InstallationMaintenance`.
2. **Priorité 2, périmètre :** la hiérarchie parent/enfant s'applique à `Installation` **et** `Asset`. Choix à la création, modifiable ensuite dans les paramètres de la fiche, réservé à `CHEF_SERVICE` (même seuil que la Priorité 1, pour cohérence).
3. **Priorité 3, scoping du stock :** `StockPiece` scopé par secteur et section (en plus de navire/service), en reprenant le même quadruplet `ship`/`service`/`sector`/`section` que `Installation`/`Asset`.
4. **Ordre de traitement :** Priorité 1 (le vrai trou fonctionnel) → Priorité 4 (rapide à livrer une fois 1 et 3 en place, forte valeur de présentation) → Priorité 3 → Priorité 2 (la moins urgente, plutôt un confort de visualisation).

Ce document est prêt à être transmis à Claude Code pour lancer la boucle d'agents (PO→Dev→Tech Lead→QA) sur ces 4 chantiers, dans l'ordre indiqué.

---

## 8. Note de revue d'installation (à ne pas ignorer)

Ajouté lors de l'installation de ce document dans le dépôt (vérification factuelle contre le code réel) : **`matrix/core/roles.py` a un bug de mapping des rôles**, indépendant des 4 priorités ci-dessus mais qui les affecte directement puisque les Priorités 1 et 2 fixent leur seuil de permission via `RoleLevel.CHEF_SERVICE`.

- `RoleLevel` ne contient que 6 valeurs (`EQUIPIER, CHEF_SECTION, CHEF_SECTEUR, CHEF_SERVICE, COMMANDANT, MASTER_ADMIN`) alors que `Roles` (accounts/models.py) en a 8.
- Le dict `ROLE_TO_LEVEL` **omet `ETAT_MAJOR`**, qui retombe silencieusement sur `RoleLevel.EQUIPIER` (le niveau le plus bas) au lieu d'un niveau cohérent avec sa place dans la hiérarchie (`ADMIN_NAVIRE → COMMANDANT → ETAT_MAJOR → CHEF_SERVICE`).
- `ADMIN_NAVIRE` n'a pas non plus de niveau propre et collapse sur le même niveau que `CHEF_SERVICE`.

**Conséquence concrète :** un utilisateur `ETAT_MAJOR`, pourtant hiérarchiquement au-dessus de `CHEF_SERVICE`, ne passera pas le test `min_role_level_write = RoleLevel.CHEF_SERVICE` proposé en Priorité 1/2 — il sera traité comme un simple équipier.

**Recommandation :** avant de commencer la Priorité 1, faire trancher par l'utilisateur (choix métier Marine Nationale, pas à deviner) comment `RoleLevel` doit représenter les 8 rôles de `Roles`, puis corriger `matrix/core/roles.py` en une tâche dédiée (Phase 1, priorité Haute) avant ou en même temps que la Priorité 1 de ce document.
