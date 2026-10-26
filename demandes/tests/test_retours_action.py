"""Retours d'action d'un dossier : confirmation après succès, jamais après refus, listes de choix alignées sur le serveur."""
from django.urls import reverse

from demandes import services
from demandes.models import Demande
from demandes.tests.test_demandes import DemandesBase
from notifications.models import Notification
from taches.models import Tache


class RetoursActionTests(DemandesBase):
    def _agir(self, user, action, **donnees):
        self.client.login(username=user.username, password="pass")
        r = self.client.post(reverse("demande-action", args=[self.demande.pk]), {"action": action, **donnees}, follow=True)
        return [(m.level_tag, str(m)) for m in r.context["messages"]]

    def _succes(self, messages):
        return [texte for niveau, texte in messages if niveau == "success"]

    def test_changement_d_etat_cite_les_personnes_notifiees(self):
        succes = self._succes(self._agir(self.chef, "etat", etat=Demande.ETAT_EN_TRAITEMENT))
        self.assertEqual(succes, ["État du dossier mis à jour. Prévenus : le déclarant."])
        self.assertTrue(Notification.objects.filter(user=self.marin, verb__contains="En traitement").exists())

    def test_changement_d_etat_cite_aussi_les_interlocuteurs(self):
        services.ajouter_interlocuteur(self.demande, self.chef, self.expert)
        succes = self._succes(self._agir(self.chef, "etat", etat=Demande.ETAT_EN_TRAITEMENT))[0]
        self.assertIn("le déclarant", succes)
        self.assertIn("les interlocuteurs", succes)
        self.assertTrue(Notification.objects.filter(user=self.expert, verb__contains="En traitement").exists())

    def test_etat_refuse_sans_confirmation(self):
        messages = self._agir(self.marin, "etat", etat=Demande.ETAT_RESOLU)
        self.assertEqual(self._succes(messages), [])
        self.assertTrue([t for n, t in messages if n == "danger"])

    def test_confier_le_dossier(self):
        autre = self._marin("chef2", self.secteur, "CHEF_SECTION", "A")
        succes = self._succes(self._agir(self.chef, "reaffecter", responsable=autre.pk))
        self.assertEqual(succes, ["Dossier confié à chef2. Prévenus : le responsable."])
        self.assertTrue(Notification.objects.filter(user=autre, verb__contains="vous confie").exists())

    def test_confier_refuse_sans_confirmation(self):
        messages = self._agir(self.marin, "reaffecter", responsable=self.chef.pk)
        self.assertEqual(self._succes(messages), [])
        self.assertTrue([t for n, t in messages if n == "danger"])

    def test_ajouter_un_interlocuteur(self):
        succes = self._succes(self._agir(self.chef, "interlocuteur", interlocuteur=self.expert.pk))
        self.assertEqual(succes, ["terre ajouté au dossier. Prévenus : les interlocuteurs."])
        self.assertTrue(Notification.objects.filter(user=self.expert, verb__contains="vous a ajouté").exists())

    def test_interlocuteur_refuse_sans_confirmation(self):
        messages = self._agir(self.marin, "interlocuteur", interlocuteur=self.expert.pk)
        self.assertEqual(self._succes(messages), [])
        self.assertTrue([t for n, t in messages if n == "danger"])

    def test_repondre_dans_le_fil(self):
        self.client.login(username="marin", password="pass")
        r = self.client.post(reverse("demande-commentaire", args=[self.demande.pk]), {"body": "Bonjour"}, follow=True)
        succes = [str(m) for m in r.context["messages"] if m.level_tag == "success"]
        self.assertEqual(succes, ["Message publié. Prévenus : le responsable."])
        self.assertTrue(Notification.objects.filter(user=self.chef, verb__contains="a répondu").exists())

    def test_reponse_vide_sans_confirmation(self):
        self.client.login(username="marin", password="pass")
        r = self.client.post(reverse("demande-commentaire", args=[self.demande.pk]), {"body": " "}, follow=True)
        self.assertEqual([m for m in r.context["messages"] if m.level_tag == "success"], [])
        self.assertTrue([m for m in r.context["messages"] if m.level_tag == "danger"])


class ChoixNeutreTests(DemandesBase):
    def _page(self):
        self.client.login(username="chef", password="pass")
        return self.client.get(reverse("demande-detail", args=[self.demande.pk]))

    def _select(self, html, nom):
        debut = html.index(f'name="{nom}"')
        return html[debut:html.index("</select>", debut)]

    def test_aucune_option_preselectionnee_et_choix_obligatoire(self):
        html = self._page().content.decode()
        for nom, vide in (("assigne", "Choisir un marin…"), ("interlocuteur", "Choisir un interlocuteur…")):
            select = self._select(html, nom)
            self.assertIn("required", select)
            self.assertIn(f'<option value="">{vide}</option>', select)
            self.assertNotIn("selected", select)

    def test_liste_marin_alignee_sur_creer_action(self):
        marins = list(self._page().context["marins"])
        self.assertIn(self.marin, marins)
        self.assertNotIn(self.terre, marins)  # équipage B à terre
        self.assertNotIn(self.etranger, marins)
        for marin in marins:
            services.creer_action(self.demande, self.chef, marin, "Vérifier")

    def test_liste_marin_exclut_l_autre_equipage_du_declarant(self):
        profil = self.marin.profile
        profil.equipage = "B"
        profil.save()
        self.navire.equipage_a_bord = "B"
        self.navire.save()
        marins = list(self._page().context["marins"])
        self.assertEqual([m.username for m in marins if m.profile.equipage != "B"], [])
        for marin in marins:
            services.creer_action(self.demande, self.chef, marin, "Vérifier")

    def test_envoi_sans_choix_refuse(self):
        self.client.login(username="chef", password="pass")
        r = self.client.post(
            reverse("demande-action", args=[self.demande.pk]), {"action": "creer_action", "titre": "Vérifier", "assigne": ""}, follow=True,
        )
        self.assertEqual(Tache.objects.filter(demande=self.demande).count(), 0)
        self.assertEqual([m for m in r.context["messages"] if m.level_tag == "success"], [])
        self.assertTrue([m for m in r.context["messages"] if m.level_tag == "danger"])

    def test_envoi_vers_un_marin_a_terre_refuse_par_le_serveur(self):
        self.client.login(username="chef", password="pass")
        r = self.client.post(
            reverse("demande-action", args=[self.demande.pk]), {"action": "creer_action", "titre": "Vérifier", "assigne": self.terre.pk}, follow=True,
        )
        self.assertEqual(Tache.objects.filter(demande=self.demande).count(), 0)
        self.assertEqual([m for m in r.context["messages"] if m.level_tag == "success"], [])
