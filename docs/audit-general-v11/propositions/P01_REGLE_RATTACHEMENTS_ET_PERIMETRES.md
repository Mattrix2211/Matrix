# P01 — Règle complète de validation des rattachements et des périmètres (DP-03)

**Statut : proposition d'audit, non implémentée.** Orientation du PO : option B complétée par D (section absente lorsqu'un secteur n'en possède aucune). Contrainte ajoutée : un marin **transversal au niveau du secteur** alors que celui-ci a plusieurs sections ne doit recevoir ni section fictive ni droits élargis par accident. Analyse de départ : `audits/AUDIT_DP03_SECTIONS.md`.

## 1. Constat de départ (mesuré)

- Le périmètre d'un marin est **déduit du niveau le plus fin renseigné** (section, sinon secteur, sinon service, sinon bâtiment) : `accounts/models.py:87-96`. Un champ vide **élargit** donc le périmètre ; il ne le réduit jamais.
- Mesuré : un équipier sans service ni secteur ni section voit 11 occurrences de maintenance sur 11 (contre 5 s'il est rattaché) (`AUDIT_DP03_SECTIONS.md` §3).
- Le périmètre est **à une seule valeur** (un seul identifiant). Un marin ne peut pas couvrir « les sections bâbord et tribord, mais pas la section auxiliaires » sans prendre le secteur entier.
- Les helpers de périmètre sont employés à 260 endroits dans 48 fichiers : toute évolution du modèle de périmètre est transversale (modules quarts, maintenance, logistique, tâches, annonces, calendrier…).
- La suppression d'une section remet à NULL le rattachement des marins (donc élargit leur périmètre) : AUD-020.

## 2. Principes proposés

1. **Rattachement (où je suis affecté) et portée (ce que je vois et fais) sont deux notions.** La portée n'est jamais déduite silencieusement d'un champ vide.
2. **Refus par défaut** : un compte opérationnel sans portée déclarée n'a accès qu'à son espace personnel, jamais à tout le bâtiment.
3. **Visibilité ≠ écriture** : voir le secteur n'autorise pas à y écrire ; les droits d'écriture suivent la fonction (voir P02).
4. **Pas de section fictive.** L'absence de section est un état explicite et valide dans deux cas seulement (§3).

## 3. États d'un rattachement à la section

| État | Définition | Quand c'est valide |
|---|---|---|
| **Renseignée** | Le marin est affecté à une section | toujours, si la section appartient au secteur |
| **Sans objet** | Le secteur n'a **aucune section active** | automatique, jamais saisi ; si une section est créée plus tard, les marins concernés passent « à compléter » |
| **Transversale** | Le marin travaille volontairement sur tout le secteur alors que celui-ci a des sections | explicite, motivée, tracée (§5) |
| **À compléter** | Section oubliée alors que le secteur en a | **état d'alerte, jamais un état de fonctionnement** : portée minimale tant qu'il n'est pas corrigé |

## 4. Règles de validation (V1 à V12)

| N° | Règle | Effet si violée |
|---|---|---|
| V1 | Cohérence de la hiérarchie : section ∈ secteur ∈ service ∈ bâtiment, tout objet archivé exclu des nouvelles affectations | refus à l'enregistrement |
| V2 | Tout compte opérationnel à bord a un bâtiment ; un service sauf fonctions de bâtiment (commandement, second, commandants adjoints, administrateur d'unité) | refus ; comptes existants listés par un rapport |
| V3 | Si le service a au moins un secteur actif, le secteur est obligatoire pour les rôles ≤ chef de secteur | refus |
| V4 | Secteur sans section active : la section est « sans objet » ; saisir une section est refusé | refus |
| V5 | Secteur avec au moins une section active : l'équipier a soit une section, soit l'état **transversal** | sinon « à compléter » (portée minimale + alerte au chef de secteur) |
| V6 | État **transversal** : réservé aux marins dont la **fonction** le justifie (liste configurable par bâtiment : mécanicien volant, brigade d'intervention, magasinier de secteur…) ; motif obligatoire ; désignation par le chef de secteur ou le chef de service ; revue périodique configurable (par défaut annuelle) ; `AuditLog` | refus sans fonction ni motif |
| V7 | Rôle et portée cohérents : `CHEF_SECTION` ⇒ section renseignée ; `CHEF_SECTEUR` ⇒ secteur, section sans objet ou transversale par nature ; `CHEF_SERVICE` ⇒ service ; commandement et commandants adjoints ⇒ bâtiment | refus |
| V8 | Création de la première section d'un secteur : tous les marins « sans objet » passent « à compléter » et le chef de secteur reçoit la liste à traiter ; aucune réaffectation automatique | alerte, pas de blocage |
| V9 | Archivage ou fusion d'une section : refusé tant que des marins, équipements ou documents y sont rattachés sans destination choisie (assistant de transfert, voir P04) ; jamais de remise à NULL | refus avec assistant |
| V10 | Double équipage : le rattachement se déclare par équipage ; le secteur est commun au bâtiment, la portée de personnes reste bornée à l'équipage (règle existante conservée) | inchangé |
| V11 | Une portée **transversale** ouvre la **lecture** de tout le secteur ; l'écriture reste limitée aux objets qui lui sont assignés ou à sa fonction (P02) | par conception |
| V12 | Contrôle d'ensemble : une page « Rattachements incohérents » (comptes à compléter, transversaux à revoir, sections vides, sections sans chef) accessible à la fonction de gestion de la structure | rapport, pas de blocage |

## 5. Le marin transversal : trois formulations possibles

| Option | Principe | Avantages | Limites |
|---|---|---|---|
| **T1 — Secteur entier explicite** | portée = secteur, état « transversal » + fonction + motif | simple ; compatible avec le modèle actuel (portée à une valeur) | donne le secteur entier même si le marin n'en couvre que deux sections sur quatre |
| **T2 — Liste de sections désignées** | le marin est affecté à plusieurs sections explicitement (par exemple bâbord et tribord) | juste : ni section fictive, ni secteur entier | demande un modèle de portée **multi-valeurs** : impact sur 260 appels de périmètre ; à lancer comme chantier propre |
| **T3 — Affectation principale + accès secondaires** | section principale + accès complémentaires temporaires (renfort) | convient aux renforts temporaires | proche de la délégation (P02) ; durée bornée obligatoire |

**Recommandation** : T1 immédiatement (aucun changement du moteur de périmètre) avec les garde-fous V5, V6, V11 ; T2 comme évolution après V1.1, si le terrain montre des marins couvrant seulement quelques sections. T3 relève de la délégation.

## 6. Transition des données existantes (sans modifier la base pendant l'audit)

1. Rapport en lecture seule des comptes dont le rattachement est incomplet (mesure sur la démonstration : 8 profils avec secteur et sans section, tous `CHEF_SECTEUR`, donc valides selon V7).
2. Classement : valide / à compléter / transversal à qualifier.
3. Aucune migration destructive ; les comptes « à compléter » conservent leur accès actuel pendant une période de grâce configurable, puis passent en portée minimale.

## 7. Cas d'essai à écrire avant toute implémentation

Secteur sans section avec équipier ; création de la première section ; transversal avec fonction ; transversal sans fonction (refus) ; archivage d'une section occupée ; fusion de deux sections ; chef de section sans section (refus) ; double équipage ; compte « bâtiment seul » (portée minimale) ; lecture du secteur et écriture limitée aux objets assignés ; rapport d'incohérences.

## 8. Dépendances avec les autres décisions

DP-13 (archivage, transfert), DP-09 (écriture par fonction), décision déjà validée « rattachement obligatoire pour tout compte opérationnel » (Notion, à faire plus tard).
