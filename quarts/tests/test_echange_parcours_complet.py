"""Échange de tours de bout en bout par l'interface, sur une liste de service à quai de plusieurs jours : demande, réponse,
décision du chef de liste, mise à jour des affectations, notifications et traçabilité ; refus du marin, rejet du chef,
conflits réels (absence validée, autre liste publiée). Aucune double affectation fictive mer/quai dans ce scénario."""
from quarts.tests.support import designer_chef
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from absences.models import Absence, TypeAbsence
from accounts.models import AuditLog, ServiceFunctionChoice, UserProfile
from calendar_app.evenements_sources import _creneaux_garde_assignes
from notifications.models import Notification
from org.models import Sector, Service, Ship
from quarts.models import ChefDeListe, CreneauServiceGarde, EchangeService, ServiceGarde


class ParcoursEchangeCompletTests(TestCase):
    def setUp(self):
        self.client.raise_request_exception = False
        self.navire = Ship.objects.create(name="Bretagne échanges", code="BX", double_equipage=True, equipage_a_bord="A")
        self.service = Service.objects.create(ship=self.navire, name="Vie à bord", commandant_adjoint="COMAEQ")
        self.secteur = Sector.objects.create(service=self.service, name="Service courant")
        self.fonction = ServiceFunctionChoice.objects.create(name="Service à quai")
        self.chef = self._marin("chef_liste", "CHEF_SERVICE", service=self.service)
        designer_chef(user=self.chef, service=self.service)
        self.alice = self._marin("alice", "EQUIPIER", sector=self.secteur)
        self.bruno = self._marin("bruno", "EQUIPIER", sector=self.secteur)
        self.chloe = self._marin("chloe", "EQUIPIER", sector=self.secteur)
        self.marin_b = self._marin("marin_b", "EQUIPIER", equipage="B", sector=self.secteur)
        base = timezone.localdate() + timedelta(days=21)
        self.jours = [base + timedelta(days=i) for i in range(3)]
        self.liste = ServiceGarde.objects.create(
            service=self.service, nom="Service à quai — semaine X", equipage="A", fonction=self.fonction,
            date_debut=self.jours[0], date_fin=self.jours[-1], type_service="Service à quai", duree_creneau_heures=24, created_by=self.chef)
        self.tours = {}
        for jour, marin in zip(self.jours, (self.alice, self.bruno, self.chloe)):
            debut = timezone.make_aware(datetime.combine(jour, datetime.min.time().replace(hour=8)))
            self.tours[marin.username] = CreneauServiceGarde.objects.create(
                service_garde=self.liste, poste="Gradé de coupée 1", marin=marin, debut=debut, fin=debut + timedelta(hours=24))
        self.liste.publier(self.chef)

    def _marin(self, nom, role, equipage="A", **champs):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": self.navire, "equipage": equipage, **champs})
        return User.objects.get(pk=user.pk)

    def _proposer(self, demandeur, mon_tour, son_tour, motif="Rendez-vous médical"):
        self.client.force_login(demandeur)
        return self.client.post(reverse("echange-proposer", args=[self.liste.pk]), {
            "creneau_id": self.tours[mon_tour].pk, "cible_creneau_id": self.tours[son_tour].pk, "motif": motif})

    def _agir(self, qui, echange, action, motif=""):
        self.client.force_login(qui)
        return self.client.post(reverse("echange-action", args=[echange.pk, action]), {"motif": motif})

    def _marins(self):
        return {n: CreneauServiceGarde.objects.get(pk=t.pk).marin for n, t in self.tours.items()}

    def test_echange_complet_demande_acceptation_validation(self):
        versions_avant = self.liste.versions.count()
        self._proposer(self.alice, "alice", "bruno")
        echange = EchangeService.objects.get()
        self.assertEqual(echange.statut, EchangeService.STATUT_DEMANDE)
        self.assertTrue(Notification.objects.filter(user=self.bruno, verb__contains="vous propose un échange").exists())
        # Seul le marin sollicité répond ; ni le demandeur, ni un tiers, ni l'équipage B.
        for intrus in (self.alice, self.chloe, self.marin_b):
            self._agir(intrus, echange, "accepter")
            echange.refresh_from_db()
            self.assertEqual(echange.statut, EchangeService.STATUT_DEMANDE, intrus.username)
        self._agir(self.bruno, echange, "accepter")
        echange.refresh_from_db()
        self.assertEqual(echange.statut, EchangeService.STATUT_ACCEPTE)
        self.assertTrue(Notification.objects.filter(user=self.chef, verb__contains="Échange à valider").exists())
        self.assertTrue(Notification.objects.filter(user=self.alice, verb__contains="a accepté l'échange").exists())
        # Les affectations ne changent qu'à la décision du chef de liste ; un marin ne peut pas valider.
        self.assertEqual(self._marins()["alice"], self.alice)
        self._agir(self.alice, echange, "valider")
        echange.refresh_from_db()
        self.assertEqual(echange.statut, EchangeService.STATUT_ACCEPTE)
        self._agir(self.chef, echange, "valider")
        echange.refresh_from_db()
        self.assertEqual((echange.statut, echange.decide_par), (EchangeService.STATUT_VALIDE, self.chef))
        # Mise à jour : les deux tours sont permutés, une version de la liste est figée, les calendriers suivent.
        self.assertEqual(self._marins(), {"alice": self.bruno, "bruno": self.alice, "chloe": self.chloe})
        self.assertEqual(self.liste.versions.count(), versions_avant + 1)
        jour_alice, jour_bruno = self.jours[0], self.jours[1]
        self.assertEqual([c.pk for c in _creneaux_garde_assignes(jour_alice, jour_alice, self.bruno)], [self.tours["alice"].pk])
        self.assertEqual([c.pk for c in _creneaux_garde_assignes(jour_bruno, jour_bruno, self.alice)], [self.tours["bruno"].pk])
        self.assertEqual(list(_creneaux_garde_assignes(jour_alice, jour_alice, self.alice)), [])
        # Traçabilité et notifications.
        actions = list(echange.evenements.order_by("pk").values_list("action", flat=True))
        self.assertEqual(actions, ["demande", "acceptation", "validation"])
        self.assertTrue(Notification.objects.filter(user=self.alice, verb__contains="Échange validé").exists())
        self.assertTrue(Notification.objects.filter(user=self.bruno, verb__contains="Échange validé").exists())

    def test_refus_du_marin_sollicite(self):
        self._proposer(self.chloe, "chloe", "alice")
        echange = EchangeService.objects.get()
        self._agir(self.alice, echange, "refuser", motif="Indisponible ce jour-là")
        echange.refresh_from_db()
        self.assertEqual(echange.statut, EchangeService.STATUT_REFUSE)
        self.assertEqual(echange.motif_decision, "Indisponible ce jour-là")
        self.assertTrue(Notification.objects.filter(user=self.chloe, verb__contains="a refusé l'échange").exists())
        self.assertEqual(self._marins(), {"alice": self.alice, "bruno": self.bruno, "chloe": self.chloe})
        self.assertEqual(list(echange.evenements.order_by("pk").values_list("action", flat=True)), ["demande", "refus_marin"])

    def test_rejet_du_chef_de_liste_apres_acceptation(self):
        self._proposer(self.alice, "alice", "chloe")
        echange = EchangeService.objects.get()
        self._agir(self.chloe, echange, "accepter")
        self._agir(self.chef, echange, "rejeter", motif="Effectif insuffisant ce jour-là")
        echange.refresh_from_db()
        self.assertEqual(echange.statut, EchangeService.STATUT_REJETE)
        self.assertEqual(self._marins(), {"alice": self.alice, "bruno": self.bruno, "chloe": self.chloe})
        for marin in (self.alice, self.chloe):
            self.assertTrue(Notification.objects.filter(user=marin, verb__contains="le chef de liste a refusé", ).exists()
                            or Notification.objects.filter(user=marin, verb__contains="Le chef de liste a refusé").exists(), marin.username)

    def test_conflit_reel_absence_validee(self):
        permission = TypeAbsence.objects.create(name="Permission")
        Absence.objects.create(marin=self.bruno, type_absence=permission, date_debut=self.jours[0], date_fin=self.jours[0], statut=Absence.STATUT_VALIDEE)
        self._proposer(self.alice, "alice", "bruno")
        self.assertFalse(EchangeService.objects.exists())

    def test_conflit_reel_avec_une_autre_liste_publiee_au_meme_moment(self):
        autre = ServiceGarde.objects.create(
            service=self.service, nom="Permanence", equipage="A", fonction=self.fonction,
            date_debut=self.jours[0], date_fin=self.jours[0], type_service="Permanence", duree_creneau_heures=24, created_by=self.chef)
        t = self.tours["alice"]
        CreneauServiceGarde.objects.create(service_garde=autre, poste="Permanence", marin=self.bruno, debut=t.debut, fin=t.fin)
        autre.publier(self.chef)
        self._proposer(self.alice, "alice", "bruno")
        self.assertFalse(EchangeService.objects.exists(), "bruno est réellement pris sur la permanence")
        self.client.force_login(self.alice)
        suivi = self.client.get(reverse("garde-detail", args=[self.liste.pk]))
        self.assertContains(suivi, "Conflit d")  # message explicite : Conflit d'affectation

    def test_un_tour_deja_commence_ne_s_echange_plus(self):
        CreneauServiceGarde.objects.filter(pk=self.tours["alice"].pk).update(debut=timezone.now() - timedelta(hours=2), fin=timezone.now() + timedelta(hours=22))
        self._proposer(self.alice, "alice", "bruno")
        self.assertFalse(EchangeService.objects.exists())

    def test_l_equipage_b_ne_voit_pas_et_n_echange_pas_avec_l_equipage_a(self):
        self.client.force_login(self.marin_b)
        reponse = self.client.post(reverse("echange-proposer", args=[self.liste.pk]), {
            "creneau_id": self.tours["alice"].pk, "cible_creneau_id": self.tours["bruno"].pk})
        self.assertIn(reponse.status_code, (302, 403, 404))
        self.assertFalse(EchangeService.objects.exists())
        self._proposer(self.alice, "alice", "bruno")
        echange = EchangeService.objects.get()
        self.assertIn(self._agir(self.marin_b, echange, "accepter").status_code, (403, 404))
        echange.refresh_from_db()
        self.assertEqual(echange.statut, EchangeService.STATUT_DEMANDE)

    def test_annulation_par_le_demandeur_avant_decision(self):
        self._proposer(self.alice, "alice", "bruno")
        echange = EchangeService.objects.get()
        self._agir(self.bruno, echange, "annuler")
        echange.refresh_from_db()
        self.assertEqual(echange.statut, EchangeService.STATUT_DEMANDE, "le sollicité ne peut pas annuler la demande d'un autre")
        self._agir(self.alice, echange, "annuler", motif="Finalement non")
        echange.refresh_from_db()
        self.assertEqual(echange.statut, EchangeService.STATUT_ANNULE)
        self.assertEqual(self._marins()["alice"], self.alice)
