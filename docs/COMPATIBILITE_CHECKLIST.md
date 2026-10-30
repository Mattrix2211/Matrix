# Contrôles de compatibilité — checklist courte

L'environnement de développement n'a que Chromium. Firefox, WebKit, Safari et les lecteurs d'écran se vérifient hors de cet environnement, **sans contourner sa politique réseau**.

## Où effectuer les contrôles (alternatives autorisées)

1. **Navigateur déjà installé sur un poste de test** du bord ou du service (Firefox, Safari), en lançant l'instance de démonstration locale décrite dans `docs/TESTS_MARINS.md`.
2. **Environnement de validation approuvé** par la sécurité du système d'information, disposant des navigateurs.
3. **Matériel personnel isolé** (poste, iPhone) sur réseau local fermé, **données fictives uniquement**, jamais relié à un réseau opérationnel.

Dans tous les cas : instance de démonstration seule (comptes fictifs, mode DEBUG), jamais une base réelle.

## Checklist (cocher, noter le navigateur et sa version)

### Firefox (poste)
- [ ] Connexion, accueil marin et chef : mise en page sans débordement, carte « À faire » complète.
- [ ] Menu : groupes repliables, état conservé après rechargement et après changement de poste.
- [ ] Bandeau d'accès limité (`chef_secteur_b`) : s'ouvre, se ferme, reste fermé après rechargement.
- [ ] Calendrier : affichage, axes HH:mm, « Toute la journée ».
- [ ] Clavier : Tab parcourt le menu puis la carte, focus toujours visible, Échap ferme le menu sur petit écran.

### Safari sur iPhone
- [ ] Accueil marin : carte « À faire », trois lignes visibles puis « Tout afficher » / « Réduire ».
- [ ] Menu tiroir : ouverture, fermeture, groupes.
- [ ] Zones tactiles (≥ 44 px) : boutons de la carte et du menu.
- [ ] Calendrier et bandeau d'accès limité.
- [ ] Rotation de l'écran : pas de débordement horizontal.

### VoiceOver (iPhone ou Mac) ou NVDA (Windows)
- [ ] Lien « Aller au contenu » annoncé et fonctionnel.
- [ ] Menu : groupes annoncés avec leur état (ouvert/fermé).
- [ ] Carte « À faire » : titre, compteurs, pastilles (Urgent, Alerte, Action requise, À suivre) lues avec leur texte.
- [ ] Section « Autres actions » : bouton annoncé avec son état, zone défilante nommée (PC).
- [ ] Bandeau d'accès limité : état et bouton « Comprendre mes droits » compréhensibles.
- [ ] Noter tout libellé ambigu ou lu deux fois.

### Molette et pavé tactile (PC)
- [ ] Zone « Autres actions » en aperçu : la molette fait défiler la liste ; en fin de liste, le défilement passe à la page.
- [ ] Pavé tactile : même comportement, sans « piège » de défilement.
- [ ] Clavier dans la zone : PageBas, flèches, Tab ; la ligne focalisée reste visible.

### Impression réelle
- [ ] Imprimer l'accueil d'un marin chargé (`equipier_a`) et d'un chef (`chef_secteur_a`) : la carte commence en page 1, aucune action coupée, toutes les actions imprimées.
- [ ] Graphiques de l'accueil du chef : légendes entières.
- [ ] Noir et blanc : pastilles « Alerte » et « Urgent » lisibles par leur texte.

## Compte rendu
Un tableau navigateur × point de contrôle (OK / écart / non testé), avec captures des écarts. Un écart n'est corrigé que s'il est démontré ; aucune refonte.
