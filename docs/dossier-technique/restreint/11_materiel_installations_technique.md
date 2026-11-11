# Chapitre 11 (technique) — Matériel et installations : mécanismes

> **Diffusion restreinte.** Complète `diffusable/11_materiel_installations.md` (à lire d'abord). **État décrit :** état B (`6d6d0be`), non fusionné dans `main`. Légende : 🟢 réel vérifié, 🔵 cible validée par le PO, ⚪ non vérifié.
> **Pour qui :** développeurs, administrateurs. **Ce que vous y trouverez :** les références de code, les droits et les points non vérifiés du chapitre.

---

## 11.T1 Modèles principaux

| Objet | Référence | Remarque |
|---|---|---|
| Matériel mobile | `assets/models.py` `Asset` (:247) | rattachement bâtiment / service / secteur / section ; parent sans cycle |
| Installation fixe | `assets/models.py` `Installation` (:356) | critique ou non ; relevés heures, vibration, isolement |
| Type de matériel | `assets/models.py` `AssetType` (:80) | porte les plans de maintenance de sa catégorie |
| Mode de déclenchement | `assets/models.py` `ModeDeclenchement` (:91) | calendaire / compteur |
| Modèle de checklist | `assets/models.py` `ChecklistTemplate` (:104) | gamme de la fiche |
| Entretien d'installation | `assets/models.py` `InstallationMaintenance` (:582) | tâches d'entretien |
| Catalogue | `assets/models.py` `CategorieCatalogue` (:695), `ArticleCatalogue` (:728), `PropositionArticle` (:773) | commun à la flotte |
| Signalement de fiche | `assets/models.py` `SignalementFiche` (:849) | ouvert jusqu'à nouvelle version |

## 11.T2 Circuits de validation

- Fiches : `assets/fiche_validation.py` — `circuit` (:63) construit la liste d'étapes selon le type (installation bord / matériel flotte) ; `etape_suivante` (:77) calcule la suite ; auto-validation et double intervention refusées.
- Propositions d'article : `assets/proposition_article.py` — `ETAPES` (:26), `circuit` (:42), `peut_proposer` (:70).
- Gestion du catalogue : `assets/permissions.py` `peut_gerer_catalogue` (:7).
- Poste COMA vacant : visa en attente, sans suppléance par le grade (voir ch. 5, `DEC-SUP-01` pour le principe de suppléance explicite).

## 11.T2 bis Modèles secondaires

| Modèle | Référence | Rôle |
|---|---|---|
| `InstallationBigrameChoice` | `assets/models.py:32` | Liste réglable des bigrammes d'installation |
| `Location` | `assets/models.py:39` | Local d'un équipement |
| `Deck` | `assets/models.py:50` | Pont du navire, support du plan |
| `ChecklistItemTemplate` | `assets/models.py:187` | Ligne d'une gamme (contrôle ou relevé) |
| `FichePreparation` | `assets/models.py:211` | Préparation de la fiche (outils, pièces, EPI, consignes) |
| `FicheEtape` | `assets/models.py:231` | Étape numérotée d'une fiche |
| `AssetChecklistOverride` | `assets/models.py:241` | Adaptation de gamme propre à un matériel |
| `AssetDocument` | `assets/models.py:350` | Document joint à un matériel |
| `DocumentInstallation` | `assets/models.py:419` | Document de référence d'une installation |
| `AssetFolder` | `assets/models.py:446` | Dossier (parent / enfants) de classement |
| `InstallationEvent` | `assets/models.py:458` | Événement ou modification technique d'une installation |
| `InstallationEventAttachment` | `assets/models.py:475` | Pièce jointe d'un événement |
| `InstallationPart` | `assets/models.py:493` | Pièce d'une installation (distincte du stock) |
| `InstallationIsolationReading` | `assets/models.py:508` | Relevé d'isolement |
| `InstallationHourReading` | `assets/models.py:525` | Relevé d'heures de marche |
| `InstallationVibrationReading` | `assets/models.py:542` | Relevé de vibration |
| `InstallationExtraField` | `assets/models.py:568` | Champ supplémentaire d'une installation |
| `InstallationMaintenanceAttachment` | `assets/models.py:666` | Pièce jointe d'un entretien |
| `ChefResponsableSpecialite` | `assets/models.py:755` | Chef désigné d'un responsable de spécialité : il vise la proposition après sa vérification |
| `EvenementProposition` | `assets/models.py:819` | Historique de chaque transition d'une proposition ou d'une version de fiche |

## 11.T3 Schémas

S22 (équiper depuis le catalogue), S23 (circuits des fiches), voir `schemas/src/`.

## 11.T4 Écarts et points à confirmer

- Transfert de matériel entre secteurs / services : `DEC-MAT-01` à `DEC-MAT-04`, lot L13, non développé (voir `ECARTS_DECISIONS_CODE.md`).
- Objets cibles du cahier (configuration réelle, états techniques fins) : non développés, non décrits comme existants.

## Tests

🟢 assets/tests/ (493 fonctions de test).

## Limites

- ⚪ Les écrans (plan du navire, grille, assistants de fiche) n'ont pas été rejoués dans un navigateur.
- ⚪ Aucun circuit de transfert de matériel n'existe (A18).

---

**Sources (état B).** Références en ligne ; `restreint/ECARTS_DECISIONS_CODE.md` (A18).
