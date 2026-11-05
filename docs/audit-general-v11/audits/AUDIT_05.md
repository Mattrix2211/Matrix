# Audit 05 — UX, cohérence et accessibilité (rapport partiel : navigateur réel)

**Statut : Clôturé avec réserves** (voir « Clôture » en bas du rapport). (elles ne sont pas des preuves rejouables, les scripts le sont).

**Limites** : un seul navigateur, Linux, résolution de référence 1366×768 puis 375×667 ; mode sombre, impression, tablette tactile, lecteur d'écran, postes anciens : non testés. La charte `design/` (dépôt `design-system`, révision `78060c5`, identique à celle du sous-module) a été récupérée à la 3ᵉ passe.

## 1. Constats exécutés

| Contrôle | Résultat | Verdict |
|---|---|---|
| Accueil « Aujourd'hui », 7 profils (équipier, chef de secteur, COMAEQ, commandant, second, administrateur d'unité, suivi à terre), 1366×768 | Chargement 600 à 700 ms, aucune erreur console, aucune requête en échec, aucune ressource externe, aucun débordement horizontal ; 6 à 13 cartes selon le profil | Conforme |
| Pages du menu latéral (23 liens équipier, 26 chef de secteur, 29 administrateur d'unité) | Toutes en 200, aucun débordement, aucune erreur console | Conforme |
| Téléphone 375×667, 8 pages | Aucun débordement horizontal | Conforme (échantillon) |
| Clavier | Premier arrêt de tabulation : lien « Aller au contenu » ; contour de focus visible (2 px) sur les six premiers éléments | Conforme (échantillon) |
| Intitulé des onglets | **Toutes** les pages ont `<title>Matrix</title>` (23, 26, 29 pages distinctes, 1 seul titre) | **Non conforme, AUD-018** |
| Champ de recherche globale | Pas d'`aria-label` : le nom accessible repose sur le seul `placeholder` | Écart mineur (AUD-018) |
| Page 404 en production | Texte : « Cette page n'existe pas, a été déplacée ou n'est pas accessible avec votre compte » (`matrix/templates/404.html`), sans lien de retour propre à l'objet ; en `DEBUG`, la page technique Django s'affiche | Acceptable ; voir AUD-008 |

## 2. Parcours exécutés avec clics réels

| Parcours | Résultat |
|---|---|
| **Feuille de service, circuit complet BSC** : `equipier_a2` crée le brouillon, le propose ; `chef_secteur_a`, `chef_service_a` puis `coma_comaeq` visent (confirmation modale à chaque visa) | Statuts successifs : brouillon → visa chef de secteur → visa chef de service → visa COMAEQ → **publiée**. Aucune erreur HTTP. 8 s de script. **Conforme.** |
| Interface de la feuille selon le profil (date sans feuille) | Seul `equipier_a2` voit « Créer le brouillon » ; `equipier_a`, chef de secteur, COMAEQ, administrateur d'unité ne le voient pas : l'interface est alignée sur le serveur (§AUDIT_06) |
| Boutons de visa « chef de secteur » sur une feuille proposée | Affichés à `chef_secteur_a`, `chef_service_a`, `coma_comaeq`, `coma_comanav`, `cdt_a`, `admin_navire` ; pas au second ni à l'équipier : l'interface montre ce que le serveur permet (AUD-014 n'est donc pas une porte dérobée, c'est une règle à arbitrer) |
| Chef de secteur : clic sur « Ouvrir » du ticket d'accueil | Page « introuvable » (AUD-008) |
| Brouillon de signalement : saisie, départ, « Reprendre » depuis l'accueil | La carte existe et ramène à l'assistant (étape 1 sur 4). **Texte saisi non revérifié** : mon script remplissait le champ de recherche `q`, non un champ de saisie métier. Le parcours complet jusqu'à l'envoi n'est **pas** joué |
| Assistant de signalement | 4 étapes (installation/matériel/secteur, titre et gravité, …) ; une bannière « brouillon » apparaît aux étapes 1 et 3 (déjà connu : ANO-010) |

## 2 bis. Comparaison aux maquettes approuvées et à la charte (3ᵉ passe)

Méthode : captures Chromium 1366×768 des deux prototypes (`docs/prototypes/quarts/vue_quotidienne_A.html`, `vue_responsable_B.html`) et des pages réelles `/quarts/` (équipier : `equipier_a` ; chef : `chef_secteur_a`), pipeline complet de démonstration (`sondes/navigateur/maquettes.js`, `maquettes_par_marin.js`).

| Élément | Maquette | Page réelle | Verdict |
|---|---|---|---|
| Vue quotidienne A : titre, état de la liste, onglets, case « mes créneaux », colonnes quarts/tours, cartes « Mon prochain tour » et « À traiter », « État des listes » | présents | présents, dans le même ordre ; colonnes dans l'ordre du mode du bâtiment (quai : tours d'abord) | **Conforme** (écart explicable par le mode) |
| Bouton « Proposer un échange » dans « Mon prochain tour » | présent | absent sur l'essai (tour en cours) | à vérifier hors tour en cours (**NV**) |
| Vue responsable B : onglet « Par marin », bandeaux d'alerte, légende quart/tour, barre de charge « comparée à l'équipe », ligne « Postes à pourvoir », grille par jour | présents | **présents** ; le seuil de charge n'est pas codé en dur (libellé « comparées à celles de l'équipe ») | **Conforme** |
| Onglet par défaut du chef | « Par marin » (B) | « Par jour » ; « Par marin » est le deuxième onglet | **Écart déjà connu** (ANO-008, décision UX ouverte) |
| Onglet « Listes » | absent des maquettes | présent | extension, non contradictoire |
| Charte : accent unique `--signal` #00B4D8, pas d'`--ember`, pas de `--green-sport`, pas de Syncopate, polices Space Grotesk / Inter / JetBrains Mono auto-hébergées, aucun emoji dans les gabarits | `design/DESIGN_SYSTEM.md` §2 à §11 | variables et polices conformes (`matrix/static/css/matrix.css`, `fonts.css`) ; les mentions d'`--ember` et de Syncopate sont dans des commentaires qui les interdisent ; 0 emoji dans les gabarits | **Conforme (analyse statique)** |
| Charte vs principe « aucun CDN » | `DESIGN_SYSTEM.md` §3 propose un lien Google Fonts | Matrix auto-héberge les polices (décision déjà documentée dans `docs/REFERENCE.md` §1) | Conforme à Matrix ; la charte générique est à ne pas suivre sur ce point |

## 3. Non audité

Comparaison aux maquettes approuvées (A et B de la page d'entrée « Quarts »), densité réelle, temps de saisie, aides contextuelles, cohérence des libellés entre modules, impressions A4, erreurs de formulaire, perte de saisie à la déconnexion automatique (15 min).

## 4. Anomalies liées

AUD-008, AUD-014, AUD-016, AUD-018.

## Clôture (4ᵉ passe)

**Statut : Clôturé avec réserves.** « Avec réserves » signifie que l'analyse technique est achevée sur le périmètre décrit ; **les éléments listés ci-dessous restent non vérifiés et ne doivent pas être lus comme conformes**.

### Contrôles ajoutés à la 4ᵉ passe

Navigateur réel : accueil de 7 profils, 3 menus, mobile 375 px (8 pages et menu ouvert/fermé par Échap), clavier, **mode sombre (bascule et mémorisation après rechargement)**, **impression** (barre latérale masquée), comparaison à deux maquettes et à la charte `design/` (révision `78060c5`).

### Non vérifié ou dépendant d'une validation externe

Tablette tactile, lecteur d'écran, postes anciens, impression sur papier réel ; comparaison à des maquettes qui n'existent que pour l'écran « Quarts ».
