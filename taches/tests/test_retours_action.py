"""Retours d'action de la fiche de tâche : confirmation après succès, jamais après refus, et « prévenus » conforme aux notifications."""
from django.urls import reverse

from notifications.models import Notification
from taches.models import Tache
from taches.tests.test_taches import TachesBase


class RetoursActionTests(TachesBase):
    def setUp(self):
        super().setUp()
        self.tache = self._tache()

    def _agir(self, user, action, **donnees):
        self.client.login(username=user.username, password="pass")
        r = self.client.post(reverse("tache-action", args=[self.tache.pk]), {"action": action, **donnees}, follow=True)
        return [(m.level_tag, str(m)) for m in r.context["messages"]]

    def _succes(self, messages):
        return [texte for niveau, texte in messages if niveau == "success"]

    def test_demarrer_confirme_et_refus_sans_confirmation(self):
        refus = self._agir(self.chef, "demarrer")
        self.assertEqual(self._succes(refus), [])
        self.assertTrue([t for n, t in refus if n == "danger"])
        self.assertEqual(self._succes(self._agir(self.marin, "demarrer")), ["Tâche démarrée."])

    def test_blocage_ne_cite_que_les_personnes_notifiees(self):
        succes = self._succes(self._agir(self.marin, "bloquer", motif="Vanne grippée"))[0]
        self.assertIn("Blocage signalé", succes)
        self.assertIn("les chefs du périmètre", succes)
        self.assertNotIn("participants", succes)
        self.assertTrue(Notification.objects.filter(user=self.chef, verb__contains="Vanne grippée").exists())

    def test_blocage_cite_les_participants_quand_ils_sont_notifies(self):
        self.tache.participants.add(self.terre)
        succes = self._succes(self._agir(self.marin, "bloquer", motif="Vanne grippée"))[0]
        self.assertIn("les participants du fil", succes)
        self.assertTrue(Notification.objects.filter(user=self.terre, verb__contains="Vanne grippée").exists())

    def test_blocage_sans_destinataire_ne_promet_aucune_notification(self):
        perso = self._tache(created_by=self.marin, partagee=False)
        self.client.login(username="marin", password="pass")
        r = self.client.post(reverse("tache-action", args=[perso.pk]), {"action": "bloquer", "motif": "Panne"}, follow=True)
        succes = [str(m) for m in r.context["messages"] if m.level_tag == "success"]
        self.assertEqual(succes, ["Blocage signalé et inscrit dans le fil."])
        self.assertFalse(Notification.objects.filter(object_id=str(perso.pk)).exists())

    def test_blocage_refuse_sans_motif(self):
        messages = self._agir(self.marin, "bloquer", motif=" ")
        self.assertEqual(self._succes(messages), [])
        self.assertTrue([t for n, t in messages if n == "danger"])

    def test_lever_le_blocage(self):
        self._agir(self.marin, "bloquer", motif="Vanne grippée")
        self.assertEqual(self._succes(self._agir(self.marin, "reprendre")), [])
        succes = self._succes(self._agir(self.chef, "reprendre"))[0]
        self.assertEqual(succes, "Blocage levé, inscrit dans le fil. Prévenus : le marin assigné.")
        self.assertTrue(Notification.objects.filter(user=self.marin, verb__startswith="Blocage levé").exists())

    def test_terminer_avec_compte_rendu(self):
        succes = self._succes(self._agir(self.marin, "rendre_compte", compte_rendu="Fait."))[0]
        self.assertIn("Compte rendu enregistré", succes)
        self.assertIn("les chefs du périmètre", succes)
        self.assertTrue(Notification.objects.filter(user=self.chef, verb__contains="rendu compte").exists())
        self.assertEqual(self._succes(self._agir(self.marin, "rendre_compte", compte_rendu="Encore.")), [])

    def test_ajouter_un_interlocuteur_prevenu(self):
        succes = self._succes(self._agir(self.chef, "interlocuteur", interlocuteur=self.terre.pk))
        self.assertEqual(succes, ["terre ajouté au fil. Prévenus : les participants du fil."])
        self.assertTrue(Notification.objects.filter(user=self.terre, verb__contains="ajouté au fil").exists())

    def test_interlocuteur_refuse_ou_vide(self):
        for envoi in ({"interlocuteur": self.terre.pk}, {"interlocuteur": ""}):
            messages = self._agir(self.marin if envoi["interlocuteur"] else self.chef, "interlocuteur", **envoi)
            self.assertEqual(self._succes(messages), [])
            self.assertTrue([t for n, t in messages if n == "danger"])
        self.assertFalse(self.tache.participants.exists())

    def test_repondre_dans_le_fil(self):
        self.client.login(username="marin", password="pass")
        r = self.client.post(reverse("tache-commentaire", args=[self.tache.pk]), {"body": "Bonjour"}, follow=True)
        succes = [str(m) for m in r.context["messages"] if m.level_tag == "success"]
        self.assertIn("Message publié.", succes[0])
        self.assertIn("les chefs du périmètre", succes[0])
        self.assertTrue(Notification.objects.filter(user=self.chef, verb__contains="a répondu").exists())

    def test_reponse_vide_sans_confirmation(self):
        self.client.login(username="marin", password="pass")
        r = self.client.post(reverse("tache-commentaire", args=[self.tache.pk]), {"body": " "}, follow=True)
        self.assertEqual([m for m in r.context["messages"] if m.level_tag == "success"], [])
        self.assertTrue([m for m in r.context["messages"] if m.level_tag == "danger"])


class ChoixNeutreTests(TachesBase):
    def test_interlocuteur_sans_presélection_et_obligatoire(self):
        tache = self._tache()
        self.client.login(username="chef", password="pass")
        html = self.client.get(reverse("tache-detail", args=[tache.pk])).content.decode()
        debut = html.index('name="interlocuteur"')
        select = html[debut:html.index("</select>", debut)]
        self.assertIn("required", select)
        self.assertIn('<option value="">Choisir un interlocuteur…</option>', select)
        self.assertNotIn("selected", select)
