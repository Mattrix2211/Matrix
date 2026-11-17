# Rapport de corrections (E1 à E6) et d'inspection partielle (phase 11)

> **DOCUMENT PROVISOIRE — DIFFUSION RESTREINTE.** Précaution documentaire. Date : 17/11/2026. Branche `claude/fervent-wright-kl6gtx`. Complète `RAPPORT_PHASE10.md`. Ce rapport ne valide ni le contenu métier, ni le logiciel, ni la diffusion. Arrêt au jalon V2.

## 1. PDF candidats corrigés (`pdf_candidats/`)

| PDF | Pages (avant → après) | Taille (octets) | SHA-256 |
|---|---|---|---|
| `Matrix_G0R2_1_Guide_utilisateur_PROVISOIRE_RESTREINT.pdf` | 89 → **84** | 19 237 581 | `1bbdefb71443503ebecc5d77cd7d4c54067aaaead3bdb18f063c0f0552438bae` |
| `Matrix_G0R2_2_Referentiel_fonctionnel_PROVISOIRE_RESTREINT.pdf` | 145 → **136** | 6 217 883 | `37a983d4628e095de52da64502da1cc76be57a5fdc7667aabcb92cc66da85ab4` |
| `Matrix_G0R2_3_Dossier_technique_reprise_PROVISOIRE_RESTREINT.pdf` | 103 → **94** | 5 239 134 | `060e841db3ed5e74b39679bfaf0ed5848e096dd2c304da8025a6827a161bc769` |
| `Matrix_G0R2_5_Registre_ecarts_decisions_PROVISOIRE_RESTREINT.pdf` | 52 → **52** | 1 819 503 | `73112713f497d7e374095813a96554626ca6a34fe1f14aefd01ce80e60f765b9` |

## 2. Corrections (dans les outils de génération, non chapitre par chapitre)

| Défaut | Correction | Effet |
|---|---|---|
| E1 légendes de capture séparées | `construire.py` : hauteur disponible des vignettes calculée page par page (titre, texte, légende et repères déduits) ; plus de légende sur page suivante | GU : 0 page de légende isolée ; 89 → 84 pages |
| E2 marques Markdown dans les lignes « Public » | `construire.py` : rendu Markdown activé dans ces blocs | RF et DT : 0 syntaxe visible sauf cas E3 |
| E3 tableaux non rendus | `construire.py` : ligne vide insérée automatiquement avant tout tableau (défaut général, dont DT p.94) ; cas distinct DT p.54 (tableau scindé par une ligne vide dans la source) corrigé dans `13_logistique_technique.md` (mise en forme seule, aucun contenu) | DT : 0 syntaxe visible |
| E4 titres orphelins | effet du saut de page limité aux parties (plan §5.4) | RF : 0 titre orphelin détecté |
| E5 pages quasi vides | un chapitre ne commence sur une nouvelle page que s'il ouvre une partie | RF 145 → 136, DT 103 → 94 ; pages < 40 % : GU 12→5, RF 11→3, DT 13→3 |
| E6 | examinée : voir §5 | |

Aucune taille de caractère réduite, aucune information supprimée (contrôle de non-perte inchangé : mêmes sources, seul `13_logistique_technique.md` modifié par suppression d'une ligne vide).

**Chemins absolus** : `construire.py` écrit désormais des chemins relatifs dans les HTML ; les 7 aperçus HTML versionnés (`apercus_V1/*`) sont convertis en chemins relatifs ; `lancer_controles_pilote.py` prend la copie de l'état B en paramètre (`MATRIX_ETAT_B` ou premier argument) ; `.gitignore` exclut les HTML intermédiaires de `pdf_candidats/`. Les aperçus `apercus_G1/*.html` restent à régénérer (voir §6).

## 3. Budget de reconstruction (plan §2 : au plus 2 par document après la candidate)

| Document | Candidate | Reconstructions | Reste |
|---|---|---|---|
| GU | 1 (phase 10) | 1 (E1, E2, E5) | 1 |
| RF | 1 | 1 (E2, E4, E5) | 1 |
| DT | 1 | **2** (E2, E3, E5, puis cas DT p.54) | **0** |
| RE | 1 | 1 (sans changement de texte ; reconstruit avec le lot) | 1 |

Le compteur du dossier technique est épuisé : toute nouvelle correction du DT exige votre accord.

## 4. Contrôles sur les PDF corrigés

| Contrôle | Résultat |
|---|---|
| C8 | **0 bloquant** sur les quatre PDF. Avertissements < 40 % : GU 5 (p.6, 58, 69, 78, 84), RF 3 (p.8, 11, 59), DT 3 (p.7, 9, 12), RE 1 (p.43). 0 titre orphelin détecté, 0 texte petit, 0 syntaxe visible |
| C6 sommaires/renvois | 0 écart (GU 37, RF 38, DT 38, RE 38 entrées), 0 renvoi cassé |
| C5 / mention | présente sur 84, 136, 94 et 52 pages ; 0 chemin de code, branche, empreinte dans GU et RF |
| C3, C7, C11 | 0 écart ; 125 décisions sur 125 avec l'état du registre dans le PDF ; matrice des droits identique |
| C1, C2, C9, C13, C14 | 0 écart (rapport transversal sur les sources inchangées) ; 0 chemin local dans les PDF |
| Schémas | 46 sur 46 à ≥ 8 pt |
| C12 reproductibilité | établie en phase 10 sur trois constructions ; **non rejouée** sur les PDF corrigés pour préserver le budget (à faire en phase 12 si vous l'ordonnez) |

## 5. Inspection visuelle (journal : `JOURNAL_INSPECTION_PHASE11.csv`)

Rendu à 96 ppp, page par page. **Inspectées : guide 84 / 84, référentiel 9 / 136, dossier technique 9 / 94, registre 6 / 52.** Les autres pages (127 + 85 + 46) sont notées « NON INSPECTÉE » : seuls les contrôles automatiques les couvrent. Je ne revendique donc pas une inspection exhaustive de phase 11 ; il reste à inspecter 258 pages, soit environ 6 séances.

Constats :
- **Bloquant : aucun** sur les pages inspectées.
- **Réserves éditoriales** (GU) : p.49 bandeau vert « Session d'appareillage ouverte » superposé à la capture et capture tronquée ; captures coupées en bas d'écran (zone de 768 px) p.33, 51, 57, 59, 61, 63, 64, 67, 72. Ce sont des limites de capture, pas de mise en page ; les corriger imposerait de refaire des captures.
- **Réserves de présentation** : GU p.47, 50, 58, 69, 78 (début de chapitre, texte court puis espace blanc, car la page suivante est une page de capture paysage : disposition justifiée). RF p.11 (une phrase seule sur la page, fin du résumé qui déborde de quelques lignes sur la limite de 2 pages) ; RF p.40 (titre du chapitre « Fiches de rôle » en bas de page, non détecté par C8).
- **Choix de présentation** : fiches en tableau, pastilles, légendes de capture en une ligne.
- Captures inspectées : lisibles, repères bien placés, étiquettes 🟢 correctes, aucune donnée réelle, locale française (dates jj/mm/aaaa, « Choisir un fichier »). Schéma S25d lisible. Matrice, fiches de rôle, prise en main, recette, tableau des 125 décisions et fiche AUD-001 (citations balisées) conformes.

## 6. Défauts encore ouverts

1. 258 pages non inspectées (voir journal).
2. RF p.11 (phrase isolée) et RF p.40 (titre en bas de page) : à corriger (saut de page ciblé ou regroupement de la section 1.5).
3. GU p.49 : message parasite dans la capture ; 9 captures coupées en bas.
4. `apercus_G1/*.html` versionnés contiennent encore des chemins absolus (régénérables ; à exclure ou régénérer en phase 12).
5. C12 à rejouer sur les PDF corrigés ; DT sans budget de reconstruction.
6. Volumes hors plan : GU 84 (cible 60–75), RF 136 (90–110), DT 94 (110–130), RE 52 (15–25, contrainte levée).

## 7. Recommandation pour le jalon V2

**Ne pas valider V2 en l'état ; valider la méthode et la qualité du rendu, et autoriser une courte phase 12 ciblée.** Arguments : le rendu est sain (0 bloquant C8, sommaires exacts, statuts et chiffres cohérents, aucune donnée sensible, guide inspecté entièrement sans défaut bloquant), mais la couverture visuelle des trois autres documents n'est que de 15 / 258 pages hors guide, et deux défauts de pagination subsistent (RF p.11 et p.40). Proposition : (a) autoriser l'inspection des 258 pages restantes ; (b) corriger RF p.11 et p.40 et régénérer `apercus_G1` (1 reconstruction du RF, 1 régénération HTML) ; (c) décider si les 9 captures coupées et celle de la p.49 justifient de nouvelles captures ; (d) rejouer C12. Les volumes au-dessus du plan sont explicables (captures paysage, tableaux générés) et n'appellent pas de suppression d'information.
