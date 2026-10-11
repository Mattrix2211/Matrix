"""Documentation : circuit proposer → valider → publier, versions conservées, ciblage, contexte et recherche."""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from documentation import services
from documentation.models import Document, VersionDocument
from matrix.core.recherche import rechercher
from notifications.models import Notification
from org.models import Sector, Service, Ship
from taches.models import Tache


class DocsBase(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Docs", code="DO")
        self.energie = Service.objects.create(ship=self.navire, name="Énergie")
        self.pont = Service.objects.create(ship=self.navire, name="Pont")
        self.secteur = Sector.objects.create(service=self.energie, name="Propulsion")
        self.redacteur = self._marin("chef_section", self.energie, self.secteur, "CHEF_SECTEUR")
        self.chef = self._marin("chef_energie", self.energie, None, "CHEF_SERVICE")
        self.chef2 = self._marin("chef_energie2", self.energie, None, "CHEF_SERVICE")
        self.marin = self._marin("marin", self.energie, self.secteur, "EQUIPIER")
        self.pont_marin = self._marin("pont", self.pont, None, "EQUIPIER")
        self.etranger = self._marin("etranger", None, None, "EQUIPIER", navire=Ship.objects.create(name="Autre", code="AU"))

    def _marin(self, nom, service, secteur, role, navire=None):
        user = User.objects.create_user(username=nom, password="pass")
        p = user.profile
        p.role, p.ship, p.service, p.sector = role, navire or self.navire, service, secteur
        p.save()
        return user

    def _publie(self, titre="Consignes de démarrage pompe", contenu="Ouvrir la vanne A."):
        document = services.creer_document(self.chef, titre, f"service:{self.energie.pk}", contenu, domaine="Propulsion")
        services.soumettre(self.chef, document.versions.get())
        services.valider(self.chef2, document.versions.get())
        return document


class CircuitTests(DocsBase):
    def test_brouillon_invisible_puis_publication_et_historique(self):
        document = services.creer_document(self.chef, "Procédure X", f"service:{self.energie.pk}", "v1", domaine="Sécurité")
        self.assertFalse(services.documents_visibles(self.marin).filter(pk=document.pk).exists())  # brouillon
        services.soumettre(self.chef, document.versions.get())
        self.assertEqual(Notification.objects.filter(user=self.chef2, action_requise=True, traitee_le__isnull=True).count(), 1)
        with self.assertRaises(PermissionError):  # pas de validation de sa propre version
            services.valider(self.chef, document.versions.get())
        services.valider(self.chef2, document.versions.get())
        self.assertTrue(services.documents_visibles(self.marin).filter(pk=document.pk).exists())
        self.assertFalse(Notification.objects.filter(action_requise=True, traitee_le__isnull=True).exists())
        # amélioration proposée par un simple marin : l'ancienne version reste applicable
        proposition = services.proposer_amelioration(self.marin, document, "v2 corrigée", "Étape ajoutée")
        self.assertEqual(document.version_applicable.numero, 1)
        with self.assertRaises(ValidationError):
            services.proposer_amelioration(self.marin, document, "autre", "")
        services.valider(self.chef, proposition)
        document.refresh_from_db()
        self.assertEqual(document.version_applicable.numero, 2)
        self.assertEqual(sorted(document.versions.values_list("etat", flat=True)), ["OBSOLETE", "PUBLIEE"])

    def test_refus_motive(self):
        document = services.creer_document(self.chef, "Procédure Y", f"service:{self.energie.pk}", "v1")
        services.soumettre(self.chef, document.versions.get())
        with self.assertRaises(ValidationError):
            services.refuser(self.chef2, document.versions.get(), " ")
        services.refuser(self.chef2, document.versions.get(), "Source manquante")
        self.assertEqual(document.versions.get().etat, VersionDocument.ETAT_REFUSEE)
        self.assertTrue(Notification.objects.filter(user=self.chef, verb__contains="refusée").exists())

    def test_droits_et_regles_d_origine(self):
        with self.assertRaises(PermissionError):
            services.creer_document(self.marin, "x", f"service:{self.energie.pk}", "y")
        with self.assertRaises(PermissionError):
            services.creer_document(self.chef, "x", f"service:{self.pont.pk}", "y")
        with self.assertRaises(ValidationError):  # officielle sans source
            services.creer_document(self.chef, "x", f"service:{self.energie.pk}", "y", origine=Document.ORIGINE_OFFICIELLE)
        with self.assertRaises(PermissionError):  # un rédacteur sous le seuil de validation ne valide pas
            doc = services.creer_document(self.redacteur, "Note", f"sector:{self.secteur.pk}", "x")
            services.soumettre(self.redacteur, doc.versions.get())
            services.valider(self.redacteur, doc.versions.get())


class VisibiliteTests(DocsBase):
    def test_ciblage_et_autres_navires(self):
        document = self._publie()
        for exclu in (self.pont_marin, self.etranger):
            self.assertFalse(services.peut_consulter(exclu, document))
            self.client.force_login(exclu)
            self.assertEqual(self.client.get(reverse("document-detail", args=[document.pk])).status_code, 404)
            self.assertEqual(self.client.post(reverse("document-action", args=[document.pk]), {"action": "proposer", "contenu": "x"}).status_code, 404)
        self.assertEqual(rechercher(self.pont_marin, "démarrage"), [])
        trouve = [g for g in rechercher(self.marin, "démarrage") if g["cle"] == "documents"]
        self.assertEqual(len(trouve), 1)

    def test_un_marin_ne_voit_pas_les_propositions_des_autres(self):
        document = self._publie()
        services.proposer_amelioration(self.chef, document, "brouillon interne confidentiel", "")
        self.client.force_login(self.marin)
        page = self.client.get(reverse("document-detail", args=[document.pk]))
        self.assertNotContains(page, "interne confidentiel")


class ContexteTests(DocsBase):
    def test_document_affiche_au_contexte_d_une_tache_et_lien_controle(self):
        document = self._publie()
        tache = Tache.objects.create(titre="Démarrer la pompe", assigne=self.marin, created_by=self.chef)
        services.lier(self.chef, document, tache)
        self.client.force_login(self.marin)
        self.assertContains(self.client.get(reverse("tache-detail", args=[tache.pk])), "Consignes de démarrage pompe")
        autre_tache = Tache.objects.create(titre="Privée", assigne=self.pont_marin, created_by=self.pont_marin, partagee=False)
        with self.assertRaises(PermissionError):
            services.lier(self.chef, document, autre_tache)
        self.client.force_login(self.pont_marin)
        self.assertNotContains(self.client.get(reverse("tache-detail", args=[autre_tache.pk])), "Consignes de démarrage pompe")

    def test_pages_de_la_bibliotheque(self):
        document = self._publie()
        self.client.force_login(self.marin)
        self.assertContains(self.client.get(reverse("documentation-index") + "?q=vanne"), "Consignes de démarrage")
        self.assertEqual(self.client.get(reverse("document-nouveau")).status_code, 404)
        self.client.force_login(self.chef)
        self.assertEqual(self.client.get(reverse("document-nouveau")).status_code, 200)
        self.assertContains(self.client.get(reverse("document-detail", args=[document.pk])), "Version applicable")
