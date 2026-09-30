"""Double équipage : un marin sans équipage ne peut pas être titulaire d'un poste
de commandant adjoint (COMAEQ, COMOPS, COMANAV, COMAVIA) d'un bâtiment à double
équipage ; les navires à équipage unique et les titulaires déjà en place ne sont
pas touchés (ils sont signalés dans les Réglages)."""
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from org.models import CommandantAdjoint, Equipage, Ship


def _marin(username, role, ship, equipage=None):
    user = User.objects.create_user(username=username, password="pass")
    UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": ship, "equipage": equipage})
    return User.objects.get(pk=user.pk)


class TitulaireSansEquipageTests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("settings")
        self.ship = Ship.objects.create(
            name="FREMM Titulaire", code="FT2", classe_navire="FREMM", double_equipage=True, capacite_aviation=True,
        )
        self.bleu = Equipage.objects.create(ship=self.ship, nom="Bleu")
        self.rouge = Equipage.objects.create(ship=self.ship, nom="Rouge")
        self.ship.equipage_a_bord = self.bleu
        self.ship.save()
        self.commandant = _marin("cdt", "COMMANDANT", self.ship, self.bleu)
        self.client.force_login(self.commandant)

    def _designer(self, poste, marin):
        return self.client.post(self.url, {
            "action": "set_titulaire_commandant_adjoint", "pk": poste.pk, "user_id": marin.pk,
        }, follow=True)

    def test_marin_sans_equipage_refuse_pour_chaque_sigle(self):
        sans_equipage = _marin("sans_eq", "ETAT_MAJOR", self.ship)
        for sigle in ("COMAEQ", "COMOPS", "COMANAV", "COMAVIA"):
            poste = CommandantAdjoint.objects.create(ship=self.ship, equipage=self.bleu, sigle=sigle)
            reponse = self._designer(poste, sans_equipage)
            poste.refresh_from_db()
            self.assertIsNone(poste.titulaire, sigle)
            self.assertContains(reponse, "rattachez-le d&#x27;abord à l&#x27;équipage Bleu")

    def test_marin_du_bon_equipage_accepte_et_autre_equipage_toujours_refuse(self):
        poste = CommandantAdjoint.objects.create(ship=self.ship, equipage=self.bleu, sigle="COMAEQ")
        du_rouge = _marin("rouge", "ETAT_MAJOR", self.ship, self.rouge)
        self._designer(poste, du_rouge)
        poste.refresh_from_db()
        self.assertIsNone(poste.titulaire)
        du_bleu = _marin("bleu", "ETAT_MAJOR", self.ship, self.bleu)
        self._designer(poste, du_bleu)
        poste.refresh_from_db()
        self.assertEqual(poste.titulaire, du_bleu)

    def test_navire_a_equipage_unique_inchange(self):
        unique = Ship.objects.create(name="BRF Unique", code="BU")
        poste = CommandantAdjoint.objects.create(ship=unique, sigle="COMAEQ")
        marin = _marin("em_unique", "ETAT_MAJOR", unique)
        commandant = _marin("cdt_unique", "COMMANDANT", unique)
        self.client.force_login(commandant)
        self._designer(poste, marin)
        poste.refresh_from_db()
        self.assertEqual(poste.titulaire, marin)

    def test_titulaire_deja_en_place_signale_sans_etre_modifie(self):
        sans_equipage = _marin("ancien", "ETAT_MAJOR", self.ship)
        # Donnée antérieure à la règle : posée par mise à jour directe, car
        # save() refuse désormais un titulaire sans équipage.
        poste = CommandantAdjoint.objects.create(ship=self.ship, equipage=self.bleu, sigle="COMOPS")
        CommandantAdjoint.objects.filter(pk=poste.pk).update(titulaire=sans_equipage)
        poste.refresh_from_db()
        reponse = self.client.get(self.url, {"tab": "commandants_adjoints"})
        self.assertContains(reponse, "rattaché à aucun équipage")
        poste.refresh_from_db()
        self.assertEqual(poste.titulaire, sans_equipage)

    def test_aucune_alerte_quand_tout_est_en_ordre(self):
        du_bleu = _marin("bleu", "ETAT_MAJOR", self.ship, self.bleu)
        CommandantAdjoint.objects.create(ship=self.ship, equipage=self.bleu, sigle="COMOPS", titulaire=du_bleu)
        reponse = self.client.get(self.url, {"tab": "commandants_adjoints"})
        self.assertNotContains(reponse, "rattaché à aucun équipage")
