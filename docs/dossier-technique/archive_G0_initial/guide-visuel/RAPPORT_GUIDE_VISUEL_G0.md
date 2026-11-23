# Rapport — Guide visuel G0

> **Diffusion restreinte provisoire.** Date : 12/11/2026. Branche : `claude/fervent-wright-kl6gtx`. État décrit : état B (`6d6d0be`, non fusionné dans `main`).
> **Contraintes respectées** : aucun changement du code applicatif ; `main` non touchée ; aucune PR ni fusion ; aucun nouveau lot ; aucune décision du PO modifiée ; aucune donnée réelle ; aucune diffusion externe ; les deux PDF du dossier G0 sont inchangés.
> **Je ne déclare rien validé** : le guide est livré pour relecture. Sa classification et ses destinataires restent à faire valider par l'autorité compétente.

## 1. Livrables

| Livrable | Emplacement |
|---|---|
| Guide visuel (**39 pages**, A4 paysage, 10,4 Mo) | `guide-visuel/pdf/Matrix_Guide_visuel_G0.pdf` |
| Captures sources (**64 images**, 2732×1536 px, rangées par fonctionnalité) | `guide-visuel/captures/01_prise_en_main` … `09_limites` |
| Profil, adresse et repères de chaque capture | `guide-visuel/captures/manifeste.json` |
| Outils (instance, captures, parcours, PDF) | `guide-visuel/outils/` |

Le gabarit est de 39 pages (cible 30 à 36) : j'ai préféré une capture lisible par page plutôt que des vignettes. L'écart vient surtout des sept étapes du parcours « anomalie → ticket ».

## 2. Méthode

- **Instance** : copie isolée de l'état B hors dépôt, préparée par `scripts/preparer_instance_test.py` (base séparée, 127.0.0.1 seulement, aucun service externe, mots de passe aléatoires non conservés). Chromium, 1366×768, facteur d'échelle 2.
- **Données** : fictives. Ajouts faits **dans la seule base de démonstration** par `outils/enrichir_demo_guide.py` (refuse de tourner hors instance marquée) : 6 matériels du secteur Moteurs de la Bretagne, 2 ponts avec plans dessinés pour l'occasion, 3 postes du bord avec affectations.
- **Parcours** : `outils/parcours.js` écrit dans la base de démonstration (anomalie, ticket, compte rendu, tâche) pour montrer le résultat réel. Chaque série de captures part d'une base remise à l'état propre.
- **Repères numérotés** : positions mesurées dans la vraie page, dessinées **dans le PDF seulement** ; les captures sources sont brutes.
- **Authenticité** : aucune capture ne provient d'une autre branche ni d'une maquette. Seuls les extraits de la page « recherche » sont rognés (indiqué sur la page), sans retouche.

## 3. Écrans réellement capturés (64) et profils

| Profil fictif | Écrans |
|---|---|
| `equipier_a` (matelot) | accueil, onglet Suivi, menu, notifications, recherche (équipement, information), calendrier, annonces, tâches (liste, détail, parcours), tours de service, feuille de service, maintenance (liste, fiche, saisie, clôture), anomalies (assistant en 4 étapes, suivi), catalogue, installations (liste, fiche), formations, documentation, RETEX, programme, profil, paramètres |
| `chef_section_a` | synthèse des tâches, calendrier « Mon équipe » |
| `chef_secteur_a` | recherche d'une personne, tours par marin, listes, échanges, maintenances en retard, anomalie (détail, prise en compte, conversion), tickets, matériels (liste, fiche), plan du navire, stock, vue du secteur, difficultés, postes, « En validation » (liste et fiche) |
| `chef_service_a` | absences, vue du service, prêt à appareiller |

**39 pages du PDF** : 3 pages de lecture, 1 page « Matrix en une page », 5 parcours (journée 4 pages, tâche 4, maintenance 4, anomalie → ticket 7, tour de service 2), 6 écrans complémentaires, 4 pages des responsables, 3 pages de limites, 1 de renvois. Les captures déjà utilisées ne sont pas répétées ; les 25 captures non retenues restent dans les sources.

## 4. Parcours vérifiés (réellement rejoués)

1. **Le marin arrive** : accueil → notifications → calendrier → recherche. ✅
2. **Tâche** : liste → détail → « Démarrer » → compte rendu → « Terminer et rendre compte » (tâche « Terminée », compte rendu dans le fil). ✅
3. **Maintenance** : liste → fiche en retard → quatre contrôles « Conforme » → « Terminer la maintenance » (statut « Terminée »). ✅
4. **Anomalie** : assistant 4 étapes → envoi → suivi par le marin → prise en compte par le chef de secteur → « Convertir en ticket correctif » → ticket (7 étapes, lien vers l'anomalie). ✅
5. **Prochain tour de service** : quarts par jour, « Mon prochain tour », feuille de service avec son circuit de validation. ✅
6. **Chef de section** : synthèse des tâches, calendrier de l'équipe. ✅ (vue « personnel » limitée à ces deux écrans)

## 5. Limites rencontrées et écrans non illustrés

- **A14** (passation) : ⚪ non capturé. La synthèse n'existe qu'après la validation d'une relève A/B ; ce parcours n'a pas été rejoué. Le constat reste celui du registre (confirmé par test).
- **A20** : 🟢 capturé (occurrence « En validation », seul bouton « Enregistrer la correction »). Aucune règle de sortie n'est présentée comme décidée.
- **A25** (modules désactivés) : ⚪ non capturé, aucun écran ne montre ces effets (API, administration, tâches planifiées).
- **Plans de maintenance du secteur** : écran vide dans la démonstration, non illustré.
- **Prêt à appareiller** : l'écran existe mais reste vide (aucune session) ; volontairement laissé vide, aucun circuit d'appareillage n'est présenté.
- **Notifications d'appareil, alertes planifiées** : non actives sur l'instance (la cloche le dit : « Non activées sur cette instance »).
- **Validation de relève, échange de service complet, transfert de matériel, fonctions 🔵 et 🟣** : aucun écran ; ils ne sont jamais présentés comme développés.
- **Constats d'interface** relevés en capturant (non corrigés, hors périmètre) : la liste des tickets n'a pas de lien de ligne visible, le ticket est atteint depuis l'anomalie ; un brouillon d'anomalie préexistant s'affichait dans l'assistant (abandonné avant la prise de vue) ; des messages de confirmation (en bas à droite) figurent sur certaines captures, tels qu'affichés.
- **Un seul navigateur** (Chromium), une seule résolution ; pas de test sous Windows ni Safari.
- **Cohérence des dates** : toutes les captures sont du 12/11/2026 (« jeudi 12 novembre »).

## 6. Contrôles faits

| Contrôle | Résultat |
|---|---|
| Chaque capture correspond à une page réellement accessible (code 200, profil indiqué) | Oui : adresse et profil dans `manifeste.json` et dans chaque légende |
| Profil indiqué sur chaque page | Oui |
| Données uniquement fictives | Oui : relecture visuelle de chaque page ; aucun nom, adresse électronique ou mot de passe réel dans le texte du PDF (recherche automatique faite aussi) |
| Mot de passe de démonstration absent du dépôt | Oui (recherche dans `guide-visuel/`) |
| **Inspection visuelle des 39 pages** à 90 dpi (taille de lecture normale), par planches de deux pages | Oui ; défauts trouvés et corrigés : recadrages de l'assistant d'anomalie (remplacés par des pages pleines), recadrage de la recherche, repère mal placé (retiré), symbole ⚪ rendu trop petit (remplacé), statut de clôture manquant dans la légende |
| Lisibilité à 100 % | Captures à 247 mm de large (texte d'interface de 6 à 8 pt) ; les petits caractères du bas des écrans restent ceux de l'application |
| PDF dossier G0 inchangés | Oui |

Je n'ai **pas relu mot à mot** les écrans eux-mêmes (ils sont ceux de l'application).

## 7. Reproduire

```bash
python3 scripts/preparer_instance_test.py --reinitialiser   # dans la copie de l'état B
python3 <dépôt>/docs/dossier-technique/guide-visuel/outils/enrichir_demo_guide.py   # avec l'environnement de la démonstration
python3 scripts/preparer_instance_test.py --servir
MDP=<mot de passe de démonstration> node outils/capturer.js <dossier>/captures && node outils/parcours.js <dossier>/captures
python3 outils/construire_guide.py guide.html && node outils/imprimer_guide.js guide.html pdf/Matrix_Guide_visuel_G0.pdf
```

## 8. Conclusion

Prêt pour relecture par le PO, avec les réserves de la section 5. Classification et destinataires à valider ; aucune diffusion n'est faite ni autorisée par ce rapport.
