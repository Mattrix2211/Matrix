"""Documents d'installation : droits, périmètre, validation du fichier, téléchargement, équipage à terre."""
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import AuditLog, UserProfile
from assets.models import DocumentInstallation, Installation
from org.models import Sector, Service, Ship

PDF = b"%PDF-1.4 contenu"


class DocumentsInstallationTests(TestCase):
    def setUp(self):
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        self.enterContext(override_settings(MEDIA_ROOT=dossier.name))
        self.navire, self.service, self.secteur = self._navire("A")
        self.navire_b, service_b, secteur_b = self._navire("B")
        self.installation = self._installation(self.navire, self.service, self.secteur)
        self.installation_b = self._installation(self.navire_b, service_b, secteur_b)
        self.chef_section = self._user("chef_section_doc", "CHEF_SECTION")
        self.chef_service = self._user("chef_service_doc", "CHEF_SERVICE")
        self.equipier = self._user("equipier_doc", "EQUIPIER")
        self.url_ajout = reverse("installation-document-ajouter", args=[self.installation.pk])

    def _navire(self, nom, **extra):
        navire = Ship.objects.create(name=f"Navire {nom} doc", code=f"{nom}-DOC", **extra)
        service = Service.objects.create(name=f"Srv {nom}", ship=navire)
        return navire, service, Sector.objects.create(name=f"Sec {nom}", service=service)

    def _installation(self, navire, service, secteur):
        return Installation.objects.create(designation="Groupe", ship=navire, service=service, sector=secteur)

    def _user(self, nom, role, **extra):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={
            "role": role, "ship": self.navire, "service": self.service, "sector": self.secteur, **extra})
        return User.objects.get(pk=user.pk)

    def _ajouter(self, user, nom="plan.pdf", contenu=PDF, url=None, **extra):
        self.client.force_login(user)
        return self.client.post(url or self.url_ajout, {
            "fichier": SimpleUploadedFile(nom, contenu), "titre": "Plan général", "type_document": "plan", **extra})

    def _document(self):
        return DocumentInstallation.objects.create(
            installation=self.installation, titre="Notice", fichier=SimpleUploadedFile("notice.pdf", PDF))

    def test_ajout_par_un_chef_de_section(self):
        r = self._ajouter(self.chef_section)
        self.assertRedirects(r, reverse("installation-detail", args=[self.installation.pk]))
        doc = DocumentInstallation.objects.get()
        self.assertEqual((doc.titre, doc.type_document, doc.created_by, doc.updated_by),
                         ("Plan général", "plan", self.chef_section, self.chef_section))
        self.assertTrue(AuditLog.objects.filter(action="installation.document_ajout").exists())

    def test_auteur_non_modifiable_par_le_formulaire(self):
        self._ajouter(self.chef_section, created_by=self.chef_service.pk)
        self.assertEqual(DocumentInstallation.objects.get().created_by, self.chef_section)

    def test_ajout_refuse_sous_le_seuil(self):
        self.assertEqual(self._ajouter(self.equipier).status_code, 403)
        self.assertFalse(DocumentInstallation.objects.exists())

    def test_refus_html_svg_script_exe(self):
        for nom in ("page.html", "image.svg", "x.js", "x.exe", "x.pdf.html", "sans_extension"):
            self._ajouter(self.chef_section, nom=nom, contenu=b"<script>alert(1)</script>")
        self.assertFalse(DocumentInstallation.objects.exists())

    def test_contenu_deguise_refuse(self):
        self._ajouter(self.chef_section, nom="faux.pdf", contenu=b"<html><script>alert(1)</script>")
        self.assertFalse(DocumentInstallation.objects.exists())

    def test_extensions_autorisees(self):
        contenus = {"a.pdf": PDF, "a.png": b"\x89PNG\r\n\x1a\n0", "a.jpg": b"\xff\xd8\xff0", "a.jpeg": b"\xff\xd8\xff0",
                    "a.webp": b"RIFF0000WEBP", "a.txt": b"texte", "a.docx": b"PK\x03\x040", "a.xlsx": b"PK\x03\x040"}
        for nom, contenu in contenus.items():
            self._ajouter(self.chef_section, nom=nom, contenu=contenu)
        self.assertEqual(DocumentInstallation.objects.count(), len(contenus))

    @override_settings(DOCUMENT_TAILLE_MAX_MO=1)
    def test_taille_maximale_configurable(self):
        self._ajouter(self.chef_section, contenu=PDF + b"0" * (1024 * 1024))
        self.assertFalse(DocumentInstallation.objects.exists())

    def test_ajout_sur_une_installation_d_un_autre_navire_introuvable(self):
        r = self._ajouter(self.chef_section, url=reverse("installation-document-ajouter", args=[self.installation_b.pk]))
        self.assertEqual(r.status_code, 404)
        self.assertFalse(DocumentInstallation.objects.exists())

    def test_telechargement_en_piece_jointe(self):
        doc = self._document()
        self.client.force_login(self.equipier)
        r = self.client.get(reverse("installation-document-telecharger", args=[self.installation.pk, doc.pk]))
        self.addCleanup(r.close)  # Windows : le PDF doit être fermé avant la suppression du dossier temporaire
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r["Content-Disposition"].startswith("attachment"))
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")

    def test_telechargement_inter_navire_et_mauvaise_installation_refuses(self):
        doc = self._document()
        autre = self._user("chef_b_doc", "CHEF_SERVICE")
        autre.profile.ship, autre.profile.service, autre.profile.sector = self.navire_b, self.installation_b.service, self.installation_b.sector
        autre.profile.save()
        self.client.force_login(autre)
        self.assertEqual(self.client.get(reverse("installation-document-telecharger", args=[self.installation.pk, doc.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("installation-document-telecharger", args=[self.installation_b.pk, doc.pk])).status_code, 404)

    def test_suppression_reservee_au_seuil_avance(self):
        doc = self._document()
        url = reverse("installation-document-supprimer", args=[self.installation.pk, doc.pk])
        self.client.force_login(self.chef_section)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertTrue(DocumentInstallation.objects.exists())
        self.client.force_login(self.chef_service)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertFalse(DocumentInstallation.objects.exists())
        self.assertTrue(AuditLog.objects.filter(action="installation.document_suppression").exists())

    def test_suppression_inter_navire_refusee(self):
        doc = self._document()
        autre = self._user("chef_b2_doc", "CHEF_SERVICE")
        autre.profile.ship, autre.profile.service, autre.profile.sector = self.navire_b, self.installation_b.service, self.installation_b.sector
        autre.profile.save()
        self.client.force_login(autre)
        r = self.client.post(reverse("installation-document-supprimer", args=[self.installation.pk, doc.pk]))
        self.assertEqual(r.status_code, 404)
        self.assertTrue(DocumentInstallation.objects.exists())

    def test_fiche_liste_documents_et_boutons_selon_droits(self):
        self._document()
        fiche = reverse("installation-detail", args=[self.installation.pk])
        self.client.force_login(self.chef_service)
        r = self.client.get(fiche)
        self.assertContains(r, "Notice")
        self.assertContains(r, "Ajouter un document")
        self.assertContains(r, "documents/%s/supprimer/" % DocumentInstallation.objects.get().pk)
        self.client.force_login(self.equipier)
        r = self.client.get(fiche)
        self.assertContains(r, "Notice")
        self.assertNotContains(r, "Ajouter un document")
        self.assertNotContains(r, "/supprimer/")

    def test_equipage_a_terre_lecture_seule(self):
        navire, service, secteur = self._navire("C", double_equipage=True, equipage_a_bord="A")
        installation = self._installation(navire, service, secteur)
        doc = DocumentInstallation.objects.create(installation=installation, titre="Notice C",
                                                  fichier=SimpleUploadedFile("c.pdf", PDF))
        terre = User.objects.create_user(username="terre_doc", password="pass")
        UserProfile.objects.update_or_create(user=terre, defaults={
            "role": "CHEF_SERVICE", "ship": navire, "service": service, "sector": secteur, "equipage": "B"})
        self.client.force_login(terre)
        fiche = self.client.get(reverse("installation-detail", args=[installation.pk]))
        self.assertContains(fiche, "Notice C")
        self.assertNotContains(fiche, "Ajouter un document")
        self.assertNotContains(fiche, "/supprimer/")
        telechargement = self.client.get(reverse("installation-document-telecharger", args=[installation.pk, doc.pk]))
        self.addCleanup(telechargement.close)
        self.assertEqual(telechargement.status_code, 200)
        r = self.client.post(reverse("installation-document-ajouter", args=[installation.pk]),
                             {"fichier": SimpleUploadedFile("p.pdf", PDF)})
        self.assertEqual(r.status_code, 403)
        r = self.client.post(reverse("installation-document-supprimer", args=[installation.pk, doc.pk]))
        self.assertEqual(r.status_code, 403)
        self.assertEqual(DocumentInstallation.objects.count(), 1)
