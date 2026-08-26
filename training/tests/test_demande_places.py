"""Tests du Circuit A — Demande et attribution de places sur une formation à
quota (ex. TP Sécurité) : un chef de secteur demande des places pour son
bord (DemandePlace), l'organisme de formation (référent de la formation POUR
SON PROPRE NAVIRE, cf. peut_valider_formation) attribue un nombre de places
éventuellement relié à une session, puis le chef de secteur affecte des
marins de son secteur sur ces places attribuées (PlaceAffectee), dans la
limite du quota propre à SA demande — en plus (pas à la place) du contrôle
de capacité physique globale de la session déjà appliqué par le signal
existant TrainingSession.reservations::_controler_reservation."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from notifications.models import Notification
from org.models import Sector, Section, Service, Ship
from training.models import (
    DemandePlace,
    PlaceAffectee,
    ReferentFormation,
    TrainingCourse,
    TrainingSession,
)


def _construire_bord(prefixe):
    """Construit une hiérarchie Navire > Service > Secteur > Section complète,
    pour disposer d'un navire résolvable via training.models.navire_de à
    partir du secteur (cas le plus courant d'un chef de secteur)."""
    ship = Ship.objects.create(name=f"Navire {prefixe}", code=prefixe[:8])
    service = Service.objects.create(ship=ship, name=f"Service {prefixe}")
    sector = Sector.objects.create(service=service, name=f"Secteur {prefixe}")
    section = Section.objects.create(sector=sector, name=f"Section {prefixe}")
    return ship, service, sector, section


class CreationDemandePlaceTests(TestCase):
    """Un chef de secteur (CHEF_SECTEUR, seuil CHEF_SECTION+) peut formuler
    une demande de places pour son propre bord."""

    def setUp(self):
        self.ship, self.service, self.sector, self.section = _construire_bord("DEM")
        self.course = TrainingCourse.objects.create(title="TP Sécurité")
        self.chef = User.objects.create_user(username="chef_secteur_dem", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef, defaults={"role": "CHEF_SECTEUR", "sector": self.sector},
        )

    def test_creation_demande_reussie(self):
        self.client.login(username="chef_secteur_dem", password="pass")
        r = self.client.post("/formations/", {
            "action": "demander_places",
            "course_id": self.course.id,
            "nb_places_demandees": 3,
        })
        self.assertEqual(r.status_code, 302)
        demande = DemandePlace.objects.get(course=self.course)
        self.assertEqual(demande.ship, self.ship)
        self.assertEqual(demande.nb_places_demandees, 3)
        self.assertEqual(demande.statut, "REQUESTED")
        self.assertEqual(demande.created_by, self.chef)

    def test_annulation_de_sa_propre_demande(self):
        demande = DemandePlace.objects.create(
            course=self.course, ship=self.ship, nb_places_demandees=2, created_by=self.chef,
        )
        self.client.login(username="chef_secteur_dem", password="pass")
        self.client.post("/formations/", {"action": "annuler_demande_place", "demande_id": demande.id})
        demande.refresh_from_db()
        self.assertEqual(demande.statut, "CANCELLED")


class RefusHorsPerimetreDemandePlaceTests(TestCase):
    """Refus de la création d'une demande hors périmètre : un rôle sous le
    seuil requis (EQUIPIER), ou un profil sans aucune unité rattachée
    (navire_de introuvable), ne peuvent pas formuler de demande."""

    def setUp(self):
        self.course = TrainingCourse.objects.create(title="TP Sécurité Refus")

    def test_equipier_ne_peut_pas_demander_de_places(self):
        equipier = User.objects.create_user(username="equipier_dem_refus", password="pass")
        UserProfile.objects.update_or_create(user=equipier, defaults={"role": "EQUIPIER"})
        self.client.login(username="equipier_dem_refus", password="pass")
        r = self.client.post("/formations/", {
            "action": "demander_places",
            "course_id": self.course.id,
            "nb_places_demandees": 2,
        })
        self.assertEqual(r.status_code, 403)
        self.assertEqual(DemandePlace.objects.count(), 0)

    def test_chef_sans_unite_rattachee_est_refuse(self):
        chef_sans_bord = User.objects.create_user(username="chef_sans_bord", password="pass")
        UserProfile.objects.update_or_create(user=chef_sans_bord, defaults={"role": "CHEF_SECTEUR"})
        self.client.login(username="chef_sans_bord", password="pass")
        r = self.client.post("/formations/", {
            "action": "demander_places",
            "course_id": self.course.id,
            "nb_places_demandees": 2,
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(DemandePlace.objects.count(), 0)


class AttributionParReferentTests(TestCase):
    """Le référent de la formation POUR L'ORGANISME (école/centre de
    formation, cf. peut_valider_formation) attribue des places, avec création
    d'une nouvelle session dans la foulée, et notifie le demandeur."""

    def setUp(self):
        self.ecole = Ship.objects.create(
            name="École Sécurité", code="ECOLE1", type_unite=Ship.TypeUnite.ECOLE,
        )
        self.ship, _, self.sector, _ = _construire_bord("ATTR")
        self.course = TrainingCourse.objects.create(title="TP Sécurité Attribution")
        self.referent = User.objects.create_user(username="referent_ecole", password="pass")
        UserProfile.objects.update_or_create(
            user=self.referent, defaults={"role": "EQUIPIER", "ship": self.ecole},
        )
        ReferentFormation.objects.create(course=self.course, ship=self.ecole, user=self.referent)
        self.referent = User.objects.get(pk=self.referent.pk)
        self.chef = User.objects.create_user(username="chef_secteur_attr", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef, defaults={"role": "CHEF_SECTEUR", "sector": self.sector},
        )
        self.demande = DemandePlace.objects.create(
            course=self.course, ship=self.ship, nb_places_demandees=3, created_by=self.chef,
        )

    def test_attribution_avec_nouvelle_session(self):
        self.client.login(username="referent_ecole", password="pass")
        date_session = (timezone.now() + timedelta(days=20)).strftime("%Y-%m-%dT%H:%M")
        r = self.client.post("/formations/", {
            "action": "attribuer_places",
            "demande_id": self.demande.id,
            "nb_places_attribuees": 2,
            "nouvelle_session_date": date_session,
            "nouvelle_session_lieu": "Centre de secours",
            "nouvelle_session_capacite": 10,
        })
        self.assertEqual(r.status_code, 302)
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut, "GRANTED")
        self.assertEqual(self.demande.nb_places_attribuees, 2)
        self.assertIsNotNone(self.demande.session)
        self.assertEqual(self.demande.session.course, self.course)
        self.assertEqual(self.demande.attribue_par, self.referent)
        self.assertIsNotNone(self.demande.date_attribution)

    def test_attribution_envoie_une_notification_au_demandeur(self):
        self.client.login(username="referent_ecole", password="pass")
        date_session = (timezone.now() + timedelta(days=20)).strftime("%Y-%m-%dT%H:%M")
        self.client.post("/formations/", {
            "action": "attribuer_places",
            "demande_id": self.demande.id,
            "nb_places_attribuees": 2,
            "nouvelle_session_date": date_session,
        })
        notif = Notification.objects.filter(user=self.chef).first()
        self.assertIsNotNone(notif)
        self.assertIn("accordée", notif.verb)
        self.assertEqual(notif.level, "info")

    def test_attribution_sur_session_existante(self):
        session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=15), capacite_max=10,
        )
        self.client.login(username="referent_ecole", password="pass")
        self.client.post("/formations/", {
            "action": "attribuer_places",
            "demande_id": self.demande.id,
            "nb_places_attribuees": 1,
            "session_id": session.id,
        })
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.session, session)
        self.assertEqual(TrainingSession.objects.count(), 1)


class RefusAttributionParNonReferentTests(TestCase):
    """Un utilisateur qui n'est pas référent de cette formation pour
    l'organisme ne peut pas attribuer (ni refuser) de places."""

    def setUp(self):
        self.ecole = Ship.objects.create(
            name="École Sécurité Refus", code="ECREF", type_unite=Ship.TypeUnite.ECOLE,
        )
        self.ship, _, self.sector, _ = _construire_bord("NREF")
        self.course = TrainingCourse.objects.create(title="TP Sécurité Non Référent")
        self.non_referent = User.objects.create_user(username="non_referent_ecole", password="pass")
        UserProfile.objects.update_or_create(
            user=self.non_referent, defaults={"role": "EQUIPIER", "ship": self.ecole},
        )
        self.chef = User.objects.create_user(username="chef_secteur_nref", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef, defaults={"role": "CHEF_SECTEUR", "sector": self.sector},
        )
        self.demande = DemandePlace.objects.create(
            course=self.course, ship=self.ship, nb_places_demandees=2, created_by=self.chef,
        )

    def test_non_referent_ne_peut_pas_attribuer(self):
        self.client.login(username="non_referent_ecole", password="pass")
        r = self.client.post("/formations/", {
            "action": "attribuer_places",
            "demande_id": self.demande.id,
            "nb_places_attribuees": 1,
            "nouvelle_session_date": (timezone.now() + timedelta(days=10)).strftime("%Y-%m-%dT%H:%M"),
        })
        self.assertEqual(r.status_code, 403)
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut, "REQUESTED")

    def test_non_referent_ne_peut_pas_refuser(self):
        self.client.login(username="non_referent_ecole", password="pass")
        r = self.client.post("/formations/", {
            "action": "refuser_demande_place",
            "demande_id": self.demande.id,
        })
        self.assertEqual(r.status_code, 403)
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.statut, "REQUESTED")


class AffectationQuotaDemandePlaceTests(TestCase):
    """L'affectation d'un marin sur une place attribuée respecte le quota
    PROPRE À LA DEMANDE (PlaceAffectee), en plus (pas à la place) du plafond
    physique global déjà appliqué par TrainingSession.reservations."""

    def setUp(self):
        self.ship, _, self.sector, _ = _construire_bord("QUOTA")
        self.course = TrainingCourse.objects.create(title="TP Sécurité Quota")
        # Capacité physique large : le quota par bord (1) doit bloquer avant
        # que la capacité globale ne soit jamais atteinte.
        self.session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=12), capacite_max=10,
        )
        self.chef = User.objects.create_user(username="chef_secteur_quota", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef, defaults={"role": "CHEF_SECTEUR", "sector": self.sector},
        )
        self.demande = DemandePlace.objects.create(
            course=self.course, ship=self.ship, nb_places_demandees=1, nb_places_attribuees=1,
            session=self.session, statut="GRANTED", created_by=self.chef,
        )
        self.marin1 = User.objects.create_user(username="marin_quota1", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin1, defaults={"role": "EQUIPIER", "sector": self.sector},
        )
        self.marin2 = User.objects.create_user(username="marin_quota2", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin2, defaults={"role": "EQUIPIER", "sector": self.sector},
        )

    def test_affectation_dans_la_limite_du_quota(self):
        self.client.login(username="chef_secteur_quota", password="pass")
        r = self.client.post("/formations/", {
            "action": "affecter_place_demandee",
            "demande_id": self.demande.id,
            "marin_id": self.marin1.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertIn(self.marin1, self.session.reservations.all())
        self.assertTrue(
            PlaceAffectee.objects.filter(demande_place=self.demande, marin=self.marin1).exists()
        )

    def test_refus_au_dela_du_quota_meme_si_capacite_globale_disponible(self):
        PlaceAffectee.objects.create(demande_place=self.demande, marin=self.marin1)
        self.session.reservations.add(self.marin1)
        self.client.login(username="chef_secteur_quota", password="pass")
        r = self.client.post("/formations/", {
            "action": "affecter_place_demandee",
            "demande_id": self.demande.id,
            "marin_id": self.marin2.id,
        })
        self.assertEqual(r.status_code, 302)
        self.assertNotIn(self.marin2, self.session.reservations.all())
        self.assertFalse(
            PlaceAffectee.objects.filter(demande_place=self.demande, marin=self.marin2).exists()
        )
        # La session a pourtant encore de la capacité physique disponible.
        self.assertGreater(self.session.places_restantes(), 0)


class CoexistenceDemandesMemeSessionTests(TestCase):
    """Deux bords différents partagent la MÊME session, chacun avec son
    propre quota (DemandePlace distinctes) : la consommation du quota de
    l'un n'interfère pas avec celle de l'autre."""

    def setUp(self):
        self.ship_a, _, self.sector_a, _ = _construire_bord("BORDA")
        self.ship_b, _, self.sector_b, _ = _construire_bord("BORDB")
        self.course = TrainingCourse.objects.create(title="TP Sécurité Partagée")
        self.session = TrainingSession.objects.create(
            course=self.course, scheduled_at=timezone.now() + timedelta(days=8), capacite_max=10,
        )
        self.chef_a = User.objects.create_user(username="chef_bord_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_a, defaults={"role": "CHEF_SECTEUR", "sector": self.sector_a},
        )
        self.chef_b = User.objects.create_user(username="chef_bord_b", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef_b, defaults={"role": "CHEF_SECTEUR", "sector": self.sector_b},
        )
        self.demande_a = DemandePlace.objects.create(
            course=self.course, ship=self.ship_a, nb_places_demandees=1, nb_places_attribuees=1,
            session=self.session, statut="GRANTED", created_by=self.chef_a,
        )
        self.demande_b = DemandePlace.objects.create(
            course=self.course, ship=self.ship_b, nb_places_demandees=1, nb_places_attribuees=1,
            session=self.session, statut="GRANTED", created_by=self.chef_b,
        )
        self.marin_a = User.objects.create_user(username="marin_bord_a", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin_a, defaults={"role": "EQUIPIER", "sector": self.sector_a},
        )
        self.marin_b = User.objects.create_user(username="marin_bord_b", password="pass")
        UserProfile.objects.update_or_create(
            user=self.marin_b, defaults={"role": "EQUIPIER", "sector": self.sector_b},
        )

    def test_les_deux_bords_affectent_leur_marin_sans_interference(self):
        self.client.login(username="chef_bord_a", password="pass")
        self.client.post("/formations/", {
            "action": "affecter_place_demandee",
            "demande_id": self.demande_a.id,
            "marin_id": self.marin_a.id,
        })
        self.client.logout()
        self.client.login(username="chef_bord_b", password="pass")
        self.client.post("/formations/", {
            "action": "affecter_place_demandee",
            "demande_id": self.demande_b.id,
            "marin_id": self.marin_b.id,
        })
        self.assertIn(self.marin_a, self.session.reservations.all())
        self.assertIn(self.marin_b, self.session.reservations.all())
        self.assertEqual(self.demande_a.places_consommees(), 1)
        self.assertEqual(self.demande_b.places_consommees(), 1)

    def test_bord_a_ne_peut_pas_affecter_un_marin_hors_secteur_sur_la_demande_de_b(self):
        # Le chef du bord A n'est pas le demandeur de la demande B : refus,
        # même si la session est partagée.
        self.client.login(username="chef_bord_a", password="pass")
        r = self.client.post("/formations/", {
            "action": "affecter_place_demandee",
            "demande_id": self.demande_b.id,
            "marin_id": self.marin_a.id,
        })
        self.assertEqual(r.status_code, 403)
        self.assertNotIn(self.marin_a, self.session.reservations.all())
