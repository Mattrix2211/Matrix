"""Demandes bord–terre : signalement, réponse d'un interlocuteur à terre, action assignée, clôture traçable."""
from django.core.exceptions import ValidationError
from django.urls import reverse

from dashboard.aujourdhui import a_faire
from demandes import services
from demandes.models import Demande
from notifications.models import Notification
from taches.services import rendre_compte
from taches.tests.test_taches import TachesBase
from threads.utils import commentaires_de


class DemandesBase(TachesBase):
    def setUp(self):
        super().setUp()
        self.tache = self._tache()
        self.demande = services.creer_demande(
            self.marin, self.tache, "Pompe bruyante", "Bruit anormal au roulement", self.chef,
        )
        self.expert = self.terre


class ParcoursTests(DemandesBase):
    def test_parcours_de_demo(self):
        # 1. le marin signale ; le responsable est prévenu, une seule alerte d'action
        self.assertEqual(Notification.objects.filter(user=self.chef, action_requise=True).count(), 1)
        # 2. un interlocuteur à terre est désigné, répond et le responsable assigne une action
        services.ajouter_interlocuteur(self.demande, self.chef, self.expert)
        self.client.force_login(self.expert)
        reponse = self.client.post(reverse("demande-commentaire", args=[self.demande.pk]), {"body": "Remplacer le roulement."})
        self.assertEqual(reponse.status_code, 302)
        action = services.creer_action(self.demande, self.chef, self.marin, "Remplacer le roulement")
        self.assertEqual(action.demande, self.demande)
        self.assertIn("Remplacer le roulement", [e["titre"] for e in a_faire(self.marin, self.aujourdhui)])
        # 3. le marin termine l'action, le dossier passe résolu puis clos
        rendre_compte(action, self.marin, "Roulement remplacé")
        services.changer_etat(self.demande, self.chef, Demande.ETAT_EN_TRAITEMENT)
        services.changer_etat(self.demande, self.chef, Demande.ETAT_RESOLU)
        services.changer_etat(self.demande, self.marin, Demande.ETAT_CLOS)
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.etat, Demande.ETAT_CLOS)
        corps = " ".join(m.body for m in commentaires_de(self.demande))
        for attendu in ("Remplacer le roulement", "Action terminée", "Résolu → Clos"):
            self.assertIn(attendu, corps)
        self.assertFalse(Notification.objects.filter(action_requise=True, traitee_le__isnull=True, user=self.chef,
                                                     object_id=str(self.demande.pk)).exists())

    def test_attente_d_information_puis_reponse_du_declarant(self):
        with self.assertRaises(ValidationError):
            services.changer_etat(self.demande, self.chef, Demande.ETAT_EN_ATTENTE)
        services.changer_etat(self.demande, self.chef, Demande.ETAT_EN_ATTENTE, "Quel est le numéro de série ?")
        self.assertTrue(Notification.objects.filter(user=self.marin, action_requise=True, traitee_le__isnull=True).exists())
        services.repondre(self.demande, self.marin, "SN-1234")
        self.demande.refresh_from_db()
        self.assertEqual(self.demande.etat, Demande.ETAT_OUVERT)
        self.assertFalse(Notification.objects.filter(user=self.marin, action_requise=True, traitee_le__isnull=True,
                                                     verb__startswith="Information attendue").exists())

    def test_transitions_reservees(self):
        for acteur, etat in ((self.marin, Demande.ETAT_RESOLU), (self.chef, Demande.ETAT_CLOS), (self.voisin, Demande.ETAT_RESOLU)):
            with self.assertRaises(PermissionError):
                services.changer_etat(self.demande, acteur, etat)

    def test_mention_d_un_interlocuteur_hors_perimetre_visible(self):
        services.ajouter_interlocuteur(self.demande, self.chef, self.expert)
        services.repondre(self.demande, self.marin, "@terre pouvez-vous confirmer ?")
        self.assertTrue(Notification.objects.filter(user=self.expert, action_requise=True,
                                                    verb__startswith="Réponse attendue").exists())


class DroitsTests(DemandesBase):
    def test_visibilite(self):
        self.assertTrue(services.peut_consulter(self.marin, self.demande))
        self.assertTrue(services.peut_consulter(self.chef, self.demande))
        for intrus in (self.voisin, self.expert, self.etranger):
            self.assertFalse(services.peut_consulter(intrus, self.demande))
            self.client.force_login(intrus)
            self.assertEqual(self.client.get(reverse("demande-detail", args=[self.demande.pk])).status_code, 404)

    def test_signalement_refuse_a_l_equipage_a_terre_et_sans_acces(self):
        with self.assertRaises(PermissionError):
            services.creer_demande(self.terre, self._tache(assigne=self.terre), "x", "", self.chef)
        with self.assertRaises(PermissionError):
            services.creer_demande(self.voisin, self.tache, "x", "", self.chef)

    def test_responsable_obligatoire_et_chef_du_navire(self):
        with self.assertRaises(ValidationError):
            services.creer_demande(self.marin, self.tache, "x", "", self.voisin)

    def test_un_interlocuteur_simple_ne_pilote_pas(self):
        services.ajouter_interlocuteur(self.demande, self.chef, self.expert)
        for operation in (
            lambda: services.ajouter_interlocuteur(self.demande, self.expert, self.voisin),
            lambda: services.creer_action(self.demande, self.expert, self.marin, "x"),
            lambda: services.reaffecter(self.demande, self.expert, self.chef),
        ):
            with self.assertRaises(PermissionError):
                operation()

    def test_le_fil_clos_refuse_les_messages(self):
        services.changer_etat(self.demande, self.chef, Demande.ETAT_RESOLU)
        services.changer_etat(self.demande, self.marin, Demande.ETAT_CLOS)
        with self.assertRaises(ValidationError):
            services.repondre(self.demande, self.marin, "encore")

    def test_pages(self):
        self.client.force_login(self.marin)
        self.assertContains(self.client.get(reverse("demandes-index")), "Pompe bruyante")
        self.assertContains(self.client.get(reverse("demande-detail", args=[self.demande.pk])), "Bruit anormal")
        self.assertContains(self.client.get(reverse("demande-nouvelle") + f"?objet=tache:{self.tache.pk}"), "Signaler une difficulté")
        self.assertEqual(self.client.get(reverse("demande-nouvelle") + "?objet=tache:99999").status_code, 404)


class DoubleEquipageTests(DemandesBase):
    def test_chef_hors_perimetre_ou_de_l_autre_equipage_refuse(self):
        autre_secteur = self._marin("chef_elec", self.voisin.profile.sector, "CHEF_SECTION", "A")
        chef_terre = self._marin("chef_terre", self.secteur, "CHEF_SECTION", "B")
        for intrus in (autre_secteur, chef_terre):
            self.assertFalse(services.peut_consulter(intrus, self.demande))
            self.assertFalse(services.demandes_visibles(intrus).filter(pk=self.demande.pk).exists())
            self.assertFalse(services.peut_piloter(intrus, self.demande))
            self.client.force_login(intrus)
            self.assertEqual(self.client.get(reverse("demande-detail", args=[self.demande.pk])).status_code, 404)
            self.assertEqual(self.client.post(reverse("demande-action", args=[self.demande.pk]),
                                              {"action": "creer_action", "titre": "x", "assigne": self.marin.pk}).status_code, 404)

    def test_action_refusee_vers_l_autre_equipage(self):
        with self.assertRaises(ValidationError):
            services.creer_action(self.demande, self.chef, self.terre, "Action")

    def test_lien_de_l_action_masque_a_l_interlocuteur_a_terre(self):
        services.ajouter_interlocuteur(self.demande, self.chef, self.terre)
        action = services.creer_action(self.demande, self.chef, self.marin, "Remplacer le roulement")
        self.client.force_login(self.terre)
        page = self.client.get(reverse("demande-detail", args=[self.demande.pk]))
        self.assertContains(page, "Remplacer le roulement")
        self.assertNotContains(page, reverse("tache-detail", args=[action.pk]))
