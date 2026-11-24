"""Administration Django : chaque modèle enregistré est fermé aux comptes sans droit d'administration (lot L29)."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from matrix.core import points_entree
from org.models import ReferenceBatiment

from .outils import MondeFictif


class AdministrationTests(MondeFictif):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.modeles = points_entree.modeles_admin()

    def _refuse(self, reponse):
        return reponse.status_code in (403, 404) or (reponse.status_code == 302 and "login" in reponse["Location"])

    def test_anonyme_et_comptes_ordinaires_sont_refuses_partout(self):
        for profil in (None, "equipier_b1", "chef_service_b", "cdt_b", "second_b", "admin_navire", "equipier_abe"):
            client = self.client_de(profil)
            for point in self.modeles:
                reponse = client.get(point.url_exemple)
                self.assertTrue(self._refuse(reponse), f"{profil} : {point.url_exemple} -> {reponse.status_code}")

    def test_un_compte_staff_sans_droit_est_refuse_partout(self):
        client = self.client_de("staff_sans_droit")
        for point in self.modeles:
            for adresse in (point.url_exemple, point.url_exemple + "add/"):
                reponse = client.get(adresse)
                self.assertTrue(self._refuse(reponse), f"{adresse} -> {reponse.status_code}")

    def test_le_compte_administrateur_general_atteint_chaque_liste(self):
        client = self.client_de("master_admin")
        for point in self.modeles:
            reponse = client.get(point.url_exemple)
            self.assertEqual(reponse.status_code, 200, point.url_exemple)

    def test_l_ecriture_d_un_compte_staff_sans_droit_est_refusee(self):
        client = self.client_de("staff_sans_droit")
        for point in self.modeles[:15]:
            reponse = client.post(point.url_exemple + "add/", {})
            self.assertTrue(self._refuse(reponse), f"{point.url_exemple}add/ -> {reponse.status_code}")

    def test_un_compte_qui_ne_peut_que_voir_ne_declenche_aucune_action_ni_modification(self):
        """Nouvelle protection L29 : les actions « archiver » et « restaurer » étaient ouvertes à qui pouvait seulement voir la liste."""
        reference = ReferenceBatiment.objects.create(nom="Bâtiment d'essai")
        lecteur = get_user_model().objects.create_user(username="lecteur_admin", password="pass", is_staff=True)
        lecteur.user_permissions.add(Permission.objects.get(codename="view_referencebatiment"))
        client = self.client_de("lecteur_admin")
        liste = "/admin/org/referencebatiment/"
        self.assertEqual(client.get(liste).status_code, 200)
        client.post(liste, {"action": "archiver", "_selected_action": [reference.pk]})
        reference.refresh_from_db()
        self.assertFalse(reference.archive)
        self.assertEqual(client.post(f"{liste}{reference.pk}/change/", {"nom": "Modifié"}).status_code, 403)
        self.assertEqual(client.post(f"{liste}{reference.pk}/delete/", {"post": "yes"}).status_code, 403)
        self.assertTrue(ReferenceBatiment.objects.filter(pk=reference.pk).exists())

    def test_toute_action_personnalisee_d_administration_exige_une_permission(self):
        from django.contrib import admin

        for modele, model_admin in admin.site._registry.items():
            for nom in model_admin.actions or ():
                action = getattr(model_admin, nom) if isinstance(nom, str) else nom
                self.assertTrue(getattr(action, "allowed_permissions", ()), f"{modele._meta.label} : action « {nom} » sans permission")
