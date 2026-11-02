# Données de démonstration — organisation par type de bâtiment

> **Décisions du PO (2 novembre 2026)** : Bretagne bâtiment principal à deux équipages ; Jacques Chevallier et
> Auguste Bénébig unités complémentaires. À bord de la Bretagne, la sécurité technique, l'incendie et les avaries
> sont rattachés **provisoirement au COMANAV** ; la protection et la vie à bord relèvent du **COMAEQ**. **Aucun
> service « Sécurité » générique** ne mélange ces responsabilités. Les organigrammes du BRF et du POM sont des
> **hypothèses de démonstration, non des organigrammes officiels**, et seront présentés comme tels.
> Les données ne sont **pas générées** tant que ces hypothèses ne sont pas relues.

Statut : **hypothèses documentées avant génération**. Principe validé par le PO : démonstration
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
| Services | Opérations (COMOPS) ; Navigation et Propulsion (COMANAV) ; Énergie et Électricité (COMANAV) ; **Sécurité technique, incendie et avaries (COMANAV, rattachement provisoire)** ; **Protection et vie à bord (COMAEQ)** **(H)** |
| Secteurs | Deux au plus par service : par exemple Moteurs et Auxiliaires pour Propulsion |
| Sections | Une à deux par secteur |
| Effectif fictif | Environ 25 marins répartis sur les deux équipages |

**Tranché par le PO** : pas de service « Sécurité » générique. La sécurité technique, l'incendie et les avaries relèvent
provisoirement du COMANAV ; la protection et la vie à bord du COMAEQ (Notion : le COMANAV est « adjoint sécurité »,
le COMAEQ « adjoint protection »).

## 3. Jacques Chevallier — BRF A 725, équipage unique (hypothèse de démonstration, non officielle)

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

## 4. Auguste Bénébig — POM P 779, équipage unique (hypothèse de démonstration, non officielle)

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

## 6. État des décisions

1. Structure de la Bretagne : **tranchée** (voir l'encadré en tête de document).
2. Organigrammes du BRF et du POM : hypothèses de démonstration, présentées comme telles dans les données et la
   documentation. Le POM garde l'hypothèse « sans commandant adjoint dédié » tant qu'elle n'est pas contredite.
3. Guide du marin 2023 : toujours non disponible dans l'environnement, donc rien n'est recoupé avec lui.

## 7. Scripts et scénarios préparés, non exécutés

La génération reprendra `seed_demo` : même mécanique (idempotente, base isolée), avec ces changements à appliquer
après relecture :

- Remplacer le service « Sécurité » par deux services distincts rattachés respectivement au COMANAV et au COMAEQ.
- Remplacer les noms de famille qui reprennent un rôle (« Coma Comops ») par des noms vraisemblables.
- Créer les deux équipages de la Bretagne, avec poste de COMAEQ vacant côté B.
- Ajouter Jacques Chevallier et Auguste Bénébig avec les hypothèses des §3 et §4.
- Ajouter un test qui ouvre chaque lien généré par la démonstration pour garantir qu'aucun ne pointe vers un objet
  inexistant.

Je ne lance pas la génération sans votre GO.
