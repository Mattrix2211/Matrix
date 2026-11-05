# Synthèse exécutive — état provisoire (phase 1 en cours)

**Ceci n'est pas le diagnostic final.** Sur les 20 audits prévus, aucun n'est terminé. Cette page dit ce qui est établi, et ce qui ne l'est pas.

## Ce qui est établi à ce jour

1. **La ligne auditée est la V1.1, pas `main`.** Le commit de référence du PO (`1c37f22`) a 117 commits d'avance sur `main` (`6ef16ad`), qui reste à la V1 FANLAB. Il n'est pas fusionné. Déployer `main` aujourd'hui reviendrait à livrer une version sans plusieurs correctifs.
2. **Une anomalie de sécurité connue existe sur `main`** : n'importe quel marin du bâtiment peut créer une feuille de service (AUD-001). Elle est corrigée sur la V1.1 (lecture de code ; reproduction à faire).
3. **Pas de filet automatique de non-régression** : aucune intégration continue (AUD-002) ; les parcours navigateur cités dans la recette ne sont pas dans le dépôt (AUD-003).
4. **Décisions explicites retrouvées** : génération automatique des tours abandonnée (09/10), Rondes retirées (02/11), QR codes hors V1, PÉPIN/CRAT et organismes à terre différés.
5. **Les sources de vérité divergent** (AUD-004 à AUD-006) : le cahier n'est plus à jour sur plusieurs points, et une contradiction demande un arbitrage (passation).
6. **Le projet est volumineux et très testé** : 22 paquets, environ 47 600 lignes de code applicatif hors tests et hors migrations, 3 829 tests découverts par Django. Le nombre de tests n'est pas une preuve de conformité métier.
7. Vérifications techniques de base : `check` sans erreur ; modèles et migrations concordent (voir `audits/AUDIT_01.md` §6).

## Constats ajoutés à la reprise (preuves dynamiques)

8. **AUD-001 rejoué** : sur 1c37f22, un matelot sans fonction de rédacteur ne peut plus créer de feuille de service (403) ; seuls les rédacteurs désignés le peuvent.
9. **Aucune erreur serveur** sur environ 330 pages ouvertes par 10 profils de la démonstration ; **un lien mort** sur l'accueil d'un chef de secteur (AUD-008).
10. **Sans Internet : conforme** pour le code statique (aucune ressource externe active).
11. **Deux risques de mise en service** : commandes de démonstration sans garde-fou (AUD-009) et mode production qui impose HTTPS sans procédure pour un bord (AUD-011).

## Ce qui n'est pas encore établi

Presque tout le reste : fonctionnement réel des parcours, droits effectifs, configurabilité par bâtiment, mise en service, UX, données, sécurité, PostgreSQL. Les questions 1 à 10 du critère de réussite **ne peuvent pas encore être répondues**.

## Décisions demandées maintenant

Voir `06_DECISIONS_PO.md` : DP-01 (sort de `main`) est la plus urgente. DP-03 (sections facultatives) conditionne l'audit de configurabilité.

## Prochaines étapes

Voir `AVANCEMENT.md`.
