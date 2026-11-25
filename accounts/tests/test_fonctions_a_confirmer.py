"""AC-14 : espace « Fonctions à confirmer » — confirmation, correction, refus, autorités, concurrence, cohérence."""
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts import fonctions
from accounts.models import AuditLog, FonctionAConfirmer, UserProfile
from org.models import Ship

User = get_user_model()


def _compte(nom, role, navire, technique=False):
    utilisateur = User.objects.create_user(username=nom, password="pass")
    UserProfile.objects.update_or_create(user=utilisateur, defaults={"role": role, "ship": navire, "administrateur_technique": technique})
    return User.objects.get(pk=utilisateur.pk)


class FonctionsAConfirmerTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Bretagne", code="BRE")
        self.autre = Ship.objects.create(name="Normandie", code="NOR")
        self.cdt = _compte("cdt", "COMMANDANT", self.navire)
        self.cdt_autre = _compte("cdt_autre", "COMMANDANT", self.autre)
        self.second = _compte("second", "COMMANDANT_EN_SECOND", self.navire)
        self.technique = _compte("tech", "EQUIPIER", self.navire, technique=True)
        self.ancien = _compte("ancien", "EQUIPIER", self.navire, technique=True)
        self.demande = FonctionAConfirmer.objects.create(user=self.ancien, ship=self.navire, fonction_ancienne="COMANAV")

    def _profil(self, compte):
        return UserProfile.objects.get(user=compte)

    def test_sans_confirmation_la_fonction_ne_donne_aucun_droit(self):
        self.assertEqual(self._profil(self.ancien).role, "EQUIPIER")
        self.assertEqual(self._profil(self.ancien).fonction_coma, "")

    def test_confirmation_attribue_la_fonction_sans_toucher_aux_droits_techniques(self):
        fonctions.decider(self.cdt, self.demande.pk, fonctions.CONFIRMER)
        profil = self._profil(self.ancien)
        self.assertEqual((profil.role, profil.fonction_coma, profil.administrateur_technique), ("ETAT_MAJOR", "COMANAV", True))
        self.demande.refresh_from_db()
        self.assertEqual((self.demande.statut, self.demande.decide_par), ("CONFIRMEE", self.cdt))
        self.assertTrue(AuditLog.objects.filter(action="fonction_a_confirmer_confirmer", target_user=self.ancien).exists())
        self.assertEqual(fonctions.anomalies_de_coherence(), [])

    def test_correction_et_refus(self):
        fonctions.decider(self.cdt, self.demande.pk, fonctions.CORRIGER, "COMOPS")
        self.assertEqual(self._profil(self.ancien).fonction_coma, "COMOPS")
        autre = FonctionAConfirmer.objects.create(user=self.technique, ship=self.navire, fonction_ancienne="COMAEQ")
        fonctions.decider(self.cdt, autre.pk, fonctions.REFUSER)
        self.assertEqual((self._profil(self.technique).role, self._profil(self.technique).fonction_coma), ("EQUIPIER", ""))
        self.assertEqual(fonctions.anomalies_de_coherence(), [])

    def test_seule_l_autorite_competente_du_batiment_decide(self):
        for acteur in (self.second, self.technique, self.cdt_autre):
            with self.assertRaises(PermissionDenied):
                fonctions.decider(acteur, self.demande.pk, fonctions.CONFIRMER)
        self.assertEqual(self._profil(self.ancien).role, "EQUIPIER")

    def test_personne_ne_decide_pour_soi_meme(self):
        propre = FonctionAConfirmer.objects.create(user=self.cdt, ship=self.navire, fonction_ancienne="COMAEQ")
        with self.assertRaises(PermissionDenied):
            fonctions.decider(self.cdt, propre.pk, fonctions.CONFIRMER)

    def test_double_traitement_et_fonction_deja_tenue_refuses(self):
        fonctions.decider(self.cdt, self.demande.pk, fonctions.CONFIRMER)
        with self.assertRaises(ValidationError):
            fonctions.decider(self.cdt, self.demande.pk, fonctions.REFUSER)
        autre = FonctionAConfirmer.objects.create(user=self.technique, ship=self.navire, fonction_ancienne="COMANAV")
        with self.assertRaises(ValidationError):
            fonctions.decider(self.cdt, autre.pk, fonctions.CONFIRMER)  # COMANAV déjà tenue par l'ancien

    def test_page_et_compteur(self):
        self.client.force_login(self.cdt)
        self.assertContains(self.client.get(reverse("user-directory")), "Fonctions à confirmer")
        reponse = self.client.get(reverse("fonctions-a-confirmer"))
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(fonctions.nombre_en_attente(self.cdt), 1)
        self.assertEqual(fonctions.nombre_en_attente(self.cdt_autre), 0)
        self.client.post(reverse("fonctions-a-confirmer"), {"pk": self.demande.pk, "decision": "confirmer"})
        self.assertEqual(self._profil(self.ancien).role, "ETAT_MAJOR")
        for compte in (self.technique, self.second):
            self.client.force_login(compte)
            self.assertEqual(self.client.get(reverse("fonctions-a-confirmer")).status_code, 403)
            self.assertEqual(self.client.post(reverse("fonctions-a-confirmer"), {"pk": self.demande.pk, "decision": "refuser"}).status_code, 403)
