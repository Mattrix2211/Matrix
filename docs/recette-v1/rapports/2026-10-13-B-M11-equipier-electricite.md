# Passage B — M11 — Équipier d'un autre service (compte `equipier_elec_a`, agent `marin-complementaire`)

| Champ | Valeur |
|---|---|
| SHA testé | `5ea072d897f79955b8d50def62f055a7090ddd5d` (branche `claude/recette-v1-passage-b`) |
| Base | SQLite jetable, `DJANGO_DEBUG=1`, `migrate` + `seed_demo` + `seed_recette`, rejouée avant la mission |
| Navigateur | Chromium headless, 1366×768, serveur MCP `playwright`, session fermée avant |
| Date | 2026-10-13 |
| Exécuté | Mission M11 par `marin-complementaire` (profil copié de `personas-comptes.md`) ; consigne ajoutée : ne pas deviner d'adresse |
| Durée mesurée par l'outil (agent entier, 17 appels d'outils) | 44,5 s |

Compte rendu du marin, tel que reçu (captures `M11-*.png` dans `captures/`).

---

COMPTE RENDU MARIN – M11 (compte equipier_elec_a, « Nora », équipière Énergie / Électricité, Bretagne)

Réussite : NON, mais sans doute normal. Je n'ai trouvé aucune tâche de la propulsion. Je n'ai aucun moyen de savoir si elle existe, ni si elle m'est cachée volontairement. Rien dans l'application ne me dit « cette tâche existe mais ne vous est pas accessible ».

Chemin suivi :
1. Connexion : page « Connexion », champs « Utilisateur » et « Mot de passe », bouton « Se connecter ». Arrivée sur « Bonjour Matelot Equipier Elec A ». Le bloc « À faire » montre 2 tâches [Recette] (isolement des tableaux principaux, serrage des barres du tableau 2), 2 annonces et 1 maintenance. Rien sur la propulsion.
2. Menu « Activité » > « Tâches » (/taches/). Sections « Mes tâches », « Ma tâche personnelle », « Terminées récemment ». Je n'y vois que mes tâches : 2 à faire, 1 terminée (« Vérifier l'étalonnage des sondes de température »). Aucune tâche de la propulsion, aucun filtre ni onglet pour voir d'autres services.
3. Barre « Rechercher dans Matrix » avec « propulsion » : 0 résultat dans toutes les catégories (Matériel, Installations, Tickets, Formations, Documents, Personnes, Anomalies, Rondes, Échanges de service, Tâches). Le message est un simple « Aucun » ou « Aucune ».
4. Même recherche avec « Recette » : je retrouve mes 2 tâches [Recette] et 3 formations [Recette] (réseau incendie, pompes d'incendie, travaux en hauteur). Aucune tâche d'un autre service.
5. Menu « Programme du bâtiment » : seulement « Exercice incendie général » le 15/10/2026 à 16:00. Rien sur la propulsion.

Mesures : environ 7 actions (connexion, clic Tâches, 2 recherches, clic Programme, plus les consultations), 5 écrans (accueil, Tâches, 2 pages de recherche, Programme), 0 retour en arrière. Durée non mesurée.

Hésitations et détours : je n'ai pas su où chercher une tâche d'un autre service. J'ai essayé la liste des Tâches, puis la recherche, puis le Programme. Je n'ai pas fouillé Postes du bord, Annonces, Documentation ni Tickets correctifs. Je ne me suis pas servie de l'URL /taches/N/ pour tester d'autres numéros, comme demandé.

Termes ambigus :
- « Aucun » / « Aucune » dans la recherche : on ne sait pas si c'est « rien n'existe » ou « rien que vous puissiez voir ».
- « Ma tâche personnelle » (« Privée par défaut : seuls vous la voyez ») : clair.

Retour du système : pas d'erreur, pas de blocage visible. Les messages sont clairs mais ne me guident pas, car il n'y a pas d'explication sur ce que je peux voir ou pas.

Correction d'erreur : sans objet, je n'ai rien créé ni modifié.

Droits constatés : aucun droit excessif. Je ne vois que mes propres tâches, et la recherche ne fait pas fuiter de tâche d'un autre service. Rien n'est bloqué à tort à ma connaissance. Mon menu contient « Prêt à appareiller » (Supervision) et « Paramètres » (Administration). Je ne les ai pas ouverts, donc je ne sais pas ce qu'ils montrent à mon niveau. À vérifier par l'équipe.

Avantage face au papier/Excel : la recherche globale est rapide et couvre beaucoup de catégories. Pour ma mission précise, elle ne m'aide pas : je n'ai aucun moyen de voir ce qui existe hors de mon périmètre ni de savoir à qui m'adresser.

Verbatim (en tant que Nora) : « Je ne vois que mes tâches. Si on me parle d'une tâche de la propulsion, soit elle n'est pas pour moi, soit elle n'existe pas, et Matrix ne me le dit pas. J'aurais voulu un message du genre "aucune tâche visible pour vous, demandez à votre chef de service". »

Captures : M11-accueil.png, M11-recherche.png (recherche « propulsion », 0 résultat).

---

## Évaluation coordinateur

- Réussite attendue (tâche d'un autre service introuvable/refusée ; rôle limité à ses activités) : **Réussi** — aucune tâche de la propulsion visible, ni dans la liste ni dans la recherche globale (10 catégories).
- Frontière « aucune fuite de titre ou de contenu » : **conforme dans ce qui a été observé** (recherche « propulsion » : 0 résultat ; « Recette » : uniquement des objets propres). **Non testé** : accès direct par identifiant (consigne donnée au marin de ne pas deviner d'adresse) — à couvrir par `qa-securite`.
- Constats : absence de message explicatif en cas de résultat vide / accès restreint (ergonomie, P3) ; menu « Administration > Paramètres » et « Supervision > Prêt à appareiller » visibles pour une équipière (signalement répété, **à confirmer par test technique**).
