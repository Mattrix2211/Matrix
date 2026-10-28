"""Annonces : ciblage par périmètre, publication selon le seuil, diffusion, accusé de lecture, versions."""
import threading
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from annonces import services
from annonces.models import Annonce
from dashboard.aujourdhui import a_faire
from matrix.core.role_thresholds import invalidate_cache
from notifications.models import Notification
from org.models import RoleThresholdConfig, Sector, Service, Ship


class AnnoncesBase(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Bretagne annonces", code="BA")
        self.energie = Service.objects.create(ship=self.navire, name="Énergie")
        self.pont = Service.objects.create(ship=self.navire, name="Pont")
        self.propulsion = Sector.objects.create(service=self.energie, name="Propulsion")
        self.cdt = self._marin("cdt", None, None, "COMMANDANT")
        self.chef_energie = self._marin("chef_energie", self.energie, None, "CHEF_SERVICE")
        self.marin = self._marin("marin", self.energie, self.propulsion, "EQUIPIER")
        self.matelot_pont = self._marin("pont", self.pont, None, "EQUIPIER")
        autre = Ship.objects.create(name="Autre", code="AU")
        self.etranger = self._marin("etranger", None, None, "EQUIPIER", navire=autre)
        self.jour = timezone.localdate()

    def _marin(self, nom, service, secteur, role, navire=None):
        user = User.objects.create_user(username=nom, password="pass")
        p = user.profile
        p.role, p.ship, p.service, p.sector = role, navire or self.navire, service, secteur
        p.save()
        return user


class PublicationTests(AnnoncesBase):
    def test_ciblage_service_et_notifications(self):
        annonce = services.publier(self.chef_energie, "Exercice incendie", "Jeudi 14h", "warning", f"service:{self.energie.pk}")
        self.assertEqual(set(services.destinataires(annonce)), {self.chef_energie, self.marin})
        self.assertTrue(Notification.objects.filter(user=self.marin, level="warning", verb__startswith="Annonce").exists())
        self.assertFalse(Notification.objects.filter(user=self.matelot_pont).exists())
        self.assertFalse(Notification.objects.filter(user=self.chef_energie).exists())
        self.assertTrue(services.annonces_visibles(self.marin).filter(pk=annonce.pk).exists())
        for exclu in (self.matelot_pont, self.etranger):
            self.assertFalse(services.annonces_visibles(exclu).filter(pk=annonce.pk).exists())
            self.assertFalse(services.peut_consulter(exclu, annonce))

    def test_un_chef_de_service_ne_cible_pas_un_autre_service_ni_le_batiment(self):
        for cible in (f"service:{self.pont.pk}", f"ship:{self.navire.pk}"):
            with self.assertRaises(PermissionError):
                services.publier(self.chef_energie, "x", "y", "info", cible)

    def test_seuil_configurable(self):
        with self.assertRaises(PermissionError):
            services.publier(self.marin, "x", "y", "info", f"sector:{self.propulsion.pk}")
        RoleThresholdConfig.objects.update_or_create(ship=self.navire, defaults={"thresholds": {"annonce_publication": "EQUIPIER"}})
        invalidate_cache(self.navire.pk)
        self.assertTrue(services.peut_publier(self.marin))
        services.publier(self.marin, "Message au secteur", "ok", "info", f"sector:{self.propulsion.pk}")

    def test_commandant_cible_tout_le_batiment_et_un_equipage(self):
        annonce = services.publier(self.cdt, "Ordre du jour", "Appareillage demain", "danger", f"ship:{self.navire.pk}")
        self.assertEqual(set(services.destinataires(annonce)), {self.cdt, self.chef_energie, self.marin, self.matelot_pont})
        self.marin.profile.equipage = "B"
        self.marin.profile.save()
        restreinte = services.publier(self.cdt, "Équipage B", "x", "info", f"ship:{self.navire.pk}", equipage="B")
        self.assertEqual(set(services.destinataires(restreinte)), {self.marin})

    def test_validations(self):
        with self.assertRaises(ValidationError):
            services.publier(self.cdt, " ", "y", "info", f"ship:{self.navire.pk}")
        with self.assertRaises(ValidationError):
            services.publier(self.cdt, "x", "y", "info", f"ship:{self.navire.pk}", date_fin=self.jour - timedelta(days=1))

    def test_date_d_effet_future_diffusee_plus_tard(self):
        annonce = services.publier(self.cdt, "Demain", "x", "info", f"ship:{self.navire.pk}", date_effet=self.jour + timedelta(days=1))
        self.assertFalse(Notification.objects.filter(user=self.marin).exists())
        self.assertEqual(services.a_lire(self.marin, self.jour), [])
        annonce.date_effet = self.jour
        annonce.save()
        self.assertEqual(services.diffuser_du_jour(), 1)
        self.assertEqual(services.diffuser_du_jour(), 0)
        self.assertEqual(Notification.objects.filter(user=self.marin).count(), 1)


class LectureTests(AnnoncesBase):
    def test_accuse_solde_l_alerte_et_se_suit(self):
        annonce = services.publier(self.cdt, "Consigne", "À lire", "warning", f"ship:{self.navire.pk}", accuse_requis=True)
        self.assertEqual(Notification.objects.filter(user=self.marin, action_requise=True, traitee_le__isnull=True).count(), 1)
        self.assertIn(annonce, services.a_lire(self.marin, self.jour))
        self.assertIn("Consigne", [e["titre"] for e in a_faire(self.marin, self.jour)])
        services.accuser(self.marin, annonce)
        self.assertEqual(services.a_lire(self.marin, self.jour), [])
        self.assertFalse(Notification.objects.filter(user=self.marin, action_requise=True, traitee_le__isnull=True).exists())
        etats = {l["user"].username: l["etat"] for l in services.suivi_lecture(annonce)}
        self.assertEqual(etats["marin"], "Accusé")
        self.assertEqual(etats["pont"], "Non lu")

    def test_ouvrir_suffit_sans_accuse_et_l_etranger_ne_peut_pas_accuser(self):
        annonce = services.publier(self.cdt, "Info", "x", "info", f"ship:{self.navire.pk}")
        self.client.force_login(self.marin)
        self.client.get(reverse("annonce-detail", args=[annonce.pk]))
        self.assertEqual(services.a_lire(self.marin, self.jour), [])
        accuse = services.publier(self.cdt, "Accusé", "x", "info", f"ship:{self.navire.pk}", accuse_requis=True)
        with self.assertRaises(PermissionError):
            services.accuser(self.etranger, accuse)
        with self.assertRaises(ValidationError):
            services.accuser(self.marin, annonce)

    def test_modification_cree_une_version_et_renouvelle_l_accuse(self):
        annonce = services.publier(self.cdt, "Consigne", "v1", "info", f"ship:{self.navire.pk}", accuse_requis=True)
        services.accuser(self.marin, annonce)
        services.modifier(self.cdt, annonce, "Consigne", "v2 corrigée", "warning")
        annonce.refresh_from_db()
        self.assertEqual((annonce.version, annonce.versions.count()), (2, 2))
        self.assertIn(annonce, services.a_lire(self.marin, self.jour))
        with self.assertRaises(PermissionError):
            services.modifier(self.marin, annonce, "x", "y", "info")

    def test_archivage(self):
        annonce = services.publier(self.cdt, "Vieille", "x", "info", f"ship:{self.navire.pk}", accuse_requis=True)
        services.archiver(self.cdt, annonce)
        self.assertEqual(services.a_lire(self.marin, self.jour), [])
        self.assertFalse(Notification.objects.filter(user=self.marin, action_requise=True, traitee_le__isnull=True).exists())


class PagesTests(AnnoncesBase):
    def test_pages_et_acces(self):
        annonce = services.publier(self.chef_energie, "Exercice", "Jeudi", "warning", f"service:{self.energie.pk}")
        self.client.force_login(self.marin)
        self.assertContains(self.client.get(reverse("annonces-index")), "Exercice")
        self.assertContains(self.client.get(reverse("annonce-detail", args=[annonce.pk])), "Jeudi")
        self.assertEqual(self.client.get(reverse("annonce-nouvelle")).status_code, 404)
        self.client.force_login(self.matelot_pont)
        self.assertEqual(self.client.get(reverse("annonce-detail", args=[annonce.pk])).status_code, 404)
        self.client.force_login(self.chef_energie)
        page = self.client.get(reverse("annonce-detail", args=[annonce.pk]))
        self.assertContains(page, "Suivi de lecture")
        self.assertEqual(self.client.post(reverse("annonce-nouvelle"), {
            "titre": "Hors périmètre", "corps": "x", "niveau": "info", "cible": f"service:{self.pont.pk}"}).status_code, 302)
        self.assertFalse(Annonce.objects.filter(titre="Hors périmètre").exists())


class EquipagesProposesTests(AnnoncesBase):
    def test_formulaire_propose_les_equipages_reels(self):
        self.marin.profile.equipage = "B"
        self.marin.profile.save()
        self.navire.equipage_a_bord = "A"
        self.navire.save()
        self.assertEqual(services.equipages_du_navire(self.cdt), ["A", "B"])
        self.client.force_login(self.cdt)
        page = self.client.get(reverse("annonce-nouvelle"))
        self.assertContains(page, '<option value="">Tous les équipages</option>', html=False)
        self.assertContains(page, '<option value="B">')

    def test_navire_sans_equipage_ne_propose_que_tous(self):
        self.assertEqual(services.equipages_du_navire(self.cdt), [])


class VisibiliteTemporelleTests(AnnoncesBase):
    def test_annonce_programmee_invisible_pour_un_destinataire(self):
        annonce = services.publier(self.cdt, "Demain", "x", "info", f"ship:{self.navire.pk}", date_effet=self.jour + timedelta(days=2))
        self.assertFalse(services.peut_consulter(self.marin, annonce))
        self.client.force_login(self.marin)
        self.assertNotContains(self.client.get(reverse("annonces-index")), "Demain")
        self.assertEqual(self.client.get(reverse("annonce-detail", args=[annonce.pk])).status_code, 404)
        self.client.force_login(self.cdt)
        self.assertContains(self.client.get(reverse("annonces-index")), "Programmées")
        self.assertEqual(self.client.get(reverse("annonce-detail", args=[annonce.pk])).status_code, 200)

    def test_version_lue_suit_la_modification_sans_accuse(self):
        annonce = services.publier(self.cdt, "Info", "v1", "info", f"ship:{self.navire.pk}")
        self.client.force_login(self.marin)
        self.client.get(reverse("annonce-detail", args=[annonce.pk]))
        services.modifier(self.cdt, annonce, "Info", "v2", "info")
        annonce.refresh_from_db()
        self.assertIn(annonce, services.a_lire(self.marin, self.jour))
        self.client.get(reverse("annonce-detail", args=[annonce.pk]))
        self.assertEqual(services.a_lire(self.marin, self.jour), [])

    def test_accuse_refuse_sur_annonce_archivee(self):
        annonce = services.publier(self.cdt, "Vieille", "x", "info", f"ship:{self.navire.pk}", accuse_requis=True)
        services.archiver(self.cdt, annonce)
        with self.assertRaises(ValidationError):
            services.accuser(self.marin, annonce)


class ModificationsSimultaneesTests(AnnoncesBase):
    def test_version_perimee_refusee_sans_rien_ecraser(self):
        annonce = services.publier(self.cdt, "Consigne", "v1", "info", f"ship:{self.navire.pk}")
        services.modifier(self.cdt, annonce, "Titre A", "corps A", "info", version_vue=1)
        autre = Annonce.objects.get(pk=annonce.pk)
        with self.assertRaises(services.ConflitVersion):
            services.modifier(self.cdt, autre, "Titre B", "corps B", "info", version_vue=1)
        annonce.refresh_from_db()
        self.assertEqual((annonce.version, annonce.titre, annonce.versions.count()), (2, "Titre A", 2))

    def test_page_reaffiche_la_saisie_apres_conflit(self):
        annonce = services.publier(self.cdt, "Consigne", "v1", "info", f"ship:{self.navire.pk}")
        services.modifier(self.cdt, annonce, "Titre A", "corps A", "info")
        self.client.force_login(self.cdt)
        reponse = self.client.post(reverse("annonce-action", args=[annonce.pk]), {
            "action": "modifier", "version": "1", "titre": "Titre B", "corps": "corps B", "niveau": "info"})
        self.assertEqual(reponse.status_code, 200)
        self.assertContains(reponse, "modifiée entre-temps")
        self.assertContains(reponse, 'value="Titre B"')
        self.assertContains(reponse, 'name="version" value="2"')
        annonce.refresh_from_db()
        self.assertEqual((annonce.titre, annonce.version), ("Titre A", 2))

    def test_formulaire_sans_version_refuse(self):
        annonce = services.publier(self.cdt, "Consigne", "v1", "info", f"ship:{self.navire.pk}")
        self.client.force_login(self.cdt)
        reponse = self.client.post(reverse("annonce-action", args=[annonce.pk]), {
            "action": "modifier", "titre": "T", "corps": "c", "niveau": "info"})
        self.assertEqual(reponse.status_code, 302)
        annonce.refresh_from_db()
        self.assertEqual(annonce.version, 1)


class ModificationsConcurrentesTests(TransactionTestCase):
    """Vraies connexions concurrentes : propre à PostgreSQL, SQLite verrouillant la base entière."""

    def _lancer(self, fonctions):
        resultats = [None] * len(fonctions)
        barriere = threading.Barrier(len(fonctions))

        def executer(i, fonction):
            try:
                barriere.wait()
                resultats[i] = fonction()
            except Exception as exc:  # remonté dans le thread principal
                resultats[i] = exc
            finally:
                connection.close()

        threads = [threading.Thread(target=executer, args=(i, f)) for i, f in enumerate(fonctions)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return resultats

    def _annonce(self):
        navire = Ship.objects.create(name="Concurrence", code="CO")
        cdt = User.objects.create_user(username="cdt_co", password="pass")
        # Équipage renseigné : sans lui, le filtre de ciblage échoue sur PostgreSQL (ANO-001, corrigé à part).
        cdt.profile.role, cdt.profile.ship, cdt.profile.equipage = "COMMANDANT", navire, "A"
        cdt.profile.save()
        return cdt, services.publier(cdt, "Consigne", "v1", "info", f"ship:{navire.pk}")

    def _coherent(self, annonce, attendu):
        annonce.refresh_from_db()
        derniere = annonce.versions.first()
        self.assertEqual(annonce.version, attendu)
        self.assertEqual((derniere.numero, derniere.titre, derniere.corps), (annonce.version, annonce.titre, annonce.corps))
        self.assertEqual(sorted(annonce.versions.values_list("numero", flat=True)), list(range(1, attendu + 1)))

    def test_deux_modifications_depuis_la_meme_version_une_seule_gagne(self):
        if connection.vendor != "postgresql":
            self.skipTest("Concurrence réelle testée sur PostgreSQL seulement.")
        cdt, annonce = self._annonce()

        def modification(nom):
            return lambda: services.modifier(
                cdt, Annonce.objects.get(pk=annonce.pk), f"Titre {nom}", f"corps {nom}", "info", version_vue=1)

        resultats = self._lancer([modification("A"), modification("B")])
        self.assertEqual(sum(isinstance(r, Annonce) for r in resultats), 1, resultats)
        self.assertEqual(sum(isinstance(r, services.ConflitVersion) for r in resultats), 1, resultats)
        self._coherent(annonce, 2)

    def test_modifications_sans_version_vue_s_enchainent(self):
        if connection.vendor != "postgresql":
            self.skipTest("Concurrence réelle testée sur PostgreSQL seulement.")
        cdt, annonce = self._annonce()
        resultats = self._lancer([
            (lambda n=n: services.modifier(cdt, Annonce.objects.get(pk=annonce.pk), f"Titre {n}", f"corps {n}", "info"))
            for n in range(4)])
        self.assertTrue(all(isinstance(r, Annonce) for r in resultats), resultats)
        self._coherent(annonce, 5)

    def test_formulaires_http_concurrents_pas_de_500(self):
        if connection.vendor != "postgresql":
            self.skipTest("Concurrence réelle testée sur PostgreSQL seulement.")
        cdt, annonce = self._annonce()

        def envoi(nom):
            def poster():
                client = Client()
                client.force_login(cdt)
                return client.post(reverse("annonce-action", args=[annonce.pk]), {
                    "action": "modifier", "version": "1", "titre": f"Titre {nom}", "corps": f"corps {nom}", "niveau": "info"}).status_code
            return poster

        codes = self._lancer([envoi("A"), envoi("B")])
        self.assertEqual(sorted(codes), [200, 302])
        self._coherent(annonce, 2)
