# Notifications par régime (MER / QUAI / COMMUNES / TRANSITION) — catalogue et classification proposée

Statut : **principe validé par le PO et implémenté** (régime et icône portés par la notification ; programme et relèves COMMUNES, échanges à quai QUAI). Aucune notification n'est supprimée ni masquée selon le mode. Précision : une notification est **urgente** quand son niveau est « Urgent » ou qu'elle demande une action ; le niveau « Important » ne suffit pas.
Source : relevé automatique de tous les points de création de notification du code (68 sites, 24 modules), puis regroupement par famille.

## 1. Principes proposés

1. La classe est une **étiquette de priorité d'affichage**, jamais un filtre : une notification n'est ni supprimée ni masquée à cause du mode du bâtiment.
2. Ordre d'affichage : d'abord les notifications de la classe du **mode courant**, les **COMMUNES** et les **TRANSITION** ; ensuite celles de l'autre mode, regroupées et repliées (« Autres régimes »), toujours consultables.
3. Une notification **urgente** (niveau « Urgent », ou action requise du destinataire non encore traitée) reste toujours dans le premier groupe, quelle que soit sa classe.
4. Mode **non renseigné** : aucun regroupement, ordre chronologique habituel.
5. Les notifications déjà reçues gardent la classe COMMUNES : **pas de reclassement rétroactif** de l'historique.
6. Mise en œuvre (après validation) : un champ nullable `regime` sur la notification, valeur par défaut COMMUNES, renseigné aux seuls points de création listés ci-dessous.

## 2. Catalogue et classification proposée

### Quarts à la mer — MER
| Source | Notification | Niveau | Classe |
|---|---|---|---|
| `quarts/models.py` (liste de quarts) | Proposition à valider : le quart attend votre publication | Attention | MER |
| `quarts/models.py` | Liste publiée : vous êtes affecté(e) au quart « … » | Info | MER |
| `quarts/models.py` | Modification de la liste publiée : vous êtes affecté(e) / retiré(e) du quart | Attention | MER |

### Services à quai, listes et activation — QUAI
| Source | Notification | Niveau | Classe |
|---|---|---|---|
| `quarts/models.py` (service à quai) | Proposition à valider / liste publiée / modification de la liste publiée | Info / Attention | QUAI |
| `quarts/activation.py` | La liste est maintenant active : votre service est confirmé | Info | QUAI |
| `quarts/alertes_activation.py` | Rappel H−30, alerte à l'heure prévue, escalade H+15 | Info / Attention | QUAI (urgentes) |
| `quarts/echanges.py` | Demande, acceptation, refus, annulation, validation, application, blocage d'un échange de tour | Info / Attention | QUAI |

### Passage mer ↔ quai — TRANSITION
| Source | Notification | Niveau | Classe |
|---|---|---|---|
| `quarts/mouvements.py` | Accostage confirmé sans liste applicable (aucune liste préparée / prévisionnelle non activée) | Attention | TRANSITION (urgente) |
| *(à venir, étape suivante)* | Correction ou annulation d'un mouvement du bâtiment | Attention | TRANSITION |

### Feuille de service (V1 : bâtiment à quai) — QUAI
| Source | Notification | Niveau | Classe |
|---|---|---|---|
| `quarts/models.py`, `quarts/rectificatif.py`, `quarts/alertes.py` | Visa attendu, renvoi pour correction, correction par le COMAEQ, publication « vous êtes de service », rectificatif à préparer, organisation d'alerte à valider, postes d'alerte non armés | Info / Attention | QUAI |

### Relève d'équipage et passation — COMMUNES
| Source | Notification | Niveau | Classe |
|---|---|---|---|
| `matrix/core/equipage.py` | Relève proposée / validée / refusée / appliquée / annulée, validation de secours | Info / Attention | COMMUNES |
| `dashboard/passation.py` | Synthèse de passation disponible | Info | COMMUNES |

### Modules indépendants du régime — COMMUNES
| Famille | Sources | Exemples |
|---|---|---|
| Tâches | `taches/services.py` | Assignation, changement de statut, clôture |
| Demandes (difficultés signalées) | `demandes/services.py` | Prise en charge, décision, tâche liée |
| Maintenance et installations | `maintenance/diffusion.py`, `maintenance/*_web.py`, `maintenance/models.py`, commandes `generate_installation_*` | Compte rendu saisi, anomalie détectée, échéances |
| Anomalies et logistique | `logistics/anomalie_views.py`, `logistics/web_views.py` | Anomalie signalée, changement de statut, ticket assigné |
| Fiches et propositions de matériel | `assets/fiche_validation.py`, `assets/proposition_article.py`, `assets/fiche_signalement.py` | Version à valider, validée, refusée |
| Documentation et RETEX | `documentation/services.py`, `retex/services.py` | Document à valider, publié, refusé ; RETEX à examiner |
| Formations | `training/web_views.py`, `training/models.py` | Réservation, candidature, désignation, validation |
| Absences | `absences/services.py` | Absence déclarée, enregistrée, validée |
| Annonces et programme | `annonces/services.py`, `programme/services.py` | Annonce, rappel, événement (le niveau de l'annonce est conservé) |
| Messagerie | `threads/mentions.py` | Vous avez été cité |

## 3. Points à trancher
1. **Programme** : un événement du programme annonçant un appareillage ou un accostage prévu doit-il être TRANSITION ? Proposition : non en V1.1 (le programme ne change jamais le mode), il reste COMMUNES.
2. **Relève d'équipage** : COMMUNES (proposé) ou TRANSITION ? Une relève n'est pas un changement de mode du bâtiment.
3. **Échanges de tour** : QUAI (proposé, car ils portent sur les services à quai) ; confirmer que cela ne gêne pas un marin qui ne reçoit que des quarts.
4. Valider les cinq principes de la section 1, notamment l'absence de reclassement de l'historique.

## 4. Repérage visuel : une icône par catégorie métier (orientation PO)

Principes : sobriété et homogénéité ; icônes reconnaissables ; **la couleur ne sert qu'à la gravité ou à la priorité**, jamais à décorer ; libellé textuel toujours présent ; lisibilité en thèmes clair et sombre ; pas de texte explicatif en plus. Aucune catégorie métier nouvelle : on réutilise la table centrale des icônes (`matrix/core/icones.py`, Bootstrap Icons auto-hébergées).

| Catégorie | Concept d'icône existant | Icône |
|---|---|---|
| Quarts à la mer et listes de quarts | `quart` | horloge |
| Services à quai, feuille de service, passation | `calendrier` | calendrier |
| Échanges de tours | **`echange` à ajouter à la table** (déjà utilisée en dur dans les gabarits d'échange) | flèches d'échange |
| Maintenance et installations | `maintenance` | outils |
| Anomalies et tickets correctifs | `anomalie` | triangle d'avertissement |
| Tâches et demandes | `tache` | liste de contrôle |
| Messagerie (mentions, discussions) | `discussion` | bulle |
| Documents, RETEX, fiches | `document` | fichier |
| Validations (accordée, publiée, validée) | `terminee` | coche |
| Alertes d'activation et d'accostage | `anomalie` | triangle d'avertissement |
| Formations et absences | `formation`, `absence` | existants |
| Annonces et programme | `annonce` | porte-voix |

Mise en œuvre prévue avec D7 (après validation de la classification) : l'icône se déduit de la source de la notification (module émetteur ou type de l'objet visé) par une table unique, sans refondre le système ; la gravité reste portée par la couleur du badge existant ; les notifications sans catégorie reconnue gardent l'icône actuelle.

