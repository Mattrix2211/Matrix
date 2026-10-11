"""Postes du bord : droits, affectation non bloquante, indicateurs d'effectifs et visibilité."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from org.models import Sector, Service, Ship
from postes import services
from training.models import TrainingCourse, TrainingRecord


class PostesBase(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Postes", code="PO")
        self.energie = Service.objects.create(ship=self.navire, name="Énergie")
        self.pont = Service.objects.create(ship=self.navire, name="Pont")
        self.secteur = Sector.objects.create(service=self.energie, name="Propulsion")
        self.chef = self._marin("chef", self.energie, None, "CHEF_SERVICE")
        self.marin = self._marin("marin", self.energie, self.secteur, "EQUIPIER")
        self.autre = self._marin("autre", self.energie, self.secteur, "EQUIPIER")
        self.pont_marin = self._marin("pont", self.pont, None, "EQUIPIER")
        self.etranger = self._marin("etranger", None, None, "EQUIPIER", navire=Ship.objects.create(name="Autre", code="AU"))
        self.incendie = TrainingCourse.objects.create(title="Lutte incendie", validity_days=365)
        self.secours = TrainingCourse.objects.create(title="Secourisme", validity_days=365)

    def _marin(self, nom, service, secteur, role, navire=None):
        user = User.objects.create_user(username=nom, password="pass")
        p = user.profile
        p.role, p.ship, p.service, p.sector = role, navire or self.navire, service, secteur
        p.save()
        return user

    def _poste(self, **kw):
        return services.creer_poste(self.chef, kw.pop("intitule", "Chef de quart machine"), f"service:{self.energie.pk}",
                                    kw.pop("effectif", 2), formations_ids=kw.pop("formations", [self.incendie.pk, self.secours.pk]))


class EffectifsTests(PostesBase):
    def test_affectation_sans_toutes_les_qualifications_est_signalee_sans_blocage(self):
        poste = self._poste()
        TrainingRecord.objects.create(user=self.marin, course=self.incendie, completed_at=timezone.localdate() - timedelta(days=30),
                                      expires_at=timezone.localdate() + timedelta(days=300))
        services.affecter(self.chef, poste, self.marin)  # pas de Secourisme : aucun blocage
        ligne = services.tableau_effectifs(self.chef)[0]
        self.assertEqual(ligne["non_pourvu"], 1)
        self.assertEqual([f.title for f in ligne["titulaires"][0]["manquantes"]], ["Secourisme"])
        self.assertEqual(ligne["sous_qualifies"], 1)

    def test_qualification_expiree_compte_comme_manquante_et_surplus_jamais_signale(self):
        poste = self._poste(formations=[self.incendie.pk])
        TrainingRecord.objects.create(user=self.marin, course=self.incendie, completed_at=timezone.localdate() - timedelta(days=400),
                                      expires_at=timezone.localdate() - timedelta(days=5))
        TrainingRecord.objects.create(user=self.autre, course=self.incendie, completed_at=timezone.localdate(), expires_at=timezone.localdate() + timedelta(days=300))
        TrainingRecord.objects.create(user=self.autre, course=self.secours, completed_at=timezone.localdate(), expires_at=timezone.localdate() + timedelta(days=300))
        services.affecter(self.chef, poste, self.marin)
        services.affecter(self.chef, poste, self.autre)
        ligne = services.tableau_effectifs(self.chef)[0]
        manquantes = {t["user"].username: len(t["manquantes"]) for t in ligne["titulaires"]}
        self.assertEqual(manquantes, {"marin": 1, "autre": 0})  # le surplus de Secourisme n'est pas un manque
        self.assertEqual(ligne["non_pourvu"], 0)


class DroitsEtVisibiliteTests(PostesBase):
    def test_creation_et_affectation_reservees_et_bornees(self):
        with self.assertRaises(PermissionError):
            services.creer_poste(self.marin, "x", f"service:{self.energie.pk}")
        with self.assertRaises(PermissionError):
            services.creer_poste(self.chef, "x", f"service:{self.pont.pk}")
        poste = self._poste()
        with self.assertRaises(PermissionError):
            services.affecter(self.marin, poste, self.autre)
        with self.assertRaises(ValidationError):
            services.affecter(self.chef, poste, self.etranger)
        with self.assertRaises(ValidationError):
            services.creer_poste(self.chef, " ", f"service:{self.energie.pk}")

    def test_un_marin_ne_voit_que_ses_postes_et_son_propre_etat(self):
        poste = self._poste()
        services.affecter(self.chef, poste, self.marin)
        services.affecter(self.chef, poste, self.autre)
        ligne = services.tableau_effectifs(self.marin)[0]
        self.assertEqual([t["user"] for t in ligne["titulaires"]], [self.marin])
        self.assertEqual(services.tableau_effectifs(self.pont_marin), [])
        self.assertEqual(services.tableau_effectifs(self.etranger), [])
        self.client.force_login(self.pont_marin)
        self.assertEqual(self.client.get(reverse("poste-detail", args=[poste.pk])).status_code, 404)

    def test_un_chef_hors_perimetre_ne_voit_pas_le_poste(self):
        poste = self._poste()
        chef_pont = self._marin("chef_pont", self.pont, None, "CHEF_SERVICE")
        self.assertEqual(services.tableau_effectifs(chef_pont), [])
        with self.assertRaises(PermissionError):
            services.affecter(chef_pont, poste, self.marin)

    def test_pages(self):
        poste = self._poste()
        services.affecter(self.chef, poste, self.marin)
        self.client.force_login(self.chef)
        self.assertContains(self.client.get(reverse("postes-index")), "Chef de quart machine")
        self.assertContains(self.client.get(reverse("poste-detail", args=[poste.pk])), "Qualifications manquantes")
        reponse = self.client.post(reverse("poste-nouveau"), {
            "intitule": "Électricien de quart", "cible": f"service:{self.energie.pk}", "effectif": "1", "formations": [self.incendie.pk]})
        self.assertEqual(reponse.status_code, 302)
        self.client.force_login(self.marin)
        self.assertEqual(self.client.get(reverse("poste-nouveau")).status_code, 404)
