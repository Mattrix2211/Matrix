# Cahier des charges UX/UI — Matrix

Ce document définit les règles d'expérience utilisateur et d'interface de Matrix. Il complète la direction artistique (`design/DESIGN_SYSTEM.md`) et les règles techniques (`CLAUDE.md`). En cas de conflit sur un point visuel, ce document précise la déclinaison propre à Matrix ; en cas de conflit sur un point métier, la page Notion « Cahier des charges » fait foi.

Décisions validées par l'utilisateur le 2 octobre 2026.

---

## 1. Objet

L'objectif n'est pas de refaire l'identité visuelle, mais de restructurer l'expérience pour que la richesse fonctionnelle de Matrix ne produise pas une interface surchargée.

**Matrix doit rester dense en fonctionnalités, mais calme visuellement.**

Principe directeur :

> Un marin ouvre Matrix, comprend immédiatement sa situation, identifie ce qui demande son attention et sait quelle action effectuer.

L'interface n'expose jamais toute la complexité fonctionnelle en permanence.

---

## 2. Contexte d'utilisation

Ces hypothèses conditionnent toutes les règles qui suivent.

### 2.1 Le PC fixe est le support principal

Matrix est utilisé sur les **postes fixes du réseau du bâtiment** (et de l'intranet Défense à terre), au clavier et à la souris.

- La **tablette** et le **scan de QR code** sont des **options** : le code doit les rendre possibles (mise en page fluide, QR imprimable sur les fiches), mais **aucun parcours ne doit en dépendre**.
- Le **survol** est autorisé pour de l'information secondaire (infobulle, aperçu), jamais pour une information ou une action essentielle.
- Les **raccourcis clavier** et la navigation au clavier (Tab, Entrée, flèches) sont prioritaires.

### 2.2 Maintenance « papier puis saisie »

Cas normal : le marin imprime la fiche de maintenance, réalise l'entretien sur place avec la fiche papier, puis **saisit le compte rendu sur un PC** au retour.

Conséquences :

- la **fiche imprimable** est un livrable de premier plan (voir §19) ;
- la **saisie après coup** doit être rapide, notamment **en série dans une grille façon tableur** ;
- l'écran d'exécution en direct (§18) reste disponible mais n'est pas le parcours de référence.

### 2.3 Postes partagés

Plusieurs marins utilisent le même poste.

- L'**utilisateur connecté est toujours visible** (nom, grade, équipage) dans la barre supérieure.
- **Connexion et déconnexion rapides** (déconnexion en un clic, accessible partout).
- **Déconnexion automatique** après inactivité. Le délai est **configurable** (principe « configuration plutôt que code »).
- Un travail en cours n'est jamais perdu par une déconnexion automatique (voir §5.4).

### 2.4 Postes anciens

- **Résolution de référence : 1366×768.** Toute page doit y être lisible sans défilement horizontal, avec l'essentiel visible sans défiler.
- Interface **légère** : pas d'animations coûteuses, pas de bibliothèque JavaScript lourde, pages rapides sur des machines lentes.

### 2.5 Hors Internet

Rappel du principe n°4 : aucune ressource distante. Les polices **et Bootstrap Icons** sont auto-hébergées dans `static/`.

---

## 3. Objectifs UX

- compréhension de l'écran en quelques secondes ;
- priorité aux informations qui demandent une action ;
- réduction du bruit visuel ;
- actions contextuelles plutôt que permanentes ;
- navigation compréhensible sans apprendre des icônes ;
- formulaires simples, préremplis et progressifs ;
- **saisie en série plus rapide qu'Excel** ;
- cohérence stricte entre tous les modules ;
- conservation du contexte lors des actions rapides.

---

## 4. Principe fondamental : divulgation progressive

Une information, une action ou un formulaire n'est affiché en permanence que s'il est utile à cet instant.

Toute fonctionnalité secondaire est masquée, repliée, ou accessible par un menu contextuel, un popover, un panneau latéral, une modale ou une page dédiée.

> Tout élément persistant à l'écran doit justifier sa présence à cet instant.
>
> Matrix ne demande pas à l'utilisateur d'ignorer les informations inutiles : il les masque pour lui.

---

## 5. Hiérarchie des interactions

### 5.1 Les niveaux

| Niveau | Usage | Exemples | Interdit |
|---|---|---|---|
| **Popover** | Petite information ou mini-action sans quitter la page | Dernier relevé, détail d'un statut, aperçu d'une anomalie, fiche résumée d'un marin, événement du calendrier | Formulaire complexe |
| **Menu contextuel** (`⋯`) | Actions secondaires | Modifier, voir le QR code, imprimer, déplacer, archiver, supprimer | Action principale |
| **Modale** | Action courte demandant une concentration temporaire | Confirmation, mot de passe pour une action sensible, signalement rapide, petite modification | Grand formulaire métier |
| **Panneau latéral** (drawer) | Plusieurs champs en gardant le contexte de la page | Filtres, ajout d'un créneau, affectation de marins, ajout d'un relevé, **discussion**, historique court | — |
| **Assistant multi-étapes** | Création d'un objet isolé complexe | Création de matériel, signalement d'anomalie, création d'une liste de quart | Saisie en série |
| **Grille de saisie** | Saisie ou contrôle **en série** | Comptes rendus de contrôle de 40 extincteurs, exemplaires d'un article du catalogue, relevés multiples | — |
| **Page complète** | Workflow métier complexe | Gérer une liste de quart, modifier une fiche de maintenance, administrer l'organisation | — |

Le panneau latéral se ferme toujours sans changer de page.

**Composants** (`matrix/templates/components/`, balises de `matrix/core/balises_composants.py`) : `popover.html`, `menu_contextuel` + `menu_item.html`, `modale`, `panneau_lateral`, `assistant`. Règles communes : Échap ferme chaque niveau, le focus revient au déclencheur, le titre est relié par `aria-labelledby` et toute icône seule porte un `aria-label`. Une seule action principale (`--signal`) par vue : jamais dans un menu `⋯`, et au plus une par modale ou par étape d'assistant. Les actions destructives sont les dernières entrées du menu (rouge). Le contenu d'une modale ou d'un panneau peut se charger par `hx-get` (paramètre `url`). La grille et la page complète sont traitées en UX-0.5 ; la règle de choix reste celle du §5.2.

### 5.2 Assistant ou grille : la règle

- **Un objet isolé à créer** → assistant multi-étapes (ou formulaire simple s'il tient en une étape).
- **Plusieurs objets ou plusieurs lignes à saisir** → **grille façon tableur**.

La grille offre au minimum : navigation au clavier (Tab, Entrée, flèches), **recopie vers le bas**, bouton **« Tout conforme »**, validation ligne par ligne avec erreurs affichées dans la cellule, enregistrement de l'ensemble en une action.

### 5.3 Règles de l'assistant

- Une étape correspond à une décision mentale cohérente.
- Affichage de l'étape actuelle, des étapes restantes et des données déjà saisies.
- Boutons Précédent / Suivant ; **revenir en arrière ne perd aucune donnée**.
- **Synthèse métier finale** avant validation.
- Ce que Matrix connaît déjà (profil, contexte de la page) est prérempli ; une étape entièrement connue est supprimée.

### 5.4 Brouillons enregistrés automatiquement

Les **comptes rendus, assistants et grilles de saisie** enregistrent un brouillon **côté serveur** au fil de la saisie. L'utilisateur le retrouve après une coupure réseau, une déconnexion automatique ou une fermeture du navigateur (« Reprendre la saisie du 02/10 à 14:12 »).

---

## 6. Assistants de référence

### 6.1 Ajout de matériel par le bord

Conforme au cadrage du catalogue de matériel flotte : **le bord ne saisit pas l'article librement**.

1. **Article** — recherche et choix d'un article du catalogue flotte.
2. **Quantité et rattachement** — quantité, service, secteur, section, emplacement (préremplis depuis le profil).
3. **Exemplaires** — **grille** : une ligne par exemplaire (n° de série, date de contrôle, péremption, photo facultative), avec recopie vers le bas.
4. **Vérification** — synthèse : « 12 × Extincteur CO₂ 5 kg — Sécurité incendie — Local 031 — NNO 123456 ». Bouton **Ajouter les 12 matériels**.

### 6.2 Signalement d'une anomalie

1. Quel est le problème ? (objet concerné prérempli si on vient de sa fiche)
2. Gravité / impact.
3. Photo, commentaire, précision.
4. Synthèse et envoi.

Si l'anomalie est critique, Matrix demande automatiquement les informations complémentaires nécessaires.

### 6.3 Création d'une liste de quart ou de garde

Type → période → périmètre → règles → vérification → création du brouillon.

### 6.4 Saisie d'un compte rendu de maintenance

Cas normal (§2.2), après l'entretien sur papier :

1. Checklist (case par case, ou **« Tout conforme »** puis exceptions).
2. Relevés.
3. Anomalies constatées.
4. Conformité globale : Conforme / À surveiller / Non conforme.
5. Synthèse ; signature (mot de passe) seulement si l'installation est critique.

Pour une série de matériels de la même catégorie : **grille de comptes rendus**, une ligne par exemplaire.

---

## 7. Navigation globale

Barre latérale **rétractable**, avec libellés texte (pas seulement des icônes) :

- **Personnel** — Aujourd'hui, Calendrier
- **Équipements** — Matériels, Installations, Plan du navire
- **Maintenance** — Maintenance, Tickets correctifs, Anomalies
- **Activité** — Rondes, Quarts et gardes
- **Compétences** — Formations
- **Supervision** (selon les droits) — Prêt à appareiller, Flotte, Spécialités, Classes de navire
- **Administration** (selon les droits) — Annuaire, Paramètres

Les groupes et entrées s'affichent selon les droits et les modules activés pour le bâtiment.

---

## 8. Barre supérieure

Uniquement les fonctions globales :

- recherche globale ;
- contexte : bâtiment (sélecteur pour les utilisateurs à terre qui suivent plusieurs bâtiments) ;
- **utilisateur connecté** (nom, grade, équipage) et déconnexion en un clic ;
- **centre de notifications** (§23) ;
- bascule **mode clair / mode sombre** (§17).

Les modules métier ne sont plus alignés sous forme d'icônes dans la barre supérieure.

---

## 9. Page d'accueil « Aujourd'hui »

Le libellé « Tableau de bord » est remplacé par **« Aujourd'hui »** : le cockpit personnel.

### 9.1 Utilisateur à bord

**En-tête** — « Bonjour QM Martin » · vendredi 2 octobre · Frégate XXX · Service Énergie/Propulsion.

**À faire** — uniquement ce qui demande une intervention, trié par : urgence, retard, criticité, échéance.

```
[rouge]  Maintenance pompe incendie — en retard, prévue hier
[ambre]  Intervention DA2 — en attente de validation
         Ronde sécurité — 10:30
         Formation incendie — 14:00
```

**Brouillons à reprendre** — comptes rendus ou saisies non terminés.

**Ma journée** — frise : 08:00 Quart · 10:30 Ronde · 14:00 Formation · 18:00 Service.

**Informations secondaires** (plus bas) — qualifications, prochaines échéances, équité, activité passée.

**Supervision** (rôles concernés, sans perturber l'espace personnel) — maintenances en retard, anomalies ouvertes, validations en attente, équipements indisponibles du périmètre.

### 9.2 Équipage à terre (double équipage)

Même page, en **lecture seule** (voir §11.4).

### 9.3 Utilisateur à terre (SSF, responsable de spécialité, chef du responsable)

**Vue flotte**, sans frise de quarts :

1. **À faire** — propositions de fiches ou d'articles du catalogue à valider, tickets à commenter, demandes en attente.
2. **Mes bâtiments** — une carte par bâtiment suivi, avec badges d'état (maintenances en retard, anomalies ouvertes, indisponibilités) ; un clic ouvre le bâtiment dans son contexte.

---

## 10. Fiches métier : anatomie standard

Toutes les grandes fiches suivent la même structure.

1. **Titre (H1) = identité de l'objet** — « Pompe incendie tribord », jamais « Installation ».
2. **Sous-titre** — type et criticité (« INSTALLATION CRITIQUE »), rattachement (« Mécanique · Machine AV »), badge d'état (« Opérationnelle »).
3. **Indicateurs clés** (composant Metric, cliquables, §12) — 1 248 h · Vibration A · Isolement 72 MΩ · Maintenance dans 12 j.
4. **Action principale** (une seule, couleur Signal) — par exemple « Signaler une anomalie ».
5. **Bouton « Discussion · N »** — ouvre la discussion de l'objet dans un **panneau latéral** (app `threads`), sur toutes les fiches.
6. **Menu `⋯`** — actions secondaires.
7. **Bandeau de version** si l'objet suit le circuit proposer → valider → publier (§11.1).
8. **Mention de traçabilité** — « Modifié par SM Durand le 01/10 à 16:40 », lien vers l'historique (§11.2).
9. **Onglets** — au maximum environ cinq.

---

## 11. Comportements transverses

### 11.1 Proposer → valider → publier

Composant standard sur tous les objets concernés (fiches de maintenance, catalogue de matériel, listes de service…) :

- **bandeau de version** : « Version publiée du 12/09 » et, s'il y en a une, « Proposition en attente de validation (SM Durand, 01/10) » ;
- **comparaison** entre la version publiée et la proposition (ajouts, suppressions, modifications mis en évidence) ;
- boutons **« Proposer »** et **« Publier »** distincts, affichés selon les droits de l'utilisateur ;
- la version publiée reste active tant que la proposition n'est pas validée ; toutes les versions sont conservées et consultables.

### 11.2 Traçabilité visible

- Chaque fiche affiche l'auteur et la date de la dernière modification.
- Un **historique uniforme** (basé sur l'`AuditLog` existant) indique qui a modifié quoi, quand, avec l'**ancienne et la nouvelle valeur**.
- L'historique est **visible par tout utilisateur qui voit la fiche**.

### 11.3 Discussion

Bouton « Discussion · N » dans l'en-tête de chaque fiche, qui ouvre un **panneau latéral** : on discute sans quitter la fiche.

### 11.4 Lecture seule (équipage à terre)

- Les actions interdites sont **masquées** (pas grisées).
- Un **bandeau discret** permanent indique « Équipage B à terre — lecture seule ».

---

## 12. Indicateurs interactifs

Un indicateur clé peut ouvrir un popover. Exemple sur « 1 248 h » :

```
Dernier relevé : 1 248 h
Ajouté aujourd'hui à 08:12
Tendance : +42 h / mois
[Ajouter un relevé]
```

Même principe pour vibration, isolement, prochaine maintenance, stock, disponibilité.

---

## 13. Fiche Installation

Cinq onglets de premier niveau :

| Onglet | Contenu |
|---|---|
| **Vue d'ensemble** | Informations générales, état, emplacement, indicateurs ; blocs repliables **Documents** et **Sous-équipements** |
| **Maintenance** | Plans et maintenances associées |
| **Mesures** | Heures de marche, vibrations, isolement (sous-sections), détection de dérive |
| **Historique** | Événements, interventions, modifications |
| **Pièces** | Pièces et stock lié |

La discussion est dans le panneau latéral (§11.3). Le QR code ne monopolise pas l'en-tête : il est accessible par `⋯ → QR code` et figure sur la fiche imprimée.

---

## 14. Cards

La card générique actuelle (accent cyan, lueur, survol) est remplacée par des composants distincts :

| Composant | Usage | Survol |
|---|---|---|
| **Surface** | Conteneur neutre | Non |
| **InteractiveCard** | Élément réellement cliquable | Léger |
| **ActionCard** | Une action est attendue | Léger |
| **Metric** | Indicateur compact (1 248 h, 4 anomalies, 72 MΩ) | Seulement s'il ouvre un popover |
| **Attention** | Vraie anomalie, retard ou danger | Non |

Une card non interactive n'a **jamais** de survol.

---

## 15. Couleurs et visuel

### 15.1 Sens des couleurs

| Couleur | Sens |
|---|---|
| **Cyan Signal** (#00B4D8) | Action principale, sélection, focus, navigation active |
| **Vert** (`--green-tech`) | Conforme, validé, opérationnel |
| **Ambre** | Attention, surveillance |
| **Rouge** | Danger, erreur, retard critique, action destructive |
| **Gris** | Neutre, désactivé, terminé |

- La couleur indique d'abord un **état**, pas un type de donnée ; pas de couleur par module.
- Signal n'est **jamais décoratif** : plus il est rare, plus il est efficace.
- Une information ne repose jamais sur la couleur seule (libellé ou icône en plus), pour l'impression en noir et blanc et l'accessibilité.

### 15.2 Visuel utile, pas de décor

On **garde** le visuel qui informe : photos de matériel, jauges, frises, graphiques, plan du navire, badges d'état. On **supprime** le décor gratuit : lueurs, accents cyan permanents, survols sur les éléments non cliquables, effets sans signification.

---

## 16. Iconographie

- Bibliothèque unique : **Bootstrap Icons**, **auto-hébergée**.
- **Aucun emoji** dans l'interface métier.
- Une action importante = **icône + texte**. Une icône seule n'est acceptable que pour une action universelle, secondaire ou dans un espace contraint, et porte toujours une **infobulle** et un **`aria-label`**.
- Un concept garde la même icône partout :

| Concept | Icône |
|---|---|
| Anomalie | `bi-exclamation-triangle` |
| Calendrier | `bi-calendar3` |
| Maintenance | `bi-tools` |
| Paramètres | `bi-gear` |
| Utilisateur | `bi-person` |
| Suppression | `bi-trash` |
| Modification | `bi-pencil` |
| Pièce | `bi-box` |
| Historique | `bi-clock-history` |
| Discussion | `bi-chat-left-text` |
| Impression | `bi-printer` |

---

## 17. Mode sombre

**Dérogation validée au design system** (qui réserve le mode clair aux contextes navals) : Matrix propose un **mode sombre**, pour l'usage de nuit (passerelle, PC NAV, locaux en éclairage réduit).

- Mode **sombre classique** : fond sombre, couleurs atténuées, contrastes suffisants ; les couleurs d'état gardent leur sens.
- Activation **manuelle** par chaque marin (bascule dans la barre supérieure ou le profil), choix mémorisé dans son profil.
- Mode clair par défaut.
- Techniquement : toutes les couleurs passent par des variables CSS (`:root` et `[data-theme="dark"]`) ; aucune couleur codée en dur dans les templates.

---

## 18. Exécution de maintenance en direct

Parcours secondaire (§2.2), utile si un poste est proche de l'installation ou si la tablette est un jour retenue.

- En-tête : « Pompe incendie tribord — Entretien trimestriel — 3 / 8 opérations réalisées ».
- Checklist avec champs de relevés en ligne (« Pression [ 4.2 ] bar »).
- **Barre d'action persistante** en bas : Enregistrer · Terminer la maintenance.
- La conformité (Conforme / À surveiller / Non conforme) est demandée **au moment de terminer**. Si Non conforme, Matrix propose immédiatement « Créer une anomalie », ou la crée selon les règles métier.
- Pour une installation critique, le mot de passe n'apparaît **qu'au moment** où il est nécessaire.

---

## 19. Impression

### 19.1 Feuille de style commune

Toute fiche, liste ou planning **s'imprime proprement** : sans navigation ni boutons, lisible en noir et blanc, en-tête avec bâtiment, date d'impression et utilisateur.

### 19.2 Fiche de maintenance papier

Gabarit dédié, pensé pour le parcours papier puis saisie :

- identité de l'installation ou du matériel, gamme, date prévue, intervenant ;
- checklist avec **cases à cocher** ;
- **champs de relevés** avec unité et plage attendue ;
- zone d'observations ;
- zone de signature ;
- QR code (facultatif) et identifiants pour retrouver la fiche à la saisie.

---

## 20. Écrans par module

### 20.1 Calendrier

- Le calendrier est le contenu principal de la page.
- En-tête : `‹ Aujourd'hui ›` et `Jour | Semaine | Mois`.
- Filtres : un bouton « Filtres » ou « Filtres · 3 » qui ouvre un panneau latéral ; filtres actifs affichés en étiquettes supprimables (« Maintenance × »).
- Plus de formulaire permanent : bouton « + Événement » qui ouvre une modale ou un panneau latéral.

### 20.2 Tickets correctifs

- Le ticket est présenté comme un workflow : frise Signalé → Diagnostiqué → Pièces → Réparation → Essais → Remise en service → Clôture.
- Zone principale : **étape actuelle** et **action suivante** (« Passer aux essais »).
- Fonctions secondaires (assignation, pièces, stock consommé, discussion, historique, REX) accessibles mais pas toutes au même niveau d'importance.

### 20.3 Rondes

Séparer **À faire** et **Historique**. Une ronde en cours passe avant les statistiques et les anciennes rondes.

### 20.4 Quarts et services de garde

- Vues : **Planning** (principale), **Échanges**, **Équité**, **Paramètres**.
- Bouton « + Créneau » qui ouvre un panneau latéral (plus de formulaire permanent).
- En brouillon : badge **BROUILLON** et action **Publier la liste** clairement identifiable.

### 20.5 Matériels et installations

- En-tête : « Matériels — 248 matériels », puis Recherche · Filtres · action principale · `⋯`.
- Filtres actifs en étiquettes supprimables.
- **Sélection multiple** : la barre d'actions groupées n'apparaît qu'après sélection (« 3 éléments sélectionnés — Déplacer · Changer le statut · Exporter · ⋯ ») et disparaît après désélection.
- **Actions individuelles** : plus de boutons Modifier / Supprimer permanents sur chaque ligne, mais un menu `⋯` (modifier, déplacer, dupliquer, archiver, supprimer). Les actions destructives restent secondaires.

### 20.6 Tableaux ou cartes

- **Cartes** quand l'aspect visuel ou physique compte : matériel avec photo, installation, formation, plan du navire.
- **Tableaux** quand il faut comparer des lignes : maintenance, tickets, annuaire, stock, historique, listes administratives.

### 20.7 Formulaires complexes

Les gros formulaires (création complète de matériel, édition d'utilisateur, installation, configuration) ne vont **jamais dans une modale** : page complète, panneau latéral large ou assistant.

### 20.8 Paramètres

Navigation verticale :

- **Organisation** — Unités, Hiérarchie
- **Utilisateurs et droits** — Utilisateurs, Rôles, Responsables
- **Application** — Modules, Notifications, Sécurité (dont délai de déconnexion automatique)
- **Système** — Journal

Les paramètres peuvent être plus denses que les écrans opérationnels.

---

## 21. Recherche globale

Moyen majeur de navigation : installation, matériel, NNO, référence, ticket, anomalie, marin, formation, emplacement. Résultats **regroupés par catégorie**. Raccourci clavier pour y accéder (palette de commandes).

---

## 22. États, chargement et retours

- **États vides** : jamais un simple « Aucun résultat ». Expliquer la situation et proposer l'action pertinente (« Aucun matériel dans ce dossier — Ajouter un matériel »).
- **Chargement** (HTMX) : skeletons légers, indicateurs contextualisés, transitions discrètes ; ne jamais bloquer toute l'interface.
- **Retours** : toute action produit un retour clair et court (« Relevé ajouté », « Liste publiée »). Un toast ne remplace jamais un message d'erreur placé dans le formulaire.

---

## 23. Notifications

- **Centre de notifications** dans la barre supérieure : cloche avec compteur des non lues.
- Liste classée par niveau (**info, attention, danger**) puis par date.
- Chaque notification mène **directement à l'objet concerné**.
- Marquer comme lu individuellement ou en totalité.
- S'appuie sur le modèle `Notification` existant (Web Push pour le niveau danger).

---

## 24. Accessibilité et tablette (option)

- Contrastes conformes en mode clair et sombre ; focus clavier toujours visible.
- `aria-label` sur toute icône seule.
- Option tablette : zones cliquables d'au moins 44 px sur les écrans opérationnels (checklists, relevés) ; aucune information essentielle dépendante du survol.

---

## 25. Règles UX obligatoires

1. Une vue a un objectif principal.
2. Une vue a au plus une action primaire dominante (couleur Signal).
3. L'identité de l'objet est le H1.
4. Les informations qui demandent une action passent avant les informations passives.
5. Les actions secondaires sont contextuelles.
6. Environ cinq onglets de premier niveau au maximum.
7. Les couleurs indiquent l'état, la criticité ou l'action.
8. Bootstrap Icons uniquement, auto-hébergée.
9. Aucun emoji dans l'interface métier.
10. Pas de gros formulaire métier dans une modale.
11. Une card non interactive n'a pas de survol.
12. Saisie en série = grille façon tableur ; objet isolé = assistant ou formulaire simple.
13. Les informations connues ne sont pas redemandées ; les formulaires sont préremplis.
14. Revenir en arrière dans un assistant ne perd aucune donnée ; la dernière étape propose une synthèse métier.
15. Les saisies longues sont enregistrées automatiquement en brouillon.
16. Les actions destructives restent secondaires.
17. L'utilisateur n'a pas à mémoriser la signification d'icônes.
18. L'utilisateur connecté est toujours visible.
19. Toute page s'imprime proprement.
20. Les fonctionnalités non pertinentes à l'instant sont masquées.

---

## 26. Composants

### 26.1 Choix techniques

- Composants = **templates partiels Django** (`{% include %}` ou balises d'inclusion) + **HTMX** + composants **Bootstrap 5** (offcanvas pour le panneau latéral, popover, modale, dropdown pour `⋯`).
- **Aucun framework JavaScript** (pas de React, Vue…). JavaScript limité à de petits scripts sans dépendance (grille de saisie, raccourcis clavier).
- Couleurs exclusivement via variables CSS (§17).
- Une **page de démonstration des composants** (styleguide), accessible aux administrateurs, documente chaque composant.

### 26.2 Liste

PageHeader · Breadcrumb · StatusBadge · Metric · ActionCard · InteractiveCard · Surface · Attention · EmptyState · FilterDrawer · ActiveFilters · ContextMenu · Popover · QuickActionModal · Drawer · Stepper · Wizard · **SaisieGrille** (grille façon tableur) · SelectionBar · Timeline · WorkflowStepper · StickyActionBar · SearchBar · CommandPalette · Toast · Skeleton · ConfirmationDialog · **VersionBanner** (proposer → valider → publier) · **HistoriqueModifications** · **DiscussionDrawer** · **ReadOnlyBanner** · **NotificationCenter** · **ThemeToggle** · **PrintLayout**.

---

## 27. Feuille de route UX

La refonte suit un **parcours séparé** des Phases 0 à 7 du cahier des charges. Dans la base Notion « Tâches en cours », ses tâches portent les étiquettes de phase `UX-0 - Fondations` à `UX-9 - Passe finale` (liste exacte dans `CLAUDE.md`, section « Phases du projet »).

| Phase | Contenu | Priorité |
|---|---|---|
| **UX-0 — Fondations** | Composants (§26), variables CSS et mode sombre, icônes auto-hébergées, hiérarchie des interactions, grille de saisie, brouillons automatiques, styleguide | Critique |
| **UX-1 — Navigation globale** | Barre latérale, barre supérieure (utilisateur visible, déconnexion, notifications, thème), déconnexion automatique configurable | Critique |
| **UX-2 — Aujourd'hui** | Page « Aujourd'hui » bord, lecture seule équipage à terre, vue flotte des utilisateurs à terre | Critique |
| **UX-3 — Maintenance et installations** | Fiche installation, saisie de compte rendu (unitaire et en grille), fiche papier imprimable, mesures, exécution en direct | Critique |
| **UX-4 — Correctif** | Tickets, anomalies, rondes | Haute |
| **UX-5 — Planning** | Calendrier, quarts, gardes | Haute |
| **UX-6 — Équipements** | Matériels, installations, ajout depuis le catalogue, tableaux, sélection multiple, filtres | Haute |
| **UX-7 — Formation** | Catalogue, arbre de compétences, formations | Moyenne |
| **UX-8 — Administration** | Annuaire, paramètres | Moyenne |
| **UX-9 — Passe finale** | 1366×768, impression, accessibilité, cohérence, option tablette, nettoyage des anciennes conventions | Critique avant bêta |

---

## 28. Critères d'acceptation

Une page n'est pas finalisée tant que les critères suivants ne sont pas satisfaits.

### 28.1 Critères vérifiés par le QA

1. **Clics ≤ Excel** — pour chaque tâche de référence de la page (exemple : saisir le contrôle de 20 extincteurs), le nombre de clics et de frappes est inférieur ou égal à celui de la même saisie dans Excel. La tâche de référence et le décompte sont notés dans la tâche Notion.
2. **Test des 5 secondes** — en 5 secondes, on sait où on est, ce qu'on regarde et ce qui demande une action.
3. **Lisible en 1366×768** — aucun défilement horizontal, l'information essentielle et l'action principale sont visibles sans défiler.

### 28.2 Questions de conception

- **Densité** — des éléments visibles pourraient-ils être masqués jusqu'à ce qu'ils deviennent utiles ?
- **Contextualisation** — des actions permanentes pourraient-elles devenir contextuelles ?
- **Navigation** — l'utilisateur doit-il mémoriser une icône ?
- **Formulaire** — pourrait-il être prérempli, simplifié, découpé, conditionnel, ou devenir une grille ?
- **Cohérence** — le comportement existe-t-il déjà ailleurs ? Si oui, réutiliser le même composant.

---

## 29. Vision

Matrix ne doit pas donner l'impression d'être une somme de modules Django. L'utilisateur ne pense pas « je vais dans Maintenance, puis Gestion, puis Occurrences », mais **« qu'est-ce que je dois faire aujourd'hui ? »**, et Matrix lui donne directement le bon écran.

La complexité est absorbée par le logiciel. L'utilisateur ne voit que la part nécessaire à sa tâche du moment.

Matrix est le **cockpit opérationnel du marin** : une application professionnelle, calme, structurée et immédiatement compréhensible malgré sa profondeur fonctionnelle.
