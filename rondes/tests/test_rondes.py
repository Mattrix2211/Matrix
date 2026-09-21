from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, UserProfile
from assets.models import Installation
from calendar_app.views import evenements_utilisateur_jour
from logistics.models import Anomalie
from notifications.models import Notification
from org.models import Section, Sector, Service, Ship
from rondes import services
from rondes.models import PointControle, Ronde, RondeModele


class BaseRondes(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NA")
        self.service = Service.objects.create(ship=self.ship, name="Service A")
        self.sector = Sector.objects.create(service=self.service, name="Secteur A")
        self.section = Section.objects.create(sector=self.sector, name="Section A")
        self.autre_sector = Sector.objects.create(service=self.service, name="Secteur B")
        self.autre_ship = Ship.objects.create(name="Navire B", code="NB")
        self.installation = Installation.objects.create(
            designation="Pompe", ship=self.ship, service=self.service, sector=self.sector,
        )
        self.marin = self._user("marin", "EQUIPIER", section=self.section)
        self.chef_secteur = self._user("chef", "CHEF_SECTEUR", sector=self.sector)
        self.chef_service = self._user("chefsvc", "CHEF_SERVICE", service=self.service)
        self.autre_marin = self._user("autre", "EQUIPIER", ship=self.autre_ship)
        self.modele = RondeModele(nom="Ronde coursives", created_by=self.chef_secteur)
        self.modele.rattacher(sector=self.sector)
        self.modele.save()
        self.p1 = PointControle.objects.create(modele=self.modele, ordre=1, libelle="État de la coursive")
        self.p2 = PointControle.objects.create(
            modele=self.modele, ordre=2, libelle="Pompe", installation=self.installation,
            avec_mesure=True, unite_mesure="bar",
        )

    def _user(self, nom, role, **perimetre):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, **perimetre})
        return User.objects.get(pk=user.pk)

    def _connecter(self, user):
        self.client.login(username=user.username, password="pass")


class ServicesTests(BaseRondes):
    def test_creation_copie_les_points_et_ne_suit_pas_le_modele(self):
        ronde = services.creer_ronde(self.modele)
        self.assertEqual(ronde.resultats.count(), 2)
        self.p1.libelle = "Modifié"
        self.p1.save()
        self.p2.delete()
        self.assertEqual(
            list(ronde.resultats.values_list("libelle", flat=True)), ["État de la coursive", "Pompe"]
        )
        self.assertEqual(ronde.resultats.get(ordre=2).equipement_libelle, "Pompe")

    def test_modele_sans_point_refuse(self):
        vide = RondeModele(nom="Vide")
        vide.rattacher(sector=self.sector)
        vide.save()
        with self.assertRaises(services.RondeImpossible):
            services.creer_ronde(vide)

    def test_non_conforme_sans_equipement_cree_anomalie_du_secteur(self):
        ronde = services.creer_ronde(self.modele)
        res = ronde.resultats.get(ordre=1)
        anomalie = services.enregistrer_resultat(res, self.marin, "NON_CONFORME", commentaire="Flaque d'eau")
        self.assertEqual(anomalie.sector, self.sector)
        self.assertEqual(anomalie.service, self.service)
        self.assertIsNone(anomalie.equipement_lie)
        res.refresh_from_db()
        self.assertEqual(res.anomalie, anomalie)
        ronde.refresh_from_db()
        self.assertEqual(ronde.statut, Ronde.EN_COURS)
        self.assertTrue(Notification.objects.filter(user=self.chef_secteur).exists())

    def test_non_conforme_avec_equipement_rattache_a_l_equipement(self):
        ronde = services.creer_ronde(self.modele)
        res = ronde.resultats.get(ordre=2)
        anomalie = services.enregistrer_resultat(res, self.marin, "NON_CONFORME", mesure="3,5", commentaire="Fuite")
        self.assertEqual(anomalie.installation, self.installation)
        res.refresh_from_db()
        self.assertEqual(str(res.mesure), "3.500")

    def test_pas_de_doublon_anomalie_entre_deux_rondes(self):
        for _ in range(2):
            ronde = services.creer_ronde(self.modele)
            services.enregistrer_resultat(ronde.resultats.get(ordre=2), self.marin, "NON_CONFORME", commentaire="Fuite")
            ronde.statut = Ronde.TERMINEE
            ronde.save()
        self.assertEqual(Anomalie.objects.count(), 1)
        self.assertEqual(Anomalie.objects.get().points_ronde.count(), 2)

    def test_pas_de_doublon_sans_equipement(self):
        for _ in range(2):
            ronde = services.creer_ronde(self.modele)
            services.enregistrer_resultat(ronde.resultats.get(ordre=1), self.marin, "NON_CONFORME", commentaire="Flaque")
            ronde.statut = Ronde.TERMINEE
            ronde.save()
        self.assertEqual(Anomalie.objects.count(), 1)

    def test_recorriger_une_reponse_ne_recree_pas_d_anomalie(self):
        ronde = services.creer_ronde(self.modele)
        res = ronde.resultats.get(ordre=1)
        services.enregistrer_resultat(res, self.marin, "NON_CONFORME", commentaire="Flaque")
        services.enregistrer_resultat(res, self.marin, "NON_CONFORME", commentaire="Flaque grande")
        self.assertEqual(Anomalie.objects.count(), 1)

    def test_erreurs_de_saisie(self):
        ronde = services.creer_ronde(self.modele)
        res = ronde.resultats.get(ordre=2)
        for valeur, mesure, commentaire in (("NON_CONFORME", "", ""), ("BOF", "", ""), ("CONFORME", "abc", "")):
            with self.assertRaises(services.RondeImpossible):
                services.enregistrer_resultat(res, self.marin, valeur, mesure, commentaire)
        self.assertEqual(Anomalie.objects.count(), 0)

    def test_terminer_exige_tous_les_points_puis_fige(self):
        ronde = services.creer_ronde(self.modele)
        services.enregistrer_resultat(ronde.resultats.get(ordre=1), self.marin, "CONFORME")
        with self.assertRaises(services.RondeImpossible):
            services.terminer_ronde(ronde, self.marin)
        services.enregistrer_resultat(ronde.resultats.get(ordre=2), self.marin, "CONFORME", mesure="4")
        self.assertEqual(services.terminer_ronde(ronde, self.marin), 0)
        ronde.refresh_from_db()
        self.assertEqual((ronde.statut, ronde.realisee_par), (Ronde.TERMINEE, self.marin))
        with self.assertRaises(services.RondeImpossible):
            services.enregistrer_resultat(ronde.resultats.get(ordre=1), self.marin, "NON_CONFORME", commentaire="x")
        self.assertTrue(AuditLog.objects.filter(action="terminer_ronde").exists())

    def test_generation_periodique_sans_doublon(self):
        aujourdhui = timezone.localdate()
        self.modele.periodicite_jours = 3
        self.modele.save()
        self.assertEqual(services.generer_rondes(aujourdhui), 1)
        self.assertEqual(services.generer_rondes(aujourdhui), 0)
        Ronde.objects.update(statut=Ronde.TERMINEE)
        self.assertEqual(services.generer_rondes(aujourdhui + timedelta(days=2)), 0)
        self.assertEqual(services.generer_rondes(aujourdhui + timedelta(days=3)), 1)

    def test_retard_marque_et_notifie_une_seule_fois(self):
        ronde = services.creer_ronde(self.modele, date_prevue=timezone.localdate() - timedelta(days=1), assigne_a=self.marin)
        self.assertEqual(services.marquer_rondes_en_retard(), 1)
        self.assertEqual(services.marquer_rondes_en_retard(), 0)
        ronde.refresh_from_db()
        self.assertEqual(ronde.statut, Ronde.EN_RETARD)
        self.assertEqual(Notification.objects.filter(user=self.marin, verb__startswith="Ronde en retard").count(), 1)

    def test_visibilite_par_perimetre(self):
        ronde = services.creer_ronde(self.modele)
        for user, attendu in (
            (self.marin, True), (self.chef_secteur, True), (self.chef_service, True), (self.autre_marin, False),
        ):
            self.assertEqual(services.rondes_visibles(user).filter(pk=ronde.pk).exists(), attendu, user.username)
        autre = RondeModele(nom="Autre secteur")
        autre.rattacher(sector=self.autre_sector)
        autre.save()
        PointControle.objects.create(modele=autre, libelle="x")
        ronde_autre = services.creer_ronde(autre)
        self.assertFalse(services.rondes_visibles(self.marin).filter(pk=ronde_autre.pk).exists())
        self.assertTrue(services.rondes_visibles(self.chef_service).filter(pk=ronde_autre.pk).exists())

    def test_calendrier_du_jour_contient_la_ronde(self):
        services.creer_ronde(self.modele)
        self.assertEqual(len(evenements_utilisateur_jour(self.marin, timezone.localdate())["rondes"]), 1)
        self.assertEqual(len(evenements_utilisateur_jour(self.autre_marin, timezone.localdate())["rondes"]), 0)


class VuesTests(BaseRondes):
    def test_equipier_ne_peut_pas_creer_de_modele(self):
        self._connecter(self.marin)
        self.assertEqual(self.client.get(reverse("ronde-modele-nouveau")).status_code, 403)
        reponse = self.client.post(reverse("ronde-modele-nouveau"), {"nom": "X", "perimetre": f"sector:{self.sector.pk}"})
        self.assertEqual(reponse.status_code, 403)

    def test_chef_cree_modele_et_points_versionnes(self):
        self._connecter(self.chef_secteur)
        reponse = self.client.post(reverse("ronde-modele-nouveau"), {
            "nom": "Ronde machines", "periodicite_jours": "2", "perimetre": f"sector:{self.sector.pk}", "actif": "on",
        })
        modele = RondeModele.objects.get(nom="Ronde machines")
        self.assertRedirects(reponse, reverse("ronde-modele", args=[modele.pk]))
        self.assertEqual((modele.sector, modele.ship, modele.periodicite_jours), (self.sector, self.ship, 2))
        self.client.post(reverse("ronde-point-ajouter", args=[modele.pk, "ajouter"]), {
            "libelle": "Niveau d'huile", "equipement": f"installation:{self.installation.pk}", "gravite": "4",
        })
        modele.refresh_from_db()
        point = modele.points.get()
        self.assertEqual((point.installation, point.gravite, modele.version), (self.installation, 4, 2))
        self.client.post(reverse("ronde-point", args=[modele.pk, point.pk, "supprimer"]))
        self.assertFalse(modele.points.exists())
        self.assertTrue(AuditLog.objects.filter(action="save_ronde_modele").exists())

    def test_perimetre_hors_zone_refuse(self):
        self._connecter(self.chef_secteur)
        reponse = self.client.post(reverse("ronde-modele-nouveau"), {
            "nom": "Hors zone", "perimetre": f"sector:{self.autre_sector.pk}",
        })
        self.assertEqual(reponse.status_code, 400)
        self.assertFalse(RondeModele.objects.filter(nom="Hors zone").exists())

    def test_equipement_d_un_autre_navire_refuse(self):
        service = Service.objects.create(ship=self.autre_ship, name="Service B")
        secteur = Sector.objects.create(service=service, name="Secteur Z")
        etranger = Installation.objects.create(designation="Étrangère", ship=self.autre_ship, service=service, sector=secteur)
        self._connecter(self.chef_secteur)
        self.client.post(reverse("ronde-point-ajouter", args=[self.modele.pk, "ajouter"]), {
            "libelle": "Piège", "equipement": f"installation:{etranger.pk}",
        })
        self.assertFalse(self.modele.points.filter(libelle="Piège").exists())

    def test_hors_perimetre_404(self):
        self._connecter(self.autre_marin)
        ronde = services.creer_ronde(self.modele)
        self.assertEqual(self.client.get(reverse("ronde-detail", args=[ronde.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("ronde-resultat", args=[ronde.pk, ronde.resultats.first().pk])).status_code, 404)

    def test_parcours_htmx_et_fin(self):
        self._connecter(self.marin)
        self.client.post(reverse("ronde-lancer", args=[self.modele.pk]))
        ronde = Ronde.objects.get()
        # Lancer deux fois reprend la même ronde
        self.client.post(reverse("ronde-lancer", args=[self.modele.pk]))
        self.assertEqual(Ronde.objects.count(), 1)
        page = self.client.get(reverse("ronde-detail", args=[ronde.pk]))
        self.assertContains(page, "État de la coursive")
        r1, r2 = ronde.resultats.all()
        erreur = self.client.post(reverse("ronde-resultat", args=[ronde.pk, r1.pk]), {"resultat": "NON_CONFORME"}, HTTP_HX_REQUEST="true")
        self.assertContains(erreur, "commentaire obligatoire")
        ok = self.client.post(reverse("ronde-resultat", args=[ronde.pk, r1.pk]), {"resultat": "NON_CONFORME", "commentaire": "Flaque"}, HTTP_HX_REQUEST="true")
        self.assertContains(ok, "Anomalie transmise")
        self.assertContains(ok, "hx-swap-oob")
        self.client.post(reverse("ronde-terminer", args=[ronde.pk]))
        ronde.refresh_from_db()
        self.assertTrue(ronde.est_ouverte)
        self.client.post(reverse("ronde-resultat", args=[ronde.pk, r2.pk]), {"resultat": "CONFORME", "mesure": "5"})
        self.client.post(reverse("ronde-terminer", args=[ronde.pk]))
        ronde.refresh_from_db()
        self.assertEqual(ronde.statut, Ronde.TERMINEE)
        historique = self.client.get(reverse("ronde-detail", args=[ronde.pk]))
        self.assertContains(historique, "Flaque")
        self.assertNotContains(historique, "Terminer la ronde")

    def test_index_et_dashboard(self):
        services.creer_ronde(self.modele)
        self._connecter(self.marin)
        self.assertContains(self.client.get(reverse("rondes-index")), "Ronde coursives")
        self.assertContains(self.client.get("/"), "Mes rondes du jour")
        self.assertContains(self.client.get(reverse("ronde-modeles")), "Ronde coursives")


class PerimetreGerableTests(BaseRondes):
    def setUp(self):
        super().setUp()
        self.chef_section = self._user("chefsec", "CHEF_SECTION", section=self.section)
        self.modele_navire = RondeModele(nom="Ronde unité")
        self.modele_navire.rattacher(ship=self.ship)
        self.modele_navire.save()
        self.modele_service = RondeModele(nom="Ronde service")
        self.modele_service.rattacher(service=self.service)
        self.modele_service.save()
        self.point_navire = PointControle.objects.create(modele=self.modele_navire, libelle="P")

    def test_chef_section_ne_modifie_pas_un_modele_navire_ou_service(self):
        self._connecter(self.chef_section)
        for modele in (self.modele_navire, self.modele_service):
            self.assertEqual(self.client.post(reverse("ronde-modele", args=[modele.pk]), {"nom": "Piraté"}).status_code, 404)
            self.assertEqual(self.client.post(reverse("ronde-point-ajouter", args=[modele.pk, "ajouter"]), {"libelle": "X"}).status_code, 404)
        for action in ("supprimer", "monter", "descendre"):
            self.assertEqual(self.client.post(reverse("ronde-point", args=[self.modele_navire.pk, self.point_navire.pk, action])).status_code, 404)
        self.assertTrue(self.modele_navire.points.filter(pk=self.point_navire.pk).exists())
        self.modele_navire.refresh_from_db()
        self.assertEqual(self.modele_navire.nom, "Ronde unité")
        # Lecture seule : aucun formulaire d'édition affiché.
        self.assertNotContains(self.client.get(reverse("ronde-modele", args=[self.modele_navire.pk])), "Ajouter le point")

    def test_chef_section_modifie_un_modele_de_son_secteur(self):
        self._connecter(self.chef_section)
        reponse = self.client.post(reverse("ronde-point-ajouter", args=[self.modele.pk, "ajouter"]), {"libelle": "Nouveau"})
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(self.modele.points.filter(libelle="Nouveau").exists())
        self.assertContains(self.client.get(reverse("ronde-modele", args=[self.modele.pk])), "Ajouter le point")

    def test_chef_service_et_etat_major_gardent_leurs_niveaux(self):
        self.assertTrue(services.modeles_gerables(self.chef_service).filter(pk=self.modele_service.pk).exists())
        self.assertFalse(services.modeles_gerables(self.chef_service).filter(pk=self.modele_navire.pk).exists())
        etat_major = self._user("em", "ETAT_MAJOR", ship=self.ship)
        self.assertTrue(services.modeles_gerables(etat_major).filter(pk=self.modele_navire.pk).exists())
