"""Archivage effectif des unités (AUD-028) : règle unique, refus d'archiver une unité occupée, aucun nouveau rattachement à une unité
archivée, historique et périmètres inchangés."""
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APIRequestFactory

from accounts.models import AuditLog, SpecialityChoice, UserProfile
from annonces.services import cibles_autorisees
from assets.equipement_web import creer_exemplaires
from assets.models import ArticleCatalogue, Asset, AssetType, CategorieCatalogue, Installation
from assets.serializers import AssetSerializer
from logistics.models import StockPiece
from matrix.core.scopes import resoudre_affectation_dans_perimetre, scope_filters_for_user
from org import archivage
from org.models import Section, Sector, Service, Ship
from quarts.models import ChefDeListe, Quart, ServiceGarde
from training.models import TrainingCourse, TrainingRequirement


def creer_compte(nom, role, **profil):
    utilisateur = User.objects.create_user(username=nom, password="x")
    UserProfile.objects.update_or_create(user=utilisateur, defaults={"role": role, **profil})
    return User.objects.get(pk=utilisateur.pk)


class BaseArchivage(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire A", code="A")
        self.service = Service.objects.create(ship=self.navire, name="Propulsion")
        self.secteur = Sector.objects.create(service=self.service, name="Moteurs")
        self.section = Section.objects.create(sector=self.secteur, name="Bâbord")
        self.autre_section = Section.objects.create(sector=self.secteur, name="Tribord")
        self.admin = creer_compte("admin_flotte", "MASTER_ADMIN")
        self.admin.is_superuser = True
        self.admin.save()
        self.admin_navire = creer_compte("admin_a", "ADMIN_NAVIRE", ship=self.navire)
        self.marin = creer_compte("marin_a", "EQUIPIER", ship=self.navire, service=self.service, sector=self.secteur, section=self.section)


class RegleCentraleTests(BaseArchivage):
    def test_une_unite_est_active_si_elle_et_ses_ancetres_ne_sont_pas_archives(self):
        self.assertTrue(archivage.est_active(self.section))
        Service.objects.filter(pk=self.service.pk).update(archived=True)
        self.service.refresh_from_db()
        self.section.refresh_from_db()
        self.secteur.refresh_from_db()
        self.assertFalse(archivage.est_active(self.service))
        self.assertFalse(archivage.est_active(self.secteur))
        self.assertFalse(archivage.est_active(self.section))

    def test_archiver_une_unite_occupee_par_des_marins_actifs_est_refuse(self):
        with self.assertRaises(ValidationError) as ctx:
            archivage.archiver(self.section, self.admin)
        self.assertIn("1 marin(s) actif(s)", str(ctx.exception))
        self.section.refresh_from_db()
        self.assertFalse(self.section.archived)
        self.assertFalse(AuditLog.objects.filter(action="archive_section").exists())

    def test_une_unite_occupee_plus_haut_dans_la_hierarchie_est_aussi_refusee(self):
        for unite in (self.secteur, self.service, self.navire):
            with self.assertRaises(ValidationError, msg=unite):
                archivage.archiver(unite, self.admin)

    def test_un_marin_desactive_ne_bloque_pas_l_archivage(self):
        User.objects.filter(pk=self.marin.pk).update(is_active=False)
        self.assertTrue(archivage.archiver(self.section, self.admin))

    def test_du_materiel_dans_l_unite_bloque_l_archivage(self):
        Installation.objects.create(designation="Diesel 1", ship=self.navire, service=self.service, sector=self.secteur)
        self.autre_section.refresh_from_db()
        with self.assertRaises(ValidationError) as ctx:
            archivage.archiver(self.secteur, self.admin)
        self.assertIn("installation(s)", str(ctx.exception))

    def test_archiver_et_reactiver_sont_idempotents_et_traces(self):
        self.assertTrue(archivage.archiver(self.autre_section, self.admin))
        self.assertFalse(archivage.archiver(self.autre_section, self.admin))
        self.assertEqual(AuditLog.objects.filter(action="archive_section").count(), 1)
        self.assertIn("False -> True", AuditLog.objects.get(action="archive_section").details)
        self.assertTrue(archivage.reactiver(self.autre_section, self.admin))
        self.assertFalse(archivage.reactiver(self.autre_section, self.admin))
        self.assertEqual(AuditLog.objects.filter(action="reactive_section").count(), 1)

    def test_reactiver_sous_un_parent_archive_est_refuse(self):
        archivage.archiver(self.autre_section, self.admin)
        Sector.objects.filter(pk=self.secteur.pk).update(archived=True)
        self.autre_section.refresh_from_db()
        self.autre_section.sector.refresh_from_db()
        with self.assertRaises(ValidationError) as ctx:
            archivage.reactiver(self.autre_section, self.admin)
        self.assertIn("parente est archivée", str(ctx.exception))

    def test_exclure_archives_ecarte_l_unite_et_ses_descendants(self):
        Service.objects.filter(pk=self.service.pk).update(archived=True)
        self.assertEqual(list(archivage.exclure_archives(Service.objects.all())), [])
        self.assertEqual(list(archivage.exclure_archives(Sector.objects.all())), [])
        self.assertEqual(list(archivage.exclure_archives(Section.objects.all())), [])
        self.assertEqual(list(archivage.exclure_archives(Ship.objects.all())), [self.navire])

    def test_exclure_archives_peut_garder_une_unite_archivee_qui_porte_encore_des_marins(self):
        Section.objects.filter(pk=self.section.pk).update(archived=True)
        Section.objects.filter(pk=self.autre_section.pk).update(archived=True)
        sections = archivage.exclure_archives(Section.objects.all(), garder_occupees=True)
        self.assertEqual(list(sections), [self.section])  # archivée mais occupée (données antérieures) ; l'autre est écartée

    def test_le_modele_refuse_d_archiver_une_unite_occupee_comme_le_ferait_l_administration(self):
        self.section.archived = True
        with self.assertRaises(ValidationError):
            self.section.full_clean()
        self.autre_section.archived = True
        self.autre_section.full_clean()  # inoccupée : permis

    def test_creer_une_unite_sous_une_unite_archivee_est_refuse(self):
        archivage.archiver(self.autre_section, self.admin)
        Section.objects.filter(pk=self.section.pk).update(archived=True)
        Sector.objects.filter(pk=self.secteur.pk).update(archived=True)
        self.secteur.refresh_from_db()
        with self.assertRaises(ValidationError):
            Section(sector=self.secteur, name="Nouvelle").full_clean()


class HistoriqueEtPerimetreInchangesTests(BaseArchivage):
    def test_une_unite_archivee_avec_des_marins_anterieurs_ne_modifie_ni_leur_rattachement_ni_leur_perimetre(self):
        avant = (scope_filters_for_user(self.marin), self.marin.profile.scope)
        Section.objects.filter(pk=self.section.pk).update(archived=True)  # donnée antérieure à la règle
        marin = User.objects.get(pk=self.marin.pk)
        self.assertEqual((scope_filters_for_user(marin), marin.profile.scope), avant)
        self.assertEqual(marin.profile.section_id, self.section.pk)

    def test_aucune_donnee_n_est_supprimee_par_l_archivage(self):
        archivage.archiver(self.autre_section, self.admin)
        self.assertTrue(Section.objects.filter(pk=self.autre_section.pk, archived=True).exists())
        self.assertEqual(Section.objects.count(), 2)

    def test_les_cibles_d_annonce_gardent_l_historique_mais_ne_proposent_plus_l_unite_archivee(self):
        archivage.archiver(self.autre_section, self.admin)
        cle = f"section:{self.autre_section.pk}"
        self.assertIn(cle, [c for c, _ in cibles_autorisees(self.admin_navire)])  # lecture / gestion de l'existant
        self.assertNotIn(cle, [c for c, _ in cibles_autorisees(self.admin_navire, actives=True)])  # nouvelle diffusion
        self.assertIn(f"section:{self.section.pk}", [c for c, _ in cibles_autorisees(self.admin_navire, actives=True)])


class AffectationDesMarinsTests(BaseArchivage):
    def setUp(self):
        super().setUp()
        archivage.archiver(self.autre_section, self.admin)
        self.autre_section.refresh_from_db()

    def test_une_unite_archivee_est_refusee_pour_un_nouveau_rattachement(self):
        for acteur in (self.admin, self.admin_navire):
            ok, *_ = resoudre_affectation_dans_perimetre(acteur, section_id=self.autre_section.pk)
            self.assertFalse(ok, acteur.username)
            ok, *_ = resoudre_affectation_dans_perimetre(acteur, section_id=self.section.pk)
            self.assertTrue(ok, acteur.username)

    def test_une_unite_archivee_deja_portee_par_le_marin_reste_acceptee_sans_changement(self):
        Section.objects.filter(pk=self.section.pk).update(archived=True)
        self.section.refresh_from_db()
        ok, *_ = resoudre_affectation_dans_perimetre(self.admin_navire, section_id=self.section.pk)
        self.assertFalse(ok)
        ok, _, _, _, section = resoudre_affectation_dans_perimetre(self.admin_navire, section_id=self.section.pk, deja=self.marin.profile)
        self.assertTrue(ok)
        self.assertEqual(section, self.section)
        ok, *_ = resoudre_affectation_dans_perimetre(self.admin_navire, section_id=self.autre_section.pk, deja=self.marin.profile)
        self.assertFalse(ok)  # tolérance limitée à la valeur inchangée

    def test_l_annuaire_ne_propose_plus_l_unite_archivee_mais_garde_celles_qui_portent_des_marins(self):
        Section.objects.filter(pk=self.section.pk).update(archived=True)  # occupée, antérieure à la règle
        client = self.client
        client.force_login(self.admin)
        contexte = client.get(reverse("user-directory")).context
        sections = list(contexte["sections"])
        self.assertIn(self.section, sections)
        self.assertNotIn(self.autre_section, sections)

    def test_l_api_des_comptes_refuse_un_nouveau_rattachement_a_une_unite_archivee(self):
        api = APIClient()
        api.force_authenticate(self.admin)
        reponse = api.patch(f"/api/accounts/profiles/{self.marin.profile.pk}/", {"section": self.autre_section.pk}, format="json")
        self.assertEqual(reponse.status_code, 400, getattr(reponse, "data", None))
        self.marin.profile.refresh_from_db()
        self.assertEqual(self.marin.profile.section_id, self.section.pk)


class ApiStructureTests(BaseArchivage):
    def setUp(self):
        super().setUp()
        self.api = APIClient()
        self.api.force_authenticate(self.admin)

    def test_archiver_une_unite_occupee_par_l_api_est_refuse_avec_un_message(self):
        reponse = self.api.patch(f"/api/org/sections/{self.section.pk}/", {"archived": True}, format="json")
        self.assertEqual(reponse.status_code, 400)
        self.assertIn("marin(s) actif(s)", str(reponse.data))
        self.section.refresh_from_db()
        self.assertFalse(self.section.archived)

    def test_archiver_et_reactiver_une_unite_libre_par_l_api(self):
        reponse = self.api.patch(f"/api/org/sections/{self.autre_section.pk}/", {"archived": True}, format="json")
        self.assertEqual(reponse.status_code, 200, reponse.data)
        self.autre_section.refresh_from_db()
        self.assertTrue(self.autre_section.archived)
        reponse = self.api.patch(f"/api/org/sections/{self.autre_section.pk}/", {"archived": False}, format="json")
        self.assertEqual(reponse.status_code, 200, reponse.data)

    def test_renommer_une_unite_archivee_reste_possible(self):
        archivage.archiver(self.autre_section, self.admin)
        reponse = self.api.patch(f"/api/org/sections/{self.autre_section.pk}/", {"name": "Tribord renommée"}, format="json")
        self.assertEqual(reponse.status_code, 200, reponse.data)

    def test_creer_ou_reactiver_sous_une_unite_archivee_est_refuse(self):
        archivage.archiver(self.autre_section, self.admin)
        Section.objects.filter(pk=self.section.pk).update(archived=True)
        Sector.objects.filter(pk=self.secteur.pk).update(archived=True)
        reponse = self.api.post("/api/org/sections/", {"sector": self.secteur.pk, "name": "Neuve"}, format="json")
        self.assertEqual(reponse.status_code, 400)
        self.assertFalse(Section.objects.filter(name="Neuve").exists())
        reponse = self.api.patch(f"/api/org/sections/{self.autre_section.pk}/", {"archived": False}, format="json")
        self.assertEqual(reponse.status_code, 400)

    def test_archiver_un_batiment_occupe_est_refuse(self):
        reponse = self.api.patch(f"/api/org/ships/{self.navire.pk}/", {"archived": True}, format="json")
        self.assertEqual(reponse.status_code, 400)
        self.navire.refresh_from_db()
        self.assertFalse(self.navire.archived)


class EcranReglagesTests(BaseArchivage):
    def _poster(self, utilisateur, **donnees):
        self.client.force_login(utilisateur)
        return self.client.post(reverse("settings"), {"next_tab": "hierarchie", "selected_ship": self.navire.pk, **donnees}, follow=True)

    def test_archiver_puis_reactiver_depuis_l_ecran(self):
        self._poster(self.admin, action="archive_unit", kind="section", pk=self.autre_section.pk)
        self.autre_section.refresh_from_db()
        self.assertTrue(self.autre_section.archived)
        self._poster(self.admin, action="reactivate_unit", kind="section", pk=self.autre_section.pk)
        self.autre_section.refresh_from_db()
        self.assertFalse(self.autre_section.archived)

    def test_archiver_une_unite_occupee_depuis_l_ecran_est_refuse_avec_un_message(self):
        reponse = self._poster(self.admin, action="archive_unit", kind="section", pk=self.section.pk)
        self.section.refresh_from_db()
        self.assertFalse(self.section.archived)
        self.assertIn("Impossible d&#x27;archiver", reponse.content.decode().replace("'", "&#x27;"))

    def test_l_ecran_distingue_visuellement_une_unite_archivee(self):
        archivage.archiver(self.autre_section, self.admin)
        reponse = self._poster(self.admin, action="noop")
        self.assertContains(reponse, "Archivé")
        self.assertContains(reponse, "Réactiver")

    def test_ajouter_sous_une_unite_archivee_depuis_l_ecran_est_refuse(self):
        Sector.objects.filter(pk=self.secteur.pk).update(archived=True)
        self._poster(self.admin, action="add_section", sector_id=self.secteur.pk, name="Interdite")
        self.assertFalse(Section.objects.filter(name="Interdite").exists())

    def test_un_administrateur_ne_peut_pas_archiver_une_unite_d_un_autre_batiment(self):
        autre = Ship.objects.create(name="Navire B", code="B")
        service_b = Service.objects.create(ship=autre, name="Service B")
        secteur_b = Sector.objects.create(service=service_b, name="Secteur B")
        self._poster(self.admin_navire, action="archive_unit", kind="sector", pk=secteur_b.pk)
        secteur_b.refresh_from_db()
        self.assertFalse(secteur_b.archived)


class SelecteursEtMaterielTests(BaseArchivage):
    def test_le_secteur_concerne_d_une_anomalie_ne_propose_plus_un_secteur_archive(self):
        from logistics.anomalie_views import _secteurs_selectionnables

        Sector.objects.filter(pk=self.secteur.pk).update(archived=True)
        self.assertNotIn(self.secteur, list(_secteurs_selectionnables(self.marin)))

    def test_un_materiel_ne_peut_pas_etre_nouvellement_rattache_a_une_unite_archivee(self):
        archivage.archiver(self.autre_section, self.admin)
        installation = Installation(designation="Pompe", ship=self.navire, service=self.service, sector=self.secteur, section=self.autre_section)
        installation.section.refresh_from_db()
        with self.assertRaises(ValidationError) as ctx:
            archivage.verifier_rattachement(installation)
        self.assertIn("section", ctx.exception.message_dict)

    def test_un_materiel_deja_rattache_reste_modifiable_apres_archivage_de_son_unite(self):
        installation = Installation.objects.create(designation="Pompe", ship=self.navire, service=self.service, sector=self.secteur, section=self.autre_section)
        Section.objects.filter(pk=self.autre_section.pk).update(archived=True)
        installation = Installation.objects.get(pk=installation.pk)
        installation.designation = "Pompe n° 2"
        archivage.verifier_rattachement(installation)  # valeur inchangée : aucune erreur
        deplacee = Installation.objects.get(pk=installation.pk)
        deplacee.section = self.section
        archivage.verifier_rattachement(deplacee)  # vers une unité active : permis


class MaterielEtComptesDesactivesTests(BaseArchivage):
    def test_l_affectation_en_masse_d_installations_a_une_section_archivee_est_refusee(self):
        archivage.archiver(self.autre_section, self.admin)
        installation = Installation.objects.create(designation="Pompe", ship=self.navire, service=self.service, sector=self.secteur)
        self.client.force_login(self.admin)
        reponse = self.client.post(reverse("installation-list"), {
            "action": "bulk_update_section", "selected_ids": [str(installation.pk)], "section_id": self.autre_section.pk}, follow=True)
        installation.refresh_from_db()
        self.assertIsNone(installation.section_id)
        self.assertContains(reponse, "archivé")

    def test_l_affectation_en_masse_a_une_section_active_reste_possible(self):
        installation = Installation.objects.create(designation="Pompe", ship=self.navire, service=self.service, sector=self.secteur)
        self.client.force_login(self.admin)
        self.client.post(reverse("installation-list"), {
            "action": "bulk_update_section", "selected_ids": [str(installation.pk)], "section_id": self.section.pk}, follow=True)
        installation.refresh_from_db()
        self.assertEqual(installation.section_id, self.section.pk)

    def test_l_api_materiel_tolere_la_valeur_archivee_inchangee_et_refuse_un_nouveau_rattachement(self):
        type_materiel = AssetType.objects.create(name="Pompe", category="Hydraulique", sector=self.secteur)
        materiel = Asset.objects.create(designation="Pompe 1", asset_type=type_materiel, ship=self.navire, service=self.service,
                                        sector=self.secteur, section=self.autre_section)
        Section.objects.filter(pk=self.autre_section.pk).update(archived=True)
        requete = APIRequestFactory().patch("/x/")
        requete.user = self.admin_navire
        contexte = {"request": requete}
        inchange = AssetSerializer(materiel, data={"section": self.autre_section.pk}, partial=True, context=contexte)
        self.assertTrue(inchange.is_valid(), inchange.errors)
        autre = Section.objects.create(sector=self.secteur, name="Archivée neuve", archived=True)
        nouveau = AssetSerializer(materiel, data={"section": autre.pk}, partial=True, context=contexte)
        self.assertFalse(nouveau.is_valid())

    def test_un_compte_desactive_rattache_a_une_unite_archivee_garde_son_option_dans_l_annuaire(self):
        User.objects.filter(pk=self.marin.pk).update(is_active=False)
        Section.objects.filter(pk=self.section.pk).update(archived=True)
        self.assertIn(self.section, list(archivage.exclure_archives(Section.objects.all(), garder_occupees=True)))
        self.client.force_login(self.admin)
        self.assertIn(self.section, list(self.client.get(reverse("user-directory")).context["sections"]))
        self.marin.profile.refresh_from_db()
        self.assertEqual(self.marin.profile.section_id, self.section.pk)  # rien n'a été modifié

    def test_deplacer_une_unite_vers_un_parent_archive_est_refuse_par_l_api(self):
        autre_service = Service.objects.create(ship=self.navire, name="Hôtellerie")
        Service.objects.filter(pk=autre_service.pk).update(archived=True)
        api = APIClient()
        api.force_authenticate(self.admin)
        reponse = api.patch(f"/api/org/sectors/{self.secteur.pk}/", {"service": autre_service.pk}, format="json")
        self.assertEqual(reponse.status_code, 400, getattr(reponse, "data", None))
        self.secteur.refresh_from_db()
        self.assertEqual(self.secteur.service_id, self.service.pk)


class StockEtListesTests(BaseArchivage):
    def setUp(self):
        super().setUp()
        archivage.archiver(self.autre_section, self.admin)
        self.autre_section.refresh_from_db()
        Sector.objects.filter(pk=self.secteur.pk).update(archived=False)
        self.secteur_archive = Sector.objects.create(service=self.service, name="Hors service", archived=True)
        self.client.force_login(self.admin)

    def _piece(self, secteur=None, **extra):
        secteur = secteur or self.secteur
        return StockPiece.objects.create(reference="R1", designation="Joint", ship=self.navire, service=self.service, sector=secteur, **extra)

    def _poster_stock(self, **donnees):
        base = {"reference": "R2", "designation": "Filtre", "quantite": "1", "quantite_minimale": "0"}
        return self.client.post(reverse("stock-piece-list"), {**base, **donnees}, follow=True)

    def test_une_nouvelle_piece_ne_peut_pas_etre_rattachee_a_un_secteur_archive(self):
        reponse = self._poster_stock(action="create_piece", sector_id=self.secteur_archive.pk)
        self.assertFalse(StockPiece.objects.filter(reference="R2").exists())
        self.assertContains(reponse, "archivé")

    def test_une_nouvelle_piece_ne_peut_pas_etre_rattachee_a_une_section_archivee(self):
        self._poster_stock(action="create_piece", sector_id=self.secteur.pk, section_id=self.autre_section.pk)
        self.assertFalse(StockPiece.objects.filter(reference="R2").exists())

    def test_une_nouvelle_piece_dans_un_secteur_actif_reste_possible(self):
        self._poster_stock(action="create_piece", sector_id=self.secteur.pk)
        self.assertTrue(StockPiece.objects.filter(reference="R2", sector=self.secteur).exists())

    def test_une_piece_ne_peut_pas_etre_deplacee_vers_un_secteur_archive(self):
        piece = self._piece()
        self._poster_stock(action="edit_piece", pk=piece.pk, reference="R1", designation="Joint", sector_id=self.secteur_archive.pk)
        piece.refresh_from_db()
        self.assertEqual(piece.sector_id, self.secteur.pk)

    def test_une_piece_deja_dans_un_secteur_archive_reste_modifiable_sans_changer_de_secteur(self):
        piece = self._piece(secteur=self.secteur_archive)
        self._poster_stock(action="edit_piece", pk=piece.pk, reference="R1", designation="Joint renommé", sector_id=self.secteur_archive.pk)
        piece.refresh_from_db()
        self.assertEqual((piece.designation, piece.sector_id), ("Joint renommé", self.secteur_archive.pk))

    def test_la_creation_de_liste_est_refusee_par_le_post_meme_si_l_option_est_forcee(self):
        for action in ("creer_quart", "creer_service_garde"):
            reponse = self.client.post(reverse("quarts-index"), {
                "action": action, "perimetre": f"section:{self.autre_section.pk}", "date_debut": "2026-12-01", "date_fin": "2026-12-07"}, follow=True)
            self.assertContains(reponse, "archivé", msg_prefix=action)
        self.assertEqual((Quart.objects.count(), ServiceGarde.objects.count()), (0, 0))

    def test_la_designation_d_un_chef_de_liste_sur_un_niveau_archive_est_refusee(self):
        self.client.post(reverse("quarts-reglages"), {
            "action": "designer", "perimetre": f"section:{self.autre_section.pk}", "user_id": self.marin.pk, "type_liste": "QUARTS"})
        self.assertFalse(ChefDeListe.objects.exists())


class FormationEtCatalogueTests(BaseArchivage):
    def setUp(self):
        super().setUp()
        archivage.archiver(self.autre_section, self.admin)
        self.autre_section.refresh_from_db()
        self.cours = TrainingCourse.objects.create(title="Lutte incendie")
        self.api = APIClient()
        self.api.force_authenticate(self.admin)

    def test_une_nouvelle_exigence_de_formation_ne_peut_pas_cibler_une_unite_archivee(self):
        reponse = self.api.post("/api/training/requirements/", {"course": self.cours.pk, "applies_to_section": self.autre_section.pk}, format="json")
        self.assertEqual(reponse.status_code, 403, getattr(reponse, "data", None))
        self.assertIn("archivée", str(reponse.data))
        self.assertFalse(TrainingRequirement.objects.exists())

    def test_une_nouvelle_exigence_vers_une_unite_active_reste_possible(self):
        reponse = self.api.post("/api/training/requirements/", {"course": self.cours.pk, "applies_to_section": self.section.pk}, format="json")
        self.assertEqual(reponse.status_code, 201, getattr(reponse, "data", None))

    def test_une_exigence_existante_sur_une_unite_archivee_reste_modifiable_mais_pas_deplacable_vers_une_autre(self):
        exigence = TrainingRequirement.objects.create(course=self.cours, applies_to_section=self.autre_section)
        reponse = self.api.patch(f"/api/training/requirements/{exigence.pk}/", {"required": False}, format="json")
        self.assertEqual(reponse.status_code, 200, getattr(reponse, "data", None))
        autre = Section.objects.create(sector=self.secteur, name="Archivée 2", archived=True)
        reponse = self.api.patch(f"/api/training/requirements/{exigence.pk}/", {"applies_to_section": autre.pk}, format="json")
        self.assertEqual(reponse.status_code, 403)

    def test_la_non_regression_formation_pour_un_administrateur_de_bord(self):
        api = APIClient()
        api.force_authenticate(self.admin_navire)
        reponse = api.post("/api/training/requirements/", {"course": self.cours.pk, "applies_to_section": self.autre_section.pk}, format="json")
        self.assertEqual(reponse.status_code, 403)
        reponse = api.post("/api/training/requirements/", {"course": self.cours.pk, "applies_to_section": self.section.pk}, format="json")
        self.assertEqual(reponse.status_code, 201, getattr(reponse, "data", None))

    def _article(self):
        specialite = SpecialityChoice.objects.create(name="Mécanique")
        categorie = CategorieCatalogue.objects.create(nom="Pompes", specialite=specialite)
        return ArticleCatalogue.objects.create(categorie=categorie, designation="Pompe type A")

    def test_la_creation_en_masse_du_catalogue_refuse_une_unite_archivee_sans_rien_creer(self):
        article = self._article()
        Sector.objects.filter(pk=self.secteur.pk).update(archived=True)
        self.secteur.refresh_from_db()
        with self.assertRaises(ValidationError):
            creer_exemplaires(self.admin, article, 3, self.secteur)
        with self.assertRaises(ValidationError):
            creer_exemplaires(self.admin, article, 3, Sector.objects.get(pk=self.secteur.pk), section=self.section)
        self.assertEqual(Asset.objects.count(), 0)

    def test_la_creation_en_masse_vers_une_section_archivee_est_refusee_et_vers_une_section_active_possible(self):
        article = self._article()
        with self.assertRaises(ValidationError):
            creer_exemplaires(self.admin, article, 2, self.secteur, section=self.autre_section)
        self.assertEqual(Asset.objects.count(), 0)
        self.assertEqual(len(creer_exemplaires(self.admin, article, 2, self.secteur, section=self.section)), 2)

    def test_l_assistant_d_equipement_refuse_un_secteur_archive_poste_a_la_main(self):
        article = self._article()
        Sector.objects.filter(pk=self.secteur.pk).update(archived=True)
        self.client.force_login(self.admin)
        reponse = self.client.post(reverse("catalogue-article-equiper", args=[article.pk]), {
            "etape": "2", "quantite": "2", "secteur": str(self.secteur.pk)})
        self.assertIn(reponse.status_code, (400, 403))
        self.assertEqual(Asset.objects.count(), 0)


class EcranReglagesComplementsTests(BaseArchivage):
    def _poster(self, **donnees):
        self.client.force_login(self.admin)
        return self.client.post(reverse("settings"), {"next_tab": "hierarchie", "selected_ship": self.navire.pk, **donnees}, follow=True)

    def test_ajouter_une_unite_dont_l_homonyme_est_archive_ne_pretend_pas_l_avoir_ajoutee(self):
        archivage.archiver(self.autre_section, self.admin)
        reponse = self._poster(action="add_section", sector_id=self.secteur.pk, name="Tribord")
        contenu = reponse.content.decode()
        self.assertIn("archivé", contenu)
        self.assertNotIn("Section ajoutée", contenu)
        self.assertEqual(Section.objects.filter(name="Tribord").count(), 1)
        self.autre_section.refresh_from_db()
        self.assertTrue(self.autre_section.archived)  # ni créé, ni réactivé en douce

    def test_ajouter_un_homonyme_actif_signale_qu_il_existe_deja(self):
        reponse = self._poster(action="add_service", name="Propulsion")
        self.assertNotIn("Service ajouté", reponse.content.decode())
        self.assertEqual(Service.objects.filter(name="Propulsion").count(), 1)

    def test_ajouter_une_unite_nouvelle_reste_possible(self):
        reponse = self._poster(action="add_service", name="Hôtellerie")
        self.assertContains(reponse, "Service ajouté")
        self.assertTrue(Service.objects.filter(name="Hôtellerie", ship=self.navire, archived=False).exists())

    def test_dupliquer_un_batiment_ne_recopie_pas_les_unites_archivees_comme_actives(self):
        archivage.archiver(self.autre_section, self.admin)
        service_archive = Service.objects.create(ship=self.navire, name="Ancien service", archived=True)
        secteur_ancien = Sector.objects.create(service=service_archive, name="Ancien secteur")
        Section.objects.create(sector=secteur_ancien, name="Ancienne section")
        self.client.force_login(self.admin)
        self.client.post(reverse("settings"), {"action": "duplicate_ship", "source_pk": self.navire.pk, "name": "Copie", "code": "CP",
                                               "fuseau_horaire": "Europe/Paris"})
        copie = Ship.objects.get(code="CP")
        self.assertEqual(sorted(Service.objects.filter(ship=copie).values_list("name", flat=True)), ["Propulsion"])
        self.assertEqual(sorted(Section.objects.filter(sector__service__ship=copie).values_list("name", flat=True)), ["Bâbord"])
        self.assertFalse(Service.objects.filter(ship=copie, archived=True).exists())
        self.assertTrue(Service.objects.filter(pk=service_archive.pk, archived=True).exists())  # l'original est intact


class EditionCompteDesactiveTests(BaseArchivage):
    """Intégration : éditer un compte désactivé rattaché à une unité archivée conserve rattachement, périmètre et historique."""

    def setUp(self):
        super().setUp()
        User.objects.filter(pk=self.marin.pk).update(is_active=False)
        Section.objects.filter(pk=self.section.pk).update(archived=True)  # donnée antérieure à la règle
        self.client.force_login(self.admin)
        self.periode = AuditLog.objects.create(actor=self.admin, action="historique_marin", target_user=self.marin, details="avant")

    def _editer(self, **champs):
        profil = self.marin.profile
        donnees = {"action": "edit_user", "pk": self.marin.pk, "username": self.marin.username, "first_name": "Karim", "last_name": "Test",
                   "ship_id": profil.ship_id, "service_id": profil.service_id, "sector_id": profil.sector_id, "section_id": profil.section_id,
                   **champs}
        return self.client.post(reverse("user-directory"), donnees, follow=True)

    def test_l_edition_conserve_le_rattachement_le_perimetre_et_l_historique(self):
        avant = (scope_filters_for_user(User.objects.get(pk=self.marin.pk)), User.objects.get(pk=self.marin.pk).profile.scope)
        reponse = self._editer()
        marin = User.objects.get(pk=self.marin.pk)
        self.assertContains(reponse, "mis à jour")
        self.assertEqual(marin.first_name, "Karim")
        self.assertFalse(marin.is_active)  # toujours désactivé
        self.assertEqual((marin.profile.ship_id, marin.profile.service_id, marin.profile.sector_id, marin.profile.section_id),
                         (self.navire.pk, self.service.pk, self.secteur.pk, self.section.pk))
        self.assertEqual((scope_filters_for_user(marin), marin.profile.scope), avant)
        self.assertTrue(AuditLog.objects.filter(pk=self.periode.pk, details="avant").exists())
        self.assertTrue(AuditLog.objects.filter(action="edit_user", target_user=marin).exists())

    def test_l_edition_ne_peut_pas_deplacer_le_compte_vers_une_autre_unite_archivee(self):
        autre = Section.objects.create(sector=self.secteur, name="Archivée 3", archived=True)
        reponse = self._editer(section_id=autre.pk, first_name="Autre")
        marin = User.objects.get(pk=self.marin.pk)
        self.assertContains(reponse, "archivé")
        self.assertEqual((marin.first_name, marin.profile.section_id), (self.marin.first_name, self.section.pk))

    def test_le_formulaire_propose_encore_l_unite_archivee_du_compte_desactive(self):
        sections = list(self.client.get(reverse("user-directory")).context["sections"])
        self.assertIn(self.section, sections)
