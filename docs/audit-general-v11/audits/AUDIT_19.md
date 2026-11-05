# Audit 19 — Conformité Marine nationale (terminologie, hiérarchie, circuits)

**Statut : partiel.** Cet audit confronte le code aux décisions écrites dans Notion (13 sous-pages lues). Les sources publiques ne sont pas consultées par l'audit : les faits de doctrine ne sont pas vérifiés indépendamment et **aucune règle militaire n'est affirmée**.

| Point | Source | Constat dans le code | Verdict |
|---|---|---|---|
| Ne pas afficher « chef de groupement » ni « CAN » | Notion p.13 | aucune occurrence dans gabarits et vues | **Conforme** |
| COMA : sigles COMAEQ, COMOPS, COMANAV, COMAVIA | p.01, p.13 | fonctions portées par `UserProfile.fonction_coma` ; titulaire résolu par bâtiment et équipage | **Conforme** (structure) |
| COMA « générique » à bannir (décision du 02/11 selon la session précédente) | AVANCEMENT | aucune occurrence du mot isolé dans les gabarits ; résiste dans des commentaires et documents | **Conforme dans l'interface** |
| Visa COMA : jamais redirigé vers un grade ; poste vacant → attente (sauf feuille : commandant de l'équipage) | p.13 | visa COMAEQ rejoué : seul le titulaire ; vacance gérée | **Conforme** pour la feuille ; autres circuits non rejoués |
| Visa « chef de secteur/service » par supérieur ou administrateur | p.13 (« aucun grade ne remplace… ») | permis par niveau | **Non conforme à l'esprit**, voir AUD-014 |
| Fraction de service à quai et quarts : régimes (bordées, tiers, quart, cinquième, sixième), « hommes morts », « de musique » | p.06 | aucune occurrence de ces notions dans `quarts/` ou les gabarits | **Non implémenté** (cadrage non autorisé en développement : « Ne pas ouvrir de travaux de code sans GO ») |
| Composition-type de la fraction de service (exemple BRF) paramétrable | p.06 | non implémentée | idem |
| Feuille de service ≠ tableau de quart | p.06 | feuille sans tableau de quart | **Conforme** |
| Génération automatique de tours | p.06, bandeau 09/10 | aucune | **Conforme à l'abandon** |
| PÉPIN / CRAT / RAV/c | p.12, p.13 | aucune occurrence | **Différé, conforme** |
| QR codes « hors V1 » | p.13 | route `/scan/<uuid>/` fonctionnelle | **Écart** à arbitrer (DP-06) |
| Rondes retirées | décision du 02/11 | routes absentes ; modèles résiduels | **Conforme** avec résidu (AUD-007) |
| IRB = « responsable de classe », ALFAN/Exploitation = « responsable de spécialité » | p.12 | rôles `ResponsableClasseNavire`, `ResponsableSpecialite` | **Conforme** (modèle) |
| Adjudant de compagnie, OSS | p.ORG (31/10) | non implémentés | **Différé** (« pas un GO d'implémentation ») |
| Commandant en second : vision globale, écritures limitées | p.13 | second exclu de la publication ; peut désigner des chefs de liste et configurer la feuille | **Partiel** (décision ouverte dans Notion) |
| Nom des bâtiments fictifs dans la démonstration | tâche Notion | 4 bâtiments sur 5 portent des noms réels de l'inventaire 2025 | **Non conforme**, AUD-024 |

## Vocabulaire du cahier

Le cahier parle d'annonces « Critique », le code d'« Urgent » : sans incidence.

## Non vérifié

Libellés complets de l'interface un à un, grades et spécialités du référentiel, correspondances public/privé, cohérence des horaires de quart avec les usages publiés, circuits PÉPIN/CRAT (hors périmètre V1), organisation d'un bâtiment à terre.
