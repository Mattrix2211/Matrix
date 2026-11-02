from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from org.data import referentiel_batiments as donnees
from org.models import ReferenceBatiment, Ship, TypeBatiment


def importer():
    sortie = StringIO()
    call_command("importer_referentiel_batiments", stdout=sortie)
    return sortie.getvalue()


class ImportReferentielTests(TestCase):
    def test_import_complet_puis_idempotent(self):
        importer()
        attendu = len(donnees.INVENTAIRE_2025) + len(donnees.GENDARMERIE_2025) + len(donnees.ESSAIS_2025) + 1
        self.assertEqual(ReferenceBatiment.objects.count(), attendu)
        importer()
        self.assertEqual(ReferenceBatiment.objects.count(), attendu)

    def test_aucun_numero_de_coque_en_double(self):
        coques = [ligne[2] for ligne in (*donnees.INVENTAIRE_2025, *donnees.GENDARMERIE_2025, *donnees.ESSAIS_2025)]
        self.assertEqual(len(coques), len(set(coques)))

    def test_statuts_2025_ni_actifs_2026_ni_fusionnes_avec_les_essais(self):
        importer()
        bretagne = ReferenceBatiment.objects.get(numero_coque="D 655")
        self.assertEqual(bretagne.statut, ReferenceBatiment.Statut.REFERENCE_2025)
        self.assertEqual(bretagne.port_base, "Brest")
        self.assertEqual(ReferenceBatiment.objects.get(numero_coque="P 782").statut, ReferenceBatiment.Statut.ESSAIS)

    def test_graphie_validee_du_ravitailleur(self):
        importer()
        self.assertEqual(ReferenceBatiment.objects.get(numero_coque="A 725").nom, "Jacques Chevallier")

    def test_gendarmerie_distincte_et_drone_sans_equipage(self):
        importer()
        self.assertEqual(ReferenceBatiment.objects.get(numero_coque="P 719").famille, ReferenceBatiment.Famille.GENDARMERIE)
        self.assertFalse(ReferenceBatiment.objects.get(numero_coque="O 701").avec_equipage)

    def test_mises_a_jour_2026_ciblees_et_de_grasse_sans_coque_inventee(self):
        importer()
        self.assertEqual(ReferenceBatiment.objects.get(numero_coque="D 660").statut, ReferenceBatiment.Statut.LIVRE)
        self.assertEqual(ReferenceBatiment.objects.get(numero_coque="S 637").statut, ReferenceBatiment.Statut.CONFIRME)
        de_grasse = ReferenceBatiment.objects.get(nom="De Grasse")
        self.assertEqual((de_grasse.numero_coque, de_grasse.statut), ("", ReferenceBatiment.Statut.LIVRE))
        self.assertEqual(ReferenceBatiment.objects.get(numero_coque="A 726").statut, ReferenceBatiment.Statut.ESSAIS)

    def test_une_saisie_en_administration_n_est_jamais_ecrasee(self):
        importer()
        ReferenceBatiment.objects.filter(numero_coque="D 655").update(statut=ReferenceBatiment.Statut.RETIRE, archive=True, port_base="Lorient")
        importer()
        bretagne = ReferenceBatiment.objects.get(numero_coque="D 655")
        self.assertEqual((bretagne.statut, bretagne.archive, bretagne.port_base), (ReferenceBatiment.Statut.RETIRE, True, "Lorient"))

    def test_une_unite_matrix_du_meme_nom_est_reliee_a_sa_reference(self):
        navire = Ship.objects.create(name="Bretagne", code="BTE-T")
        importer()
        navire.refresh_from_db()
        self.assertEqual((navire.numero_coque, navire.trigramme, navire.type_batiment.code), ("D 655", "BTE", "FREMM"))
        self.assertEqual(ReferenceBatiment.objects.get(numero_coque="D 655").unite, navire)

    def test_un_nouveau_type_et_un_nouveau_batiment_s_ajoutent_sans_code(self):
        importer()
        type_neuf = TypeBatiment.objects.create(code="NOUVEAU", libelle="Nouveau type")
        reference = ReferenceBatiment.objects.create(nom="Futur bâtiment", numero_coque="X 999", type_batiment=type_neuf)
        self.assertEqual(str(reference), "Futur bâtiment (X 999)")
        self.assertFalse(type_neuf.silhouette)


class SilhouetteDuBandeauTests(TestCase):
    """Le bandeau affiche la silhouette du type quand elle existe, sinon le repère neutre."""

    def setUp(self):
        from django.contrib.auth.models import User
        from accounts.models import UserProfile
        self.navire = Ship.objects.create(name="Bretagne bandeau", code="BB")
        user = User.objects.create_user(username="marin_bandeau", password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": "EQUIPIER", "ship": self.navire})
        self.client.login(username="marin_bandeau", password="pass")

    def test_repli_neutre_sans_silhouette(self):
        page = self.client.get("/")
        self.assertNotContains(page, "mx-silhouette")
        self.assertContains(page, "mx-barre__batiment")

    def test_silhouette_du_type_affichee(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        type_ = TypeBatiment.objects.create(code="FREMM", libelle="FREMM")
        type_.silhouette.save("fremm.svg", SimpleUploadedFile("fremm.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>"), save=True)
        self.addCleanup(type_.silhouette.delete, False)
        self.navire.type_batiment = type_
        self.navire.save()
        page = self.client.get("/")
        self.assertContains(page, 'class="mx-silhouette"')
        self.assertContains(page, "silhouettes/fremm")
