"""Commandant en second : publication d'annonces bornée, autres fonctions en lecture, visa COMA conservé.
Comptes et données de seed_demo."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog
from annonces import services as annonces
from annonces.models import Annonce, LectureAnnonce, ParametresAnnonces
from assets.models import CategorieCatalogue, PropositionArticle
from assets.proposition_article import habilite_coma
from dashboard.models import ItemAppareillage, SessionAppareillage
from demandes import services as demandes
from matrix.core.role_thresholds import invalidate_cache
from matrix.core.roles import RoleLevel, niveau_ecriture
from matrix.tests.test_securite_terre_second import Base
from notifications.models import Notification, NotificationLevel
from org.models import RoleThresholdConfig, Service, Ship
from postes import services as postes
from retex import services as retex_services
from retex.models import Retex
from rondes import services as rondes
from training.web_views import peut_valider_proposition_bord


class AnnoncesDuSecondTests(Base):
    """Le second publie sur son bâtiment, par le registre des seuils, sans autre écriture."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.nor = Ship.objects.get(code="NOR")

    def publier(self, compte, **plus):
        donnees = {"titre": "Exercice incendie", "corps": "Rassemblement jeudi.", "niveau": "info",
                   "cible": f"ship:{self.bre.pk}", "equipage": "", **plus}
        client = self.client_de(compte)
        return client.post(reverse("annonce-nouvelle"), donnees)

    def test_trois_categories_diffusion_audit_et_auteur(self):
        for niveau in (NotificationLevel.INFO, NotificationLevel.WARNING, NotificationLevel.DANGER):
            reponse = self.publier("second_a", titre=f"Annonce {niveau}", niveau=niveau.value)
            self.assertEqual(reponse.status_code, 302, niveau)
            annonce = Annonce.objects.get(titre=f"Annonce {niveau}")
            self.assertEqual((annonce.auteur.username, annonce.niveau, annonce.ship_id), ("second_a", niveau.value, self.bre.pk))
            self.assertIsNotNone(annonce.diffusee_le)
            self.assertTrue(Notification.objects.filter(user=self.equipier, verb__contains=annonce.titre, level=niveau.value).exists())
            self.assertFalse(Notification.objects.filter(user__username="second_a", verb__contains=annonce.titre).exists())
            self.assertFalse(Notification.objects.filter(user__username="equipier_nor", verb__contains=annonce.titre).exists())
            self.assertTrue(AuditLog.objects.filter(actor__username="second_a", action="annonce_publiee", details__startswith=f"annonce={annonce.pk};").exists())

    def test_accuse_suivi_et_rappel(self):
        self.publier("second_a", titre="À accuser", accuse_requis="on")
        annonce = Annonce.objects.get(titre="À accuser")
        self.assertTrue(annonce.accuse_requis)
        self.client_de("equipier_a").post(reverse("annonce-action", args=[annonce.pk]), {"action": "accuser"})
        self.assertTrue(LectureAnnonce.objects.get(annonce=annonce, user=self.equipier).accuse)
        suivi = {l["user"].username: l["etat"] for l in annonces.suivi_lecture(annonce)}
        self.assertEqual(suivi["equipier_a"], "Accusé")
        self.assertEqual(suivi["equipier_a2"], "Non lu")
        self.assertEqual(self.client_de("second_a").get(reverse("annonce-detail", args=[annonce.pk])).status_code, 200)
        parametres = ParametresAnnonces.courants()
        parametres.jours_rappel_accuse = 2
        parametres.save()
        Annonce.objects.filter(pk=annonce.pk).update(diffusee_le=timezone.now() - timedelta(days=5))
        self.assertGreater(annonces.rappeler_accuses(), 0)
        self.assertTrue(Notification.objects.filter(user=self.equipier2, verb__startswith=annonces.PREFIXE_RAPPEL).exists())
        self.assertFalse(Notification.objects.filter(user=self.equipier, verb__startswith=annonces.PREFIXE_RAPPEL).exists())

    def test_jamais_un_autre_batiment_ni_un_equipage_inconnu(self):
        client = self.client_de("second_a")
        avant = self.etat()
        autre = {"titre": "Intrus", "corps": "x", "niveau": "info", "equipage": ""}
        client.post(reverse("annonce-nouvelle"), {**autre, "cible": f"ship:{self.nor.pk}"})
        service_nor = Service.objects.filter(ship=self.nor).first()
        client.post(reverse("annonce-nouvelle"), {**autre, "cible": f"service:{service_nor.pk}"})
        client.post(reverse("annonce-nouvelle"), {**autre, "cible": f"ship:{self.bre.pk}", "equipage": "Z"})
        self.assertFalse(Annonce.objects.filter(titre="Intrus").exists())
        self.assertEqual(self.etat(), avant)

    def test_les_autres_ne_publient_pas(self):
        for compte in ("equipier_a", "chef_section_a", "terre_classe", "terre_securite"):
            self.publier(compte, titre=f"Refus {compte}")
            self.assertFalse(Annonce.objects.filter(titre=f"Refus {compte}").exists(), compte)
        self.assertEqual(self.client_de("equipier_a").get(reverse("annonce-nouvelle")).status_code, 404)

    def test_chef_de_service_et_commandant_publient_toujours(self):
        self.publier("cdt_a", titre="Annonce cdt_a")
        self.assertTrue(Annonce.objects.filter(titre="Annonce cdt_a").exists())
        cible = annonces.cibles_autorisees(User.objects.get(username="chef_service_a"))[0][0]
        self.publier("chef_service_a", titre="Annonce du service", cible=cible)
        self.assertTrue(Annonce.objects.filter(titre="Annonce du service").exists())

    def test_l_exception_ne_donne_aucune_autre_ecriture(self):
        second = User.objects.get(username="second_a")
        self.assertTrue(annonces.peut_publier(second))
        self.assertEqual(niveau_ecriture(second), RoleLevel.EQUIPIER)
        client = self.client_de("second_a")
        avant = self.etat()
        for nom, url, donnees in self.requetes_web():
            client.post(url, donnees)
        self.assertEqual(self.etat(), avant)

    def test_le_seuil_reste_configurable_par_le_registre(self):
        RoleThresholdConfig.objects.update_or_create(ship=self.bre, defaults={"thresholds": {"annonce_publication": "COMMANDANT"}})
        invalidate_cache(self.bre.id)
        self.addCleanup(invalidate_cache, self.bre.id)
        self.assertFalse(annonces.peut_publier(User.objects.get(username="second_a")))
        self.assertTrue(annonces.peut_publier(User.objects.get(username="cdt_a")))


class FonctionsDuSecondEnLectureTests(Base):
    def test_pret_a_appareiller_consultation_sans_modification(self):
        self.client_de("cdt_a").post(reverse("session-appareillage-ouvrir"))
        session = SessionAppareillage.objects.get(ship=self.bre, cloturee_le__isnull=True)
        item = session.items.first() or ItemAppareillage.objects.create(
            session=session, categorie=ItemAppareillage.CATEGORIE_STOCK, libelle="Pièce")
        client = self.client_de("second_a")
        page = client.get(reverse("pret-appareillage"))
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, 'name="cocher"')
        self.assertNotContains(page, reverse("item-appareillage-cocher", args=[item.pk]))
        avant = self.etat()
        self.assertEqual(client.post(reverse("item-appareillage-cocher", args=[item.pk])).status_code, 403)
        self.assertEqual(client.post(reverse("session-appareillage-ouvrir")).status_code, 403)
        self.assertEqual(self.etat(), avant)
        self.assertEqual(self.client_de("equipier_a").post(reverse("item-appareillage-cocher", args=[item.pk])).status_code, 200)

    def test_retex_lecture_transverse_sans_decision(self):
        domaine = retex_services.domaines_du_navire(self.bre.pk).first()
        proposition = retex_services.proposer(self.equipier, "Fuite", "Constat", "Enseignement", domaine.pk)
        second = User.objects.get(username="second_a")
        self.assertTrue(retex_services.peut_consulter(second, proposition))
        self.assertFalse(retex_services.peut_valider(second, proposition))
        with self.assertRaises(PermissionError):
            retex_services.valider(second, proposition)
        with self.assertRaises(PermissionError):
            retex_services.refuser(second, proposition, "non")
        self.assertEqual(Retex.objects.get(pk=proposition.pk).etat, Retex.ETAT_PROPOSE)
        autre = retex_services.proposer(second, "Idée du second", "Constat", "Enseignement", domaine.pk)
        self.assertEqual(autre.auteur.username, "second_a")
        retex_services.valider(User.objects.get(username="chef_service_a"), proposition)
        self.assertEqual(Retex.objects.get(pk=proposition.pk).etat, Retex.ETAT_VALIDE)

    def test_documentation_postes_rondes_sans_gestion(self):
        from documentation import services as documentation

        second = User.objects.get(username="second_a")
        self.assertFalse(documentation.peut_rediger(second))
        self.assertFalse(postes.peut_gerer(second))
        self.assertFalse(rondes.peut_gerer_modeles(second))
        self.assertTrue(rondes.peut_gerer_modeles(User.objects.get(username="chef_service_a")))
        with self.assertRaises(PermissionError):
            postes.creer_poste(second, "Poste", f"ship:{self.bre.pk}")
        for url in ("/postes/", "/rondes/", "/documentation/", "/formations/", "/retex/"):
            self.assertEqual(self.client_de("second_a").get(url).status_code, 200, url)

    def test_formation_pas_de_validation_universelle(self):
        from training.models import TrainingCourse, peut_valider_formation

        course = TrainingCourse.objects.first()
        if course:
            self.assertFalse(peut_valider_formation(User.objects.get(username="second_a"), course, self.bre))


class DemandeEtVisaDuSecondTests(Base):
    def test_le_second_n_est_pas_responsable_mais_reste_interlocuteur(self):
        second = User.objects.get(username="second_a")
        self.assertNotIn(second, demandes.responsables_possibles(self.equipier))
        self.assertIn(second, demandes.interlocuteurs_possibles(self.demande))
        self.assertTrue(demandes.peut_consulter(second, self.demande))
        self.assertFalse(demandes.peut_piloter(second, self.demande))
        demandes.ajouter_interlocuteur(self.demande, self.chef_section, second)
        self.assertTrue(self.demande.interlocuteurs.filter(pk=second.pk).exists())
        self.assertTrue(Notification.objects.filter(user=second, verb__contains="ajouté").exists())
        reponse = self.client_de("second_a").post(f"/demandes/{self.demande.pk}/commentaire/", {"body": "Je coordonne."})
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(self.demande.interlocuteurs.filter(pk=second.pk).exists())

    def proposition_au_visa_coma(self):
        categorie = CategorieCatalogue.objects.get(nom="Extincteurs")
        self.client_de("chef_section_a").post(reverse("catalogue-proposition-nouvelle"), {
            "designation": "Extincteur test visa", "categorie": str(categorie.pk), "marque": "Sicli"})
        proposition = PropositionArticle.objects.get(designation="Extincteur test visa")
        for compte in ("chef_secteur_a", "chef_service_a"):
            self.client_de(compte).post(reverse("catalogue-proposition-viser", args=[proposition.pk]), {"etape": proposition.etat})
            proposition.refresh_from_db()
        return proposition

    def test_repli_sur_le_grade_ferme_et_visa_coma_du_second_conserve(self):
        proposition = self.proposition_au_visa_coma()
        second = User.objects.get(username="second_a")
        # Avec un titulaire COMA, seul lui vise : ni le grade ni le second.
        self.assertFalse(habilite_coma(second, proposition))
        self.assertTrue(habilite_coma(User.objects.get(username="coma_comanav"), proposition))
        # Sans titulaire, le second garde son visa nommé par le circuit ; le grade seul ne valide rien d'autre.
        Service.objects.filter(pk=proposition.service_id).update(commandant_adjoint="COMAVIA")
        proposition.refresh_from_db()
        self.assertTrue(habilite_coma(second, proposition))
        self.assertFalse(habilite_coma(User.objects.get(username="equipier_a"), proposition))
        self.assertFalse(peut_valider_proposition_bord(second, self.chef_section))
        self.assertTrue(peut_valider_proposition_bord(User.objects.get(username="cdt_a"), self.chef_section))
