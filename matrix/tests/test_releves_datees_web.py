"""Relèves datées au niveau HTTP : saisie dans le fuseau du bâtiment, middleware, droits, API, administration."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from accounts.models import AuditLog, UserProfile
from matrix.core.fuseau import champ_local
from matrix.core.tasks import appliquer_releves_echues as tache_appliquer
from org.models import ReleveEquipage, Ship
from org.tests.test_releves_datees import Base, a_l_instant

User = get_user_model()


def client_de(utilisateur):
    client = Client()
    client.force_login(utilisateur)
    return client


class SaisieWebTests(Base):
    def proposer_web(self, utilisateur, **plus):
        donnees = {"action": "proposer_releve", "equipage": "B", "date_effet": champ_local(self.navire, timezone.now() + timedelta(hours=3))}
        donnees.update(plus)
        return client_de(utilisateur).post("/parametre/", donnees, follow=True)

    def test_saisie_interpretee_dans_le_fuseau_du_batiment_et_stockee_en_utc(self):
        self.proposer_web(self.cdt_a, date_effet="2099-07-01T12:00")
        self.assertEqual(ReleveEquipage.objects.get().date_effet.isoformat(), "2099-07-01T10:00:00+00:00")

    def test_meme_saisie_dans_un_autre_fuseau_donne_un_autre_instant(self):
        Ship.objects.filter(pk=self.navire.pk).update(fuseau_horaire="Pacific/Noumea")
        self.navire.refresh_from_db()
        self.proposer_web(self.cdt_a, date_effet="2099-07-01T12:00")
        self.assertEqual(ReleveEquipage.objects.get().date_effet.isoformat(), "2099-07-01T01:00:00+00:00")

    def test_date_passee_ou_absente_refusee(self):
        reponse = self.proposer_web(self.cdt_a, date_effet="2020-01-01T12:00")
        self.assertContains(reponse, "ne peut pas être dans le passé")
        reponse = self.proposer_web(self.cdt_a, date_effet="")
        self.assertContains(reponse, "Indiquez la date et l&#x27;heure d&#x27;effet")
        self.assertFalse(ReleveEquipage.objects.exists())

    def test_page_indique_le_fuseau_et_la_releve_planifiee(self):
        releve = self.planifier()
        page = client_de(self.cdt_a).get("/parametre/?tab=equipage")
        self.assertContains(page, "Fuseau du bâtiment : Europe/Paris")
        self.assertContains(page, "Relève planifiée")
        self.assertContains(page, "annuler_releve_planifiee")
        self.assertContains(page, "(Europe/Paris)")
        ReleveEquipage.objects.filter(pk=releve.pk).update(statut="annulee")
        Ship.objects.filter(pk=self.navire.pk).update(fuseau_horaire="")
        page = client_de(self.cdt_a).get("/parametre/?tab=equipage")
        self.assertContains(page, "Fuseau par défaut hérité : Europe/Paris")
        self.assertContains(page, 'type="datetime-local"')


class AnnulationWebTests(Base):
    def annuler(self, utilisateur, motif="Report"):
        return client_de(utilisateur).post("/parametre/", {"action": "annuler_releve_planifiee", "motif": motif}, follow=True)

    def test_le_commandement_a_terre_peut_annuler_malgre_la_lecture_seule(self):
        releve = self.planifier()
        self.assertEqual(self.annuler(self.second_b).status_code, 200)
        releve.refresh_from_db()
        self.assertEqual(releve.statut, ReleveEquipage.Statut.ANNULEE)

    def test_equipier_ou_motif_vide_sans_effet(self):
        releve = self.planifier()
        self.annuler(self.equipier_a)
        self.annuler(self.equipier_b)
        reponse = self.annuler(self.cdt_a, motif="")
        self.assertContains(reponse, "justification de l&#x27;annulation est obligatoire")
        releve.refresh_from_db()
        self.assertEqual(releve.statut, ReleveEquipage.Statut.PLANIFIEE)

    def test_annulation_apres_la_date_refusee(self):
        releve = self.planifier()
        with a_l_instant(releve.date_effet + timedelta(minutes=1)):
            reponse = self.annuler(self.cdt_a)
        self.assertContains(reponse, "déjà été appliquée")
        releve.refresh_from_db()
        self.assertEqual(releve.statut, ReleveEquipage.Statut.VALIDEE)


class FuseauWebTests(Base):
    def changer(self, utilisateur, nom="Pacific/Noumea"):
        return client_de(utilisateur).post("/parametre/", {"action": "modifier_fuseau", "fuseau_horaire": nom}, follow=True)

    def test_l_administrateur_de_l_unite_change_le_fuseau_sans_toucher_aux_instants(self):
        releve = self.planifier()
        avant = releve.date_effet
        self.changer(self.admin_navire)
        self.navire.refresh_from_db()
        self.assertEqual(self.navire.fuseau_horaire, "Pacific/Noumea")
        releve.refresh_from_db()
        self.assertEqual(releve.date_effet, avant)
        self.assertTrue(AuditLog.objects.filter(action="fuseau_horaire_modifie", actor=self.admin_navire).exists())

    def test_commandant_ou_equipier_ne_changent_pas_le_fuseau(self):
        for utilisateur in (self.cdt_a, self.equipier_a):
            self.changer(utilisateur)
            self.navire.refresh_from_db()
            self.assertEqual(self.navire.fuseau_horaire, "Europe/Paris", utilisateur.username)

    def test_equipage_a_terre_bloque_par_le_middleware(self):
        # Même habilité (seuil abaissé), l'équipage à terre ne modifie pas un réglage du bâtiment.
        UserProfile.objects.filter(user=self.cdt_b).update(role="ADMIN_NAVIRE")
        reponse = self.changer(self.cdt_b)
        self.assertEqual(reponse.status_code, 403)
        self.navire.refresh_from_db()
        self.assertEqual(self.navire.fuseau_horaire, "Europe/Paris")

    def test_fuseau_invalide_refuse(self):
        self.changer(self.admin_navire, "Mars/Olympus")
        self.navire.refresh_from_db()
        self.assertEqual(self.navire.fuseau_horaire, "Europe/Paris")


class MiddlewareAccesseurTests(Base):
    """La lecture seule de l'équipage à terre suit l'équipage à bord à l'instant, sans tâche ni page préalable."""

    def ecrire(self, utilisateur):
        return client_de(utilisateur).post("/taches/", {"assigne": self.equipier_a.pk, "titre": "Test"}).status_code

    def test_la_bascule_a_la_date_d_effet_change_qui_peut_ecrire(self):
        releve = self.planifier()
        with a_l_instant(releve.date_effet - timedelta(minutes=1)):
            self.assertNotEqual(self.ecrire(self.cdt_a), 403)
            self.assertEqual(self.ecrire(self.cdt_b), 403)
        self.assertEqual(Ship.objects.get(pk=self.navire.pk).equipage_a_bord, "A")
        with a_l_instant(releve.date_effet + timedelta(seconds=1)):
            self.assertEqual(self.ecrire(self.cdt_a), 403)
            self.assertNotEqual(self.ecrire(self.cdt_b), 403)
        self.assertEqual(Ship.objects.get(pk=self.navire.pk).equipage_a_bord, "B")


class TacheTests(Base):
    def test_tache_planifiee_applique_les_releves_echues(self):
        from django.conf import settings

        self.assertEqual(
            settings.CELERY_BEAT_SCHEDULE["appliquer_releves_echues_minute"]["task"], "matrix.core.tasks.appliquer_releves_echues"
        )
        releve = self.planifier()
        with a_l_instant(releve.date_effet + timedelta(minutes=1)):
            self.assertEqual(tache_appliquer(), 1)
            self.assertEqual(tache_appliquer(), 0)
        self.navire.refresh_from_db()
        self.assertEqual(self.navire.equipage_a_bord, "B")


class ApiEtAdministrationTests(Base):
    def test_api_expose_l_equipage_a_bord_apres_application_des_releves_echues(self):
        releve = self.planifier()
        with a_l_instant(releve.date_effet + timedelta(minutes=1)):
            reponse = client_de(self.admin_navire).get(f"/api/org/ships/{self.navire.pk}/")
        self.assertEqual(reponse.json()["equipage_a_bord"], "B")
        self.assertEqual(reponse.json()["fuseau_horaire"], "Europe/Paris")

    def test_creation_d_un_batiment_exige_un_fuseau_explicite(self):
        donnees = {"name": "Nouveau", "code": "NOU", "type_unite": "NAVIRE"}
        self.assertEqual(client_de(self.cdt_a).post("/api/org/ships/", donnees, content_type="application/json").status_code, 403)
        client = client_de(self.master)
        reponse = client.post("/api/org/ships/", donnees, content_type="application/json")
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("fuseau_horaire", reponse.json())
        reponse = client.post("/api/org/ships/", {**donnees, "fuseau_horaire": "Mars/Olympus"}, content_type="application/json")
        self.assertEqual(reponse.status_code, 400)
        reponse = client.post("/api/org/ships/", {**donnees, "fuseau_horaire": "Atlantic/Reykjavik"}, content_type="application/json")
        self.assertEqual(reponse.status_code, 201, reponse.content)
        self.assertEqual(Ship.objects.get(code="NOU").fuseau_horaire, "Atlantic/Reykjavik")

    def test_modification_du_fuseau_par_l_api_reservee_a_l_administration(self):
        url = f"/api/org/ships/{self.navire.pk}/"
        reponse = client_de(self.cdt_a).patch(url, {"fuseau_horaire": "Pacific/Noumea"}, content_type="application/json")
        self.assertIn(reponse.status_code, (403, 404))
        reponse = client_de(self.admin_navire).patch(url, {"fuseau_horaire": "Pacific/Noumea"}, content_type="application/json")
        self.assertEqual(reponse.status_code, 200, reponse.content)
        self.navire.refresh_from_db()
        self.assertEqual(self.navire.fuseau_horaire, "Pacific/Noumea")
        self.assertTrue(AuditLog.objects.filter(action="fuseau_horaire_modifie").exists())

    def test_creation_d_unite_par_les_reglages_exige_un_fuseau(self):
        root = User.objects.create_superuser("root", "r@navy.fr", "pass")
        client = client_de(root)
        client.post("/parametre/", {"action": "add_ship", "name": "Sans", "code": "SAN", "next_tab": "navires"})
        self.assertFalse(Ship.objects.filter(code="SAN").exists())
        client.post("/parametre/", {
            "action": "add_ship", "name": "Avec", "code": "AVE", "fuseau_horaire": "Europe/Paris", "next_tab": "navires",
        })
        self.assertEqual(Ship.objects.get(code="AVE").fuseau_horaire, "Europe/Paris")
        client.post("/parametre/", {
            "action": "duplicate_ship", "source_pk": self.navire.pk, "name": "Copie", "code": "COP", "next_tab": "navires",
        })
        self.assertFalse(Ship.objects.filter(code="COP").exists())
        client.post("/parametre/", {
            "action": "duplicate_ship", "source_pk": self.navire.pk, "name": "Copie", "code": "COP",
            "fuseau_horaire": "Pacific/Noumea", "next_tab": "navires",
        })
        self.assertEqual(Ship.objects.get(code="COP").fuseau_horaire, "Pacific/Noumea")

    def test_administration_django_ne_ecrase_pas_une_releve_appliquee_entre_temps(self):
        root = User.objects.create_superuser("root", "r@navy.fr", "pass")
        client = client_de(root)
        url = f"/admin/org/ship/{self.navire.pk}/change/"
        formulaire = {
            "name": "Bretagne renommée", "code": "BRE", "type_unite": "NAVIRE", "classe_navire": "",
            "double_equipage": "on", "equipage_a_bord": "A", "fuseau_horaire": "Europe/Paris",
            "initial-equipage_a_bord": "A",
        }
        releve = self.planifier()
        with a_l_instant(releve.date_effet + timedelta(minutes=1)):
            reponse = client.post(url, formulaire)
        self.assertEqual(reponse.status_code, 302, getattr(reponse, "content", b"")[:2000])
        self.navire.refresh_from_db()
        self.assertEqual((self.navire.name, self.navire.equipage_a_bord), ("Bretagne renommée", "B"))

    def test_administration_django_exige_un_fuseau_pour_un_nouveau_batiment(self):
        root = User.objects.create_superuser("root", "r@navy.fr", "pass")
        client = client_de(root)
        formulaire = {"name": "Neuf", "code": "NEU", "type_unite": "NAVIRE", "classe_navire": "", "equipage_a_bord": ""}
        reponse = client.post("/admin/org/ship/add/", formulaire)
        self.assertEqual(reponse.status_code, 200)
        self.assertFalse(Ship.objects.filter(code="NEU").exists())
        reponse = client.post("/admin/org/ship/add/", {**formulaire, "fuseau_horaire": "Europe/Paris"})
        self.assertEqual(reponse.status_code, 302)
        self.assertTrue(Ship.objects.filter(code="NEU").exists())
