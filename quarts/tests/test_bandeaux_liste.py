"""Fiche de liste : moins d'empilement de bandeaux informatifs, sans jamais masquer une alerte bloquante."""
from datetime import timedelta

from django.utils import timezone

from accounts.models import FonctionQuartChoice
from quarts.alertes_activation import traiter_echeances
from quarts.models import CreneauQuart, Quart, ServiceGarde
from quarts.tests.test_activation_liste_quai import BaseActivation


class BandeauxListeTests(BaseActivation):
    def _page(self, user):
        self.client.force_login(user)
        return self.client.get(self.url).content.decode()

    def _quart(self, en_cours):
        quart = Quart.objects.create(
            service=self.service, fonction=FonctionQuartChoice.objects.create(name="Barre"),
            date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=7), statut=Quart.STATUT_PUBLIEE,
        )
        garde = self.liste.creneaux.get()
        if en_cours:
            garde.debut, garde.fin = timezone.now() - timedelta(hours=1), timezone.now() + timedelta(hours=23)
            garde.save()
            debut = timezone.now() - timedelta(minutes=30)
        else:
            debut = garde.debut + timedelta(hours=2)
        CreneauQuart.objects.create(quart=quart, poste="Barre", debut=debut, fin=debut + timedelta(hours=4), marin=self.marin)

    def test_une_seule_alerte_d_activation_est_affichee_la_plus_avancee(self):
        self._previsionnelle()
        prevue = timezone.now() + timedelta(hours=3)
        ServiceGarde.objects.filter(pk=self.liste.pk).update(prise_effet_prevue=prevue)
        for decalage in (-30, 1, 16):  # rappel, alerte, escalade : trois alertes ouvertes
            traiter_echeances(prevue + timedelta(minutes=decalage))
        self.assertEqual(self.liste.alertes_activation.filter(fermee_le__isnull=True).count(), 3)
        page = self._page(self.chef)
        self.assertEqual(page.count("Escalade :") + page.count("devait prendre effet et n'est pas activée") + page.count("Rappel :"), 1)
        self.assertIn("Escalade : la liste n'est toujours pas activée", page)

    def test_les_avertissements_non_bloquants_sont_replies_mais_presents(self):
        self._quart(en_cours=False)
        self._previsionnelle()
        page = self._page(self.chef)
        self.assertIn("<details", page)
        self.assertIn("non bloquants", page)
        self.assertIn("recouvre le service", page)

    def test_un_conflit_bloquant_reste_un_bandeau_visible(self):
        self._quart(en_cours=True)
        self._previsionnelle()
        page = self._page(self.chef)
        self.assertIn("Activation bloquée tant que ces recouvrements ne sont pas résolus", page)
        self.assertIn('class="alert alert-warning"', page)

    def test_etat_et_mode_tiennent_sur_une_seule_rangee(self):
        self._previsionnelle()
        page = self._page(self.chef)
        self.assertEqual(page.count("mx-mode "), 1)
        self.assertLess(page.index("mx-mode"), page.index("Liste prévisionnelle : elle ne s'applique pas encore") + 400)

    def test_la_grille_indique_la_date_de_fin_d_un_creneau_qui_enjambe_minuit(self):
        self._previsionnelle()
        garde = self.liste.creneaux.get()
        garde.debut, garde.fin = timezone.now(), timezone.now() + timedelta(hours=26)
        garde.save()
        page = self._page(self.chef)
        fin = timezone.localtime(garde.fin).strftime("%d/%m %H:%M")
        self.assertIn(fin, page)

    def test_le_publicateur_est_affiche_par_son_nom_complet(self):
        self._previsionnelle()
        self.commandant.first_name, self.commandant.last_name = "Anne", "Dupont"
        self.commandant.save()
        self.assertIn("par Anne Dupont", self._page(self.chef))
