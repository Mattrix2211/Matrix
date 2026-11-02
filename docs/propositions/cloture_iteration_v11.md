# Clôture de l'itération V1.1 — droits, test de date, réserves

Statut : document de clôture. Les résultats des suites complètes et le tableau final sont dans le rapport remis
au PO et dans Notion. Aucun merge, aucun déploiement.

## 1. Écriture des commandants adjoints : règle appliquée

Décision du PO : lecture et écriture séparées. Un commandant adjoint **consulte** ce qui sert à la coordination du
bâtiment, mais **n'écrit** que sur les services dont `Service.commandant_adjoint` est sa fonction.

### Mécanisme (extension de l'existant, pas de système parallèle)

`matrix/core/ecriture_service.py` complète `niveau_ecriture` :

- `services_rattaches(user)` : services du bâtiment rattachés à la fonction du marin (vide sans fonction).
- `niveau_ecriture_sur(user, objet)` : niveau du rôle, ramené au niveau **équipier** pour un état-major hors des
  services de sa fonction. Les autres rôles ne sont pas concernés.
- `niveau_ecriture_ui(user)` : pour afficher les commandes d'une page de liste ; un état-major sans service rattaché
  n'en a pas.
- `q_ecriture(user, chemin)` et `verifier_cible_ecriture` : bornent les objets sélectionnés en actions groupées et
  les services, secteurs ou sections visés par un formulaire.
- `RolePermission.has_object_permission` (API) utilise `niveau_ecriture_sur` : toute l'API d'écriture est couverte.

### Points d'écriture couverts

| Domaine | Couvert |
|---|---|
| Maintenance | Exécution et correction d'une occurrence, plans, compte rendu correctif, tournées |
| Logistique | Tickets (assignation, transition, demandes de pièces, prélèvement), anomalies (transition, conversion), stock (création, modification, mouvements) |
| Équipements | Matériels et installations (création, modification, suppression, actions groupées, documents), équipement par le catalogue, contrôle visuel |
| API | Tous les ViewSets à `RolePermission`, au niveau de l'objet |

### Ce qui n'est pas borné par service (à arbitrer)

Domaines transverses ou sans service : tâches (attribution dans le périmètre hiérarchique), formations, documents,
RETEX, programme du bâtiment, absences, déplacement d'événements du calendrier, postes. Le plan du navire n'est plus
configurable par un état-major sans service rattaché. À confirmer : ces domaines restent-ils ouverts à tout
état-major, ou faut-il aussi les rattacher à des services ?

### Ce qui est inchangé

Visa final, correction et renvoi de la feuille de service par le COMAEQ de l'équipage de la feuille ; désignation des
rédacteurs ; séparation des équipages A et B (l'équipage à terre garde la lecture) ; droits des chefs de service,
chefs de secteur, commandant et administrateurs.

## 2. Test de date qui échoue sur l'ancien jalon

Test : `dashboard.tests.test_accueil_ux.AccueilUxTests.test_mes_tours_de_service_montre_les_prochaines_dates_et_fonctions`.

### Cause

Le test attend exactement **3** tours de service dans `mes_tours_de_service`. Deux faits se combinent :

1. `quarts.services.prochains_tours_de_service(user, limite=4)` plafonne à **4**. Le plafond et le test ont été
   écrits dans le même commit (`9712bec`) avec deux valeurs différentes.
2. `seed_demo` place les tours de service **relativement au lundi de la semaine courante** (`debut = aujourd'hui -
   weekday`), et le test ne garde que les tours encore à venir (`fin >= maintenant`). Le nombre de tours restants
   change donc **chaque jour de la semaine**.

Le test a ainsi passé un jour précis (en début d'écriture) et échoue les autres. Le 2 novembre 2026, un lundi, le
marin de démonstration a 4 tours à venir : `4 != 3`. L'échec existe à l'identique sur le jalon 284430d : il ne vient
pas de cette itération.

### Correction proposée (non appliquée, en attente de votre accord)

Remplacer l'égalité fragile par ce que la fonction garantit réellement :

```python
tours = self.client.get(reverse("home")).context["mes_tours_de_service"]
self.assertGreaterEqual(len(tours), 1)
self.assertLessEqual(len(tours), 4)  # plafond de prochains_tours_de_service
self.assertEqual(tours, sorted(tours, key=lambda t: t.debut))  # ordre chronologique
```

Variante plus stricte : figer l'instant du test (`unittest.mock.patch` sur `django.utils.timezone.now`) à un jour
connu, afin d'exiger un nombre exact. À privilégier si le nombre de tours affichés est une règle métier.

## 3. Réserves et risques résiduels

| Réserve | Nature |
|---|---|
| Touche Entrée à la connexion | Non reproduite dans Chromium ; sujet gardé ouvert, test à refaire par le PO |
| Silhouettes des bâtiments | En attente des fichiers du Guide du marin 2023 et des droits de reproduction |
| Données de démonstration | Hypothèses documentées, génération non lancée |
| Quarts et tours | Propositions A et B retenues ; prototypes desktop et mobile à préparer avant implémentation |
| Domaines d'écriture transverses | Voir §1, à arbitrer |
| Résidus de CSS des Rondes | Quelques classes `.mx-ronde-*` probablement orphelines |
| Navigateurs | Tests navigateur faits sous Chromium uniquement |
