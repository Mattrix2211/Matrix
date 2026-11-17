# Rapport de phase 10 — construction des PDF candidats

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Précaution documentaire, non une classification officielle. Date : 17/11/2026. Branche `claude/fervent-wright-kl6gtx`. Base : sources de la barrière G1 (commit `c16c5d6`). **Les PDF sont des candidats : aucune correction n'a été faite après construction** (corrections = phase 12, non autorisée). Aucun PDF historique n'est remplacé. Ce rapport ne valide ni le contenu métier, ni le logiciel, ni la diffusion.

## 1. Les quatre PDF candidats

Dossier : `docs/dossier-technique/refonte/pdf_candidats/`. Une seule construction candidate par document (deux passes d'impression internes pour le sommaire, pagination stable entre les deux).

| Document | Nom exact | Pages | Taille (octets) | SHA-256 |
|---|---|---|---|---|
| Guide utilisateur illustré | `Matrix_G0R2_1_Guide_utilisateur_PROVISOIRE_RESTREINT.pdf` | 89 | 19 279 966 | `a362ba3ff58340ee571f0bd8ffb7ca9e4b95e845093131baf7250f0d25ff1811` |
| Référentiel fonctionnel et de gouvernance | `Matrix_G0R2_2_Referentiel_fonctionnel_PROVISOIRE_RESTREINT.pdf` | 145 | 6 392 463 | `9a77025f13c2000fd3e1e36f3e25fbdd881a8eda5a1c65bcd5b52e2a558f661f` |
| Dossier technique de reprise | `Matrix_G0R2_3_Dossier_technique_reprise_PROVISOIRE_RESTREINT.pdf` | 103 | 5 404 065 | `b9d28cb2c7290c8846fd37a240320cdbb1c1ba0ac19f68e0d5fc502d46901db7` |
| Registre des écarts et décisions | `Matrix_G0R2_5_Registre_ecarts_decisions_PROVISOIRE_RESTREINT.pdf` | 52 | 1 819 499 | `a8c77eeec91be68f1de8973d6bdc853b45bfff3b0d07c6b1ffd036dd0fbb1b19` |

Les empreintes des fichiers changent à chaque construction (horodatage interne du PDF) ; c'est le **texte extrait** qui est reproductible (voir C12). Métadonnées : titre « <document> — MTX-G0-R2 », créateur Chromium, auteur vide. Aucune erreur de génération.

## 2. Résultats détaillés des contrôles

Rapports bruts : `pdf_candidats/controles_GU.md`, `_RF.md`, `_DT.md`, `_RE.md`, `controles_transversaux.md`, `schemas_lisibilite.csv`.

| Contrôle demandé | Résultat |
|---|---|
| **Sommaires et pagination (C6)** | Numéros du sommaire égaux aux pages réelles : 0 écart (GU 37 entrées, RF 38, DT 38, RE 38 vérifiées). Pagination identique entre les deux passes d'impression. |
| **Renvois et signets** | 0 renvoi vers une section inexistante. Signets : GU 67, RF 321, DT 206, RE 96. Liens internes : GU 99, RF 318, DT 255, RE 58 ; **0 lien externe** (aucune URI). |
| **Séparation des références techniques (C5)** | Guide et référentiel : 0 chemin de code, 0 branche, 0 empreinte de version, 0 variable d'environnement, 0 port. 0 occurrence des termes interdits hors citations balisées d'AUD-001 (registre). |
| **Mention provisoire sur toutes les pages (C5)** | Présente sur 89 / 145 / 103 / 52 pages, aucune absente. |
| **Pages vides ou presque vides (C8)** | **Réserve** : GU 12 pages < 40 %, RF 11, DT 13, RE 1 ; aucune page entièrement vide. Les pages < 10 % sont listées au §4. |
| **Tableaux, figures, légendes séparés (C8)** | 0 légende en haut de page (règle automatique) ; 2 titres orphelins en bas de page (RF p.37, p.117) ; **légendes de capture séparées de leur image** repérées à l'œil dans le guide (voir §3, E1). Tableaux coupés en milieu de ligne : non détectable automatiquement, à examiner en phase 11. |
| **Dimensions des captures et schémas** | Résolution effective des captures : minimale **158 ppp** (p_anomalie_2 à 4), toutes les autres captures à 202 ppp ou plus, seuil de 150 ppp respecté. Schémas : 46 sur 46 à 8 pt ou plus à la largeur de page (`schemas_lisibilite.csv`) ; 0 page à texte petit dans les quatre PDF. |
| **Chiffres et statuts (C3, C7, C11)** | Chiffres du texte extrait des PDF : 0 écart avec `faits.yaml`. Les **125 décisions** du tableau du registre PDF portent l'état de `registre.json` (125 / 125, `outils/controle_statuts_pdf.py`). 0 plage de décisions. Matrice des droits : 35 actions identiques au code. |
| **Reproductibilité du texte extrait (C12)** | Trois constructions successives de chaque PDF : **texte extrait et nombre de pages identiques** (GU 89 `6cc4ec4efb7e…`, RF 145 `2489a978bb52…`, DT 103 `d2e7a484eac2…`, RE 52 `0d207744a8fe…`). |
| **C1** | 507 titres couverts ou retirés, 0 orphelin. |
| **C2** | 0 étiquette perdue ou promue (8 passages relus, `config/revue_manuelle.yaml`). |
| **C4** | Dossier technique et registre : 666 références de code, 35 preuves, 260 clés, **0 erreur** (inchangé depuis G1 : sources identiques). |
| **C9** | 70 entrées au manifeste, 0 anomalie ; 0 requête externe sur 36 écrans. |
| **C13** | 0 fichier hors `docs/dossier-technique` modifié depuis `637de94` ; `main` distante inchangée (`6ef16adcfe8e`). |
| **C14** | 0 adresse électronique, jeton, mot de passe de démonstration ou chemin absolu dans le texte des quatre PDF, leurs métadonnées et leurs liens. |
| **C8 syntaxe visible** | **ÉCHEC** : RF 9 bloquants (7 syntaxes visibles + 2 titres orphelins), DT 11 bloquants. Détail et corrections au §3. Les contrôles n'ont pas été contournés ; le PDF GU et le PDF RE sont conformes sur ce point. |

## 3. Erreurs et défauts constatés (aucun corrigé : phase 12)

**E1 — Guide : légende de capture isolée sur une page quasi vide (réserve de mise en page).** Quand la capture, son titre et sa légende dépassent la hauteur d'une page paysage, la légende (« Écran réel · profil… · Repères… ») passe seule sur la page suivante. Pages concernées : GU p.9, 31, 66, 86 (5 % de remplissage) ; p.83 (légende des deux vues de téléphone, 11 %) ; p.81 (titre de section et avertissement d'émulation seuls avant la page de capture, 14 %). Cause : la hauteur réservée aux vignettes (132 mm par défaut) n'ôte pas la place de la légende allongée par les repères numérotés. Correction : réduire la hauteur disponible des captures concernées (paramètre `dispo`) ou raccourcir les légendes de repères ; aucune modification des captures.

**E2 — Marques de mise en forme visibles dans les lignes « Public ».** Les lignes d'en-tête des chapitres sont des blocs HTML : la mise en gras (`**`) et les accents graves (`` ` ``) y restent affichés tels quels. RF : p.61, 105, 111, 117, 130, 136 ; DT : p.30, 36, 40, 68, 81, 88, 100. Correction : écrire ces lignes en balises HTML (`<b>`, `<code>`) ou ajouter l'attribut de rendu Markdown aux blocs.

**E3 — Tableaux non rendus dans le dossier technique.** DT p.54 (tableau « Routes web » de la logistique : lignes en barres verticales brutes) et p.94 (tableau « Ce qui contient l'état de l'instance » collé à son paragraphe). Même défaut que AUD-032 : ligne vide manquante avant le tableau dans la source. Correction : une ligne vide avant chaque tableau (`restreint/…` repris tels quels).

**E4 — Titres orphelins.** RF p.37 (titre de la section 6.9) et p.117 (titre de la section 19.2.1) en bas de page, texte sur la page suivante.

**E5 — Pages quasi vides hors guide** (< 10 %) : RF p.11 (2 %), DT p.7 (5 %), p.12 (9 %), p.23 (4 %), p.29 (9 %), p.39 (2 %), p.67 (8 %). Ce sont des fins de chapitre (paragraphe « Sources » seul) ou des débuts de chapitre ; les chapitres démarrent sur une nouvelle page.

**E6 — Signalements à examiner** : RF p.110 et p.145 (11 et 17 %), tableaux courts isolés en fin de chapitre (constaté à l'œil) ; DT p.72 (18 %), non examinée.

Aucune erreur de génération (aucun échec Chromium, aucun avertissement de police, pagination stable).

## 4. Réserves de mise en page et volumes

| Document | Cible du plan | Obtenu | Écart | Explication |
|---|---|---|---|---|
| Guide utilisateur | 60 à 75 pages | **89** | + 14 | 64 pages de capture en paysage ; 4 à 6 pages de légende isolées (E1) |
| Référentiel fonctionnel | 90 à 110 pages | **145** | + 35 | 40 000 mots, 228 sections de niveau 2, tableaux générés (écarts, décisions) dans chaque fiche, démarrage de chaque chapitre en haut de page |
| Dossier technique | 110 à 130 pages | **103** | − 7 | annexes détaillées déportées dans les annexes consultables ; chapitres techniques repris tels quels |
| Registre | 15 à 25 pages | **52** | + 27 | une fiche par anomalie et par écart ; contrainte de pages levée par le PO au jalon V1 |

L'estimation du rapport G1 (référentiel 90 à 100 pages, dossier technique 60 à 70 pages) était inexacte : elle reposait sur 450 mots par page, sans les tableaux générés ni les sauts de page de chapitre. Les chiffres du tableau ci-dessus sont les mesures réelles.

## 5. Vérifications complémentaires demandées

**Décompte des captures.** Le rapport G1 additionnait à tort 65 + 4 = 70. Le manifeste compte **70 entrées = 69 captures-images + 1 entrée sans image** (`en_validation_execution_marin`, assertion DOM seule : bouton absent côté exécutant). Sur les 69 images : **65 utilisées, 4 non utilisées** (`p_anomalie_6_chef`, `p_anomalie_9_tickets`, `p_maintenance_3_liste`, `tache_detail`). `baseline/BARRIERE_G1.md`, `inventaire_g1_synthese.md` et `outils/inventaire_g1.py` sont corrigés (erratum daté). Aucune capture n'a été modifiée, ajoutée ni retirée.

**Chemins absolus.** Aucun chemin local dans les quatre PDF (texte, métadonnées, liens). Dans le dépôt, les chemins de la machine de travail (`/home/user/Matrix/...`, `/tmp/claude-0/...`) figurent dans **8 fichiers suivis** :

| Fichier | Occurrences | Nature |
|---|---|---|
| `refonte/apercus_G1/GU.html` | 64 | adresses `file:///home/user/Matrix/docs/dossier-technique/refonte/captures/...` des images |
| `refonte/apercus_G1/RF.html` | 24 | idem (schémas) |
| `refonte/apercus_G1/DT.html` | 14 | idem |
| `refonte/apercus_V1/GU.html` | 11 | idem (aperçus du jalon V1) |
| `refonte/apercus_V1/RF.html`, `DT.html` | 2 + 2 | idem |
| `refonte/apercus_V1/presentation.html` | 3 | idem |
| `refonte/outils/lancer_controles_pilote.py` | 1 | chemin d'un dossier temporaire de session (`ETAT_B`) en dur |

Ils ne contiennent ni secret, ni donnée personnelle (le nom `user` est générique), mais ils sont **inutiles** et propres à la machine de travail. Corrections proposées (non faites) : ne plus versionner les aperçus HTML générés (ou les produire avec des chemins relatifs), et remplacer le chemin en dur du script par un paramètre. Les fichiers HTML intermédiaires du dossier `pdf_candidats/` (identiques) **ne sont pas versionnés** ; seuls les PDF, les rapports de contrôle et les fichiers de couverture sans chemin le sont.

## 6. Pages à examiner en priorité en phase 11

1. **Guide** : p.8–10, 30–32, 65–67, 85–87 (couples capture/légende séparés), p.81–83 (vues de téléphone), p.62 à 64 et p.12 à 22 (captures à repères et à vignettes multiples du chapitre pilote), puis toutes les captures à 158 ppp (p_anomalie_2 à 4).
2. **Référentiel** : p.61, 105, 111, 117, 130, 136 (syntaxe visible) ; p.37 et 117 (titres orphelins) ; p.11, 110, 145 (pages presque vides) ; fiche Maintenance (chapitre pilote) ; matrice des actions ; fiches de rôle ; résumé pour le décideur (limite de 2 pages à vérifier).
3. **Dossier technique** : p.54 et 94 (tableaux non rendus) ; p.30, 36, 40, 68, 81, 88, 100 (syntaxe visible) ; p.7, 12, 23, 29, 39, 67, 72 (pages presque vides) ; prise en main développeur ; recette de déploiement ; schémas S09d, S10, S25d.
4. **Registre** : p.43 (28 %) ; fiche AUD-001 (citations balisées) ; tableau des 125 décisions et section « Précisions sur les décisions partielles » ; titres des anomalies.
5. **Transversal** : couvertures et sommaires des quatre PDF, schémas en mode cible (bandeau « CIBLE »), tableaux larges en paysage, pastilles d'étiquettes.

Le protocole de phase 11 (100 % des pages à 96 ppp, journal par page) n'est pas engagé.

## 7. Suite

Arrêt après la construction et les contrôles de phase 10. Aucune des phases 11, 12 ou 13 n'est lancée. Le budget de reconstruction (au plus 2 par document après la candidate) reste entier. Décision attendue : examen des PDF candidats par le PO, puis ordre ou non de passer à la phase 11 / au jalon V2.
