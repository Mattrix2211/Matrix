"""Règle du 30/09/2026 (double équipage) : un titulaire de poste COMA ou de
commandant en second ne change ni d'équipage ni de bâtiment sans libérer son
poste, et un service ne change pas d'équipage tant que des listes de quarts ou
de gardes lui sont rattachées."""
from datetime import date

from django.core.exceptions import ValidationError

from accounts.models import UserProfile
from org.models import CommandantAdjoint, CommandantEnSecond, Sector, Service, Ship
from org.tests.test_coherence_equipage import BaseDoubleEquipage, creer_marin
from quarts.models import Quart, ServiceGarde


class DeplacementTitulaireTests(BaseDoubleEquipage):
    def setUp(self):
        super().setUp()
        self.titulaire = creer_marin("coma_bleu", "ETAT_MAJOR", self.ship, self.bleu)
        CommandantAdjoint.objects.create(ship=self.ship, equipage=self.bleu, sigle="COMOPS", titulaire=self.titulaire)

    def test_profil_refuse_l_autre_equipage_et_nomme_le_poste(self):
        profil = self.titulaire.profile
        profil.equipage = self.rouge
        with self.assertRaises(ValidationError) as ctx:
            profil.save()
        self.assertIn("COMOPS de l'équipage Bleu", " ".join(ctx.exception.messages))

    def test_profil_refuse_le_changement_de_navire(self):
        autre = Ship.objects.create(name="Autre unité", code="AUT")
        profil = self.titulaire.profile
        profil.ship = autre
        with self.assertRaises(ValidationError):
            profil.save(update_fields=["ship"])

    def test_clean_du_profil_refuse_pour_l_administration(self):
        profil = self.titulaire.profile
        profil.equipage = self.rouge
        with self.assertRaises(ValidationError):
            profil.full_clean(exclude=["user"])

    def test_poste_libere_le_marin_peut_changer(self):
        CommandantAdjoint.objects.update(titulaire=None)
        profil = self.titulaire.profile
        profil.equipage = self.rouge
        profil.save()
        profil.refresh_from_db()
        self.assertEqual(profil.equipage, self.rouge)

    def test_enregistrement_sans_changement_d_equipage_passe(self):
        profil = self.titulaire.profile
        profil.grade = "Capitaine de frégate"
        profil.save()

    def test_commandant_en_second_meme_regle(self):
        second = creer_marin("second_bleu", "ETAT_MAJOR", self.ship, self.bleu)
        CommandantEnSecond.objects.create(ship=self.ship, equipage=self.bleu, titulaire=second)
        profil = second.profile
        profil.equipage = self.rouge
        with self.assertRaises(ValidationError) as ctx:
            profil.save()
        self.assertIn("Commandant en second", " ".join(ctx.exception.messages))

    def test_modele_en_second_refuse_un_titulaire_de_l_autre_equipage(self):
        etranger = creer_marin("second_rouge", "ETAT_MAJOR", self.ship, self.rouge)
        with self.assertRaises(ValidationError):
            CommandantEnSecond.objects.create(ship=self.ship, equipage=self.bleu, titulaire=etranger)

    def test_modele_en_second_refuse_un_titulaire_sans_equipage(self):
        sans = creer_marin("second_sans", "ETAT_MAJOR", self.ship, None)
        with self.assertRaises(ValidationError):
            CommandantEnSecond.objects.create(ship=self.ship, equipage=self.bleu, titulaire=sans)

    def test_navire_a_equipage_unique_inchange(self):
        unique = Ship.objects.create(name="Unique", code="UNI")
        marin = creer_marin("coma_unique", "ETAT_MAJOR", unique)
        CommandantAdjoint.objects.create(ship=unique, sigle="COMAEQ", titulaire=marin)
        profil = UserProfile.objects.get(user=marin)
        profil.ship = self.ship
        profil.save()


class ListesDuServiceTests(BaseDoubleEquipage):
    def setUp(self):
        super().setUp()
        self.service = Service.objects.create(ship=self.ship, equipage=self.bleu, name="Énergie")
        self.secteur = Sector.objects.create(service=self.service, equipage=self.bleu, name="Propulsion")

    def _liste(self, modele, **perimetre):
        return modele.objects.create(date_debut=date(2026, 10, 1), date_fin=date(2026, 10, 7), **perimetre)

    def test_changement_bloque_avec_les_listes_nommees(self):
        self._liste(Quart, service=self.service, nom="Semaine 40")
        self._liste(ServiceGarde, sector=self.secteur)
        self.service.equipage = self.rouge
        with self.assertRaises(ValidationError) as ctx:
            self.service.save()
        texte = " ".join(ctx.exception.message_dict["equipage"])
        self.assertIn("liste de quarts « Semaine 40 »", texte)
        self.assertIn("le secteur « Propulsion »", texte)
        self.service.refresh_from_db()
        self.assertEqual(self.service.equipage, self.bleu)

    def test_sans_liste_le_changement_passe(self):
        self.service.equipage = self.rouge
        self.service.save()
        self.secteur.refresh_from_db()
        self.assertEqual(self.secteur.equipage, self.rouge)
