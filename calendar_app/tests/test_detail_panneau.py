"""Panneau latéral de détail du calendrier : droits, commentaire, objet sans fil."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from absences.models import Absence, TypeAbsence
from org.models import Sector, Service, Ship
from programme import services as programme
from programme.models import EvenementProgramme
from quarts.models import CreneauQuart, Quart
from taches.models import Tache
from threads.models import Thread
from threads.utils import commentaires_de


class DetailPanneauTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="FREMM détail", code="FD", double_equipage=True, equipage_a_bord="A")
        service = Service.objects.create(ship=self.navire, name="Énergie")
        self.secteur = Sector.objects.create(service=service, name="Propulsion")
        autre = Sector.objects.create(service=service, name="Électricité")
        self.chef = self._marin("chef", self.secteur, "CHEF_SECTION", "A")
        self.marin = self._marin("marin", self.secteur, "EQUIPIER", "A")
        self.voisin = self._marin("voisin", autre, "EQUIPIER", "A")
        self.terre = self._marin("terre", self.secteur, "EQUIPIER", "B")
        self.etranger = self._marin("etranger", None, "EQUIPIER", "", navire=Ship.objects.create(name="Autre", code="AU"))
        self.aujourdhui = timezone.localdate()
        self.tache = Tache.objects.create(titre="Contrôler la pompe", echeance=self.aujourdhui, assigne=self.marin, created_by=self.chef)

    def _marin(self, nom, secteur, role, equipage, navire=None):
        user = User.objects.create_user(username=nom, password="pass")
        profil = user.profile
        profil.role, profil.sector, profil.equipage, profil.ship = role, secteur, equipage, navire or self.navire
        if secteur:
            profil.service = secteur.service
        profil.save()
        return user

    def detail(self, nom, type_evenement, pk):
        self.client.login(username=nom, password="pass")
        return self.client.get(reverse("calendar-detail", args=[type_evenement, pk]), HTTP_HX_REQUEST="true")

    def commenter(self, nom, type_evenement, pk, corps="Bien reçu"):
        self.client.login(username=nom, password="pass")
        return self.client.post(reverse("calendar-detail-commentaire", args=[type_evenement, pk]), {"body": corps}, HTTP_HX_REQUEST="true")

    def _creneau(self, marin):
        quart = Quart.objects.create(sector=self.secteur, date_debut=self.aujourdhui, date_fin=self.aujourdhui, statut=Quart.STATUT_PUBLIEE)
        debut = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0)
        return CreneauQuart.objects.create(quart=quart, poste="Barre", debut=debut, fin=debut + timedelta(hours=4), marin=marin)

    # --- Tâches -----------------------------------------------------------

    def test_tache_affiche_responsable_fil_et_fiche(self):
        reponse = self.detail("marin", "tache", self.tache.pk)
        self.assertContains(reponse, "Contrôler la pompe")
        self.assertContains(reponse, "Responsable")
        self.assertContains(reponse, "Ouvrir la fiche complète")
        self.assertContains(reponse, reverse("calendar-detail-commentaire", args=["tache", self.tache.pk]))

    def test_tache_hors_perimetre_introuvable(self):
        for nom in ("voisin", "etranger"):
            self.assertEqual(self.detail(nom, "tache", self.tache.pk).status_code, 404)
            self.assertEqual(self.commenter(nom, "tache", self.tache.pk).status_code, 404)
        self.assertFalse(commentaires_de(self.tache).exists())

    def test_chef_voit_l_avancement_de_l_equipe(self):
        self.assertContains(self.detail("chef", "tache", self.tache.pk), "Avancement de l'équipe")
        self.assertNotContains(self.detail("marin", "tache", self.tache.pk), "Avancement de l'équipe")

    def test_commentaire_visible_dans_la_fiche_de_la_tache(self):
        reponse = self.commenter("marin", "tache", self.tache.pk, "Pompe contrôlée")
        self.assertContains(reponse, "Pompe contrôlée")
        self.client.login(username="chef", password="pass")
        self.assertContains(self.client.get(reverse("tache-detail", args=[self.tache.pk])), "Pompe contrôlée")

    def test_commentaire_vide_refuse(self):
        reponse = self.commenter("marin", "tache", self.tache.pk, "   ")
        self.assertContains(reponse, "ne peut pas être vide")
        self.assertFalse(commentaires_de(self.tache).exists())

    def test_demarrer_reserve_au_marin_assigne(self):
        self.client.login(username="chef", password="pass")
        self.client.post(reverse("calendar-detail-demarrer", args=[self.tache.pk]))
        self.tache.refresh_from_db()
        self.assertEqual(self.tache.statut, Tache.STATUT_A_FAIRE)
        self.client.login(username="marin", password="pass")
        self.client.post(reverse("calendar-detail-demarrer", args=[self.tache.pk]))
        self.tache.refresh_from_db()
        self.assertEqual(self.tache.statut, Tache.STATUT_EN_COURS)

    def test_equipage_a_terre_en_lecture_seule(self):
        # Le marin d'équipage à terre voit le détail mais sans formulaire, et l'écriture est refusée.
        tache = Tache.objects.create(titre="À terre", assigne=self.terre, created_by=self.terre)
        self.assertNotContains(self.detail("terre", "tache", tache.pk), "<textarea")
        self.assertEqual(self.commenter("terre", "tache", tache.pk).status_code, 403)

    # --- Objets sans fil (créé à la première réponse) ---------------------

    def test_creneau_sans_fil_cree_a_la_premiere_reponse(self):
        creneau = self._creneau(self.marin)
        self.assertContains(self.detail("marin", "quart", creneau.pk), "Aucun commentaire")
        self.assertFalse(Thread.objects.exists())
        self.assertContains(self.commenter("marin", "quart", creneau.pk, "Relève faite"), "Relève faite")
        self.assertEqual(Thread.objects.count(), 1)
        self.assertEqual(commentaires_de(creneau).get().body, "Relève faite")

    def test_creneau_reserve_au_marin_et_a_son_chef(self):
        creneau = self._creneau(self.marin)
        self.assertEqual(self.detail("chef", "quart", creneau.pk).status_code, 200)
        for nom in ("voisin", "etranger"):
            self.assertEqual(self.detail(nom, "quart", creneau.pk).status_code, 404)
            self.assertEqual(self.commenter(nom, "quart", creneau.pk).status_code, 404)

    def test_evenement_programme_visible_seulement_du_public_vise(self):
        type_id = programme.types_du_navire(self.navire.pk).first().pk
        second = self._marin("second", None, "COMMANDANT_EN_SECOND", "A")
        evt = programme.creer_evenement(second, "Escale", type_id, timezone.now() + timedelta(days=1), None, f"ship:{self.navire.pk}")
        self.assertContains(self.detail("marin", "programme", evt.pk), "Escale")
        self.assertEqual(self.detail("etranger", "programme", evt.pk).status_code, 404)
        self.assertContains(self.commenter("marin", "programme", evt.pk, "Compris"), "Compris")
        self.assertEqual(self.commenter("etranger", "programme", evt.pk).status_code, 404)
        self.assertEqual(EvenementProgramme.objects.count(), 1)

    # --- Détail seul : absences, inconnus ---------------------------------

    def test_absence_detail_sans_fil(self):
        type_absence = TypeAbsence.objects.create(name="Permission")
        absence = Absence.objects.create(marin=self.marin, type_absence=type_absence, date_debut=self.aujourdhui, date_fin=self.aujourdhui)
        reponse = self.detail("marin", "absence", absence.pk)
        self.assertContains(reponse, "Permission")
        self.assertNotContains(reponse, "<textarea")
        self.assertEqual(self.commenter("marin", "absence", absence.pk).status_code, 404)
        self.assertEqual(self.detail("voisin", "absence", absence.pk).status_code, 404)

    def test_type_inconnu_et_anonyme(self):
        self.assertEqual(self.detail("marin", "ronde", 1).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("calendar-detail", args=["tache", self.tache.pk])).status_code, 302)
