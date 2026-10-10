"""Feuille de service : un commandant ne peut ni lire, ni rédiger, ni viser la feuille d'un autre navire."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import UserProfile
from org.models import Ship
from quarts.models import (
    FeuilleService,
    peut_gerer_brouillon_feuille,
    peut_lire_feuille_service,
    peut_rediger_feuille_service,
    peut_viser_comaeq,
    peut_viser_secteur,
    peut_viser_service,
)


def creer_marin(username, role, ship):
    user = User.objects.create_user(username=username, password="pass")
    UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": ship})
    return User.objects.get(pk=user.pk)


class FeuilleAutreNavireTests(TestCase):
    def setUp(self):
        self.navire_a = Ship.objects.create(name="Navire A", code="NA", classe_navire="FDA")
        self.navire_b = Ship.objects.create(name="Navire B", code="NB", classe_navire="FDA")
        self.jour = timezone.localdate()
        self.feuille_b = FeuilleService.objects.create(
            ship=self.navire_b, date=self.jour, statut=FeuilleService.STATUT_PUBLIEE
        )
        self.cdt_a = creer_marin("cdt_a", "COMMANDANT", self.navire_a)
        self.cdt_b = creer_marin("cdt_b", "COMMANDANT", self.navire_b)
        self.url_b = f"/quarts/feuille-service/{self.navire_b.pk}/{self.jour.isoformat()}/"

    def test_le_commandant_d_un_autre_navire_n_a_aucun_droit(self):
        for droit in (peut_lire_feuille_service, peut_gerer_brouillon_feuille, peut_viser_secteur,
                      peut_viser_service, peut_viser_comaeq):
            self.assertFalse(droit(self.cdt_a, self.feuille_b), droit.__name__)
        self.assertFalse(peut_rediger_feuille_service(self.cdt_a, self.navire_b))

    def test_le_commandant_du_navire_garde_ses_droits(self):
        self.assertTrue(peut_lire_feuille_service(self.cdt_b, self.feuille_b))
        self.assertTrue(peut_rediger_feuille_service(self.cdt_b, self.navire_b))

    def test_la_page_est_refusee_au_commandant_d_un_autre_navire(self):
        self.client.force_login(self.cdt_a)
        self.assertEqual(self.client.get(self.url_b).status_code, 403)
        self.assertEqual(self.client.post(self.url_b, {"action": "creer"}).status_code, 403)

    def test_la_page_reste_ouverte_au_commandant_du_navire_et_a_l_administrateur_general(self):
        for utilisateur in (self.cdt_b, creer_marin("admin_g", "MASTER_ADMIN", None)):
            self.client.force_login(utilisateur)
            self.assertEqual(self.client.get(self.url_b).status_code, 200, utilisateur.username)
