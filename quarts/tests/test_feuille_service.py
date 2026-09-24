"""Tests de la feuille de service quotidienne (tâche Notion « Feuille de
service quotidienne — personnel de service et en-tête (à quai) ») : personnel
calculé automatiquement depuis les tours publiés, circuit de visa à 3
paliers (secteur -> service -> COMAEQ), historique des versions,
notifications et permissions."""
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import ServiceFunctionChoice, UserProfile
from notifications.models import Notification
from org.models import Sector, Service, Ship
from quarts.models import (
    CreneauServiceGarde,
    FeuilleService,
    FonctionFeuilleService,
    RubriqueEnTeteFeuilleService,
    ServiceGarde,
    peut_viser_comaeq,
    peut_viser_secteur,
    peut_viser_service,
    personnel_du_jour,
)


def _utilisateur(username, role, ship=None, service=None, sector=None):
    user = User.objects.create_user(username=username, password="pass")
    UserProfile.objects.update_or_create(
        user=user, defaults={"role": role, "ship": ship, "service": service, "sector": sector}
    )
    # Le signal accounts.models.create_user_profile crée déjà un profil (rôle
    # EQUIPIER) au moment de create_user() ci-dessus, et Django met alors en
    # cache cette relation inverse sur `user` (comportement symétrique du
    # OneToOneField). L'update_or_create suivant modifie la ligne en base
    # mais PAS ce cache déjà posé sur l'objet `user` en mémoire : sans ce
    # refresh, `user.profile` renverrait encore l'ancien rôle EQUIPIER.
    user.refresh_from_db()
    return user


class FeuilleServiceTestsBase(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Feuille", code="FDS")
        self.autre_ship = Ship.objects.create(name="Autre navire", code="AUT")
        self.service = Service.objects.create(ship=self.ship, name="Pont")
        self.sector = Sector.objects.create(service=self.service, name="Service courant")

        self.equipier = _utilisateur("bsc", "EQUIPIER", ship=self.ship, service=self.service, sector=self.sector)
        self.chef_secteur = _utilisateur("chef_secteur", "CHEF_SECTEUR", ship=self.ship, sector=self.sector)
        self.chef_secteur_autre = _utilisateur(
            "chef_autre_secteur", "CHEF_SECTEUR",
            ship=self.ship, sector=Sector.objects.create(service=self.service, name="Autre secteur"),
        )
        self.chef_service = _utilisateur("chef_service", "CHEF_SERVICE", ship=self.ship, service=self.service)
        self.etat_major = _utilisateur("etat_major", "ETAT_MAJOR", ship=self.ship)
        self.etat_major_autre_navire = _utilisateur("etat_major_autre", "ETAT_MAJOR", ship=self.autre_ship)
        self.commandant = _utilisateur("commandant", "COMMANDANT", ship=self.ship)
        self.marin_service = _utilisateur("marin_service", "EQUIPIER", ship=self.ship)

        self.fonction = FonctionFeuilleService.objects.create(
            ship=self.ship, libelle="Officier de garde", ordre=1
        )
        self.rubrique_fixe = RubriqueEnTeteFeuilleService.objects.create(
            ship=self.ship, libelle="Mesures de sécurité", ordre=1,
            type_saisie=RubriqueEnTeteFeuilleService.TYPE_FIXE, valeur_fixe="Vigipirate renforcé",
        )
        self.rubrique_quotidienne = RubriqueEnTeteFeuilleService.objects.create(
            ship=self.ship, libelle="Type de journée", ordre=2,
        )

        self.jour = timezone.localdate()
        self.fonction_choice = ServiceFunctionChoice.objects.create(name="Officier de garde")

    def _publier_tour(self, poste="Officier de garde", marin=None, debut=None, fin=None):
        """Crée et publie un ServiceGarde avec un créneau couvrant self.jour,
        pour que personnel_du_jour puisse le retrouver."""
        garde = ServiceGarde.objects.create(
            ship=self.ship, fonction=self.fonction_choice,
            date_debut=self.jour, date_fin=self.jour, statut=ServiceGarde.STATUT_PUBLIEE,
        )
        debut = debut or timezone.make_aware(datetime.combine(self.jour, datetime.min.time().replace(hour=8)))
        fin = fin or debut + timedelta(hours=24)
        return CreneauServiceGarde.objects.create(service_garde=garde, poste=poste, debut=debut, fin=fin, marin=marin)


class PersonnelDuJourTests(FeuilleServiceTestsBase):
    def test_trouve_le_titulaire_par_correspondance_de_poste(self):
        self._publier_tour(marin=self.marin_service)
        resultat = personnel_du_jour(self.ship, self.jour)
        self.assertEqual(len(resultat), 1)
        self.assertEqual(resultat[0]["creneau"].marin, self.marin_service)

    def test_correspondance_insensible_a_la_casse(self):
        self._publier_tour(poste="OFFICIER DE GARDE", marin=self.marin_service)
        resultat = personnel_du_jour(self.ship, self.jour)
        self.assertEqual(resultat[0]["creneau"].marin, self.marin_service)

    def test_aucun_titulaire_si_poste_different(self):
        self._publier_tour(poste="Gradé coupé 1", marin=self.marin_service)
        resultat = personnel_du_jour(self.ship, self.jour)
        self.assertIsNone(resultat[0]["creneau"])

    def test_ignore_les_listes_non_publiees(self):
        garde = ServiceGarde.objects.create(
            ship=self.ship, fonction=self.fonction_choice,
            date_debut=self.jour, date_fin=self.jour, statut=ServiceGarde.STATUT_BROUILLON,
        )
        debut = timezone.make_aware(datetime.combine(self.jour, datetime.min.time().replace(hour=8)))
        CreneauServiceGarde.objects.create(
            service_garde=garde, poste="Officier de garde", debut=debut, fin=debut + timedelta(hours=24),
            marin=self.marin_service,
        )
        resultat = personnel_du_jour(self.ship, self.jour)
        self.assertIsNone(resultat[0]["creneau"])


class WorkflowFeuilleServiceTests(FeuilleServiceTestsBase):
    def setUp(self):
        super().setUp()
        self._publier_tour(marin=self.marin_service)
        self.feuille = FeuilleService.objects.create(
            ship=self.ship, date=self.jour, created_by=self.equipier, updated_by=self.equipier,
        )

    def test_proposer_par_un_equipier_passe_par_le_visa_secteur(self):
        self.feuille.proposer(self.equipier)
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_VISA_SECTEUR)
        self.assertEqual(self.feuille.secteur_redacteur, self.sector)
        self.assertTrue(Notification.objects.filter(user=self.chef_secteur).exists())

    def test_proposer_par_un_chef_de_secteur_saute_le_visa_secteur(self):
        self.feuille.proposer(self.chef_secteur)
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_VISA_SERVICE)

    def test_circuit_complet_jusqu_a_la_publication(self):
        self.feuille.proposer(self.equipier)
        self.assertTrue(peut_viser_secteur(self.chef_secteur, self.feuille))
        self.assertFalse(peut_viser_secteur(self.chef_secteur_autre, self.feuille))

        self.feuille.viser_secteur(self.chef_secteur)
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_VISA_SERVICE)
        self.assertTrue(peut_viser_service(self.chef_service, self.feuille))

        self.feuille.viser_service(self.chef_service)
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_VISA_COMAEQ)
        self.assertTrue(peut_viser_comaeq(self.etat_major, self.feuille))
        self.assertFalse(peut_viser_comaeq(self.etat_major_autre_navire, self.feuille))

        self.feuille.viser_comaeq(self.etat_major)
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_PUBLIEE)
        self.assertIsNotNone(self.feuille.publiee_le)
        self.assertEqual(self.feuille.versions.count(), 1)
        # Fraction de service notifiée (le marin trouvé sur le tour publié),
        # jamais tout l'équipage (cf. tâche Notion).
        self.assertTrue(Notification.objects.filter(user=self.marin_service).exists())
        self.assertFalse(Notification.objects.filter(user=self.equipier, verb__icontains="publiée").exists())

    def test_supervision_globale_peut_viser_a_toutes_les_etapes(self):
        self.feuille.proposer(self.equipier)
        self.assertTrue(peut_viser_secteur(self.commandant, self.feuille))
        self.feuille.viser_secteur(self.commandant)
        self.assertTrue(peut_viser_service(self.commandant, self.feuille))
        self.feuille.viser_service(self.commandant)
        self.assertTrue(peut_viser_comaeq(self.commandant, self.feuille))

    def test_renvoyer_remet_en_brouillon_avec_motif(self):
        self.feuille.proposer(self.equipier)
        self.feuille.viser_secteur(self.chef_secteur)
        self.feuille.renvoyer(self.chef_service, "Erreur sur le nom du titulaire")
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_BROUILLON)
        self.assertEqual(self.feuille.motif_retour, "Erreur sur le nom du titulaire")
        self.assertIsNone(self.feuille.visa_secteur_le)
        self.assertTrue(
            Notification.objects.filter(user=self.equipier, verb__icontains="renvoyée").exists()
        )

    def test_creer_version_fige_entete_et_personnel(self):
        self.feuille.valeurs_entete = {str(self.rubrique_quotidienne.pk): "Dimanche au port base"}
        self.feuille.save(update_fields=["valeurs_entete"])
        self.feuille.proposer(self.chef_service)
        self.feuille.viser_service(self.chef_service)
        self.feuille.viser_comaeq(self.etat_major)
        version = self.feuille.versions.get(numero=1)
        libelles_entete = [e["libelle"] for e in version.contenu_fige["entete"]]
        self.assertIn("Mesures de sécurité", libelles_entete)
        self.assertIn("Type de journée", libelles_entete)
        fonctions_personnel = [p["fonction"] for p in version.contenu_fige["personnel"]]
        self.assertIn("Officier de garde", fonctions_personnel)


class WebViewsFeuilleServiceTests(FeuilleServiceTestsBase):
    def setUp(self):
        super().setUp()
        self._publier_tour(marin=self.marin_service)
        self.url = f"/quarts/feuille-service/{self.ship.pk}/{self.jour.isoformat()}/"

    def test_index_redirige_vers_la_feuille_du_jour_du_navire(self):
        self.client.login(username="bsc", password="pass")
        r = self.client.get("/quarts/feuille-service/")
        self.assertRedirects(r, self.url)

    def test_creation_du_brouillon_par_un_marin_du_navire(self):
        self.client.login(username="bsc", password="pass")
        r = self.client.post(self.url, {"action": "creer"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(FeuilleService.objects.filter(ship=self.ship, date=self.jour).exists())

    def test_circuit_complet_via_les_vues_web(self):
        FeuilleService.objects.create(ship=self.ship, date=self.jour, created_by=self.equipier, updated_by=self.equipier)

        self.client.login(username="bsc", password="pass")
        r = self.client.post(self.url, {"action": "proposer"})
        self.assertEqual(r.status_code, 302, r.content)
        self.assertEqual(FeuilleService.objects.get().statut, FeuilleService.STATUT_VISA_SECTEUR)

        self.client.login(username="chef_secteur", password="pass")
        r = self.client.post(self.url, {"action": "viser_secteur"})
        self.assertEqual(r.status_code, 302, r.content)
        self.assertEqual(FeuilleService.objects.get().statut, FeuilleService.STATUT_VISA_SERVICE)

        self.client.login(username="chef_service", password="pass")
        r = self.client.post(self.url, {"action": "viser_service"})
        self.assertEqual(r.status_code, 302, r.content)
        self.assertEqual(FeuilleService.objects.get().statut, FeuilleService.STATUT_VISA_COMAEQ)

        self.client.login(username="etat_major", password="pass")
        r = self.client.post(self.url, {"action": "viser_comaeq"})
        self.assertEqual(r.status_code, 302, r.content)
        self.assertEqual(FeuilleService.objects.get().statut, FeuilleService.STATUT_PUBLIEE)

    def test_un_chef_de_secteur_etranger_ne_peut_pas_viser(self):
        FeuilleService.objects.create(ship=self.ship, date=self.jour, created_by=self.equipier, updated_by=self.equipier)
        self.client.login(username="bsc", password="pass")
        self.client.post(self.url, {"action": "proposer"})

        self.client.login(username="chef_autre_secteur", password="pass")
        r = self.client.post(self.url, {"action": "viser_secteur"})
        self.assertEqual(r.status_code, 403)

    def test_marin_hors_navire_ne_peut_pas_lire_la_feuille_publiee(self):
        feuille = FeuilleService.objects.create(
            ship=self.ship, date=self.jour, created_by=self.equipier, updated_by=self.equipier,
        )
        feuille.proposer(self.chef_service)
        feuille.viser_service(self.chef_service)
        feuille.viser_comaeq(self.etat_major)
        marin_autre_navire = _utilisateur("marin_autre_navire", "EQUIPIER", ship=self.autre_ship)
        self.client.login(username="marin_autre_navire", password="pass")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)


class ReglagesFeuilleServiceTests(FeuilleServiceTestsBase):
    def test_chef_service_peut_ajouter_une_rubrique_et_une_fonction(self):
        self.client.login(username="chef_service", password="pass")
        r = self.client.post(
            f"/quarts/feuille-service/reglages/?ship={self.ship.pk}",
            {
                "action": "enregistrer_rubriques", "ship": self.ship.pk,
                "nouvelle_rubrique_libelle": "Heure des couleurs",
                "nouvelle_rubrique_type_saisie": "QUOTIDIENNE", "nouvelle_rubrique_ordre": "3",
            },
        )
        self.assertEqual(r.status_code, 302, r.content)
        self.assertTrue(RubriqueEnTeteFeuilleService.objects.filter(ship=self.ship, libelle="Heure des couleurs").exists())

    def test_equipier_ne_peut_pas_configurer(self):
        self.client.login(username="bsc", password="pass")
        r = self.client.post(
            f"/quarts/feuille-service/reglages/?ship={self.ship.pk}",
            {"action": "enregistrer_rubriques", "ship": self.ship.pk, "nouvelle_rubrique_libelle": "Test"},
        )
        self.assertEqual(r.status_code, 403)
