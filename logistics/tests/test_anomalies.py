import io

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image as PILImage

from accounts.models import AuditLog, UserProfile
from assets.models import Asset, AssetType, Installation
from logistics.models import Anomalie, AnomalieStatutLog, CorrectiveTicket
from notifications.models import Notification
from org.models import Section, Sector, Service, Ship


def _png_1x1():
    # PNG 1x1 généré à la volée par Pillow : doit décoder réellement
    # (Image.open().verify()), même fixture que test_plan_navire_web.py.
    tampon = io.BytesIO()
    PILImage.new("RGB", (1, 1), color=(128, 128, 128)).save(tampon, format="PNG")
    return tampon.getvalue()


@override_settings(MEDIA_ROOT="/tmp/matrix_tests_media")
class AnomalieTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NA")
        self.service = Service.objects.create(ship=self.ship, name="Service A")
        self.sector = Sector.objects.create(service=self.service, name="Secteur A")
        self.section = Section.objects.create(sector=self.sector, name="Section A")
        self.autre_sector = Sector.objects.create(service=self.service, name="Secteur B")
        self.autre_section = Section.objects.create(sector=self.autre_sector, name="Section B")
        type_actif = AssetType.objects.create(name="T", category="C", sector=self.sector)
        self.asset = Asset.objects.create(
            asset_type=type_actif, ship=self.ship, service=self.service, sector=self.sector, section=self.section,
        )
        self.installation = Installation.objects.create(
            designation="Pompe", ship=self.ship, service=self.service, sector=self.sector,
        )
        self.autre_ship = Ship.objects.create(name="Navire B", code="NB")
        autre_service = Service.objects.create(ship=self.autre_ship, name="Service Z")
        autre_secteur = Sector.objects.create(service=autre_service, name="Secteur Z")
        self.asset_etranger = Asset.objects.create(
            asset_type=AssetType.objects.create(name="TZ", category="C", sector=autre_secteur),
            ship=self.autre_ship, service=autre_service, sector=autre_secteur,
        )

        self.marin = self._user("marin", "EQUIPIER", section=self.section)
        self.marin2 = self._user("marin2", "EQUIPIER", section=self.section)
        self.chef_section = self._user("chef_section", "CHEF_SECTION", section=self.section)
        self.chef_secteur = self._user("chef_secteur", "CHEF_SECTEUR", sector=self.sector)
        self.chef_autre_section = self._user("chef_autre", "CHEF_SECTION", section=self.autre_section)
        self.chef_autre_navire = self._user("chef_etranger", "CHEF_SERVICE", ship=self.autre_ship)

    def _user(self, nom, role, **perimetre):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, **perimetre})
        # Recharge l'utilisateur : le profil créé par signal reste en cache sur l'instance.
        return User.objects.get(pk=user.pk)

    def _signaler(self, user, **donnees):
        self.client.login(username=user.username, password="pass")
        donnees.setdefault("titre", "Fuite en coursive")
        return self.client.post(reverse("anomalie-create"), donnees)

    def test_signalement_minimal_sans_equipement(self):
        reponse = self._signaler(self.marin, titre="Obstacle sur issue de secours")
        anomalie = Anomalie.objects.get()
        self.assertRedirects(reponse, reverse("anomalie-detail", args=[anomalie.pk]))
        self.assertEqual(anomalie.statut, "SIGNALEE")
        self.assertEqual(anomalie.created_by, self.marin)
        self.assertEqual((anomalie.section, anomalie.sector, anomalie.service, anomalie.ship),
                         (self.section, self.sector, self.service, self.ship))
        self.assertIsNone(anomalie.installation)
        self.assertEqual(AnomalieStatutLog.objects.filter(anomalie=anomalie).count(), 1)
        self.assertTrue(AuditLog.objects.filter(action="create_anomalie", actor=self.marin).exists())

    def test_titre_obligatoire(self):
        reponse = self._signaler(self.marin, titre="  ")
        self.assertEqual(reponse.status_code, 400)
        self.assertFalse(Anomalie.objects.exists())

    def test_photo_et_localisation_enregistrees(self):
        # Depuis la validation serveur des fichiers téléversés (tâche [SEC]),
        # un contenu factice comme b"\x89PNG\r\n" est refusé par Pillow
        # (Image.open().verify()) : il faut un vrai PNG décodable.
        photo = SimpleUploadedFile("p.png", _png_1x1(), content_type="image/png")
        self._signaler(self.marin, localisation="Coursive bâbord", photo=photo)
        anomalie = Anomalie.objects.get()
        self.assertEqual(anomalie.localisation, "Coursive bâbord")
        self.assertTrue(anomalie.photo)

    def test_equipement_herite_du_perimetre_de_l_equipement(self):
        self._signaler(self.marin, asset=str(self.asset.pk), gravite="4")
        anomalie = Anomalie.objects.get()
        self.assertEqual(anomalie.asset, self.asset)
        self.assertEqual(anomalie.gravite, 4)

    def test_equipement_hors_perimetre_refuse(self):
        reponse = self._signaler(self.marin, asset=str(self.asset_etranger.pk))
        self.assertEqual(reponse.status_code, 400)
        self.assertFalse(Anomalie.objects.exists())

    def test_installation_et_materiel_ensemble_refuses(self):
        reponse = self._signaler(self.marin, asset=str(self.asset.pk), installation=str(self.installation.pk))
        self.assertEqual(reponse.status_code, 400)

    def test_identifiant_equipement_invalide_refuse(self):
        reponse = self._signaler(self.marin, asset="n-importe-quoi")
        self.assertEqual(reponse.status_code, 400)

    def test_gravite_bornee(self):
        self._signaler(self.marin, gravite="99")
        self.assertEqual(Anomalie.objects.get().gravite, 5)

    def test_notifie_les_chefs_du_perimetre_uniquement(self):
        self._signaler(self.marin, gravite="4")
        self.assertTrue(Notification.objects.filter(user=self.chef_section, level="danger").exists())
        self.assertTrue(Notification.objects.filter(user=self.chef_secteur).exists())
        self.assertFalse(Notification.objects.filter(user=self.chef_autre_section).exists())
        self.assertFalse(Notification.objects.filter(user=self.chef_autre_navire).exists())
        self.assertFalse(Notification.objects.filter(user=self.marin).exists())

    def _creer(self, auteur=None, **kw):
        anomalie = Anomalie(titre="A", created_by=auteur or self.marin, **kw)
        anomalie.rattacher_a(self.marin.profile if auteur is None else auteur.profile)
        anomalie.save()
        return anomalie

    def test_visibilite_equipier_sa_section_seulement(self):
        mienne = self._creer(self.marin)
        collegue = self._creer(self.marin2)
        autre_section = self._creer(self._user("marin_b", "EQUIPIER", section=self.autre_section))
        self.client.login(username="marin", password="pass")
        self.assertEqual(self.client.get(reverse("anomalie-detail", args=[mienne.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("anomalie-detail", args=[collegue.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("anomalie-detail", args=[autre_section.pk])).status_code, 404)
        section = self.client.get(reverse("anomalie-list") + "?vue=perimetre")
        self.assertEqual(set(section.context["anomalies"]), {mienne, collegue})
        self.assertEqual(section.context["libelle_perimetre"], "Ma section")
        mes = self.client.get(reverse("anomalie-list"))
        self.assertEqual(list(mes.context["anomalies"]), [mienne])

    def test_equipier_voit_la_section_mais_ne_peut_pas_traiter(self):
        collegue = self._creer(self.marin2)
        self.client.login(username="marin", password="pass")
        self.assertEqual(
            self.client.post(reverse("anomalie-transition", args=[collegue.pk]), {"statut": "CLOTUREE"}).status_code, 403)
        self.assertNotContains(self.client.get(reverse("anomalie-detail", args=[collegue.pk])), "Mettre à jour")

    def test_equipier_sans_section_ne_voit_que_les_siennes(self):
        sans_section = self._user("marin_ship", "EQUIPIER", ship=self.ship)
        mienne = self._creer(sans_section)
        self._creer(self.marin)
        self.client.login(username="marin_ship", password="pass")
        liste = self.client.get(reverse("anomalie-list"))
        self.assertEqual(list(liste.context["anomalies"]), [mienne])
        self.assertFalse(liste.context["peut_voir_perimetre"])

    def test_visibilite_chefs_par_perimetre(self):
        anomalie = self._creer(self.marin)
        for chef, attendu in [
            (self.chef_section, 200), (self.chef_secteur, 200),
            (self.chef_autre_section, 404), (self.chef_autre_navire, 404),
        ]:
            self.client.login(username=chef.username, password="pass")
            self.assertEqual(
                self.client.get(reverse("anomalie-detail", args=[anomalie.pk])).status_code, attendu, chef.username,
            )
        self.client.login(username="chef_section", password="pass")
        liste = self.client.get(reverse("anomalie-list") + "?vue=perimetre")
        self.assertEqual(list(liste.context["anomalies"]), [anomalie])
        self.assertEqual(liste.context["total"], 1)

    def test_admin_sans_perimetre_voit_tout(self):
        anomalie = self._creer(self.marin)
        admin = self._user("admin_general", "MASTER_ADMIN")
        self.client.login(username=admin.username, password="pass")
        self.assertEqual(self.client.get(reverse("anomalie-detail", args=[anomalie.pk])).status_code, 200)

    def test_transition_par_chef_avec_historique_et_notification(self):
        anomalie = self._creer(self.marin)
        self.client.login(username="chef_section", password="pass")
        self.client.post(reverse("anomalie-transition", args=[anomalie.pk]), {"statut": "PRISE_EN_COMPTE", "note": "vu"})
        anomalie.refresh_from_db()
        self.assertEqual(anomalie.statut, "PRISE_EN_COMPTE")
        log = AnomalieStatutLog.objects.filter(anomalie=anomalie).last()
        self.assertEqual((log.ancien_statut, log.nouveau_statut, log.user, log.note),
                         ("SIGNALEE", "PRISE_EN_COMPTE", self.chef_section, "vu"))
        self.assertTrue(AuditLog.objects.filter(
            action="anomalie_status_change", details=f"anomalie={anomalie.pk}; SIGNALEE -> PRISE_EN_COMPTE").exists())
        self.assertTrue(Notification.objects.filter(user=self.marin, verb__contains="Prise en compte").exists())

    def test_transition_interdite_a_un_equipier_et_hors_perimetre(self):
        anomalie = self._creer(self.marin)
        self.client.login(username="marin", password="pass")
        self.assertEqual(
            self.client.post(reverse("anomalie-transition", args=[anomalie.pk]), {"statut": "CLOTUREE"}).status_code, 403)
        self.client.login(username="chef_autre", password="pass")
        self.assertEqual(
            self.client.post(reverse("anomalie-transition", args=[anomalie.pk]), {"statut": "CLOTUREE"}).status_code, 404)
        anomalie.refresh_from_db()
        self.assertEqual(anomalie.statut, "SIGNALEE")

    def test_transition_statut_invalide(self):
        anomalie = self._creer(self.marin)
        self.client.login(username="chef_section", password="pass")
        reponse = self.client.post(reverse("anomalie-transition", args=[anomalie.pk]), {"statut": "XXX"})
        self.assertEqual(reponse.status_code, 400)

    def test_conversion_en_ticket_lien_bidirectionnel(self):
        anomalie = self._creer(self.marin, asset=self.asset, gravite=4, description="Détail")
        self.client.login(username="chef_section", password="pass")
        reponse = self.client.post(reverse("anomalie-convertir", args=[anomalie.pk]))
        anomalie.refresh_from_db()
        ticket = CorrectiveTicket.objects.get()
        self.assertRedirects(reponse, reverse("ticket-detail", args=[ticket.pk]))
        self.assertEqual(anomalie.ticket, ticket)
        self.assertEqual(ticket.anomalie_source, anomalie)
        self.assertEqual((ticket.asset, ticket.severity), (self.asset, 4))
        self.assertEqual(anomalie.statut, "PRISE_EN_COMPTE")
        self.assertTrue(AuditLog.objects.filter(action="anomalie_convertie_ticket").exists())
        # Le ticket affiche le lien retour vers l'anomalie.
        self.assertContains(self.client.get(reverse("ticket-detail", args=[ticket.pk])), reverse("anomalie-detail", args=[anomalie.pk]))
        # Une seconde conversion ne recrée rien.
        self.client.post(reverse("anomalie-convertir", args=[anomalie.pk]))
        self.assertEqual(CorrectiveTicket.objects.count(), 1)

    def test_conversion_installation_en_ticket(self):
        anomalie = self._creer(self.marin, installation=self.installation, gravite=4)
        self.client.login(username="chef_secteur", password="pass")
        self.client.post(reverse("anomalie-convertir", args=[anomalie.pk]))
        ticket = CorrectiveTicket.objects.get()
        anomalie.refresh_from_db()
        self.assertEqual((ticket.installation, ticket.asset, anomalie.ticket), (self.installation, None, ticket))
        self.assertEqual(anomalie.statut, "PRISE_EN_COMPTE")

    def test_conversion_impossible_sans_equipement(self):
        anomalie = self._creer(self.marin)
        self.client.login(username="chef_section", password="pass")
        self.client.post(reverse("anomalie-convertir", args=[anomalie.pk]))
        self.assertFalse(CorrectiveTicket.objects.exists())

    def test_secteur_choisi_definit_le_perimetre_et_les_notifications(self):
        chef_autre_secteur = self._user("chef_secteur_b", "CHEF_SECTEUR", sector=self.autre_sector)
        self._signaler(self.marin, secteur=str(self.autre_sector.pk), gravite="4")
        anomalie = Anomalie.objects.get()
        self.assertEqual((anomalie.sector, anomalie.service, anomalie.ship, anomalie.section),
                         (self.autre_sector, self.service, self.ship, None))
        self.assertTrue(Notification.objects.filter(user=chef_autre_secteur).exists())
        self.assertFalse(Notification.objects.filter(user=self.chef_secteur).exists())
        self.assertFalse(Notification.objects.filter(user=self.chef_section).exists())
        # Visible du chef du secteur concerné, pas des chefs de l'ancien secteur du déclarant.
        self.client.login(username="chef_secteur_b", password="pass")
        self.assertEqual(self.client.get(reverse("anomalie-detail", args=[anomalie.pk])).status_code, 200)
        self.client.login(username="chef_section", password="pass")
        self.assertEqual(self.client.get(reverse("anomalie-detail", args=[anomalie.pk])).status_code, 404)

    def test_secteur_propre_conserve_la_section(self):
        self._signaler(self.marin, secteur=str(self.sector.pk))
        self.assertEqual(Anomalie.objects.get().section, self.section)

    def test_secteur_hors_navire_refuse(self):
        secteur_etranger = Sector.objects.create(
            service=Service.objects.create(ship=self.autre_ship, name="S"), name="Etranger",
        )
        reponse = self._signaler(self.marin, secteur=str(secteur_etranger.pk))
        self.assertEqual(reponse.status_code, 400)
        self.assertFalse(Anomalie.objects.exists())

    def test_formulaire_prerempli_avec_le_secteur_du_declarant(self):
        self.client.login(username="marin", password="pass")
        reponse = self.client.get(reverse("anomalie-create"))
        self.assertContains(reponse, f'value="{self.sector.pk}" selected')

    def test_equipement_prevaut_sur_le_secteur_choisi(self):
        self._signaler(self.marin, asset=str(self.asset.pk), secteur=str(self.autre_sector.pk))
        self.assertEqual(Anomalie.objects.get().sector, self.sector)

    def test_conversion_interdite_equipier_et_hors_perimetre(self):
        anomalie = self._creer(self.marin, asset=self.asset)
        self.client.login(username="marin", password="pass")
        self.assertEqual(self.client.post(reverse("anomalie-convertir", args=[anomalie.pk])).status_code, 403)
        self.client.login(username="chef_etranger", password="pass")
        self.assertEqual(self.client.post(reverse("anomalie-convertir", args=[anomalie.pk])).status_code, 404)
        self.assertFalse(CorrectiveTicket.objects.exists())

    def test_commentaire(self):
        anomalie = self._creer(self.marin)
        self.client.login(username="marin", password="pass")
        self.client.post(reverse("anomalie-comment", args=[anomalie.pk]), {"body": "Toujours là"})
        self.assertContains(self.client.get(reverse("anomalie-detail", args=[anomalie.pk])), "Toujours là")
        self._user("marin_b", "EQUIPIER", section=self.autre_section)
        self.client.login(username="marin_b", password="pass")
        self.assertEqual(
            self.client.post(reverse("anomalie-comment", args=[anomalie.pk]), {"body": "x"}).status_code, 404)

    def test_liste_compteurs_et_filtre_statut(self):
        self._creer(self.marin)
        deuxieme = self._creer(self.marin)
        deuxieme.statut = "TRAITEE"
        deuxieme.save()
        self.client.login(username="marin", password="pass")
        reponse = self.client.get(reverse("anomalie-list"))
        self.assertEqual({e["code"]: e["nombre"] for e in reponse.context["etapes"]},
                         {"SIGNALEE": 1, "PRISE_EN_COMPTE": 0, "TRAITEE": 1, "CLOTUREE": 0})
        filtre = self.client.get(reverse("anomalie-list") + "?statut=TRAITEE")
        self.assertEqual(list(filtre.context["anomalies"]), [deuxieme])

    def test_formulaire_prerempli_depuis_la_fiche_equipement(self):
        self.client.login(username="marin", password="pass")
        reponse = self.client.get(reverse("anomalie-create") + f"?asset={self.asset.pk}")
        self.assertContains(reponse, f'value="{self.asset.pk}" selected')

    def test_acces_anonyme_redirige(self):
        self.assertEqual(self.client.get(reverse("anomalie-list")).status_code, 302)
