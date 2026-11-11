"""Protection contre les suppressions destructrices (AUD-020) : une unité référencée ne se supprime jamais, rien n'est perdu."""
from django.contrib.admin.sites import site as admin_site
from django.contrib.auth.models import User
from django.db.models import ProtectedError
from django.test import RequestFactory, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import AuditLog, UserProfile
from assets.models import Asset, AssetType
from org import structure_services
from org.models import Section, Sector, Service, Ship


def compte(nom, role, **profil):
    utilisateur = User.objects.create_user(username=nom, password="x")
    UserProfile.objects.update_or_create(user=utilisateur, defaults={"role": role, **profil})
    return User.objects.get(pk=utilisateur.pk)


class Base(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire A", code="A")
        self.service = Service.objects.create(ship=self.navire, name="Propulsion")
        self.secteur = Sector.objects.create(service=self.service, name="Moteurs")
        self.section = Section.objects.create(sector=self.secteur, name="Bâbord")
        self.admin = compte("admin_flotte", "MASTER_ADMIN")
        self.admin.is_superuser = True
        self.admin.save()
        self.marin = compte("marin_a", "EQUIPIER", ship=self.navire, service=self.service, sector=self.secteur, section=self.section)


class RegleTests(Base):
    def test_unite_vide_se_supprime_avec_ses_sous_unites_et_trace(self):
        UserProfile.objects.filter(user=self.marin).update(ship=None, service=None, sector=None, section=None)
        structure_services.supprimer(self.service, self.admin)
        self.assertFalse(Service.objects.filter(pk=self.service.pk).exists())
        self.assertFalse(Section.objects.filter(pk=self.section.pk).exists())
        self.assertTrue(AuditLog.objects.filter(action="delete_service", actor=self.admin).exists())

    def test_unite_referencee_par_un_marin_est_refusee_et_rien_n_est_perdu(self):
        with self.assertRaises(structure_services.SuppressionRefusee) as ctx:
            structure_services.supprimer(self.section, self.admin)
        self.assertIn("Archivez-le", str(ctx.exception))
        self.assertTrue(Section.objects.filter(pk=self.section.pk).exists())
        self.assertTrue(AuditLog.objects.filter(action="suppression_unite_refusee").exists())

    def test_le_profil_du_marin_n_est_jamais_elargi(self):
        with self.assertRaises(structure_services.SuppressionRefusee):
            structure_services.supprimer(self.service, self.admin)
        profil = UserProfile.objects.get(user=self.marin)
        self.assertEqual((profil.service_id, profil.sector_id, profil.section_id), (self.service.pk, self.secteur.pk, self.section.pk))

    def test_reference_d_une_sous_unite_bloque_le_parent(self):
        type_materiel = AssetType.objects.create(name="Pompe", sector=self.secteur)
        Asset.objects.create(designation="P1", asset_type=type_materiel, ship=self.navire, service=self.service, sector=self.secteur, section=self.section)
        UserProfile.objects.filter(user=self.marin).update(ship=None, service=None, sector=None, section=None)
        comptes = structure_services.dependances(self.navire)
        self.assertTrue(comptes)
        with self.assertRaises(structure_services.SuppressionRefusee):
            structure_services.supprimer(self.navire, self.admin)

    def test_suppression_directe_par_l_orm_est_bloquee_par_protect(self):
        with self.assertRaises(ProtectedError):
            Section.objects.filter(pk=self.section.pk).delete()
        self.assertTrue(UserProfile.objects.filter(user=self.marin, section=self.section).exists())

    def test_apres_reaffectation_la_suppression_est_possible(self):
        UserProfile.objects.filter(user=self.marin).update(ship=None, service=None, sector=None, section=None)
        structure_services.supprimer(self.section, self.admin)
        self.assertFalse(Section.objects.filter(pk=self.section.pk).exists())


class ApiTests(Base):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_api_refuse_une_unite_referencee_en_409(self):
        reponse = self.client.delete(f"/api/org/sections/{self.section.pk}/")
        self.assertEqual(reponse.status_code, 409, reponse.content)
        self.assertIn("references", reponse.json())
        self.assertTrue(Section.objects.filter(pk=self.section.pk).exists())

    def test_api_supprime_une_unite_vide_en_204(self):
        UserProfile.objects.filter(user=self.marin).update(section=None)
        reponse = self.client.delete(f"/api/org/sections/{self.section.pk}/")
        self.assertEqual(reponse.status_code, 204, reponse.content)


class EcranEtAdminTests(Base):
    def test_ecran_reglages_refuse_et_garde_l_unite(self):
        self.client.force_login(self.admin)
        reponse = self.client.post(reverse("settings"), {"action": "delete_section", "pk": self.section.pk}, follow=True)
        self.assertTrue(Section.objects.filter(pk=self.section.pk).exists())
        self.assertContains(reponse, "Impossible de supprimer")

    def test_ecran_reglages_supprime_une_section_vide(self):
        UserProfile.objects.filter(user=self.marin).update(section=None)
        self.client.force_login(self.admin)
        self.client.post(reverse("settings"), {"action": "delete_section", "pk": self.section.pk}, follow=True)
        self.assertFalse(Section.objects.filter(pk=self.section.pk).exists())

    def test_administration_refuse_sans_cascade(self):
        requete = RequestFactory().post("/")
        requete.user = self.admin
        requete.session, requete._messages = {}, type("M", (), {"add": lambda *a, **k: None})()
        admin_site._registry[Service].delete_model(requete, self.service)
        self.assertTrue(Service.objects.filter(pk=self.service.pk).exists())
        self.assertTrue(UserProfile.objects.filter(user=self.marin, section=self.section).exists())
