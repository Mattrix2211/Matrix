"""Parcours complet anomalie → ticket correctif : signalement, prise en compte, conversion, rattachement, affectation,
suivi et clôture, avec permissions, notifications et traçabilité à chaque étape."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import AuditLog, UserProfile
from assets.models import Asset, AssetType
from logistics.models import Anomalie, AnomalieStatutLog, CorrectiveTicket, TicketStatusLog
from notifications.models import Notification
from org.models import Sector, Service, Ship


class ParcoursAnomalieTicketTests(TestCase):
    def setUp(self):
        self.client.raise_request_exception = False
        self.navire = Ship.objects.create(name="Bretagne parcours", code="BP", double_equipage=True, equipage_a_bord="A")
        self.nav = Service.objects.create(ship=self.navire, name="Navigation", commandant_adjoint="COMANAV")
        self.ops = Service.objects.create(ship=self.navire, name="Operations", commandant_adjoint="COMOPS")
        self.secteur = Sector.objects.create(service=self.nav, name="Moteurs")
        self.secteur_ops = Sector.objects.create(service=self.ops, name="Passerelle")
        type_asset = AssetType.objects.create(name="Pompe", category="MCO", sector=self.secteur)
        self.pompe = Asset.objects.create(asset_type=type_asset, internal_id="POMPE-1", designation="Pompe de refroidissement",
                                          ship=self.navire, service=self.nav, sector=self.secteur)
        self.declarant = self._marin("declarant", "EQUIPIER", sector=self.secteur)
        self.chef_secteur = self._marin("chef_secteur", "CHEF_SECTEUR", service=self.nav, sector=self.secteur)
        self.chef_secteur_ops = self._marin("chef_secteur_ops", "CHEF_SECTEUR", service=self.ops, sector=self.secteur_ops)
        self.mecano = self._marin("mecano", "EQUIPIER", sector=self.secteur)
        self.comanav = self._marin("comanav", "ETAT_MAJOR", fonction_coma="COMANAV")
        self.comops = self._marin("comops", "ETAT_MAJOR", fonction_coma="COMOPS")
        self.marin_b = self._marin("marin_b", "EQUIPIER", equipage="B", sector=self.secteur)

    def _marin(self, nom, role, equipage="A", fonction_coma="", **champs):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": self.navire, "equipage": equipage,
                                                                   "fonction_coma": fonction_coma, **champs})
        return User.objects.get(pk=user.pk)

    def _poster(self, qui, nom_route, args=(), donnees=None):
        self.client.force_login(qui)
        return self.client.post(reverse(nom_route, args=args), donnees or {})

    def test_parcours_complet_signalement_a_cloture(self):
        # 1. Signalement par un marin : rattaché au service et au secteur de l'équipement.
        reponse = self._poster(self.declarant, "anomalie-create", donnees={
            "asset": self.pompe.pk, "titre": "Fuite sur la pompe", "gravite": "4", "localisation": "Machine", "description": "Fuite continue."})
        self.assertEqual(reponse.status_code, 302)
        anomalie = Anomalie.objects.get(titre="Fuite sur la pompe")
        self.assertEqual((anomalie.statut, anomalie.created_by, anomalie.asset), ("SIGNALEE", self.declarant, self.pompe))
        self.assertEqual(anomalie.service, self.nav)
        self.assertTrue(Notification.objects.filter(user=self.chef_secteur).exists(), "le chef du secteur est prévenu")

        # 2. Permissions de traitement : ni le déclarant, ni un autre service, ni un autre commandant adjoint.
        for intrus, attendu in ((self.declarant, 403), (self.chef_secteur_ops, 404), (self.comops, 403), (self.marin_b, 403)):
            reponse = self._poster(intrus, "anomalie-transition", (anomalie.pk,), {"statut": "PRISE_EN_COMPTE"})
            self.assertEqual(reponse.status_code, attendu, intrus.username)
        anomalie.refresh_from_db()
        self.assertEqual(anomalie.statut, "SIGNALEE")

        # 3. Prise en compte par le chef de secteur : statut, journal, notification du déclarant.
        self._poster(self.chef_secteur, "anomalie-transition", (anomalie.pk,), {"statut": "PRISE_EN_COMPTE", "note": "Vu sur place"})
        anomalie.refresh_from_db()
        self.assertEqual(anomalie.statut, "PRISE_EN_COMPTE")
        self.assertTrue(AnomalieStatutLog.objects.filter(anomalie=anomalie, nouveau_statut="PRISE_EN_COMPTE", user=self.chef_secteur).exists())
        self.assertTrue(Notification.objects.filter(user=self.declarant).exists())

        # 4. Conversion en ticket : rattachement à l'équipement, anomalie liée, trace, une seule conversion.
        self.assertEqual(self._poster(self.comops, "anomalie-convertir", (anomalie.pk,)).status_code, 403)
        reponse = self._poster(self.chef_secteur, "anomalie-convertir", (anomalie.pk,))
        anomalie.refresh_from_db()
        ticket = anomalie.ticket
        self.assertIsNotNone(ticket)
        self.assertRedirects(reponse, reverse("ticket-detail", args=[ticket.pk]), fetch_redirect_response=False)
        self.assertEqual((ticket.asset, ticket.severity, ticket.status), (self.pompe, 4, "REPORTED"))
        self.assertTrue(AuditLog.objects.filter(action="anomalie_convertie_ticket", actor=self.chef_secteur).exists())
        self._poster(self.chef_secteur, "anomalie-convertir", (anomalie.pk,))
        self.assertEqual(CorrectiveTicket.objects.count(), 1, "pas de doublon de ticket")

        # 5. Affectation du ticket : le mécanicien est prévenu ; un autre service ne peut pas affecter.
        self.assertEqual(self._poster(self.chef_secteur_ops, "ticket-assign", (ticket.pk,), {"assignees": [self.mecano.pk]}).status_code, 404)
        self.assertEqual(self._poster(self.comops, "ticket-assign", (ticket.pk,), {"assignees": [self.mecano.pk]}).status_code, 403)
        self._poster(self.chef_secteur, "ticket-assign", (ticket.pk,), {"assignees": [self.mecano.pk]})
        self.assertEqual(list(ticket.assignees.all()), [self.mecano])
        self.assertTrue(Notification.objects.filter(user=self.mecano, verb__contains="assigné").exists())

        # 6. Suivi et clôture : le COMANAV (service rattaché) agit, le COMOPS non ; chaque statut est journalisé.
        for statut in ("DIAGNOSED", "IN_REPAIR", "TESTING"):
            self.assertEqual(self._poster(self.comops, "ticket-transition", (ticket.pk,), {"status": statut}).status_code, 403, statut)
            self._poster(self.comanav, "ticket-transition", (ticket.pk,), {"status": statut})
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "TESTING")
        # Remise en service : confirmation explicite obligatoire (refus tracé), puis clôture avec diagnostic et solution.
        self._poster(self.chef_secteur, "ticket-transition", (ticket.pk,), {"status": "RETURNED_TO_SERVICE", "confirmation": "on"})
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "TESTING")
        retour = {"diagnostic_final": "Joint défectueux", "solution": "Joint remplacé"}
        self._poster(self.chef_secteur, "ticket-transition", (ticket.pk,), {"status": "RETURNED_TO_SERVICE", "confirmation": "1", **retour})
        self._poster(self.chef_secteur, "ticket-transition", (ticket.pk,), {"status": "CLOSED"})
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "RETURNED_TO_SERVICE", "clôture refusée sans diagnostic ni solution")
        self._poster(self.chef_secteur, "ticket-transition", (ticket.pk,), {"status": "CLOSED", **retour})
        self.assertTrue(AuditLog.objects.filter(action="ticket_validation_critique", actor=self.chef_secteur).exists())
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "CLOSED")
        journal = list(TicketStatusLog.objects.filter(ticket=ticket).order_by("pk").values_list("new_status", flat=True))
        self.assertEqual(journal[-5:], ["DIAGNOSED", "IN_REPAIR", "TESTING", "RETURNED_TO_SERVICE", "CLOSED"])

        # 7. Le déclarant suit l'issue depuis « Mes signalements » et voit le ticket lié ; contexte conservé par le lien retour.
        self.client.force_login(self.declarant)
        suivi = self.client.get(reverse("anomalie-detail", args=[anomalie.pk]))
        self.assertEqual(suivi.status_code, 200)
        self.assertContains(suivi, reverse("ticket-detail", args=[ticket.pk]))
        self.assertContains(suivi, 'class="mx-retour__lien"')

    def test_une_anomalie_sans_equipement_ne_se_convertit_pas(self):
        anomalie = Anomalie.objects.create(titre="Odeur suspecte", ship=self.navire, service=self.nav, sector=self.secteur, created_by=self.declarant)
        self._poster(self.chef_secteur, "anomalie-convertir", (anomalie.pk,))
        anomalie.refresh_from_db()
        self.assertIsNone(anomalie.ticket)
        self.assertEqual(CorrectiveTicket.objects.count(), 0)
