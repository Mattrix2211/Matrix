"""Tests de la page « Prêt à appareillage » (dashboard/web_views.py) : session
de préparation à un appareillage datée et tracée — création, cochage des
items (ouvert à tout marin), signature (réservée à CHEF_SECTEUR+), immutabilité
après clôture, isolation par navire. Cf. tâche Notion « [FEAT] Tableau de bord
Prêt à appareillage »."""
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Installation, InstallationHourReading
from dashboard.models import ItemAppareillage, SessionAppareillage
from notifications.models import Notification
from org.models import Sector, Service, Ship


class PretAppareillageTestsBase(TestCase):
    """Fixtures communes : un navire avec une installation critique sans
    aucun relevé (donc au moins un point de vigilance à l'ouverture d'une
    session), et un jeu d'utilisateurs de rôles différents."""

    def setUp(self):
        self.navire = Ship.objects.create(name="Navire A", code="NA-SA")
        self.service = Service.objects.create(ship=self.navire, name="Service A")
        self.secteur = Sector.objects.create(service=self.service, name="Secteur A")
        self.installation_critique = Installation.objects.create(
            designation="Groupe électrogène", ship=self.navire, service=self.service,
            sector=self.secteur, critique=True,
        )

        self.autre_navire = Ship.objects.create(name="Navire B", code="NB-SA")
        self.autre_service = Service.objects.create(ship=self.autre_navire, name="Service B")

        self.equipier = self._creer_utilisateur("equipier", "EQUIPIER", ship=self.navire)
        self.chef_section = self._creer_utilisateur("chef_section", "CHEF_SECTION", ship=self.navire)
        self.chef_secteur = self._creer_utilisateur("chef_secteur", "CHEF_SECTEUR", ship=self.navire)
        self.commandant = self._creer_utilisateur("commandant", "COMMANDANT", ship=self.navire)
        self.equipier_autre_navire = self._creer_utilisateur(
            "equipier_b", "EQUIPIER", ship=self.autre_navire
        )
        self.chef_secteur_autre_navire = self._creer_utilisateur(
            "chef_secteur_b", "CHEF_SECTEUR", ship=self.autre_navire
        )

        self.url_page = reverse("pret-appareillage")
        self.url_ouvrir = reverse("session-appareillage-ouvrir")

    def _creer_utilisateur(self, username, role, **scope):
        user = User.objects.create_user(username=username, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, **scope})
        return user

    def _ouvrir_session(self, user, ship):
        """Ouvre une session pour `ship` en tant que `user` (CHEF_SECTEUR+) —
        raccourci pour les tests qui ne portent pas sur l'ouverture elle-même.
        `ship` est passé explicitement plutôt que lu via user.profile.ship : le
        signal accounts.models.create_user_profile met en cache un profil sans
        périmètre sur l'objet `user` dès sa création (avant que
        _creer_utilisateur ne le mette à jour), donc relire user.profile
        renverrait cette version périmée."""
        self.client.login(username=user.username, password="pass")
        self.client.post(self.url_ouvrir)
        return SessionAppareillage.objects.filter(ship=ship, cloturee_le__isnull=True).first()


class AccesPageTests(PretAppareillageTestsBase):
    """Contrôle d'accès à la page principale : tout marin authentifié du
    navire peut la consulter (aucune restriction de rôle sur la saisie)."""

    def test_utilisateur_non_authentifie_redirige_vers_login(self):
        response = self.client.get(self.url_page)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_equipier_a_acces_a_la_page(self):
        self.client.login(username="equipier", password="pass")
        response = self.client.get(self.url_page)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aucune session d'appareillage ouverte")

    def test_equipier_ne_voit_pas_le_bouton_ouvrir_une_session(self):
        self.client.login(username="equipier", password="pass")
        response = self.client.get(self.url_page)
        self.assertFalse(response.context["peut_ouvrir_session"])
        self.assertNotContains(response, self.url_ouvrir)

    def test_chef_secteur_voit_le_bouton_ouvrir_une_session(self):
        self.client.login(username="chef_secteur", password="pass")
        response = self.client.get(self.url_page)
        self.assertTrue(response.context["peut_ouvrir_session"])
        self.assertContains(response, self.url_ouvrir)

    def test_commentaire_dev_checklist_non_affiche_en_clair(self):
        """Régression : le commentaire {# ... #} multi-lignes d'en-tête de
        dashboard/_checklist_appareillage.html s'affichait en clair, faute
        d'être invisible avec {% comment %}...{% endcomment %}."""
        self.client.login(username="equipier", password="pass")
        response = self.client.get(self.url_page)
        self.assertNotContains(response, "Checklist d'une session d'appareillage")


class OuvertureSessionTests(PretAppareillageTestsBase):
    """Création d'une session : réservée à CHEF_SECTEUR+, une seule session
    ouverte à la fois par navire, items générés à partir des points de
    vigilance constatés à l'ouverture."""

    def test_chef_secteur_peut_ouvrir_une_session(self):
        self.client.login(username="chef_secteur", password="pass")
        response = self.client.post(self.url_ouvrir, follow=True)

        self.assertEqual(response.status_code, 200)
        session = SessionAppareillage.objects.get(ship=self.navire)
        self.assertTrue(session.est_ouverte)
        self.assertIsNone(session.cloturee_le)
        self.assertEqual(session.created_by, self.chef_secteur)

    def test_session_contient_le_point_de_vigilance_installation_critique_sans_releve(self):
        self.client.login(username="chef_secteur", password="pass")
        self.client.post(self.url_ouvrir)

        session = SessionAppareillage.objects.get(ship=self.navire)
        libelles = list(session.items.values_list("libelle", flat=True))
        self.assertTrue(any("Groupe électrogène" in libelle for libelle in libelles))

    def test_relever_recent_najoute_pas_de_point_de_vigilance_releve(self):
        InstallationHourReading.objects.create(
            installation=self.installation_critique, date=timezone.localdate(), hours=1200,
        )
        self.client.login(username="chef_secteur", password="pass")
        self.client.post(self.url_ouvrir)

        session = SessionAppareillage.objects.get(ship=self.navire)
        libelles = list(session.items.values_list("libelle", flat=True))
        self.assertFalse(any("heures de marche" in libelle for libelle in libelles))

    def test_derive_signalee_a_plusieurs_destinataires_ne_cree_quun_seul_item(self):
        """_signaler_ou_resoudre_derive (notifications/tasks.py) crée une
        Notification par destinataire (CHEF_SERVICE, CHEF_SECTEUR, CHEF_SECTION...)
        pour une même dérive physique : ici deux destinataires reçoivent chacun
        une notification sur la même dérive d'isolement de l'installation
        critique, et la session ne doit contenir qu'un seul point de vigilance
        « dérive » pour cette installation, pas un par destinataire notifié."""
        installation_ct = ContentType.objects.get_for_model(Installation)
        object_id = f"{self.installation_critique.id}:DERIVE_ISOLEMENT"
        for destinataire in (self.chef_secteur, self.chef_section):
            Notification.objects.create(
                user=destinataire,
                content_type=installation_ct,
                object_id=object_id,
                is_read=False,
                verb="Dérive détectée sur l'isolement de Groupe électrogène : seuil estimé atteint dans 5 j",
            )

        self.client.login(username="chef_secteur", password="pass")
        self.client.post(self.url_ouvrir)

        session = SessionAppareillage.objects.get(ship=self.navire)
        items_derive = session.items.filter(categorie=ItemAppareillage.CATEGORIE_DERIVE)
        self.assertEqual(items_derive.count(), 1)

    def test_equipier_ne_peut_pas_ouvrir_de_session(self):
        self.client.login(username="equipier", password="pass")
        response = self.client.post(self.url_ouvrir)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(SessionAppareillage.objects.filter(ship=self.navire).exists())

    def test_chef_section_ne_peut_pas_ouvrir_de_session(self):
        """Rôle juste en dessous du seuil minimum (CHEF_SECTEUR)."""
        self.client.login(username="chef_section", password="pass")
        response = self.client.post(self.url_ouvrir)

        self.assertEqual(response.status_code, 403)

    def test_blocage_si_une_session_est_deja_ouverte(self):
        self.client.login(username="chef_secteur", password="pass")
        self.client.post(self.url_ouvrir)
        self.assertEqual(SessionAppareillage.objects.filter(ship=self.navire).count(), 1)

        response = self.client.post(self.url_ouvrir, follow=True)

        self.assertEqual(SessionAppareillage.objects.filter(ship=self.navire).count(), 1)
        self.assertContains(response, "déjà ouverte")

    def test_session_dun_navire_nempeche_pas_louverture_sur_un_autre_navire(self):
        self.client.login(username="chef_secteur", password="pass")
        self.client.post(self.url_ouvrir)

        self.client.login(username="chef_secteur_b", password="pass")
        response = self.client.post(self.url_ouvrir, follow=True)

        self.assertTrue(SessionAppareillage.objects.filter(ship=self.autre_navire).exists())


class CochageItemTests(PretAppareillageTestsBase):
    """Cochage d'un item : ouvert à tout marin authentifié du navire, sans
    restriction de rôle — mais isolé par navire et bloqué une fois la session
    clôturée."""

    def setUp(self):
        super().setUp()
        self.session = self._ouvrir_session(self.chef_secteur, self.navire)
        self.item = self.session.items.first()
        self.url_cocher = reverse("item-appareillage-cocher", args=[self.item.id])

    def test_equipier_peut_cocher_un_item(self):
        self.client.login(username="equipier", password="pass")
        response = self.client.post(self.url_cocher)

        self.assertEqual(response.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.verifie_par, self.equipier)
        self.assertIsNotNone(self.item.verifie_le)

    def test_cocher_deux_fois_decoche_litem(self):
        self.client.login(username="equipier", password="pass")
        self.client.post(self.url_cocher)
        self.client.post(self.url_cocher)

        self.item.refresh_from_db()
        self.assertIsNone(self.item.verifie_par)
        self.assertIsNone(self.item.verifie_le)

    def test_progression_de_la_session_reflete_les_items_verifies(self):
        self.client.login(username="equipier", password="pass")
        self.client.post(self.url_cocher)

        self.session.refresh_from_db()
        self.assertEqual(self.session.nombre_items_verifies, 1)

    def test_marin_dun_autre_navire_ne_peut_pas_cocher(self):
        self.client.login(username="equipier_b", password="pass")
        response = self.client.post(self.url_cocher)

        self.assertEqual(response.status_code, 403)
        self.item.refresh_from_db()
        self.assertIsNone(self.item.verifie_par)


class SignatureSessionTests(PretAppareillageTestsBase):
    """Signature/clôture : réservée à CHEF_SECTEUR+, même pattern de mot de
    passe que MaintenanceExecution (maintenance/web_views.py)."""

    def setUp(self):
        super().setUp()
        self.session = self._ouvrir_session(self.chef_secteur, self.navire)
        self.url_signer = reverse("session-appareillage-signer", args=[self.session.id])

    def test_chef_secteur_peut_signer_avec_le_bon_mot_de_passe(self):
        self.client.login(username="chef_secteur", password="pass")
        response = self.client.post(self.url_signer, {"mot_de_passe": "pass"}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertFalse(self.session.est_ouverte)
        self.assertEqual(self.session.valide_par, self.chef_secteur)
        self.assertIsNotNone(self.session.date_validation)
        self.assertIsNotNone(self.session.cloturee_le)

    def test_mot_de_passe_incorrect_ne_signe_pas_la_session(self):
        self.client.login(username="chef_secteur", password="pass")
        response = self.client.post(self.url_signer, {"mot_de_passe": "mauvais"}, follow=True)

        self.assertContains(response, "Mot de passe incorrect")
        self.session.refresh_from_db()
        self.assertTrue(self.session.est_ouverte)
        self.assertIsNone(self.session.valide_par)

    def test_commandant_peut_signer(self):
        """Rôle supérieur au minimum requis : doit aussi être accepté."""
        self.client.login(username="commandant", password="pass")
        response = self.client.post(self.url_signer, {"mot_de_passe": "pass"}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertFalse(self.session.est_ouverte)

    def test_chef_section_ne_peut_pas_signer(self):
        self.client.login(username="chef_section", password="pass")
        response = self.client.post(self.url_signer, {"mot_de_passe": "pass"})

        self.assertEqual(response.status_code, 403)
        self.session.refresh_from_db()
        self.assertTrue(self.session.est_ouverte)

    def test_equipier_ne_peut_pas_signer(self):
        self.client.login(username="equipier", password="pass")
        response = self.client.post(self.url_signer, {"mot_de_passe": "pass"})

        self.assertEqual(response.status_code, 403)

    def test_chef_secteur_dun_autre_navire_ne_peut_pas_signer(self):
        self.client.login(username="chef_secteur_b", password="pass")
        response = self.client.post(self.url_signer, {"mot_de_passe": "pass"})

        self.assertEqual(response.status_code, 403)
        self.session.refresh_from_db()
        self.assertTrue(self.session.est_ouverte)


class ImmutabiliteApresClotureTests(PretAppareillageTestsBase):
    """Une session clôturée est figée : plus aucune modification n'est
    possible, ni sur les items, ni via une nouvelle signature."""

    def setUp(self):
        super().setUp()
        self.session = self._ouvrir_session(self.chef_secteur, self.navire)
        self.item = self.session.items.first()
        self.client.login(username="chef_secteur", password="pass")
        self.client.post(reverse("session-appareillage-signer", args=[self.session.id]), {"mot_de_passe": "pass"})
        self.session.refresh_from_db()

    def test_cocher_un_item_dune_session_cloturee_est_refuse(self):
        self.client.login(username="equipier", password="pass")
        response = self.client.post(reverse("item-appareillage-cocher", args=[self.item.id]))

        self.assertEqual(response.status_code, 400)
        self.item.refresh_from_db()
        self.assertIsNone(self.item.verifie_par)

    def test_une_nouvelle_session_peut_etre_ouverte_apres_cloture(self):
        self.client.login(username="chef_secteur", password="pass")
        response = self.client.post(self.url_ouvrir, follow=True)

        self.assertEqual(SessionAppareillage.objects.filter(ship=self.navire).count(), 2)
        self.assertNotContains(response, "déjà ouverte")


class HistoriqueEtDetailTests(PretAppareillageTestsBase):
    """Historique des sessions clôturées et détail en lecture seule — isolés
    par navire."""

    def setUp(self):
        super().setUp()
        self.session = self._ouvrir_session(self.chef_secteur, self.navire)
        self.client.login(username="chef_secteur", password="pass")
        self.client.post(reverse("session-appareillage-signer", args=[self.session.id]), {"mot_de_passe": "pass"})
        self.session.refresh_from_db()
        self.url_historique = reverse("historique-appareillage")
        self.url_detail = reverse("session-appareillage-detail", args=[self.session.id])

    def test_session_cloturee_apparait_dans_lhistorique_du_navire(self):
        self.client.login(username="equipier", password="pass")
        response = self.client.get(self.url_historique)

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.session, response.context["sessions"])

    def test_session_absente_de_lhistorique_dun_autre_navire(self):
        self.client.login(username="equipier_b", password="pass")
        response = self.client.get(self.url_historique)

        self.assertNotIn(self.session, response.context["sessions"])

    def test_detail_accessible_pour_un_marin_du_meme_navire(self):
        self.client.login(username="equipier", password="pass")
        response = self.client.get(self.url_detail)

        self.assertEqual(response.status_code, 200)

    def test_detail_refuse_pour_un_marin_dun_autre_navire(self):
        self.client.login(username="equipier_b", password="pass")
        response = self.client.get(self.url_detail)

        self.assertEqual(response.status_code, 403)

    def test_detail_ne_propose_pas_de_signature(self):
        self.client.login(username="chef_secteur", password="pass")
        response = self.client.get(self.url_detail)

        self.assertFalse(response.context["peut_signer"])
