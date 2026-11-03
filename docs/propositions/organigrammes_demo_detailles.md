# Organigrammes détaillés de la démonstration

Statut : **présentation pour relecture. Aucune donnée n'est générée** et `seed_demo` n'est pas modifié.
Complète `donnees_demo_organisation.md` (décisions et règles communes).

## Légende des sources

| Marque | Sens |
|---|---|
| **[D]** | **Documenté** : Notion « Organigramme et rôles » (page de référence) ou référentiel des bâtiments validé comme base documentaire |
| **[H]** | **Hypothèse de démonstration** : plausible, jamais présentée comme officielle ; configurable |
| **[PO]** | Décidé par le PO (messages du 2 novembre 2026) |
| **[E]** | Déjà présent dans `seed_demo` actuel ; conservé tel quel ou à modifier (précisé) |

Ce qui est **documenté** reste court : la hiérarchie générale, les responsabilités des commandants adjoints, le
double équipage, la règle « chaque service est rattaché au COMA compétent », les fonctions OSS et adjudant de
compagnie. Le **découpage interne précis** d'un bâtiment n'est pas documenté (Notion : il « reste fondé sur les
décisions et connaissances métier du PO » et doit rester configurable). Il est donc presque entièrement **[H]**.

Les noms de marins ne sont pas fixés ici : des noms vraisemblables, sans rôle dans le nom, seront choisis à la
génération. Les profils de recette actuels (`cdt_a`, `comanav_a`…) gardent leurs identifiants de connexion.

## 1. Hiérarchie commune

| Niveau | Source |
|---|---|
| Commandant → commandant en second → commandants adjoints (COMOPS, COMANAV, COMAEQ, COMAVIA selon le bâtiment) → chefs de service → chefs de secteur → chefs de section → équipiers | **[D]** |
| COMOPS : opérations, activité à la mer. COMANAV : conservation, matériels, adjoint sécurité. COMAEQ : vie à bord, service courant, adjoint protection | **[D]** |
| Chaque service rattaché au COMA compétent (`Service.commandant_adjoint`) | **[D]** |
| OSS (officier de sécurité du service) : fonction complémentaire d'un chef de service | **[D]** (fonction reconnue, droits non encore implémentés) |
| COMAVIA uniquement si capacité aviation | **[D]** ; aucune des trois unités n'en a dans la démo **[H]** |
| Maximum deux secteurs par service, une à deux sections par secteur | **[H]** (lisibilité de la démo) |

## 2. Bretagne — FREMM D 655, double équipage A et B

Identité : FREMM, indicatif de coque D 655, port d'attache Brest **[D]** (référentiel). Double équipage **[PO]**.
Équipage A à bord, équipage B à terre **[E]** (conservé : permet de montrer la lecture seule à terre).

### 2.1 Commandement, par équipage

| Fonction | Équipage A | Équipage B | Source |
|---|---|---|---|
| Commandant | 1 | 1 | [D] structure, [E] pour A et B |
| Commandant en second | 1 | 1 | [D] |
| COMOPS | 1 | 1 | [D] structure, [H] titulaires |
| COMANAV | 1 | 1 | [D] structure, [H] titulaires |
| COMAEQ | 1 | **poste vacant** | [E] ; vacance **[H]** (montre le visa exceptionnel par le commandant de l'équipage) |

### 2.2 Services, secteurs, sections

| Service | COMA | Secteurs | Sections | Source |
|---|---|---|---|---|
| Opérations | COMOPS | Passerelle ; Transmissions | Veille, Quart passerelle ; Transmissions bord | [E] service et secteur Passerelle ; reste [H] |
| Propulsion | COMANAV | Moteurs ; Auxiliaires | Moteurs bâbord, Moteurs tribord ; Pompes | [E] services, secteurs et sections bâbord et pompes ; tribord [H] |
| Énergie et électricité | COMANAV | Électricité | Tableaux, Groupes électrogènes | [E] « Énergie / Électricité / Tableaux » ; renommage et groupes [H] |
| Sécurité technique, incendie et avaries | COMANAV (rattachement provisoire) | Incendie ; Avaries | Sections incendie ; Sauvegarde | **[PO]** rattachement ; découpage [H] ; remplace le service « Sécurité » actuel [E] à modifier |
| Protection et vie à bord | COMAEQ | Protection ; Vie à bord | Garde et coupée ; Service courant | **[PO]** rattachement ; découpage [H] |

Aucun service « Sécurité » générique **[PO]**. Le service actuel `Sécurité` (COMAEQ) du jeu de départ est donc
**scindé** : la part incendie et avaries passe au COMANAV, la part protection au COMAEQ.

### 2.3 Équipages et effectif fictif

| | Équipage A (à bord) | Équipage B (à terre) |
|---|---|---|
| Direction | Commandant, second, 3 COMA | Commandant, second, COMOPS, COMANAV (COMAEQ vacant) |
| Chefs de service | 5 | 5 |
| Chefs de secteur | 4 | 3 |
| Chefs de section et équipiers | 6 | 3 |
| Total fictif | environ 18 | environ 14 |

Total d'environ 32 marins au lieu de 25 **[H]**, parce que chaque équipage doit avoir sa chaîne complète
(visas, désignations, séparation A/B). À réduire si vous préférez.

### 2.4 Scénarios que cette structure doit permettre

- Visa de la feuille de service par le COMAEQ A ; visa exceptionnel par le commandant B (poste vacant).
- Un COMANAV ne modifie rien dans « Protection et vie à bord » ; le COMAEQ ne modifie rien dans « Propulsion ».
- Un chef de service, un chef de secteur et un équipier de chaque équipage, avec cas de refus.
- Un marin de l'équipage B voit en lecture seule, ne modifie rien tant qu'il est à terre.
- Un marin désactivé et une désignation de rédacteur inopérante (cas déjà prévus).

## 3. Jacques Chevallier — BRF A 725, équipage unique

Unité complémentaire **[PO]**. Identité (BRF, A 725, Toulon) **[D]** (référentiel). Organigramme : **hypothèse de
démonstration, non officielle [PO]**. Un bâtiment ravitailleur n'a pas l'organisation d'une frégate **[H]**.

| Niveau | Contenu | Source |
|---|---|---|
| Commandement | Commandant, commandant en second | [D] structure |
| Commandants adjoints | COMOPS, COMANAV, COMAEQ ; **pas de COMAVIA** | [H] |
| Services | Pont et manœuvre (COMANAV) ; Propulsion et énergie (COMANAV) ; Ravitaillement (COMOPS) ; Vie à bord et soutien (COMAEQ) | [H] |
| Secteurs | Pont et manœuvre : Manœuvre ; Propulsion et énergie : Moteurs, Électricité ; Ravitaillement : Ravitaillement à la mer ; Vie à bord : Service courant | [H] |
| Sections | Une par secteur (Manœuvre : Pont ; Moteurs : Moteurs ; Électricité : Tableaux ; Ravitaillement à la mer : Rampes ; Service courant : Coupée) | [H] |
| Effectif fictif | environ 10 marins | [H] |

Rôle dans la démo : prouver l'isolation entre bâtiments (un marin de la Bretagne ne voit rien du BRF) et montrer
la silhouette du type BRF (en attente du Guide du marin, aucune illustration de substitution).

## 4. Auguste Bénébig — POM P 779, équipage unique

Unité complémentaire **[PO]**. Identité (POM, P 779, Nouméa) **[D]** (référentiel). Organigramme : **hypothèse de
démonstration, non officielle [PO]**.

| Niveau | Contenu | Source |
|---|---|---|
| Commandement | Commandant, commandant en second | [D] structure |
| Commandants adjoints | **Aucun dédié** : le commandement porte directement les services | [H] à confirmer |
| Services | Pont et opérations ; Machine ; Vie à bord | [H] |
| Secteurs | Un par service : Passerelle ; Moteurs ; Service courant | [H] |
| Sections | Une par secteur au plus | [H] |
| Effectif fictif | environ 7 marins | [H] |

Cas d'usage : **services sans commandant adjoint** (`commandant_adjoint` vide). Conformément à votre décision du
3 novembre, un commandant adjoint éventuel y serait en lecture seule ; ici le commandant et le second gardent
leurs droits, comme les chefs de service. Ce cas sert à tester la règle.

Question ouverte : un POM n'a-t-il vraiment aucun commandant adjoint ? À confirmer ; la configuration permet
d'en ajouter sans changer le code.

## 5. Récapitulatif des écarts avec le jeu actuel (à appliquer après votre accord)

| Écart | Action prévue à la génération |
|---|---|
| Service « Sécurité » (COMAEQ) unique | Scinder en « Sécurité technique, incendie et avaries » (COMANAV) et « Protection et vie à bord » (COMAEQ) |
| Noms de marins qui reprennent un rôle | Remplacer par des noms vraisemblables, grades et fonctions cohérents |
| Bretagne : un seul équipage complet | Deux chaînes complètes, COMAEQ B vacant |
| Normandie et BordOps I | Conservées en support des tests existants, ou retirées de la démo selon votre choix |
| BRF et POM absents | Ajoutés selon les §3 et §4 |
| Aucun contrôle des liens de démonstration | Test qui ouvre chaque lien généré (pas d'objet inexistant) |

## 6. Questions pour le PO

1. Accord sur le découpage des cinq services de la Bretagne (§2.2), noms compris ?
2. Effectif de la Bretagne : environ 32 marins (deux chaînes complètes) ou réduire ?
3. Le BRF comporte-t-il un COMOPS, et son service « Ravitaillement » relève-t-il bien de lui ?
4. POM sans commandant adjoint : confirmé, ou ajouter un COMAEQ ?
5. Conserver ou retirer Normandie et BordOps I de la démonstration ?

La génération ne démarre qu'après vos réponses et votre GO.
