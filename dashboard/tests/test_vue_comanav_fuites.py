"""Vue COMANAV : aucune fiche à viser, proposition, qualification ni dérive d'un autre bâtiment ne fuit sur la page."""
from datetime import date, timedelta

from django.utils import timezone

from accounts.models import ResponsableSpecialite, SpecialityChoice
from assets.mesures import derives_de
from assets.models import (
    CategorieCatalogue, ChecklistTemplate, InstallationIsolationReading, InstallationMaintenance, PropositionArticle,
)
from matrix.core.contexte_batiment import CLE_SESSION
from training.models import TrainingCourse, TrainingRecord

from .test_vue_comanav import BaseComanav


class FuitesInterNaviresTests(BaseComanav):
    def setUp(self):
        super().setUp()
        self.specialite = SpecialityChoice.objects.create(name="Mécanicien")
        self.categorie = CategorieCatalogue.objects.create(nom="Outillage", specialite=self.specialite)
        # Le COMANAV est aussi responsable de spécialité : il peut agir sur les circuits de TOUTE la flotte.
        ResponsableSpecialite.objects.create(specialite=self.specialite, user=self.comanav)
        self.redacteur = self._marin("redacteur", "CHEF_SECTION", self.navire)

    def _proposition(self, navire, service, designation):
        return PropositionArticle.objects.create(
            etat=PropositionArticle.Etat.VERIFICATION, ship=navire, service=service, categorie=self.categorie,
            designation=designation, role_redacteur="CHEF_SECTION", created_by=self.redacteur,
        )

    def _fiche_flotte(self, navire, service, titre):
        fiche = InstallationMaintenance.objects.create(
            niveau="FLOTTE", categorie=self.categorie, periodicity="1 an", title=titre)
        return ChecklistTemplate.objects.create(
            name=titre, fiche=fiche, etat=ChecklistTemplate.Etat.VERIFICATION, ship_origine=navire,
            service_origine=service, redacteur=self.redacteur, role_redacteur="CHEF_SECTION",
        )

    def test_fiches_et_propositions_d_un_autre_navire_ecartees(self):
        self._fiche_flotte(self.navire, self.service, "Fiche ALP")
        self._fiche_flotte(self.autre, self.service_b, "ZZFicheBRAZZ")
        self._proposition(self.navire, self.service, "Article ALP")
        self._proposition(self.autre, self.service_b, "ZZArticleBRAZZ")
        reponse = self._page(self.comanav)
        bloc = self._bloc(reponse, "Gestion technique des matériels")
        # Un seul de chaque : celui du bâtiment ; l'autre est pourtant actionnable par ce marin.
        self.assertEqual([i["valeur"] for i in bloc["indicateurs"]], [1, 1])
        self.assertContains(reponse, "Fiche ALP")
        self.assertContains(reponse, "Article ALP")
        self.assertNotContains(reponse, "ZZFicheBRAZZ")
        self.assertNotContains(reponse, "ZZArticleBRAZZ")

    def test_qualifications_d_un_autre_navire_ecartees(self):
        aujourdhui = timezone.localdate()
        cours = TrainingCourse.objects.create(title="ZZCoursZZ", validity_days=365)
        for nom, navire in (("marin_alp", self.navire), ("marin_bra", self.autre)):
            marin = self._marin(nom, "EQUIPIER", navire)
            TrainingRecord.objects.create(
                user=marin, course=cours, completed_at=aujourdhui, expires_at=aujourdhui + timedelta(days=5))
        admin = self._marin("admin_flotte", "MASTER_ADMIN", None)
        self.client.force_login(admin)
        session = self.client.session
        session[CLE_SESSION] = self.navire.pk
        session.save()
        reponse = self.client.get("/dashboard/comanav/")
        self.assertEqual(reponse.context["navire"], self.navire)
        self.assertEqual(self._valeur(reponse, "Chaîne sécurité", "Qualifications"), 1)
        self.assertContains(reponse, "marin_alp")
        self.assertNotContains(reponse, "marin_bra")

    def test_derives_d_un_autre_navire_ecartees(self):
        # Les deux installations ont de vrais relevés qui produisent une dérive.
        propre = self._installation(designation="Groupe ALP", isolation_seuil_ohms=500_000)
        etrangere = self._installation(self.autre, designation="ZZGroupeBRAZZ", isolation_seuil_ohms=500_000)
        for installation in (propre, etrangere):
            for i in range(5):
                InstallationIsolationReading.objects.create(
                    installation=installation, date=date(2026, 1, 1) + timedelta(days=i), ohms=1_000_000 - i * 100_000)
        self.assertIsNotNone(next(j for g, _, j in derives_de(etrangere) if g == "ISOLEMENT"))
        reponse = self._page(self.comanav)
        bloc = self._bloc(reponse, "Dérives")
        self.assertEqual(bloc["indicateurs"][0]["valeur"], 1)
        self.assertEqual([ligne["titre"] for ligne in bloc["lignes"]], ["Groupe ALP"])
        self.assertNotContains(reponse, "ZZGroupeBRAZZ")
