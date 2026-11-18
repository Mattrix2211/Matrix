# Rapport V2 — inspection complète, corrections ciblées, PDF candidats finalisés

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Précaution documentaire. Date : 18/11/2026. Branche `claude/fervent-wright-kl6gtx`. Ce rapport ne valide ni le contenu métier, ni le logiciel, ni la diffusion. Arrêt au jalon V2 ; phase 13 non engagée.

## 1. PDF candidats finalisés (`pdf_candidats/`)

| PDF | Pages | Taille (octets) | SHA-256 |
|---|---|---|---|
| `Matrix_G0R2_1_Guide_utilisateur_PROVISOIRE_RESTREINT.pdf` | 86 | 19 807 858 | `966983dc5aa7ee23e644747f303b98ae37526b4641143ca1f400ed254242f0a2` |
| `Matrix_G0R2_2_Referentiel_fonctionnel_PROVISOIRE_RESTREINT.pdf` | 135 | 6 232 179 | `ed5539bd77fd0bb9535690506ed808bcc6278e1d6152219afb83f5e3f0cc9a4e` |
| `Matrix_G0R2_3_Dossier_technique_reprise_PROVISOIRE_RESTREINT.pdf` | 94 | 5 239 134 | `060e841db3ed5e74b39679bfaf0ed5848e096dd2c304da8025a6827a161bc769` |
| `Matrix_G0R2_5_Registre_ecarts_decisions_PROVISOIRE_RESTREINT.pdf` | 52 | 1 812 916 | `61ee477df0ec8fc94ceaf16c5119db6aaba7ad6c8d0ac109b03fc27ebe910e38` |

Total : 367 pages (le guide passe de 84 à 86 pages : une capture ajoutée, une capture scindée en deux). Les empreintes de fichier changent à chaque construction ; le texte extrait est reproductible (§5).

## 2. Inspection (journal : `pdf_candidats/JOURNAL_INSPECTION_V2.csv`, 367 lignes)

Rendu à 96 ppp, pages examinées par planches de 2 à 4 pages. Le journal indique, **pour chaque page, la base de l'inspection** :
- **« build finale »** : la page a été vue sous sa forme finale ;
- **« build précédente, identique par empreinte »** : la page a été vue sur la construction précédente, et son image est identique (empreinte de pixels) dans la version finale.

Aucune page n'est notée « NON REVUE ». Couverture : guide 86/86, référentiel 135/135, dossier technique 94/94 (le dossier technique n'a pas été reconstruit : ses 94 pages sont identiques à celles inspectées), registre 52/52. Limite de méthode : la lecture est faite sur des planches à 80–96 ppp ; le texte courant est lisible, mais les très petits caractères des captures le sont moins ; aucune page n'a été examinée à un grossissement supérieur.

## 3. Registre consolidé des défauts

| Id | Gravité | Emplacement | Constat | Traitement |
|---|---|---|---|---|
| D-01 | Bloquant | GU p.49 (avant : session ouverte) | Bandeau vert « Session ouverte » superposé à la capture | **Corrigé** : capture refaite sans message ; la validation (bas de page) a sa propre capture (p.50) |
| D-02 | Défaut important | GU captures tronquées (anciennes p.33, 51, 57, 59, 61, 63, 64, 67, 72) | Cadrage de 768 px coupant du contenu utile : liste des matériels, absences, stock, calendrier d'équipe, vues du secteur et du service, etc. | **Corrigé** : les écrans de moins de 960 px sont capturés en entier (9 captures) ; les écrans plus longs sont conservés en partie haute avec la mention « la page se poursuit en dessous » ; l'accueil du chef a 3 captures (haut, milieu, bas). Captures refaites sur l'instance isolée, données fictives |
| D-03 | Défaut important | RF p.11 et p.40 | Phrase isolée ; titre « Fiches de rôle » seul en bas de page | **Corrigé** (phrase fusionnée ; saut de page limité aux parties) |
| D-04 | Défaut important de lisibilité | RF p.16-17, 53, 82, 95 | Un schéma remplacé par deux tableaux dont le second (« De / Condition / Vers ») répète le premier | **Ouvert** : supprimer le second tableau ferait perdre les liaisons ; décision éditoriale demandée |
| D-05 | Défaut mineur | RF p.127 | « Dossier V1.2 (, comptes rendus… » : parenthèse mal formée en pied de section | **Ouvert** (une correction de source, mineure) |
| D-06 | Défaut mineur | RF p.135 | Index des schémas incomplet et libellés hétérogènes (« Schéma S25 — … ») | **Ouvert** |
| D-07 | Défaut d'édition | RF p.98, 103, 108, 112 | Mentions d'une couverture de tests « avec l'ensemble 3 » et de « rapport de lot conservé dans les archives » : traces de l'édition initiale | **Ouvert** (reformulation à valider) |
| D-08 | Erreur factuelle potentielle | — | Aucune erreur factuelle ou contradiction nouvelle détectée ; contrôles C3, C7, C11 à 0 écart ; 125 décisions et leur état identiques au registre | — |
| D-09 | Défaut corrigé | RF, DT | Marques Markdown, tableaux non rendus, titres orphelins, chemins `.md`, numéros de chapitre de l'édition initiale (« ch. N »), mentions « remplacé par un tableau », état documentaire « maquette pilote » en pied de page, ponctuation orpheline des paragraphes « Sources » | **Corrigés** dans les sources ou les outils |
| D-10 | Choix de présentation | GU p.6, 59, 71, 80, 86 ; RF p.8 ; DT p.7, 9, 12 ; RE p.43 | Pages remplies à moins de 40 % (début ou fin de chapitre avant une page paysage, dernière page) | Justifiées, laissées en l'état |
| D-11 | Amélioration esthétique | GU p.84 | Marge blanche sous le contenu de la capture (hauteur d'écran) | Laissée en l'état |
| D-12 | Réserve | GU | Les captures en « partie haute » ne montrent pas le bas des écrans longs (accueil du marin, tours de service, exécution de maintenance, etc.) | Dite en légende ; à arbitrer par le PO si un bas d'écran doit être ajouté |

Défauts bloquants restants : **aucun**.

## 4. Comparatif avant / après (corrections importantes)

| Page (avant → après) | Avant | Après |
|---|---|---|
| GU p.49 → p.49-50 | Capture tronquée, bandeau vert parasite | Haut de la session sans message ; page 50 : bas de page avec la validation |
| GU anciennes p.51, 57 → p.51, 58 | Liste des matériels et du stock coupés | Listes entières |
| GU anciennes p.59-60 → p.60-62 | Accueil du chef en deux captures (haut, bas) | Trois captures (haut, milieu, bas) |
| GU anciennes p.63-64 → p.63, 65-66 | Calendrier d'équipe et vues d'ensemble coupés | Vues entières |
| RF p.11 | Une phrase isolée sur la page | Phrase fusionnée dans la section 1.3 |
| RF p.40 → p.40 | Titre « 7 Fiches de rôle » seul en bas de page | Titre en haut de page, avec son contenu |

Les PDF précédents (phase 10 : 89/145/103/52 pages ; phase 11 : 84/136/94/52 pages) sont dans l'historique git.

## 5. Contrôles

| Contrôle | Résultat |
|---|---|
| C1 | 507/507 titres couverts, 0 orphelin |
| C2 | 0 étiquette perdue ou promue |
| C3, C7 | 0 écart ; 0 plage de décisions |
| C4 | 666 références de code, 0 erreur |
| C5 | 0 chemin de code, branche, empreinte dans GU et RF ; mention sur 86/135/94/52 pages ; règle étendue aux fichiers `.md` |
| C6 | sommaires exacts (0 écart), 0 renvoi cassé |
| C8 | **0 bloquant** ; avertissements < 40 % : GU 5, RF 2, DT 3, RE 1 (justifiés, D-10) ; 0 titre orphelin, 0 syntaxe visible, 0 texte petit |
| C9 | 72 entrées de manifeste, 0 anomalie |
| C11 | matrice des droits identique ; **125/125 décisions** du registre PDF avec l'état de `registre.json` ; aucun statut ni décision PO modifié (contrôle comparatif du registre) |
| C12 | **Rejoué** : deux constructions successives des PDF GU, RF et RE donnent un texte extrait et un nombre de pages identiques ; DT non reconstruit (texte identique à la candidate) |
| C13 | 0 fichier hors `docs/dossier-technique` modifié depuis `637de94` ; `main` inchangée |
| C14 | 0 donnée sensible, 0 chemin local dans les PDF |
| Schémas | 46/46 à ≥ 8 pt ; résolution des captures ≥ 150 ppp |

## 6. Reconstructions effectuées (depuis la construction candidate de phase 10)

| PDF | Phase 11 (précédent rapport) | Ce lot | Total après la candidate |
|---|---|---|---|
| Guide | 1 | 4 (captures élargies, partie haute, capture de session, rebuild final) | 5 |
| Référentiel | 1 | 5 (E1 à E9 de ce lot : phrase isolée, renvois, sources, chemins, « ch. N ») | 6 |
| Dossier technique | 2 | **0** | 2 |
| Registre | 1 | 1 | 2 |

Le budget de deux reconstructions par document est **dépassé pour le guide et le référentiel** ; j'ai regroupé les corrections quand c'était possible, mais certaines (renvois et chemins `.md` découverts pendant l'inspection de pages tardives) ont exigé de nouvelles constructions. Les constructions de contrôle de reproductibilité (hors dépôt) ne sont pas comptées. Le dossier technique n'a pas été reconstruit.

## 7. Réserves restantes

1. D-04 à D-07 et D-12 ouverts (voir §3).
2. Le dossier technique reste sous le volume prévu (94 pages pour 110 à 130), le guide au-dessus (86 pour 60 à 75), le référentiel au-dessus (135 pour 90 à 110), le registre au-dessus (52 pour 15 à 25, contrainte levée).
3. Vues de téléphone émulées ; parcours non rejoués listés dans les fiches (⚪).
4. L'inspection est visuelle à 80–96 ppp ; elle ne remplace ni la relecture métier par le PO ni un contrôle sur écran physique.

## 8. Recommandation pour la validation V2

**Je recommande de valider V2 sous réserve**, c'est-à-dire d'accepter les quatre PDF comme candidats de référence pour la décision de basculement, à condition de trancher les défauts ouverts :
- les PDF sont complets, cohérents et réellement inspectés (367/367 pages au journal) ; aucun défaut bloquant ne subsiste ; les contrôles automatiques sont verts et reproductibles ;
- les défauts ouverts sont d'édition (D-04 à D-07) ou éditoriaux (D-12) : aucun ne touche une règle métier, un statut ou une décision ;
- il faut votre arbitrage pour D-04 (supprimer ou garder le second tableau), D-06 et D-07 (reformulation), et vous dire si les bas d'écran longs doivent figurer (D-12) ;
- si vous les traitez, une dernière reconstruction ciblée (RF, éventuellement GU) suffirait, hors budget initial, à documenter ; sinon les PDF peuvent partir en phase 13 tels quels avec ces réserves.
