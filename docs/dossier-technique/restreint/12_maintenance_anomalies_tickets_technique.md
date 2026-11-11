# Chapitre 12 (technique) — Maintenance, anomalies, tickets : mécanismes

> **Diffusion restreinte.** Complète `diffusable/12_maintenance_anomalies_tickets.md` (à lire d'abord). **État décrit :** état B (`6d6d0be`), non fusionné dans `main`. Légende : 🟢 réel vérifié, 🔵 cible validée par le PO, ⚪ non vérifié.
> **Pour qui :** développeurs, administrateurs. **Ce que vous y trouverez :** les références de code, les droits et les points non vérifiés du chapitre.

---

## 12.T1 Modèles

| Objet | Référence |
|---|---|
| Plan de maintenance | `maintenance/models.py` `MaintenancePlan` (:18) |
| Occurrence (statuts PLANNED…CANCELLED, contrainte XOR matériel / installation) | `maintenance/models.py` `MaintenanceOccurrence` (:36) |
| Journal d'états | `maintenance/models.py` `OccurrenceStatusLog` (:103) |
| Exécution (compte rendu) | `maintenance/models.py` `MaintenanceExecution` (:110) |
| Modification de compte rendu | `maintenance/models.py` `ModificationCompteRendu` (:146) |
| Compte rendu correctif | `maintenance/models.py` `CompteRenduCorrectif` (:164) |
| Ticket correctif | `logistics/models.py` `CorrectiveTicket` (:23) ; `STATUTS_TICKET_OUVERTS` (:19) |
| Anomalie | `logistics/models.py` `Anomalie` (:317) |
| Demande / ligne de pièce | `logistics/models.py` `PartRequest` (:97), `PartLineItem` (:107) |

## 12.T2 Logique

- **Exécution** : `maintenance/web_views.py` `OccurrenceExecuteView` (:72) ; `post` (:150) ; écriture sous verrou `_ecrire` (:248) ; statut final `DONE` ou `WAITING_VALIDATION` selon `NON_CONFORME` (:283) ; confirmation d'installation critique (:193) ; conflit d'écriture simultanée (`_Conflit`).
- **Ticket automatique** : signal `create_corrective_on_non_conform` (`maintenance/models.py:213`), matériel mobile seulement.
- **Génération et retard** : `maintenance/tasks.py` `generate_occurrences` (:66), `generate_installation_occurrences` (:89), `compute_overdue` (:83).
- **Tournée** : `maintenance/tournee.py` (tableau par catégorie), saisie `maintenance/tournee_web.py`.
- **Ticket** : `logistics/web_views.py` `ACTION_SUIVANTE_TICKET` (:153), `TicketTransitionView` (:368) — seuil `CHEF_SECTION`, périmètre `perimetre_tickets_q`, REX obligatoire à la clôture, confirmation `remise_en_service`.
- **Anomalie** : `logistics/anomalie_views.py` `_est_chef` (:35), `_peut_traiter` (:39), `AnomalieCreateView` (:141), `AnomalieConvertirView` (:341).
- **Confirmations** : `matrix/core/confirmations.py` (`maintenance_critique`, `remise_en_service`).

## 12.T2 bis Modèles secondaires

| Modèle | Référence | Rôle |
|---|---|---|
| `TicketStatusLog` | `logistics/models.py:90` | Historique des états d'un ticket |
| `AnomalieStatutLog` | `logistics/models.py:401` | Historique des états d'une anomalie |
| `RondeModele` | `rondes/models.py:22` | Modèle de ronde ; module **retiré de l'interface** (aucune vue) |
| `PointControle` | `rondes/models.py:75` | Point de contrôle d'une ronde |
| `Ronde` | `rondes/models.py:102` | Exécution datée d'un modèle |
| `ResultatPoint` | `rondes/models.py:143` | Résultat d'un point de contrôle |

## 12.T3 Schémas

S24 (plan → réalisation), S25 (états), S26 (ticket et anomalie).

## 12.T4 Points non vérifiés

- Sortie de `WAITING_VALIDATION` : écrite par `maintenance/web_views.py:283` (clôture ou correction), `maintenance/views.py:167` (action `complete` de l'API) ; `maintenance/tournee_web.py:195` (tournée) ; exclue des retards par `maintenance/perimetre.py:18` ; verrouillée en tournée (`maintenance/tournee.py:19`) ; aucune action de validation dédiée ni lien ticket → occurrence. Seule sortie : correction du compte rendu (seuil `maintenance_compte_rendu_correction`, chef de secteur), avec conformité finale autre que non conforme.
- Module `rondes` : modèles seuls (`rondes/models.py`), module retiré de l'interface (`matrix/tests/test_module_rondes_retire.py`).

## Tests

🟢 maintenance/tests/ (178 fonctions), logistics/tests/ (228 fonctions, partagées avec le chapitre 13).

## Limites

- Sortie de l'état En validation : correction du compte rendu seulement ; risque de blocage sans alerte (A20).
- ⚪ Les envois de notifications ne sont pas rejoués.

---

**Sources (état B).** Références en ligne ; `restreint/ECARTS_DECISIONS_CODE.md` (A20).
