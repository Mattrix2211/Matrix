"""Tests du workflow d'échange de tours de service de garde (VISION §7.4)."""
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import AuditLog, ServiceFunctionChoice, UserProfile
from calendar_app.views import evenements_utilisateur_jour
from notifications.models import Notification
from org.models import Sector, Service, Ship
from quarts.echanges import (
    EchangeImpossible,
    accepter_echange,
    analyser_echange,
    proposer_echange,
    valider_echange,
)
from quarts.models import (
    ChefDeListe,
    CreneauQuart,
    CreneauServiceGarde,
    EchangeService,
    Quart,
    ServiceGarde,
)
from accounts.models import FonctionQuartChoice
from training.models import TrainingCourse, TrainingRecord


def _marin(nom, secteur):
    user = User.objects.create_user(username=nom, password="pass")
    UserProfile.objects.update_or_create(user=user, defaults={"role": "EQUIPIER", "sector": secteur})
    return user


class BaseEchangeTests(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Échange", code="ECH")
        self.sector = Sector.objects.create(service=Service.objects.create(ship=self.ship, name="Pont"), name="Manœuvre")
        self.a = _marin("marin_a", self.sector)
        self.b = _marin("marin_b", self.sector)
        self.c = _marin("marin_c", self.sector)
        self.chef = _marin("chef_liste", self.sector)
        ChefDeListe.objects.create(user=self.chef, sector=self.sector)
        self.autre_chef = _marin("chef_autre", self.sector)
        self.autre_secteur = Sector.objects.create(service=self.sector.service, name="Autre")
        ChefDeListe.objects.create(user=self.autre_chef, sector=self.autre_secteur)

        aujourdhui = timezone.localdate()
        self.garde = ServiceGarde.objects.create(
            sector=self.sector, fonction=ServiceFunctionChoice.objects.create(name="Permanence"),
            date_debut=aujourdhui, date_fin=aujourdhui + timedelta(days=30),
            statut=ServiceGarde.STATUT_PUBLIEE, created_by=self.chef,
        )
        base = timezone.now() + timedelta(days=5)
        self.creneau_a = self._creneau(base, self.a)
        self.creneau_b = self._creneau(base + timedelta(days=1), self.b)

    def _creneau(self, debut, marin, garde=None):
        return CreneauServiceGarde.objects.create(
            service_garde=garde or self.garde, poste="Officier de quart", debut=debut,
            fin=debut + timedelta(hours=24), marin=marin,
        )

    def _echange_accepte(self):
        echange = proposer_echange(self.a, self.creneau_a, self.creneau_b, "Rendez-vous médical")
        accepter_echange(echange, self.b)
        echange.refresh_from_db()
        return echange


class WorkflowTests(BaseEchangeTests):
    def test_workflow_complet_permute_les_tours_et_historise(self):
        echange = proposer_echange(self.a, self.creneau_a, self.creneau_b, "Rendez-vous médical")
        self.assertEqual(echange.statut, EchangeService.STATUT_DEMANDE)
        self.assertTrue(Notification.objects.filter(user=self.b, object_id=str(echange.pk)).exists())

        accepter_echange(echange, self.b)
        self.assertTrue(Notification.objects.filter(user=self.chef, verb__contains="à valider").exists())
        self.assertTrue(Notification.objects.filter(user=self.a, verb__contains="accepté").exists())
        # Tant que le chef n'a pas validé, rien ne bouge.
        self.creneau_a.refresh_from_db()
        self.assertEqual(self.creneau_a.marin, self.a)

        echange.refresh_from_db()
        valider_echange(echange, self.chef)
        self.creneau_a.refresh_from_db()
        self.creneau_b.refresh_from_db()
        self.assertEqual(self.creneau_a.marin, self.b)
        self.assertEqual(self.creneau_b.marin, self.a)

        echange.refresh_from_db()
        self.assertEqual(echange.statut, EchangeService.STATUT_VALIDE)
        # La situation d'avant reste lisible (jamais d'écrasement silencieux).
        self.assertEqual(echange.demandeur, self.a)
        self.assertEqual(echange.cible, self.b)
        self.assertEqual(
            list(echange.evenements.values_list("action", flat=True)), ["demande", "acceptation", "validation"]
        )
        journal = AuditLog.objects.get(action="echange_service_validation")
        self.assertIn("marin_a -> marin_b", journal.details)
        for user in (self.a, self.b, self.chef):
            self.assertTrue(Notification.objects.filter(user=user, verb__startswith="Échange validé").exists())

    def test_calendriers_personnels_mis_a_jour(self):
        echange = self._echange_accepte()
        valider_echange(echange, self.chef)
        jour_a = timezone.localtime(self.creneau_a.debut).date()
        self.assertEqual(evenements_utilisateur_jour(self.b, jour_a)["creneaux"], [self.creneau_a])
        self.assertEqual(evenements_utilisateur_jour(self.a, jour_a)["creneaux"], [])

    def test_refus_du_marin_ne_change_rien_et_notifie_le_demandeur(self):
        from quarts.echanges import refuser_echange
        echange = proposer_echange(self.a, self.creneau_a, self.creneau_b)
        refuser_echange(echange, self.b, "Indisponible")
        echange.refresh_from_db()
        self.assertEqual(echange.statut, EchangeService.STATUT_REFUSE)
        self.creneau_a.refresh_from_db()
        self.assertEqual(self.creneau_a.marin, self.a)
        self.assertTrue(Notification.objects.filter(user=self.a, verb__contains="Indisponible").exists())

    def test_refus_du_chef_notifie_les_deux_marins(self):
        from quarts.echanges import rejeter_echange
        echange = self._echange_accepte()
        rejeter_echange(echange, self.chef, "Effectif insuffisant")
        echange.refresh_from_db()
        self.assertEqual(echange.statut, EchangeService.STATUT_REJETE)
        for user in (self.a, self.b):
            self.assertTrue(Notification.objects.filter(user=user, verb__contains="Effectif insuffisant").exists())

    def test_on_ne_valide_pas_avant_l_accord_du_marin(self):
        echange = proposer_echange(self.a, self.creneau_a, self.creneau_b)
        with self.assertRaises(EchangeImpossible):
            valider_echange(echange, self.chef)

    def test_seul_le_chef_de_la_liste_valide(self):
        echange = self._echange_accepte()
        for intrus in (self.a, self.b, self.c, self.autre_chef):
            with self.assertRaises(EchangeImpossible):
                valider_echange(echange, intrus)

    def test_seul_le_marin_sollicite_accepte(self):
        echange = proposer_echange(self.a, self.creneau_a, self.creneau_b)
        with self.assertRaises(EchangeImpossible):
            accepter_echange(echange, self.c)
        with self.assertRaises(EchangeImpossible):
            accepter_echange(echange, self.a)

    def test_annulation_par_le_demandeur(self):
        from quarts.echanges import annuler_echange
        echange = proposer_echange(self.a, self.creneau_a, self.creneau_b)
        with self.assertRaises(EchangeImpossible):
            annuler_echange(echange, self.b)
        annuler_echange(echange, self.a)
        echange.refresh_from_db()
        self.assertEqual(echange.statut, EchangeService.STATUT_ANNULE)
        with self.assertRaises(EchangeImpossible):
            accepter_echange(echange, self.b)


class SituationsImpossiblesTests(BaseEchangeTests):
    def _message(self, exc):
        return " ".join(exc.exception.problemes)

    def test_pas_de_demande_sur_le_tour_d_un_autre(self):
        with self.assertRaises(EchangeImpossible):
            proposer_echange(self.c, self.creneau_a, self.creneau_b)

    def test_pas_d_echange_avec_soi_meme_ni_avec_un_tour_vide(self):
        libre = self._creneau(timezone.now() + timedelta(days=9), None)
        with self.assertRaises(EchangeImpossible):
            proposer_echange(self.a, self.creneau_a, libre)
        autre_a = self._creneau(timezone.now() + timedelta(days=10), self.a)
        with self.assertRaises(EchangeImpossible):
            proposer_echange(self.a, self.creneau_a, autre_a)

    def test_double_demande_sur_le_meme_tour_refusee(self):
        proposer_echange(self.a, self.creneau_a, self.creneau_b)
        with self.assertRaises(EchangeImpossible):
            proposer_echange(self.b, self.creneau_b, self.creneau_a)

    def test_conflit_d_affectation_explique(self):
        # B a déjà une autre garde qui chevauche le tour de A.
        self._creneau(self.creneau_a.debut + timedelta(hours=2), self.b)
        with self.assertRaises(EchangeImpossible) as ctx:
            proposer_echange(self.a, self.creneau_a, self.creneau_b)
        self.assertIn("Conflit d'affectation", self._message(ctx))
        self.assertIn("marin_b", self._message(ctx))

    def test_conflit_avec_un_quart_publie(self):
        quart = Quart.objects.create(
            sector=self.sector, fonction=FonctionQuartChoice.objects.create(name="Barre"),
            date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=30),
            statut=Quart.STATUT_PUBLIEE,
        )
        CreneauQuart.objects.create(
            quart=quart, poste="Barre", debut=self.creneau_b.debut + timedelta(hours=1),
            fin=self.creneau_b.debut + timedelta(hours=5), marin=self.a,
        )
        with self.assertRaises(EchangeImpossible) as ctx:
            proposer_echange(self.a, self.creneau_a, self.creneau_b)
        self.assertIn("Conflit d'affectation", self._message(ctx))

    def test_habilitation_manquante_expliquee_puis_ok_une_fois_valide(self):
        formation = TrainingCourse.objects.create(title="Officier de quart quai")
        self.garde.formations_requises.add(formation)
        with self.assertRaises(EchangeImpossible) as ctx:
            proposer_echange(self.a, self.creneau_a, self.creneau_b)
        self.assertIn("Habilitation manquante", self._message(ctx))
        self.assertIn("Officier de quart quai", self._message(ctx))

        for marin in (self.a, self.b):
            TrainingRecord.objects.create(
                user=marin, course=formation, completed_at=date.today() - timedelta(days=30),
                expires_at=date.today() + timedelta(days=300),
            )
        self.assertEqual(proposer_echange(self.a, self.creneau_a, self.creneau_b).statut, "DEMANDE")

    def test_habilitation_expiree_le_jour_du_tour(self):
        formation = TrainingCourse.objects.create(title="Habilitation X")
        self.garde.formations_requises.add(formation)
        for marin in (self.a, self.b):
            TrainingRecord.objects.create(
                user=marin, course=formation, completed_at=date.today() - timedelta(days=300),
                expires_at=date.today() + timedelta(days=2),
            )
        with self.assertRaises(EchangeImpossible) as ctx:
            proposer_echange(self.a, self.creneau_a, self.creneau_b)
        self.assertIn("Habilitation manquante", self._message(ctx))

    def test_delai_minimal_configurable(self):
        self.garde.delai_minimal_echange_heures = 24 * 7
        self.garde.save()
        with self.assertRaises(EchangeImpossible) as ctx:
            proposer_echange(self.a, self.creneau_a, self.creneau_b)
        self.assertIn("à l'avance", self._message(ctx))

    def test_tour_deja_commence(self):
        self.creneau_a.debut = timezone.now() - timedelta(hours=1)
        self.creneau_a.save()
        with self.assertRaises(EchangeImpossible) as ctx:
            proposer_echange(self.a, self.creneau_a, self.creneau_b)
        self.assertIn("déjà commencé", self._message(ctx))

    def test_situation_changee_entre_accord_et_validation(self):
        echange = self._echange_accepte()
        self.creneau_b.marin = self.c
        self.creneau_b.save()
        problemes = analyser_echange(echange)
        self.assertTrue(any("la situation a changé" in p for p in problemes))
        with self.assertRaises(EchangeImpossible):
            valider_echange(echange, self.chef)
        self.creneau_a.refresh_from_db()
        self.assertEqual(self.creneau_a.marin, self.a)

    def test_liste_non_publiee(self):
        self.garde.statut = ServiceGarde.STATUT_BROUILLON
        self.garde.save()
        with self.assertRaises(EchangeImpossible):
            proposer_echange(self.a, self.creneau_a, self.creneau_b)


class VuesEchangeTests(BaseEchangeTests):
    def test_bouton_proposer_un_echange_visible_sur_son_tour(self):
        self.client.login(username="marin_a", password="pass")
        r = self.client.get(f"/quarts/garde/{self.garde.pk}/")
        self.assertContains(r, "Proposer un échange", count=1)
        self.client.login(username="marin_c", password="pass")
        self.assertNotContains(self.client.get(f"/quarts/garde/{self.garde.pk}/"), "Proposer un échange")

    def test_proposition_puis_reponse_puis_validation_via_http(self):
        self.client.login(username="marin_a", password="pass")
        r = self.client.post(
            f"/quarts/garde/{self.garde.pk}/echanges/proposer/",
            {"creneau_id": self.creneau_a.pk, "cible_creneau_id": self.creneau_b.pk, "motif": "Famille"},
        )
        self.assertRedirects(r, "/quarts/echanges/")
        echange = EchangeService.objects.get()
        self.client.login(username="marin_b", password="pass")
        self.assertContains(self.client.get("/quarts/echanges/"), "Accepter")
        self.client.post(f"/quarts/echanges/{echange.pk}/accepter/")
        self.client.login(username="chef_liste", password="pass")
        self.assertContains(self.client.get("/quarts/echanges/"), "Valider l'échange")
        self.client.post(f"/quarts/echanges/{echange.pk}/valider/")
        echange.refresh_from_db()
        self.assertEqual(echange.statut, EchangeService.STATUT_VALIDE)
        self.creneau_a.refresh_from_db()
        self.assertEqual(self.creneau_a.marin, self.b)

    def test_un_marin_ne_voit_que_ses_demandes(self):
        proposer_echange(self.a, self.creneau_a, self.creneau_b)
        self.client.login(username="marin_c", password="pass")
        r = self.client.get("/quarts/echanges/")
        self.assertNotContains(r, "marin_a")
        self.assertEqual(self.client.post(f"/quarts/echanges/{EchangeService.objects.get().pk}/accepter/").status_code, 400)

    def test_chef_d_un_autre_perimetre_ne_voit_ni_ne_valide(self):
        echange = self._echange_accepte()
        self.client.login(username="chef_autre", password="pass")
        self.assertNotContains(self.client.get("/quarts/echanges/"), "marin_a")
        self.assertEqual(self.client.post(f"/quarts/echanges/{echange.pk}/valider/").status_code, 400)

    def test_erreur_expliquee_a_l_ecran(self):
        self._creneau(self.creneau_a.debut + timedelta(hours=2), self.b)
        self.client.login(username="marin_a", password="pass")
        r = self.client.post(
            f"/quarts/garde/{self.garde.pk}/echanges/proposer/",
            {"creneau_id": self.creneau_a.pk, "cible_creneau_id": self.creneau_b.pk},
            follow=True,
        )
        self.assertContains(r, "Conflit d&#x27;affectation")
        self.assertFalse(EchangeService.objects.exists())

    def test_suppression_d_un_creneau_annule_les_echanges_en_cours(self):
        echange = proposer_echange(self.a, self.creneau_a, self.creneau_b)
        self.client.login(username="chef_liste", password="pass")
        self.client.post(
            f"/quarts/garde/{self.garde.pk}/", {"action": "supprimer_creneau", "creneau_id": self.creneau_b.pk}
        )
        echange.refresh_from_db()
        self.assertEqual(echange.statut, EchangeService.STATUT_ANNULE)
        self.assertTrue(Notification.objects.filter(user=self.a, verb__contains="annulé").exists())

    def test_chef_regle_les_conditions_d_echange(self):
        formation = TrainingCourse.objects.create(title="Habilitation Y")
        self.client.login(username="chef_liste", password="pass")
        self.client.post(f"/quarts/garde/{self.garde.pk}/", {
            "action": "regler_echanges", "delai_minimal_echange_heures": "12",
            "formations_requises": [formation.pk],
        })
        self.garde.refresh_from_db()
        self.assertEqual(self.garde.delai_minimal_echange_heures, 12)
        self.assertEqual(list(self.garde.formations_requises.all()), [formation])
        # Un marin simple ne peut pas modifier ces règles.
        self.client.login(username="marin_a", password="pass")
        r = self.client.post(f"/quarts/garde/{self.garde.pk}/", {"action": "regler_echanges", "delai_minimal_echange_heures": "0"})
        self.assertEqual(r.status_code, 400)
        self.garde.refresh_from_db()
        self.assertEqual(self.garde.delai_minimal_echange_heures, 12)
