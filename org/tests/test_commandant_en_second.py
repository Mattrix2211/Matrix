"""Commandant en second : vision globale du commandant en LECTURE sur son navire
(son équipage en double équipage), sans droit d'écriture supplémentaire ;
configuration dans l'onglet « Commandants adjoints » des Réglages."""
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import AuditLog, UserProfile
from org.commandant_en_second import a_vision_commandant
from org.models import CommandantEnSecond, Equipage, Service, Ship


def _marin(username, role, ship, equipage=None):
    user = User.objects.create_user(username=username, password="pass")
    UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": ship, "equipage": equipage})
    return User.objects.get(pk=user.pk)


class VisionCommandantEnSecondTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="BRF Second", code="BRF-S")
        self.autre = Ship.objects.create(name="Autre S", code="AUT-S")
        self.second = _marin("second", "ETAT_MAJOR", self.ship)
        service = Service.objects.create(ship=self.ship, name="Pont")
        self.matelot = _marin("matelot", "EQUIPIER", None)
        UserProfile.objects.filter(user=self.matelot).update(service=service)
        self.etranger = _marin("etranger", "EQUIPIER", self.autre)
        self.api = APIClient()

    def _logins_visibles(self, user):
        self.api.force_authenticate(user)
        reponse = self.api.get("/api/accounts/users/")
        self.assertEqual(reponse.status_code, 200)
        donnees = reponse.json()
        donnees = donnees["results"] if isinstance(donnees, dict) else donnees
        return {u["username"] for u in donnees}

    def test_sans_poste_l_etat_major_ne_voit_pas_tout_le_navire(self):
        self.assertFalse(a_vision_commandant(self.second))
        self.assertNotIn("matelot", self._logins_visibles(self.second))

    def test_titulaire_voit_tout_son_navire_et_pas_un_autre(self):
        CommandantEnSecond.objects.create(ship=self.ship, titulaire=self.second)
        vus = self._logins_visibles(self.second)
        self.assertIn("matelot", vus)
        self.assertNotIn("etranger", vus)

    def test_poste_sur_un_autre_navire_ne_donne_rien(self):
        CommandantEnSecond.objects.create(ship=self.autre, titulaire=self.second)
        self.assertFalse(a_vision_commandant(self.second))

    def test_aucun_droit_d_ecriture_supplementaire(self):
        CommandantEnSecond.objects.create(ship=self.ship, titulaire=self.second)
        self.client.force_login(self.second)
        reponse = self.client.post(reverse("settings"), {"action": "add_commandant_adjoint", "sigle": "COMAEQ"})
        self.assertEqual(reponse.status_code, 403)
        # Lecture seule : l'annuaire s'ouvre, mais aucune écriture n'est acceptée.
        self.assertEqual(self.client.get(reverse("user-directory")).status_code, 200)
        self.assertEqual(self.client.post(reverse("user-directory"), {"action": "bulk_delete_users"}).status_code, 403)

    def test_double_equipage_limite_a_son_equipage(self):
        ship = Ship.objects.create(name="FREMM S", code="FR-S", double_equipage=True)
        bleu = Equipage.objects.create(ship=ship, nom="Bleu")
        rouge = Equipage.objects.create(ship=ship, nom="Rouge")
        second = _marin("second_bleu", "ETAT_MAJOR", ship, bleu)
        _marin("marin_bleu", "EQUIPIER", ship, bleu)
        _marin("marin_rouge", "EQUIPIER", ship, rouge)
        CommandantEnSecond.objects.create(ship=ship, equipage=bleu, titulaire=second)
        vus = self._logins_visibles(second)
        self.assertIn("marin_bleu", vus)
        self.assertNotIn("marin_rouge", vus)


class ConfigurationCommandantEnSecondTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("settings")
        self.ship = Ship.objects.create(name="BRF Conf", code="BRF-C")
        self.autre = Ship.objects.create(name="Autre Conf", code="AUT-C")
        self.commandant = _marin("cdt", "COMMANDANT", self.ship)
        self.em = _marin("em", "ETAT_MAJOR", self.ship)
        self.client.force_login(self.commandant)

    def _post(self, action, **donnees):
        return self.client.post(self.url, {"action": action, **donnees}, follow=True)

    def test_chef_de_service_refuse(self):
        self.client.force_login(_marin("chef", "CHEF_SERVICE", self.ship))
        self._post("set_commandant_en_second", libelle="OFFICIER_EN_SECOND", user_id=self.em.pk)
        self.assertFalse(CommandantEnSecond.objects.exists())

    def test_designation_avec_libelle_et_audit_sur_son_navire_seulement(self):
        self._post("set_commandant_en_second", libelle="OFFICIER_EN_SECOND", user_id=self.em.pk, ship_id=self.autre.pk)
        poste = CommandantEnSecond.objects.get()
        self.assertEqual((poste.ship, poste.titulaire, poste.libelle), (self.ship, self.em, "OFFICIER_EN_SECOND"))
        self.assertTrue(AuditLog.objects.filter(action="set_commandant_en_second", actor=self.commandant).exists())
        self.assertContains(self.client.get(self.url, {"tab": "commandants_adjoints"}), "Officier en second")

    def test_titulaire_hors_etat_major_ou_autre_navire_refuse(self):
        self._post("set_commandant_en_second", libelle="COMMANDANT_EN_SECOND", user_id=_marin("x", "EQUIPIER", self.ship).pk)
        self._post("set_commandant_en_second", libelle="COMMANDANT_EN_SECOND", user_id=_marin("y", "ETAT_MAJOR", self.autre).pk)
        self.assertFalse(CommandantEnSecond.objects.exists())

    def test_suppression_du_poste(self):
        CommandantEnSecond.objects.create(ship=self.ship, titulaire=self.em)
        self._post("delete_commandant_en_second")
        self.assertFalse(CommandantEnSecond.objects.exists())
