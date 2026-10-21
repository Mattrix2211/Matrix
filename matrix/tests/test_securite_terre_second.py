"""Soutien à terre et commandant en second : consultation, commentaire, modification, validation.

Le soutien à terre (sans bâtiment : responsables de classe et de spécialité) consulte et commente ; il ne
modifie pas les données du bord. Le commandant en second a une vision transverse, mais ses écritures
viennent de workflows explicites (programme du bâtiment, visas, relève), pas de son grade.
Comptes et données de seed_demo."""
import json
from io import StringIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection
from django.db.models import Q
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from absences.models import Absence
from accounts.models import ResponsableSpecialite, TypeAbsence, UserProfile
from assets.models import ArticleCatalogue, Asset, CategorieCatalogue, ChecklistTemplate, Installation, InstallationMaintenance
from demandes.models import Demande
from logistics.models import Anomalie, CorrectiveTicket, StockPiece
from maintenance.models import MaintenanceOccurrence
from matrix.core.fuseau import champ_local
from matrix.core.roles import RoleLevel, niveau_ecriture, user_role_level
from matrix.core.scopes import soutien_a_terre
from org.models import ReleveEquipage, Ship
from programme.models import EvenementProgramme, TypeProgramme
from taches.models import Tache
from threads.models import Message, Thread

SOUTIEN = ["terre_classe", "terre_securite", "terre_chef_securite"]
TABLES_IGNOREES = {"django_session"}


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())
        cls.bre = Ship.objects.get(code="BRE")
        cls.equipier = User.objects.get(username="equipier_a")
        cls.equipier2 = User.objects.get(username="equipier_a2")
        cls.chef_section = User.objects.get(username="chef_section_a")
        cls.tache_ouverte = Tache.objects.get(titre__startswith="Contrôler le graissage")
        cls.tache_bloquee = Tache.objects.get(statut="BLOQUEE")
        cls.demande = Demande.objects.get()
        cls.ticket = CorrectiveTicket.objects.filter(Q(asset__ship=cls.bre) | Q(installation__ship=cls.bre), status="REPORTED").order_by("description").first()
        cls.anomalie = Anomalie.objects.filter(statut="SIGNALEE").order_by("pk").first()
        cls.piece = StockPiece.objects.filter(ship=cls.bre).order_by("pk").first()
        cls.materiel = Asset.objects.filter(ship=cls.bre).order_by("internal_id").first()
        cls.installation = Installation.objects.get(designation="Pompe de graissage")
        cls.occurrence = MaintenanceOccurrence.objects.filter(status="PLANNED").order_by("pk").first()
        cls.type_absence = TypeAbsence.objects.order_by("pk").first()

    def client_de(self, compte):
        client = Client()
        client.force_login(User.objects.get(username=compte))
        return client

    def etat(self):
        """Empreinte de toutes les tables métier, journal d'audit et notifications compris."""
        empreinte = {}
        with connection.cursor() as curseur:
            for table in connection.introspection.table_names():
                if table in TABLES_IGNOREES:
                    continue
                curseur.execute(f'SELECT * FROM "{table}"')
                empreinte[table] = sorted(map(repr, curseur.fetchall()))
        return empreinte

    def envoyer(self, client, methode, url, donnees=None):
        if methode in ("patch", "put"):
            return getattr(client, methode)(url, data=json.dumps(donnees), content_type="application/json")
        if methode == "delete":
            return client.delete(url)
        return getattr(client, methode)(url, donnees or {})

    @staticmethod
    def fichier():
        return SimpleUploadedFile("note.pdf", b"%PDF-1.4 essai", "application/pdf")

    def requetes_web(self):
        """Écritures du bord par écran : (nom, URL, données)."""
        return [
            ("créer une tâche pour un marin", "/taches/", {"assigne": self.equipier.pk, "titre": "Intrus"}),
            ("reprendre une tâche bloquée", f"/taches/{self.tache_bloquee.pk}/action/", {"action": "reprendre"}),
            ("réaffecter une tâche", f"/taches/{self.tache_ouverte.pk}/action/",
             {"action": "modifier", "assigne": self.equipier2.pk, "echeance": "", "priorite": "NORMALE"}),
            ("joindre un fichier à une tâche", f"/taches/{self.tache_ouverte.pk}/action/",
             {"action": "joindre", "fichier": self.fichier()}),
            ("ajouter un interlocuteur à une tâche", f"/taches/{self.tache_ouverte.pk}/action/",
             {"action": "interlocuteur", "interlocuteur": self.equipier2.pk}),
            ("réaffecter une demande", f"/demandes/{self.demande.pk}/action/",
             {"action": "reaffecter", "responsable": User.objects.get(username="chef_service_a").pk}),
            ("créer une action sur une demande", f"/demandes/{self.demande.pk}/action/",
             {"action": "creer_action", "titre": "Action", "assigne": self.equipier2.pk}),
            ("ajouter un interlocuteur à une demande", f"/demandes/{self.demande.pk}/action/",
             {"action": "interlocuteur", "interlocuteur": self.equipier2.pk}),
            ("transition de ticket", f"/logistics/tickets/{self.ticket.pk}/transition/", {"status": "IN_REPAIR"}),
            ("assigner un ticket", f"/logistics/tickets/{self.ticket.pk}/assign/", {"assignees": [self.equipier.pk]}),
            ("demande de pièces", f"/logistics/tickets/{self.ticket.pk}/part-request/create/", {}),
            ("statut d'anomalie", f"/logistics/anomalies/{self.anomalie.pk}/statut/", {"statut": "PRISE_EN_COMPTE"}),
            ("mouvement de stock", f"/logistics/stock/{self.piece.pk}/mouvements/", {"type": "ENTREE", "quantite": "5"}),
            ("absence validée d'office pour un marin", "/absences/",
             {"action": "declarer", "marin_id": self.equipier.pk, "type_absence": self.type_absence.pk,
              "date_debut": "2026-11-02", "date_fin": "2026-11-03"}),
            ("document d'installation", f"/installations/{self.installation.pk}/documents/ajouter/",
             {"titre": "Doc", "type_document": "AUTRE", "fichier": self.fichier()}),
        ]

    def requetes_api(self):
        """Écritures de l'API : (nom, méthode, URL, données)."""
        return [
            ("PATCH matériel", "patch", f"/api/assets/assets/{self.materiel.pk}/", {"designation": "Piraté"}),
            ("DELETE matériel", "delete", f"/api/assets/assets/{self.materiel.pk}/", None),
            ("PATCH ticket", "patch", f"/api/logistics/tickets/{self.ticket.pk}/", {"description": "Piraté"}),
            ("PATCH occurrence", "patch", f"/api/maintenance/occurrences/{self.occurrence.pk}/", {"priority": 1}),
            ("transition de ticket par l'API", "post", f"/api/logistics/tickets/{self.ticket.pk}/transition/", {"status": "IN_REPAIR"}),
            ("demande de pièces par l'API", "post", "/api/logistics/part-requests/", {"ticket": str(self.ticket.pk)}),
            ("POST fil de discussion", "post", "/api/threads/threads/", {"content_type": 1, "object_id": "1"}),
        ]


class DefinitionTests(Base):
    def test_soutien_a_terre_est_defini_en_un_seul_point(self):
        for compte in SOUTIEN:
            utilisateur = User.objects.get(username=compte)
            self.assertTrue(soutien_a_terre(utilisateur), compte)
            self.assertGreaterEqual(user_role_level(utilisateur), RoleLevel.CHEF_SERVICE)
            self.assertEqual(niveau_ecriture(utilisateur), RoleLevel.EQUIPIER, compte)
        for compte in ("cdt_a", "chef_section_a", "equipier_a", "second_a", "admin_navire", "marin_b"):
            self.assertFalse(soutien_a_terre(User.objects.get(username=compte)), compte)

    def test_sans_batiment_ni_responsabilite_ce_n_est_pas_du_soutien(self):
        isole = User.objects.create_user(username="isole", password="pass")
        isole.profile.role = "CHEF_SERVICE"
        isole.profile.save()
        isole = User.objects.get(pk=isole.pk)
        self.assertFalse(soutien_a_terre(isole))
        self.assertEqual(niveau_ecriture(isole), RoleLevel.CHEF_SERVICE)

    def test_administrateur_general_n_est_pas_du_soutien(self):
        admin = User.objects.get(username="admin")
        self.assertFalse(soutien_a_terre(admin))
        self.assertEqual(niveau_ecriture(admin), RoleLevel.MASTER_ADMIN)

    def test_le_second_garde_sa_vision_mais_pas_ses_ecritures_heritees(self):
        second = User.objects.get(username="second_a")
        self.assertEqual(user_role_level(second), RoleLevel.COMMANDANT_EN_SECOND)
        self.assertEqual(niveau_ecriture(second), RoleLevel.EQUIPIER)
        for compte, niveau in (("cdt_a", RoleLevel.COMMANDANT), ("chef_service_a", RoleLevel.CHEF_SERVICE),
                               ("chef_section_a", RoleLevel.CHEF_SECTION), ("equipier_a", RoleLevel.EQUIPIER),
                               ("admin_navire", RoleLevel.ADMIN_NAVIRE)):
            self.assertEqual(niveau_ecriture(User.objects.get(username=compte)), niveau, compte)


class SoutienATerreTests(Base):
    """F4 : les requêtes exactes du rapport sont refusées, l'état du bord ne bouge pas."""

    def test_aucune_ecriture_web_sur_les_donnees_du_bord(self):
        for compte in SOUTIEN:
            client = self.client_de(compte)
            for nom, url, donnees in self.requetes_web():
                avant = self.etat()
                reponse = client.post(url, donnees)
                self.assertEqual(reponse.status_code, 403, f"{compte} : {nom}")
                self.assertEqual(self.etat(), avant, f"{compte} : {nom}")

    def test_aucune_ecriture_api_sur_les_donnees_du_bord(self):
        for compte in SOUTIEN:
            client = self.client_de(compte)
            for nom, methode, url, donnees in self.requetes_api():
                avant = self.etat()
                reponse = self.envoyer(client, methode, url, donnees)
                self.assertEqual(reponse.status_code, 403, f"{compte} : {nom}")
                self.assertEqual(self.etat(), avant, f"{compte} : {nom}")

    def test_ecritures_personnelles_du_bord_fermees_aussi(self):
        client = self.client_de("terre_classe")
        for nom, url, donnees in [
            ("tâche personnelle", "/taches/", {"titre": "Perso"}),
            ("absence propre", "/absences/", {"action": "declarer", "type_absence": self.type_absence.pk,
                                              "date_debut": "2026-11-09", "date_fin": "2026-11-10"}),
            ("auto-affectation à une maintenance", f"/maintenance/occurrences/{self.occurrence.pk}/assigner/", {}),
            ("signalement libre", "/logistics/anomalies/signaler/", {}),
            ("exécution d'une maintenance", f"/maintenance/occurrences/{self.occurrence.pk}/execute/", {}),
        ]:
            avant = self.etat()
            self.assertEqual(client.post(url, donnees).status_code, 403, nom)
            self.assertEqual(self.etat(), avant, nom)
        self.assertFalse(Absence.objects.filter(marin__username="terre_classe").exists())

    def test_programme_et_reglages_du_batiment_refuses(self):
        client = self.client_de("terre_classe")
        type_programme = TypeProgramme.objects.filter(ship=self.bre).first()
        avant = self.etat()
        reponse = client.post("/programme/nouveau/", {
            "titre": "Escale", "type": type_programme.pk if type_programme else "", "debut": "2030-01-10T08:00",
            "cible": f"ship:{self.bre.pk}"})
        self.assertEqual(reponse.status_code, 403)
        self.assertEqual(client.post("/parametre/", {"action": "toggle_module"}).status_code, 403)
        self.assertEqual(self.etat(), avant)
        self.assertFalse(EvenementProgramme.objects.filter(titre="Escale").exists())

    def test_commentaires_et_suivi_restent_ouverts(self):
        client = self.client_de("terre_classe")
        for url in (
            f"/demandes/{self.demande.pk}/commentaire/",
            f"/taches/commentaire/{self.tache_ouverte.pk}/",
            f"/logistics/tickets/{self.ticket.pk}/commentaire/",
            f"/logistics/anomalies/{self.anomalie.pk}/commentaire/",
            f"/maintenance/occurrences/{self.occurrence.pk}/commentaire/",
        ):
            avant = Message.objects.count()
            reponse = client.post(url, {"body": "Bien reçu, je lance la recherche côté terre."})
            self.assertEqual(reponse.status_code, 302, url)
            self.assertEqual(Message.objects.count(), avant + 1, url)
            self.assertTrue(Message.objects.filter(author__username="terre_classe").order_by("-pk").first().body.startswith("Bien reçu"))

    def test_message_de_fil_par_l_api_reste_ouvert_mais_pas_la_creation_de_fil(self):
        client = self.client_de("terre_classe")
        client.post(f"/logistics/tickets/{self.ticket.pk}/commentaire/", {"body": "Premier message"})
        fil = Thread.objects.get(object_id=str(self.ticket.pk))
        reponse = self.envoyer(client, "post", "/api/threads/messages/", {"thread": fil.pk, "body": "Réponse par l'API"})
        self.assertEqual(reponse.status_code, 201)
        nombre = Thread.objects.count()
        self.assertEqual(self.envoyer(client, "post", "/api/threads/threads/", {"content_type": fil.content_type_id, "object_id": "x"}).status_code, 403)
        self.assertEqual(Thread.objects.count(), nombre)

    def test_consultation_et_tableaux_de_bord_de_classe_et_de_specialite(self):
        client = self.client_de("terre_classe")
        for url in ("/", "/taches/", f"/taches/{self.tache_ouverte.pk}/", "/demandes/", f"/demandes/{self.demande.pk}/",
                    f"/logistics/tickets/{self.ticket.pk}/", "/logistics/stock/", "/maintenance/gestion/occurrences/",
                    "/dashboard/flotte/", reverse("dashboard-classe-navire", args=["FREMM"])):
            self.assertEqual(client.get(url).status_code, 200, url)
        specialite = ResponsableSpecialite.objects.get(user__username="terre_securite").specialite
        self.assertEqual(self.client_de("terre_securite").get(reverse("dashboard-specialite", args=[specialite.pk])).status_code, 200)

    def test_formulaires_d_ecriture_masques_sur_tache_et_demande(self):
        client = self.client_de("terre_classe")
        page = client.get(f"/taches/{self.tache_ouverte.pk}/").content.decode()
        for interdit in ("Réaffecter ou replanifier", "Ajouter un interlocuteur au fil", "Joindre", "Proposer un RETEX",
                         "Signaler une difficulté"):
            self.assertNotIn(interdit, page, interdit)
        self.assertIn("Répondre dans le fil", page)
        self.assertIn("Soutien à terre", page)
        page = client.get(f"/demandes/{self.demande.pk}/").content.decode()
        for interdit in ("Assigner une action", "Ajouter un interlocuteur", "Confier à un autre responsable", "Proposer un RETEX"):
            self.assertNotIn(interdit, page, interdit)
        self.assertIn("Répondre", page)

    def test_circuit_du_catalogue_flotte_pour_le_responsable_de_specialite(self):
        client = self.client_de("terre_securite")
        specialite = ResponsableSpecialite.objects.get(user__username="terre_securite").specialite
        reponse = client.post("/catalogue/categories/nouvelle/", {"nom": "Détection", "specialite": specialite.pk, "ordre": 1})
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(CategorieCatalogue.objects.filter(nom="Détection").exists())

    def test_ecritures_personnelles_et_de_session_restent_ouvertes(self):
        client = self.client_de("terre_classe")
        self.assertEqual(client.post("/users/theme/", {"theme": "sombre"}).status_code, 302)
        self.assertEqual(client.post("/notifications/tout-lu/").status_code, 200)
        self.assertEqual(client.post("/logout/").status_code, 302)


class CommandantEnSecondTests(Base):
    """F7 : vision transverse, mais aucune écriture héritée du grade."""

    def test_aucune_ecriture_web_heritee_du_grade(self):
        client = self.client_de("second_a")
        for nom, url, donnees in self.requetes_web():
            avant = self.etat()
            reponse = client.post(url, donnees)
            self.assertIn(reponse.status_code, (302, 403), nom)
            self.assertEqual(self.etat(), avant, nom)

    def test_aucune_ecriture_api_heritee_du_grade(self):
        client = self.client_de("second_a")
        for nom, methode, url, donnees in self.requetes_api():
            avant = self.etat()
            reponse = self.envoyer(client, methode, url, donnees)
            self.assertEqual(reponse.status_code, 403, nom)
            self.assertEqual(self.etat(), avant, nom)

    def test_la_vision_du_batiment_reste_entiere(self):
        client = self.client_de("second_a")
        for url in ("/taches/", f"/taches/{self.tache_ouverte.pk}/", f"/demandes/{self.demande.pk}/", "/logistics/tickets/?vue=perimetre",
                    f"/logistics/tickets/{self.ticket.pk}/", "/logistics/stock/", "/absences/", "/programme/", "/users/",
                    "/api/assets/assets/", "/api/org/ships/"):
            self.assertEqual(client.get(url).status_code, 200, url)

    def test_formulaires_d_ecriture_masques(self):
        client = self.client_de("second_a")
        page = client.get(f"/taches/{self.tache_ouverte.pk}/").content.decode()
        for interdit in ("Réaffecter ou replanifier", "Ajouter un interlocuteur au fil", "Joindre"):
            self.assertNotIn(interdit, page, interdit)
        page = client.get(f"/demandes/{self.demande.pk}/").content.decode()
        for interdit in ("Assigner une action", "Confier à un autre responsable"):
            self.assertNotIn(interdit, page, interdit)

    def test_un_dossier_n_est_pas_confie_au_second(self):
        from demandes.services import responsables_possibles

        noms = set(responsables_possibles(self.equipier).values_list("username", flat=True))
        self.assertIn("chef_section_a", noms)
        self.assertNotIn("second_a", noms)

    def test_circuits_explicites_conserves(self):
        client = self.client_de("second_a")
        type_programme = TypeProgramme.objects.filter(ship=self.bre).first() or TypeProgramme.objects.create(ship=self.bre, nom="Exercice")
        reponse = client.post("/programme/nouveau/", {
            "titre": "Exercice du second", "type": type_programme.pk, "debut": "2030-01-10T08:00", "cible": f"ship:{self.bre.pk}"})
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(EvenementProgramme.objects.filter(titre="Exercice du second").exists())
        avant = Message.objects.count()
        for url in (f"/demandes/{self.demande.pk}/commentaire/", f"/taches/commentaire/{self.tache_ouverte.pk}/",
                    f"/logistics/tickets/{self.ticket.pk}/commentaire/"):
            self.assertEqual(client.post(url, {"body": "Suivi du second"}).status_code, 302, url)
        self.assertEqual(Message.objects.count(), avant + 3)

    def test_ses_propres_donnees_restent_modifiables(self):
        client = self.client_de("second_a")
        self.assertEqual(client.post("/taches/", {"titre": "Mon rappel"}).status_code, 302)
        self.assertTrue(Tache.objects.filter(titre="Mon rappel", assigne__username="second_a").exists())
        client.post("/absences/", {"action": "declarer", "type_absence": self.type_absence.pk,
                                   "date_debut": "2026-11-09", "date_fin": "2026-11-10"})
        absence = Absence.objects.get(marin__username="second_a")
        self.assertEqual(absence.statut, Absence.STATUT_DECLAREE)


class ChaineEmbarqueeSansRegressionTests(Base):
    """Les rôles de la chaîne embarquée gardent leurs workflows existants."""

    def test_chef_de_section_attribue_suit_et_valide(self):
        client = self.client_de("chef_section_a")
        self.assertEqual(client.post("/taches/", {"assigne": self.equipier.pk, "titre": "Vérifier le graissage"}).status_code, 302)
        self.assertTrue(Tache.objects.filter(titre="Vérifier le graissage", assigne=self.equipier).exists())
        client.post(f"/taches/{self.tache_bloquee.pk}/action/", {"action": "reprendre"})
        self.tache_bloquee.refresh_from_db()
        self.assertEqual(self.tache_bloquee.statut, Tache.STATUT_EN_COURS)
        client.post(f"/demandes/{self.demande.pk}/action/", {"action": "creer_action", "titre": "Remplacer", "assigne": self.equipier.pk})
        self.assertTrue(Tache.objects.filter(titre="Remplacer", demande=self.demande).exists())
        client.post("/absences/", {"action": "declarer", "marin_id": self.equipier.pk, "type_absence": self.type_absence.pk,
                                   "date_debut": "2026-11-02", "date_fin": "2026-11-03"})
        self.assertTrue(Absence.objects.filter(marin=self.equipier, date_debut="2026-11-02", statut=Absence.STATUT_VALIDEE).exists())
        client.post(f"/installations/{self.installation.pk}/documents/ajouter/",
                    {"titre": "Notice", "type_document": "AUTRE", "fichier": self.fichier()})
        self.assertTrue(self.installation.documents.filter(titre="Notice").exists())

    def test_commandant_et_administrateur_d_unite_gardent_leurs_ecritures(self):
        for compte in ("cdt_a", "admin_navire"):
            client = self.client_de(compte)
            self.assertEqual(client.post(f"/logistics/tickets/{self.ticket.pk}/transition/", {"status": "IN_REPAIR"}).status_code, 302, compte)
            self.ticket.refresh_from_db()
            self.assertEqual(self.ticket.status, "IN_REPAIR", compte)
            CorrectiveTicket.objects.filter(pk=self.ticket.pk).update(status="REPORTED")
            self.piece.refresh_from_db()
            avant = self.piece.quantite
            client.post(f"/logistics/stock/{self.piece.pk}/mouvements/", {"type": "ENTREE", "quantite": "5"})
            self.piece.refresh_from_db()
            self.assertEqual(self.piece.quantite, avant + 5, compte)
            StockPiece.objects.filter(pk=self.piece.pk).update(quantite=avant)
            reponse = self.envoyer(client, "patch", f"/api/assets/assets/{self.materiel.pk}/", {"designation": f"Renommé par {compte}"})
            self.assertEqual(reponse.status_code, 200, compte)
            self.assertEqual(client.post(f"/logistics/anomalies/{self.anomalie.pk}/statut/", {"statut": "PRISE_EN_COMPTE"}).status_code, 302, compte)
            Anomalie.objects.filter(pk=self.anomalie.pk).update(statut="SIGNALEE")

    def test_chef_de_service_garde_le_stock_et_l_attribution(self):
        client = self.client_de("chef_service_a")
        avant = self.piece.quantite
        client.post(f"/logistics/stock/{self.piece.pk}/mouvements/", {"type": "ENTREE", "quantite": "2"})
        self.piece.refresh_from_db()
        self.assertEqual(self.piece.quantite, avant + 2)
        client.post("/taches/", {"assigne": self.equipier.pk, "titre": "Tâche du service"})
        self.assertTrue(Tache.objects.filter(titre="Tâche du service").exists())

    def test_equipier_garde_ses_gestes_personnels_et_reste_borne(self):
        client = self.client_de("equipier_a")
        self.assertEqual(client.post("/taches/", {"titre": "Mon aide-mémoire"}).status_code, 302)
        self.assertTrue(Tache.objects.filter(titre="Mon aide-mémoire", assigne=self.equipier).exists())
        client.post(f"/taches/{self.tache_ouverte.pk}/action/", {"action": "demarrer"})
        self.tache_ouverte.refresh_from_db()
        self.assertEqual(self.tache_ouverte.statut, Tache.STATUT_EN_COURS)
        avant = self.etat()
        for nom, url, donnees in self.requetes_web()[8:13]:
            self.assertEqual(client.post(url, donnees).status_code, 403, nom)
        self.assertEqual(self.etat(), avant)
        client = self.client_de("equipier_a")
        for nom, methode, url, donnees in self.requetes_api():
            self.assertEqual(self.envoyer(client, methode, url, donnees).status_code, 403, nom)

    def test_ecriture_des_comptes_embarques_n_est_pas_bloquee_par_la_garde_du_soutien(self):
        for compte in ("cdt_a", "second_a", "chef_section_a", "equipier_a", "admin_navire"):
            self.assertEqual(self.client_de(compte).post("/users/theme/", {"theme": "sombre"}).status_code, 302, compte)


def creer_marin(nom, role, **rattachement):
    utilisateur = User.objects.create_user(username=nom, password="pass")
    UserProfile.objects.update_or_create(user=utilisateur, defaults={"role": role, **rattachement})
    return User.objects.get(pk=utilisateur.pk)


class SansBatimentNiChargeTests(Base):
    """Un commandant ou un second sans bâtiment ni charge à terre n'est pas du soutien et n'écrit nulle part."""

    def test_ni_soutien_ni_ecriture_ni_lecture_du_bord(self):
        for compte, role in (("cdt_isole", "COMMANDANT"), ("second_isole", "COMMANDANT_EN_SECOND")):
            utilisateur = creer_marin(compte, role)
            self.assertFalse(soutien_a_terre(utilisateur), compte)
            client = self.client_de(compte)
            for nom, url, donnees in self.requetes_web():
                avant = self.etat()
                reponse = client.post(url, donnees)
                self.assertIn(reponse.status_code, (302, 400, 403, 404), f"{compte} : {nom}")
                self.assertEqual(self.etat(), avant, f"{compte} : {nom}")
            for nom, methode, url, donnees in self.requetes_api():
                avant = self.etat()
                reponse = self.envoyer(client, methode, url, donnees)
                self.assertIn(reponse.status_code, (400, 403, 404), f"{compte} : {nom}")
                self.assertEqual(self.etat(), avant, f"{compte} : {nom}")
            self.assertEqual(client.get("/api/assets/assets/").json(), [], compte)
            self.assertNotContains(client.get("/taches/"), self.tache_ouverte.titre)


class EquipageBACommandementTests(Base):
    """B : le commandement de l'équipage à terre garde la relève sous lecture seule, rien d'autre."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.second_b = creer_marin("second_b", "COMMANDANT_EN_SECOND", ship=cls.bre, equipage="B")

    def setUp(self):
        ReleveEquipage.objects.all().delete()

    def relever(self, compte, action, **plus):
        if action == "proposer_releve":
            plus.setdefault("date_effet", champ_local(self.bre, timezone.now()))
        return self.client_de(compte).post("/parametre/", {"action": action, **plus})

    def en_attente(self):
        return ReleveEquipage.objects.filter(ship=self.bre, statut=ReleveEquipage.Statut.EN_ATTENTE).first()

    def test_ni_soutien_ni_ecriture_hors_releve(self):
        for compte in ("cdt_b", "second_b"):
            self.assertFalse(soutien_a_terre(User.objects.get(username=compte)), compte)
            client = self.client_de(compte)
            avant = self.etat()
            reponse = client.post("/taches/", {"assigne": self.equipier.pk, "titre": "Intrus"})
            self.assertEqual(reponse.status_code, 403, compte)
            self.assertEqual(self.etat(), avant, compte)

    def test_proposer_et_annuler_la_releve_sous_lecture_seule(self):
        for compte in ("cdt_b", "second_b"):
            self.assertEqual(self.relever(compte, "proposer_releve", equipage="B").status_code, 302, compte)
            self.assertEqual(self.en_attente().propose_par.username, compte)
            self.relever(compte, "annuler_releve")
            self.assertIsNone(self.en_attente(), compte)

    def test_decider_la_releve_sous_lecture_seule(self):
        self.relever("second_a", "proposer_releve", equipage="B")
        self.relever("cdt_b", "decider_releve", decision="valider")
        self.bre.refresh_from_db()
        self.assertEqual(self.bre.equipage_a_bord, "B")

    def test_le_second_a_bord_decide_et_propose_mais_pas_sa_propre_proposition(self):
        self.relever("cdt_b", "proposer_releve", equipage="B")
        self.relever("second_a", "decider_releve", decision="valider")
        self.bre.refresh_from_db()
        self.assertEqual(self.bre.equipage_a_bord, "B")
        self.bre.equipage_a_bord = "A"
        self.bre.save()
        self.relever("second_a", "proposer_releve", equipage="B")
        proposition = self.en_attente()
        self.assertEqual(proposition.propose_par.username, "second_a")
        self.relever("second_a", "decider_releve", decision="valider")
        self.assertEqual(self.en_attente().pk, proposition.pk)

    def test_equipier_et_chef_de_section_ne_decident_pas(self):
        self.relever("cdt_b", "proposer_releve", equipage="B")
        proposition = self.en_attente()
        for compte in ("equipier_a", "chef_section_a"):
            self.relever(compte, "decider_releve", decision="valider")
            self.relever(compte, "annuler_releve")
            self.assertEqual(self.en_attente().pk, proposition.pk, compte)
        self.bre.refresh_from_db()
        self.assertEqual(self.bre.equipage_a_bord, "A")


class CircuitsCatalogueFlotteTests(Base):
    """C : au niveau HTTP, le responsable de spécialité et son chef tiennent leurs circuits du catalogue flotte."""

    def donnees_fiche(self, **plus):
        return {"name": "Contrôle trimestriel", "mode_declenchement": "CALENDRIER", "intervalle": "3", "unite_intervalle": "M",
                "duree_estimee_min": "30", "nb_personnes": "1", "etape_texte": ["Contrôler"], "etape_attention": [""],
                "ligne_cle": [""], "ligne_type": ["checkbox"], "ligne_label": ["Goupille"], "ligne_unite": [""],
                "ligne_min": [""], "ligne_max": [""], "ligne_obligatoire": ["1"], **plus}

    def visas_du_bord(self, url_viser, objet, etapes=3):
        for compte in ("chef_secteur_a", "chef_service_a", "coma_comanav")[:etapes]:
            objet.refresh_from_db()
            self.client_de(compte).post(url_viser, {"etape": objet.etat})
        objet.refresh_from_db()

    def test_fiche_flotte_verifiee_puis_visee(self):
        categorie = CategorieCatalogue.objects.get(nom="Extincteurs")
        self.assertEqual(self.client_de("chef_section_a").post(
            reverse("fiche-flotte-nouvelle", args=[categorie.pk]), self.donnees_fiche()).status_code, 302)
        version = ChecklistTemplate.objects.get(name="Contrôle trimestriel", fiche__niveau="FLOTTE")
        self.visas_du_bord(reverse("fiche-viser", args=[version.pk]), version)
        self.assertEqual(version.etat, ChecklistTemplate.Etat.VERIFICATION)
        resp = self.client_de("terre_securite")
        self.assertEqual(resp.post(reverse("fiche-flotte-verifier", args=[version.pk]), self.donnees_fiche(resume_modifications="")).status_code, 302)
        version.refresh_from_db()
        self.assertEqual(version.etat, ChecklistTemplate.Etat.VISA_CHEF_SPECIALITE)
        self.client_de("terre_chef_securite").post(reverse("fiche-viser", args=[version.pk]), {"etape": version.etat})
        version.refresh_from_db()
        self.assertEqual(version.etat, ChecklistTemplate.Etat.VALIDEE)

    def test_proposition_d_article_verifiee_puis_visee(self):
        from assets.models import PropositionArticle

        categorie = CategorieCatalogue.objects.get(nom="Extincteurs")
        self.client_de("chef_section_a").post(reverse("catalogue-proposition-nouvelle"), {
            "designation": "Extincteur poudre 6 kg", "categorie": str(categorie.pk), "marque": "Sicli"})
        proposition = PropositionArticle.objects.get(designation="Extincteur poudre 6 kg")
        self.visas_du_bord(reverse("catalogue-proposition-viser", args=[proposition.pk]), proposition)
        self.assertEqual(proposition.etat, ChecklistTemplate.Etat.VERIFICATION)
        self.client_de("terre_securite").post(reverse("catalogue-proposition-verifier", args=[proposition.pk]), {
            "designation": proposition.designation, "categorie": str(categorie.pk), "marque": "Sicli"})
        proposition.refresh_from_db()
        self.assertEqual(proposition.etat, ChecklistTemplate.Etat.VISA_CHEF_SPECIALITE)
        self.client_de("terre_chef_securite").post(reverse("catalogue-proposition-viser", args=[proposition.pk]), {"etape": proposition.etat})
        self.assertTrue(ArticleCatalogue.objects.filter(designation="Extincteur poudre 6 kg").exists())

    def test_api_du_catalogue_repond_au_responsable(self):
        client = self.client_de("terre_securite")
        specialite = ResponsableSpecialite.objects.get(user__username="terre_securite").specialite
        cree = self.envoyer(client, "post", "/api/assets/catalogue-categories/", {"nom": "API", "specialite": specialite.pk, "ordre": 1})
        self.assertEqual(cree.status_code, 201)
        self.assertEqual(client.get("/api/assets/catalogue-articles/").status_code, 200)
        categorie = CategorieCatalogue.objects.get(nom="Extincteurs")
        article = self.envoyer(client, "post", "/api/assets/catalogue-articles/", {"categorie": str(categorie.pk), "designation": "Article API"})
        self.assertEqual(article.status_code, 201)

    def test_pas_de_redaction_de_fiche_d_installation_du_bord(self):
        fiche = InstallationMaintenance.objects.filter(niveau="BORD", installation__ship=self.bre).order_by("installation__designation", "created_at").first()
        urls = [(f"/installations/{self.installation.pk}/fiches/nouvelle/", self.donnees_fiche())]
        if fiche:
            urls += [(f"/fiches/{fiche.pk}/modifier/", self.donnees_fiche()), (f"/fiches/{fiche.pk}/dupliquer/", {"installation": str(self.installation.pk)})]
        for compte in ("terre_securite", "terre_chef_securite"):
            client = self.client_de(compte)
            for url, donnees in urls:
                avant = self.etat()
                self.assertIn(client.post(url, donnees).status_code, (302, 403, 404), f"{compte} {url}")
                self.assertEqual(self.etat(), avant, f"{compte} {url}")


class GestionDesComptesParApiTests(Base):
    """F7 : le second ne gère aucun compte par l'API, comme l'annuaire web."""

    def test_le_second_ne_change_pas_un_role(self):
        profil = self.equipier2.profile
        client = self.client_de("second_a")
        avant = self.etat()
        reponse = self.envoyer(client, "patch", f"/api/accounts/profiles/{profil.pk}/", {"role": "CHEF_SECTION"})
        self.assertEqual(reponse.status_code, 403)
        self.assertEqual(self.etat(), avant)

    def test_le_commandant_garde_la_gestion(self):
        profil = self.equipier2.profile
        reponse = self.envoyer(self.client_de("cdt_a"), "patch", f"/api/accounts/profiles/{profil.pk}/", {"role": "CHEF_SECTION"})
        self.assertEqual(reponse.status_code, 200)
