"""Fichiers téléversés (/media/…) : aucun accès sans autorisation de l'objet propriétaire,
même en connaissant l'URL ; tout champ fichier du projet est couvert par le registre."""
from django.apps import apps
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import UserProfile
from assets.models import Asset, AssetDocument, AssetType, Deck, DocumentInstallation, Installation
from documentation import services
from logistics.models import Anomalie
from matrix.core.medias import registre
from matrix.core.testing import MediaRootTemporaireMixin
from org.models import Sector, Service, Ship
from taches.models import PieceJointeTache, Tache

CONTENU = b"%PDF-1.4\nsecret de test\n"


def _fichier(nom="secret.pdf", contenu=CONTENU):
    return SimpleUploadedFile(nom, contenu)


class RegistreMediasTests(TestCase):
    def test_tout_champ_fichier_est_protege(self):
        """Un nouveau champ fichier oublié du registre resterait inaccessible : ce test le signale."""
        couverts = {(e.modele, e.champ) for e in registre()}
        for modele in apps.get_models():
            for champ in modele._meta.get_fields():
                if isinstance(champ, models.FileField):
                    self.assertIn((modele, champ.name), couverts, f"{modele.__name__}.{champ.name} hors registre")


class MediasBase(MediaRootTemporaireMixin, TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Navire A", code="NA")
        self.service = Service.objects.create(ship=self.navire, name="Énergie")
        self.secteur = Sector.objects.create(service=self.service, name="Propulsion")
        self.autre_secteur = Sector.objects.create(service=self.service, name="Électricité")
        self.autre_navire = Ship.objects.create(name="Navire B", code="NB")
        self.autre_service = Service.objects.create(ship=self.autre_navire, name="Pont")
        self.autre_sect = Sector.objects.create(service=self.autre_service, name="Manoeuvre")
        self.chef = self._marin("chef", self.navire, self.secteur, "CHEF_SECTION")
        self.marin = self._marin("marin", self.navire, self.secteur, "EQUIPIER")
        self.voisin = self._marin("voisin", self.navire, self.autre_secteur, "EQUIPIER")
        self.etranger = self._marin("etranger", self.autre_navire, self.autre_sect, "EQUIPIER")

    def _marin(self, nom, navire, secteur, role):
        user = User.objects.create_user(username=nom, password="pass")
        profil = user.profile
        profil.role, profil.ship, profil.sector, profil.service = role, navire, secteur, secteur.service
        profil.save()
        return user

    def _chef_service(self, nom):
        user = self._marin(nom, self.navire, self.secteur, "CHEF_SERVICE")
        UserProfile.objects.filter(user=user).update(sector=None)
        return User.objects.get(pk=user.pk)

    def _recupere(self, url, nom=None):
        if nom:
            self.client.login(username=nom, password="pass")
        return self.client.get(url)

    def assert_servi(self, url, nom):
        reponse = self._recupere(url, nom)
        self.assertEqual(reponse.status_code, 200, nom)
        self.assertEqual(b"".join(reponse.streaming_content), CONTENU)
        self.assertEqual(reponse["X-Content-Type-Options"], "nosniff")

    def assert_refuse(self, url, nom=None):
        self.assertEqual(self._recupere(url, nom).status_code, 404, nom)


class FichiersMetierTests(MediasBase):
    def test_anonyme_redirige_vers_la_connexion(self):
        piece = PieceJointeTache.objects.create(
            tache=Tache.objects.create(titre="T", assigne=self.marin, created_by=self.chef), fichier=_fichier(), nom="s.pdf")
        reponse = self.client.get(piece.fichier.url)
        self.assertEqual(reponse.status_code, 302)
        self.assertIn("/login", reponse["Location"])

    def test_piece_jointe_de_tache(self):
        tache = Tache.objects.create(titre="Privée", assigne=self.marin, created_by=self.chef)
        piece = PieceJointeTache.objects.create(tache=tache, fichier=_fichier(), nom="secret.pdf")
        self.assertTrue(piece.fichier.url.startswith("/media/taches_pieces_jointes/"))
        self.assert_servi(piece.fichier.url, "marin")
        self.assert_servi(piece.fichier.url, "chef")
        for nom in ("voisin", "etranger"):
            self.assert_refuse(piece.fichier.url, nom)

    def test_documentation_brouillon_invisible(self):
        auteur = self._chef_service("redacteur")
        document = services.creer_document(auteur, "Procédure", f"service:{self.service.pk}", "texte", fichier=_fichier())
        version = document.versions.get()
        self.assert_servi(version.fichier.url, "redacteur")
        self.assert_refuse(version.fichier.url, "marin")  # brouillon : réservé à l'auteur et aux gestionnaires
        self.assert_refuse(version.fichier.url, "etranger")

    def test_documentation_publiee_visible_du_public_vise_seulement(self):
        auteur = self._chef_service("redacteur")
        valideur = self._chef_service("valideur")
        document = services.creer_document(auteur, "Procédure", f"service:{self.service.pk}", "texte", fichier=_fichier())
        services.soumettre(auteur, document.versions.get())
        services.valider(valideur, document.versions.get())
        url = document.versions.get().fichier.url
        self.assert_servi(url, "marin")
        self.assert_refuse(url, "etranger")

    def test_document_de_materiel_par_batiment(self):
        type_actif = AssetType.objects.create(name="Pompe", category="Fluides", sector=self.secteur)
        actif = Asset.objects.create(asset_type=type_actif, ship=self.navire, service=self.service, sector=self.secteur)
        doc = AssetDocument.objects.create(asset=actif, file=_fichier(), name="Notice")
        self.assert_servi(doc.file.url, "marin")
        self.assert_refuse(doc.file.url, "etranger")

    def test_document_d_installation_par_batiment(self):
        installation = Installation.objects.create(
            designation="Groupe", ship=self.navire, service=self.service, sector=self.secteur)
        doc = DocumentInstallation.objects.create(installation=installation, titre="Plan", fichier=_fichier())
        self.assert_servi(doc.fichier.url, "marin")
        self.assert_refuse(doc.fichier.url, "etranger")

    def test_plan_de_pont_reserve_au_navire(self):
        pont = Deck.objects.create(ship=self.navire, name="Pont 1", image=_fichier("plan.png", CONTENU))
        self.assert_servi(pont.image.url, "marin")
        self.assert_refuse(pont.image.url, "etranger")

    def test_photo_d_anomalie(self):
        anomalie = Anomalie.objects.create(
            titre="Fuite", ship=self.navire, service=self.service, sector=self.secteur,
            created_by=self.marin, photo=_fichier("fuite.png", CONTENU))
        self.assert_servi(anomalie.photo.url, "marin")
        self.assert_refuse(anomalie.photo.url, "etranger")
        self.assert_refuse(anomalie.photo.url, "voisin")  # autre secteur du même bâtiment

    def test_chemins_invalides_ou_inconnus(self):
        self.client.login(username="marin", password="pass")
        for chemin in ("inconnu/x.pdf", "taches_pieces_jointes/../../etc/passwd", "taches_pieces_jointes/absent.pdf",
                       "anomalie_photos/attente/x.png"):
            self.assertEqual(self.client.get(f"/media/{chemin}").status_code, 404, chemin)

    @override_settings(MEDIA_ACCEL_REDIRECT="/media-interne/")
    def test_delegation_au_serveur_web(self):
        tache = Tache.objects.create(titre="T", assigne=self.marin, created_by=self.chef)
        piece = PieceJointeTache.objects.create(tache=tache, fichier=_fichier(), nom="s.pdf")
        self.client.login(username="marin", password="pass")
        reponse = self.client.get(piece.fichier.url)
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse["X-Accel-Redirect"], f"/media-interne/{piece.fichier.name}")
        self.assertEqual(reponse.content, b"")
        self.client.login(username="etranger", password="pass")
        self.assertEqual(self.client.get(piece.fichier.url).status_code, 404)
