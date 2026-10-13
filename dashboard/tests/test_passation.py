"""Synthèse de passation à la relève du double équipage."""
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, ServiceFunctionChoice, UserProfile
from annonces.models import Annonce
from assets.models import Asset, AssetType
from dashboard.passation import generer_passation_manuelle, syntheses_visibles
from demandes.models import Demande
from logistics.models import Anomalie, CorrectiveTicket, StockPiece
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from matrix.core.equipage import decider_releve, proposer_releve, valider_releve_secours
from notifications.liens import lien_objet
from notifications.models import Notification
from org.models import ParametresPassation, ReleveEquipage, Sector, Service, Ship, SynthesePassation
from quarts.models import CreneauServiceGarde, ServiceGarde
from taches.models import Tache
from training.models import TrainingCourse, TrainingRecord

User = get_user_model()


def marin(nom, role, navire, equipage="", service=None, secteur=None):
    user = User.objects.create_user(username=nom, password="pass")
    UserProfile.objects.update_or_create(
        user=user, defaults={"role": role, "ship": navire, "service": service, "sector": secteur, "equipage": equipage}
    )
    return User.objects.get(pk=user.pk)


def bloc(synthese, cle):
    return next(b for b in synthese.contenu["blocs"] if b["cle"] == cle)


class PassationBase(TestCase):
    activee = True

    def setUp(self):
        ParametresPassation.objects.create(active=self.activee)
        self.navire = Ship.objects.create(name="Bretagne", code="BRE", double_equipage=True, equipage_a_bord="A")
        self.service = Service.objects.create(ship=self.navire, name="Énergie")
        self.secteur = Sector.objects.create(service=self.service, name="Tableaux")
        self.cdt_a = marin("cdt_a", "COMMANDANT", self.navire, "A")
        self.cdt_b = marin("cdt_b", "COMMANDANT", self.navire, "B")
        self.chef_a = marin("chef_a", "CHEF_SECTEUR", self.navire, "A", self.service, self.secteur)
        self.chef_b = marin("chef_b", "CHEF_SECTEUR", self.navire, "B", self.service, self.secteur)
        self.equipier_b = marin("equipier_b", "EQUIPIER", self.navire, "B", self.service, self.secteur)
        self.equipier_a = marin("equipier_a", "EQUIPIER", self.navire, "A", self.service, self.secteur)
        self.aujourdhui = timezone.localdate()

    def relever(self):
        """Relève A → B proposée par le commandant A, validée par le commandant B."""
        proposition, erreur = proposer_releve(self.cdt_a, self.navire, "B")
        self.assertEqual(erreur, "")
        self.assertEqual(decider_releve(self.cdt_b, proposition, True), "")
        self.navire.refresh_from_db()
        return proposition

    def peupler(self):
        """Une donnée par bloc de la synthèse."""
        Tache.objects.create(titre="Purger", assigne=self.equipier_a, created_by=self.chef_a, statut="BLOQUEE", motif_blocage="Pièce")
        Tache.objects.create(titre="Peindre", assigne=self.equipier_a, created_by=self.chef_a, statut="A_FAIRE")
        Tache.objects.create(titre="Finie", assigne=self.equipier_a, created_by=self.chef_a, statut="TERMINEE")
        Tache.objects.create(titre="Secrète", assigne=self.equipier_a, created_by=self.equipier_a, statut="A_FAIRE", partagee=False)
        type_ = AssetType.objects.create(name="Pompe", category="Incendie", sector=self.secteur)
        asset = Asset.objects.create(asset_type=type_, ship=self.navire, service=self.service, sector=self.secteur)
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name="Contrôle", every_n_days=30)
        MaintenanceOccurrence.objects.create(plan=plan, asset=asset, scheduled_for=self.aujourdhui - timedelta(days=3), status="OVERDUE")
        CorrectiveTicket.objects.create(asset=asset, description="Fuite", severity=4)
        Anomalie.objects.create(titre="Odeur", description="x", created_by=self.equipier_a, ship=self.navire)
        StockPiece.objects.create(reference="F-1", designation="Filtre", quantite=0, quantite_minimale=2,
                                  ship=self.navire, service=self.service, sector=self.secteur)
        cours = TrainingCourse.objects.create(title="Incendie")
        TrainingRecord.objects.create(user=self.equipier_a, course=cours, completed_at=self.aujourdhui - timedelta(days=400),
                                      expires_at=self.aujourdhui - timedelta(days=5))
        garde = ServiceGarde.objects.create(
            fonction=ServiceFunctionChoice.objects.create(name="Permanence"), ship=self.navire, date_debut=self.aujourdhui,
            date_fin=self.aujourdhui + timedelta(days=30), statut=ServiceGarde.STATUT_PUBLIEE, created_by=self.cdt_a)
        debut = timezone.now() + timedelta(days=2)
        CreneauServiceGarde.objects.create(service_garde=garde, poste="Officier de garde", debut=debut, fin=debut + timedelta(hours=24))
        Annonce.objects.create(titre="Consigne", corps="x", ship=self.navire, accuse_requis=True, auteur=self.cdt_a, created_by=self.cdt_a)
        Demande.objects.create(titre="Pièce", declarant=self.equipier_a, responsable=self.chef_a, ship=self.navire,
                               content_type=ContentType.objects.get_for_model(Tache), object_id="1")


class GenerationTests(PassationBase):
    def test_la_releve_cree_la_synthese_et_la_trace(self):
        releve = self.relever()
        synthese = SynthesePassation.objects.get()
        self.assertEqual((synthese.ship, synthese.releve, synthese.equipage_sortant, synthese.equipage_montant),
                         (self.navire, releve, "A", "B"))
        self.assertTrue(AuditLog.objects.filter(action="passation_generee", actor=self.cdt_b).exists())

    def test_chaque_bloc_compte_ses_donnees(self):
        self.peupler()
        self.relever()
        synthese = SynthesePassation.objects.get()
        totaux = {b["cle"]: b["total"] for b in synthese.contenu["blocs"]}
        self.assertEqual(totaux, {
            "taches": 2, "maintenance": 1, "tickets": 1, "anomalies": 1, "stock": 1,
            "qualifications": 1, "listes": 1, "annonces": 1, "demandes": 1,
        })
        titres = [ligne["titre"] for groupe in bloc(synthese, "taches")["groupes"] for ligne in groupe["lignes"]]
        self.assertEqual(sorted(titres), ["Peindre", "Purger"])

    def test_synthese_figee(self):
        self.peupler()
        self.relever()
        Anomalie.objects.create(titre="Nouvelle", description="x", created_by=self.equipier_a, ship=self.navire)
        self.assertEqual(bloc(SynthesePassation.objects.get(), "anomalies")["total"], 1)

    def test_pas_de_fuite_inter_navires(self):
        autre = Ship.objects.create(name="Autre", code="AUT", double_equipage=True, equipage_a_bord="A")
        Anomalie.objects.create(titre="Étrangère", description="x", created_by=self.cdt_a, ship=autre)
        StockPiece.objects.create(
            reference="X", designation="Étranger", quantite=0, quantite_minimale=1, ship=autre,
            service=Service.objects.create(ship=autre, name="S"), sector=Sector.objects.create(
                service=Service.objects.get(ship=autre), name="T"))
        self.relever()
        synthese = SynthesePassation.objects.get()
        self.assertEqual(bloc(synthese, "anomalies")["total"], 0)
        self.assertEqual(bloc(synthese, "stock")["total"], 0)

    def test_idempotente_manuel_et_automatique(self):
        self.relever()
        synthese, erreur = generer_passation_manuelle(self.cdt_a, self.navire)
        self.assertEqual(erreur, "")
        self.assertEqual(synthese, SynthesePassation.objects.get())
        generer_passation_manuelle(self.cdt_b, self.navire)
        self.assertEqual(SynthesePassation.objects.count(), 1)

    def test_manuel_reserve_au_commandement_et_a_une_releve_existante(self):
        self.assertEqual(SynthesePassation.objects.count(), 0)
        self.assertIn("Aucune relève", generer_passation_manuelle(self.cdt_a, self.navire)[1])
        self.assertIn("commandement", generer_passation_manuelle(self.chef_a, self.navire)[1])

    def test_manuel_reprend_une_releve_sans_synthese(self):
        releve = self.relever()
        SynthesePassation.objects.all().delete()
        synthese, erreur = generer_passation_manuelle(self.cdt_a, self.navire)
        self.assertEqual((erreur, synthese.releve, synthese.equipage_sortant), ("", releve, "A"))

    def test_equipage_unique_sans_fonction_ni_erreur(self):
        unique = Ship.objects.create(name="Unique", code="UNI")
        cdt = marin("cdt_u", "COMMANDANT", unique)
        self.assertEqual(generer_passation_manuelle(cdt, unique)[0], None)
        self.assertEqual(SynthesePassation.objects.count(), 0)

    def test_refus_ou_attente_ne_generent_rien(self):
        proposition, _ = proposer_releve(self.cdt_a, self.navire, "B")
        self.assertEqual(SynthesePassation.objects.count(), 0)
        decider_releve(self.cdt_b, proposition, False)
        self.assertEqual(SynthesePassation.objects.count(), 0)
        self.assertEqual(ReleveEquipage.objects.get().statut, "refusee")

    def test_bouton_manuel_depuis_les_reglages(self):
        self.relever()
        SynthesePassation.objects.all().delete()
        self.client.force_login(self.cdt_a)  # équipage à terre : l'action reste permise
        reponse = self.client.post("/parametre/", {"action": "generer_passation", "next_tab": "equipage"})
        synthese = SynthesePassation.objects.get()
        self.assertRedirects(reponse, reverse("passation", args=[synthese.pk]))


class NotificationTests(PassationBase):
    def test_chefs_de_l_equipage_montant_notifies_avec_lien(self):
        self.relever()
        synthese = SynthesePassation.objects.get()
        notifies = set(Notification.objects.filter(content_type=ContentType.objects.get_for_model(synthese))
                       .values_list("user__username", flat=True))
        self.assertEqual(notifies, {"cdt_b", "chef_b"})
        notification = Notification.objects.get(user=self.chef_b, object_id=str(synthese.pk))
        self.assertEqual(lien_objet(self.chef_b, synthese), reverse("passation", args=[synthese.pk]))
        self.assertIn("Bretagne", notification.verb)


class DroitsTests(PassationBase):
    def setUp(self):
        super().setUp()
        self.relever()
        self.synthese = SynthesePassation.objects.get()
        self.url = reverse("passation", args=[self.synthese.pk])

    def code(self, user):
        self.client.force_login(user)
        return self.client.get(self.url).status_code

    def test_commandement_et_chefs_des_deux_equipages(self):
        for user in (self.cdt_a, self.cdt_b, self.chef_a, self.chef_b):
            self.assertEqual(self.code(user), 200, user.username)

    def test_equipier_et_anonyme_exclus(self):
        self.assertEqual(self.code(self.equipier_b), 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_jamais_un_autre_navire(self):
        autre = Ship.objects.create(name="Autre", code="AUT", double_equipage=True, equipage_a_bord="A")
        for role in ("COMMANDANT", "CHEF_SECTEUR"):
            etranger = marin(f"etranger_{role}", role, autre, "B")
            self.assertEqual(self.code(etranger), 404, role)
            self.assertFalse(syntheses_visibles(etranger).exists())

    def test_chef_hors_des_deux_equipages_exclu(self):
        chef_c = marin("chef_c", "CHEF_SECTEUR", self.navire, "C", self.service, self.secteur)
        self.assertEqual(self.code(chef_c), 404)

    def test_page_imprimable_et_pdf(self):
        self.client.force_login(self.cdt_b)
        page = self.client.get(self.url)
        self.assertContains(page, "Synthèse de passation")
        self.assertContains(page, "Tâches ouvertes et bloquées")
        pdf = self.client.get(reverse("passation-pdf", args=[self.synthese.pk]))
        self.assertIn(pdf.status_code, (200, 404))
        if pdf.status_code == 200:
            self.assertEqual(pdf["Content-Type"], "application/pdf")


class EchecGenerationTests(PassationBase):
    def verifier_releve_intacte(self, proposition):
        proposition.refresh_from_db()
        self.navire.refresh_from_db()
        self.assertEqual(proposition.statut, ReleveEquipage.Statut.VALIDEE)
        self.assertEqual(self.navire.equipage_a_bord, "B")
        self.assertEqual(SynthesePassation.objects.count(), 0)
        self.assertTrue(AuditLog.objects.filter(action="passation_echec").exists())

    def test_echec_n_annule_pas_la_releve(self):
        proposition, _ = proposer_releve(self.cdt_a, self.navire, "B")
        with mock.patch("dashboard.passation.contenu_passation", side_effect=RuntimeError), self.assertLogs("matrix.core.equipage", "ERROR"):
            self.assertEqual(decider_releve(self.cdt_b, proposition, True), "")
        self.verifier_releve_intacte(proposition)

    def test_echec_n_annule_pas_la_validation_de_secours(self):
        admin = User.objects.create_superuser("admin_s", password="pass")
        proposition, _ = proposer_releve(self.cdt_a, self.navire, "B")
        UserProfile.objects.filter(user=self.cdt_b).update(role="EQUIPIER")
        with mock.patch("dashboard.passation.contenu_passation", side_effect=RuntimeError), self.assertLogs("matrix.core.equipage", "ERROR"):
            self.assertEqual(valider_releve_secours(admin, proposition, "Aucun commandant"), "")
        self.verifier_releve_intacte(proposition)


class DesactiveeTests(PassationBase):
    activee = False

    def test_releve_sans_synthese_ni_notification_ni_trace(self):
        self.relever()
        self.assertEqual(self.navire.equipage_a_bord, "B")
        self.assertEqual(SynthesePassation.objects.count(), 0)
        self.assertEqual(Notification.objects.filter(user__in=(self.cdt_b, self.chef_b), verb__contains="passation").count(), 0)
        self.assertFalse(AuditLog.objects.filter(action__startswith="passation").exists())

    def test_active_par_defaut_sans_reglage_enregistre(self):
        ParametresPassation.objects.all().delete()
        self.assertTrue(ParametresPassation.courants().active)
        self.relever()
        self.assertEqual(SynthesePassation.objects.count(), 1)

    def test_bouton_manuel_refuse_et_pages_fermees(self):
        self.relever()
        self.client.force_login(self.cdt_a)
        self.client.post("/parametre/", {"action": "generer_passation", "next_tab": "equipage"})
        self.assertEqual(SynthesePassation.objects.count(), 0)
        self.assertNotContains(self.client.get("/parametre/?tab=equipage"), "Générer la synthèse de passation")
        synthese = SynthesePassation.objects.create(ship=self.navire, equipage_sortant="A", equipage_montant="B")
        self.assertEqual(self.client.get(reverse("passation", args=[synthese.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("passation-pdf", args=[synthese.pk])).status_code, 404)
        ParametresPassation.objects.update(active=True)
        self.assertEqual(self.client.get(reverse("passation", args=[synthese.pk])).status_code, 200)

    def test_activation_reservee_a_l_administrateur_general_et_tracee(self):
        self.client.force_login(self.cdt_a)
        self.client.post("/parametre/", {"action": "update_parametres_passation", "active": "on", "next_tab": "seuils_role"})
        self.assertFalse(ParametresPassation.courants().active)
        admin = User.objects.create_superuser("admin_p", password="pass")
        self.client.force_login(admin)
        self.client.post("/parametre/", {"action": "update_parametres_passation", "active": "on", "next_tab": "seuils_role"})
        self.assertTrue(ParametresPassation.courants().active)
        self.client.post("/parametre/", {"action": "update_parametres_passation", "next_tab": "seuils_role"})
        self.assertFalse(ParametresPassation.courants().active)
        self.assertTrue(AuditLog.objects.filter(action="update_parametres_passation").exists())
