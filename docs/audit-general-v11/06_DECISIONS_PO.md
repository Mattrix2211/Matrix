# Décisions attendues du Product Owner — version 0

Chaque point est un arbitrage que l'audit ne peut pas trancher. Rien n'est choisi à la place du PO.

| ID | Sujet | Chronologie des sources | Options | Impact si non tranché |
|---|---|---|---|---|
| DP-01 | **TRANCHÉ le 2026-11-05 par le PO** : `main` n'est pas touchée ; aucune fusion, aucun déploiement, aucune modification applicative sans autorisation explicite ; l'audit reste sur une branche dédiée, avec `1c37f22` comme référence. | PO | — | Appliqué |
| DP-02 | **Synthèse de passation** en V1 | Page 13, bandeau du 10/10 : retirée par la PR #7 et différée ; page 13, complément de recette d'octobre : « maintenue en V1, configurable, activée par défaut » ; Feuille de route : différée | Maintenue / différée | Périmètre de V1 incertain (AUD-006) |
| DP-03 | **EN ANALYSE** : le PO veut comprendre avant de décider. Analyse, exemple à bord et options A à D : `audits/AUDIT_DP03_SECTIONS.md`. Aucune modification du modèle de données. | Brief 05/11 ; code ; Notion p.01 et p.13 | Options A à D | Décision attendue du PO |
| DP-04 | **Cahier des charges** à aligner (Rondes retirées, « COMA » banni, baseline) | Décisions des 02/11 | Mettre à jour la page, ou conserver comme historique daté | Lecture erronée du besoin (AUD-004) |
| DP-05 | **Données de Rondes** : suppression physique ou conservation | Décision du 02/11 : « préserver tant qu'une suppression physique n'a pas été autorisée » | Conserver ; exporter puis supprimer | Résidus (AUD-007) |
| DP-06 | **QR codes** : « hors V1 » alors que du code de scan existe dans `assets/` | Page 13 et Cahier | Retirer, désactiver ou qualifier | À préciser par l'audit 08 |
| DP-07 | **Intégration continue** compatible avec un environnement sans Internet | — | Serveur interne ; script local obligatoire | AUD-002 |
| DP-08 | **Tests navigateur versionnés** | — | Les ajouter au dépôt ; les garder hors dépôt | AUD-003 |

Questions déjà ouvertes ailleurs (non dupliquées ici, à reprendre dans les audits 06 et 19) : portée du COMAEQ (« tout le bâtiment » ou « ses services » : `docs/propositions/droits_comaeq.md`), délégations aux commandants adjoints, matrice des modules sans service, points UX ANO-007 à ANO-010 du dossier de recette.

## Décisions ajoutées à la 2ᵉ passe

| ID | Sujet | Constat | Options | Impact si non tranché |
|---|---|---|---|---|
| DP-09 | **Droits par niveau dans le circuit quarts/feuille** (AUD-014, AUD-015) | Visas secteur et service donnés par COMA, commandant et administrateur d'unité, éventuellement par une seule personne ; publication des listes par COMANAV et COMOPS ; modification directe des listes publiées par commandant et administrateurs | Garder la supervision du commandant, exclure l'administrateur d'unité, exiger des personnes différentes, réserver la publication au COMAEQ | Contradiction entre l'intention des tests et le comportement ; dépend aussi des tâches D-05 |
| DP-10 | **Architecture HTTPS du bord** (AUD-011) | Le proxy TLS ne fonctionne pas tel que livré ; aucun serveur d'application déclaré | Proxy TLS, TLS porté par l'application, TLS bout en bout (voir `AUDIT_15.md` §4) ; autorité de certification interne à définir avec l'autorité compétente | Premier bâtiment bloqué ou contourné |
| DP-11 | **Import en masse du personnel** (AUD-012) | Pas d'import de comptes ; import de matériel existant | Besoin à qualifier : volume, format source (tableur, annuaire), fréquence | Mise en service lourde |
| DP-12 | **404 du brouillon de signalement** | Non reproduit sur 1c37f22 | Le PO décrit les étapes exactes de l'époque, ou le point est clos comme « non reproductible » | Point laissé ouvert |
| DP-13 | **Qui administre la structure du bord ?** (AUD-019, AUD-020, AUD-021) | Services, secteurs, sections : réservés au compte technique de la flotte ; pas de renommage ; suppression physique | Seuil configurable dédié limité à l'unité ; ou maintenir le compte technique en documentant la procédure ; archivage plutôt que suppression | Un bord ne peut pas se réorganiser seul |
| DP-14 | **Règles de droits écrites en dur** (AUD-022) | 55 comparaisons de niveau en dur | Revue cas par cas : plancher de sécurité ou règle métier | Principe « configuration plutôt que code » non tenu partout |
