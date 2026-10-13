from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from taches.models import Tache


class SeedDemoTachesTests(TestCase):
    def test_jeu_de_donnees_idempotent_et_complet(self):
        for _ in range(2):
            call_command("seed_demo", stdout=StringIO())
        statuts = sorted(Tache.objects.values_list("statut", flat=True))
        self.assertEqual(statuts, [Tache.STATUT_A_FAIRE] * 3 + [Tache.STATUT_BLOQUEE, Tache.STATUT_TERMINEE])
        bloquee = Tache.objects.get(statut=Tache.STATUT_BLOQUEE)
        self.assertEqual(bloquee.participants.get().username, "chef_secteur_b")

    def test_demande_et_annonce_de_demo(self):
        from annonces.models import Annonce
        from demandes.models import Demande

        for _ in range(2):
            call_command("seed_demo", stdout=StringIO())
        demande = Demande.objects.get()
        self.assertEqual((demande.etat, demande.interlocuteurs.get().username), (Demande.ETAT_EN_TRAITEMENT, "chef_secteur_b"))
        annonce = Annonce.objects.get()
        self.assertTrue(annonce.accuse_requis)

    def test_planning_publie_unique_et_visible_au_calendrier(self):
        from datetime import timedelta

        from django.contrib.auth.models import User
        from django.utils import timezone

        from calendar_app.evenements_sources import _creneaux_quart_assignes
        from quarts.models import Quart

        for _ in range(2):
            call_command("seed_demo", stdout=StringIO())
        planning = Quart.objects.get(nom="Planning Propulsion — cette semaine")
        self.assertEqual((planning.statut, planning.service.name, planning.creneaux.count()), (Quart.STATUT_PUBLIEE, "Propulsion", 21))
        debut = timezone.localdate() - timedelta(days=timezone.localdate().weekday())
        for nom in ("equipier_a", "equipier_a2"):
            marin = User.objects.get(username=nom)
            self.assertTrue(_creneaux_quart_assignes(debut, debut + timedelta(days=6), user=marin).filter(quart=planning).exists())

    def test_fil_des_quatre_vues_selon_le_role(self):
        call_command("seed_demo", stdout=StringIO())
        self.client.login(username="chef_section_a", password="pass")
        page = self.client.get("/").content.decode()
        for libelle in ("Mon quotidien", "Mon équipe", "Suivi", "Synthèse"):
            self.assertIn(libelle, page)
        self.client.login(username="equipier_a", password="pass")
        page = self.client.get("/").content.decode()
        self.assertNotIn("Mon équipe", page)
        self.assertNotIn("Synthèse", page)
