# Contrôles de compatibilité — checklist courte

L'environnement de développement n'a que Chromium. Firefox, WebKit, Safari et les lecteurs d'écran se vérifient hors de cet environnement, **sans contourner sa politique réseau**.

## Où effectuer les contrôles (alternatives autorisées)

**Essais PC locaux** : l'instance de démonstration de `docs/TESTS_MARINS.md` (`python scripts/preparer_instance_test.py --servir`), qui n'écoute que sur `127.0.0.1`. Elle sert pour Firefox ou Safari installés sur ce même poste, la molette, le pavé tactile, le clavier et l'impression.

**Essais mobiles réels (iPhone, tablette, autre poste)** : l'instance locale n'est pas joignable depuis un autre appareil, et il ne faut **pas** l'exposer (DEBUG et comptes fictifs). Il faut un **environnement de validation distinct**, isolé et approuvé par la sécurité du système d'information, hébergeant une instance configurée pour cet usage (données fictives uniquement, jamais relié à un réseau opérationnel). Si aucun environnement mobile sûr n'est disponible, **ces contrôles sont marqués « non effectués »** : ne pas les remplacer par un serveur de développement ouvert sur le réseau.

Autres options autorisées pour Firefox ou WebKit : un poste de test avec le navigateur déjà installé, ou du matériel personnel isolé (réseau local fermé, données fictives).

Dans tous les cas : jamais une base réelle, jamais d'identifiants réels.

## Checklist (cocher, noter le navigateur et sa version)

### Windows (poste des essais) — lancement de la démonstration, non testé en développement
Le kit a été éprouvé sous Linux ; ce contrôle se fait sur le poste Windows des essais, environnement virtuel activé (`venv\Scripts\activate`) :
- [ ] `python scripts\preparer_instance_test.py --verifier` affiche « Contrôle réussi » (ce contrôle n'écrit rien).
- [ ] `python scripts\preparer_instance_test.py` se termine sur « Base prête » (chemin avec espaces ou dossier synchronisé OneDrive : à noter).
- [ ] `python scripts\preparer_instance_test.py --servir` ouvre `http://127.0.0.1:8800/` ; connexion avec un compte fictif ; Ctrl+C arrête proprement.
- [ ] Depuis un autre appareil du réseau, `http://<adresse du poste>:8800/` ne répond pas (écoute locale seulement).
- [ ] Si un Redis tourne sur le poste, il ne reçoit aucune connexion pendant la démonstration.
- [ ] `--reinitialiser` recrée la base ; une base absente du dossier `instance_test_marins` est refusée.
Un message « Refus : … » est un résultat attendu quand une condition de sécurité manque : le noter, ne pas contourner.

### Firefox (poste)
- [ ] Connexion, accueil marin et chef : mise en page sans débordement, carte « À faire » complète.
- [ ] Menu : groupes repliables, état conservé après rechargement et après changement de poste.
- [ ] Bandeau d'accès limité (`chef_secteur_b`) : s'ouvre, se ferme, reste fermé après rechargement.
- [ ] Calendrier : affichage, axes HH:mm, « Toute la journée ».
- [ ] Clavier : Tab parcourt le menu puis la carte, focus toujours visible, Échap ferme le menu sur petit écran.

### Safari sur iPhone (environnement mobile approuvé requis, sinon « non effectué »)
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
