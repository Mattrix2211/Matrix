"""Feuilles publiées figées et versions rectificatives : la version publiée est
immuable, l'écart avec le planning effectif est signalé, un rectificatif suit
le circuit de visa et ne remplace la version qu'à sa publication."""
from datetime import datetime, timedelta
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, ServiceFunctionChoice, UserProfile
from notifications.models import Notification
from org.models import Ship
from quarts.models import (
    CreneauServiceGarde,
    FeuilleService,
    FonctionFeuilleService,
    PosteAlerte,
    ScenarioAlerte,
    ServiceGarde,
    peut_lire_feuille_service,
)
from quarts.rectificatif import divergences_effectives
from quarts.services import feuille_service_du_jour_pour
from quarts.tests.test_feuille_service import FeuilleServiceTestsBase, _utilisateur


class RectificatifBase(FeuilleServiceTestsBase):
    def setUp(self):
        super().setUp()
        self.scenario = ScenarioAlerte.objects.create(
            ship=self.ship, libelle="Alerte intrus", famille=ScenarioAlerte.FAMILLE_PROTECTION,
        )
        PosteAlerte.objects.create(scenario=self.scenario, libelle="PC sécu", fonction=self.fonction, obligatoire=True)
        self.relais = _utilisateur("marin_relais", "EQUIPIER", ship=self.ship)
        self.creneau = self._publier_tour(marin=self.marin_service)
        self.feuille = FeuilleService.objects.create(
            ship=self.ship, date=self.jour, created_by=self.equipier, updated_by=self.equipier,
        )
        self.url = reverse("feuille-service-detail", args=[self.ship.pk, f"{self.jour:%Y-%m-%d}"])
        self._circuit()

    def _circuit(self):
        self.feuille.proposer(self.chef_service)
        self.feuille.viser_service(self.chef_service)
        self.feuille.viser_comaeq(self.etat_major)
        self.feuille.refresh_from_db()

    def _echange(self, marin):
        """Le planning publié change de titulaire (effet d'un échange de service validé)."""
        self.creneau.marin = marin
        self.creneau.save(update_fields=["marin", "updated_at"])

    def _post(self, username, action):
        self.client.force_login(User.objects.get(username=username))
        return self.client.post(self.url, {"action": action})

    def _circuit_rectificatif(self):
        self._post("bsc", "proposer")
        self._post("chef_secteur", "viser_secteur")
        self._post("chef_service", "viser_service")
        self._post("etat_major", "viser_comaeq")

    def _page(self, username):
        self.client.force_login(User.objects.get(username=username))
        return self.client.get(self.url)


class PublicationFigeeTests(RectificatifBase):
    def test_titulaires_et_alertes_lus_dans_la_version_apres_un_echange(self):
        self._echange(self.relais)
        self.assertEqual(self.feuille.personnel[0]["marin_fige"], "marin_service")
        reponse = self._page("bsc")
        self.assertEqual(reponse.context["personnel"][0]["marin_fige"], "marin_service")
        poste = reponse.context["alertes"][0]["postes"][0]
        self.assertEqual((poste["marin_fige"], poste["arme"]), ("marin_service", True))
        self.assertContains(reponse, "Alerte intrus")

    def test_la_version_n_est_jamais_modifiee(self):
        avant = self.feuille.versions.get().contenu_fige
        self._echange(self.relais)
        self._page("bsc")
        self.assertEqual(self.feuille.versions.get().contenu_fige, avant)
        self.assertEqual(self.feuille.versions.count(), 1)

    def test_le_contenu_figé_porte_les_identifiants_des_marins(self):
        contenu = self.feuille.versions.get().contenu_fige
        self.assertEqual(contenu["personnel"][0]["marin_id"], self.marin_service.pk)
        self.assertEqual(contenu["alertes"][0]["postes"][0]["marin_id"], self.marin_service.pk)

    def test_je_suis_de_service_suit_la_version(self):
        self._echange(self.relais)
        self.assertTrue(feuille_service_du_jour_pour(self.marin_service, self.jour)["je_suis_de_service"])
        self.assertFalse(feuille_service_du_jour_pour(self.relais, self.jour)["je_suis_de_service"])


class DivergenceTests(RectificatifBase):
    def test_aucune_divergence_sans_changement(self):
        self.assertEqual(divergences_effectives(self.feuille), [])
        self.assertNotContains(self._page("bsc"), "ont changé depuis la publication")

    def test_un_changement_de_titulaire_est_signale_sans_annuler_l_echange(self):
        self._echange(self.relais)
        libelles = {d["libelle"] for d in divergences_effectives(self.feuille)}
        self.assertEqual(libelles, {"Officier de garde", "Alerte intrus — PC sécu"})
        page = self._page("bsc").content.decode()
        self.assertIn("Les affectations effectives ont changé depuis la publication", page)
        self.assertIn("reste la référence publiée", page)
        self.assertIn("restent effectifs dans le planning", page)
        self.assertNotIn("annulé", page)
        self.creneau.refresh_from_db()
        self.assertEqual(self.creneau.marin, self.relais)

    def test_pas_de_rectificatif_sans_difference_effective(self):
        self.assertEqual(self._post("bsc", "ouvrir_rectificatif").status_code, 302)
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_PUBLIEE)
        self.assertFalse(AuditLog.objects.filter(action="feuille_service_rectificatif_ouvert").exists())

    def test_retour_au_titulaire_d_origine_efface_la_divergence(self):
        self._echange(self.relais)
        self._echange(self.marin_service)
        self.assertEqual(divergences_effectives(self.feuille), [])


class RectificatifTests(RectificatifBase):
    def _ouvrir(self):
        self._echange(self.relais)
        self.assertEqual(self._post("bsc", "ouvrir_rectificatif").status_code, 302)
        self.feuille.refresh_from_db()

    def test_ouverture_par_le_redacteur_habilite(self):
        self._ouvrir()
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_BROUILLON)
        self.assertTrue(self.feuille.rectificatif_en_cours)
        self.assertEqual(self.feuille.rectificatif_ouvert_par, self.equipier)
        self.assertEqual(self.feuille.versions.count(), 1)
        self.assertTrue(AuditLog.objects.filter(action="feuille_service_rectificatif_ouvert").exists())
        # Aucune notification avant la publication.
        self.assertFalse(Notification.objects.filter(verb__icontains="rectificative").exists())

    def test_la_version_publiee_reste_la_reference_et_n_est_pas_remplacee(self):
        self._ouvrir()
        version = self.feuille.versions.get()
        self.assertFalse(version.est_remplacee)
        # Un marin non acteur lit toujours la version publiée, sans 403.
        page = self._page("marin_service")
        self.assertEqual(page.status_code, 200)
        contenu = page.content.decode()
        self.assertIn("Version 1", contenu)
        self.assertEqual(page.context["personnel"][0]["marin_fige"], "marin_service")
        self.assertIn("ont changé depuis la publication", contenu)
        self.assertNotIn("Préparer un rectificatif", contenu)
        self.assertTrue(feuille_service_du_jour_pour(self.marin_service, self.jour)["je_suis_de_service"])

    def test_le_redacteur_voit_la_copie_de_travail_avec_les_nouvelles_affectations(self):
        self._ouvrir()
        contenu = self._page("bsc").content.decode()
        self.assertIn("Rectificatif en cours", contenu)
        self.assertEqual(self.feuille.personnel[0]["creneau"].marin, self.relais)

    def test_circuit_puis_publication_remplace_la_version(self):
        self._ouvrir()
        self._post("bsc", "proposer")
        self._post("chef_secteur", "viser_secteur")
        self._post("chef_service", "viser_service")
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_VISA_COMAEQ)
        self.assertFalse(self.feuille.versions.get().est_remplacee)
        self._post("etat_major", "viser_comaeq")
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_PUBLIEE)
        v1, v2 = self.feuille.versions.order_by("numero")
        self.assertTrue(v1.est_remplacee)
        self.assertFalse(v2.est_remplacee)
        self.assertEqual((v2.numero, v2.remplace_numero), (2, 1))
        self.assertTrue(v2.est_rectificative)
        self.assertEqual(v2.contenu_fige["personnel"][0]["marin"], "marin_relais")
        self.assertEqual(v1.contenu_fige["personnel"][0]["marin"], "marin_service")
        self.assertIsNone(self.feuille.rectificatif_ouvert_par)
        self.assertEqual(divergences_effectives(self.feuille), [])

    def test_impression_et_historique_identifient_la_rectification(self):
        self._ouvrir()
        self._circuit_rectificatif()
        page = self._page("marin_service").content.decode()
        self.assertIn("Version rectificative n°2 — remplace la version 1", page)
        self.assertIn("window.print()", page)
        self.assertIn("Remplacée", page)
        self.assertIn("Référence publiée", page)
        self.assertIn("marin_relais", page)

    def test_notifications_a_la_publication_seulement(self):
        self._ouvrir()
        self._post("bsc", "proposer")
        self._post("chef_secteur", "viser_secteur")
        self._post("chef_service", "viser_service")
        self.assertFalse(Notification.objects.filter(verb__icontains="rectificative").exists())
        self._post("etat_major", "viser_comaeq")
        notifies = set(Notification.objects.filter(verb__icontains="rectificative").values_list("user__username", flat=True))
        # Ancien et nouveau titulaires touchés, et rédacteur du rectificatif.
        self.assertEqual(notifies, {"marin_service", "marin_relais", "bsc"})
        self.assertTrue(AuditLog.objects.filter(action="feuille_service_rectificatif_publie").exists())

    def test_plusieurs_echanges_sont_consolides_en_une_version(self):
        autre = _utilisateur("marin_autre", "EQUIPIER", ship=self.ship)
        self._echange(self.relais)
        self._echange(autre)
        self._post("bsc", "ouvrir_rectificatif")
        self._circuit_rectificatif()
        self.assertEqual(self.feuille.versions.count(), 2)
        self.assertEqual(self.feuille.versions.first().contenu_fige["personnel"][0]["marin"], "marin_autre")

    def test_renvoi_garde_la_version_de_reference_et_le_redacteur(self):
        self._ouvrir()
        self._post("bsc", "proposer")
        self.client.force_login(self.chef_secteur)
        self.client.post(self.url, {"action": "renvoyer", "motif": "À revoir"})
        self.feuille.refresh_from_db()
        self.assertEqual(self.feuille.statut, FeuilleService.STATUT_BROUILLON)
        self.assertTrue(self.feuille.rectificatif_en_cours)
        self.assertTrue(Notification.objects.filter(user=self.equipier, verb__icontains="renvoyée").exists())
        self.assertEqual(self.feuille.versions.count(), 1)

    def test_pas_de_second_rectificatif_pendant_le_premier(self):
        self._ouvrir()
        self.assertEqual(self._post("bsc", "ouvrir_rectificatif").status_code, 403)

    def test_rubrique_saisie_dans_le_rectificatif_ne_change_pas_la_version(self):
        self._ouvrir()
        self.client.force_login(self.equipier)
        self.client.post(self.url, {"action": "enregistrer_entete", f"rubrique_{self.rubrique_quotidienne.uid}": "Lundi"})
        entete = self.feuille.versions.get().contenu_fige["entete"]
        self.assertEqual([e["valeur"] for e in entete if e["libelle"] == "Type de journée"], [""])


class FausseDivergenceEtFuiteTests(RectificatifBase):
    def test_changement_de_grade_ou_de_nom_n_est_pas_une_divergence(self):
        UserProfile.objects.filter(user=self.marin_service).update(grade="CNE")
        User.objects.filter(pk=self.marin_service.pk).update(first_name="Paul", last_name="Durand")
        self.assertEqual(divergences_effectives(self.feuille), [])
        self.assertNotContains(self._page("bsc"), "ont changé depuis la publication")

    def test_ancienne_version_sans_identifiant_compare_le_texte(self):
        version = self.feuille.versions.get()
        for e in version.contenu_fige["personnel"]:
            e.pop("marin_id")
        version.save(update_fields=["contenu_fige"])
        self.assertEqual(divergences_effectives(self.feuille), [])
        self._echange(self.relais)
        self.assertTrue(divergences_effectives(self.feuille))

    def test_motif_de_renvoi_et_structure_invisibles_d_un_non_acteur(self):
        self._echange(self.relais)
        self.feuille.ouvrir_rectificatif(self.equipier)
        self.feuille.proposer(self.equipier)
        self.feuille.renvoyer(self.chef_secteur, "MOTIFSECRET")
        self.fonction.libelle = "Fonction modifiée"
        self.fonction.save()
        page = self._page("marin_service")
        self.assertNotContains(page, "MOTIFSECRET")
        self.assertNotContains(page, "ont changé depuis la création")
        self.assertContains(self._page("bsc"), "MOTIFSECRET")

    def test_echec_de_creation_de_version_laisse_la_feuille_inchangee(self):
        feuille = FeuilleService.objects.create(
            ship=self.ship, date=self.jour + timedelta(days=1), created_by=self.equipier,
        )
        feuille.proposer(self.chef_service)
        feuille.viser_service(self.chef_service)
        with mock.patch.object(FeuilleService, "creer_version", side_effect=RuntimeError("échec")):
            with self.assertRaises(RuntimeError):
                feuille.viser_comaeq(self.etat_major)
        feuille.refresh_from_db()
        self.assertEqual(feuille.statut, FeuilleService.STATUT_VISA_COMAEQ)
        self.assertFalse(feuille.versions.exists())
        self.assertIsNone(feuille.publiee_le)


class DroitsRectificatifTests(RectificatifBase):
    def test_marin_d_un_autre_navire_ne_peut_ni_lire_ni_ouvrir(self):
        _utilisateur("etranger", "EQUIPIER", ship=self.autre_ship)
        self._echange(self.relais)
        self.assertEqual(self._post("etranger", "ouvrir_rectificatif").status_code, 403)
        self.assertEqual(self._page("etranger").status_code, 403)

    def test_feuille_non_publiee_pas_d_ouverture(self):
        feuille = FeuilleService.objects.create(ship=self.ship, date=self.jour + timezone.timedelta(days=1))
        url = reverse("feuille-service-detail", args=[self.ship.pk, f"{feuille.date:%Y-%m-%d}"])
        self.client.force_login(self.equipier)
        self.assertEqual(self.client.post(url, {"action": "ouvrir_rectificatif"}).status_code, 403)

    def test_lecture_pendant_rectificatif_reservee_au_navire(self):
        self._echange(self.relais)
        self.feuille.ouvrir_rectificatif(self.equipier)
        self.feuille.refresh_from_db()
        self.assertTrue(peut_lire_feuille_service(self.marin_service, self.feuille))
        self.assertFalse(peut_lire_feuille_service(User.objects.get(username="etat_major_autre"), self.feuille))


class DoubleEquipageRectificatifTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(
            name="FREMM Rectif", code="FRE", classe_navire="FREMM", double_equipage=True, equipage_a_bord="A",
        )
        self.jour = timezone.localdate()
        self.fonction = FonctionFeuilleService.objects.create(ship=self.ship, libelle="Officier de garde", ordre=1)
        choix = ServiceFunctionChoice.objects.create(name="Officier de garde")
        self.marins = {}
        for e in ("A", "B"):
            for nom, role, coma in ((f"redacteur_{e}", "EQUIPIER", ""), (f"chef_{e}", "COMMANDANT", ""),
                                    (f"comaeq_{e}", "ETAT_MAJOR", "COMAEQ"), (f"titulaire_{e}", "EQUIPIER", ""),
                                    (f"relais_{e}", "EQUIPIER", "")):
                user = User.objects.create_user(username=nom, password="pass")
                UserProfile.objects.update_or_create(user=user, defaults={
                    "role": role, "ship": self.ship, "equipage": e, "fonction_coma": coma})
                self.marins[nom] = User.objects.get(pk=user.pk)
        self.url = reverse("feuille-service-detail", args=[self.ship.pk, f"{self.jour:%Y-%m-%d}"])
        garde = ServiceGarde.objects.create(
            ship=self.ship, fonction=choix, date_debut=self.jour, date_fin=self.jour, statut=ServiceGarde.STATUT_PUBLIEE,
        )
        debut = timezone.make_aware(datetime.combine(self.jour, datetime.min.time().replace(hour=8)))
        self.creneaux = {
            e: CreneauServiceGarde.objects.create(
                service_garde=garde, poste="Officier de garde", debut=debut, fin=debut + timedelta(hours=24),
                marin=self.marins[f"titulaire_{e}"],
            )
            for e in ("A", "B")
        }
        for e in ("A", "B"):
            feuille = FeuilleService.objects.create(
                ship=self.ship, equipage=e, date=self.jour, created_by=self.marins[f"redacteur_{e}"],
            )
            feuille.proposer(self.marins[f"chef_{e}"])
            feuille.viser_service(self.marins[f"chef_{e}"])
            feuille.viser_comaeq(self.marins[f"comaeq_{e}"])

    def _post(self, nom, action, suffixe=""):
        self.client.force_login(self.marins[nom])
        return self.client.post(self.url + suffixe, {"action": action})

    def _echange(self, e):
        c = self.creneaux[e]
        c.marin = self.marins[f"relais_{e}"]
        c.save(update_fields=["marin", "updated_at"])

    def test_l_equipage_a_terre_ouvre_et_publie_le_rectificatif_de_sa_feuille(self):
        self._echange("B")
        self.assertEqual(self._post("redacteur_B", "ouvrir_rectificatif").status_code, 302)
        self._post("chef_B", "proposer")
        self._post("chef_B", "viser_service")
        self._post("comaeq_B", "viser_comaeq")
        feuille = FeuilleService.objects.get(ship=self.ship, equipage="B", date=self.jour)
        self.assertEqual(feuille.versions.count(), 2)
        self.assertEqual(feuille.versions.first().remplace_numero, 1)
        autre = FeuilleService.objects.get(ship=self.ship, equipage="A", date=self.jour)
        self.assertEqual(autre.versions.count(), 1)

    def test_rectificatif_d_un_equipage_refuse_a_l_autre(self):
        self._echange("B")
        # Le paramètre forgé est ignoré : la feuille résolue est celle de l'équipage du rédacteur, sans divergence.
        self._post("redacteur_A", "ouvrir_rectificatif", "?equipage=B")
        self._post("redacteur_A", "ouvrir_rectificatif")
        self.assertFalse(FeuilleService.objects.get(ship=self.ship, equipage="A", date=self.jour).rectificatif_en_cours)
        self.assertFalse(FeuilleService.objects.get(ship=self.ship, equipage="B", date=self.jour).rectificatif_en_cours)

    def test_la_divergence_d_un_equipage_n_apparait_pas_chez_l_autre(self):
        self._echange("B")
        self.client.force_login(self.marins["redacteur_A"])
        self.assertNotContains(self.client.get(self.url), "ont changé depuis la publication")
        self.client.force_login(self.marins["redacteur_B"])
        self.assertContains(self.client.get(self.url), "ont changé depuis la publication")

    def test_le_comaeq_de_l_autre_equipage_ne_vise_pas_le_rectificatif(self):
        self._echange("B")
        self._post("redacteur_B", "ouvrir_rectificatif")
        self._post("chef_B", "proposer")
        self._post("chef_B", "viser_service")
        self.assertEqual(self._post("comaeq_A", "viser_comaeq").status_code, 403)
