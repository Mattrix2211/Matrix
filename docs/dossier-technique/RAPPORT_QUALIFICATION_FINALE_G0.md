# Rapport de qualification finale — Dossier technique G0

> **Diffusion restreinte.** Date : 12/11/2026. Branche documentaire : `claude/fervent-wright-kl6gtx`. État du logiciel de référence : **état B**, `claude/l03-suppression-sure-v11` @ `6d6d0be`, **non fusionné dans `main`**.
> **Contraintes respectées** : aucun changement du code applicatif ; aucun lot (L04 non lancé) ; `main` non touchée ; aucune PR ni fusion vers `main` ; aucune décision du PO modifiée ; aucune donnée opérationnelle ; aucune modification de classification ni de diffusion. **Je ne déclare pas G0 définitivement validé : cette décision revient au PO.** La diffusion des deux PDF reste soumise à validation de leur classification et de leurs destinataires par l'autorité compétente.

---

## 1. Périmètre réellement vérifié

| Volet | Fait | Non fait |
|---|---|---|
| A14, A20, A25 | Lecture du code de l'état B ; **29 tests ciblés** sur une **copie isolée** de l'état B (base en mémoire, comptes fictifs), fichiers de test **non conservés** dans le dépôt | Aucun essai sur une instance réelle, PostgreSQL, Celery/Redis réels |
| Branche ChatGPT | Examen de ses 4 commits, vérification de chacun, intégration par `cherry-pick` | — |
| Relecture transversale | Contrôles automatiques sur les 42 chapitres-fichiers et 9 annexes ; **relecture de fond ciblée** des passages sensibles des chapitres 5, 6, 7, 11, 12, 16, 17, 20, 22, 23, 25 ; recherche systématique de renvois, termes et mentions de cible | **Pas de relecture mot à mot des 26 chapitres** : les chapitres 8, 9, 10, 14, 15 et les annexes n'ont été relus que par contrôles automatiques et par sondage |
| PDF | Régénération ; contrôles automatiques sur les 246 pages ; inspection visuelle partielle (§6) | Inspection visuelle **exhaustive non réalisée** |

## 2. Corrections effectuées et commits

| Commit | Contenu | Justification |
|---|---|---|
| `333c2e4` | Chapitre 3 : « quatre étiquettes » (titre et encadré) | Le tableau compte 4 étiquettes depuis l'ajout de 🟣 ; texte devenu faux (relecture ChatGPT, **vérifiée**) |
| `7a1115a` | Chapitre 17 : légende à quatre étiquettes, observations de recette distinguées des décisions | Idem (**vérifié**) |
| `26794d9` | Chapitre 6 : mention de la page « Recette UX V1.1 » | La page avait été lue pour le chapitre 17 ; la mention « pas encore lue » était périmée (**vérifié**) |
| `d0b2d57` | Ajout du rapport `REVUE_INDEPENDANTE_G0_2026-11-12.md` | Conservé tel quel comme **document source** de la revue ChatGPT ; ses deux réserves (A14 « à confirmer par test », A20 « à vérifier ») sont **levées par le présent rapport** |
| `e80eb93` | Corrections issues des vérifications (détail ci-dessous) | Voir §3 |
| `8c83d44` | 24 schémas relayoutés, PDF régénérés, outils de contrôle, mise à jour des pages du guide de lecture | Schémas illisibles dans les PDF (§6) |

**Corrections de `e80eb93`**, chacune justifiée par une vérification :
- **Chapitre 6 §6.6, registre A14, synthèse, complément technique** : A14 passe de « non vérifié » à « confirmé par test ».
- **Chapitre 6 §6.9, chapitre 7, chapitre 12, complément du chapitre 7** : l'affirmation « un module désactivé disparaît de l'accueil et du calendrier » était **fausse** (contrôle par grep et par test : seuls menu, recherche et pages web appliquent le filtre).
- **Chapitre 12 §12.4, complément, registre A20, synthèse, schéma S25** : trois sorties de « En validation » et suspension de l'entretien d'une installation ; la phrase « la prochaine échéance de la même gamme est générée indépendamment » était **fausse pour une installation**.
- **Chapitre 12 §12.8** : « tout marin peut exécuter » corrigé (l'assigné, ou un chef de section ou plus ; tout marin peut s'auto-assigner).
- **Chapitre 11 §11.7** : une orientation Notion (« une modification technique devrait entraîner… ») était écrite comme règle ; reclassée ⚪.
- **Chapitre 22 et chapitre 20** : l'API n'est pas soumise à l'activation des modules.
- **Registre A25** : constat complété. `00_LISEZ-MOI.md` : « trois étiquettes » → quatre.

Les rapports déjà livrés (`RAPPORT_E1` à `E4`, `BILAN_FINAL_G0.md`) **n'ont pas été modifiés** : leurs chiffres (105 et 142 pages ; A14 et A20 non vérifiés) sont **remplacés par le présent rapport**.

## 3. Résultats détaillés des vérifications

### A14 — Confidentialité de la passation : **défaut confirmé par test**
- **Code** : `syntheses_visibles` (`dashboard/passation.py:53`) filtre par bâtiment, puis par équipage pour qui peut superviser (seuil de la tâche « attribution », **chef de section par défaut**) ; **aucune borne par section**. `contenu_passation` fige le bâtiment entier. Le code assume : « l'équipage montant lit tout ».
- **Règle du PO** (Notion « 13 — Décisions », recette V1, relue en entier) : « un chef de section ne consulte que sa propre section ».
- **Tests** (8, deux sections, deux équipages, deux bâtiments) : le chef de section d'une section **lit** les tâches, le motif de blocage et l'anomalie de **l'autre section** ; le chef de section de l'équipage sortant lit aussi ; **refusés** : équipier, chef d'un autre bâtiment, chef sans équipage, chef d'un troisième équipage.
- **Qualification** : *défaut confirmé* (écart entre la règle du PO et le comportement observé) ; **aucune fuite réelle alléguée** ; la règle du PO n'est pas modifiée.

### A20 — « En validation » : **blocage confirmé, avec précisions**
Transitions réellement possibles depuis `WAITING_VALIDATION` (18 tests) :
1. **Correction du compte rendu** par un **chef de secteur ou plus**, motif obligatoire : conformité finale conforme → *Terminée*. Un marin (même exécutant) et un chef de section **échouent**. Sans motif : refusée. Reste « non conforme » : l'état ne change pas.
2. **API `start`** (`maintenance/views.py:108`) : écrit « En cours » **sans contrôler l'état de départ**, y compris pour un marin assigné ; l'occurrence reste avec un compte rendu terminé « non conforme » : **état incohérent** (alors comptée en retard) ; une correction par un chef de secteur le répare.
3. **Administration Django** : écriture libre du statut (testé : « Annulée »).
- **Non possibles** : API `complete` (409), modification directe du statut (400), enregistrement en direct, assignation, annulation web ou API (aucune n'existe), tâche de retard, tâche de génération.
- **Notifications** : aucune ne vise l'occurrence (retard et « échéance proche » ne la traitent pas) ; elle reste **visible** en « À faire » (« En attente de validation ») et en supervision.
- **Tickets** : un ticket est créé pour le **matériel mobile** ; sa clôture complète (diagnostic → remis en service → fermé) **ne change pas** l'occurrence. Pour une **installation** : **aucun ticket** et **la génération de l'échéance suivante est suspendue** tant que l'occurrence n'est pas terminée (testé : 1 occurrence avant et après génération ; reprise après correction) ; pour le matériel mobile, la génération continue.
- **Réponse** : oui, une occurrence peut rester **indéfiniment** « En validation » **sans notification, sans échéance, sans escalade** ; elle n'est pas invisible. **Aucune règle nouvelle proposée** : la sortie reste à décider par le PO (D2).

### A25 — Modules désactivés : **constat technique confirmé ; règle attendue non décidée**
Test avec les modules « maintenance » et « logistique » désactivés (3 tests) et audit des routes :
| Surface | Constat |
|---|---|
| Pages web des modules du registre | **134 routes**, toutes à vue-classe : **refusées** (redirection vers l'accueil avec message) ; aucune vue-fonction non protégée |
| Menu, recherche | Entrées et catégories **masquées** (contrôle avec module actif puis inactif) |
| **API** | **Lecture et écriture accessibles** (liste, démarrage d'une occurrence, transition d'un ticket : 200) |
| **Administration Django** | Accessible (200) |
| **Tâches planifiées** | Notifications de retard et de stock **créées**, échéances **générées** |
| **Enchaînement interne** | Maintenance non conforme → ticket **créé** |
| **Accueil « À faire », calendrier** | **Continuent d'afficher** les maintenances, avec lien vers une page refusée |
- Le code l'écrit (middleware limité aux chemins hors `/api/` et `/admin/`) : c'est un **choix explicite** pour ne pas casser les enchaînements. **La règle métier attendue** (masquer l'interface seulement, ou aussi bloquer API et tâches) **n'est pas décidée** ; rien n'a été corrigé.
- Le commentaire de code « COMMANDANT par défaut » pour `module_gestion` est périmé : le seuil réel est le niveau de vision du commandement (commandant en second ; annexe B exacte).

## 4. Tests réellement exécutés
| Série | Tests | Résultat |
|---|---|---|
| A14 (copie isolée de l'état B) | 8 | OK |
| A20 (idem) | 18 | OK |
| A25 (idem) | 3 | OK (constats imprimés) |
| Audit des routes (script de lecture) | 1 | 134 protégées, 0 non protégée |
Total **29 tests OK** ; base en mémoire, comptes fictifs, fichiers de test **non versionnés**. **Non rejoués** : la suite complète de 3 963 tests ; les tests de l'ensemble 4 (1 434 OK) datent de la veille.

## 5. Contrôle des chapitres, annexes et schémas
| Contrôle | Résultat |
|---|---|
| 26 chapitres, 8 annexes (+ H bis) | Présents, structure homogène |
| Références de code (fichier, ligne, symbole) | **1 105, 0 erreur** |
| Cohérence (étiquettes, liens, chiffres, secrets) | **51 fichiers, 0 erreur** |
| Séparation diffusable / restreint | **0 violation** |
| Revue transversale | **0 erreur** : paquets, 135 modèles, tâches, commandes, routes web, circuits couverts |
| Renvois « chapitre N », « §N.N », « annexe X » | **0 renvoi cassé** |
| Identifiants `DEC-…` | 70 cités, 70 existent |
| Cible écrite comme existante | Quatre erreurs corrigées (§2) ; aucune autre relevée dans les chapitres relus |
| Terminologie Marine (COMA, COMAEQ, COMANAV, COMOPS, COMAVIA, BSC…) | Cohérente avec les pages Notion 07 et 13 ; aucun terme interdit (« chef de groupement », « CAN ») |
| Schémas | **42 sur 42** exportés, référencés, indexés et retrouvés (légende) dans les PDF ; S25, S30, S31 mis à jour avec les constats |
| Explications trop techniques pour un marin | Peu de jargon dans les fichiers diffusables (0 à 3 occurrences par chapitre) ; **jugement de lisibilité non éprouvé** auprès de lecteurs réels |

## 6. Contrôle des deux PDF
- **Régénération** : diffusable **105 pages**, restreint **141 pages** (dont 56 en paysage), avec couverture, sommaire cliquable, signets, bandeau de diffusion et pagination.
- **Contrôles automatiques sur toutes les pages** : aucune page sans texte ; aucun texte au bord ou hors page ; les quatre étiquettes 🟢🔵🟣⚪ sont présentes dans le texte extrait des deux PDF ; aucune référence de code, variable d'environnement, commande ni adresse dans le PDF diffusable ; aucune mention « diffusion générale » dans le PDF restreint.
- **Défauts trouvés et corrigés grâce à l'inspection** : 24 schémas rendus en bandeaux illisibles (rapport largeur/hauteur jusqu'à 55) → relayoutés (aucun contenu changé) ; mots coupés dans les colonnes étroites des tableaux ; **listes Markdown rendues en paragraphe** (une ligne vide manquait) → corrigé dans le générateur.
- **Inspection visuelle réellement faite** : page de garde, pages de plusieurs chapitres, feuilles de schémas S01 à S06 (avant relayout), S19 à S24 et S25 à S30 (après relayout), une page de tableau et de liste après correction, une mosaïque basse résolution du PDF restreint.
- **Inspection visuelle NON faite** : les feuilles de schémas S07 à S18 et S31 à S42 **après** relayout, les mosaïques du PDF diffusable, la plupart des annexes en paysage. **Je ne déclare donc pas l'inspection visuelle réussie.** La vérification des 42 schémas est **automatique (présence) et partielle (lisibilité)**.
- **Limites connues** : une page du PDF restreint (chapitre 15, complément) ne contient que la ligne « Sources » (débordement d'une ligne) ; le schéma S01 reste large (rapport 4,6) ; le sommaire n'a pas de numéros de page (signets et liens à la place) ; sauts de page non relus un par un.
- **Diffusion** : mention conservée en couverture : « La séparation n'est pas une autorisation de diffusion : la classification et les destinataires restent à valider par le PO ». Aucune classification modifiée.

## 7. Écarts et décisions PO restant ouverts (non modifiés)
**26 écarts** (A1 à A26) ; **8 points à confirmer** (B1 à B8) ; **7 propositions** (D1 à D7). Statuts mis à jour par ce rapport : **A14 confirmé par test**, **A20 confirmé et précisé**, **A25 confirmé (règle attendue non décidée)**. Tous les autres sont inchangés, dont les plus lourds : A1, A2, A3, A4, A15, A17, A23, A24. Aucune décision du PO n'est modifiée ; aucune correction de code n'est demandée ni engagée.

## 8. Conclusion
**Prêt avec réserves** pour la validation du PO.

Réserves :
1. **Inspection visuelle des PDF incomplète** (§6) : le PO relira les PDF ; les schémas S07 à S18 et S31 à S42 relayoutés sont à regarder en priorité.
2. **Relecture de fond non exhaustive** : chapitres 8, 9, 10, 14, 15 et annexes relus par contrôles automatiques et sondage seulement.
3. **Lisibilité non éprouvée** auprès d'un marin, d'un responsable et d'un développeur.
4. **Suite complète de 3 963 tests non rejouée** ; tests de vérification limités aux trois écarts.
5. **Classification et destinataires** des deux PDF à valider par l'autorité compétente avant toute diffusion.

Le dossier ne vaut ni recette, ni homologation, ni autorisation de diffusion. Je m'arrête ici et j'attends votre validation.
