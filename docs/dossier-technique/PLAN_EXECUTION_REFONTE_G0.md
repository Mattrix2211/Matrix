# Plan d'exécution — Refonte documentaire G0

> **Document provisoire — diffusion restreinte.** Date : 13/11/2026. Branche : `claude/fervent-wright-kl6gtx`. Base de référence de l'audit : commit `637de94`. État applicatif décrit : état B (`6d6d0be`).
> **Statut : plan soumis à validation du PO. Rien n'est commencé.** Ce plan ne vaut ni validation du dossier, ni validation logicielle, ni autorisation de diffusion.
> **Contraintes** : aucun changement du code applicatif ; `main` intacte ; aucune fusion ni PR ; aucun nouveau lot ; aucune diffusion externe ; les 29 tests A14/A20/A25 restent dans `audit_preuves/` ; A1–A26 et NE-01 à NE-06 restent des écarts documentés, jamais des autorisations de modifier le logiciel.

---

## 1. Décisions du PO prises en compte

| # | Décision | Conséquence directe dans ce plan |
|---|---|---|
| 1 | Architecture du §J.3 retenue | Cinq livrables (§3) : guide utilisateur illustré, référentiel fonctionnel et de gouvernance, dossier technique de reprise, annexes consultables hors PDF, registre vivant |
| 2 | Mention provisoire restrictive partout ; chemins de code, branches, éléments techniques sensibles réservés aux documents techniques à accès restreint | Mention unique sur **chaque page** ; le mot « diffusable » disparaît des noms de fichiers, des titres et des en-têtes ; les deux documents non techniques deviennent « sans référence de code » (contrôle automatique C5) |
| 3 | Les 29 tests restent dans les preuves versionnées | Aucun fichier de test n'entre dans le dépôt applicatif ; le registre cite leur chemin dans `audit_preuves/` |
| 4 | A1–A26 et NE-01 à NE-06 = écarts documentés | Le registre vivant les porte avec un statut « documenté, non arbitré » |

**Mention provisoire (texte unique, injecté partout)** :
> DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE. Classification et destinataires en attente de validation de l'autorité compétente. Ne pas diffuser.

---

## 2. Principe pour ne régénérer les PDF qu'une fois

Tous les défauts P0/P1 sont corrigés **dans les sources**, sur un aperçu HTML et par des contrôles automatiques, **avant** toute génération de PDF. Les PDF ne sont construits qu'après la barrière G1 (§6). Ensuite :
- **1 construction « candidate »** des trois PDF ;
- inspection à taille réelle ;
- corrections dans les sources puis **reconstruction du seul document touché** (les trois documents sont indépendants) ;
- budget : **au plus 2 reconstructions par document** après la candidate ; au-delà, arrêt et rapport au PO.
Un **chapitre pilote** (module Maintenance, présent dans les trois documents) est produit en PDF dès la phase 3 pour valider la maquette **avant** la rédaction en masse : c'est la seule génération PDF anticipée, jetable.

---

## 3. Livrables exacts

Convention : racine `docs/dossier-technique/refonte/` (nouvelle arborescence ; les sources actuelles `diffusable/`, `restreint/`, `schemas/`, `guide-visuel/` restent **intactes** jusqu'au basculement de la phase 13).

### D1 — Guide utilisateur illustré (public : marin, chef)
- `refonte/1_guide_utilisateur/*.md` (sources) ; PDF : `pdf/Matrix_G0_1_Guide_utilisateur_PROVISOIRE_RESTREINT.pdf`.
- Contenu : « Matrix en une page » ; une partie par profil (marin, chef de section, chef de secteur, chef de service) ; **parcours d'abord** (journée, tâche, maintenance et compte rendu, anomalie et ticket, tour de service, échange de tour, annonce à accuser, recherche, appareillage) ; écrans de référence par module ; limites visibles de l'état B ; glossaire minimal ; index des termes.
- Reprend et étend le guide visuel de 39 pages (captures refaites, §P4) ; **aucune référence de code** ; fonctions 🔵 et 🟣 jamais montrées comme disponibles.
- Taille cible : **60 à 75 pages**, A4 paysage pour les pages de capture, portrait pour le texte.

### D2 — Référentiel fonctionnel et de gouvernance (public : responsable, commandement, décideur)
- `refonte/2_referentiel_fonctionnel/*.md` ; PDF : `pdf/Matrix_G0_2_Referentiel_fonctionnel_PROVISOIRE_RESTREINT.pdf`.
- Contenu : **résumé décideur de 2 pages** (valeur, maturité par module, limites, décisions en attente) ; lire ce document (étiquettes 🟢🔵🟣⚪, état B sans identifiant de commit) ; organisation et rôles avec **fiche de rôle** d'une page par rôle ; **une fiche de module** par module (modèle imposé : à quoi ça sert ; qui fait quoi ; écran de référence ; règles ; circuit (schéma) ; actuel / cible ; limites et écarts ; décisions) ; fonctionnement cible et feuille de route sans noms de branches ; glossaire (reprise de l'annexe A) et index.
- Matrice rôle × action **en libellés** (sans clés de code).
- Taille cible : **90 à 110 pages**.

### D3 — Dossier technique de reprise (public : développeur, mainteneur, exploitant ; accès restreint)
- `refonte/3_dossier_technique/*.md` ; PDF : `pdf/Matrix_G0_3_Dossier_technique_reprise_PROVISOIRE_RESTREINT.pdf`.
- Contenu : **prise en main développeur** (nouveau : installer, lancer, tester, ajouter une action de seuil, un module activable, une tâche planifiée — chaque pas exécuté dans une copie isolée avant d'être écrit) ; **recette de déploiement** (checklist du chapitre 23 enrichie : QR et nom d'hôte (NE-04), proxy TLS (NE-03), sauvegarde minimale à définir avec les SIC) ; architecture, données, API, interactions, sécurité, exploitation, qualité ; **un chapitre technique par module** fusionnant chaque chapitre technique actuel (`4T` à `17T`) ; historique des branches et des lots (ancien 26T, F.4) ; renvoi aux preuves (`audit_preuves/`).
- Annexes dans le PDF : totaux, méthode et extraits seulement ; le détail passe en D4.
- Taille cible : **110 à 130 pages**.

### D4 — Annexes consultables hors PDF
- `refonte/4_annexes_consultables/` : `index.html` (**un seul fichier autonome**, hors ligne, sans CDN ni police distante, tri et filtre en JavaScript local) ; données `*.csv` (UTF-8, séparateur `;`) ; bandeau de mention provisoire dans chaque fichier.
- Tables : matrice rôle × action (clés de code, accès restreint), index des routes (721), index des modèles (135), tâches, commandes et variables, matrice de couverture, **registre des éléments non vérifiés** (ancien F.5, refait en tableau : document, section, point, étiquette), index des schémas.
- Générées par les outils existants étendus (`generer_annexe_b.py`, `generer_annexes_e4.py`, `generer_annexe_f.py`, `generer_matrice_couverture.py`).
- Accès restreint (elles contiennent des chemins de code).

### D5 — Registre vivant des écarts et décisions
- Source unique **`refonte/5_registre/registre.json`** (une entrée par élément) ; vues générées : `ECARTS_ET_DECISIONS.md`, `registre.html`, PDF court (`pdf/Matrix_G0_5_Registre_ecarts_decisions_PROVISOIRE_RESTREINT.pdf`, 15 à 25 pages).
- Entrées : A1–A26 ; B1–B8 ; D1–D7 ; NE-01 à NE-06 ; anomalies documentaires AUD actives ; **125 décisions** du dossier V1.2 avec état (réalisée, partielle, non développée, non traitée dans ce dossier) — fin des plages « DEC-X-01 à 11 ».
- Champs : identifiant, nature (écart logiciel, écart documentaire, point à confirmer, proposition), règle ou décision, constat, preuve et niveau (§0.1 de l'audit), **profils concernés** (P1-7), conséquences, lot, statut, **dernière vérification (date, commit)**.
- Règle de vie : une modification = un commit daté ; l'historique d'un statut reste lisible ; aucune entrée ne devient « décision » sans mention du PO.

### Documents d'accompagnement
- `refonte/README_DOSSIER.md` (point d'entrée unique : qui lit quoi, versions, état) ; remplace `00_LISEZ-MOI.md` et `GUIDE_DE_LECTURE.md` (conservés dans l'archive).
- `refonte/MAPPING_ANCIEN_NOUVEAU.csv` : **chaque** titre de section des 26 chapitres, 8 annexes, 42 schémas → emplacement dans la nouvelle structure ou « retiré » avec motif.
- `refonte/RAPPORT_RECETTE_REFONTE.md` : résultats de tous les contrôles (§8), couverture exacte, limites.
- `refonte/faits.yaml` : **registre des chiffres** (135 modèles, 721 routes, 190 migrations, 20 tâches, 35 actions, 18 commandes, 31 variables, 14 modules, etc.), généré depuis l'inventaire du code de l'état B et **injecté** dans les trois documents.

### Fichiers existants concernés
| Fichier | Opération |
|---|---|
| `outils/construire_pdf.py`, `imprimer_pdf.js` | Remplacés par un constructeur unique configurable (`refonte/outils/construire.py`), même moteur Chromium ; l'ancien est conservé |
| `outils/controle_separation.py`, `controle_coherence.py`, `controle_transversal.py`, `verifier_references.py` | Adaptés (nouveaux chemins, nouvelle règle de séparation C5) ; versions d'origine conservées |
| `outils/generer_*.py`, `inventaire.py` | Étendus pour produire CSV et HTML ; mêmes sources de vérité (code de l'état B) |
| `outils/rendre_schemas.js`, `schemas/src/*.mmd` | Copiés dans `refonte/schemas/` puis modifiés ; originaux intacts |
| `guide-visuel/outils/*.js, *.py` | Repris dans `refonte/outils/captures/` (locale française, attentes des messages, assertions DOM) |
| `pdf/*.pdf` (3 PDF actuels) | **Retrait proposé au basculement** (phase 13), après validation du PO ; ils portent l'en-tête « DIFFUSION GÉNÉRALE » et ne doivent plus circuler. L'historique git les conserve |
| `diffusable/`, `restreint/`, `schemas/`, `guide-visuel/`, rapports E1–E4 etc. | Déplacés dans `archive_G0_initial/` (git mv) au basculement ; jamais supprimés |
| `audit_preuves/`, `AUDIT_GLOBAL_G0.md` | **Inchangés** (les tests A14/A20/A25 y restent) ; seul un lien est ajouté dans le registre |
| Code applicatif, `main` | **Aucun fichier touché** (contrôle C13) |

---

## 4. Plan de contenu : de l'ancien au nouveau

| Ancien | Devient | Remarque |
|---|---|---|
| Ch. 1 vision | D1 « Matrix en une page » + D2 §1 | Retrait des « rondes de contrôle » (AUD-004) |
| Ch. 2 vue d'ensemble | D2 §2 (carte en **tableau**, S02 retiré) + D1 | Menu : D1 |
| Ch. 3 lire ce dossier | D2 « Lire ce document » + `README_DOSSIER.md` | Plus d'identifiant de commit ni de branche (D3 seul) |
| Ch. 4, 5 | D2 §3–4 (+ fiches de rôle) ; mécanismes → D3 | |
| Ch. 6 | D2 fiche « Accueil et pilotage » (+ barre de parcours, AUD-005) | |
| Ch. 7 | D2 fiche « Calendrier » | |
| Ch. 8 | D2 fiche « Quarts, services, feuille » (impression : AUD-002) | |
| Ch. 9 à 16 | D2 fiches de module | |
| Ch. 17 | D1 (usage) + D2 (principes d'interface) | |
| Ch. 25, 26 | D2 « Cible et feuille de route » ; branches et commits → D3 | |
| Compléments `4T`–`17T` | D3 chapitres de module | Fusion par module |
| Ch. 18 à 24 | D3 | |
| Annexe A (glossaire) | D2 + D1 (court) | |
| Annexes B, C, D, E, G, H bis | D4 (+ totaux en D3) | |
| Annexe F | D4 (F.5 refait) + D3 (sources, branches) | AUD-031, 038 |
| ECARTS_DECISIONS_CODE.md | D5 | |
| Guide visuel (39 p.) | D1 | |
| Rapports E1–E4, bilan, qualification, clôture | `archive_G0_initial/rapports/` | |

### Schémas (42) : décision par schéma
| Action | Schémas |
|---|---|
| **Conserver** (même contenu, rendu aux normes) | S01, S03, S04, S05, S06, S07, S08, S11, S12, S15, S16, S18, S19, S20, S23, S25, S26, S29, S30, S32, S34, S35, S39 |
| **Refaire** (mise en page) | S09 (regrouper les paquets), S10 (scinder en deux), S13 (texte ≥ 8 pt), S28 (un circuit par schéma) |
| **Marquer « 🔵 CIBLE — non développé » dans l'image** (cadre pointillé, bandeau) | S17, S21, S31, S33 |
| **Remplacer par un tableau** | S02, S14, S22, S24, S27, S36, S37, S38, S40, S42 |
| **Conserver en D3 seulement** | S41 (processus interne) |
Critère : corps de police **≥ 8 pt** à la largeur de la page ; aucune légende séparée de sa figure.

---

## 5. Conception des PDF (règles appliquées à D1, D2, D3, D5)

1. **Mention provisoire** : en-tête courant **et** couverture ; aucun cartouche de 5 lignes répété en tête de chaque chapitre (remplacé par une ligne « Public · Périmètre · Étiquettes » de 2 lignes).
2. **Couverture** : titre, public, version, date, mention provisoire, état décrit (D3 seulement : état B et commit).
3. **Sommaire avec numéros de page**, calculé en **deux passes** d'impression (passe 1 : mesure ; passe 2 : insertion) ; signets ; liens internes ; index des termes (D1, D2).
4. **Mise en page** : A4 portrait ; paysage uniquement pour les tableaux larges ; saut de page avant les **parties** seulement ; une figure ne se sépare jamais de sa légende ; une ligne de tableau n'est jamais coupée ; titres jamais seuls en bas de page ; corps du texte ≥ 9,5 pt, tableaux ≥ 8 pt (7,5 pt toléré en annexe paysage, liste d'exceptions).
5. **Étiquettes** : 🟢 🔵 🟣 ⚪ rendues en pastilles dessinées (corrige le rendu « ◦ » de ⚪).
6. **Références entre documents** : par **code de document et numéro de section** (`GU §3.2`, `RF §5.1`, `DT §9`), jamais par numéro de page seul ; liens cliquables en HTML.
7. **Captures** : pleine largeur, légende (profil, écran, étiquette), repères numérotés discrets, aucune miniature.
8. **Langue** : français pour tout texte lu par un humain ; vocabulaire Marine (COMAEQ, COMOPS, COMANAV, COMAVIA).

---

## 6. Ordre des opérations

Chaque phase se termine par un commit daté, un push et un **rapport de barrière** (résultat des contrôles de la phase). Un point de reprise est écrit dans `refonte/REPRISE.md` (phase en cours, dernière tâche, contrôles verts) après chaque barrière.

| Phase | Contenu | Effort | Barrière |
|---|---|---|---|
| **0. Gel et cadrage** | Référence `637de94` ; squelette `refonte/` ; `MAPPING_ANCIEN_NOUVEAU.csv` généré depuis les titres actuels ; première version de `faits.yaml` ; mesure de **référence** des contrôles sur l'existant | 0,5 j | G0 : mapping complet, 0 section orpheline |
| **1. Socle d'outillage** | Constructeur unique, gabarits et CSS, mention provisoire, deux passes de sommaire, résolveur de renvois, scripts de contrôle C1 à C14 (§8) calibrés sur l'existant | 2 j | G1a : les contrôles détectent des défauts connus (pages vides, légendes séparées, tableaux cassés p.37 et p.79, F.5) |
| **2. Registre vivant (D5) et faits** | `registre.json` (A, B, D, NE, AUD actifs, 125 décisions avec état) ; vues générées ; `faits.yaml` définitif | 1,5 j | G2 : 125 décisions classées, 0 plage `DEC-… à …`, A14/A20/A25 liés aux preuves |
| **3. Schémas et chapitre pilote** | Schémas selon §4 ; chapitre « Maintenance » rédigé dans D1, D2, D3 ; **PDF pilote jetable** | 2,5 j | **V1 — validation PO de la maquette** (densité, ton, fiche de module, renvois) |
| **4. Instance et captures** | Copie isolée de l'état B (`git archive 6d6d0be`), instance de démonstration, données fictives ; **reprise complète des captures** en locale française, date courante, attente des messages, assertions DOM stockées dans le manifeste ; nouvelles captures (annonce à accuser, fiche d'installation, échange de tour, Documentation, RETEX, bas d'accueil et bloc Supervision, appareillage avec session ouverte, deux captures mobiles **émulées**, signalées comme telles) ; suppression des 8 doublons | 2 j | G4 : 0 donnée réelle (analyse du texte DOM), tous les écrans en 200, locale vérifiée |
| **5. Rédaction D1** | Parcours et écrans, profils, limites | 3 j | G5 |
| **6. Rédaction D2** | Résumé décideur, fiches de rôle, fiches de module (modèle imposé), cible et feuille de route | 6 à 7 j | G6 |
| **7. Rédaction D3** | Fusion par module ; prise en main et recette de déploiement **exécutées** dans une copie isolée ; architecture à sécurité | 4 à 5 j | G7 : chaque commande de la prise en main exécutée avec succès (journal archivé) |
| **8. Annexes consultables (D4)** | Génération CSV et HTML autonome ; F.5 refait en tableau | 2 j | G8 : fonctionne hors ligne, 0 requête réseau, filtre opérationnel, totaux = `faits.yaml` |
| **9. Contrôles sur sources (HTML)** | Tous les contrôles automatiques de §8 sur les sources et aperçus HTML | 1 j | **G1 — barrière « sources vertes »** : aucune construction PDF avant |
| **10. Construction candidate** | Trois PDF + registre en PDF, une seule fois | 0,5 j | G10 : mêmes contrôles sur le texte extrait des PDF |
| **11. Inspection à taille réelle** | §9 | 3 j | **V2 — validation PO** des PDF candidats |
| **12. Corrections et cohérence inter-documents** | Corrections dans les sources ; reconstruction du seul document touché (≤ 2 fois) ; contrôle de cohérence (§8, C11) ; `RAPPORT_RECETTE_REFONTE.md` | 2 j | G12 |
| **13. Basculement** | README, archivage des anciennes arborescences (git mv), **retrait des 3 anciens PDF sur ordre du PO**, push | 0,5 j | **V3 — validation finale PO** (documentaire seulement) |
| **Total** | | **≈ 31 à 34 jours de travail effectif** | |

**Parallélisation** : les phases 5, 6 et 7 partagent le registre (phase 2) et les faits ; elles se font dans l'ordre D2 → D1 → D3 pour que le guide cite des fiches existantes.
**Séances** : environ 15 à 20 séances ; chaque séance finit par commit, push et mise à jour de `REPRISE.md`.

---

## 7. Critères d'acceptation par livrable

### D1 — Guide utilisateur
- [ ] 0 chemin de code, 0 nom de branche, 0 identifiant de commit, 0 variable d'environnement (C5).
- [ ] Chaque capture : profil, adresse, statut HTTP 200, assertions DOM (ex. « bouton *Enregistrer la correction* présent pour le chef de secteur, absent pour l'exécutant ») dans le manifeste ; locale française (aucun « mm/dd/yyyy », « Choose File », « AM/PM »).
- [ ] 0 doublon d'image ; 0 message parasite ; 0 donnée réelle (analyse du texte capturé contre la liste blanche des identités fictives).
- [ ] 9 parcours complets, chaque étape illustrée ou expliquée ; limites A14/A20/A25 visibles ; NE-01 annoté sur la capture concernée.
- [ ] Aucune fonction 🔵 ou 🟣 présentée comme disponible.

### D2 — Référentiel fonctionnel
- [ ] Résumé décideur ≤ 2 pages, lisible seul.
- [ ] Toutes les fiches de module respectent le modèle (8 rubriques) ; aucun module sans « limites et écarts ».
- [ ] Erreurs corrigées : impression de la feuille (AUD-002), rondes (AUD-004), barre de parcours (AUD-005), recherche de personnes existant/cible (AUD-022), mentions « non rejoué » mises à jour (AUD-003).
- [ ] Décisions citées **une à une** avec leur état ; 0 plage.
- [ ] Même contenu fonctionnel que les 19 chapitres actuels : chaque section du mapping retrouvée ou retirée avec motif approuvé.

### D3 — Dossier technique
- [ ] Toutes les références de code vérifiées sur l'état B : **≥ 1 105 références, 0 erreur** (le nombre peut baisser seulement par fusion de doublons, justifiée).
- [ ] Prise en main : chaque pas exécuté avec succès dans une copie isolée ; journal archivé dans `audit_preuves/`.
- [ ] NE-03 et NE-04 documentés comme ⚪ (non testés) dans la recette de déploiement.
- [ ] Toute affirmation 🟢 porte sa preuve ; aucune règle inventée.

### D4 — Annexes consultables
- [ ] Un seul fichier HTML, 0 requête réseau (vérifié par Playwright), fonctionnement à 1024×768 et 1366×768.
- [ ] Totaux = `faits.yaml` = inventaire du code (721, 135, 35, 20, 18, 31).
- [ ] F.5 refait : 0 texte tronqué, 0 fragment Markdown.

### D5 — Registre
- [ ] 125 décisions, 26 écarts, 8 points, 7 propositions, 6 NE, AUD actifs : tous présents, tous avec preuve et niveau.
- [ ] Aucune « décision » sans mention PO ; aucune solution non arbitrée présentée comme définitive.

### Tous les PDF
- [ ] Mention provisoire sur 100 % des pages (extraction du texte) ; 0 occurrence de « DIFFUSION GÉNÉRALE » ou de « diffusable ».
- [ ] Sommaire exact (numéros de page = pages réelles) ; 0 lien cassé.
- [ ] 0 page remplie à moins de 40 % hors couverture, fin de partie et dernière page ; 0 légende séparée ; 0 tableau coupé en milieu de ligne ; 0 syntaxe Markdown visible.
- [ ] Police minimale respectée (§5) ; schémas ≥ 8 pt.

---

## 8. Contrôles de non-régression et de cohérence (automatisés, rejoués à chaque barrière)

| Id | Contrôle | Principe | Seuil |
|---|---|---|---|
| C1 | **Couverture du mapping** | Chaque titre de l'ancien dossier se retrouve dans le nouveau ou est « retiré (motif) » | 0 orphelin |
| C2 | **Étiquettes** | Les phrases portant 🔵 / 🟣 / ⚪ de l'ancien dossier se retrouvent avec la même étiquette (comparaison normalisée, liste des écarts approuvés) | 0 étiquette perdue ou promue |
| C3 | **Faits chiffrés** | `faits.yaml` régénéré depuis l'état B ; chaque chiffre cité dans un document égale le registre | 0 écart |
| C4 | **Références de code** | `verifier_references.py` adapté | 0 erreur |
| C5 | **Séparation et classification** | Sur D1, D2, PDF compris : 0 motif `.py`, `/…/…` de code, `claude/`, hash 7 à 40 hexadécimaux, `manage.py`, variables d'environnement, ports ; mention provisoire présente ; mots interdits (« diffusable », « diffusion générale ») absents partout | 0 violation |
| C6 | **Liens et sommaire** | Annotations de liens, ancres, numéros de page du sommaire vs texte extrait | 0 écart |
| C7 | **Décisions** | Identifiants cités existent à la source (branche `claude/eager-hopper-2cbcqh`) ; aucune plage ; état cohérent avec le registre | 0 écart |
| C8 | **Mise en page (auto)** | Taux de remplissage par page, orphelines et veuves, légendes séparées, tailles de police (pypdfium2), marges, résolution des images ≥ 150 dpi | seuils du §7 |
| C9 | **Captures** | Manifeste complet ; code 200 ; profil ; assertions DOM ; liste blanche des identités ; absence de mot de passe, e-mail, jeton | 0 écart |
| C10 | **Inspection à taille réelle** | §9 | 100 % des pages inspectées et journalisées |
| C11 | **Cohérence inter-documents** | (a) mêmes termes (liste de variantes interdites) ; (b) même chiffre partout (via `faits.yaml`) ; (c) matrice de droits **générée une fois** pour D2 et D3 ; (d) tout identifiant A/B/D/NE/DEC a **un seul statut** (celui du registre) dans tous les documents ; (e) chaque renvoi `GU/RF/DT §n` pointe une section existante ; (f) chaque capture citée dans D2 existe dans D1 avec la même explication ; (g) aucune fonction 🔵 de D2 décrite 🟢 dans D1 ou D3 | 0 contradiction |
| C12 | **Reproductibilité** | Deux constructions successives donnent le même texte extrait (empreinte) et le même nombre de pages | identiques |
| C13 | **Application intacte** | `git diff 637de94 -- . ':!docs/dossier-technique'` vide ; `main` distante inchangée | 0 fichier |
| C14 | **Données sensibles** | Recherche de motifs (adresses électroniques, mots de passe de démonstration, jetons, chemins absolus de la machine) dans toutes les sorties et manifestes | 0 occurrence |

Les contrôles sont d'abord exécutés sur l'**ancien** dossier (phase 1) pour mesurer la base ; le rapport de recette compare avant et après.

---

## 9. Vérification à taille réelle des pages et annexes denses

**Définition de « taille réelle »** : rendu de la page à **96 dpi** (A4 = 794 × 1123 px, paysage 1123 × 794 px), soit un pixel de l'écran pour un pixel de l'image, sans réduction. Limite honnête : je lis des images, pas un écran physique ; je garantis donc la lisibilité au sens « corps du texte déchiffrable à 100 % », pas un essai sur matériel.

**Protocole**
1. **100 % des pages** des trois documents et du registre sont rendues à 96 dpi (≈ 290 à 340 pages) et regardées **une par une** (deux pages côte à côte au plus, sans réduction).
2. Les **pages denses** (annexes en PDF, matrices larges, tableaux de plus de 20 lignes, schémas, captures annotées) sont regardées en plus à **150 dpi** par moitiés (haut/bas ou gauche/droite).
3. Les **annexes consultables (D4)** sont ouvertes dans Chromium à 1366 × 768 et 1024 × 768 : lisibilité, tri, filtre, 0 requête réseau.
4. Journal `refonte/inspection_pages.csv` : document, page, résolution, verdict (OK / défaut), défaut, correction, date. Une page n'est « inspectée » que si elle a une ligne.
5. Séances limitées à ~40 pages avec point de reprise ; **aucune page déclarée inspectée sans ligne de journal**.
6. Critères visuels : texte coupé, mot tronqué, tableau déformé, légende séparée, page quasi vide, schéma < 8 pt, capture floue, repères mal placés, mention provisoire absente, contraste.
7. Toute page non inspectée est **listée dans le rapport de recette** ; le PO n'a pas à deviner la couverture.

---

## 10. Jalons de validation du PO

| Jalon | Quand | Ce que le PO valide |
|---|---|---|
| **V0** | Maintenant | Le présent plan et les points ouverts du §12 |
| **V1** | Fin de la phase 3 | Maquette : chapitre pilote en trois PDF, schémas refaits, registre, densité et ton |
| **V2** | Fin de la phase 11 | PDF candidats et rapport d'inspection |
| **V3** | Fin de la phase 13 | Basculement (retrait des anciens PDF, archivage). **Validation documentaire seulement** : ni validation logicielle, ni autorisation de diffusion |

---

## 11. Risques et parades

| Risque | Parade |
|---|---|
| Rédaction massive : dérive du contenu ou perte d'information | Mapping C1, étiquettes C2, faits C3, relecture du pilote (V1), **réutilisation du texte existant** (déplacement et condensation plutôt que réécriture) |
| Instance de démonstration indisponible ou différente | Recréation depuis `git archive 6d6d0be` ; script d'enrichissement versionné ; manifeste des versions |
| Captures datées « jeudi 12 novembre » | Reprise complète à la date courante ; textes sans date codée en dur |
| Vue mobile non essayée sur appareil | Émulation seulement, étiquetée « émulation » ; ⚪ pour l'appareil réel |
| Prise en main impossible à exécuter (dépendances) | Copie isolée ; en cas d'échec, la limite est documentée (⚪), jamais inventée |
| Régénération des PDF qui dérive | Barrière G1 (aucun PDF avant sources vertes) ; budget de 2 reconstructions |
| Mention du commit de l'état B nécessaire pour la traçabilité | Réservée à D3 ; D1/D2 disent « état B, version de référence du 11/11/2026 » |
| Contexte de session limité | `REPRISE.md` à chaque barrière ; sorties volumineuses hors de la conversation |

---

## 12. Points ouverts à trancher par le PO (V0)

1. **Nom et numéro de version** des nouveaux documents : conserver « édition G0 » avec révision (« G0 rév. 2 »), ou autre libellé ? (Le plan utilise « G0 ».)
2. **Retrait des trois anciens PDF** de la branche au basculement (l'historique git les garde) : accord ?
3. **Annexes consultables** : un fichier HTML autonome + CSV vous convient-il (pas de XLSX) ?
4. **Identifiant de l'état B** : confirmé réservé à D3 ; D1 et D2 parlent de « l'état B du 11/11/2026 ».
5. **Captures mobiles** : deux captures émulées, étiquetées comme telles — acceptées ?
6. **Matrice rôle × action** : version en libellés pour D2, version avec clés de code en D4 (accès restreint) — acceptée ?
7. **Ordre de rédaction** D2 → D1 → D3 et **chapitre pilote « Maintenance »** : acceptés ?

*Aucune opération du présent plan n'a été exécutée. J'attends votre validation (V0).*
