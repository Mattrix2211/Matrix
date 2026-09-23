"""Accès à l'arbre de compétences (CompetencyTreeView) depuis la portabilité
des formations (tâche Notion « Formation unique et portable entre navires ») :
le catalogue de formations étant désormais global, l'arbre est le MÊME pour
tout marin connecté, quel que soit son navire, service, secteur ou section —
il n'y a plus de notion de secteur "visible" ou non par un référent, ni de
sélecteur de secteur dans l'URL."""
from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Section, Sector, Service, Ship
from training.models import TrainingCourse


class ArbreGlobalAccessibleATousTests(TestCase):
    """Cas le plus courant pour un équipier : profil rattaché à une section,
    pas directement à un secteur/navire — l'accès à l'arbre ne dépend plus du
    tout du rattachement organisationnel du marin."""

    def setUp(self):
        ship = Ship.objects.create(name="Navire Section", code="SEC")
        service = Service.objects.create(ship=ship, name="Sécurité")
        sector = Sector.objects.create(service=service, name="Incendie")
        section = Section.objects.create(sector=sector, name="Équipe A")
        TrainingCourse.objects.create(title="Extinction niveau 1")

        self.equipier = User.objects.create_user(username="equipier_section", password="pass")
        UserProfile.objects.update_or_create(
            user=self.equipier, defaults={"role": "EQUIPIER", "section": section},
        )

    def test_equipier_accede_a_larbre(self):
        self.client.login(username="equipier_section", password="pass")
        r = self.client.get("/formations/arbre-competences/")
        self.assertEqual(r.status_code, 200)

    def test_arbre_affiche_bien_les_formations_du_catalogue(self):
        self.client.login(username="equipier_section", password="pass")
        r = self.client.get("/formations/arbre-competences/")
        self.assertContains(r, "Extinction niveau 1")


class ArbreIdentiqueQuelQueSoitLeNavireTests(TestCase):
    """Deux marins de navires différents doivent voir exactement le même
    arbre (catalogue global) — plus de notion de secteur "hors périmètre"."""

    def setUp(self):
        ship_a = Ship.objects.create(name="Navire Arbre A", code="ARB-A")
        ship_b = Ship.objects.create(name="Navire Arbre B", code="ARB-B")
        TrainingCourse.objects.create(title="Formation partagée")

        self.marin_a = User.objects.create_user(username="marin_arbre_a", password="pass")
        UserProfile.objects.update_or_create(user=self.marin_a, defaults={"role": "EQUIPIER", "ship": ship_a})
        self.marin_b = User.objects.create_user(username="marin_arbre_b", password="pass")
        UserProfile.objects.update_or_create(user=self.marin_b, defaults={"role": "EQUIPIER", "ship": ship_b})

    def test_les_deux_marins_voient_la_meme_formation(self):
        self.client.login(username="marin_arbre_a", password="pass")
        r_a = self.client.get("/formations/arbre-competences/")
        self.client.logout()
        self.client.login(username="marin_arbre_b", password="pass")
        r_b = self.client.get("/formations/arbre-competences/")
        self.assertContains(r_a, "Formation partagée")
        self.assertContains(r_b, "Formation partagée")
