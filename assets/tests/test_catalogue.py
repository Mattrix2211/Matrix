"""Catalogue de la flotte : lecture ouverte, écriture réservée aux responsables de la spécialité."""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import ResponsableSpecialite, SpecialityChoice, UserProfile
from assets.models import ArticleCatalogue, CategorieCatalogue
from assets.permissions import peut_gerer_catalogue

URL_CAT = "/api/assets/catalogue-categories/"
URL_ART = "/api/assets/catalogue-articles/"


class CatalogueTests(TestCase):
    def setUp(self):
        self.elec = SpecialityChoice.objects.create(name="Électricien cat")
        self.meca = SpecialityChoice.objects.create(name="Mécanicien cat")
        self.resp_elec = self._user("resp_elec", "EQUIPIER", self.elec)
        self.resp_meca = self._user("resp_meca", "EQUIPIER", self.meca)
        self.chef = self._user("chef_cat", "CHEF_SERVICE")
        self.bord = self._user("bord_cat", "EQUIPIER")
        self.master = self._user("master_cat", "MASTER_ADMIN")
        self.cat = CategorieCatalogue.objects.create(nom="Outillage", specialite=self.elec)

    def _user(self, nom, role, specialite=None):
        u = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=u, defaults={"role": role})
        if specialite:
            ResponsableSpecialite.objects.create(user=u, specialite=specialite)
        return User.objects.get(pk=u.pk)  # évite le profil mis en cache par le signal

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user)
        return c

    def test_helper(self):
        self.assertTrue(peut_gerer_catalogue(self.resp_elec, self.elec))
        self.assertFalse(peut_gerer_catalogue(self.resp_elec, self.meca))
        self.assertFalse(peut_gerer_catalogue(self.chef, self.elec))
        self.assertTrue(peut_gerer_catalogue(self.master, self.meca))

    def test_lecture_ouverte_a_tous(self):
        ArticleCatalogue.objects.create(categorie=self.cat, designation="Multimètre", marque="Fluke")
        for u in (self.bord, self.chef, self.resp_meca):
            c = self._client(u)
            self.assertEqual(c.get(URL_CAT).status_code, 200)
            r = c.get(URL_ART, {"search": "fluke"})
            self.assertEqual(len(r.data), 1 if isinstance(r.data, list) else r.data["count"])
        self.assertEqual(APIClient().get(URL_CAT).status_code in (401, 403), True)

    def test_responsable_cree_et_auteur_serveur(self):
        c = self._client(self.resp_elec)
        r = c.post(URL_CAT, {"nom": "Mesure", "specialite": self.elec.pk, "created_by": self.bord.pk}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        cat = CategorieCatalogue.objects.get(pk=r.data["id"])
        self.assertEqual(cat.created_by, self.resp_elec)
        r = c.post(URL_ART, {"categorie": cat.pk, "designation": "Pince", "updated_by": self.bord.pk}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(ArticleCatalogue.objects.get(pk=r.data["id"]).updated_by, self.resp_elec)
        r = c.patch(f"{URL_ART}{r.data['id']}/", {"actif": False}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_ecriture_refusee_aux_autres(self):
        art = ArticleCatalogue.objects.create(categorie=self.cat, designation="Pince")
        for u in (self.resp_meca, self.bord, self.chef):
            c = self._client(u)
            self.assertEqual(c.post(URL_CAT, {"nom": "X", "specialite": self.elec.pk}, format="json").status_code, 403)
            self.assertEqual(c.post(URL_ART, {"categorie": self.cat.pk, "designation": "X"}, format="json").status_code, 403)
            self.assertEqual(c.patch(f"{URL_ART}{art.pk}/", {"designation": "Y"}, format="json").status_code, 403)
            self.assertEqual(c.patch(f"{URL_CAT}{self.cat.pk}/", {"nom": "Y"}, format="json").status_code, 403)
        art.refresh_from_db()
        self.assertEqual(art.designation, "Pince")

    def test_transfert_vers_autre_specialite_refuse(self):
        r = self._client(self.resp_elec).patch(f"{URL_CAT}{self.cat.pk}/", {"specialite": self.meca.pk}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_suppression_reservee_au_master(self):
        self.assertEqual(self._client(self.resp_elec).delete(f"{URL_CAT}{self.cat.pk}/").status_code, 403)
        self.assertEqual(self._client(self.master).delete(f"{URL_CAT}{self.cat.pk}/").status_code, 204)

    def test_master_ecrit_partout(self):
        r = self._client(self.master).post(URL_CAT, {"nom": "Moteurs", "specialite": self.meca.pk}, format="json")
        self.assertEqual(r.status_code, 201, r.content)

    def test_cycle_refuse(self):
        fille = CategorieCatalogue.objects.create(nom="Fille", specialite=self.elec, parent=self.cat)
        r = self._client(self.resp_elec).patch(f"{URL_CAT}{self.cat.pk}/", {"parent": fille.pk}, format="json")
        self.assertEqual(r.status_code, 400)
        self.cat.parent = fille
        with self.assertRaises(ValidationError):
            self.cat.save()

    def test_sous_categorie_meme_specialite(self):
        r = self._client(self.master).post(
            URL_CAT, {"nom": "Z", "specialite": self.meca.pk, "parent": self.cat.pk}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_migrations_a_jour(self):
        call_command("makemigrations", "--check", "--dry-run", verbosity=0)
