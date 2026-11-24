"""L06 : migration des comptes administrateurs (AC-01) — conversion, traçabilité, absence d'élévation, retour arrière."""
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

AVANT = ("accounts", "0023_protection_suppression_unites")
APRES = ("accounts", "0024_administrateur_technique")


class MigrationAdministrateursTests(TransactionTestCase):
    def _migrer(self, cible):
        executeur = MigrationExecutor(connection)
        executeur.migrate([cible])
        return executeur.loader.project_state([cible]).apps

    def tearDown(self):
        self._migrer(APRES)

    def _comptes_avant(self, apps):
        User, Profil = apps.get_model("auth", "User"), apps.get_model("accounts", "UserProfile")
        comptes = {}
        for nom, role, fonction in (
            ("admin_seul", "ADMIN_NAVIRE", ""), ("admin_coma", "ADMIN_NAVIRE", "COMANAV"),
            ("commandant", "COMMANDANT", ""), ("marin", "EQUIPIER", ""), ("chef_section", "CHEF_SECTION", ""),
        ):
            utilisateur = User.objects.create(username=nom)
            Profil.objects.update_or_create(user=utilisateur, defaults={"role": role, "fonction_coma": fonction})
            comptes[nom] = utilisateur.pk
        return comptes

    def _etat(self, apps, comptes):
        Profil = apps.get_model("accounts", "UserProfile")
        resultat = {}
        for nom, pk in comptes.items():
            profil = Profil.objects.get(user_id=pk)
            resultat[nom] = (profil.role, getattr(profil, "administrateur_technique", None))
        return resultat

    def test_conversion_sans_deduction_ni_elevation_puis_retour_arriere(self):
        apres_base = self._migrer(AVANT)
        comptes = self._comptes_avant(apres_base)
        avant = self._etat(apres_base, comptes)
        self.assertEqual(avant["admin_seul"][0], "ADMIN_NAVIRE")

        apres = self._migrer(APRES)
        etat = self._etat(apres, comptes)
        self.assertEqual(etat["admin_seul"], ("EQUIPIER", True))  # fonction inconnue : droits techniques seuls
        self.assertEqual(etat["admin_coma"], ("EQUIPIER", True))  # aucune fonction déduite : la fiche est seulement journalisée
        for nom in ("commandant", "marin", "chef_section"):  # aucun autre compte n'est touché ni promu
            self.assertEqual(etat[nom], (avant[nom][0], False), nom)
        journal = apres.get_model("accounts", "AuditLog").objects.filter(action="l06_migration_role")
        self.assertEqual(journal.count(), 2)
        self.assertTrue(all("ADMIN_NAVIRE" in ligne.details for ligne in journal))
        self.assertTrue(journal.filter(details__contains="fonction_a_confirmer=COMANAV").exists())

        retour = self._migrer(AVANT)
        self.assertEqual(self._etat(retour, comptes)["admin_seul"][0], "ADMIN_NAVIRE")
        self.assertEqual(self._etat(retour, comptes)["admin_coma"][0], "ADMIN_NAVIRE")
        self.assertEqual(self._etat(retour, comptes)["commandant"][0], "COMMANDANT")
        self.assertFalse(retour.get_model("accounts", "AuditLog").objects.filter(action="l06_migration_role").exists())

    def test_retour_arriere_respecte_un_role_modifie(self):
        base = self._migrer(AVANT)
        User, Profil = base.get_model("auth", "User"), base.get_model("accounts", "UserProfile")
        navire = base.get_model("org", "Ship").objects.create(name="Fictif", code="FIC")
        for nom, role, fonction in (("titulaire", "ETAT_MAJOR", "COMANAV"), ("admin_doublon", "ADMIN_NAVIRE", "COMANAV"),
                                    ("admin_modifie", "ADMIN_NAVIRE", "")):  # un titulaire existant n'est jamais dédoublé
            utilisateur = User.objects.create(username=nom)
            Profil.objects.update_or_create(user=utilisateur, defaults={"role": role, "fonction_coma": fonction, "ship": navire})
        etat = self._etat(self._migrer(APRES), {n: User.objects.get(username=n).pk for n in ("titulaire", "admin_doublon", "admin_modifie")})
        self.assertEqual(etat["admin_doublon"], ("EQUIPIER", True))  # fonction déjà tenue : à confirmer, pas de doublon
        Profil.objects.filter(user__username="admin_modifie").update(role="CHEF_SECTION")
        retour = self._migrer(AVANT)
        profils = {p.user.username: p.role for p in retour.get_model("accounts", "UserProfile").objects.select_related("user")}
        self.assertEqual(profils["admin_doublon"], "ADMIN_NAVIRE")
        self.assertEqual(profils["admin_modifie"], "CHEF_SECTION")  # rôle changé depuis : jamais écrasé
