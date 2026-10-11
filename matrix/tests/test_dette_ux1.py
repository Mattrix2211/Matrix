"""Dette UX-1 : la barre latérale n'est pas calculée pour un fragment HTMX ; le mode lecture seule reste connu des fragments."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from org.models import Ship


class FragmentsHtmxTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Bâtiment double", code="BD", double_equipage=True, equipage_a_bord="A")
        self.terre = User.objects.create_user(username="marin_terre", password="pass")
        self.terre.profile.ship, self.terre.profile.equipage = self.navire, "B"
        self.terre.profile.save()
        self.client.force_login(self.terre)

    def test_page_complete_et_fragment(self):
        complete = self.client.get(reverse("notifications-centre"))
        self.assertIn("navigation_laterale", complete.context)
        fragment = self.client.get(reverse("notifications-panneau"), HTTP_HX_REQUEST="true")
        self.assertNotIn("navigation_laterale", fragment.context)
        self.assertEqual(fragment.context["equipage_a_terre"], "B")
        self.assertNotIn("batiment_courant", fragment.context)


class EntreesTransversesTests(TestCase):
    def test_master_admin_sans_specialite_ni_classe_ne_voit_pas_les_entrees(self):
        from dashboard.templatetags.dashboard_extras import peut_voir_dashboard_classe_navire, peut_voir_dashboard_specialite

        admin = User.objects.create_superuser("root", password="pass")
        self.assertFalse(peut_voir_dashboard_specialite(admin))
        self.assertFalse(peut_voir_dashboard_classe_navire(admin))
        Ship.objects.create(name="Classé", code="CL", classe_navire="FREMM")
        self.assertTrue(peut_voir_dashboard_classe_navire(admin))
