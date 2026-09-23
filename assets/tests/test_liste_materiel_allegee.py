from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from org.models import Ship, Service, Sector
from assets.models import AssetFolder


class ListeMaterielAllegeeTests(TestCase):
    """Vérifie l'allègement visuel de la liste des matériels (/assets/) :
    - la carte "Dossiers" ne rend son contenu (grille de sous-dossiers, astuce)
      que s'il existe au moins un sous-dossier à afficher, pour ne pas imposer
      une grande carte vide aux utilisateurs qui ne se servent jamais des
      dossiers (le bandeau fil d'Ariane + bouton "Nouveau" reste toujours là) ;
    - le bouton "Actions groupées" est rendu masqué par défaut (classe d-none),
      il n'est révélé qu'après sélection d'au moins un matériel, en JS.
    Changement purement d'affichage (aucune fonctionnalité retirée, aucun champ
    de données modifié) : couvert ici par un simple contrôle du HTML rendu."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire A", code="NAV-A")
        self.service = Service.objects.create(name="Srv A", ship=self.ship)
        self.sector = Sector.objects.create(name="Sec A", service=self.service)
        self.chef = User.objects.create_user(username="chef_allege", password="pass")
        UserProfile.objects.update_or_create(
            user=self.chef, defaults={"role": "CHEF_SERVICE", "ship": self.ship, "service": self.service}
        )
        self.client.login(username="chef_allege", password="pass")

    def test_bouton_actions_groupees_masque_par_defaut(self):
        r = self.client.get("/assets/")
        self.assertContains(r, 'id="bulkActionsBtn"')
        # Le bouton doit porter la classe d-none dans le HTML servi : c'est le
        # JS (countSelected) qui la retire lorsqu'au moins un matériel est coché.
        self.assertContains(r, 'class="btn btn-outline-secondary dropdown-toggle d-none" type="button" id="bulkActionsBtn"')

    def test_carte_dossiers_sans_contenu_si_aucun_sous_dossier(self):
        # Aucun AssetFolder créé : la carte "Dossiers" ne doit pas rendre de
        # grille (folderGrid), seulement son bandeau (fil d'Ariane + Nouveau).
        r = self.client.get("/assets/")
        self.assertContains(r, ">Dossiers<")
        self.assertNotContains(r, 'id="folderGrid"')

    def test_carte_dossiers_affiche_la_grille_si_des_sous_dossiers_existent(self):
        AssetFolder.objects.create(name="Extincteurs")
        r = self.client.get("/assets/")
        self.assertContains(r, 'id="folderGrid"')
        self.assertContains(r, "Extincteurs")
