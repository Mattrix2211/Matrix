# Chapitre 16 (technique) — Préparation à l'appareillage : mécanismes

> **Diffusion restreinte.** Complète `diffusable/16_preparation_appareillage.md` (à lire d'abord). **État décrit :** état B (`6d6d0be`), non fusionné dans `main`. Légende : 🟢 réel vérifié, 🔵 cible validée par le PO, ⚪ non vérifié.
> **Pour qui :** développeurs, administrateurs. **Ce que vous y trouverez :** les références de code, les droits et les points non vérifiés du chapitre.

---

| Objet | Référence |
|---|---|
| Session | `dashboard/models.py` `SessionAppareillage` (:18) — `valide_par`, `date_validation`, `cloturee_le` |
| Point | `dashboard/models.py` `ItemAppareillage` (:77) — catégories OCCURRENCE, RELEVE, DERIVE, STOCK |
| Calcul des points | `dashboard/web_views.py` `_points_de_vigilance_navire` (:367) |
| Page | `dashboard/web_views.py` `PretAppareillageView` (:531) |
| Signature | `dashboard/web_views.py` `SessionAppareillageSignerView` (:664) — seuil `CHEF_SECTEUR`, `confirmation_web`, `AuditLog` |
| Accès | `dashboard/templatetags/dashboard_extras.py` `peut_voir_pret_appareillage` (:25) |
| Confirmation | `matrix/core/confirmations.py` (`pret_appareillage`) |

Schémas : S32, S33. Décisions : `DEC-APP-01` à `DEC-APP-14`.

Écart : une seule signature (`valide_par`) et pas de fiche de référence, contre `DEC-APP-02` / `DEC-APP-14` (L23). L'unicité de la session ouverte par navire est un contrôle applicatif, sans contrainte base.

## Tests

🟢 dashboard/tests/ (261 fonctions, partagées avec le chapitre 6).

## Limites

- ⚪ Aucune fiche de référence d'appareillage dans le code (A17).
- ⚪ L'affichage de la précision « la signature n'atteste pas l'aptitude » n'a pas été vérifié à l'écran.

---

**Sources (état B).** Références en ligne ; `restreint/ECARTS_DECISIONS_CODE.md` (A17).
