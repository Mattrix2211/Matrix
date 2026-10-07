"""Centre de notifications (UX-1.3) : compteur, tri, isolation, actions, liens."""
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import Client, RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import UserProfile
from assets.models import Installation
from matrix.context_processors import compteur_notifications
from notifications.models import Notification
from org.models import Sector, Service, Ship


class CentreNotificationsTestCase(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Alsace", code="D656")
        self.autre_navire = Ship.objects.create(name="Provence", code="D652")
        self.marin = self._marin("marin", self.navire)
        self.autre = self._marin("autre", self.navire)

    def _marin(self, nom, navire):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": "EQUIPIER", "ship": navire})
        return User.objects.get(pk=user.pk)

    def _notif(self, user, verb="Message", level="info", lue=False, **kw):
        return Notification.objects.create(user=user, verb=verb, level=level, is_read=lue, **kw)

    def _installation(self, navire):
        service = Service.objects.create(ship=navire, name=f"Service {navire.code}")
        secteur = Sector.objects.create(service=service, name="Secteur")
        return Installation.objects.create(designation="Pompe", ship=navire, service=service, sector=secteur)


class CompteurTests(CentreNotificationsTestCase):
    def test_compteur_par_utilisateur_et_non_lues_seulement(self):
        self._notif(self.marin)
        self._notif(self.marin, lue=True)
        self._notif(self.autre)
        requete = RequestFactory().get("/")
        requete.user = self.marin
        self.assertEqual(compteur_notifications(requete), {"notifications_non_lues": 1})

    def test_une_seule_requete_count_et_aucune_pour_un_anonyme(self):
        from django.contrib.auth.models import AnonymousUser

        requete = RequestFactory().get("/")
        requete.user = self.marin
        with CaptureQueriesContext(connection) as requetes:
            compteur_notifications(requete)
        self.assertEqual(len(requetes), 1)
        self.assertIn("COUNT", requetes[0]["sql"].upper())
        requete.user = AnonymousUser()
        with CaptureQueriesContext(connection) as requetes:
            self.assertEqual(compteur_notifications(requete), {})
        self.assertEqual(len(requetes), 0)


class BarreTests(CentreNotificationsTestCase):
    def test_cloche_avec_aria_label_et_compteur_accessible(self):
        for _ in range(2):
            self._notif(self.marin)
        self.client.force_login(self.marin)
        html = self.client.get(reverse("home")).content.decode()
        self.assertIn('aria-label="Notifications"', html)
        self.assertIn("2 notifications non lues", html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn('id="centre-notifications"', html)

    def test_compteur_masque_a_zero(self):
        self.client.force_login(self.marin)
        html = self.client.get(reverse("home")).content.decode()
        self.assertNotIn("non lue", html)
        self.assertNotIn("mx-cloche__pastille", html)

    def test_singulier(self):
        self._notif(self.marin)
        self.client.force_login(self.marin)
        self.assertContains(self.client.get(reverse("home")), "1 notification non lue")


class PanneauTests(CentreNotificationsTestCase):
    def test_tri_par_niveau_puis_date_decroissante(self):
        self._notif(self.marin, "info récente", "info")
        self._notif(self.marin, "danger ancien", "danger")
        self._notif(self.marin, "warning", "warning")
        self._notif(self.marin, "danger récent", "danger")
        self.client.force_login(self.marin)
        html = self.client.get(reverse("notifications-panneau")).content.decode()
        ordre = [html.index(t) for t in ("danger récent", "danger ancien", "warning", "info récente")]
        self.assertEqual(ordre, sorted(ordre))

    def test_niveau_en_texte_et_message(self):
        self._notif(self.marin, "Alerte", "danger")
        self.client.force_login(self.marin)
        html = self.client.get(reverse("notifications-panneau")).content.decode()
        self.assertIn("Critique", html)
        self.assertIn("Alerte", html)

    def test_message_echappe(self):
        self._notif(self.marin, "<script>alert(1)</script>")
        self.client.force_login(self.marin)
        reponse = self.client.get(reverse("notifications-panneau"))
        self.assertContains(reponse, "&lt;script&gt;")
        self.assertNotContains(reponse, "<script>alert(1)")

    def test_ne_montre_pas_les_notifications_des_autres(self):
        self._notif(self.autre, "Secret de l'autre")
        self.client.force_login(self.marin)
        reponse = self.client.get(reverse("notifications-panneau"))
        self.assertNotContains(reponse, "Secret de l'autre")
        self.assertContains(reponse, "Aucune notification")

    def test_anonyme_redirige(self):
        for nom, args in (("notifications-panneau", []), ("notifications-compteur", [])):
            self.assertEqual(self.client.get(reverse(nom, args=args)).status_code, 302)
        self.assertEqual(self.client.post(reverse("notifications-tout-lu")).status_code, 302)


class LienTests(CentreNotificationsTestCase):
    def _notif_installation(self, user, installation):
        return self._notif(
            user, "Échéance", "warning",
            content_type=ContentType.objects.get_for_model(Installation), object_id=str(installation.pk),
        )

    def test_lien_vers_objet_accessible(self):
        installation = self._installation(self.navire)
        self._notif_installation(self.marin, installation)
        self.client.force_login(self.marin)
        self.assertContains(
            self.client.get(reverse("notifications-panneau")),
            reverse("installation-detail", args=[installation.pk]),
        )

    def test_aucun_lien_vers_objet_interdit(self):
        installation = self._installation(self.autre_navire)
        self._notif_installation(self.marin, installation)
        self.client.force_login(self.marin)
        reponse = self.client.get(reverse("notifications-panneau"))
        self.assertContains(reponse, "Échéance")
        self.assertNotContains(reponse, str(installation.pk))

    def test_identifiant_malforme_sans_erreur(self):
        self._notif(self.marin, "X", content_type=ContentType.objects.get_for_model(Installation), object_id="pas-un-uuid")
        self.client.force_login(self.marin)
        self.assertEqual(self.client.get(reverse("notifications-panneau")).status_code, 200)


class ActionsTests(CentreNotificationsTestCase):
    def test_marquer_lue_met_a_jour_liste_et_compteur(self):
        notif = self._notif(self.marin)
        self._notif(self.marin)
        self.client.force_login(self.marin)
        reponse = self.client.post(reverse("notifications-lue", args=[notif.pk]))
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)
        self.assertContains(reponse, 'hx-swap-oob="true"')
        self.assertContains(reponse, "1 notification non lue")

    def test_tout_marquer_lu(self):
        self._notif(self.marin)
        self._notif(self.marin, "Critique", "danger")
        autre = self._notif(self.autre)
        self.client.force_login(self.marin)
        reponse = self.client.post(reverse("notifications-tout-lu"))
        self.assertFalse(Notification.objects.filter(user=self.marin, is_read=False).exists())
        autre.refresh_from_db()
        self.assertFalse(autre.is_read)
        self.assertNotContains(reponse, "non lue")

    def test_notification_d_un_autre_introuvable(self):
        notif = self._notif(self.autre)
        self.client.force_login(self.marin)
        self.assertEqual(self.client.post(reverse("notifications-lue", args=[notif.pk])).status_code, 404)
        notif.refresh_from_db()
        self.assertFalse(notif.is_read)

    def test_get_refuse_sur_les_actions(self):
        notif = self._notif(self.marin)
        self.client.force_login(self.marin)
        self.assertEqual(self.client.get(reverse("notifications-lue", args=[notif.pk])).status_code, 405)

    def test_csrf_exige(self):
        notif = self._notif(self.marin)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.marin)
        self.assertEqual(client.post(reverse("notifications-lue", args=[notif.pk])).status_code, 403)
        self.assertEqual(client.post(reverse("notifications-tout-lu")).status_code, 403)


class ApiTests(CentreNotificationsTestCase):
    url = "/api/notifications/notifications/"

    def setUp(self):
        super().setUp()
        self.api = APIClient()
        self.api.force_authenticate(self.marin)

    def test_post_ne_cree_rien(self):
        reponse = self.api.post(self.url, {"user": self.autre.pk, "verb": "Injection", "level": "danger"}, format="json")
        self.assertEqual(reponse.status_code, 405)
        self.assertFalse(Notification.objects.filter(verb="Injection").exists())

    def test_patch_ne_reaffecte_pas(self):
        notif = self._notif(self.marin, "Origine")
        reponse = self.api.patch(f"{self.url}{notif.pk}/", {"user": self.autre.pk, "verb": "Changé", "is_read": True}, format="json")
        self.assertEqual(reponse.status_code, 200)
        notif.refresh_from_db()
        self.assertEqual((notif.user, notif.verb, notif.is_read), (self.marin, "Origine", True))

    def test_delete_refuse(self):
        notif = self._notif(self.marin)
        self.assertEqual(self.api.delete(f"{self.url}{notif.pk}/").status_code, 405)
        self.assertTrue(Notification.objects.filter(pk=notif.pk).exists())

    def test_patch_notification_d_un_autre_introuvable(self):
        notif = self._notif(self.autre)
        self.assertEqual(self.api.patch(f"{self.url}{notif.pk}/", {"is_read": True}, format="json").status_code, 404)

    def test_mark_all_read(self):
        self._notif(self.marin)
        autre = self._notif(self.autre)
        reponse = self.api.post(f"{self.url}mark_all_read/")
        self.assertEqual(reponse.json(), {"marked": 1})
        autre.refresh_from_db()
        self.assertFalse(autre.is_read)


class PageCentreTests(CentreNotificationsTestCase):
    def test_historique_personnel_et_pagination(self):
        for i in range(25):
            self._notif(self.marin, verb=f"Mienne {i}")
        self._notif(self.autre, verb="Secrète")
        self.client.force_login(self.marin)
        r = self.client.get(reverse("notifications-centre"))
        self.assertEqual(len(r.context["page"].object_list), 20)
        self.assertNotContains(r, "Secrète")
        self.assertEqual(len(self.client.get(reverse("notifications-centre") + "?page=2").context["page"].object_list), 5)

    def test_filtres_lu_et_niveau(self):
        self._notif(self.marin, verb="Neuve")
        self._notif(self.marin, verb="Ancienne", lue=True)
        self._notif(self.marin, verb="Grave", level="danger")
        self.client.force_login(self.marin)
        url = reverse("notifications-centre")
        self.assertEqual(len(self.client.get(url + "?etat=non_lues").context["page"].object_list), 2)
        self.assertEqual(len(self.client.get(url + "?etat=lues").context["page"].object_list), 1)
        self.assertEqual(len(self.client.get(url + "?niveau=danger").context["page"].object_list), 1)

    def test_tout_marquer_lu_ne_touche_que_le_marin(self):
        self._notif(self.marin)
        autre = self._notif(self.autre)
        self.client.force_login(self.marin)
        self.client.post(reverse("notifications-centre-tout-lu"))
        self.assertFalse(Notification.objects.filter(user=self.marin, is_read=False).exists())
        autre.refresh_from_db()
        self.assertFalse(autre.is_read)

    def test_marquer_lue_refuse_celle_dun_autre(self):
        autre = self._notif(self.autre)
        self.client.force_login(self.marin)
        r = self.client.post(reverse("notifications-centre-lue", args=[autre.pk]))
        self.assertEqual(r.status_code, 404)

    def test_marquer_lue_conserve_les_filtres(self):
        n = self._notif(self.marin)
        self.client.force_login(self.marin)
        r = self.client.post(reverse("notifications-centre-lue", args=[n.pk]), {"requete": "etat=non_lues"})
        self.assertRedirects(r, reverse("notifications-centre") + "?etat=non_lues")
        n.refresh_from_db()
        self.assertTrue(n.is_read)

    def test_equipage_a_terre_peut_marquer_lu(self):
        self.navire.double_equipage, self.navire.equipage_a_bord = True, "A"
        self.navire.save()
        profil = self.marin.profile
        profil.equipage = "B"
        profil.save()
        n = self._notif(self.marin)
        self.client.force_login(self.marin)
        self.client.post(reverse("notifications-centre-lue", args=[n.pk]))
        self.client.post(reverse("notifications-centre-tout-lu"))
        self.assertFalse(Notification.objects.filter(user=self.marin, is_read=False).exists())

    def test_panneau_propose_voir_tout(self):
        self.client.force_login(self.marin)
        self.assertContains(self.client.get(reverse("notifications-panneau")), reverse("notifications-centre"))
