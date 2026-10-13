# Matrice de couverture

Légende : **P** prévu · **E** exécuté · **R** réussi · **X** échoué · **NT** non testé · **IV** impossible à vérifier avec les outils disponibles. Les statuts de cette table sont mis à jour dans `rapports/` ; l'état au SHA `59dd2f2` est dans `rapports/2026-10-13-passage-A-preparation.md`.

## Technique (équipe A)

| Id | Domaine | Contrôle | Agent | Statut |
|---|---|---|---|---|
| INT-01 | Tests Django | Suite complète sur SQLite | qa-integration | voir rapport |
| INT-02 | Migrations | `makemigrations --check`, migration depuis zéro, `seed_demo` relançable | qa-integration | voir rapport |
| INT-03 | PostgreSQL | Migrations et suite ciblée sur PostgreSQL (non éprouvées selon la PR) | qa-integration | voir rapport |
| INT-04 | Migration de données | `logistics` 0013 (stocks) et retour arrière | qa-integration | P |
| INT-05 | Cohérence | Tâche ↔ calendrier ↔ notification ↔ « Aujourd'hui » ↔ audit | qa-integration | P |
| INT-06 | Traçabilité | `AuditLog` sur tâches, listes, relève ; aucun écrasement silencieux | qa-integration | P |
| INT-07 | Transitions | Tâches, maintenances, listes de quarts, relève A/B, demandes, annonces | qa-integration | P |
| INT-08 | Échéances | Notifications, rappel unique d'accusé, test intermittent déclaré | qa-integration | P |
| INT-09 | Concurrence et saisie | Double soumission, valeurs limites, session expirée | qa-integration | P |
| INT-10 | Dégradé | Redis/Celery absents, WeasyPrint absent | qa-integration | P |
| SEC-01 | RBAC | Droits par fonction (et non par grade) pour chaque rôle de démo | qa-securite | P |
| SEC-02 | Périmètres | Section, secteur, service, accès direct par identifiant (IDOR) | qa-securite | P |
| SEC-03 | Isolation | Bretagne/Normandie ; équipage A/B, lecture seule, exception de réponse contextuelle | qa-securite | P |
| SEC-04 | Données privées | Tâche personnelle privée, pièces jointes, documents | qa-securite | P |
| SEC-05 | Serveur | Vues web, API DRF, HTMX, exports : contrôle côté serveur | qa-securite | P |
| SEC-06 | Validations | Visa vers le COMA du service ; chef de liste ; référent formation ; publication | qa-securite | P |
| SEC-07 | Sessions | Poste partagé, déconnexion, mot de passe provisoire | qa-securite | P |
| ERG-01 | 1366×768 | Pages du menu, débordement, console (déclaré dans `docs/RECETTE.md`, un seul rôle) | qa-ergonomie | déclaré, P |
| ERG-02 | Clavier et contrastes | Focus, ordre de tabulation, clair/sombre | qa-ergonomie | P |
| ERG-03 | Impression | A4 formations, quarts, feuille de service, tâches | qa-ergonomie | P |
| ERG-04 | Performance | Requêtes et poids de pages sur « Aujourd'hui », calendrier, tâches | qa-ergonomie | P |
| ERG-05 | Hors ligne | Aucune ressource externe (CDN, polices) | qa-ergonomie | P |
| ERG-06 | Mobile | Contrôles secondaires déclarés | qa-ergonomie | déclaré, P |

## Fonctionnel (équipe B, missions de `missions-aveugle.md`)

| Parcours demandé | Missions | Personas | Statut |
|---|---|---|---|
| Accueil quotidien | M01 | Lucas | P (IV : pas de navigateur MCP) |
| Calendrier, tâches, notifications | M01, M02 | Lucas | P (IV) |
| Affectation et suivi par les chefs | M05, M06, M08 | Claire, Antoine | P (IV) |
| Quarts, gardes, échanges, publication | M10 | Chef de liste | P (IV) |
| Absences et conflits | M08, M10 | Antoine, chef de liste | P (IV) |
| Maintenance préventive et corrective | M03, M09 | Julien, Antoine | P (IV) ; données de Julien manquantes |
| Anomalies, demandes, réponses contextuelles | M02, M03, M12 | Lucas, Julien, équipage B | P (IV) |
| Documentation et comptes rendus | M03, M04 | Julien | P (IV) |
| Formations, qualifications, validations | M17 | Référent formation | P (IV) |
| Annonces et accusés | M01, M13 | Lucas, commandements | P (IV) |
| Double équipage et relève | M12, M13 | Équipage B, commandements | P (IV) |
| Suivi technique COMANAV | M15 | COMANAV | P (IV) |
| Service courant et COMAEQ | M14 | COMAEQ | P (IV) |
| Acteurs à terre | M16 | Soutien à terre | P (IV) |
| Administration et limites | M07, M11, M18 | Claire, Noémie, admin navire | P (IV) |

Profils non joués = **non testés**. Aucun profil n'a été joué à ce jour.
