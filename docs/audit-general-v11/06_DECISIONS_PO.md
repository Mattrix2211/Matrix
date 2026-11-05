# Décisions attendues du Product Owner — version 0

Chaque point est un arbitrage que l'audit ne peut pas trancher. Rien n'est choisi à la place du PO.

| ID | Sujet | Chronologie des sources | Options | Impact si non tranché |
|---|---|---|---|---|
| DP-01 | **Cible de fusion** : `main` est à `6ef16ad`, la V1.1 à `1c37f22` (117 commits d'avance, dont le correctif AUD-001) | Brief : « ne pas fusionner vers main » ; Notion : « pas de merge sans GO » | Fusionner après recette ; ou maintenir deux lignes | `main` reste la ligne fautive (AUD-001) |
| DP-02 | **Synthèse de passation** en V1 | Page 13, bandeau du 10/10 : retirée par la PR #7 et différée ; page 13, complément de recette d'octobre : « maintenue en V1, configurable, activée par défaut » ; Feuille de route : différée | Maintenue / différée | Périmètre de V1 incertain (AUD-006) |
| DP-03 | **Sections facultatives** selon le bâtiment : le brief du PO les dit facultatives ; la source écrite n'a pas été retrouvée | Brief 05/11 | Confirmer par une page Notion ou une décision écrite | Impossible de dire si le modèle `org` est conforme (EX-030) |
| DP-04 | **Cahier des charges** à aligner (Rondes retirées, « COMA » banni, baseline) | Décisions des 02/11 | Mettre à jour la page, ou conserver comme historique daté | Lecture erronée du besoin (AUD-004) |
| DP-05 | **Données de Rondes** : suppression physique ou conservation | Décision du 02/11 : « préserver tant qu'une suppression physique n'a pas été autorisée » | Conserver ; exporter puis supprimer | Résidus (AUD-007) |
| DP-06 | **QR codes** : « hors V1 » alors que du code de scan existe dans `assets/` | Page 13 et Cahier | Retirer, désactiver ou qualifier | À préciser par l'audit 08 |
| DP-07 | **Intégration continue** compatible avec un environnement sans Internet | — | Serveur interne ; script local obligatoire | AUD-002 |
| DP-08 | **Tests navigateur versionnés** | — | Les ajouter au dépôt ; les garder hors dépôt | AUD-003 |

Questions déjà ouvertes ailleurs (non dupliquées ici, à reprendre dans les audits 06 et 19) : portée du COMAEQ (« tout le bâtiment » ou « ses services » : `docs/propositions/droits_comaeq.md`), délégations aux commandants adjoints, matrice des modules sans service, points UX ANO-007 à ANO-010 du dossier de recette.
