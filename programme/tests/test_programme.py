"""Programme du bâtiment : saisie par l'état-major, délégation, ciblage, notifications et calendrier."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from notifications.models import Notification
from org.models import Sector, Service, Ship
from programme import services
from programme.models import EvenementProgramme


class ProgrammeBase(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Programme", code="PR")
        self.energie = Service.objects.create(ship=self.navire, name="Énergie")
        self.pont = Service.objects.create(ship=self.navire, name="Pont")
        self.secteur = Sector.objects.create(service=self.energie, name="Propulsion")
        self.second = self._marin("second", None, None, "COMMANDANT_EN_SECOND")
        self.chef_energie = self._marin("chef_energie", self.energie, None, "CHEF_SERVICE")
        self.marin = self._marin("marin", self.energie, self.secteur, "EQUIPIER")
        self.matelot_pont = self._marin("pont", self.pont, None, "EQUIPIER")
        self.etranger = self._marin("etranger", None, None, "EQUIPIER", navire=Ship.objects.create(name="Autre", code="AU"))
        self.demain = timezone.now() + timedelta(days=1)

    def _marin(self, nom, service, secteur, role, navire=None):
        user = User.objects.create_user(username=nom, password="pass")
        p = user.profile
        p.role, p.ship, p.service, p.sector = role, navire or self.navire, service, secteur
        p.save()
        return user

    def _type(self, nom="Exercice"):
        return services.types_du_navire(self.navire.pk).get(nom=nom).pk


class SaisieEtDroitsTests(ProgrammeBase):
    def test_etat_major_saisit_et_le_public_vise_est_prevenu(self):
        evt = services.creer_evenement(self.second, "Exercice incendie", self._type(), self.demain, None, f"ship:{self.navire.pk}")
        for marin in (self.marin, self.matelot_pont, self.chef_energie):
            self.assertTrue(services.evenements_visibles(marin).filter(pk=evt.pk).exists())
            self.assertEqual(Notification.objects.filter(user=marin, verb__startswith="Programme").count(), 1)
        self.assertFalse(services.evenements_visibles(self.etranger).filter(pk=evt.pk).exists())
        self.assertFalse(Notification.objects.filter(user=self.second).exists())

    def test_ciblage_service(self):
        evt = services.creer_evenement(self.second, "Réunion énergie", self._type("Réunion"), self.demain, None, f"service:{self.energie.pk}")
        self.assertTrue(services.evenements_visibles(self.marin).filter(pk=evt.pk).exists())
        self.assertFalse(services.evenements_visibles(self.matelot_pont).filter(pk=evt.pk).exists())
        self.assertFalse(Notification.objects.filter(user=self.matelot_pont).exists())

    def test_marin_sans_droit_refuse_puis_delegue(self):
        with self.assertRaises(PermissionError):
            services.creer_evenement(self.chef_energie, "x", self._type(), self.demain, None, f"service:{self.energie.pk}")
        services.deleguer(self.second, self.chef_energie)
        evt = services.creer_evenement(self.chef_energie, "Point service", self._type("Réunion"), self.demain, None, f"service:{self.energie.pk}")
        self.assertEqual(evt.auteur, self.chef_energie)
        with self.assertRaises(PermissionError):  # hors de son périmètre
            services.creer_evenement(self.chef_energie, "x", self._type(), self.demain, None, f"service:{self.pont.pk}")
        with self.assertRaises(PermissionError):
            services.deleguer(self.chef_energie, self.marin)
        services.retirer_delegation(self.second, self.chef_energie.delegations_programme.get().pk)
        self.assertFalse(services.peut_saisir(self.chef_energie))

    def test_horaire_modifie_notifie_une_fois_et_annulation(self):
        evt = services.creer_evenement(self.second, "Escale", self._type("Escale"), self.demain, None, f"ship:{self.navire.pk}")
        services.modifier_evenement(self.second, evt, "Escale", self.demain, None, lieu="Brest")  # horaire inchangé
        self.assertFalse(Notification.objects.filter(verb__startswith="Horaire modifié").exists())
        services.modifier_evenement(self.second, evt, "Escale", self.demain + timedelta(hours=3), None)
        self.assertEqual(Notification.objects.filter(user=self.marin, verb__startswith="Horaire modifié").count(), 1)
        services.annuler_evenement(self.second, evt)
        self.assertTrue(Notification.objects.filter(user=self.marin, verb__startswith="Annulé").exists())
        self.assertFalse(services.evenements_periode(self.marin, timezone.localdate(), timezone.localdate() + timedelta(days=3)).exists())

    def test_validations_et_types_configurables(self):
        with self.assertRaises(ValidationError):
            services.creer_evenement(self.second, "x", self._type(), self.demain, self.demain - timedelta(hours=1), f"ship:{self.navire.pk}")
        with self.assertRaises(PermissionError):
            services.ajouter_type(self.second, "Revue", "#123456")
        admin = self._marin("admin", None, None, "ADMIN_NAVIRE")
        services.ajouter_type(admin, "Revue d'armement", "#123456")
        self.assertTrue(services.types_du_navire(self.navire.pk).filter(nom="Revue d'armement").exists())

    def test_lien_avec_une_tache_preparatoire(self):
        from taches.models import Tache

        evt = services.creer_evenement(self.second, "Exercice", self._type(), self.demain, None, f"ship:{self.navire.pk}")
        tache = Tache.objects.create(titre="Vérifier les extincteurs", assigne=self.marin, created_by=self.second)
        services.lier_tache(self.second, evt, tache.pk)
        self.assertEqual(list(evt.taches.all()), [tache])
        with self.assertRaises(PermissionError):
            services.lier_tache(self.marin, evt, tache.pk)


class PagesEtCalendrierTests(ProgrammeBase):
    def test_tache_liee_invisible_pour_un_marin_sans_acces(self):
        from taches.models import Tache

        evt = services.creer_evenement(self.second, "Exercice", self._type(), self.demain, None, f"ship:{self.navire.pk}")
        tache = Tache.objects.create(titre="Tâche confidentielle XYZ", assigne=self.marin, created_by=self.second, partagee=False)
        services.lier_tache(self.second, evt, tache.pk)
        self.client.force_login(self.matelot_pont)
        self.assertNotContains(self.client.get(reverse("evenement-detail", args=[evt.pk])), "confidentielle XYZ")
        self.client.force_login(self.marin)
        self.assertContains(self.client.get(reverse("evenement-detail", args=[evt.pk])), "confidentielle XYZ")

    def test_pages_et_acces(self):
        evt = services.creer_evenement(self.second, "Exercice", self._type(), self.demain, None, f"service:{self.energie.pk}")
        self.client.force_login(self.marin)
        self.assertContains(self.client.get(reverse("programme-index")), "Exercice")
        self.assertEqual(self.client.get(reverse("evenement-nouveau")).status_code, 404)
        self.client.force_login(self.matelot_pont)
        self.assertEqual(self.client.get(reverse("evenement-detail", args=[evt.pk])).status_code, 404)
        self.client.force_login(self.second)
        self.assertEqual(self.client.get(reverse("programme-reglages")).status_code, 200)
        reponse = self.client.post(reverse("evenement-nouveau"), {
            "titre": "Escale Brest", "type": self._type("Escale"), "debut": "2030-01-10T08:00",
            "cible": f"ship:{self.navire.pk}"})
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(EvenementProgramme.objects.filter(titre="Escale Brest").exists())

    def test_evenement_dans_l_agenda_du_marin_cible_seulement(self):
        services.creer_evenement(self.second, "Exercice énergie", self._type(), self.demain, None, f"service:{self.energie.pk}")
        jour = timezone.localdate()
        parametres = {"start": jour.isoformat(), "end": (jour + timedelta(days=5)).isoformat()}
        self.client.force_login(self.marin)
        titres = [e["title"] for e in self.client.get(reverse("calendar-events"), parametres).json()]
        self.assertIn("Exercice - Exercice énergie", titres)
        self.client.force_login(self.matelot_pont)
        titres = [e["title"] for e in self.client.get(reverse("calendar-events"), parametres).json()]
        self.assertNotIn("Exercice - Exercice énergie", titres)
