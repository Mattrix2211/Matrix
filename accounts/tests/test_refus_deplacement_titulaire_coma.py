"""Règle du double équipage : un titulaire de poste COMA (ou de commandant en
second) ne change pas d'équipage, de bâtiment ni de service sans libérer son
poste. Le refus doit s'afficher en message français (web) ou en réponse 400
(API), jamais en erreur serveur, et laisser le titulaire inchangé."""
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.urls import reverse
from rest_framework.test import APIClient

from org.models import CommandantAdjoint, Section, Sector, Service, Ship
from org.tests.test_coherence_equipage import BaseDoubleEquipage, creer_marin


class BaseRefusTitulaire(BaseDoubleEquipage):
    def setUp(self):
        super().setUp()
        # Marins rattachés au bâtiment uniquement par leur section (champ navire vide) :
        # un changement de service, secteur ou section peut donc les faire changer de bâtiment.
        service = Service.objects.create(ship=self.ship, equipage=self.bleu, name="Service bord")
        secteur = Sector.objects.create(service=service, equipage=self.bleu, name="Secteur bord")
        self.section = Section.objects.create(sector=secteur, equipage=self.bleu, name="Section bord")
        self.titulaire = creer_marin("coma_bleu", "ETAT_MAJOR", None, self.bleu, section=self.section)
        CommandantAdjoint.objects.create(ship=self.ship, equipage=self.bleu, sigle="COMOPS", titulaire=self.titulaire)
        self.simple = creer_marin("simple_bleu", "EQUIPIER", None, self.bleu, section=self.section)
        self.autre = Ship.objects.create(name="Autre unité", code="AUT")
        self.service_autre = Service.objects.create(ship=self.autre, name="Service autre")
        self.secteur_autre = Sector.objects.create(service=self.service_autre, name="Secteur autre")
        self.section_autre = Section.objects.create(sector=self.secteur_autre, name="Section autre")
        self.master = User.objects.create_superuser(username="master_coma", password="pass", email="m@example.com")
        self.client.login(username="master_coma", password="pass")

    def _messages(self, reponse):
        return " ".join(str(m) for m in get_messages(reponse.wsgi_request))

    def _titulaire_inchange(self):
        profil = self.titulaire.profile
        profil.refresh_from_db()
        self.assertEqual(profil.equipage, self.bleu)
        self.assertEqual(profil.section, self.section)
        self.assertIsNone(profil.ship)


class AnnuaireRefusTitulaireTests(BaseRefusTitulaire):
    def _post(self, action, **donnees):
        return self.client.post(reverse("user-directory"), {"action": action, **donnees})

    def _verifier_bulk(self, action, **donnees):
        reponse = self._post(action, selected_ids=[self.titulaire.pk, self.simple.pk], **donnees)
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("COMOPS", self._messages(reponse))
        self._titulaire_inchange()
        return self.simple.profile

    def test_bulk_update_ship(self):
        profil = self._verifier_bulk("bulk_update_ship", ship_id=self.autre.pk)
        profil.refresh_from_db()
        self.assertEqual(profil.ship, self.autre)

    def test_bulk_update_service(self):
        profil = self._verifier_bulk("bulk_update_service", service_id=self.service_autre.pk)
        profil.refresh_from_db()
        self.assertEqual(profil.service, self.service_autre)

    def test_bulk_update_sector(self):
        profil = self._verifier_bulk("bulk_update_sector", sector_id=self.secteur_autre.pk)
        profil.refresh_from_db()
        self.assertEqual(profil.sector, self.secteur_autre)

    def test_bulk_update_section(self):
        profil = self._verifier_bulk("bulk_update_section", section_id=self.section_autre.pk)
        profil.refresh_from_db()
        self.assertEqual(profil.section, self.section_autre)

    def test_edit_user(self):
        reponse = self._post(
            "edit_user", pk=self.titulaire.pk, username="coma_bleu", ship_id=self.autre.pk,
        )
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("COMOPS", self._messages(reponse))
        self._titulaire_inchange()


class PageEquipagesRefusTitulaireTests(BaseRefusTitulaire):
    def test_affecter_refuse_le_titulaire_et_garde_le_non_titulaire(self):
        reponse = self.client.post(reverse("equipages"), {
            "action": "affecter_equipage_marin", "ship_id": self.ship.pk,
            "user_id": self.titulaire.pk, "equipage_id": self.rouge.pk,
        })
        self.assertIn("COMOPS", self._messages(reponse))
        self._titulaire_inchange()
        self.client.post(reverse("equipages"), {
            "action": "affecter_equipage_marin", "ship_id": self.ship.pk,
            "user_id": self.simple.pk, "equipage_id": self.rouge.pk,
        })
        self.simple.profile.refresh_from_db()
        self.assertEqual(self.simple.profile.equipage, self.rouge)


class ApiRefusTitulaireTests(BaseRefusTitulaire):
    def setUp(self):
        super().setUp()
        self.api = APIClient()
        self.api.login(username="master_coma", password="pass")
        self.url = f"/api/accounts/profiles/{self.titulaire.profile.pk}/"

    def test_patch_renvoie_400_avec_le_message(self):
        reponse = self.api.patch(self.url, {"equipage": self.rouge.pk}, format="json")
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("COMOPS", " ".join(reponse.json()["equipage"]))
        self._titulaire_inchange()

    def test_put_renvoie_400(self):
        reponse = self.api.put(
            self.url, {"role": "ETAT_MAJOR", "ship": self.autre.pk, "equipage": None}, format="json"
        )
        self.assertEqual(reponse.status_code, 400)
        self._titulaire_inchange()

    def test_patch_d_un_non_titulaire_passe(self):
        reponse = self.api.patch(
            f"/api/accounts/profiles/{self.simple.profile.pk}/", {"equipage": self.rouge.pk}, format="json"
        )
        self.assertEqual(reponse.status_code, 200)
        self.simple.profile.refresh_from_db()
        self.assertEqual(self.simple.profile.equipage, self.rouge)
