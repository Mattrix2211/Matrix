"""Un visiteur non connecté n'atteint aucune route non publique, quelle que soit la méthode HTTP (lot L29).

Preuve par exécution de l'authentification sur l'ensemble des pages et de l'API ; le résultat par profil connecté est
dans test_matrice_profils.py."""
from django.test import Client

from matrix.core import points_entree
from matrix.core.registre_acces import PUBLIC, regle_de

from .outils import MondeFictif, acces_anonymes_non_refuses


class AccesAnonymeTests(MondeFictif):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.points = points_entree.routes()

    def test_aucune_route_non_publique_n_est_atteinte_sans_connexion(self):
        self.maxDiff = None
        self.assertEqual(acces_anonymes_non_refuses(self.points, methodes=("get", "post", "put", "patch", "delete", "options", "head")), [])

    def test_les_routes_publiques_sont_les_seules_declarees_telles(self):
        publiques = sorted(p.cle for p in self.points if regle_de(p).classe == PUBLIC)
        self.assertEqual(publiques, ["accounts/login/", "login/", "service-worker.js"])

    def test_les_routes_publiques_ne_donnent_acces_a_aucune_donnee(self):
        client = Client()
        for adresse in ("/accounts/login/", "/login/", "/service-worker.js"):
            reponse = client.get(adresse)
            corps = (reponse.content if hasattr(reponse, "content") else b"".join(reponse.streaming_content)).decode("utf-8", "replace")
            self.assertNotIn("Bretagne", corps, adresse)

    def test_la_verification_couvre_au_moins_toutes_les_routes_construisibles(self):
        construisibles = [p for p in self.points if p.url_exemple and regle_de(p).classe != PUBLIC]
        self.assertGreater(len(construisibles), 250)

    def test_l_ecriture_anonyme_de_l_api_de_maintenance_est_refusee(self):
        """Nouvelle protection L29 : RolePermission laissait passer l'anonyme quand le seuil d'écriture était celui d'un équipier."""
        client = Client()
        for adresse in ("/api/maintenance/occurrences/", "/api/maintenance/executions/", "/api/maintenance/occurrences/1/start/",
                        "/api/maintenance/occurrences/1/complete/"):
            self.assertIn(client.post(adresse, {}).status_code, (401, 403), adresse)

    def test_l_ecriture_anonyme_de_l_api_de_formation_est_refusee(self):
        """Nouvelle protection L29 : la permission des sessions de formation ne vérifiait pas la connexion (PUT, PATCH, DELETE,
        et POST ne portant que sur les présences)."""
        client = Client()
        self.assertIn(client.post("/api/training/sessions/", {"attendees": []}, content_type="application/json").status_code, (401, 403))
        for methode in ("put", "patch", "delete"):
            self.assertIn(getattr(client, methode)("/api/training/sessions/1/").status_code, (401, 403), methode)

    def test_des_identifiants_de_connexion_http_invalides_ne_donnent_aucun_acces(self):
        client = Client(HTTP_AUTHORIZATION="Basic " + "aW5jb25udTppbmNvbm51")  # « inconnu:inconnu », compte inexistant
        for adresse in ("/api/accounts/users/", "/api/maintenance/occurrences/", "/api/logistics/tickets/"):
            self.assertIn(client.get(adresse).status_code, (401, 403), adresse)
            self.assertIn(client.post(adresse, {}).status_code, (401, 403), adresse)

    def test_les_requetes_json_et_htmx_anonymes_sont_aussi_refusees(self):
        client = Client(HTTP_ACCEPT="application/json", HTTP_HX_REQUEST="true")
        for adresse in ("/calendar/events/", "/notifications/panneau/", "/search/rapide/", "/taches/", "/dashboard/flotte/"):
            reponse = client.get(adresse)
            self.assertTrue(reponse.status_code in (401, 403) or (reponse.status_code == 302 and "login" in reponse["Location"]), adresse)
