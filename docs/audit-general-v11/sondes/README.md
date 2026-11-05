# Sondes d'audit (non applicatives)

Scripts d'exécution **jetables** qui ont produit les preuves des rapports. Ils ne font pas partie de l'application, n'écrivent jamais dans une base réelle et ne doivent pas être lancés ailleurs que sur une base temporaire de démonstration.

## Préparer une base temporaire (SQLite)

```bash
python -m venv /chemin/hors/depot/venv && /chemin/hors/depot/venv/bin/pip install -r requirements.txt
export DJANGO_DEBUG=1 DJANGO_SECRET_KEY=audit-temporaire MATRIX_SQLITE_PATH=/chemin/hors/depot/audit.sqlite3 DJANGO_ALLOWED_HOSTS=testserver,localhost
python manage.py migrate -v0 && python manage.py seed_demo
```

## Sondes côté serveur (client de test Django, écritures annulées)

Chaque script se lance par `python manage.py shell < docs/audit-general-v11/sondes/<script>.py`.

| Script | Preuve produite | Rapport |
|---|---|---|
| `sonde_routes_anonymes.py` | Routes accessibles sans connexion | AUDIT_06, AUDIT_15 |
| `sonde_pages_par_profil.py` | Création de feuille par 11 profils ; pages ouvertes par 10 profils | AUDIT_06 |
| `matrice_droits.py` | Porte d'autorisation des écritures de quarts (21 profils) | AUDIT_06 |
| `droits2.py` | Effets réels : désignation, création inter-équipage, voie directe | AUDIT_06 |
| `circuit.py`, `auto_visa.py` | Circuit de visa de la feuille, acteurs, double visa par une seule personne | AUDIT_06, AUDIT_09 |
| `ticket404.py`, `ticket404b.py` | Cause du 404 du ticket (AUD-008) | AUDIT_04 |
| `brouillons.py` | Reprise de brouillons (AUD-016) | AUDIT_04 |
| `liens_morts.py` | Liens refusés sur 42 comptes (3 778 requêtes) | AUDIT_04 |
| `perf.py`, `prof.py` | Mesures de durée et profil (AUD-013) | AUDIT_17 |
| `sections2.py` | Périmètre selon le rattachement (DP-03) | AUDIT_DP03_SECTIONS |
| `prod_proxy.py` | Mode production : HTTP, proxy TLS, TLS natif (AUD-011) ; à lancer avec `DJANGO_DEBUG=0`, une vraie clé secrète et `DJANGO_ALLOWED_HOSTS=matrix.bord.local,testserver` | AUDIT_15 |

Les identifiants de la démonstration (comptes `equipier_a`, `chef_secteur_a`…) viennent de `docs/recette/01_COMPTES.md` ; les dates utilisées (2027) sont arbitraires. Certains scripts dépendent d'identifiants créés par `seed_demo` (ticket n° `1a696760-…`, quart n° 2) : ils sont à adapter si les données changent.

## Sondes navigateur (Chromium via Playwright)

```bash
python manage.py runserver 127.0.0.1:8800 --noreload      # même environnement que ci-dessus
node docs/audit-general-v11/sondes/navigateur/nav1.js /chemin/hors/depot/captures
```

`nav1` : accueil de 7 profils ; `nav2` : ticket, brouillon, interface de la feuille ; `nav3` : assistant de signalement (exploratoire) ; `nav4` : titres, menus, clavier, téléphone ; `nav5` et `nav7` : circuit de la feuille et boutons de visa par profil ; `nav6` : modale de confirmation d'un visa. Les scripts `nav5` et `nav7` écrivent dans la base temporaire (dates 2027-09-01 et 2027-09-02).

## PostgreSQL jetable

Cluster local `initdb` sous un utilisateur système dédié, port 54329, base `matrix_audit`, puis `DB_HOST=127.0.0.1 DB_PORT=54329 DB_NAME=matrix_audit DB_USER=matrix DB_PASSWORD=<jetable>` pour `migrate`, `seed_demo` et `test`.
