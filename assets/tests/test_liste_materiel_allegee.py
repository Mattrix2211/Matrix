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
      dossiers (le bandeau fil d'Ariane reste toujours là) ;
    - la barre d'actions groupées est rendue masquée par défaut (classe d-none),
      elle n'est révélée qu'après sélection d'au moins un matériel, en JS.
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

    def test_barre_actions_groupees_masquee_par_defaut(self):
        r = self.client.get("/assets/")
        # La barre n'est révélée par le JS qu'après sélection d'au moins un matériel.
        self.assertContains(r, 'class="mx-barre-selection d-none" id="barreSelection"')

    def test_carte_dossiers_sans_contenu_si_aucun_sous_dossier(self):
        # Aucun AssetFolder créé : la carte "Dossiers" ne doit pas rendre de
        # grille (folderGrid), seulement son bandeau (fil d'Ariane).
        r = self.client.get("/assets/")
        self.assertContains(r, ">Dossiers<")
        self.assertNotContains(r, 'id="folderGrid"')

    def test_carte_dossiers_affiche_la_grille_si_des_sous_dossiers_existent(self):
        AssetFolder.objects.create(name="Extincteurs")
        r = self.client.get("/assets/")
        self.assertContains(r, 'id="folderGrid"')
        self.assertContains(r, "Extincteurs")
