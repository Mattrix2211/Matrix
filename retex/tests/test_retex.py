"""RETEX : proposition depuis une source, routage par domaine, décision, publication et actions suivies."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from documentation.models import Document, VersionDocument
from notifications.models import Notification
from org.models import Sector, Service, Ship
from retex import services
from retex.models import Retex
from taches.models import Tache


class RetexBase(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Retex", code="RE")
        self.energie = Service.objects.create(ship=self.navire, name="Énergie")
        self.secteur = Sector.objects.create(service=self.energie, name="Propulsion")
        self.chef = self._marin("chef_energie", self.energie, None, "CHEF_SERVICE", fonction="COMANAV")
        self.chef_autre = self._marin("chef_autre", self.energie, None, "CHEF_SERVICE")
        self.marin = self._marin("marin", self.energie, self.secteur, "EQUIPIER")
        self.etranger = self._marin("etranger", None, None, "EQUIPIER", navire=Ship.objects.create(name="Autre", code="AU"))
        self.domaine = services.domaines_du_navire(self.navire.pk).get(coma="COMANAV")

    def _marin(self, nom, service, secteur, role, navire=None, fonction=""):
        user = User.objects.create_user(username=nom, password="pass")
        p = user.profile
        p.role, p.ship, p.service, p.sector, p.fonction_service = role, navire or self.navire, service, secteur, fonction
        p.save()
        return user

    def _propose(self, source=None):
        return services.proposer(self.marin, "Joint de graisseur défectueux", "Fuite répétée", "Contrôler la référence avant montage",
                                 self.domaine.pk, source=source)


class ParcoursTests(RetexBase):
    def test_proposition_validation_publication_et_actions(self):
        tache = Tache.objects.create(titre="Resserrer le graisseur", assigne=self.marin, created_by=self.chef)
        retex = self._propose(source=tache)
        self.assertEqual(retex.organisme, "SSF / ERO / IRB puis ERDT / IRDT")  # routage du domaine
        self.assertEqual(retex.source_libelle, "Resserrer le graisseur")
        # le COMA référent (fonction COMANAV) est prévenu en premier, l'auteur jamais
        self.assertEqual([u.username for u in services.valideurs(retex)][:1], ["chef_energie"])
        self.assertEqual(Notification.objects.filter(action_requise=True, traitee_le__isnull=True).count(), 2)
        self.assertFalse(Notification.objects.filter(user=self.marin).exists())
        with self.assertRaises(PermissionError):
            services.valider(self.marin, retex)
        services.valider(self.chef, retex, "Bonne remontée")
        retex.refresh_from_db()
        self.assertEqual(retex.etat, Retex.ETAT_VALIDE)
        self.assertFalse(Notification.objects.filter(action_requise=True, traitee_le__isnull=True, verb__startswith="RETEX").exists())
        # publié dans la documentation, lisible du bord
        self.assertEqual(retex.document.versions.get().etat, VersionDocument.ETAT_PUBLIEE)
        self.assertIn("Contrôler la référence", retex.document.versions.get().contenu)
        # action suivie, puis clôture seulement une fois terminée
        action = services.creer_action(self.chef, retex, self.marin, "Contrôler les joints en magasin", timezone.localdate() + timedelta(days=7))
        with self.assertRaises(ValidationError):
            services.clore(self.chef, retex)
        action.statut = Tache.STATUT_TERMINEE
        action.save()
        services.clore(self.chef, retex)
        retex.refresh_from_db()
        self.assertEqual(retex.etat, Retex.ETAT_CLOS)

    def test_refus_motive_et_decision_unique(self):
        retex = self._propose()
        with self.assertRaises(ValidationError):
            services.refuser(self.chef, retex, " ")
        services.refuser(self.chef, retex, "Déjà traité dans la procédure")
        self.assertTrue(Notification.objects.filter(user=self.marin, verb__contains="refusé").exists())
        with self.assertRaises(ValidationError):
            services.valider(self.chef, retex)

    def test_champs_obligatoires_domaine_et_source_inaccessible(self):
        with self.assertRaises(ValidationError):
            services.proposer(self.marin, "x", "", "y", self.domaine.pk)
        with self.assertRaises(ValidationError):
            services.proposer(self.marin, "x", "y", "z", 99999)
        privee = Tache.objects.create(titre="Privée", assigne=self.chef, created_by=self.chef, partagee=False)
        with self.assertRaises(PermissionError):
            self._propose(source=privee)

    def test_domaines_configurables(self):
        with self.assertRaises(PermissionError):
            services.ajouter_domaine(self.marin, "Sûreté", "COMSUR", "")
        services.ajouter_domaine(self.chef, "Sûreté", "COMSUR", "ALFAN / Exploitation")
        self.assertTrue(services.domaines_du_navire(self.navire.pk).filter(nom="Sûreté").exists())


class VisibiliteTests(RetexBase):
    def test_perimetre_et_pages(self):
        retex = self._propose()
        self.client.force_login(self.etranger)
        self.assertEqual(self.client.get(reverse("retex-detail", args=[retex.pk])).status_code, 404)
        self.client.force_login(self.chef_autre)  # habilité du bâtiment
        self.assertContains(self.client.get(reverse("retex-detail", args=[retex.pk])), "Joint de graisseur")
        self.client.force_login(self.marin)
        self.assertContains(self.client.get(reverse("retex-index")), "Joint de graisseur")
        self.assertContains(self.client.get(reverse("retex-nouveau") + f"?source=tache:{Tache.objects.create(titre='Ma tâche', assigne=self.marin, created_by=self.chef).pk}"), "Ma tâche")
        self.assertEqual(self.client.get(reverse("retex-nouveau") + "?source=tache:99999").status_code, 404)
        self.assertEqual(self.client.get(reverse("retex-domaines")).status_code, 404)
        # un RETEX non validé reste invisible d'un autre marin du bâtiment
        autre = self._marin("autre_marin", self.energie, self.secteur, "EQUIPIER")
        self.client.force_login(autre)
        self.assertEqual(self.client.get(reverse("retex-detail", args=[retex.pk])).status_code, 404)
        services.valider(self.chef, retex)
        self.assertEqual(self.client.get(reverse("retex-detail", args=[retex.pk])).status_code, 200)
