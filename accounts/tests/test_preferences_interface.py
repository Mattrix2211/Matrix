"""Préférences d'interface par marin : liste blanche, isolation, fusion, rendu serveur, signature des droits."""
import threading

from django.contrib.auth.models import User
from django.db import connection
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from accounts import preferences
from org.models import Ship


def _marin(nom, navire, equipage):
    user = User.objects.create_user(username=nom, password="pass")
    profil = user.profile
    profil.ship, profil.equipage = navire, equipage
    profil.save()
    return user


class PreferencesBase(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Frégate test", code="FT-PR", double_equipage=True, equipage_a_bord="A")
        self.marin = _marin("martin", self.navire, "A")
        self.terre = _marin("terre", self.navire, "B")
        self.client.login(username="martin", password="pass")
        self.url = reverse("enregistrer-preference")

    def _envoyer(self, cle, sous_cle, valeur, client=None):
        return (client or self.client).post(self.url, {"cle": cle, "sous_cle": sous_cle, "valeur": valeur})

    def _prefs(self, user):
        user.profile.refresh_from_db()
        return user.profile.preferences_interface


class EnregistrementTests(PreferencesBase):
    def test_groupe_enregistre(self):
        self.assertEqual(self._envoyer("menu_groupes", "Mon quotidien", "0").status_code, 204)
        self.assertEqual(self._prefs(self.marin), {"menu_groupes": {"Mon quotidien": False}})

    def test_aide_enregistree_puis_supprimee(self):
        self._envoyer("aides_vues", "acces", "0123456789ab")
        self.assertEqual(self._prefs(self.marin)["aides_vues"], {"acces": "0123456789ab"})
        self._envoyer("aides_vues", "acces", "")
        self.assertEqual(self._prefs(self.marin)["aides_vues"], {})

    def test_liste_blanche_refuse_tout_le_reste(self):
        for cle, sous_cle, valeur in (
            ("inconnue", "x", "1"), ("menu_groupes", "Groupe inventé", "1"), ("menu_groupes", "Mon quotidien", "oui"),
            ("aides_vues", "autre", "0123456789ab"), ("aides_vues", "acces", "pas-une-signature"), ("", "", ""),
        ):
            self.assertEqual(self._envoyer(cle, sous_cle, valeur).status_code, 400, (cle, sous_cle, valeur))
        self.assertEqual(self._prefs(self.marin), {})

    def test_taille_limitee(self):
        profil = self.marin.profile
        profil.preferences_interface = {"menu_groupes": {"x" * preferences.TAILLE_MAX: True}}
        profil.save()
        self.assertEqual(self._envoyer("menu_groupes", "Mon quotidien", "1").status_code, 400)

    def test_fusion_conserve_les_autres_reglages(self):
        self._envoyer("menu_groupes", "Mon quotidien", "0")
        self._envoyer("aides_vues", "acces", "0123456789ab")
        self._envoyer("menu_groupes", "Mon quotidien", "1")
        self.assertEqual(
            self._prefs(self.marin), {"menu_groupes": {"Mon quotidien": True}, "aides_vues": {"acces": "0123456789ab"}}
        )

    def test_isolation_entre_deux_marins_du_meme_navire(self):
        self._envoyer("menu_groupes", "Mon quotidien", "0")
        self.assertEqual(self._prefs(self.terre), {})

    def test_anonyme_redirige_sans_ecriture(self):
        reponse = self._envoyer("menu_groupes", "Mon quotidien", "0", client=Client())
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(self._prefs(self.marin), {})

    def test_get_refuse_et_csrf_exige(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        strict.login(username="martin", password="pass")
        self.assertEqual(strict.post(self.url, {"cle": "menu_groupes", "sous_cle": "Mon quotidien", "valeur": "0"}).status_code, 403)

    def test_champs_existants_non_touches(self):
        profil = self.marin.profile
        profil.barre_laterale_repliee, profil.theme = True, "sombre"
        profil.save()
        self._envoyer("menu_groupes", "Mon quotidien", "0")
        profil.refresh_from_db()
        self.assertEqual((profil.barre_laterale_repliee, profil.theme), (True, "sombre"))

    def test_aucun_journal_d_audit(self):
        from accounts.models import AuditLog
        avant = AuditLog.objects.count()
        self._envoyer("menu_groupes", "Mon quotidien", "0")
        self.assertEqual(AuditLog.objects.count(), avant)


class RenduServeurTests(PreferencesBase):
    def test_groupe_replie_rendu_par_le_serveur(self):
        self._envoyer("menu_groupes", "Équipements", "0")
        html = self.client.get("/").content.decode()
        debut = html.index('data-groupe="Équipements"')
        self.assertIn("mx-lateral__groupe--ferme", html[html.rindex("<section", 0, debut):debut])

    def test_ancien_localstorage_non_repris(self):
        html = self.client.get("/").content.decode()
        self.assertNotIn("localStorage", html)
        self.assertNotIn("mx-menu-groupes", html)

    def test_aide_rouverte_quand_le_contexte_d_autorisation_change(self):
        self.client.logout()
        self.client.login(username="terre", password="pass")
        html = self.client.get("/").content.decode()
        self.assertIn('data-aide="acces"', html)
        signature = html.split('data-signature="')[1].split('"')[0]
        self.assertRegex(html, r'<details class="mx-acces"[^>]* open>')
        self._envoyer("aides_vues", "acces", signature)
        self.assertNotRegex(self.client.get("/").content.decode(), r'<details class="mx-acces"[^>]* open>')
        # Même contexte : l'aide reste refermée. Autre rôle : la signature change et l'aide se rouvre.
        self.assertEqual(self.client.get("/").content.decode().count(" open>"), 0)
        profil = self.terre.profile
        profil.role = "CHEF_SECTEUR"
        profil.save()
        self.assertRegex(self.client.get("/").content.decode(), r'<details class="mx-acces"[^>]* open>')

    def test_signature_change_avec_l_equipage_le_role_et_l_etat_a_terre(self):
        base = preferences.signature_droits(self.terre, True, False)
        self.assertNotEqual(base, preferences.signature_droits(self.terre, False, False))
        self.assertNotEqual(base, preferences.signature_droits(self.terre, True, True))
        profil = self.terre.profile
        profil.equipage = "A"
        self.assertNotEqual(base, preferences.signature_droits(self.terre, True, False))

    def test_les_preferences_ne_donnent_aucun_droit(self):
        self._envoyer("menu_groupes", "Administration", "1")
        self.assertNotIn(b"/users/nouveau/", self.client.get("/").content)


class ConcurrenceTests(TransactionTestCase):
    def test_deux_postes_n_effacent_pas_leurs_reglages(self):
        if connection.vendor != "postgresql":
            self.skipTest("Verrou de ligne : concurrence réelle testée sur PostgreSQL seulement.")
        navire = Ship.objects.create(name="Frégate test", code="FT-CC")
        marin = _marin("martin", navire, "")
        erreurs = []

        def ecrire(cle, sous_cle, valeur):
            try:
                preferences.enregistrer(marin, cle, sous_cle, valeur)
            except Exception as exc:  # noqa: BLE001
                erreurs.append(exc)
            finally:
                connection.close()

        fils = [
            threading.Thread(target=ecrire, args=("menu_groupes", "Mon quotidien", "0")),
            threading.Thread(target=ecrire, args=("aides_vues", "acces", "0123456789ab")),
        ]
        for fil in fils:
            fil.start()
        for fil in fils:
            fil.join()
        marin.profile.refresh_from_db()
        self.assertEqual(erreurs, [])
        self.assertEqual(
            marin.profile.preferences_interface,
            {"menu_groupes": {"Mon quotidien": False}, "aides_vues": {"acces": "0123456789ab"}},
        )
