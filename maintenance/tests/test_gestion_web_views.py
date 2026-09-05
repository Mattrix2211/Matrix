"""Tests de la page web de gestion de la maintenance (plans + occurrences),
distincte de la vue calendrier — cf. tâche [FEAT] Vraie page de gestion
« Maintenance » (plans + occurrences).

Vérifie : la lecture ouverte à tout marin scopé, le seuil de rôle pour
l'écriture sur les plans (CHEF_SECTION, même seuil que MaintenancePlanViewSet
côté API), le filtrage des occurrences par statut et par retard, l'isolation
par périmètre (navire/service/secteur) et l'absence de création manuelle
d'occurrence (générées uniquement par la tâche Celery generate_occurrences).
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Asset, AssetType
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship


class GestionMaintenanceWebViewsTests(TestCase):
    def setUp(self):
        # Navire A (périmètre de l'utilisateur testé)
        self.navire_a = Ship.objects.create(name="Navire A", code="NA")
        self.service_a = Service.objects.create(ship=self.navire_a, name="Service A")
        self.secteur_a = Sector.objects.create(service=self.service_a, name="Secteur A")
        self.type_a = AssetType.objects.create(name="Extincteur", category="Incendie", sector=self.secteur_a)
        self.actif_a = Asset.objects.create(
            asset_type=self.type_a, ship=self.navire_a, service=self.service_a, sector=self.secteur_a,
        )

        # Navire B (hors périmètre), pour les tests d'isolation
        self.navire_b = Ship.objects.create(name="Navire B", code="NB")
        self.service_b = Service.objects.create(ship=self.navire_b, name="Service B")
        self.secteur_b = Sector.objects.create(service=self.service_b, name="Secteur B")
        self.type_b = AssetType.objects.create(name="EPI", category="Sécurité", sector=self.secteur_b)
        self.actif_b = Asset.objects.create(
            asset_type=self.type_b, ship=self.navire_b, service=self.service_b, sector=self.secteur_b,
        )

        self.plan_a = MaintenancePlan.objects.create(
            scope="ASSET", asset=self.actif_a, name="Contrôle mensuel A", every_n_days=30, expected_duration_min=45,
        )
        self.plan_b = MaintenancePlan.objects.create(
            scope="ASSET", asset=self.actif_b, name="Contrôle mensuel B", every_n_days=30,
        )

        aujourdhui = timezone.localdate()
        self.occ_a_planifiee = MaintenanceOccurrence.objects.create(
            plan=self.plan_a, asset=self.actif_a, scheduled_for=aujourdhui, status="PLANNED",
        )
        self.occ_a_en_retard = MaintenanceOccurrence.objects.create(
            plan=self.plan_a, asset=self.actif_a,
            scheduled_for=aujourdhui - timezone.timedelta(days=5), status="PLANNED",
        )
        self.occ_a_terminee = MaintenanceOccurrence.objects.create(
            plan=self.plan_a, asset=self.actif_a,
            scheduled_for=aujourdhui - timezone.timedelta(days=10), status="DONE",
        )
        self.occ_b = MaintenanceOccurrence.objects.create(
            plan=self.plan_b, asset=self.actif_b, scheduled_for=aujourdhui, status="PLANNED",
        )

        self.equipier = User.objects.create_user(username="equipier_a", password="pass")
        UserProfile.objects.filter(user=self.equipier).update(role="EQUIPIER", sector=self.secteur_a)

        self.chef = User.objects.create_user(username="chef_a", password="pass")
        UserProfile.objects.filter(user=self.chef).update(role="CHEF_SECTION", sector=self.secteur_a)

        self.url_plans = reverse("maintenance-plans")
        self.url_occurrences = reverse("maintenance-occurrences")

    # --- Lecture ouverte à tout marin scopé -------------------------------

    def test_equipier_peut_lire_la_liste_des_plans(self):
        self.client.login(username="equipier_a", password="pass")
        response = self.client.get(self.url_plans)
        self.assertEqual(response.status_code, 200)
        plans = list(response.context["plans"])
        self.assertIn(self.plan_a, plans)

    def test_equipier_peut_lire_le_tableau_des_occurrences(self):
        self.client.login(username="equipier_a", password="pass")
        response = self.client.get(self.url_occurrences)
        self.assertEqual(response.status_code, 200)
        occurrences = list(response.context["occurrences"])
        self.assertIn(self.occ_a_planifiee, occurrences)

    def test_commentaire_dev_formulaire_plan_non_affiche_en_clair(self):
        """Régression : le commentaire {# ... #} multi-lignes d'en-tête des
        champs communs de plan (maintenance/_plan_form_fields.html, inclus
        dans les modales de création/modification) s'affichait en clair,
        faute d'être invisible avec {% comment %}...{% endcomment %}."""
        self.client.login(username="equipier_a", password="pass")
        response = self.client.get(self.url_plans)
        self.assertNotContains(response, "Champs communs aux modales de création/modification")

    def test_utilisateur_non_authentifie_redirige_vers_login(self):
        response = self.client.get(self.url_plans)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(self.url_occurrences)
        self.assertEqual(response.status_code, 302)

    # --- Seuil de rôle sur les plans (CHEF_SECTION+) -----------------------

    def test_equipier_ne_peut_pas_creer_un_plan(self):
        self.client.login(username="equipier_a", password="pass")
        response = self.client.post(self.url_plans, {
            "action": "create_plan", "name": "Nouveau plan", "scope": "ASSET",
            "asset_id": self.actif_a.id, "every_n_days": "30", "expected_duration_min": "20",
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(MaintenancePlan.objects.filter(name="Nouveau plan").exists())

    def test_equipier_ne_peut_pas_modifier_un_plan(self):
        self.client.login(username="equipier_a", password="pass")
        response = self.client.post(self.url_plans, {
            "action": "edit_plan", "pk": self.plan_a.pk, "name": "Modifié", "scope": "ASSET",
            "asset_id": self.actif_a.id, "every_n_days": "30", "expected_duration_min": "20",
        })
        self.assertEqual(response.status_code, 403)
        self.plan_a.refresh_from_db()
        self.assertEqual(self.plan_a.name, "Contrôle mensuel A")

    def test_chef_section_peut_creer_un_plan(self):
        self.client.login(username="chef_a", password="pass")
        response = self.client.post(self.url_plans, {
            "action": "create_plan", "name": "Nouveau plan", "scope": "ASSET",
            "asset_id": self.actif_a.id, "every_n_days": "60", "expected_duration_min": "20",
            "requires_validation": "on",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        plan = MaintenancePlan.objects.get(name="Nouveau plan")
        self.assertEqual(plan.every_n_days, 60)
        self.assertEqual(plan.asset, self.actif_a)
        self.assertTrue(plan.requires_validation)

    def test_chef_section_peut_modifier_un_plan(self):
        self.client.login(username="chef_a", password="pass")
        response = self.client.post(self.url_plans, {
            "action": "edit_plan", "pk": self.plan_a.pk, "name": "Contrôle trimestriel A", "scope": "ASSET",
            "asset_id": self.actif_a.id, "every_n_days": "90", "expected_duration_min": "45",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.plan_a.refresh_from_db()
        self.assertEqual(self.plan_a.name, "Contrôle trimestriel A")
        self.assertEqual(self.plan_a.every_n_days, 90)

    def test_chef_section_ne_peut_pas_creer_un_plan_sur_un_actif_hors_perimetre(self):
        # Le chef de section A ne doit pas pouvoir créer un plan rattaché à un
        # actif du navire B en postant directement son identifiant, même s'il
        # n'apparaît pas dans son menu déroulant.
        self.client.login(username="chef_a", password="pass")
        response = self.client.post(self.url_plans, {
            "action": "create_plan", "name": "Plan hors périmètre", "scope": "ASSET",
            "asset_id": self.actif_b.id, "every_n_days": "30", "expected_duration_min": "20",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(MaintenancePlan.objects.filter(name="Plan hors périmètre").exists())

    # --- Isolation par périmètre --------------------------------------------

    def test_liste_des_plans_isolee_par_perimetre(self):
        self.client.login(username="equipier_a", password="pass")
        response = self.client.get(self.url_plans)
        plans = list(response.context["plans"])
        self.assertIn(self.plan_a, plans)
        self.assertNotIn(self.plan_b, plans)

    def test_tableau_des_occurrences_isole_par_perimetre(self):
        self.client.login(username="equipier_a", password="pass")
        response = self.client.get(self.url_occurrences)
        occurrences = list(response.context["occurrences"])
        ids = {o.id for o in occurrences}
        self.assertIn(self.occ_a_planifiee.id, ids)
        self.assertNotIn(self.occ_b.id, ids)

    # --- Filtrage des occurrences par statut et par retard ------------------

    def test_filtre_par_statut(self):
        self.client.login(username="equipier_a", password="pass")
        response = self.client.get(self.url_occurrences, {"statut": "DONE"})
        occurrences = list(response.context["occurrences"])
        self.assertEqual(occurrences, [self.occ_a_terminee])

    def test_filtre_par_retard(self):
        self.client.login(username="equipier_a", password="pass")
        response = self.client.get(self.url_occurrences, {"retard": "1"})
        occurrences = list(response.context["occurrences"])
        # Seule l'occurrence planifiée avec une échéance dépassée est en retard :
        # celle du jour même n'est pas en retard, celle déjà terminée non plus.
        self.assertEqual(occurrences, [self.occ_a_en_retard])
        self.assertTrue(occurrences[0].en_retard)

    # --- Auto-assignation (EQUIPIER+) ---------------------------------------

    def test_equipier_peut_sassigner_une_occurrence(self):
        self.client.login(username="equipier_a", password="pass")
        url = reverse("occurrence-self-assign", args=[self.occ_a_planifiee.pk])
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.occ_a_planifiee.refresh_from_db()
        self.assertIn(self.equipier, self.occ_a_planifiee.assignees.all())
        self.assertEqual(self.occ_a_planifiee.status, "ASSIGNED")

    def test_equipier_ne_peut_pas_sassigner_une_occurrence_hors_perimetre(self):
        self.client.login(username="equipier_a", password="pass")
        url = reverse("occurrence-self-assign", args=[self.occ_b.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        self.occ_b.refresh_from_db()
        self.assertNotIn(self.equipier, self.occ_b.assignees.all())

    # --- Absence de création manuelle d'occurrence ---------------------------

    def test_aucun_bouton_de_creation_manuelle_doccurrence(self):
        # Réservé au chef de section (seuil de droit d'écriture le plus haut
        # testé ici) : même un chef ne doit voir aucun moyen de créer une
        # occurrence à la main, seule generate_occurrences (Celery) le fait.
        self.client.login(username="chef_a", password="pass")
        response = self.client.get(self.url_occurrences)
        contenu = response.content.decode()
        self.assertNotIn("Nouvelle occurrence", contenu)
        self.assertNotIn("Créer une occurrence", contenu)
        self.assertNotIn("Ajouter une occurrence", contenu)
