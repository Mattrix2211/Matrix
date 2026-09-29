"""Double équipage, tranche 3 : organisation en miroir par équipage, duplication
d'un équipage vers l'autre, duplication de navire et rétrocompatibilité des
navires à équipage unique."""
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import AuditLog, UserProfile
from org.models import CommandantAdjoint, Equipage, Section, Sector, Service, Ship


def creer_utilisateur(username, role, ship, equipage=None, superuser=False):
    user = User.objects.create_user(username=username, password="pass", is_superuser=superuser)
    UserProfile.objects.update_or_create(user=user, defaults={"role": role, "ship": ship, "equipage": equipage})
    return User.objects.get(pk=user.pk)


class OrganisationMiroirBase(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="FREMM A", code="FA", classe_navire="FREMM", capacite_aviation=True)
        self.commandant = creer_utilisateur("cdt", "COMMANDANT", self.navire)
        self.client.force_login(self.commandant)

    def activer(self):
        self.client.post("/equipages/", {"action": "activer_double_equipage", "ship_id": self.navire.pk})
        self.navire.refresh_from_db()
        self.bleu = self.navire.equipages.get(nom="Bleu")
        self.rouge = self.navire.equipages.get(nom="Rouge")

    def construire_organisation(self, equipage):
        coma = CommandantAdjoint.objects.create(ship=self.navire, equipage=equipage, sigle="COMOPS")
        service = Service.objects.create(ship=self.navire, equipage=equipage, name="Énergie", commandant_adjoint=coma)
        secteur = Sector.objects.create(service=service, equipage=equipage, name="Propulsion", color="#123456")
        Section.objects.create(sector=secteur, equipage=equipage, name="Diesel")


class UniciteTests(OrganisationMiroirBase):
    def test_meme_nom_de_service_dans_les_deux_equipages(self):
        bleu = Equipage.objects.create(ship=self.navire, nom="Bleu")
        rouge = Equipage.objects.create(ship=self.navire, nom="Rouge")
        Service.objects.create(ship=self.navire, equipage=bleu, name="Énergie")
        Service.objects.create(ship=self.navire, equipage=rouge, name="Énergie")
        CommandantAdjoint.objects.create(ship=self.navire, equipage=bleu, sigle="COMAEQ")
        CommandantAdjoint.objects.create(ship=self.navire, equipage=rouge, sigle="COMAEQ")

    def test_equipage_unique_reste_unique(self):
        Service.objects.create(ship=self.navire, name="Énergie")
        CommandantAdjoint.objects.create(ship=self.navire, sigle="COMAEQ")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Service.objects.create(ship=self.navire, name="Énergie")
        with self.assertRaises(IntegrityError), transaction.atomic():
            CommandantAdjoint.objects.create(ship=self.navire, sigle="COMAEQ")

    def test_doublon_dans_un_meme_equipage_refuse(self):
        bleu = Equipage.objects.create(ship=self.navire, nom="Bleu")
        Service.objects.create(ship=self.navire, equipage=bleu, name="Énergie")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Service.objects.create(ship=self.navire, equipage=bleu, name="Énergie")


class ActivationEtDuplicationTests(OrganisationMiroirBase):
    def test_activation_rattache_l_organisation_existante_a_l_equipage_a_bord(self):
        self.construire_organisation(None)
        self.activer()
        for modele in (CommandantAdjoint, Service, Sector, Section):
            self.assertFalse(modele.objects.filter(equipage__isnull=True).exists(), modele)
        self.assertEqual(Service.objects.get().equipage, self.navire.equipage_a_bord)

    def test_duplication_miroir_en_un_clic(self):
        self.construire_organisation(None)
        self.activer()
        reponse = self.client.post("/equipages/", {
            "action": "dupliquer_organisation",
            "source_id": self.navire.equipage_a_bord.pk,
            "destination_id": self.rouge.pk if self.navire.equipage_a_bord == self.bleu else self.bleu.pk,
        })
        self.assertEqual(reponse.status_code, 302)
        autre = self.rouge if self.navire.equipage_a_bord == self.bleu else self.bleu
        service = Service.objects.get(equipage=autre)
        self.assertEqual(service.name, "Énergie")
        self.assertEqual(service.commandant_adjoint.equipage, autre)
        self.assertIsNone(service.commandant_adjoint.titulaire)
        secteur = service.sectors.get()
        self.assertEqual((secteur.color, secteur.equipage), ("#123456", autre))
        self.assertEqual(secteur.sections.get().equipage, autre)
        self.assertEqual(Service.objects.count(), 2)
        self.assertTrue(AuditLog.objects.filter(action="dupliquer_organisation_equipage", actor=self.commandant).exists())

    def test_duplication_idempotente(self):
        self.activer()
        self.construire_organisation(self.bleu)
        donnees = {"action": "dupliquer_organisation", "source_id": self.bleu.pk, "destination_id": self.rouge.pk}
        self.client.post("/equipages/", donnees)
        self.client.post("/equipages/", donnees)
        self.assertEqual(Service.objects.filter(equipage=self.rouge).count(), 1)
        self.assertEqual(CommandantAdjoint.objects.filter(equipage=self.rouge).count(), 1)

    def test_duplication_refusee_meme_equipage_ou_equipage_d_un_autre_navire(self):
        self.activer()
        autre_navire = Ship.objects.create(name="FREMM B", code="FB", classe_navire="FREMM", double_equipage=True)
        etranger = Equipage.objects.create(ship=autre_navire, nom="Vert")
        self.construire_organisation(self.bleu)
        for destination in (self.bleu.pk, etranger.pk):
            self.client.post("/equipages/", {
                "action": "dupliquer_organisation", "source_id": self.bleu.pk, "destination_id": destination,
            })
        self.assertEqual(Service.objects.count(), 1)

    def test_droit_de_gestion_requis(self):
        self.activer()
        chef = creer_utilisateur("chef", "CHEF_SERVICE", self.navire)
        self.client.force_login(chef)
        reponse = self.client.post("/equipages/", {"action": "dupliquer_organisation"})
        self.assertEqual(reponse.status_code, 403)

    def test_duplication_refusee_a_l_equipage_a_terre(self):
        self.construire_organisation(None)
        self.activer()
        a_bord = self.navire.equipage_a_bord
        a_terre = self.rouge if a_bord == self.bleu else self.bleu
        commandant_terre = creer_utilisateur("cdt_terre", "COMMANDANT", self.navire, a_terre)
        self.client.force_login(commandant_terre)
        self.client.post("/equipages/", {
            "action": "dupliquer_organisation", "source_id": a_bord.pk, "destination_id": a_terre.pk,
        })
        self.assertEqual(Service.objects.count(), 1)
        self.assertFalse(AuditLog.objects.filter(action="dupliquer_organisation_equipage").exists())


class DuplicationNavireTests(OrganisationMiroirBase):
    def setUp(self):
        super().setUp()
        self.admin = creer_utilisateur("root", "MASTER_ADMIN", None, superuser=True)
        self.client.force_login(self.admin)

    def test_la_duplication_de_navire_reprend_les_equipages_et_leur_organisation(self):
        self.activer()
        self.construire_organisation(self.bleu)
        self.construire_organisation(self.rouge)
        self.client.post("/parametre/", {
            "action": "duplicate_ship", "source_pk": self.navire.pk, "name": "FREMM C", "code": "FC",
        })
        copie = Ship.objects.get(code="FC")
        self.assertTrue(copie.double_equipage)
        self.assertEqual(sorted(copie.equipages.values_list("nom", flat=True)), ["Bleu", "Rouge"])
        self.assertEqual(copie.equipage_a_bord.nom, self.navire.equipage_a_bord.nom)
        for equipage in copie.equipages.all():
            service = Service.objects.get(ship=copie, equipage=equipage)
            self.assertEqual(service.commandant_adjoint.equipage, equipage)
            self.assertEqual(service.sectors.get().sections.get().equipage, equipage)

    def test_navire_a_equipage_unique_duplique_sans_equipage(self):
        self.construire_organisation(None)
        self.client.post("/parametre/", {
            "action": "duplicate_ship", "source_pk": self.navire.pk, "name": "FREMM D", "code": "FD",
        })
        copie = Ship.objects.get(code="FD")
        self.assertFalse(copie.double_equipage)
        self.assertFalse(copie.equipages.exists())
        service = Service.objects.get(ship=copie)
        self.assertIsNone(service.equipage)
        self.assertIsNone(service.commandant_adjoint.equipage)


class ComaParEquipageTests(OrganisationMiroirBase):
    def poster(self, **donnees):
        return self.client.post("/parametre/?tab=commandants_adjoints", donnees)

    def test_un_meme_sigle_par_equipage(self):
        self.activer()
        for equipage in (self.bleu, self.rouge):
            self.poster(action="add_commandant_adjoint", sigle="COMAEQ", equipage_id=equipage.pk)
        self.assertEqual(CommandantAdjoint.objects.filter(sigle="COMAEQ").count(), 2)

    def test_equipage_obligatoire_en_double_equipage(self):
        self.activer()
        self.poster(action="add_commandant_adjoint", sigle="COMAEQ")
        self.assertFalse(CommandantAdjoint.objects.exists())

    def test_service_rattache_seulement_au_poste_de_son_equipage(self):
        self.activer()
        poste_rouge = CommandantAdjoint.objects.create(ship=self.navire, equipage=self.rouge, sigle="COMOPS")
        service_bleu = Service.objects.create(ship=self.navire, equipage=self.bleu, name="Énergie")
        self.poster(action="set_service_commandant_adjoint", service_id=service_bleu.pk, coma_id=poste_rouge.pk)
        service_bleu.refresh_from_db()
        self.assertIsNone(service_bleu.commandant_adjoint)

    def test_navire_a_equipage_unique_inchange(self):
        self.poster(action="add_commandant_adjoint", sigle="COMAEQ")
        poste = CommandantAdjoint.objects.get()
        self.assertIsNone(poste.equipage)
        service = Service.objects.create(ship=self.navire, name="Énergie")
        self.poster(action="set_service_commandant_adjoint", service_id=service.pk, coma_id=poste.pk)
        service.refresh_from_db()
        self.assertEqual(service.commandant_adjoint, poste)


class CreationServiceEquipageTests(OrganisationMiroirBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(creer_utilisateur("tech", "MASTER_ADMIN", self.navire, superuser=True))

    def poster_service(self, **extra):
        return self.client.post(
            "/parametre/",
            {"action": "add_service", "name": "Énergie", "ship_id": self.navire.pk, "next_tab": "hierarchie", **extra},
        )

    def test_double_equipage_sans_equipage_refuse(self):
        self.activer()
        self.poster_service()
        self.poster_service(equipage_id=99999)
        self.assertFalse(Service.objects.filter(ship=self.navire).exists())

    def test_double_equipage_avec_equipage_cree_le_service(self):
        self.activer()
        self.poster_service(equipage_id=self.bleu.pk)
        self.assertEqual(Service.objects.get(ship=self.navire).equipage, self.bleu)

    def test_equipage_unique_creation_inchangee(self):
        self.poster_service()
        service = Service.objects.get(ship=self.navire)
        self.assertIsNone(service.equipage)


class CreationApiEquipageTests(OrganisationMiroirBase):
    def test_api_service_double_equipage_sans_equipage_refuse(self):
        self.activer()
        r = self.client.post("/api/org/services/", {"ship": self.navire.pk, "name": "Énergie"})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Service.objects.filter(ship=self.navire).exists())

    def test_api_service_equipage_unique_inchange(self):
        r = self.client.post("/api/org/services/", {"ship": self.navire.pk, "name": "Énergie"})
        self.assertEqual(r.status_code, 201)

    def test_api_secteur_et_section_heritent_de_l_equipage(self):
        self.activer()
        service = Service.objects.create(ship=self.navire, equipage=self.rouge, name="Énergie")
        r = self.client.post("/api/org/sectors/", {"service": service.pk, "name": "Propulsion"})
        self.assertEqual(r.status_code, 201, r.content)
        secteur = Sector.objects.get(service=service)
        self.assertEqual(secteur.equipage, self.rouge)
        r = self.client.post("/api/org/sections/", {"sector": secteur.pk, "name": "Diesel"})
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Section.objects.get(sector=secteur).equipage, self.rouge)
