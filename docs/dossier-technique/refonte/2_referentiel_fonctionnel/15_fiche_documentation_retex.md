<!-- couvre: diffusable/15_documentation_retex.md | Chapitre 15 — Documentation du bord et retours d'expérience (RETEX) -->
<!-- couvre: diffusable/15_documentation_retex.md | 15.1 Deux objets qui se nourrissent -->
<!-- couvre: diffusable/15_documentation_retex.md | 15.2 Ce que voit et fait le marin -->
<!-- couvre: diffusable/15_documentation_retex.md | 15.3 Documents : qui fait quoi -->
<!-- couvre: diffusable/15_documentation_retex.md | 15.4 Le circuit RETEX aujourd'hui 🟢 -->
<!-- couvre: diffusable/15_documentation_retex.md | 15.5 Le circuit RETEX cible 🔵 -->
<!-- couvre: diffusable/15_documentation_retex.md | 15.6 Interactions avec les autres modules -->
<!-- couvre: diffusable/15_documentation_retex.md | 15.7 Cas particuliers -->
<!-- couvre: diffusable/15_documentation_retex.md | 15.8 Limites et éléments non vérifiés -->
<!-- partie: Modules -->
# Documentation du bord et retours d'expérience (RETEX)

<div class="ligne-public"><b>Public :</b> marins, responsables, développeurs · <b>Ce que vous y trouverez :</b> la base de connaissances du bâtiment (documents, versions, validation), le circuit RETEX qui l'alimente, et — séparés — le circuit tel qu'il fonctionne aujourd'hui et le circuit **cible** décidé par le PO</div>

**Écran de référence :** [[GU:16_ecrans_competences]] (captures de l'état B sur une instance de démonstration).

## Deux objets qui se nourrissent

| | **Document** | **RETEX** |
|---|---|---|
| Rôle | Procédure, consigne ou note que le bord applique | Enseignement tiré d'un événement, proposé pour que le bord s'améliore |
| Cycle | Brouillon → soumis → **publié** (versionné) | Proposé → **validé et publié** (ou refusé) → clos |
| Lien | Un RETEX validé **devient un document publié** | Une action décidée devient une **tâche** suivie |

## Ce que voit et fait le marin

> Exemple fictif : le matelot Durand a vécu une fuite mal traitée.

1. **Il consulte** les documents qui le visent (bâtiment, service, secteur, section, équipage) : titre, domaine, **version applicable**, historique des versions, origine (**procédure officielle** avec sa référence, ou **note locale non réglementaire**), date de prochaine révision.
2. **Il retrouve un document** par la recherche, ou directement depuis l'objet concerné : une installation, une formation ou une tâche peuvent afficher **leurs documents liés**.
3. **Il propose une amélioration** d'un document : une nouvelle version est soumise à validation (une seule proposition à la fois par document).
4. **Il propose un RETEX** depuis l'objet concerné (anomalie, ticket, demande…) ou depuis la page RETEX : titre, **constat**, causes si établies, **enseignement**, recommandation, portée, niveau de diffusion (**bâtiment** ou **flotte**), domaine. Le constat, l'enseignement et le titre sont **obligatoires**.

## Documents : qui fait quoi

| Action | Qui (seuil par défaut) | Règles |
|---|---|---|
| Rédiger / soumettre | **Chef de section ou plus** (`documentation_redaction`) | Seulement vers des publics de son périmètre ; une procédure officielle **cite sa source** |
| Valider et publier, archiver | **Chef de service ou plus** (`documentation_validation`) | Dans le périmètre du document ; **jamais sa propre version** |
| Refuser | Même droit | **Motif obligatoire** |
| Lier un document à un objet | Droit de gestion des liens | Seulement des objets auxquels on a accès |
| Proposer une amélioration | Tout marin qui voit le document | Équipage à bord uniquement |

![Versions de document](../schemas/svg/S29_versions_documentation.svg)

- Une version **publiée** devient la **version applicable** ; la précédente devient **obsolète** mais **reste consultable**. Rien n'est écrasé.
- Le **brouillon, la proposition et le refus** ne sont visibles que de leur **auteur** et des **gestionnaires**.
- Les validateurs reçoivent une notification « Document à valider » ; l'auteur est notifié de la décision.
- Les documents **dont la révision est due** sont signalés aux gestionnaires.
- Un **équipage à terre** consulte mais ne soumet pas.

## Le circuit RETEX aujourd'hui 🟢

![RETEX actuel](../schemas/svg/S30_retex_reel.svg)

1. **Proposition** par un marin à bord : le RETEX est rattaché à un **domaine du bâtiment**. Les quatre domaines par défaut (modifiables par bâtiment) désignent chacun un **commandant adjoint référent** et un **organisme destinataire habituel** :

   | Domaine | COMA référent | Organisme destinataire |
   |---|---|---|
   | Opérations et missions | COMOPS | ALFAN / Entraînement |
   | Technique, sécurité matérielle, MCO | COMANAV | SSF / ERO / IRB puis ERDT / IRDT |
   | Service courant, protection, vie à bord | COMAEQ | ALFAN / Exploitation |
   | Aviation | COMAVIA | ALFAN / Exploitation |

2. **Routage** : sont notifiés (avec action requise) **tous les habilités du bâtiment** (seuil `retex_validation`, chef de service par défaut), **ceux dont la fonction cite le COMA référent du domaine apparaissant en premier**. Il n'y a **pas d'étape intermédiaire**.
3. **Décision** : un habilité **valide** (le RETEX est **publié comme document du bâtiment**, version 1, origine « note locale ») ou **refuse avec motif**.
4. **Actions** : après validation, le valideur crée une **tâche assignée** à un marin du bâtiment (à bord), liée au RETEX.
5. **Clôture** : le valideur peut **clore** le RETEX, **uniquement quand toutes ses actions sont terminées**. Les domaines (COMA référent, organisme) se configurent au niveau du seuil de validation.
6. **Traçabilité** : chaque étape est enregistrée dans le journal d'audit.

Le RETEX est **limité au bâtiment** : on ne propose ni ne valide pour un autre navire ; le commandement le voit en lecture ; un marin voit les siens et les RETEX **validés** de son bâtiment.

## Le circuit RETEX cible 🔵

![RETEX cible](../schemas/svg/S31_retex_cible.svg)

Décisions du PO (dossier V1.2) :
- `DEC-RTX-01` : **auteur → chef de section (s'il existe) → chef de secteur → chef de service**. Cette décision **remplace** l'ancienne recommandation « COMA référent d'abord ».
- `DEC-RTX-02` : une **demande de correction** doit être **motivée**.
- `DEC-RTX-03` : une correction entraîne une **nouvelle version** et les validations nécessaires.
- `DEC-RTX-04` : **traçabilité** de qui a proposé, modifié, validé ou rejeté.

| | Aujourd'hui | Cible |
|---|---|---|
| Étapes | Une seule : un habilité décide | Chef de section → chef de secteur → chef de service |
| Rôle du COMA référent | Ordre de notification | Ne décide pas d'abord (décision remplacée) |
| Correction | Pas de demande de correction : valider ou refuser | Demande motivée → nouvelle version → nouvelles validations |
| Traçabilité | Audit de chaque étape | Idem, plus l'historique des versions |

**Trois actes à ne jamais confondre** (précisé par le PO) :
1. la **validation** (circuit hiérarchique ci-dessus) ;
2. l'**autorisation de diffusion**, donnée par le **chef de service après la validation** 🔵 ;
3. la **transmission effective** à un organisme extérieur, qui est un acte distinct, **ni une validation, ni un simple changement de statut**.

⚪ **À confirmer avec les procédures métier applicables** : les **destinataires, les canaux et les responsabilités exacts** de la transmission. Aucune règle n'est inventée ici.

🟢 **Aujourd'hui, le marquage « flotte » n'est pas une transmission.** Il enregistre seulement le niveau de diffusion souhaité et l'organisme habituel du domaine ; **aucun envoi, aucune notification, aucun accusé** n'existe. Il ne doit jamais être lu comme la preuve qu'un organisme a reçu le RETEX. Écart inscrit au registre (A15, A16 ; lot L11).

## Interactions avec les autres modules

| Module | Lien |
|---|---|
| Tickets, anomalies ([[RF:12_fiche_maintenance]]) | Source d'un RETEX ; le ticket fermé porte déjà un **retour d'expérience** (diagnostic et solution) |
| Tâches ([[RF:10_fiche_taches_demandes_programme_postes]]) | Les actions décidées sont des tâches |
| Formations ([[RF:14_fiche_formations]]) | Un RETEX peut déboucher sur une formation (cible : reboucle formation, maintenance, exploitation) |
| Installations, matériel ([[RF:11_fiche_materiel_installations]]) | Documents liés à l'objet |
| Recherche globale | Documents trouvés, bornés au public visé |
| Annonces ([[RF:09_fiche_communication]]) | ⚪ Pas de lien automatique |

## Cas particuliers

- **Équipage à terre** : lecture seule pour la documentation et le RETEX.
- **Document archivé** : plus de proposition d'amélioration.
- **Objet source inaccessible** : un RETEX ne peut pas citer une source que l'on ne peut pas ouvrir.

## Limites et éléments non vérifiés

- ⚪ **Couverture de tests faible** : `documentation` 9 fonctions de test, `retex` 5 fonctions (contre 493 pour `assets`). Les règles décrites viennent surtout de la lecture du code ; le compte rendu de lot de l'édition initiale (11/11/2026) rapporte 1 491 tests OK pour sept paquets dont ces deux-là, résultat **historique non rejoué pour la révision 2**, qui ne protège presque pas ces deux modules.
- ⚪ Le modèle documentaire **cible** (bibliothèque unifiée, droits de lecture fins par document) n'est pas décrit : aucune décision correspondante n'a été lue.
- 🟢 Les écrans de documentation et de RETEX ont été rejoués (liste) sur l'instance de démonstration le 16/11/2026 ; ⚪ le circuit de validation et la proposition d'un RETEX n'ont pas été rejoués.

**Sources (état B).** Décisions `DEC-RTX-01`, `DEC-RTX-02`, `DEC-RTX-03`, `DEC-RTX-04` (dossier V1.2). Références dans la partie restreinte du dossier.

## Écarts et décisions du registre

Les tableaux ci-dessous sont **générés depuis le registre central** : le statut et l'état de chaque entrée y sont tenus ; cette fiche n'en donne aucun autre. Une proposition 🟣 n'est pas une décision ; « non développée » signifie seulement que le lot correspondant n'est pas livré dans l'état B.

### Écarts, points à confirmer et propositions

@ecarts A15 A16 D3

### Décisions du PO

@decisions DEC-RTX-01 DEC-RTX-02 DEC-RTX-03 DEC-RTX-04
