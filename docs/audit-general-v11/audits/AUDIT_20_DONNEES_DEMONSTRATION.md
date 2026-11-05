# Audit 20 — Qualité des données de démonstration

**Statut : Clôturé avec réserves** (voir « Clôture » en bas du rapport). Périmètre : pipeline complet de génération (`seed_demo`, `seed_demo_mer_quai`, `seed_demo_dense`, `seed_demo_metier`, ≈ 54 s sur SQLite), base **non modifiée** pendant l'audit (lecture seule, sondes `couverture_demo.py`, `credibilite_demo.py`, `demo.py`). Aucune donnée de démonstration n'a été modifiée.

## 1. Crédibilité

| Contrôle | Mesure | Verdict |
|---|---|---|
| Noms de bâtiments | **4 sur 5 sont des noms réels** (Bretagne, Normandie, Jacques Chevallier, Auguste Bénébig) | Non conforme à « données entièrement fictives » (AUD-024, déjà au backlog) |
| Identités | 61 comptes, 50 prénoms et 61 noms distincts ; **34 comptes sur 61 portent une étiquette technique** (« Equipier A », « Cdt A », « Coma Comaeq »…) | Voulu pour la recette, mais peu crédible en présentation ; les 27 autres (jeu dense) ont des noms usuels (non relus un par un) |
| Grades et rôles | commandants capitaines de frégate ; second capitaine de corvette ; COMA lieutenants de vaisseau (4) et capitaine de corvette (1) ; chefs de service maîtres ou capitaines de corvette ; chefs de secteur seconds-maîtres ; équipiers surtout matelots (22 sur 32), avec quelques gradés | Hiérarchie vraisemblable ; **7 grades et 3 spécialités seulement** ; aucune fonction de service renseignée ; 8 comptes sans grade (comptes techniques) |
| Mots de passe | 60 comptes en « pass », 1 en « admin » | Voulu pour la démonstration ; risque de production (AUD-009) |
| Effectifs | 36 marins à Bretagne (FREMM) | Faible mais suffisant pour l'écran ; non représentatif d'un effectif réel |
| Dates | créneaux de quart du 2026-11-01 au 2026-12-09 autour du jour de la mesure (2026-11-05) ; 10 tâches en retard ; échéances relatives | Cohérent et rejouable (génération relative au jour) ; non testé dans le temps |

## 2. Diversité et organisations

Cinq bâtiments de formes différentes (un ou deux équipages ; un à quatre services ; zéro à trois commandants adjoints ; modes MER, QUAI et non renseigné) : détail et lecture dans `AUDIT_19_COHERENCE_MARINE.md` §3. **Absents** : COMAVIA, secteur sans section, marin transversal, bâtiment à terre, second absent, compte désactivé (0 sur 61).

## 3. Cohérence interne

- Chaque compte du pipeline complet est rattaché à un équipage si le bâtiment est à double équipage, et à un service, secteur ou section s'il n'est pas du commandement (0 exception).
- **AUD-008** : avec `seed_demo` seul, un ticket est assigné à un chef qui ne peut pas l'ouvrir ; **le pipeline complet corrige ce cas** mais l'anomalie de classe subsiste (liens d'anomalies liées).
- `seed_demo` seul est incohérent avec la recette (42 comptes, aucun échange) : **seul le pipeline complet est la démonstration de référence**.
- 1 service sans commandant adjoint (BordOps I) ; 2 pièces de stock à quantité nulle sur 11 ; aucun stock sous le seuil d'alerte.

## 4. Matrice de couverture par module et par profil (données propres du profil)

Chaque cellule est le nombre d'objets du module **dont le profil est titulaire ou destinataire** (créneaux comme marin, échanges comme demandeur ou cible, notifications reçues, annonces lues, désignations de chef de liste, rédacteur ou référent). `0` = **espace vide** pour ce module : le profil n'a rien à y voir en démonstration.

| Profil | Rôle | Tâches | Maint. | Tickets | Quarts | Gardes | Échanges | Absences | Qualif. | Notif. | Annonces lues | Postes | Brouillons | Désign. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `equipier_a` | matelot (équipage A) | 6 | 5 | 9 | 50 | 3 | 1 | 1 | 1 | 93 | 5 | 0 | 1 | 0 |
| `equipier_a2` | matelot BSC, rédacteur | 2 | 1 | 0 | 51 | 3 | 1 | 1 | 0 | 86 | 5 | 0 | 0 | 1 |
| `marin_b` | équipage B, rédacteur | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 29 | 5 | 0 | 0 | 1 |
| `chef_section_a` | chef de section | 0 | 0 | 0 | 13 | 6 | 0 | 1 | 0 | 56 | 5 | 0 | 0 | 0 |
| `chef_secteur_a` | chef de secteur, chef de liste | 0 | 0 | 1 | 31 | 3 | 0 | 0 | 0 | 83 | 5 | 0 | 0 | 5 |
| `chef_service_a` | chef de service | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 47 | 5 | 0 | 0 | 0 |
| `coma_comaeq` | COMAEQ | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 50 | 5 | 0 | 0 | 0 |
| `coma_comanav` | COMANAV | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 | 54 | 5 | 0 | 0 | 0 |
| `coma_comops` | COMOPS | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 56 | 5 | 0 | 0 | 0 |
| `second_a` | second | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 14 | 5 | 0 | 0 | 0 |
| `cdt_a` | commandant A | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 42 | 0 | 0 | 0 | 0 |
| `admin_navire` | administrateur d'unité | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 49 | 5 | 0 | 0 | 0 |
| `terre_classe` | suivi de classe à terre | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `marin_abe_1` | matelot, bâtiment ABE | 0 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 |
| `cdt_abe` | commandant ABE | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| `m_chevalier` | marin du jeu dense | 1 | 0 | 0 | 10 | 0 | 0 | 1 | 0 | 39 | 5 | 0 | 0 | 0 |

**Lecture** : seuls le matelot `equipier_a` et dans une moindre mesure `equipier_a2` et `chef_secteur_a` ont un espace personnel riche (tâches, maintenance, tickets, quarts, échange, qualification, brouillon). **Cinq profils n'ont aucune donnée propre sauf des notifications** (chef de service, COMAEQ, commandant, administrateur d'unité, second) ; **`terre_classe` n'a aucune donnée personnelle ni notification** ; aucun profil n'a de **poste** affecté parmi ceux sondés (5 postes et 9 affectations existent pour d'autres marins) ; `cdt_a`, `cdt_abe` et `marin_abe_1` n'ont presque rien. Les vues de supervision (accueil des chefs, vue COMANAV) fonctionnent sur les données du bâtiment, pas sur ces comptes.

## 5. Couverture des états (machines à états)

| Objet | États présents | États **absents** de la démonstration |
|---|---|---|
| Ticket correctif | REPORTED, DIAGNOSED, WAITING_PARTS, IN_REPAIR, TESTING, BLOCKED, CLOSED | **PLANNED, RETURNED_TO_SERVICE** (remise en service avec confirmation), CANCELLED |
| Occurrence de maintenance | tous (PLANNED, ASSIGNED, IN_PROGRESS, WAITING_VALIDATION, DONE, OVERDUE, CANCELLED) | aucun |
| Tâche | à faire, en cours, bloquée, terminée | aucun |
| Échange de service | tous (demande, accepté, validé, refusé, rejeté, annulé) | aucun |
| Liste de quart | publiée, brouillon | **proposée** |
| Liste de garde | publiée, proposée, brouillon | aucun |
| Feuille de service | **publiée (1)** | **brouillon, visa chef de secteur, visa chef de service, visa COMAEQ** : le circuit en cours n'est pas montré |
| Anomalie | signalée, prise en compte, traitée, clôturée | aucun |
| Difficulté signalée (demande) | ouvert, en traitement | **en attente d'information, résolu, clos** |
| Version de document | publiée, soumise, brouillon | **refusée, obsolète** |
| RETEX | proposé, validé | **refusé, clos** |
| Candidature de formation | **aucune** | **les 6 états** : en attente d'approbation, transmise, sélectionnée, 3 refus |
| Relève de double équipage | en attente (1) | **planifiée, validée, refusée, annulée** |
| Annonce | information, important | **urgent** |
| Notification, absence | tous niveaux, tous types | aucun |

## 6. Cas limites exercés ou non

| Cas limite | Exercé ? |
|---|---|
| Double équipage A/B, équipage à terre | oui |
| Échange dans tous ses états | oui |
| Tâche bloquée avec motif | oui (7) |
| Remplacement de chef de liste actif | oui (1) ; **expiré ou révoqué : non** |
| Mode MER, QUAI | oui ; mode non renseigné : oui (2 bâtiments) |
| Accents et caractères spéciaux dans les noms | oui |
| **Secteur sans section** | **non** |
| **Marin transversal, marin sans rattachement** | **non** |
| **Poste de COMAEQ vacant** | non (variante exécutée par l'audit seulement) |
| **COMAVIA** | non |
| **Compte désactivé, départ d'un marin** | non |
| **Suppression ou archivage d'une unité** | non |
| Stock sous le seuil d'alerte | **non** |
| Échéances dépassées | oui (10 tâches, 8 maintenances) |

## 7. Scénarios manquants (à ajouter à la démonstration **après autorisation du PO**)

1. Feuille de service **en cours de visa** (brouillon, puis chacun des trois paliers) pour montrer le circuit, et une feuille d'un équipage à terre.
2. Ticket **remis en service** (confirmation explicite) et ticket annulé.
3. Candidature de formation dans chaque état, avec refus hiérarchique et BRH.
4. Relève planifiée et validée ; relève annulée avec justification.
5. Difficulté résolue et close ; RETEX refusé et clos ; version de document refusée et obsolète.
6. Annonce « urgent » avec accusé requis.
7. Stock sous seuil d'alerte (pour l'alerte planifiée) et pièce en rupture liée à un ticket.
8. Secteur sans section avec marins rattachés ; marin transversal avec fonction ; marin sans rattachement (compte « à compléter »).
9. Bâtiment avec COMAVIA ; poste de COMAEQ vacant ; second absent.
10. Compte désactivé ; départ d'un marin avec historique.
11. Remplacement de chef de liste expiré et révoqué.
12. Noms de bâtiments fictifs (AUD-024) et identités vraisemblables pour tous les comptes de présentation.
13. Espace personnel non vide pour le suivi à terre, le commandant et le COMAEQ (tâches ou rappels propres).

## 8. Anomalies liées

AUD-008, AUD-009, AUD-024, **AUD-036** (couverture insuffisante de la démonstration).

## Clôture (4ᵉ passe et addendum)

**Statut : Clôturé avec réserves.** L'analyse est achevée sur les cinq critères demandés (crédibilité, diversité, cohérence, couverture fonctionnelle, cas limites) ; matrice de couverture et scénarios manquants produits.

### Non vérifié ou dépendant d'une validation externe

Fidélité aux usages réels (expert du bord) ; `lancer_demo.bat` sous Windows ; comportement des dates relatives dans le temps ; couverture par module de **données secondaires** non sondées (documents par bâtiment, programme, fiches de maintenance, rondes retirées).
