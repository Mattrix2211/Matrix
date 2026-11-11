# Chapitre 15 (technique) — Documentation et RETEX : mécanismes

> **Diffusion restreinte.** Complète `diffusable/15_documentation_retex.md` (à lire d'abord). **État décrit :** état B (`6d6d0be`), non fusionné dans `main`. Légende : 🟢 réel vérifié, 🔵 cible validée par le PO, ⚪ non vérifié.
> **Pour qui :** développeurs, administrateurs. **Ce que vous y trouverez :** les références de code, les droits et les points non vérifiés du chapitre.

---

| Objet | Référence |
|---|---|
| Document | `documentation/models.py` `Document` (:15) |
| Version | `documentation/models.py` `VersionDocument` (:48) ; états BROUILLON, SOUMISE, PUBLIEE, REFUSEE, OBSOLETE |
| Lien objet ↔ document | `documentation/models.py` `LienDocument` (:77) |
| Droits | `documentation/services.py` `peut_rediger` (:38), `peut_valider` (:46) ; seuils `documentation_redaction` (chef de section), `documentation_validation` (chef de service) dans `matrix/core/role_thresholds.py` |
| Cycle | `documentation/services.py` `creer_document` (:114), `soumettre` (:136), `proposer_amelioration` (:149), `valider` (:169), `refuser` (:189), `archiver` (:207) |
| Domaine RETEX | `retex/models.py` `DomaineRetex` (:15) |
| RETEX | `retex/models.py` `Retex` (:31) ; états PROPOSE, VALIDE, REFUSE, CLOS |
| Routage | `retex/services.py` `valideurs` (:54) |
| Actions | `retex/services.py` `creer_action` (:167) |
| Clôture | `retex/services.py` `clore` (:185) |
| Publication | `retex/services.py` `_publier` : crée un `Document` + `VersionDocument` n° 1 publiée |

Seuil `retex_validation` : `matrix/core/role_thresholds.py`, portée navire, chef de service.

Schémas : S29, S30, S31. Décisions : `DEC-RTX-01` à `04`.

Écart : circuit RETEX unique-étape (code) vs circuit hiérarchique `DEC-RTX-01` ; pas de demande de correction (`DEC-RTX-02/03`) ; pas de transmission à l'organisme.

## Tests

🟢 documentation/tests/ (9 fonctions de test), retex/tests/ (5 fonctions) — couverture faible.

## Limites

- ⚪ Couverture de tests faible pour ces deux paquets : les règles décrites viennent surtout de la lecture du code.
- ⚪ Circuit RETEX en une étape (A15) ; pas de transmission à l'organisme (A16).

---

**Sources (état B).** Références en ligne ; `restreint/ECARTS_DECISIONS_CODE.md` (A15, A16).
