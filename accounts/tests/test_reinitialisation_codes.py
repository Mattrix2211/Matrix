"""AC-16 : réinitialisation par code à usage unique — expiration, essais, réutilisation, autre compte, vérification indépendante."""
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts import reinitialisation
from accounts.models import AuditLog, DemandeReinitialisation, UserProfile
from notifications.models import Notification
from org.models import Ship

User = get_user_model()
NOUVEAU = "Nouveau-mdp-solide-42"


def _compte(nom, role="EQUIPIER", navire=None, technique=False, general=False, fonction=""):
    utilisateur = User.objects.create_user(username=nom, password="ancien-mdp-123")
    UserProfile.objects.filter(user=utilisateur).update(
        role=role, ship=navire, administrateur_technique=technique, administrateur_general=general, fonction_coma=fonction)
    return User.objects.get(pk=utilisateur.pk)


class MondeCodes(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Bretagne", code="BRE")
        self.autre_navire = Ship.objects.create(name="Normandie", code="NOR")
        self.technique = _compte("technique", navire=self.navire, technique=True)
        self.technique2 = _compte("technique2", navire=self.navire, technique=True)
        self.general = _compte("general", general=True)
        self.general2 = _compte("general2", general=True)
        self.marin = _compte("marin", navire=self.navire)
        self.autre = _compte("autre", navire=self.navire)
        self.chef_service = _compte("chef_service", "CHEF_SERVICE", self.navire)
        self.commandant = _compte("commandant", "COMMANDANT", self.navire)
        self.adjoint = _compte("adjoint", "ETAT_MAJOR", self.navire, fonction="COMAEQ")


class ParcoursSimpleTests(MondeCodes):
    def test_parcours_complet_et_usage_unique(self):
        session = Client()
        session.force_login(self.marin)
        self.assertEqual(session.get(reverse("mon-profil")).status_code, 200)
        demande, code = reinitialisation.initier(self.technique, self.marin)
        self.assertFalse(demande.verification_requise)
        reinitialisation.utiliser("marin", code, "", NOUVEAU)
        self.marin.refresh_from_db()
        self.assertTrue(self.marin.check_password(NOUVEAU))
        self.assertFalse(self.marin.check_password("ancien-mdp-123"))
        self.assertEqual(session.get(reverse("mon-profil")).status_code, 302)  # ancienne session révoquée
        self.assertTrue(Notification.objects.filter(user=self.marin, categorie="securite").exists())
        with self.assertRaises(ValidationError):  # le code est invalidé définitivement
            reinitialisation.utiliser("marin", code, "", "Autre-mdp-solide-77")
        self.assertTrue(User.objects.get(pk=self.marin.pk).check_password(NOUVEAU))

    def test_aucun_secret_ni_empreinte_lisible_dans_les_journaux_et_la_base(self):
        demande, code = reinitialisation.initier(self.technique, self.marin)
        reinitialisation.utiliser("marin", code, "", NOUVEAU)
        brut = code.replace("-", "")
        textes = [a.details for a in AuditLog.objects.all()] + [demande.code_initiateur, demande.code_verificateur]
        demande.refresh_from_db()
        textes += [demande.code_initiateur]
        self.assertFalse(any(code in t or brut in t or NOUVEAU in t for t in textes))
        self.assertTrue(demande.code_initiateur.startswith("pbkdf2_"))

    def test_code_incorrect_puis_blocage_apres_cinq_essais_meme_avec_le_bon_code(self):
        demande, code = reinitialisation.initier(self.technique, self.marin)
        for _ in range(5):
            with self.assertRaises(ValidationError):
                reinitialisation.utiliser("marin", "AAAA-BBBB-CCCC-DDDD", "", NOUVEAU)
        with self.assertRaises(ValidationError):
            reinitialisation.utiliser("marin", code, "", NOUVEAU)  # 6e essai : demande bloquée
        demande.refresh_from_db()
        self.assertEqual(demande.statut, DemandeReinitialisation.Statut.BLOQUEE)
        self.assertTrue(AuditLog.objects.filter(action="reinitialisation_bloquee", target_user=self.marin).exists())
        self.assertTrue(User.objects.get(pk=self.marin.pk).check_password("ancien-mdp-123"))

    def test_code_expire(self):
        demande, code = reinitialisation.initier(self.technique, self.marin)
        DemandeReinitialisation.objects.filter(pk=demande.pk).update(expire_le=timezone.now() - timedelta(seconds=1))
        with self.assertRaises(ValidationError):
            reinitialisation.utiliser("marin", code, "", NOUVEAU)
        demande.refresh_from_db()
        self.assertEqual(demande.statut, DemandeReinitialisation.Statut.EXPIREE)

    def test_validite_par_defaut_de_trente_minutes_et_bornes_non_contournables(self):
        demande, _ = reinitialisation.initier(self.technique, self.marin)
        delai = demande.expire_le - demande.created_at
        self.assertTrue(timedelta(minutes=29) < delai <= timedelta(minutes=31))
        from matrix import settings as reglages
        self.assertEqual(reglages._entier_borne("INEXISTANT_TEST", 30, 5, 120), 30)
        with mock.patch.dict("os.environ", {"INEXISTANT_TEST": "100000"}):
            self.assertEqual(reglages._entier_borne("INEXISTANT_TEST", 30, 5, 120), 120)
        with mock.patch.dict("os.environ", {"INEXISTANT_TEST": "0"}):
            self.assertEqual(reglages._entier_borne("INEXISTANT_TEST", 30, 5, 120), 5)

    def test_code_destine_a_un_autre_compte_ou_a_une_autre_demande(self):
        _, code_marin = reinitialisation.initier(self.technique, self.marin)
        _, code_autre = reinitialisation.initier(self.technique, self.autre)
        with self.assertRaises(ValidationError):
            reinitialisation.utiliser("autre", code_marin, "", NOUVEAU)
        with self.assertRaises(ValidationError):
            reinitialisation.utiliser("marin", code_autre, "", NOUVEAU)
        _, nouveau_code = reinitialisation.initier(self.technique, self.marin)  # annule la demande précédente
        with self.assertRaises(ValidationError):
            reinitialisation.utiliser("marin", code_marin, "", NOUVEAU)
        reinitialisation.utiliser("marin", nouveau_code, "", NOUVEAU)

    def test_identifiant_inconnu_et_code_faux_donnent_le_meme_message(self):
        reinitialisation.initier(self.technique, self.marin)
        messages = set()
        for identifiant in ("inconnu", "marin"):
            with self.assertRaises(ValidationError) as ctx:
                reinitialisation.utiliser(identifiant, "AAAA-BBBB-CCCC-DDDD", "", NOUVEAU)
            messages.add(" ".join(ctx.exception.messages))
        self.assertEqual(len(messages), 1)

    def test_mot_de_passe_trop_faible_refuse_sans_consommer_le_code(self):
        _, code = reinitialisation.initier(self.technique, self.marin)
        with self.assertRaises(ValidationError):
            reinitialisation.utiliser("marin", code, "", "123")
        reinitialisation.utiliser("marin", code, "", NOUVEAU)

    def test_consommation_concurrente_une_seule_reussit(self):
        _, code = reinitialisation.initier(self.technique, self.marin)

        def concurrent(*args, **kwargs):  # un second appel termine le parcours entre la vérification et l'écriture
            DemandeReinitialisation.objects.filter(user=self.marin).update(statut=DemandeReinitialisation.Statut.UTILISEE)

        with mock.patch("accounts.reinitialisation.validate_password", side_effect=concurrent):
            with self.assertRaises(ValidationError):
                reinitialisation.utiliser("marin", code, "", NOUVEAU)
        self.assertTrue(User.objects.get(pk=self.marin.pk).check_password("ancien-mdp-123"))

    def test_page_publique_sans_connexion_et_message_d_erreur_unique(self):
        _, code = reinitialisation.initier(self.technique, self.marin)
        client = Client()
        self.assertEqual(client.get(reverse("reinitialisation-mot-de-passe")).status_code, 200)
        mauvais = client.post(reverse("reinitialisation-mot-de-passe"), {
            "identifiant": "marin", "code_initiateur": "AAAA-BBBB-CCCC-DDDD", "nouveau_mot_de_passe": NOUVEAU, "confirmation": NOUVEAU})
        self.assertEqual(mauvais.status_code, 400)
        bon = client.post(reverse("reinitialisation-mot-de-passe"), {
            "identifiant": "marin", "code_initiateur": code, "nouveau_mot_de_passe": NOUVEAU, "confirmation": NOUVEAU})
        self.assertRedirects(bon, reverse("login"), fetch_redirect_response=False)
        self.assertTrue(Client().login(username="marin", password=NOUVEAU))


class VerificationIndependanteTests(MondeCodes):
    def test_un_compte_porteur_d_autorite_exige_deux_codes_et_un_second_responsable(self):
        demande, code_a = reinitialisation.initier(self.technique, self.chef_service)
        self.assertTrue(demande.verification_requise)
        self.assertEqual(demande.statut, DemandeReinitialisation.Statut.EN_ATTENTE_VERIFICATION)
        with self.assertRaises(ValidationError):  # l'initiateur seul : le premier code ne suffit pas
            reinitialisation.utiliser("chef_service", code_a, "", NOUVEAU)

    def test_l_initiateur_ne_peut_pas_valider_sa_propre_demande(self):
        demande, code_a = reinitialisation.initier(self.technique, self.chef_service)
        with self.assertRaises(PermissionDenied):
            reinitialisation.verifier_identite(self.technique, demande.pk)
        self.assertNotIn(demande, reinitialisation.demandes_a_verifier_par(self.technique))
        with self.assertRaises(ValidationError):
            reinitialisation.utiliser("chef_service", code_a, code_a, NOUVEAU)

    def test_seul_un_second_responsable_habilite_valide_le_titulaire_exclu_aussi(self):
        demande, code_a = reinitialisation.initier(self.technique, self.chef_service)
        for intrus in (self.commandant, self.marin, self.chef_service):
            with self.assertRaises(PermissionDenied):
                reinitialisation.verifier_identite(intrus, demande.pk)
        autre_navire = _compte("technique_autre", navire=self.autre_navire, technique=True)
        with self.assertRaises(PermissionDenied):
            reinitialisation.verifier_identite(autre_navire, demande.pk)
        _, code_b = reinitialisation.verifier_identite(self.technique2, demande.pk)
        with self.assertRaises(ValidationError):  # un seul des deux codes
            reinitialisation.utiliser("chef_service", code_a, "", NOUVEAU)
        with self.assertRaises(ValidationError):
            reinitialisation.utiliser("chef_service", code_b, code_a, NOUVEAU)  # codes inversés
        reinitialisation.utiliser("chef_service", code_a, code_b, NOUVEAU)
        self.assertTrue(User.objects.get(pk=self.chef_service.pk).check_password(NOUVEAU))
        self.assertTrue(AuditLog.objects.filter(action="reinitialisation_identite_verifiee", actor=self.technique2).exists())

    def test_l_administrateur_general_verifie_et_les_comptes_de_niveau_general_exigent_un_administrateur_general(self):
        demande, code_a = reinitialisation.initier(self.general, self.commandant)
        with self.assertRaises(PermissionDenied):  # un administrateur technique n'est pas compétent pour un commandant
            reinitialisation.verifier_identite(self.technique2, demande.pk)
        with self.assertRaises(PermissionDenied):
            reinitialisation.verifier_identite(self.general, demande.pk)  # ni l'initiateur
        _, code_b = reinitialisation.verifier_identite(self.general2, demande.pk)
        reinitialisation.utiliser("commandant", code_a, code_b, NOUVEAU)
        self.assertTrue(User.objects.get(pk=self.commandant.pk).check_password(NOUVEAU))

    def test_la_verification_expire_avec_la_demande_et_ne_se_rejoue_pas(self):
        demande, _ = reinitialisation.initier(self.technique, self.chef_service)
        reinitialisation.verifier_identite(self.technique2, demande.pk)
        with self.assertRaises(ValidationError):
            reinitialisation.verifier_identite(self.technique2, demande.pk)

    def test_pages_de_verification_et_codes_web(self):
        client = Client()
        client.force_login(self.technique)
        reponse = client.post(reverse("user-directory"), {"action": "set_password", "pk": self.chef_service.pk})
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "second responsable")
        pk = DemandeReinitialisation.objects.get(user=self.chef_service).pk
        verif = Client()
        verif.force_login(self.technique2)
        self.assertContains(verif.get(reverse("verifications-identite")), "Vérifications d'identité")
        suite = verif.post(reverse("verifications-identite"), {"pk": pk})
        self.assertEqual(suite.status_code, 200)
        self.assertEqual(suite["Cache-Control"], "no-store")
        self.assertEqual(client.post(reverse("verifications-identite"), {"pk": pk}).status_code, 302)  # l'initiateur est refusé
        refus = Client()
        refus.force_login(self.marin)
        self.assertEqual(refus.post(reverse("verifications-identite"), {"pk": pk}).status_code, 302)
        self.assertEqual(DemandeReinitialisation.objects.get(pk=pk).verificateur, self.technique2)


class InterfaceVerificationTests(MondeCodes):
    def test_le_lien_et_le_compteur_ne_sont_proposes_qu_aux_responsables_competents(self):
        reinitialisation.initier(self.technique, self.chef_service)
        verificateur = Client()
        verificateur.force_login(self.technique2)
        page = verificateur.get(reverse("user-directory"))
        self.assertContains(page, "Vérifications d'identité")
        self.assertEqual(page.context["verifications_en_attente"], 1)
        initiateur = Client()
        initiateur.force_login(self.technique)
        self.assertEqual(initiateur.get(reverse("user-directory")).context["verifications_en_attente"], 0)  # pas la sienne
        simple = Client()
        simple.force_login(self.commandant)
        self.assertNotContains(simple.get(reverse("user-directory")), "Vérifications d'identité")


class NotificationTests(MondeCodes):
    def test_le_titulaire_est_notifie_a_la_demande_et_a_l_aboutissement(self):
        from notifications.models import Notification
        demande, code = reinitialisation.initier(self.technique, self.marin)
        self.assertEqual(Notification.objects.filter(user=self.marin, categorie="securite").count(), 1)
        reinitialisation.utiliser("marin", code, "", NOUVEAU)
        self.assertEqual(Notification.objects.filter(user=self.marin, categorie="securite").count(), 2)
