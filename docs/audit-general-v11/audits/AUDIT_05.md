# Audit 05 — UX, cohérence et accessibilité (rapport partiel : navigateur réel)

**Statut : partiel, non terminé.** Chromium (Playwright) piloté contre l'instance de démonstration temporaire (`runserver` sur 127.0.0.1:8800, SQLite temporaire, `DJANGO_DEBUG=1`). Scripts : `sondes/navigateur/*.js`. Les captures sont dans l'environnement d'audit et **ne sont pas versionnées** (elles ne sont pas des preuves rejouables, les scripts le sont).

**Limites** : un seul navigateur, Linux, résolution de référence 1366×768 puis 375×667 ; maquettes UX V1.1 et charte `design/` **non comparées** (sous-module non initialisé, prototypes non confrontés) ; mode sombre, impression, tablette tactile, lecteur d'écran, postes anciens : non testés.

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

## 3. Non audité

Comparaison aux maquettes approuvées (A et B de la page d'entrée « Quarts »), densité réelle, temps de saisie, aides contextuelles, cohérence des libellés entre modules, impressions A4, erreurs de formulaire, perte de saisie à la déconnexion automatique (15 min).

## 4. Anomalies liées

AUD-008, AUD-014, AUD-016, AUD-018.
