# Chapitre 9 (technique) — Communication : mécanismes

> **Diffusion restreinte.** Complète `diffusable/09_communication.md` (à lire d'abord). **État décrit :** état B (`6d6d0be`), non fusionné dans `main`.
> **Pour qui :** développeurs, administrateurs. **Ce que vous y trouverez :** les modèles de `threads` (3), `annonces` (4) et `notifications` (2), les règles de droits exactes, la création des notifications, le Web Push, la recherche et les tâches planifiées.

---

## 9T.1 Discussions (`threads`)

| Élément | Détail |
|---|---|
| `Thread` (`threads/models.py:11`) | Fil attaché à un objet par **relation générique** (`content_type`, `object_id`) ; créé à la première réponse |
| `Message` (`:19`) | `author`, `body`, `is_system` (messages produits par le système), `mentions` (M2M vers `User`) |
| `Attachment` (`:27`) | Fichier (validateur `valider_document`) lié à un message ; livré par le service protégé des médias (`thread_attachments/`) |
| `ajouter_commentaire` (`threads/utils.py:30`), `commentaires_de` (`threads/utils.py:18`), `contexte_discussion` (`threads/utils.py:41`) | Interface utilisée par les modules : **le contrôle d'accès reste porté par la vue appelante, sur l'objet parent** ; ces fonctions ne recréent aucun système de droits |
| Mentions (`threads/mentions.py`) | Signal `post_save` sur `Message` : une mention `@identifiant` (`_MENTION`) crée une alerte « **Réponse attendue** » pour le marin cité, **soldée** quand il répond dans le fil (`traiter_actions`) ; ignoré pour les messages système ou sans auteur |
| API REST (`threads/views.py`) | `ThreadViewSet`, `MessageViewSet`, `AttachmentViewSet` sous `/api/threads/` ; écriture au seuil `thread_ecriture` (chef de section par défaut) ; **lecture bornée** par `_filtre_perimetre_threads` aux fils des **tickets** et des **occurrences de maintenance** du périmètre (tout autre type reste masqué côté API) ; un utilisateur à terre garde les fils des bâtiments suivis |

## 9T.2 Annonces (`annonces`)

| Élément | Détail |
|---|---|
| `Annonce` (`annonces/models.py:14`) | `niveau` (réutilise `NotificationLevel` : Information, Important, Urgent), `accuse_requis`, `date_effet`, `date_fin`, `archivee`, cible (bâtiment, service, secteur, section, équipage), `auteur` |
| `VersionAnnonce` (`:47`) | Version conservée à chaque modification |
| `LectureAnnonce` (`:60`) | Lecture ou accusé d'un marin ; **la date est celle de la première** |
| `ParametresAnnonces` (`:71`) | Réglage commun à la flotte, dont `jours_rappel_accuse` |

| Question | Fonction (`annonces/services.py`) | Règle |
|---|---|---|
| Qui publie | `peut_publier` (`:99`) | Pas d'équipage à terre en lecture seule ; `niveau_pour_action` ≥ seuil `annonce_publication` (**chef de service**, avec exception explicite `ouverte_au_second` : le commandant en second est comparé à son **grade**) |
| Qui peut cibler quoi | `cibles_autorisees` (`:81`), `resoudre_cible` (`:117`) | Son niveau de périmètre et ce qui en dépend ; équipages réels du bâtiment (`equipages_du_navire`) |
| Qui est le public | `filtre_public` (`:143`), `filtre_ciblage`, `filtre_gestion` | Résolus en filtres `Q` (sur `User`, ou sur un modèle ciblé) |
| Qui consulte / gère | `peut_consulter` (`:207`), `peut_gerer` (`:211`), `annonces_gerees` (`:200`) | Auteur, périmètre de publication |
| Modifier | `modifier` (`:255`) | Nouvelle version ; prévient le public déjà informé ; accusés à renouveler ; `ConflitVersion` si l'annonce a changé depuis l'affichage du formulaire |
| Diffuser | `diffuser` (`:299`), `diffuser_du_jour` (`:308`) | Une seule fois, à la date d'effet ; tâche `diffuser_annonces_hourly` |
| Rappeler | `rappeler_accuses` (`:316`) | Une seule fois, N jours après la diffusion ; tâche `rappeler_accuses_annonces_daily` (07:15) |
| Lire | `marquer_lue` (`:346`), `a_lire` (`:367`), `suivi_lecture` (`:382`) | Ouvrir suffit sans accusé ; sinon accusé de la **version courante** |

Routes : `/annonces/`, `/annonces/nouvelle/`, `/annonces/<id>/`, `…/action/`.

## 9T.3 Notifications (`notifications`)

- **Modèle** `Notification` (`notifications/models.py:28`) : `user`, `verb`, `level`, `is_read`, **cible générique** (`content_type`, `object_id`, `target`), `url` (chemin interne quand il n'y a pas d'objet), `action_requise`, `traitee_le`, `regime`, `categorie`. `NotificationLevel` (`:10`) : `info`, `warning`, `danger` ; `RegimeNotification` (`:20`) : `MER`, `QUAI`, `COMMUNES`, `TRANSITION`. `PushSubscription` (`:49`) : abonnement Web Push (endpoint unique, clés `p256dh` et `auth`).
- **Création** : directe (`Notification.objects.create`) ou **en masse** par `creer_notifications_en_masse` (`notifications/services.py:30`), **seul point d'entrée autorisé** pour une création groupée (le `bulk_create` ne déclenche pas le signal d'envoi du Web Push). `traiter_actions` (`:54`) solde les alertes d'action quand la source est résolue ; `compter_non_lues` (`:25`) est l'unique source du compteur.
- **Signal** (`notifications/signals.py`) : `post_save` sur `Notification` → envoi Web Push **si niveau `danger`**.
- **Web Push** (`notifications/push.py`) : `push_disponible` (`:32`) ; `envoyer_notification_push` (`:46`) ; clés VAPID en variables d'environnement ; durée totale bornée par `WEBPUSH_DELAI_MAX` (3 s) tous appareils confondus ; sans `pywebpush` ou sans clés, envoi simplement désactivé. API d'abonnement : `/api/notifications/push/public-key/`, `…/subscribe/`, `…/unsubscribe/`.
- **Liens** (`notifications/liens.py`) : `liens_accessibles` (`:13`) et `lien_objet` (`:32`) : un résolveur **par type d'objet**, qui reprend le contrôle d'accès de la fiche détail ; aucun lien vers un objet interdit.
- **Régimes** (`notifications/regimes.py`) : `repartir(notifications, mode)` sépare « prioritaires » et « autres régimes » selon le **mode du bâtiment** (`mode_du_batiment_de`, chapitre 8) ; **jamais de suppression** ; une notification `danger` ou `action_requise` non traitée est toujours prioritaire (`est_urgente`).
- **Panneau et centre** (`notifications/web_views.py`) : flux court = non lues **ou** action requise non traitée, trié par action puis niveau puis date ; les lues restent dans le centre ; routes `/notifications/` (centre), `/notifications/panneau/`, `/notifications/compteur/`, `…/tout-lu/`, `…/<id>/lue/`.
- **Tâches planifiées** (`notifications/tasks.py`) : `notify_ma_journee`, `notify_ma_journee_demain` (chaque minute, décision par marin selon `notification_time` et `notification_time_soir`), `notify_taches_en_retard` (07:00), `notify_maintenance_echeance_proche`, `notify_low_stock`, `notify_expiring_training`, `notify_overdue_occurrences`, `generate_installation_notifications`, `generate_installation_maintenance_notifications`, `detect_installation_drift` (08:30) (chapitre 21).

## 9T.4 Recherche (`matrix/core/recherche.py`)

- `normaliser` (`:36`) : terme nettoyé, borné ; vide s'il fait moins de `MIN_CARACTERES` (2). `rechercher` (`:197`) parcourt `CATEGORIES` (`:182`) : **8** catégories (`installations`, `materiels`, `tickets`, `anomalies`, `formations`, `documents`, `taches`, `marins`), saute celles dont le **module est désactivé** (`module_actif_pour_user`), limite à `PAR_CATEGORIE` (5) résultats et ajoute un lien « Tout voir » vers la liste filtrée (`?q=`) quand elle le supporte.
- Chaque catégorie **réutilise le périmètre de ses vues de liste et de détail** (`scope_filters_for_user`, `build_scope_q`, `anomalies_visibles`) ; `icontains` échappe lui-même `%` et `_` : aucun SQL brut.
- Routes : `/search/` (page) et `/search/rapide/` (barre).

## 9T.5 Tests

`notifications/tests/` (165 fonctions de test), `annonces/tests/` (46), `threads/tests/` (30).

## 9T.6 Limites et éléments non vérifiés

- ⚪ Relations génériques (`Thread`, `Notification`) non contrôlées face à la suppression d'un objet visé (chapitre 19).
- ⚪ La requête de `peut_publier_liste` / `publicateurs_a_notifier` (chapitre 8) boucle sur les utilisateurs actifs ; mesure de performance non faite.
- ⚪ Web Push : **HTTPS requis** hors développement ; non éprouvé sur appareil réel ; navigateurs concernés non étudiés.
- ⚪ Le courrier électronique n'est pas utilisé pour les notifications (configuration console par défaut).
- 🔵 Espaces de groupe, chat bord–terre, recherche universelle étendue : non développés.

---

**Sources (état B).** Références en ligne ; `couverture/etat_B/INVENTAIRE.md` (tâches planifiées, signaux : `threads/mentions.py:25`, `notifications/signals.py:9`).
