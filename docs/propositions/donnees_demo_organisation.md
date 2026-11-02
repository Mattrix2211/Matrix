# Données de démonstration — organisation par type de bâtiment

Statut : **proposition de vérification avant génération**. Principe validé par le PO : démonstration
reconstruite autour de Bretagne (deux équipages), avec des scénarios complémentaires sur Jacques Chevallier
et Auguste Bénébig. L'organigramme d'une FREMM n'est **pas** transposé aux deux autres unités.

Limite : le Guide du marin 2023 n'est pas disponible dans mon environnement. Les structures ci-dessous
s'appuient sur Notion (« Organigramme et rôles » et référentiel des bâtiments) et sur l'existant de Matrix ;
elles ne sont pas recoupées avec le guide. Tout ce qui est une hypothèse de ma part est marqué **(H)**.

## 1. Règles communes retenues

- Hiérarchie configurable par bâtiment : commandant, second, commandants adjoints (COMAEQ, COMOPS,
  COMANAV, COMAVIA selon le bâtiment), services, secteurs, sections, équipiers.
- Chaque service est rattaché au commandant adjoint réellement compétent (`Service.commandant_adjoint`).
- Aucun nom de rôle dans le nom d'un marin fictif. Grades et fonctions cohérents entre eux.
- **COMAVIA uniquement si l'unité a une capacité aviation.** Aucune des trois unités n'en a dans la démo :
  pas de COMAVIA.
- Double équipage seulement là où le référentiel le prévoit.

## 2. Bretagne — FREMM D 655, double équipage A et B

| Élément | Contenu |
|---|---|
| Commandement | Un commandant et un commandant en second par équipage |
| COMOPS | Un titulaire par équipage |
| COMANAV | Un titulaire par équipage |
| COMAEQ | Un titulaire pour A ; **poste vacant pour B** (cas de visa exceptionnel) |
| Services | Opérations (COMOPS) ; Navigation et Propulsion (COMANAV) ; Énergie et Électricité (COMANAV) ; Sécurité (COMAEQ) **(H)** |
| Secteurs | Deux au plus par service : par exemple Moteurs et Auxiliaires pour Propulsion |
| Sections | Une à deux par secteur |
| Effectif fictif | Environ 25 marins répartis sur les deux équipages |

**(H) à confirmer** : le service Sécurité rattaché au COMAEQ. Notion précise que le COMANAV est
« adjoint sécurité » et le COMAEQ « adjoint protection ». Selon ce que couvre le service Sécurité
(lutte contre l'incendie, avaries, protection), il relève du COMANAV ou du COMAEQ.

## 3. Jacques Chevallier — BRF A 725, équipage unique

Un bâtiment ravitailleur a une organisation différente d'une frégate : pas de service Opérations de
combat, activité centrée sur la propulsion, le ravitaillement à la mer et le soutien.

| Élément | Contenu **(H)** |
|---|---|
| Commandement | Un commandant, un commandant en second |
| Commandants adjoints | COMOPS, COMANAV, COMAEQ |
| Services | Pont et manœuvre (COMANAV) ; Propulsion et Énergie (COMANAV) ; Ravitaillement (COMOPS) ; Vie à bord et soutien (COMAEQ) |
| Particularité | Secteur « Ravitaillement à la mer » dans son propre service |
| Effectif fictif | Environ 8 marins |

Usage dans la démo : isoler un autre bâtiment (un marin de la Bretagne ne doit voir aucun objet du BRF),
et montrer la silhouette BRF.

## 4. Auguste Bénébig — POM P 779, équipage unique

Un patrouilleur outre-mer a un effectif réduit et peu de niveaux hiérarchiques.

| Élément | Contenu **(H)** |
|---|---|
| Commandement | Un commandant, un commandant en second |
| Commandants adjoints | Aucun COMA dédié : le commandement porte directement les services |
| Services | Pont et opérations ; Machine ; Vie à bord |
| Secteurs et sections | Une section par secteur au plus |
| Effectif fictif | Environ 6 marins |

**(H) à confirmer** : l'absence de commandant adjoint sur un POM. Si l'unité en compte, je les ajoute.
Le modèle de Matrix le permet : la configuration ne suppose pas qu'un bâtiment ait les quatre fonctions.

## 5. Ce que la démonstration doit montrer

Identique à la proposition précédente (audit de reprise, §3) : profils de recette, scénarios de bout en bout,
cas de refus d'accès, poste vacant, marin désactivé, désignation inopérante. S'y ajoute :

- Un marin de chaque bâtiment qui tente d'ouvrir un objet d'un autre bâtiment : page 404 cohérente.
- Aucun lien du jeu de données vers un objet inexistant, contrôlé par un test qui parcourt la base.

## 6. Décisions attendues

1. Confirmer ou corriger les structures **(H)** des paragraphes 2, 3 et 4.
2. Service Sécurité de la Bretagne : COMANAV ou COMAEQ.
3. Fournir le Guide du marin 2023 pour recouper ces structures avant la génération.

Je ne génère pas les données tant que ces trois points ne sont pas tranchés.
