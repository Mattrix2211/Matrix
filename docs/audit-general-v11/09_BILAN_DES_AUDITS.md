# Bilan précis des audits : clos, partiels, bloqués

Date : 2026-11-05. Commit audité `1c37f22`. Un audit n'est **clos** que si ses questions centrales ont une réponse prouvée sur un périmètre écrit **et** qu'aucune vérification essentielle ne reste à faire. Sinon il est **partiel**, avec la liste de ce qui reste. **Aucun audit n'est clos sans réserve.**

| N° | Audit | Statut | Prouvé par exécution | Vérifications essentielles restantes | Blocage réel |
|---|---|---|---|---|---|
| 01 | Besoin et historique | Partiel | Notion (hub + 13 pages), 16 titres de PR, décompte du backlog, registre de 48 exigences | lecture des 380 tâches et des descriptions de PR | conversations ChatGPT, documents FANLAB propres, `MATRIX_V11_AUDIT_INDEPENDANT.md` non disponibles |
| 02 | Configurabilité | Partiel | seuils réglables (35 actions), écran et API de structure, 55 droits en dur | parcours complet d'un bord en navigateur (création d'unité par l'écran du compte de flotte, effet d'un changement de seuil) | décisions A1 à A4 (bloc A) pour figer les conclusions |
| 03 | Première mise en service | Partiel | `migrate` + démo sur SQLite et PostgreSQL, procédure du README, autonomie de configuration | simulation complète d'un nouveau bâtiment par l'interface ; `setup.bat`, `start.bat`, `lancer_demo.bat` | Windows non disponible |
| 04 | Usage quotidien | Partiel | 8 468 requêtes de navigation, causes de AUD-008/016/027, brouillons | parcours bout en bout (signalement jusqu'à l'envoi, tâche bloquée, fin de journée), temps de saisie | aucun technique ; un marin utilisateur pour mesurer l'efficacité |
| 05 | UX et accessibilité | Partiel | accueil 7 profils, menus 3 profils, mobile 375, clavier, comparaison aux 2 maquettes et à la charte | mode sombre, impression A4, tablette, lecteur d'écran, formulaires d'erreur, autres écrans | tablette réelle et lecteur d'écran |
| 06 | Rôles et permissions | Partiel | quarts et feuille : 1 407 + 196 + circuit ; formation, stock, structure, API org, calendrier ; deux jeux de données | autres modules (tâches, annonces, documents, fiches, programme), délégations, cache des permissions | décisions du bloc B pour juger des cas ouverts |
| 07 | Calendrier | Partiel | 7 sources, étanchéité, iCal | interface mois/semaine, glisser-déposer, fuseaux, conflits | aucun technique |
| 08 | Maintenance et installations | Partiel | confirmation critique (API), non-conformité installation/matériel, QR | parcours web d'exécution, fiches, périodicité, dérive, catalogue, tournées | aucun technique |
| 09 | Quarts et services | Partiel | droits, circuit, voies directes, lecture par état | création et échange de bout en bout, changement de mode, impressions, concurrence | experts du bord pour les régimes réels |
| 10 | Logistique | Partiel | invariants du stock, refus, immuabilité, droits | interface, seuils d'alerte planifiés, volumes | périmètre prêts/retours différé par décision |
| 11 | Communication | Partiel | accès par propriétaire et par périmètre | écriture de messages, mentions, pièces jointes, rappels, Web Push | HTTPS requis pour le Web Push (AUD-011) |
| 12 | Formations et autres modules | Partiel | inventaire des 9 modules, accès, validation de qualification | tous les circuits de validation | aucun technique |
| 13 | Architecture | Partiel | taille, complexité, imports, couplage | duplication, N+1, cycles d'import, performance réelle | volumétrie réelle |
| 14 | Données et intégrité | Partiel | PostgreSQL : migrate, démo, suite complète 3 829 OK ; cascades et protections | migration d'une base peuplée, sauvegarde/restauration, concurrence en charge | base réelle anonymisée |
| 15 | Sécurité et résilience | Partiel | secrets, production simulée, proxy, isolement des comptes de démo, accès anonyme | mots de passe, verrouillage, XSS/injections, fichiers, en-têtes, Celery | politique SSI pour juger |
| 16 | Qualité des tests | Partiel | volumes, lacunes constatées | pertinence des assertions, couverture mesurée | aucun technique |
| 17 | Déploiement et exploitation | Partiel | installation, PostgreSQL, proxy simulé, absence de procédure | vrai reverse proxy, serveur d'application, sauvegarde, reprise après redémarrage | responsables SIC |
| 18 | Cohérence globale | Partiel (synthèse intermédiaire) | croisement des rapports | à refaire après achèvement des autres | dépend de tous |
| 19 | Conformité Marine nationale | Partiel | vocabulaire, hiérarchie, circuits, comparaison aux 13 pages | sources publiques, validation par un expert du bord | expert métier ; aucune doctrine inventée |
| 20 | Données de démonstration | **Clos avec réserves** | pipeline complet mesuré, couverture, noms réels, mots de passe | fidélité aux usages réels, Windows | expert du bord (fidélité) |

## Blocages réels (non techniques ou hors de portée de l'audit)

1. **Décisions du PO** des blocs A, B, C, D (`06_DECISIONS_PO.md`) pour figer les recommandations.
2. **Responsables SIC** : architecture HTTPS, certificats, politique de sécurité.
3. **Expert du bord** : fidélité de la démonstration, régimes de quart, efficacité des parcours.
4. **Matériel non disponible** : poste Windows, tablette, lecteur d'écran, volume réel de données.
5. **Sources manquantes** (audit 01) : conversations ChatGPT, FANLAB, rapport indépendant cité.

## Ce qui ne bloque pas et reste faisable par l'audit

Parcours navigateur de bout en bout (calendrier, maintenance, tâches, annonces, échanges, formations), revue des assertions des tests, détection de duplication, simulation complète d'un nouveau bâtiment, lecture des tâches Notion une à une, relecture des descriptions de PR : c'est le travail restant pour passer les audits 01, 04, 05, 07, 08, 09, 10, 11, 12, 13, 16 à « clos avec réserves ».
