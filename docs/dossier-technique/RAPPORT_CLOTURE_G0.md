# Rapport de clôture — Dossier technique G0 (passe de finition des PDF)

> **Diffusion restreinte.** Date : 12/11/2026. Branche : `claude/fervent-wright-kl6gtx`. État de référence : état B (`6d6d0be`), non fusionné dans `main`.
> **Contraintes respectées** : aucun changement du code applicatif ; `main` non touchée ; aucun lot (L04 non lancé) ; aucune PR ni fusion ; aucune nouvelle règle métier ; aucune décision du PO modifiée ; aucune diffusion externe des PDF. Seuls ont été modifiés : des textes documentaires (corrections éditoriales), des schémas (disposition uniquement) et les outils de génération PDF.
> **Je ne déclare pas G0 validé** : cette décision revient au PO.

---

## 1. Défauts corrigés

| Défaut | Correction | Où |
|---|---|---|
| Page du PDF restreint portant **uniquement** « Sources » (et autres fins de chapitre orphelines : 3 dans le diffusable, 4 dans le restreint) | **À la source** : le dernier bloc, le filet et la ligne « Sources » sont gardés ensemble, la dernière ligne d'un tableau reste avec ce qui suit, orphelines et veuves à 3 lignes, titres jamais seuls en bas de page | `outils/construire_pdf.py` |
| Schémas rendus trop petits (jusqu'à 4,9 px de texte à la largeur de la page) | Disposition seule : S01 (horizontal), S02 (domaines en liste), S05 (accents rétablis, guillemets parasites retirés), S08, S13, S28, S31, S35 (retours à la ligne), S31 (le bouclage devient une note), S25 (étiquettes coupées) ; mêmes nœuds, mêmes relations | `schemas/src/`, `schemas/svg/` |
| S10 (relations entre entités) trop large | Disposition « gauche-droite » | idem |
| Liste « Limites » du complément du chapitre 12 en retard sur le texte corrigé la veille (relevé pendant l'inspection des pages) | Mise à jour de la phrase (trois chemins de sortie, suspension de l'entretien d'une installation) ; aucune règle nouvelle | `restreint/12_…_technique.md` |
| Annexe F §F.5 : titres de sections recopiés comme titres dans la liste des éléments non vérifiés | Les lignes de titre ne sont plus reprises (168 passages au lieu de 173) | `outils/generer_annexes_e4.py` |
| Numéros de page du guide de lecture devenus faux après régénération | Mis à jour | `GUIDE_DE_LECTURE.md` |

Rappel de la passe précédente : mots coupés dans les tableaux et listes Markdown rendues en paragraphe, déjà corrigés.

## 2. Pages et schémas réellement inspectés

**Méthode.** Rendu image de chaque page des deux PDF régénérés, puis lecture de mosaïques de **12 pages** (titres, marges, tableaux, coupures, schémas). Pour les schémas : rendu individuel à la largeur de la page (510 px) avec la hauteur maximale de l'impression, regroupés par 4.

| Élément | Inspecté visuellement |
|---|---|
| PDF diffusable (108 pages) | **Toutes les pages**, au niveau de la mise en page |
| PDF restreint (143 pages, dont 55 en paysage) | **Toutes les pages**, au même niveau ; annexes B à H bis incluses |
| Schémas S01 à S42 | **Les 42**, après relayout (S01, S02, S05, S10 ; S03, S04, S06 à S09, S11, S12 ; S13 à S24 ; S25 à S42 ; S08, S13, S25, S31 revus après correction) |
| Comparaison schéma / texte | Faite pour S05, S25, S28, S30, S31, S33 et revérifiée sur les schémas modifiés ; **non refaite chapitre par chapitre** pour les autres |

Limites de cette inspection : les mosaïques sont à résolution réduite ; **je n'ai pas relu mot à mot le texte courant** ni vérifié à l'œil chaque caractère de chaque page. Un contrôle automatique ne remplace pas ce regard : il le complète seulement.

## 3. Contrôles exécutés et résultats

| Contrôle | Résultat |
|---|---|
| Références de code (fichier, ligne, symbole) | **1 105, 0 erreur** |
| Cohérence documentaire (structure, liens, chiffres, secrets) | **0 erreur** |
| Séparation diffusable / restreint | **0 violation** |
| Revue transversale (26 chapitres, 8 annexes, 135 modèles, tâches, commandes, routes, circuits, schémas) | **0 erreur** |
| PDF régénérés | **108 pages** (diffusable), **143 pages** (restreint) |
| Pages quasi vides ou « Sources » seules | **Aucune** dans les deux PDF |
| Contenu dans les 2,5 % de marge gauche et droite (analyse d'image) | **Aucun** |
| Étiquettes 🟢 🔵 🟣 ⚪ dans le texte extrait | **Présentes** dans les deux PDF |
| PDF diffusable : référence de code, variable d'environnement, adresse, en-tête « restreinte » | **Aucune** (109 en-têtes « diffusion générale ») |
| PDF restreint : en-tête « diffusion générale » | **Aucun** (144 en-têtes « diffusion restreinte ») |
| Constats A14, A20, A25 | **Conservés** (§4) |

Tests de l'application : **non rejoués** (aucun code modifié ; les 29 tests de vérification A14, A20, A25 sont ceux du rapport de qualification).

## 4. A14, A20, A25 : documentation conservée
- **A14** : « confirmé par test » dans le registre, le chapitre 6, son complément et la synthèse par criticité.
- **A20** : trois chemins de sortie, suspension de l'entretien d'une installation, aucune règle nouvelle (D2) : chapitre 12, complément (désormais cohérent aussi dans « Limites »), registre, synthèse, schéma S25.
- **A25** : constat technique complet, règle attendue non décidée : registre, chapitres 6, 7, 12, 20, 22, 23.

## 5. Limites restantes
1. **Lecture mot à mot** des PDF non faite par moi : à faire par le PO.
2. **Densité** : S09, S10, S11 et S13 restent petits (7 px environ) ; lisibles à la largeur de la page, mais à regarder à l'écran en zoom.
3. **Sommaire** sans numéros de page (liens et signets à la place) ; les numéros de page du guide sont ceux des PDF de ce jour et changeront si les PDF sont régénérés.
4. **Pas de relecture par un marin, un responsable et un développeur** (réserve inchangée).
5. **Suite complète de 3 963 tests non rejouée.**
6. **Classification et destinataires** des deux PDF à valider par l'autorité compétente ; la séparation diffusable / restreint n'est pas une autorisation de diffusion.
7. Les rapports précédents (`RAPPORT_E1` à `E4`, `BILAN_FINAL_G0`, `RAPPORT_QUALIFICATION_FINALE_G0`) conservent leurs chiffres d'origine (pages, statuts) : **le présent rapport fait foi** pour la version PDF actuelle.

## 6. Commits produits
Trois commits sur `claude/fervent-wright-kl6gtx` : (1) finition éditoriale des sources (complément du chapitre 12, guide, annexe F) ; (2) schémas relayoutés, outils de génération et PDF régénérés ; (3) ce rapport. Les identifiants figurent dans la réponse de livraison.

## 7. Conclusion
**Prêt pour validation PO, avec les réserves 1 à 6 ci-dessus.** Les deux PDF sont à relire par le PO avant toute décision ; aucune diffusion n'est faite ni autorisée par ce rapport.
