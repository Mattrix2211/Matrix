"""L06 : migration des comptes administrateurs (AC-01) — conversion, traçabilité, absence d'élévation, retour arrière."""
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

AVANT = ("accounts", "0023_protection_suppression_unites")
APRES = ("accounts", "0030_corrections_securite_l06")
AVANT_0030 = ("accounts", "0029_securite_reinitialisation_administrateur_general")


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
        self.assertEqual(apres.get_model("accounts", "UserProfile").objects.get(user_id=comptes["admin_coma"]).fonction_coma, "")

        demandes = apres.get_model("accounts", "FonctionAConfirmer").objects.all()
        self.assertEqual([(d.user_id, d.fonction_ancienne, d.statut) for d in demandes], [(comptes["admin_coma"], "COMANAV", "EN_ATTENTE")])

        retour = self._migrer(AVANT)
        self.assertEqual(self._etat(retour, comptes)["admin_seul"][0], "ADMIN_NAVIRE")
        self.assertEqual(self._etat(retour, comptes)["admin_coma"][0], "ADMIN_NAVIRE")
        self.assertEqual(self._etat(retour, comptes)["commandant"][0], "COMMANDANT")
        self.assertEqual(retour.get_model("accounts", "UserProfile").objects.get(user_id=comptes["admin_coma"]).fonction_coma, "COMANAV")
        journal_retour = retour.get_model("accounts", "AuditLog").objects
        self.assertFalse(journal_retour.filter(action="l06_migration_role").exists())
        self.assertEqual(journal_retour.filter(action="l06_migration_role_annulee").count(), 2)  # la trace n'est jamais supprimée

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


class MigrationsAdministrateurGeneralEtProvisoiresTests(TransactionTestCase):
    """0028 : MASTER_ADMIN devient un indicateur sans fonction métier ; 0029 : plus de mot de passe provisoire valable."""

    def _migrer(self, cible):
        executeur = MigrationExecutor(connection)
        executeur.migrate([cible])
        return executeur.loader.project_state([cible]).apps

    def tearDown(self):
        self._migrer(APRES)

    def test_administrateur_general_converti_sans_attribution_puis_retour_arriere(self):
        base = self._migrer(("accounts", "0027_echec_connexion"))
        User, Profil = base.get_model("auth", "User"), base.get_model("accounts", "UserProfile")
        general, commandant, superuser = (User.objects.create(username=n) for n in ("general", "cdt", "su"))
        User.objects.filter(pk=superuser.pk).update(is_superuser=True)
        for utilisateur, role in ((general, "MASTER_ADMIN"), (commandant, "COMMANDANT"), (superuser, "EQUIPIER")):
            Profil.objects.update_or_create(user=utilisateur, defaults={"role": role})
        apres = self._migrer(("accounts", "0028_administrateur_general"))
        Profil = apres.get_model("accounts", "UserProfile")
        etat = {p.user.username: (p.role, p.administrateur_general) for p in Profil.objects.select_related("user")}
        self.assertEqual(etat, {"general": ("EQUIPIER", True), "cdt": ("COMMANDANT", False), "su": ("EQUIPIER", False)})
        self.assertEqual(apres.get_model("accounts", "AuditLog").objects.filter(action="l06_migration_administrateur_general").count(), 1)
        retour = self._migrer(("accounts", "0027_echec_connexion"))
        self.assertEqual(retour.get_model("accounts", "UserProfile").objects.get(user__username="general").role, "MASTER_ADMIN")
        journal_retour = retour.get_model("accounts", "AuditLog").objects
        self.assertFalse(journal_retour.filter(action="l06_migration_administrateur_general").exists())
        self.assertEqual(journal_retour.filter(action="l06_migration_administrateur_general_annulee").count(), 1)

    def test_un_mot_de_passe_provisoire_existant_est_invalide(self):
        base = self._migrer(("accounts", "0028_administrateur_general"))
        User, Profil = base.get_model("auth", "User"), base.get_model("accounts", "UserProfile")
        marin = User.objects.create(username="provisoire", password="pbkdf2_sha256$1$x$y")
        normal = User.objects.create(username="normal", password="pbkdf2_sha256$1$x$y")
        Profil.objects.update_or_create(user=marin, defaults={"mot_de_passe_provisoire": True})
        Profil.objects.update_or_create(user=normal, defaults={"mot_de_passe_provisoire": False})
        apres = self._migrer(("accounts", "0029_securite_reinitialisation_administrateur_general"))
        User = apres.get_model("auth", "User")
        self.assertTrue(User.objects.get(username="provisoire").password.startswith("!"))
        self.assertEqual(User.objects.get(username="normal").password, "pbkdf2_sha256$1$x$y")


class Migration0030Tests(TransactionTestCase):
    """0030 rattrape une base qui a déjà appliqué la version initiale de 0029 (schéma et données)."""

    def _migrer(self, cible):
        executeur = MigrationExecutor(connection)
        executeur.migrate([cible])
        return executeur.loader.project_state([cible]).apps

    def tearDown(self):
        self._migrer(APRES)

    def test_mise_a_niveau_d_une_base_en_0029_sans_perte_ni_divergence(self):
        base = self._migrer(AVANT_0030)
        User = base.get_model("auth", "User")
        Demande, Operateur, Compteur = (base.get_model("accounts", n) for n in ("DemandeReinitialisation", "OperateurRecuperation", "CompteurConnexion"))
        from django.utils import timezone
        marin, autre = User.objects.create(username="marin"), User.objects.create(username="autre")
        maintenant = timezone.now()
        Demande.objects.create(user=marin, statut="BLOQUEE", code_initiateur="x", expire_le=maintenant, essais=7)
        Demande.objects.create(user=autre, statut="ACTIVE", code_initiateur="y", expire_le=maintenant, essais=2)
        Operateur.objects.create(nom="Alice", identifiant_systeme="sys-a", phrase="x")
        Operateur.objects.create(nom="Alice", identifiant_systeme="sys-b", phrase="x")
        Compteur.objects.create(identifiant="marin", source="10.0.0.1", essais=3, derniere_activite=maintenant)
        for i in range(5):
            Compteur.objects.create(identifiant=f"invente-{i}", source="10.0.0.1", essais=1, derniere_activite=maintenant)

        apres = self._migrer(APRES)
        Demande, Operateur, Compteur = (apres.get_model("accounts", n) for n in ("DemandeReinitialisation", "OperateurRecuperation", "CompteurConnexion"))
        self.assertEqual(Demande.objects.get(user__username="marin").statut, "ANNULEE")
        self.assertEqual(Demande.objects.get(user__username="autre").statut, "ACTIVE")
        self.assertFalse(any(f.name == "essais" for f in Demande._meta.get_fields()))
        self.assertEqual(sorted(Operateur.objects.values_list("nom", flat=True)), ["Alice", "Alice (2)"])
        self.assertEqual(sorted(Operateur.objects.values_list("identifiant_systeme", flat=True)), ["sys-a", "sys-b"])
        self.assertEqual(list(Compteur.objects.values_list("identifiant", flat=True)), ["marin"])  # les identifiants inventés disparaissent
        self.assertTrue(Compteur._meta.get_field("derniere_activite").db_index)
        self.assertTrue(Operateur._meta.get_field("nom").unique)

    def test_base_neuve_et_retour_arriere_de_0030(self):
        apres = self._migrer(APRES)
        self.assertEqual(apres.get_model("accounts", "OperateurRecuperation").objects.count(), 0)
        retour = self._migrer(AVANT_0030)
        self.assertTrue(any(f.name == "essais" for f in retour.get_model("accounts", "DemandeReinitialisation")._meta.get_fields()))
