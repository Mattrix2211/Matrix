"""Double équipage : cohérence des équipages, garantie au niveau modèle,
administration Django et API (décisions Matrix du 30/09/2026).

- le titulaire d'un poste COMAEQ/COMOPS/COMANAV/COMAVIA appartient à l'équipage
  du poste (ni sans équipage, ni de l'autre équipage) ;
- le changement d'équipage d'un service est atomique sur Service -> Secteurs ->
  Sections, et bloqué avec le détail des postes et affectations à corriger."""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import UserProfile
from org.models import CommandantAdjoint, Equipage, Section, Sector, Service, Ship


def creer_marin(username, role, ship, equipage=None, **rattachement):
    user = User.objects.create_user(username=username, password="pass")
    UserProfile.objects.update_or_create(
        user=user, defaults={"role": role, "ship": ship, "equipage": equipage, **rattachement}
    )
    return User.objects.get(pk=user.pk)


class BaseDoubleEquipage(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="FREMM Cohérence", code="FCO", classe_navire="FREMM", double_equipage=True)
        self.bleu = Equipage.objects.create(ship=self.ship, nom="Bleu")
        self.rouge = Equipage.objects.create(ship=self.ship, nom="Rouge")
        self.ship.equipage_a_bord = self.bleu
        self.ship.save()


class TitulaireComaModeleTests(BaseDoubleEquipage):
    def _poste(self, titulaire):
        return CommandantAdjoint(ship=self.ship, equipage=self.bleu, sigle="COMAEQ", titulaire=titulaire)

    def test_clean_refuse_un_marin_sans_equipage(self):
        poste = self._poste(creer_marin("sans", "ETAT_MAJOR", self.ship))
        with self.assertRaises(ValidationError) as ctx:
            poste.clean()
        self.assertIn("aucun équipage", ctx.exception.message_dict["titulaire"][0])

    def test_clean_refuse_un_marin_de_l_autre_equipage(self):
        poste = self._poste(creer_marin("rouge", "ETAT_MAJOR", self.ship, self.rouge))
        with self.assertRaises(ValidationError) as ctx:
            poste.clean()
        self.assertIn("autre équipage", ctx.exception.message_dict["titulaire"][0])

    def test_clean_accepte_un_marin_du_bon_equipage_ou_un_poste_vacant(self):
        self._poste(creer_marin("bleu", "ETAT_MAJOR", self.ship, self.bleu)).clean()
        self._poste(None).clean()

    def test_save_refuse_aussi_hors_formulaire(self):
        sans = creer_marin("sans2", "ETAT_MAJOR", self.ship)
        with self.assertRaises(ValidationError):
            CommandantAdjoint.objects.create(ship=self.ship, equipage=self.bleu, sigle="COMOPS", titulaire=sans)
        poste = CommandantAdjoint.objects.create(ship=self.ship, equipage=self.bleu, sigle="COMOPS")
        poste.titulaire = sans
        with self.assertRaises(ValidationError):
            poste.save()
        poste.refresh_from_db()
        self.assertIsNone(poste.titulaire)

    def test_titulaire_deja_en_place_non_bloque_une_sauvegarde_partielle(self):
        sans = creer_marin("ancien", "ETAT_MAJOR", self.ship)
        poste = CommandantAdjoint.objects.create(ship=self.ship, equipage=self.bleu, sigle="COMOPS")
        CommandantAdjoint.objects.filter(pk=poste.pk).update(titulaire=sans)
        poste.refresh_from_db()
        poste.save(update_fields=["updated_at"])

    def test_equipage_unique_inchange(self):
        unique = Ship.objects.create(name="BRF Coh", code="BCO")
        marin = creer_marin("unique", "ETAT_MAJOR", unique)
        CommandantAdjoint.objects.create(ship=unique, sigle="COMAEQ", titulaire=marin)

    def test_equipage_d_une_autre_unite_refuse(self):
        autre = Ship.objects.create(name="FREMM Autre", code="FAU", classe_navire="FREMM", double_equipage=True)
        equipage_etranger = Equipage.objects.create(ship=autre, nom="Bleu")
        poste = CommandantAdjoint(ship=self.ship, equipage=equipage_etranger, sigle="COMAEQ")
        with self.assertRaises(ValidationError):
            poste.clean()


class TitulaireComaAdminTests(BaseDoubleEquipage):
    def setUp(self):
        super().setUp()
        self.admin = creer_marin("root", "MASTER_ADMIN", None)
        self.admin.is_staff = self.admin.is_superuser = True
        self.admin.save()
        self.client.force_login(self.admin)
        self.poste = CommandantAdjoint.objects.create(ship=self.ship, equipage=self.bleu, sigle="COMAEQ")

    def _envoyer(self, titulaire):
        return self.client.post(f"/admin/org/commandantadjoint/{self.poste.pk}/change/", {
            "ship": self.ship.pk, "sigle": "COMAEQ", "titulaire": titulaire.pk, "equipage": self.bleu.pk,
        })

    def test_admin_refuse_un_titulaire_sans_equipage(self):
        reponse = self._envoyer(creer_marin("sans_adm", "ETAT_MAJOR", self.ship))
        self.assertContains(reponse, "rattachez-le d&#x27;abord")
        self.poste.refresh_from_db()
        self.assertIsNone(self.poste.titulaire)

    def test_admin_refuse_un_titulaire_de_l_autre_equipage(self):
        reponse = self._envoyer(creer_marin("rouge_adm", "ETAT_MAJOR", self.ship, self.rouge))
        self.assertContains(reponse, "autre équipage")
        self.poste.refresh_from_db()
        self.assertIsNone(self.poste.titulaire)

    def test_admin_accepte_le_bon_equipage(self):
        titulaire = creer_marin("bleu_adm", "ETAT_MAJOR", self.ship, self.bleu)
        self.assertEqual(self._envoyer(titulaire).status_code, 302)
        self.poste.refresh_from_db()
        self.assertEqual(self.poste.titulaire, titulaire)


class BaseBranche(BaseDoubleEquipage):
    def setUp(self):
        super().setUp()
        self.service = Service.objects.create(ship=self.ship, equipage=self.bleu, name="Énergie")
        self.secteur = Sector.objects.create(service=self.service, equipage=self.bleu, name="Propulsion")
        self.section = Section.objects.create(sector=self.secteur, equipage=self.bleu, name="Diesel")
        self.commandant = creer_marin("cdt", "COMMANDANT", self.ship, self.bleu)
        self.client.force_login(self.commandant)

    def _equipages(self):
        for objet in (self.service, self.secteur, self.section):
            objet.refresh_from_db()
        return [objet.equipage for objet in (self.service, self.secteur, self.section)]


class ChangementEquipageServiceTests(BaseBranche):
    def _api(self, methode="patch", **donnees):
        return getattr(self.client, methode)(
            f"/api/org/services/{self.service.pk}/", donnees, content_type="application/json"
        )

    def test_changement_sans_conflit_propage_a_toute_la_branche(self):
        reponse = self._api(equipage=self.rouge.pk)
        self.assertEqual(reponse.status_code, 200, reponse.content)
        self.assertEqual(self._equipages(), [self.rouge] * 3)

    def test_put_complet_propage_aussi(self):
        reponse = self._api("put", ship=self.ship.pk, name="Énergie", equipage=self.rouge.pk)
        self.assertEqual(reponse.status_code, 200, reponse.content)
        self.assertEqual(self._equipages(), [self.rouge] * 3)

    def test_un_marin_de_l_autre_equipage_affecte_bloque_et_est_nomme(self):
        creer_marin("chef_sect", "CHEF_SECTEUR", self.ship, self.bleu, sector=self.secteur)
        reponse = self._api(equipage=self.rouge.pk)
        self.assertEqual(reponse.status_code, 400)
        message = " ".join(reponse.json()["equipage"])
        self.assertIn("chef_sect", message)
        self.assertIn("le secteur « Propulsion »", message)
        self.assertEqual(self._equipages(), [self.bleu] * 3)

    def test_marin_d_une_section_bloque_et_section_nommee(self):
        creer_marin("opé", "EQUIPIER", self.ship, self.bleu, section=self.section)
        reponse = self._api(equipage=self.rouge.pk)
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("la section « Diesel »", " ".join(reponse.json()["equipage"]))

    def test_marin_sans_equipage_ne_bloque_pas(self):
        creer_marin("libre", "EQUIPIER", self.ship, None, section=self.section)
        self.assertEqual(self._api(equipage=self.rouge.pk).status_code, 200)

    def test_marin_du_nouvel_equipage_ne_bloque_pas(self):
        creer_marin("rouge_sect", "CHEF_SECTEUR", self.ship, self.rouge, sector=self.secteur)
        self.assertEqual(self._api(equipage=self.rouge.pk).status_code, 200)

    def test_poste_coma_de_l_ancien_equipage_bloque(self):
        coma = CommandantAdjoint.objects.create(ship=self.ship, equipage=self.bleu, sigle="COMOPS")
        self.service.commandant_adjoint = coma
        self.service.save()
        reponse = self._api(equipage=self.rouge.pk)
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("COMOPS", " ".join(reponse.json()["equipage"]))
        self.assertEqual(self._equipages(), [self.bleu] * 3)

    def test_changement_avec_poste_du_nouvel_equipage_passe(self):
        coma = CommandantAdjoint.objects.create(ship=self.ship, equipage=self.rouge, sigle="COMOPS")
        reponse = self._api(equipage=self.rouge.pk, commandant_adjoint=coma.pk)
        self.assertEqual(reponse.status_code, 200, reponse.content)

    def test_poste_d_un_autre_equipage_refuse_sans_changer_d_equipage(self):
        coma = CommandantAdjoint.objects.create(ship=self.ship, equipage=self.rouge, sigle="COMOPS")
        reponse = self._api(commandant_adjoint=coma.pk)
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("même équipage", " ".join(reponse.json()["commandant_adjoint"]))

    def test_nom_deja_pris_dans_l_equipage_d_arrivee_bloque(self):
        Service.objects.create(ship=self.ship, equipage=self.rouge, name="Énergie")
        self.assertEqual(self._api(equipage=self.rouge.pk).status_code, 400)
        self.service.equipage = self.rouge
        with self.assertRaises(ValidationError) as ctx:
            self.service.clean()
        self.assertIn("existe déjà", " ".join(ctx.exception.message_dict["equipage"]))
        self.assertEqual(self._equipages(), [self.bleu] * 3)

    def test_modele_atomique_et_bloquant_hors_api(self):
        creer_marin("chef_sect2", "CHEF_SECTEUR", self.ship, self.bleu, sector=self.secteur)
        self.service.equipage = self.rouge
        with self.assertRaises(ValidationError):
            self.service.save()
        self.assertEqual(self._equipages(), [self.bleu] * 3)

    def test_modele_sans_conflit_propage(self):
        self.service.equipage = self.rouge
        self.service.save()
        self.assertEqual(self._equipages(), [self.rouge] * 3)

    def test_sauvegarde_partielle_sans_equipage_ne_propage_pas(self):
        self.service.name = "Énergie 2"
        self.service.save(update_fields=["name", "updated_at"])
        self.assertEqual(self._equipages(), [self.bleu] * 3)


class ChangementEquipageAdminTests(BaseBranche):
    def setUp(self):
        super().setUp()
        admin = creer_marin("root", "MASTER_ADMIN", None)
        admin.is_staff = admin.is_superuser = True
        admin.save()
        self.client.force_login(admin)

    def _formulaire(self, equipage):
        return self.client.post(f"/admin/org/service/{self.service.pk}/change/", {
            "ship": self.ship.pk, "name": "Énergie", "equipage": equipage.pk,
        })

    def test_admin_bloque_et_indique_l_affectation(self):
        creer_marin("chef_adm", "CHEF_SECTEUR", self.ship, self.bleu, sector=self.secteur)
        reponse = self._formulaire(self.rouge)
        self.assertContains(reponse, "chef_adm")
        self.assertEqual(self._equipages(), [self.bleu] * 3)

    def test_admin_sans_conflit_propage(self):
        self.assertEqual(self._formulaire(self.rouge).status_code, 302)
        self.assertEqual(self._equipages(), [self.rouge] * 3)
