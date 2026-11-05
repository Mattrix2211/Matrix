# Audit 09 — Quarts et services MER/QUAI (rapport partiel)

**Statut : Clôturé avec réserves** (voir « Clôture » en bas du rapport). Seul le volet « droits d'écriture » est audité (matrice dans `AUDIT_06.md`). Non audités : création et génération des listes, échanges de service de bout en bout, changements de mode MER/QUAI, activations différées, impressions, concurrence.

## 1. Constats exécutés

- **Aucune génération automatique de tours** dans `quarts/` : conforme à l'abandon du 09/10/2026 (EX-021). Seule durée « 24 h » trouvée, à l'affichage (`quarts/entree.py:39`), non comme règle.
- Circuit de la feuille de service (BROUILLON → VISA_SECTEUR → VISA_SERVICE → VISA_COMAEQ → PUBLIEE) **rejoué** : transitions correctes avec les acteurs prévus ; voir `AUDIT_06.md` §2 pour les acteurs supplémentaires qui franchissent les deux premiers paliers.
- Un quart ou une garde publié(e) se modifie directement (ajout/retrait de créneau avec motif) par le commandant et les administrateurs, pas par le chef de liste : cohérent avec les tâches Notion D-05 A et C « À faire » (proposition de modification et modification urgente). État actuel = **voie directe non fermée**.
- Étanchéité entre bâtiments pour les listes : conforme sur l'échantillon (bâtiment Auguste Bénébig).
- Étanchéité entre équipages (A/B) pour la création de feuille : conforme (`AUDIT_06.md` §2).

## 2. Exigences associées

EX-020, EX-021, EX-026, EX-027 (validation par équipage : **V-C** sur le visa COMAEQ et la désignation), EX-028 (échange : non audité).

## 3. Anomalies liées

AUD-014, AUD-015.

## Clôture (4ᵉ passe)

**Statut : Clôturé avec réserves.** « Avec réserves » signifie que l'analyse technique est achevée sur le périmètre décrit ; **les éléments listés ci-dessous restent non vérifiés et ne doivent pas être lus comme conformes**.

### Contrôles ajoutés à la 4ᵉ passe

Cas limites des listes publiées : retrait sans motif refusé, avec motif accepté et audité ; marin d'un autre bâtiment refusé ; fin avant début refusée ; **doublon accepté sur double envoi (AUD-033)** ; double publication idempotente. Échange de service rejoué (demande, acceptation, validation par le chef). Visas de la feuille (circuit complet en navigateur).

### Non vérifié ou dépendant d'une validation externe

Assistant de création de liste jusqu'à la publication, changements de mode MER/QUAI, impressions, concurrence réelle ; régimes de quart réels (expert du bord).
