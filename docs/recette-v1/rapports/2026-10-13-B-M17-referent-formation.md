# Passage B — M17 — Référent formation (compte `referent_formation_a`, agent `marin-complementaire`)

| Champ | Valeur |
|---|---|
| SHA testé | `5ea072d897f79955b8d50def62f055a7090ddd5d` (branche `claude/recette-v1-passage-b`) |
| Base | SQLite jetable, `DJANGO_DEBUG=1`, `migrate` + `seed_demo` + `seed_recette`, rejouée avant la mission |
| Navigateur | Chromium headless, 1366×768, serveur MCP `playwright`, session fermée avant |
| Date | 2026-10-13 |
| Exécuté | Mission M17 par `marin-complementaire` (profil : référente formation pour certaines formations, copié de `personas-comptes.md`) |
| Durée mesurée par l'outil (agent entier, 29 appels d'outils) | 74,4 s |

Compte rendu du marin, tel que reçu (captures `M17-*.png` dans `captures/`).

---

COMPTE RENDU M17 – Solène (compte referent_formation_a)

Réussite : partielle.
- Fait : la candidature d'Omar est passée par « Sélectionner ». J'ai aussi affecté Julien à la session du 31/10 pour sa qualification qui expire le 02/11/2026.
- Pourquoi partielle : je n'ai aucune preuve visible du résultat de la sélection d'Omar. Je ne suis pas sûre non plus que « sélectionner » soit bien ce qu'on attendait de moi.

Chemin suivi, écran par écran
1. Connexion : champs « Utilisateur » et « Mot de passe », bouton « Se connecter ».
2. Accueil « Bonjour Second-maître Referent Formation A ». Cloche « Notifications » avec le badge « 2 notifications non lues ».
   - Les « À faire » ne sont que deux annonces à accuser.
   - Aucune notification ne parle de la candidature ni de l'échéance.
3. Clic sur la cloche : rien ne s'ouvre ni ne change à l'écran, ce que j'ai constaté sur le snapshot. Je ne peux donc pas lire mes 2 notifications.
4. Menu Compétences > Formations (/formations/). Bloc « Candidatures transmises — sélection de l'organisme ».
   - Contenu : « Omar Equipier Incendie A — candidature à « [Recette] Conduite du réseau incendie » », étiquette « Transmise à l'organisme », boutons « Sélectionner » et « Refuser ».
5. Pour décider en connaissance de cause, j'ai ouvert la fiche « [Recette] Conduite du réseau incendie » (/formations/5/).
   - Je l'ai ouverte en tapant l'adresse, alors que j'aurais pu cliquer sur le lien de la liste. C'est une entorse mineure.
   - La fiche indique : session du 31/10/2026 à 09:00 au Centre de formation, 4 places sur 4.
   - « Référents (votre unité) : Solène Referent Formation A ».
   - « Dernières validations » : Julien Equipier A3, validée le 02/11/2024, expire le 02/11/2026, « À jour ».
   - Menu « Autres actions » : seulement « Arbre de compétences ».
6. Retour à la liste (retour arrière), clic sur « Sélectionner ». Le bloc des candidatures a disparu. Aucun message de confirmation visible.
7. Retour sur la fiche 5. Je n'y vois aucune trace d'Omar : pas de liste de participants, et toujours 4 places sur 4.
8. Sur la fiche 5, dans « Marin à affecter », choix de « Julien Equipier A3», puis « Affecter ».
   - Retour automatique sur la liste /formations/, sans message.
   - Sur la fiche, la session passe à « 3 place(s) restante(s) sur 4 ». C'est la seule confirmation.

Mesures
- Environ 12 actions utiles : connexion, cloche, formations, ouverture de la fiche, menu « Autres actions », retour, « Sélectionner », fiche, choix de Julien, « Affecter », fiche.
- Environ 9 changements d'écran.
- 1 retour arrière.
- Durée non mesurée.

Hésitations et détours
- La cloche muette m'a fait chercher ailleurs.
- Je ne savais pas où voir les qualifications proches de l'échéance. Les compteurs de la page Formations (« À renouveler 0 », « Expirées 0 ») ne concernent que moi. Je n'ai trouvé la date du 02/11 de Julien que sur la fiche de formation, dans « Dernières validations ».
- Après « Sélectionner », je ne savais pas ce qui s'était passé.

Termes ambigus
- « Candidatures transmises — sélection de l'organisme » : je ne comprends pas si c'est moi ou l'organisme qui sélectionne.
- « Transmise à l'organisme » : à quel stade est la candidature, et qui l'a transmise ?
- « Non suivie » : je ne sais pas si c'est mon état personnel ou l'état de la formation.
- « Marins à jour : 1 » : de quelle unité ?

Retour du système
- Aucune confirmation claire, ni pour « Sélectionner » (le bloc disparaît simplement), ni pour « Affecter » (retour sur la liste sans message).
- Aucun message d'erreur rencontré.
- Je n'ai pas pu vérifier si Omar est informé.

Correction d'erreur
- Aucun bouton « Annuler » ou « Défaire » après « Sélectionner » ou « Affecter ». Je n'ai pas vu comment retirer Julien de la session.
- « Refuser » : je ne l'ai pas utilisé, donc je ne sais pas s'il demande un motif.

Droits constatés
- Bien : je suis référente de la formation 5 et je peux traiter les candidatures de mon unité (équipage A). Je peux aussi affecter des marins à la session.
- À signaler : la liste « Marin à affecter » propose toutes les personnes du navire, y compris l'équipage B (Marc Marin B, Benoît Cdt B, Ivan Chef Secteur B) et l'administrateur.
- À signaler : le bouton « Valider une formation » est visible sur la page Formations. Je ne l'ai pas utilisé, par prudence. À vérifier : une référente le voit-elle pour toutes les formations, même celles dont elle n'est pas référente ?
- Je n'ai pas vérifié les fiches 4 et 6 pour voir si je suis référente de ces formations aussi.
- Le bouton « Réserver une place » est visible pour moi, ce qui est normal pour tout marin.

Avantage perçu face au papier/Excel
- La liste des candidatures avec « Sélectionner » et « Refuser » en un clic est rapide.
- Le compteur de places qui se met à jour est utile.
- Mais sans confirmation, sans liste des inscrits et sans alerte d'échéance, je garderais un Excel à côté pour vérifier.

Verbatim (ressenti de Solène)
- « Ça va vite, mais je clique et rien ne me dit que c'est bien pris en compte. »
- « Où vois-je les qualifications de mon équipage qui arrivent à échéance ? »

Captures : M17-accueil.png, M17-notifications.png, M17-apres-selection.png, M17-apres-affectation.png. Le marin n'a pas pu relire leur contenu ; ses constats viennent des snapshots.

---

## Évaluation coordinateur

- Réussite attendue (validation limitée au cours dont il est référent) : candidature de son ressort **traitée** (« Sélectionner », bloc disparu), affectation de Julien confirmée par « 3 place(s) restante(s) sur 4 » (compteur, **preuve indirecte**). L'effet de « Sélectionner » sur la candidature d'Omar n'est pas visible (**Exécuté, non prouvé** pour le statut final).
- Frontière « candidature d'un autre périmètre refusée » : la seule candidature affichée est celle de son ressort ; la candidature hors ressort prévue par `seed_recette` (« Travaux en hauteur ») **n'est pas apparue** dans le bloc — **cohérent avec la frontière attendue** (absence d'exposition), mais le refus explicite (tentative d'instruction) est **Non testé**.
- **Signalement à confirmer (non confirmé)** : la liste « Marin à affecter » propose le personnel de l'équipage B, des commandants et l'administrateur (même famille de signalement que M05/M06/M09/M14) ; bouton « Valider une formation » visible pour une référente (portée à vérifier).
- Constats : cloche de notifications sans effet visible pour ce compte (hypothèse : artefact de l'outil ou défaut du panneau — non reproduit ailleurs : cf. M12 où le panneau s'ouvre ; **à confirmer**) ; aucune confirmation après « Sélectionner » / « Affecter » (P2) ; pas de vue des qualifications de l'équipage proches de l'échéance pour la référente (fonction manquante ou difficile à découvrir, P2) ; absence de bouton d'annulation.
