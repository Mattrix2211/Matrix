# Rapport de clôture du jalon V2 — Matrix G0, révision 2

Branche `claude/fervent-wright-kl6gtx` · état applicatif B `6d6d0be` · base d'audit `637de94`.
Aucun code applicatif modifié (C13 : différence vide), aucune modification de `main`, aucune PR, aucune diffusion, phase 13 non engagée.

## 1. Corrections autorisées

1. **Règle générique de mise en page** (`gabarits/refonte.css`) : un titre de niveau 2 à 4 reste avec le début significatif de son contenu (deux premières puces, ou premier paragraphe). Le contrôle C8 et ses seuils n'ont pas été modifiés. Vérifié : RF « 12.2.2 » ouvre la p.70 avec ses puces ; DT « 23.2 » ouvre la p.90 avec ses puces ; 0 titre orphelin ; aucune page vide anormale.
2. **Registre A25** : « ticket créé depuis une maintenance non conforme » remplacé par « ticket correctif créé depuis un contrôle non conforme sur un matériel mobile (aucun ticket automatique pour une installation, NE-07) ». Résultats historiques, état et décisions inchangés ; 125 décisions sur 125 avec leur état (0 écart).
3. **Inspection visuelle** : voir `pdf_candidats/JOURNAL_INSPECTION_V4.csv`.

## 2. Livrables

| Document | Pages | Taille (octets) | SHA-256 |
|---|---|---|---|
| Guide utilisateur (GU) | 86 | 19 807 858 | `966983dc5aa7ee23e644747f303b98ae37526b4641143ca1f400ed254242f0a2` (identique à la V2) |
| Référentiel fonctionnel (RF) | 137 | 6 541 278 | `e5c91dff173bf8a38525de470e4dace0099d84def19cfc87adafd773fa06dbf3` |
| Dossier technique (DT) | 96 | 5 270 715 | `c0bfd130bf913d64fb37e21e7613dc5bf96deb822a472a81dee2b5cb5ef3bda0` |
| Registre (RE) | 52 | 1 813 119 | `45bc78edbb5629fd5a4fbe3ded8b1e37adc0047a2249927aff046a014a437caf` |

Compteurs de reconstruction réels (jamais remis à zéro) : GU 5, RF 8, DT 4, RE 3. Le budget de deux reconstructions est dépassé ; les constructions temporaires de reproductibilité (C12) ne sont pas comptées.

## 3. Contrôles

C8 sans bloquant (RF 0, DT 0 ; pages remplies à moins de 40 % : RF 4, DT 5, déjà connues) ; C13 vide ; états 125/125 ; relations des schémas S02, S14, S22, S27, S38 : 0 écart ; distinction matériel mobile / installation / relevé hors plage relue dans les quatre documents (aucune formulation générale restante).

## 4. Défaut nouveau — reconstruction DT demandée, non faite

**DT p.36-37 : le titre du chapitre 9 est coupé** (« 9 Tâches, demandes, programme, postes : » en bas de p.36, « mécanismes » en haut de p.37). Le défaut n'existait ni en V2 ni au commit `5a9885e` ; il est apparu avec le déplacement de contenu de la reconstruction n°4 et le contrôle C8 ne le détecte pas. Correction proposée : empêcher la coupure d'un titre de chapitre (règle CSS générique) et garder l'encadré « Public » d'un bloc avec son titre ; cela traiterait aussi les réserves cosmétiques ci-dessous. Elle exige une reconstruction du DT (n°5), éventuellement du RF (n°9). **Je me suis arrêté avant de reconstruire, comme demandé.**

Réserves cosmétiques (encadré « Public » coupé entre deux pages) : RF p.115-116 (présent aussi au commit `5a9885e`) ; DT p.33-34 et p.70-71 (la V2 en avait déjà : DT p.25 et p.36).

## 5. Autres réserves connues

Pages peu remplies : RF p.8, 16, 130, 137 ; DT p.7, 9, 12, 56, 75 ; GU 5 ; RE p.43. Schémas non repris dans un document : S09, S10b, S24, S28b, S40.
