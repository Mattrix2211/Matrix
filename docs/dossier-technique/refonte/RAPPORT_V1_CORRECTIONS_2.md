# Jalon V1 — dernières corrections après audit indépendant

Branche `claude/fervent-wright-kl6gtx`, état applicatif B `6d6d0be` (inchangé). Documents non validés ; la validation de la V1 appartient au PO.

## Corrections et pages concernées (avant → après)

| Réf. | Avant (b8c1c11) | Après | Pages finales |
|---|---|---|---|
| P0 Registre, anomalies | Les anomalies documentaires (AUD-015 `[V]`, AUD-026 `[?]`…) avaient perdu leur description | Une fiche par anomalie (AUD-001 à AUD-038) : constat, document et page, preuve, conséquence, correction recommandée, gravité, priorité, traitement prévu, statut. Aucune information supprimée | RE pp. 24–42 (chap. 6) |
| P0 A21 | A21 présenté entièrement « non développé » (RE p.14, RF p.7) | État décision par décision : DEC-PER-01 partielle, DEC-PER-04 réalisée, DEC-PER-02/03, DEC-OUT-01 à 05, DEC-DUR-01 à 07 non développées ; ce qui est disponible et ce qui reste à développer sont séparés. Aucun statut modifié | RE p.14 ; RF pp.7–9 |
| P1 DEC-DRT-05 | « partielle » sans détail | Partielle (2 lots livrés sur 3) : L02 livré, L03 livré, L04 non livré ; statut global conservé | RE p.45 et p.51 (§7.1) |
| P1 DEC-PRE-06 (même logique) | « partielle » sans détail | L01 livré, L21 non livré (1 lot sur 2) | RE p.49 et p.51 |
| P1 Guide | Étiquettes non définies explicitement | Phrase définissant 🟢 / 🔵 / 🟣 / ⚪ ; seules les mentions 🟢 décrivent l'existant ; 🟣 jamais présenté comme disponible | GU p.3 |
| P2 S25d | Flèches et libellés ambigus | Regroupement « Avant exécution », libellés explicites ; logique et chapitres inchangés | DT p.4 |

Pagination : GU 15, RF 9, DT 9 pages (inchangées) ; RE 33 → 51 pages (une fiche par anomalie, car aucune information ne devait être supprimée). Sommaires et renvois régénérés ; les entrées AUD ne figurent pas au sommaire (listées au chap. 6).

## Contrôles

C1, C5, C6, C7, C8, C13, C14 : 0 bloquant. C4 : 0 erreur. G2 `controler_registre.py` : 0 ❌. 46 schémas ≥ 8 pt. C13 : aucun fichier hors `docs/dossier-technique` modifié depuis `637de94`. Cohérence registre ↔ référentiel vérifiée pour A21 (mêmes états). Aucune décision promue : états de DEC-PRE-06, DEC-DRT-05, DEC-PER-01 (partielle) et DEC-PER-04 (réalisée) inchangés. Les contrôles automatiques ne prouvent pas l'exactitude métier.

## Inspection visuelle (96 dpi, build final)

Inspectées une à une : GU p.3 ; RF pp.7–9 ; DT pp.4–5 ; RE pp.2, 3, 14, 15, 16, 24–51. Aucun défaut bloquant. Observations mineures : titres de fiches AUD tronqués par « … » (titre court tiré du constat, texte complet dans la fiche) ; AUD-001 conserve des mentions entre crochets à la place des anciens mots interdits. Pages non modifiées non revues cette passe (revues lors de b8c1c11).

## Réserves ouvertes

1. RE passe à 51 pages : à arbitrer par le PO (format plus compact possible).
2. États des décisions déduits du plan en lots et du code ; « à instruire ◯ » ≠ non réalisé.
3. Titres d'anomalies abrégés.
4. A1–A26 et NE-01 à NE-07 restent des écarts documentés, pas des autorisations de modifier le logiciel ; les 29 tests restent dans `audit_preuves/`.
5. V1/G0 non déclarés validés.
