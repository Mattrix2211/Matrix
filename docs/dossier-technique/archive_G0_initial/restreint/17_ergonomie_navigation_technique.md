# Chapitre 17 (technique) — Interface et ergonomie : mécanismes

> **Diffusion restreinte.** Complète `diffusable/17_ergonomie_navigation.md` (à lire d'abord). **État décrit :** état B (`6d6d0be`), non fusionné dans `main`. Légende : 🟢 réel vérifié, 🔵 cible, ⚪ non vérifié.
> **Pour qui :** développeurs, administrateurs. **Ce que vous y trouverez :** les composants de l'interface, leur emplacement dans le code, les réglages et les contrôles.

---

## 17T.1 Gabarits, composants et ressources

| Élément | Emplacement |
|---|---|
| Gabarit de base, composants, pages d'erreur | `matrix/templates/base.html`, `matrix/templates/components/`, `400.html`, `403.html`, `404.html`, `500.html` |
| Gabarits par module | `matrix/templates/<module>/` (absences, accounts, annonces, assets, calendar, dashboard, demandes, documentation, logistics, maintenance, postes, programme, quarts, retex, settings, taches, threads, training) |
| Feuilles de style | `matrix/static/css/` : `fonts.css`, `matrix.css`, `naval_premium.css`, `impression.css` |
| Bibliothèques embarquées | `matrix/static/vendor/` : bootstrap, bootstrap-icons, chartjs, fullcalendar, htmx |
| Polices embarquées | `matrix/static/fonts/` : inter, jetbrains-mono, space-grotesk |
| JavaScript maison (sans dépendance) | `matrix/static/js/` : `grille.js`, `brouillon.js`, `aide_progressive.js`, `preferences.js`, `inactivite.js`, `barre_laterale.js`, `theme.js`, `recherche.js`, `push.js`, `service-worker.js`… |
| Manifeste | `matrix/static/manifest.json` (affichage « standalone », `start_url` « / ») |
| Styleguide | route `styleguide/` (`matrix/urls.py:61`) |
| Balises de gabarit | `matrix/core/balises_composants.py`, `matrix/core/balises_icones.py` |

## 17T.2 Navigation

- Groupes et entrées : `matrix/core/navigation.py` (`GROUPES` :56) ; construction par personne `construire_navigation` (:134) ; groupes ouverts par défaut `GROUPES_OUVERTS_PAR_DEFAUT` (:107).
- Filtre de module : `matrix/core/modules.py` (registre des 14 modules désactivables) ; blocage par URL : `ModuleActivationMiddleware` (`matrix/core/middleware.py:210`). **La désactivation ne vaut que pour les vues web** : l'API REST, les tâches Celery et les enchaînements internes continuent de fonctionner.
- Préférences d'interface par compte (groupes du menu, aides vues, thème, barre repliée) : `accounts/preferences.py` ; enregistrement par `preferences/` (`accounts/web_urls.py:12`) et `preferences.js` ; **jamais un contrôle d'accès**.
- Recherche : `matrix/core/recherche.py`, routes `search/` et `search/rapide/` (`matrix/urls.py:62`, `matrix/urls.py:63`).

## 17T.3 Chaîne de middlewares (ordre du réglage `MIDDLEWARE`)

1. `ContexteConfigurationMiddleware` — borne le mémo des versions de configuration à la requête.
2. Sécurité, session, commun, CSRF Django.
3. `SansNulMiddleware` — retire le caractère NUL des paramètres (erreur 500 sous PostgreSQL).
4. Authentification Django, puis `InactiviteMiddleware` (`matrix/core/inactivite.py:105`).
5. Messages, protection contre l'inclusion en cadre.
6. `IdentitePageMiddleware` (`matrix/core/middleware.py:165`) — écriture refusée si la page a été ouverte pour un autre marin.
7. `HabillageErreur400Middleware`, `BatimentCourantMiddleware`, `MotDePasseProvisoireMiddleware`, `ModuleActivationMiddleware`, `EquipageATerreMiddleware` (`matrix/core/middleware.py:310`), `ErreurSaisieMiddleware`.

## 17T.4 Réglages de l'interface (variables d'environnement)

| Réglage | Défaut | Effet |
|---|---|---|
| `INACTIVITE_DELAI_SECONDES` | 900 | Déconnexion automatique ; bornes 60 à 28 800 |
| `INACTIVITE_AVERTISSEMENT_SECONDES` | 60 | Préavis ; bornes 10 à la moitié du délai |
| `BROUILLONS_CONSERVATION_JOURS` | 30 | Purge des brouillons (0 = jamais) ; tâche `purger_brouillons` |
| `BROUILLONS_TAILLE_MAX` | 262 144 octets | Taille maximale d'un brouillon |
| `DOCUMENT_TAILLE_MAX_MO` | 20 | Taille maximale d'un document téléversé |

## 17T.5 Brouillons, confirmations, fichiers

- Brouillons : `matrix/core/brouillons.py` (`purger_brouillons_anciens` :70), route `brouillons/` (`matrix/urls.py:59`), script `brouillon.js`.
- Confirmations d'actes critiques : `matrix/core/confirmations.py` (`texte_confirmation` :27, `confirmation_web` :39, `confirmation_api` :44, `tracer_refus` :55) ; clés `maintenance_critique`, `remise_en_service`, `pret_appareillage`.
- Fichiers téléversés servis par `servir_media` (`matrix/core/medias.py:110`), après contrôle des droits ; en production, `MEDIA_ACCEL_REDIRECT` délègue l'envoi au serveur web (en-tête `X-Accel-Redirect`).
- Web Push : `matrix/static/js/push.js`, `matrix/static/js/service-worker.js` (aucun cache hors-ligne).

## 17T.6 Paramètres

`SettingsView` (`matrix/views.py:268`) : onglets et actions par rôle (seuils de rôle, modules, équipage, responsables, référentiels, unités, journal, paramètres des tâches, des annonces et de la passation, vibration). Les accès autres que l'administrateur général sont limités aux onglets listés au §17.8 du chapitre diffusable ; chaque action vérifie le droit **côté serveur** dans `dispatch`.

## 17T.7 Tests

Tests Django de l'interface (`matrix/tests/` : navigation latérale, composants, contrastes, inactivité, brouillons, grille, manifeste, pages d'erreur, modules activables, balayage de saisie, étanchéité d'équipage) et tests JavaScript sous Node : `matrix/tests/` (`grille.test.js`, `brouillon.test.js`, `compte_rendu.test.js`, `inactivite.test.js`).

## 17T.8 Limites

- ⚪ Aucune recette navigateur rejouée ; sous-module `design/` vide.
- ⚪ Les observations PO-xx de la recette V1.1 ne sont pas rapprochées une à une du code de l'état B.

---

**Sources (état B).** Références en ligne ; `docs/UX.md` ; `restreint/ECARTS_DECISIONS_CODE.md` (A11).
