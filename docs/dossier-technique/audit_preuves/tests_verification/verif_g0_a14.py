"""VÉRIFICATION TEMPORAIRE G0 / A14 — copie isolée de l'état B ; données fictives ; non conservée dans le dépôt."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from dashboard.passation import syntheses_visibles
from dashboard.tests.test_passation import PassationBase, bloc
from logistics.models import Anomalie
from org.models import Section, SynthesePassation
from taches.models import Tache

User = get_user_model()


def marin_section(nom, role, navire, equipage, service, secteur, section):
    u = User.objects.create_user(username=nom, password="pass")
    UserProfile.objects.update_or_create(user=u, defaults={"role": role, "ship": navire, "service": service, "sector": secteur, "section": section, "equipage": equipage})
    return User.objects.get(pk=u.pk)


class A14(PassationBase):
    def setUp(self):
        super().setUp()
        self.s1 = Section.objects.create(sector=self.secteur, name="Section 1")
        self.s2 = Section.objects.create(sector=self.secteur, name="Section 2")
        self.chef_s1 = marin_section("chef_s1", "CHEF_SECTION", self.navire, "B", self.service, self.secteur, self.s1)
        self.chef_s2 = marin_section("chef_s2", "CHEF_SECTION", self.navire, "B", self.service, self.secteur, self.s2)
        self.chef_s1_sortant = marin_section("chef_s1_A", "CHEF_SECTION", self.navire, "A", self.service, self.secteur, self.s1)
        self.m_s2 = marin_section("marin_s2", "EQUIPIER", self.navire, "A", self.service, self.secteur, self.s2)
        self.m_s1 = marin_section("marin_s1", "EQUIPIER", self.navire, "A", self.service, self.secteur, self.s1)
        Tache.objects.create(titre="TACHE-SECTION-1", assigne=self.m_s1, created_by=self.chef_s1_sortant, statut="A_FAIRE")
        Tache.objects.create(titre="TACHE-SECTION-2", assigne=self.m_s2, created_by=self.chef_s2, statut="BLOQUEE", motif_blocage="Motif-S2")
        Anomalie.objects.create(titre="ANOMALIE-SECTION-2", description="x", created_by=self.m_s2, ship=self.navire, section=self.s2)
        self.relever()
        self.syn = SynthesePassation.objects.get()

    def lire(self, user):
        self.client.force_login(user)
        return self.client.get(reverse("passation", args=[self.syn.pk]))

    def test_contenu_fige_couvre_toutes_les_sections(self):
        titres = [l["titre"] for g in bloc(self.syn, "taches")["groupes"] for l in g["lignes"]]
        self.assertIn("TACHE-SECTION-1", titres)
        self.assertIn("TACHE-SECTION-2", titres)

    def test_chef_de_section_equipage_montant_lit_la_section_voisine(self):
        r = self.lire(self.chef_s1)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "TACHE-SECTION-2")
        self.assertContains(r, "Motif-S2")
        self.assertContains(r, "ANOMALIE-SECTION-2")

    def test_chef_de_section_equipage_sortant_lit_aussi(self):
        self.assertEqual(self.lire(self.chef_s1_sortant).status_code, 200)

    def test_equipier_refuse(self):
        self.assertEqual(self.lire(self.m_s1).status_code, 404)

    def test_autre_navire_refuse(self):
        from org.models import Ship
        autre = Ship.objects.create(name="Autre", code="AUT", double_equipage=True, equipage_a_bord="A")
        etr = marin_section("chef_etr", "CHEF_SECTION", autre, "B", None, None, None)
        self.assertEqual(self.lire(etr).status_code, 404)

    def test_chef_sans_equipage_refuse(self):
        sans = marin_section("chef_sans_equ", "CHEF_SECTION", self.navire, "", self.service, self.secteur, self.s1)
        self.assertEqual(self.lire(sans).status_code, 404)

    def test_pdf_meme_perimetre(self):
        r = self.client.get(reverse("passation-pdf", args=[self.syn.pk]))  # non connecté
        self.assertIn(r.status_code, (302, 403, 404))

    def test_chef_de_section_pas_dans_les_syntheses_visibles_hors_ses_equipages(self):
        troisieme = marin_section("chef_c", "CHEF_SECTION", self.navire, "C", self.service, self.secteur, self.s1)
        self.assertEqual(list(syntheses_visibles(troisieme)), [])
