"""Traçabilité des créneaux ajoutés/supprimés sur une liste publiée
(AuditLog + notification du marin) ; rien pour un brouillon."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, FonctionQuartChoice, ServiceFunctionChoice, UserProfile
from notifications.models import Notification
from org.models import Sector, Section, Service, Ship
from quarts.models import ChefDeListe, CreneauQuart, CreneauServiceGarde, Quart, ServiceGarde


class TraceCreneauxTests(TestCase):
    def setUp(self):
        ship = Ship.objects.create(name="Navire Trace", code="TRC")
        self.sector = Sector.objects.create(service=Service.objects.create(ship=ship, name="Pont"), name="Manœuvre")
        section = Section.objects.create(sector=self.sector, name="Plage avant")
        self.cdl = User.objects.create_user(username="cdl_trace", password="pass")
        UserProfile.objects.update_or_create(user=self.cdl, defaults={"role": "EQUIPIER", "section": section})
        ChefDeListe.objects.create(user=self.cdl, sector=self.sector)
        self.marin = User.objects.create_user(username="marin_trace", password="pass", first_name="Jean", last_name="Dupont")
        UserProfile.objects.update_or_create(user=self.marin, defaults={"role": "EQUIPIER", "section": section})
        self.client.login(username="cdl_trace", password="pass")
        debut = timezone.localdate()
        fin = debut + timedelta(days=6)
        self.quart = Quart.objects.create(
            sector=self.sector, date_debut=debut, date_fin=fin,
            fonction=FonctionQuartChoice.objects.create(name="Barre"),
        )
        self.garde = ServiceGarde.objects.create(
            sector=self.sector, date_debut=debut, date_fin=fin,
            fonction=ServiceFunctionChoice.objects.create(name="Permanence"),
        )

    def _liste(self, type_liste, statut):
        liste = self.quart if type_liste == "quart" else self.garde
        liste.statut = statut
        liste.save(update_fields=["statut"])
        return liste

    def _ajouter(self, type_liste, liste, marin=None, note=""):
        donnees = {
            "action": "ajouter_creneau", "poste": "Passerelle", "note": note,
            "debut": (timezone.now() + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M"),
        }
        if marin:
            donnees["marin"] = marin.pk
        return self.client.post(reverse(f"{'quart' if type_liste == 'quart' else 'garde'}-detail", args=[liste.pk]), donnees)

    def _supprimer(self, type_liste, liste, creneau):
        return self.client.post(
            reverse(f"{'quart' if type_liste == 'quart' else 'garde'}-detail", args=[liste.pk]),
            {"action": "supprimer_creneau", "creneau_id": creneau.pk},
        )

    def test_ajout_sur_liste_publiee_trace_et_notifie(self):
        for type_liste in ("quart", "garde"):
            with self.subTest(type_liste):
                liste = self._liste(type_liste, Quart.STATUT_PUBLIEE)
                self._ajouter(type_liste, liste, self.marin, note="Relève")
                journal = AuditLog.objects.get(action="liste_service_creneau_ajoute", details__startswith=f"{liste.libelle_type()} #{liste.pk} ")
                self.assertIn("Passerelle", journal.details)
                self.assertIn("Jean Dupont", journal.details)
                self.assertIn("Relève", journal.details)
                notif = Notification.objects.filter(user=self.marin, verb__contains="affecté(e)").latest("pk")
                self.assertIn("Modification de la liste publiée", notif.verb)

    def test_ajout_sur_brouillon_ne_trace_rien(self):
        for type_liste in ("quart", "garde"):
            with self.subTest(type_liste):
                liste = self._liste(type_liste, Quart.STATUT_BROUILLON)
                self._ajouter(type_liste, liste, self.marin)
        self.assertFalse(AuditLog.objects.filter(action__startswith="liste_service_creneau").exists())
        self.assertFalse(Notification.objects.filter(user=self.marin).exists())

    def test_suppression_conserve_les_details_et_notifie(self):
        for type_liste, modele, attr in (("quart", CreneauQuart, "quart"), ("garde", CreneauServiceGarde, "service_garde")):
            with self.subTest(type_liste):
                liste = self._liste(type_liste, Quart.STATUT_PUBLIEE)
                debut = timezone.now() + timedelta(hours=5)
                creneau = modele.objects.create(
                    poste="Veille", debut=debut, fin=debut + timedelta(hours=4), marin=self.marin, **{attr: liste},
                )
                self._supprimer(type_liste, liste, creneau)
                self.assertFalse(modele.objects.filter(pk=creneau.pk).exists())
                journal = AuditLog.objects.get(action="liste_service_creneau_supprime", details__startswith=f"{liste.libelle_type()} #{liste.pk} ")
                self.assertIn("Veille", journal.details)
                self.assertIn("Jean Dupont", journal.details)
                self.assertTrue(Notification.objects.filter(user=self.marin, verb__contains="retiré(e)").exists())

    def test_creneau_sans_marin_trace_sans_notification(self):
        liste = self._liste("quart", Quart.STATUT_PUBLIEE)
        self._ajouter("quart", liste)
        journal = AuditLog.objects.get(action="liste_service_creneau_ajoute")
        self.assertIn("non affecté", journal.details)
        self.assertFalse(Notification.objects.exists())

    def test_pas_de_notification_a_soi_meme(self):
        liste = self._liste("quart", Quart.STATUT_PUBLIEE)
        self._ajouter("quart", liste, self.cdl)
        self.assertTrue(AuditLog.objects.filter(action="liste_service_creneau_ajoute").exists())
        self.assertFalse(Notification.objects.filter(user=self.cdl).exists())

    def test_reglage_des_echanges_sur_liste_publiee_est_trace(self):
        liste = self._liste("garde", ServiceGarde.STATUT_PUBLIEE)
        self.client.post(reverse("garde-detail", args=[liste.pk]), {"action": "regler_echanges", "delai_minimal_echange_heures": 12})
        self.assertTrue(AuditLog.objects.filter(action="liste_service_echanges_regles").exists())
        liste = self._liste("garde", ServiceGarde.STATUT_BROUILLON)
        AuditLog.objects.all().delete()
        self.client.post(reverse("garde-detail", args=[liste.pk]), {"action": "regler_echanges", "delai_minimal_echange_heures": 6})
        self.assertFalse(AuditLog.objects.filter(action="liste_service_echanges_regles").exists())


class TraceCreneauxAdminTests(TestCase):
    def test_admin_trace_ajout_et_suppression_sur_liste_publiee(self):
        from django.contrib.admin.sites import site
        from unittest.mock import MagicMock

        ship = Ship.objects.create(name="Navire Admin", code="ADM")
        admin_user = User.objects.create_superuser("admin_trace", password="pass")
        quart = Quart.objects.create(
            ship=ship, date_debut=timezone.localdate(), date_fin=timezone.localdate(), statut=Quart.STATUT_PUBLIEE,
            fonction=FonctionQuartChoice.objects.create(name="Veille"),
        )
        debut = timezone.now() + timedelta(hours=2)
        existant = CreneauQuart.objects.create(quart=quart, poste="Ancien", debut=debut, fin=debut + timedelta(hours=4))
        nouveau = CreneauQuart(quart=quart, poste="Nouveau", debut=debut, fin=debut + timedelta(hours=4))
        formset = MagicMock(model=CreneauQuart, deleted_objects=[existant])
        formset.save.return_value = [nouveau]
        form = MagicMock(instance=quart)
        request = MagicMock(user=admin_user)
        site._registry[Quart].save_formset(request, form, formset, True)
        self.assertTrue(AuditLog.objects.filter(action="liste_service_creneau_supprime", details__contains="Ancien").exists())
        self.assertTrue(AuditLog.objects.filter(action="liste_service_creneau_ajoute", details__contains="Nouveau").exists())
        self.assertFalse(CreneauQuart.objects.filter(pk=existant.pk).exists())
        self.assertTrue(CreneauQuart.objects.filter(poste="Nouveau").exists())
