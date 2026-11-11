# Chapitre 14 (technique) — Formations : mécanismes

> **Diffusion restreinte.** Complète `diffusable/14_formations.md` (à lire d'abord). **État décrit :** état B (`6d6d0be`), non fusionné dans `main`. Légende : 🟢 réel vérifié, 🔵 cible validée par le PO, ⚪ non vérifié.
> **Pour qui :** développeurs, administrateurs. **Ce que vous y trouverez :** les références de code, les droits et les points non vérifiés du chapitre.

---

| Objet | Référence |
|---|---|
| Formation (fiche unique, circuit C) | `training/models.py` `TrainingCourse` (:19) ; `statut_validation` (:78) |
| Référent d'une formation / du navire | `training/models.py` `ReferentFormation` (:100), `ReferentFormationNavire` (:124) |
| Exigence | `training/models.py` `TrainingRequirement` (:335) |
| Session, liste d'attente | `training/models.py` `TrainingSession` (:353), `TrainingWaitlistEntry` (:416) |
| Circuit A | `training/models.py` `DemandePlace` (:556), `PlaceAffectee` (:611) ; attribution `training/web_views.py` `_attribuer_places` (:1311) |
| Circuit B | `training/models.py` `PersonnelBRH` (:631), `CandidatureFormation` (:654) |
| Validation (qualification) | `training/models.py` `TrainingRecord` (:719) |
| Droit de valider | `training/models.py` `peut_valider_formation` (:210) |
| Seuil demande de places | `training/web_views.py` `_peut_demander_places` (:136) |
| Validation hiérarchie candidature | `training/web_views.py` `_peut_valider_candidature_hierarchie` (:158) ; BRH `_peut_valider_candidature_brh` (:169) |
| Validation formation « bord » | `training/web_views.py` `peut_valider_proposition_bord` (:212) |
| Carte de compétences | `training/services.py` `calculer_carte_competences` (:50) |
| Alertes d'expiration | `notifications/tasks.py` `notify_expiring_training` (:26) |

Schéma : S28. Décisions : `DEC-QUA-01` à `04`, `DEC-ORG-04`, `DEC-ORG-05`.

Points à confirmer : organisme de formation non modélisé comme acteur ; transition automatique session → qualification absente.

## Tests

🟢 training/tests/ (310 fonctions).

## Limites

- ⚪ L'organisme de formation n'est pas modélisé comme acteur (A19).
- ⚪ Pas de transition automatique session → qualification.

---

**Sources (état B).** Références en ligne ; `restreint/ECARTS_DECISIONS_CODE.md` (A19).
