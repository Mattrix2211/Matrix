"""Tests de la génération intelligente de proposition de répartition (Phase 2,
tâche Notion « Génération intelligente des listes de service : proposition
automatique de répartition »)."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from accounts.models import ServiceFunctionChoice, TypeAbsence, UserProfile
from absences.models import Absence
from org.models import Sector, Service, Ship
from quarts.generation import proposer_repartition
from quarts.models import CreneauQuart, CreneauServiceGarde, Quart, ServiceGarde
from training.models import TrainingCourse, TrainingRecord


def _marin(nom, secteur):
    user = User.objects.create_user(username=nom, password="pass")
    UserProfile.objects.update_or_create(user=user, defaults={"role": "EQUIPIER", "sector": secteur})
    return user


class GenerationQuartTests(TestCase):
    """Génération sur une liste de quarts (pas d'habilitation exigée, cf.
    docstring de quarts/generation.py : Quart ne porte pas ce champ)."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Génération", code="GEN")
        self.sector = Sector.objects.create(service=Service.objects.create(ship=self.ship, name="Pont"), name="Manœuvre")
        self.a = _marin("marin_a", self.sector)
        self.b = _marin("marin_b", self.sector)
        self.c = _marin("marin_c", self.sector)

        aujourdhui = timezone.localdate()
        self.quart = Quart.objects.create(
            sector=self.sector, date_debut=aujourdhui, date_fin=aujourdhui + timedelta(days=6),
        )

    def _creneau_libre(self, quand, poste="Passerelle", duree_heures=4):
        return CreneauQuart.objects.create(
            quart=self.quart, poste=poste, debut=quand, fin=quand + timedelta(hours=duree_heures),
        )

    def test_aucun_creneau_non_affecte_renvoie_une_liste_vide(self):
        self.assertEqual(proposer_repartition(self.quart), [])

    def test_absence_exclut_le_marin(self):
        creneau = self._creneau_libre(timezone.now() + timedelta(days=1))
        type_conge = TypeAbsence.objects.create(name="Permission")
        jour = timezone.localtime(creneau.debut).date()
        Absence.objects.create(marin=self.a, type_absence=type_conge, date_debut=jour, date_fin=jour)

        proposition = proposer_repartition(self.quart)
        self.assertEqual(len(proposition), 1)
        eligibles = {m.pk for m in proposition[0]["eligibles"]}
        self.assertNotIn(self.a.pk, eligibles)
        self.assertIn(self.b.pk, eligibles)
        self.assertNotEqual(proposition[0]["propose"], self.a)

    def test_deja_affecte_sur_une_liste_publiee_exclut_le_marin(self):
        autre_quart = Quart.objects.create(
            sector=self.sector, date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=6),
            statut=Quart.STATUT_PUBLIEE,
        )
        debut = timezone.now() + timedelta(days=1)
        CreneauQuart.objects.create(quart=autre_quart, poste="Barre", debut=debut, fin=debut + timedelta(hours=4), marin=self.a)
        creneau = self._creneau_libre(debut, poste="Passerelle")

        proposition = proposer_repartition(self.quart)
        eligibles = {m.pk for m in proposition[0]["eligibles"]}
        self.assertNotIn(self.a.pk, eligibles)

    def test_deja_affecte_sur_la_meme_liste_exclut_le_marin(self):
        debut = timezone.now() + timedelta(days=1)
        CreneauQuart.objects.create(quart=self.quart, poste="Barre", debut=debut, fin=debut + timedelta(hours=4), marin=self.a)
        creneau_libre = self._creneau_libre(debut, poste="Passerelle")

        proposition = proposer_repartition(self.quart)
        item = next(i for i in proposition if i["creneau"].pk == creneau_libre.pk)
        eligibles = {m.pk for m in item["eligibles"]}
        self.assertNotIn(self.a.pk, eligibles)

    def test_aucun_marin_eligible_est_signale_clairement(self):
        creneau = self._creneau_libre(timezone.now() + timedelta(days=1))
        type_conge = TypeAbsence.objects.create(name="Mission")
        jour = timezone.localtime(creneau.debut).date()
        for marin in (self.a, self.b, self.c):
            Absence.objects.create(marin=marin, type_absence=type_conge, date_debut=jour, date_fin=jour)

        proposition = proposer_repartition(self.quart)
        self.assertTrue(proposition[0]["aucun_eligible"])
        self.assertIsNone(proposition[0]["propose"])
        self.assertEqual(proposition[0]["eligibles"], [])

    def test_equilibrage_intra_calcul_alterne_entre_marins_a_charge_egale(self):
        # Deux créneaux disjoints dans le temps, sur des postes différents
        # (pour ne pas activer la contrainte de non-répétition immédiate en
        # plus de l'équilibrage) : le second créneau doit être proposé à
        # l'autre marin, pas systématiquement au même.
        c1 = self._creneau_libre(timezone.now() + timedelta(days=1), poste="Passerelle")
        c2 = self._creneau_libre(timezone.now() + timedelta(days=2), poste="Barre")
        # Aucun marin_c éligible n'est nécessaire ici ; on l'exclut par simplicité.
        type_conge = TypeAbsence.objects.create(name="Congé")
        Absence.objects.create(
            marin=self.c, type_absence=type_conge,
            date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=10),
        )

        proposition = proposer_repartition(self.quart)
        propose_1 = next(i["propose"] for i in proposition if i["creneau"].pk == c1.pk)
        propose_2 = next(i["propose"] for i in proposition if i["creneau"].pk == c2.pk)
        self.assertIsNotNone(propose_1)
        self.assertIsNotNone(propose_2)
        self.assertNotEqual(propose_1.pk, propose_2.pk)

    def test_non_repetition_immediate_evite_le_meme_marin_consecutif(self):
        # marin_b est déjà affecté (manuellement) sur un créneau antérieur du
        # même poste ; marin_c est également éligible sur le créneau suivant,
        # à charge égale : la génération doit préférer marin_c plutôt que de
        # reproduire immédiatement marin_b sur le même poste.
        debut_predecesseur = timezone.now() + timedelta(days=1, hours=0)
        CreneauQuart.objects.create(
            quart=self.quart, poste="Passerelle", debut=debut_predecesseur,
            fin=debut_predecesseur + timedelta(hours=1), marin=self.b,
        )
        debut_suivant = debut_predecesseur + timedelta(hours=2)
        creneau_suivant = self._creneau_libre(debut_suivant, poste="Passerelle", duree_heures=1)
        # marin_a exclu pour isoler uniquement marin_b (prédécesseur) contre marin_c.
        type_conge = TypeAbsence.objects.create(name="Stage")
        Absence.objects.create(
            marin=self.a, type_absence=type_conge,
            date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=10),
        )

        proposition = proposer_repartition(self.quart)
        item = next(i for i in proposition if i["creneau"].pk == creneau_suivant.pk)
        self.assertEqual(item["propose"], self.c)

    def test_non_repetition_immediate_autorise_si_seul_eligible(self):
        debut_predecesseur = timezone.now() + timedelta(days=1)
        CreneauQuart.objects.create(
            quart=self.quart, poste="Passerelle", debut=debut_predecesseur,
            fin=debut_predecesseur + timedelta(hours=1), marin=self.b,
        )
        debut_suivant = debut_predecesseur + timedelta(hours=2)
        creneau_suivant = self._creneau_libre(debut_suivant, poste="Passerelle", duree_heures=1)
        type_conge = TypeAbsence.objects.create(name="Stage")
        for marin in (self.a, self.c):
            Absence.objects.create(
                marin=marin, type_absence=type_conge,
                date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=10),
            )

        proposition = proposer_repartition(self.quart)
        item = next(i for i in proposition if i["creneau"].pk == creneau_suivant.pk)
        # Seul marin_b reste éligible : jamais de créneau laissé vide s'il
        # existe un candidat possible, même en répétition immédiate.
        self.assertEqual(item["propose"], self.b)


class GenerationServiceGardeTests(TestCase):
    """Génération sur une liste de services de garde : vérifie l'exclusion par
    habilitation manquante et la réutilisation du compteur d'équité existant."""

    def setUp(self):
        self.ship = Ship.objects.create(name="Navire Génération Garde", code="GNG")
        self.sector = Sector.objects.create(service=Service.objects.create(ship=self.ship, name="Machine"), name="Propulsion")
        self.a = _marin("marin_garde_a", self.sector)
        self.b = _marin("marin_garde_b", self.sector)
        self.formation = TrainingCourse.objects.create(title="Habilitation électrique")

        aujourdhui = timezone.localdate()
        self.garde = ServiceGarde.objects.create(
            sector=self.sector, fonction=ServiceFunctionChoice.objects.create(name="Permanence"),
            date_debut=aujourdhui, date_fin=aujourdhui + timedelta(days=30),
        )
        self.garde.formations_requises.add(self.formation)

    def test_habilitation_manquante_exclut_le_marin(self):
        debut = timezone.now() + timedelta(days=1)
        TrainingRecord.objects.create(
            user=self.a, course=self.formation,
            completed_at=timezone.localdate() - timedelta(days=30),
            expires_at=timezone.localdate() + timedelta(days=365),
        )
        creneau = CreneauServiceGarde.objects.create(
            service_garde=self.garde, poste="Officier de garde", debut=debut, fin=debut + timedelta(hours=24),
        )

        proposition = proposer_repartition(self.garde)
        eligibles = {m.pk for m in proposition[0]["eligibles"]}
        self.assertIn(self.a.pk, eligibles)
        self.assertNotIn(self.b.pk, eligibles)
        self.assertEqual(proposition[0]["propose"], self.a)

    def test_equilibrage_reutilise_le_compteur_dequite_existant(self):
        # marin_a a déjà 1 garde publiée cette année, marin_b n'en a aucune :
        # la génération doit privilégier marin_b (charge la plus faible).
        for marin in (self.a, self.b):
            TrainingRecord.objects.create(
                user=marin, course=self.formation,
                completed_at=timezone.localdate() - timedelta(days=30),
                expires_at=timezone.localdate() + timedelta(days=365),
            )
        garde_publiee = ServiceGarde.objects.create(
            sector=self.sector, date_debut=timezone.localdate(), date_fin=timezone.localdate() + timedelta(days=30),
            statut=ServiceGarde.STATUT_PUBLIEE,
        )
        passe = timezone.now() - timedelta(days=5)
        CreneauServiceGarde.objects.create(
            service_garde=garde_publiee, poste="Officier de garde", debut=passe, fin=passe + timedelta(hours=24), marin=self.a,
        )

        debut = timezone.now() + timedelta(days=2)
        CreneauServiceGarde.objects.create(
            service_garde=self.garde, poste="Officier de garde", debut=debut, fin=debut + timedelta(hours=24),
        )

        proposition = proposer_repartition(self.garde)
        self.assertEqual(proposition[0]["propose"], self.b)
