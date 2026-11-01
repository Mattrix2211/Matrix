"""Accueil : cartes cliquables, tours de service, indicateurs chiffrés, bandeau allégé, aides à la demande."""
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from maintenance.models import MaintenanceOccurrence


class AccueilUxTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", stdout=StringIO())

    def _accueil(self, nom="equipier_a"):
        self.client.login(username=nom, password="pass")
        return self.client.get(reverse("home"))

    def test_ma_journee_est_une_carte_cliquable_sans_lien_redondant(self):
        page = self._accueil().content.decode()
        debut = page.index("Ma journée")
        carte = page[page.rindex("<a ", 0, debut):page.index("</a>", debut)]
        self.assertIn(f'href="{reverse("calendar-index")}"', carte)
        self.assertNotIn("Voir mon calendrier et mes échéances", page)
        self.assertEqual(carte.count("<a "), 1)  # aucun lien imbriqué dans la carte

    def test_cartes_d_information_menent_au_module(self):
        page = self._accueil().content.decode()
        for titre, adresse in (("Prochaines formations", reverse("formation-list")), ("Mes qualifications", reverse("formation-list")),
                               ("Mes tours de service", reverse("quarts-index"))):
            debut = page.index(titre)
            self.assertIn(f'href="{adresse}"', page[page.rindex("<a ", 0, debut):debut], titre)

    def test_mes_tours_de_service_montre_les_prochaines_dates_et_fonctions(self):
        page = self._accueil().content.decode()
        self.assertIn("Mes tours de service", page)
        self.assertNotIn("Listes publiées uniquement", page)
        self.assertIn("Gradé de coupée 1", page)
        self.assertIn(timezone.localdate().strftime("%d") , page)
        self.assertEqual(len(self.client.get(reverse("home")).context["mes_tours_de_service"]), 3)

    def test_sans_tour_publie_un_message_clair(self):
        self.client.login(username="equipier_nor", password="pass")
        self.assertContains(self.client.get(reverse("home")), "Aucun tour de service publié à venir.")

    def test_les_graphiques_decoratifs_sont_remplaces_par_des_chiffres_avec_perimetre(self):
        page = self._accueil("chef_secteur_a").content.decode()
        self.assertNotIn("chartPreventive", page)
        self.assertNotIn("chartCorrective", page)
        self.assertNotIn("<canvas", page)
        self.assertIn("Maintenance et correctif", page)
        self.assertRegex(page, r"(Bâtiment|Service|Secteur|Section) : ")
        for libelle in ("En retard", "À venir (7 jours)", "En attente de validation", "Tickets correctifs ouverts"):
            self.assertIn(libelle, page)

    def test_les_chiffres_correspondent_aux_listes_filtrees(self):
        self.client.login(username="chef_secteur_a", password="pass")
        indicateurs = {i["libelle"]: i for i in self.client.get(reverse("home")).context["indicateurs_maintenance"]}
        for libelle, filtre in (("En retard", "retard=1"), ("À venir (7 jours)", "a_venir=1"), ("En attente de validation", "statut=WAITING_VALIDATION")):
            indicateur = indicateurs[libelle]
            self.assertTrue(indicateur["url"].endswith(filtre), libelle)
            liste = self.client.get(indicateur["url"])
            self.assertEqual(liste.status_code, 200)
            self.assertEqual(len(liste.context["occurrences"]), indicateur["valeur"], libelle)

    def test_filtre_a_venir_n_inclut_ni_retard_ni_terminees(self):
        jour = timezone.localdate()
        self.client.login(username="chef_secteur_a", password="pass")
        liste = self.client.get(reverse("maintenance-occurrences") + "?a_venir=1").context["occurrences"]
        for occurrence in liste:
            self.assertIn(occurrence.status, ("PLANNED", "ASSIGNED", "IN_PROGRESS"))
            self.assertTrue(jour <= occurrence.scheduled_for <= jour + timedelta(days=7))
        self.assertTrue(MaintenanceOccurrence.objects.filter(status="DONE").exists())

    def test_bandeau_allege_et_recherche_centree(self):
        page = self._accueil().content.decode()
        self.assertNotIn("bg-dark", page.split("</header>")[0])
        self.assertIn('class="mx-barre__gauche"', page)
        self.assertIn("mx-recherche", page)

    def test_aide_de_la_page_suivi_a_la_demande(self):
        self.client.login(username="equipier_a", password="pass")
        page = self.client.get(reverse("demandes-index")).content.decode()
        self.assertIn("<summary>Comment signaler une difficulté ?</summary>", page)
        self.assertNotRegex(page, r'<details class="mx-aide[^>]* open')
        self.assertNotIn('<p class="text-muted">Suivi des difficultés remontées', page)

    def test_fil_des_vues_sans_defilement_parasite(self):
        css = open("matrix/static/css/naval_premium.css", encoding="utf-8").read()
        ligne = next(l for l in css.splitlines() if l.startswith(".mx-parcours {"))
        self.assertNotIn("overflow", ligne)
