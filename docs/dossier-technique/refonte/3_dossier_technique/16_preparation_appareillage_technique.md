<!-- couvre: restreint/16_preparation_appareillage_technique.md | Chapitre 16 (technique) — Préparation à l'appareillage : mécanismes -->
<!-- couvre: restreint/16_preparation_appareillage_technique.md | Tests -->
<!-- couvre: restreint/16_preparation_appareillage_technique.md | Limites -->
<!-- partie: Modules -->
# Préparation à l'appareillage : mécanismes

<div class="ligne-public"><b>Public :</b> développeurs, administrateurs · <b>Ce que vous y trouverez :</b> les références de code, les droits et les points non vérifiés du chapitre</div>

| Objet | Référence |
|---|---|
| Session | `dashboard/models.py` `SessionAppareillage` (:18) — `valide_par`, `date_validation`, `cloturee_le` |
| Point | `dashboard/models.py` `ItemAppareillage` (:77) — catégories OCCURRENCE, RELEVE, DERIVE, STOCK |
| Calcul des points | `dashboard/web_views.py` `_points_de_vigilance_navire` (:367) |
| Page | `dashboard/web_views.py` `PretAppareillageView` (:531) |
| Signature | `dashboard/web_views.py` `SessionAppareillageSignerView` (:664) — seuil `CHEF_SECTEUR`, `confirmation_web`, `AuditLog` |
| Accès | `dashboard/templatetags/dashboard_extras.py` `peut_voir_pret_appareillage` (:25) |
| Confirmation | `matrix/core/confirmations.py` (`pret_appareillage`) |

Schémas : S32, S33. Décisions : `DEC-APP-01`, `DEC-APP-02`, `DEC-APP-03`, `DEC-APP-04`, `DEC-APP-05`, `DEC-APP-06`, `DEC-APP-07`, `DEC-APP-08`, `DEC-APP-09`, `DEC-APP-10`, `DEC-APP-11`, `DEC-APP-12`, `DEC-APP-13`, `DEC-APP-14`.

Écart : une seule signature (`valide_par`) et pas de fiche de référence, contre `DEC-APP-02` / `DEC-APP-14` (L23). L'unicité de la session ouverte par navire est un contrôle applicatif, sans contrainte base.

## Tests

🟢 dashboard/tests/ (261 fonctions, partagées avec le [[DT:06_accueil_pilotage_technique]]).

## Limites

- ⚪ Aucune fiche de référence d'appareillage dans le code (A17).
- ⚪ L'affichage de la précision « la signature n'atteste pas l'aptitude » n'a pas été vérifié à l'écran.

**Sources (état B).** Références en ligne ; `restreint/ECARTS_DECISIONS_CODE.md` (A17).
