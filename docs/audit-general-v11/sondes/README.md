# Sondes d'audit (non applicatives, rejouables)

Scripts d'exécution **jetables** qui ont produit les preuves des rapports. Ils ne font pas partie de l'application, n'écrivent jamais dans une base réelle (les écritures sont annulées par transaction ou faites dans une base temporaire) et ne doivent pas être lancés ailleurs que sur une base de démonstration temporaire.

## Rejeu complet en une commande (reproductibilité vérifiée)

```bash
PYTHON=/chemin/python docs/audit-general-v11/sondes/rejouer_tout.sh [dossier_de_travail_hors_depot]
```

Le script crée une base SQLite temporaire, applique les migrations, lance les **quatre** générateurs de démonstration, rejoue chaque sonde listée dans `attendus.json` et **compare la sortie aux lignes attendues** ; il échoue si un script est absent, si une sonde plante ou si une ligne attendue manque. Les sorties sont conservées dans `<dossier>/resultats/`. **Dernière exécution à partir de ce dossier versionné, sur une base neuve (2026-11-05) : 31 sondes conformes, 0 écart (dont les neuf sondes de la recette ciblée).** Prérequis : `pip install -r requirements.txt` dans un environnement hors dépôt ; aucun accès réseau.

Hypothèses connues : les sondes s'appuient sur les comptes de `docs/recette/01_COMPTES.md` et sur des identifiants créés par le pipeline complet (quart n° 2, bâtiment « Bretagne ») ; elles ne s'appliquent pas à `seed_demo` seul (certaines sorties diffèrent : AUD-008).

## Sondes côté serveur (client de test Django)

Chaque script se lance par `python manage.py shell < docs/audit-general-v11/sondes/<script>.py` avec `DJANGO_DEBUG=1`, `DJANGO_SECRET_KEY=…`, `MATRIX_SQLITE_PATH=…` (le dépôt `main` n'a pas `MATRIX_SQLITE_PATH` : sa base est `db.sqlite3` à la racine).

| Script | Preuve produite | Rapport |
|---|---|---|
| `sonde_routes_anonymes.py` | routes accessibles sans connexion | 06, 15 |
| `sonde_pages_par_profil.py` | création de feuille par 11 profils ; pages ouvertes par 10 profils | 06 |
| `matrice_droits.py`, `droits2.py` | porte d'autorisation et effets réels des écritures de quarts | 06 |
| `circuit.py`, `auto_visa.py`, `lecture_brouillon.py` | circuit de visa, double visa par une personne, lecture par état | 06, 09 |
| `cas_limites.py` | cas limites : listes publiées, délégations, cascades de suppression | 06, 09, 14 |
| `structure.py`, `structure2.py`, `api_org.py`, `archive.py`, `cascade.py`, `fk.py` | administration, suppression et archivage de la structure | 02, 14 |
| `suppr_compte.py`, `suppr2.py` | suppression d'un compte (AUD-034) | 14 |
| `nouveau_batiment.py` | simulation d'un nouveau bâtiment | 03 |
| `seuils_secu.py`, `seuil_inter.py` | effet d'un seuil, connexions répétées, étanchéité inter-bâtiments | 02, 15 |
| `ticket404.py`, `ticket404b.py`, `brouillons.py`, `liens_morts.py` | navigation et liens refusés | 04 |
| `calendrier.py`, `comm.py`, `stock.py`, `maintenance.py`, `mnt2.py`, `autres.py`, `recherche.py` | calendrier, communication, stock, maintenance, autres modules, recherche | 07 à 12 |
| `perf.py`, `prof.py` | durées et profil (AUD-013) | 17 |
| `sections2.py`, `demo.py`, `reg.py`, `comptes.py` | périmètre selon le rattachement, données de démonstration, registre de seuils | DP-03, 20 |
| `organisations_reelles.py` | cinq organisations de démonstration et variantes (COMAEQ vacant, COMAVIA, installations) | 19 |
| `couverture_demo.py`, `credibilite_demo.py` | couverture par profil et par état, crédibilité des données (lecture seule) | 20 |
| `prod_proxy.py`, `prod_proxy_reglages.py`, `config/reglages_proxy.py` | mode production : HTTP, proxy TLS, TLS natif (à lancer avec `DJANGO_DEBUG=0`, une vraie clé secrète, `DJANGO_ALLOWED_HOSTS=matrix.bord.local,testserver` ; la seconde avec `DJANGO_SETTINGS_MODULE=reglages_proxy` et `PYTHONPATH=…/config`) | 15 |
| `recette_rm12.py`, `recette_rm25_38_fiche_bord.py`, `recette_rm25_fiche_flotte.py`, `recette_rm26.py`, `recette_rm30.py`, `recette_rm39.py`, `recette_rm40.py`, `recette_rm41.py`, `recette_rm45.py` | recette métier ciblée : réaffectation d'installation, fiches du bord et de la flotte, cycle de vie du ticket, postes d'une fraction de service, RETEX, relève de double équipage, prêt à appareiller, vocabulaire du quart (écritures annulées par transaction) | 19 § 6 |
| `qualite_tests.py` | métriques statiques des tests (lancement direct par `python`, depuis la racine du dépôt) | 16 |
| `mutations/mutations*.py` | mutations de la logique de droits dans une copie jetable (`WT=<git worktree>` et `PYTHON=…` requis) | 16 |

## Sondes navigateur (Chromium via Playwright, `node`)

```bash
python manage.py runserver 127.0.0.1:8800 --noreload      # base de démonstration complète
node docs/audit-general-v11/sondes/navigateur/<script>.js [dossier_captures]
```

`e2e_lib.js` (aides) ; `e2e1` calendrier, événement personnel, tâche ; `e2e2`–`e2e4` tâche, maintenance, échange, annonce, documentation, anomalie ; `e2e5`–`e2e8` assistant d'anomalie, maintenance (non-conformité, confirmation critique) ; `e2e9`, `e2e10` formation, critique, discussion, RETEX, absence ; `nav1`–`nav10` accueil, menus, clavier, mobile, circuit de la feuille, paramètres ; `maquettes*.js` comparaison aux maquettes. **Ces scripts écrivent dans la base temporaire** (tâches, annonces, documents, échanges créés) : ne les lancer que sur une base jetable, et ne pas les enchaîner deux fois sans la recréer (certains parcours supposent un état initial).

## PostgreSQL jetable

Cluster local `initdb` sous un utilisateur système dédié, port 54329, puis `DB_HOST=127.0.0.1 DB_PORT=54329 DB_NAME=<base> DB_USER=matrix DB_PASSWORD=<jetable>` pour `migrate`, `seed_demo*`, `test`. Les sondes SQLite se rejouent à l'identique avec ces variables.

## Limites des sondes

Les sondes mesurent des **états de démonstration**, pas une exploitation réelle ; elles ne remplacent pas des tests ajoutés à la suite du projet (`05_MATRICE_NON_REGRESSION.md`). Les captures d'écran ne sont pas versionnées.
