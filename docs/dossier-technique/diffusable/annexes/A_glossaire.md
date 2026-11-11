# Annexe A — Glossaire Marine et Matrix

> **Diffusion :** générale. **Édition :** ensemble 1 (11/11/2026) ; complétée à chaque ensemble.
> **Comment l'utiliser :** les définitions viennent des pages Notion de référence (Organigramme et rôles, pages 06, 07, 12 et 13) et du code de l'état B. Les termes marqués ⚪ n'ont pas de définition sourcée dans les documents consultés : ils sont donnés tels qu'employés, **sans être complétés de mémoire**. Le vocabulaire d'usage fourni par le PO n'est pas une norme réglementaire.

---

## A.1 Les cinq notions de droits (à ne jamais confondre)

| Terme | Définition dans Matrix |
|---|---|
| **Grade** | Rang de la personne. N'ouvre aucun droit métier à lui seul. |
| **Fonction (exercée)** | Ce que la personne fait réellement : chef de liste, BSC, COMAEQ, fonction de service ou de quart. Une fonction est un poste de service, pas un grade. |
| **Rôle** | Profil d'accès dans Matrix, parmi neuf, ordonnés du plus bas au plus haut : équipier, chef de section, chef de secteur, chef de service, état-major, commandant en second, commandant, administrateur d'unité, administrateur général. |
| **Périmètre** | Ce sur quoi la personne agit : sa section, son secteur, son service, son bâtiment. Déduit du rattachement le plus fin renseigné sur son profil. |
| **Brevet / qualification / habilitation** | Ce que la personne est qualifiée pour faire (formation). Informatif pour les tâches ordinaires ; les exigences réglementaires restent respectées pour les visas, fonctions de service et signatures officielles. |

## A.2 Termes de Matrix

| Terme | Définition |
|---|---|
| **État A / État B** | Deux états du code décrits par ce dossier : A = `main` (`6ef16ad`, V1 FANLAB) ; **B = `claude/l03-suppression-sure-v11` (`6d6d0be`), référence principale, non fusionné dans `main`**. |
| **🟢 Actuel / 🔵 Cible / ⚪ Non vérifié** | Étiquettes du dossier : existe dans le code ; décidé par le PO mais non développé ; non confirmé. |
| **Lot (L01 à L28)** | Unité de travail du plan de développement V1.2. L01, L02, L03 et L05 sont livrés **sur la branche B** ; les autres ne sont pas lancés. |
| **DEC-…** | Identifiant d'une décision du PO dans le registre du dossier V1.2 (125 décisions). |
| **Seuil de rôle** | Rôle minimal requis pour une action ; réglable par bâtiment. |
| **Module activable** | Ensemble de pages que chaque bâtiment peut masquer, sans supprimer de données. 14 sont activables. |
| **Unité** | Bâtiment, école, centre de formation ou bureau : premier niveau de la hiérarchie. |
| **Archiver / supprimer (une unité)** | Archiver : retirer de la vie courante en conservant tout. Supprimer : possible seulement si plus rien ne la référence. |
| **Relève (d'équipage)** | Changement de l'équipage à bord d'un bâtiment à double équipage : proposée par un commandant, validée par l'autre équipage. |
| **Synthèse de passation** | Document généré à la relève, au profit de l'équipage montant. Activée par défaut, désactivable. |
| **Journal d'audit** | Enregistrement de qui a fait quoi, quand, sur quoi. |
| **Proposer → valider → publier** | Principe des modifications sensibles : la version publiée reste active jusqu'à validation de la suivante ; chaque version est conservée. |
| **Soutien à terre** | Personnel sans bâtiment (responsable de classe, de spécialité) : il consulte et commente, il n'écrit que dans les circuits prévus. |
| **Équipage à terre** | Équipage d'un bâtiment à double équipage qui n'est pas à bord : lecture seule du bâtiment, sa propre feuille de service. À ne pas confondre avec un organisme de soutien. |
| **Chef de liste** | Marin désigné pour préparer les listes de quarts et de gardes. Ce n'est pas un rôle. |
| **Référent de formation** | Marin habilité à valider les formations ; indépendant du rang. |
| **Annuaire** | Écran de gestion des comptes, visible à partir du commandant en second. |
| **Réglages (Paramètres)** | Écran de configuration, dont les onglets dépendent des droits. |

## A.3 Fonctions et organisation du bord

| Terme | Définition (source) |
|---|---|
| **COMA** (commandant adjoint) | Niveau d'organisation configurable : COMAEQ, COMOPS, COMANAV, COMAVIA selon le bâtiment. Chaque service est rattaché à son COMA compétent ; les circuits retrouvent ce rattachement au lieu d'un « état-major » générique. |
| **COMAEQ** | Vie à bord, service courant, coordination du personnel à quai ; adjoint protection ; conduite nautique en liaison avec le COMOPS. Vise la feuille de service. |
| **COMOPS** | Opérations, conduite des opérations, activité à la mer, analyse et comptes rendus opérationnels. |
| **COMANAV** | Conservation du bâtiment et de ses équipements ; adjoint sécurité ; gestion technique des matériels et logistique opérationnelle. |
| **COMAVIA** | Aviation et sécurité aérienne, sur les unités concernées. |
| **Commandant en second** | Remplaçant désigné du commandant ; coordonne les COMA et les services ; chef des organisations sécurité et protection. Vision globale dans Matrix ; écritures limitées aux responsabilités attribuées. |
| **Chef de service / de secteur / de section** | Encadrent respectivement un service, un secteur, une section. Le secteur est l'échelon responsable lorsqu'il n'y a pas de section. |
| **BSC** | Bureau du service courant : orchestration quotidienne et documents du service courant (prévisions d'activité, roulement du service, mouvements de personnel…). Prépare la feuille de service ; **n'est pas une autorité parallèle au COMAEQ**. |
| **Service courant** | Vie quotidienne du bord : personnel, mouvements, horaires, tâches collectives, gardes, consignes. |
| **Tableau de service** | Cadre permanent du service selon la situation (à quai, mer ou mouillage, escale). |
| **Feuille de service** | Déclinaison quotidienne qui complète le tableau de service ; point de convergence du jour J. Distincte des tableaux de quart à la mer. |
| **Fraction de service** | Ensemble de marins désignés pour assurer la garde du bâtiment sur une période. |
| **Service à quai, garde, quart** | Notions distinctes, à ne pas confondre. |
| **OG** | Officier de garde : délégation du commandant, responsabilité générale du bâtiment et de la fraction pendant la garde (exemple BRF). |
| **OPSC** | Officier de permanence service courant (exemple BRF). |
| **OPN** | Officier de permanence navire ; assure aussi la fonction DDI dans l'exemple BRF. |
| **DDI** | Directeur d'intervention (dans l'exemple BRF, exercé par l'OPN pendant le service). |
| **Gradé de coupée, gradé mécanicien, gradé électricien, gradé sécurité** | Fonctions de la fraction de service dans l'exemple BRF ; une fonction n'est pas un grade. Les gradés de coupée organisent eux-mêmes leurs relèves. |
| **Adjudant de compagnie** | Fonction attribuée à une personne : relais d'encadrement et de suivi de proximité. Reconnue dans le référentiel métier (31/10/2026) ; **pas un grade ni un droit général** ; non implémentée. |
| **OSS** | Officier de sécurité du service : fonction complémentaire auprès du chef de service (consignes, contrôles et formations de sécurité). À ne pas confondre avec l'officier de sécurité chargé du secret ni l'OSSI. Reconnue ; non implémentée. |

## A.4 Vocabulaire des quarts

> Ces définitions sont celles du PO (31/10/2026), prises pour **références de travail**, pas comme normes nationales. Les grilles varient selon l'unité et la situation.

| Terme | Définition |
|---|---|
| **Quart à la mer** | Roulement horaire distinct du service à quai. Régimes possibles : **par bordées** (2), **par tiers** (3), **au quart** (4), **au cinquième** (5), **au sixième** (6). |
| **Sept créneaux** | Journée organisée autour de 00–04, 04–08, 08–12, 12–15, 15–18, 18–20, 20–24, dans l'exemple documenté. |
| **De musique** | Nuit complète sans quart (20 h–08 h). Ce n'est ni un poste ni une quatrième plage de nuit. |
| **Homme mort** | Marin qui n'effectue aucun quart de la journée ni de la nuit sur le roulement considéré ; il peut avoir d'autres obligations. **Pas synonyme de « musique ».** Vocabulaire d'usage. |
| **Tiers, bordée** | Équipes qui se relaient dans un roulement (trois, deux). |

## A.5 Organismes et sigles externes au bord

| Sigle | Signification (page Notion 12) |
|---|---|
| **ALFAN** | Autorité organique de la FAN : disponibilité, préparation, entraînement et qualification des unités de surface |
| **ALFAN/EXPL** | Exploitation, expertise métier et retour d'expérience selon domaines |
| **ALFAN/ENT** | Entraînement et préparation opérationnelle |
| **DIVENT** | Division entraînement d'ALFAN |
| **SSF** | Service de soutien de la flotte : pilotage du maintien en condition opérationnelle (MCO) naval |
| **IRB** | Ingénieur responsable bâtiment (SSF), au contact d'un ou plusieurs bâtiments ; correspond au « responsable de classe » de Matrix |
| **ERO** | Équipe responsable d'opération : conduite d'opérations MCO ou de familles de bâtiments |
| **ERDT / IRDT** | Équipe responsable de domaine technique ; responsable d'une ERDT : expertise transverse |
| **SLM** | Service logistique de la Marine : ateliers, rechanges, transports, soutien technique |
| **CEPN** | Centre d'expertise des programmes navals |
| **CFPES** | Centre de formation pratique et d'entraînement à la sécurité |
| **FPS** | Flottilles de perfectionnement du surfacier |
| **DIRISI** | Direction interarmées des réseaux d'infrastructure et des systèmes d'information |
| **CMC2** | Centre Marine du combat cyber |
| **SCA / commissariat** | Soutien de l'homme, administration, vivres, finances, vie commune, soutien courant |
| **CPPE** | Commission permanente des programmes et des essais : sécurité maritime et caractéristiques militaires |
| **DPM** | Direction du personnel de la Marine : RH, parcours, affectations, compétences, formation |
| **SIC** | Systèmes d'information et de communication (cyber, réseaux) |
| **Responsable de classe** | Dans Matrix : correspond à l'**IRB**. Désignation à l'échelle de la flotte. |
| **Responsable de spécialité** | Rôle métier rattaché à ALFAN Exploitation ; n'englobe pas tous les bureaux d'ALFAN. |
| **Organisme à terre** | Cible : unité pouvant comprendre divisions, bureaux, cellules et personnel. Plus large qu'IRB et ALFAN Exploitation. |
| **PÉPIN, CRAT, RAV/c** | Messages et procédures officielles évoqués par le PO. **Leur développé, leurs destinataires et leurs circuits de validation ne sont pas établis** ; à ne pas déduire. |
| **Circuit d'information** | Règles de rédaction, contrôle, visas, transmission, diffusion, traitement, réponse et clôture. Distinct de l'organigramme. |

## A.6 Autres termes

| Terme | Définition |
|---|---|
| **MCO** | Maintien en condition opérationnelle. |
| **RETEX** | Retour d'expérience. |
| **GMAO** | Gestion de maintenance assistée par ordinateur : un module de Matrix, pas Matrix. |
| **NNO** | Numéro de Nomenclature OTAN : référence militaire standard identifiant une pièce de façon univoque (libellé du champ du stock ; champ facultatif, texte libre). Présent sur le matériel, le catalogue et le stock. |
| **VAPID / Web Push** | Clés et mécanisme d'envoi de notifications au navigateur, auto-hébergés. |
| **Mot de passe provisoire** | Mot de passe généré à la réinitialisation, affiché une seule fois, à remplacer à la première connexion. |
| **Instance de démonstration** | Base fictive isolée, marquée comme telle ; ne démarre jamais en production. |
| **Prêt à appareiller** | Session de préparation de l'appareillage (chapitre 16). Matrix n'autorise pas l'appareillage. |

---

**Sources.** Notion : « Organigramme et rôles », « 06 — Service courant, BSC, feuille de service et commissariat » (31/10/2026), « 07 — SIC, cyber, protection-défense et conformité », « 12 — Glossaire et responsabilités des organismes externes au bord » (21/10/2026), « 13 — Décisions Matrix et gouvernance fonctionnelle ». Code de l'état B : `accounts/models.py:11`, `matrix/core/roles.py:4`. Ces pages Notion portent l'état « non vérifié ».
