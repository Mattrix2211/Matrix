"""Tests du validateur commun de fichiers téléversés (tâche Notion [SEC]
« Validation serveur des fichiers téléversés »).

Ce fichier teste le validateur en profondeur (matrix/core/validators.py) :
c'est ici, et non dans chaque app, que sont vérifiés les trois scénarios
demandés par la tâche (fichier renommé refusé, fichier trop gros refusé,
image valide acceptée). Les apps concernées (assets, logistics, threads,
training) n'ont qu'un test d'intégration ciblé sur un modèle représentatif,
pour ne pas dupliquer cette logique commune 15 fois.
"""
import io

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile, TemporaryUploadedFile
from django.test import SimpleTestCase
from PIL import Image as PILImage

from matrix.core.validators import (
    EXTENSIONS_DOCUMENTS,
    EXTENSIONS_IMAGES,
    ValidateurFichierTeleverse,
    message_erreur_fichier,
    valider_document,
    valider_photo,
)


def _png_1x1():
    # PNG 1x1 généré à la volée par Pillow plutôt qu'un octet figé à la main :
    # doit décoder réellement (Image.open().verify()), pas seulement
    # ressembler à un PNG.
    tampon = io.BytesIO()
    PILImage.new("RGB", (1, 1), color=(128, 128, 128)).save(tampon, format="PNG")
    return tampon.getvalue()


_PNG_1X1 = _png_1x1()


def _image_valide(nom="photo.png"):
    return SimpleUploadedFile(nom, _PNG_1X1, content_type="image/png")


def _executable_renomme(nom="virus.png"):
    # En-tête d'un exécutable Windows (signature "MZ"), renommé avec une
    # extension d'image : exactement le scénario signalé par le QA
    # (2026-08-28), accepté avant cette tâche faute de contrôle du vrai
    # contenu du fichier.
    contenu = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff" + b"\x00" * 64
    return SimpleUploadedFile(nom, contenu, content_type="image/png")


class ValidateurFichierTeleverseTests(SimpleTestCase):
    def test_image_valide_acceptee(self):
        # Ne doit lever aucune exception.
        valider_photo(_image_valide())

    def test_extension_non_autorisee_refusee(self):
        fichier = SimpleUploadedFile("notice.txt", b"contenu quelconque", content_type="text/plain")
        with self.assertRaises(ValidationError) as ctx:
            valider_photo(fichier)
        self.assertIn("Extension de fichier non autorisée", str(ctx.exception))

    def test_executable_renomme_en_image_refuse(self):
        with self.assertRaises(ValidationError) as ctx:
            valider_photo(_executable_renomme())
        self.assertIn("n'est pas une image valide", str(ctx.exception))

    def test_fichier_trop_volumineux_refuse(self):
        # Limite artificiellement basse (10 octets) pour ne pas avoir à
        # fabriquer un vrai fichier de plusieurs Mo dans les tests.
        validateur = ValidateurFichierTeleverse(EXTENSIONS_IMAGES, taille_max_octets=10, verifier_image=False)
        fichier = SimpleUploadedFile("photo.png", _PNG_1X1, content_type="image/png")
        with self.assertRaises(ValidationError) as ctx:
            validateur(fichier)
        self.assertIn("trop volumineux", str(ctx.exception))

    def test_documents_conformes_acceptes(self):
        # Un document n'est jamais décodé par Pillow : son en-tête (magic
        # bytes) doit en revanche correspondre à son extension.
        conformes = {
            "compte_rendu.pdf": b"%PDF-1.7\n1 0 obj",
            "bareme.docx": b"PK\x03\x04\x14\x00\x06\x00",
            "releves.xlsx": b"PK\x03\x04\x14\x00\x06\x00",
            "plan.odt": b"PK\x03\x04\x14\x00\x00\x08",
            "ancien.doc": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1\x00",
            "ancien.xls": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1\x00",
            "notes.txt": "Ordre du jour : réunion\n".encode("utf-8"),
            "export.csv": b"nom;grade\ndupont;QM1\n",
        }
        for nom, contenu in conformes.items():
            with self.subTest(nom=nom):
                valider_document(SimpleUploadedFile(nom, contenu))

    def test_executable_renomme_en_pdf_refuse(self):
        contenu = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 64
        with self.assertRaises(ValidationError) as ctx:
            valider_document(SimpleUploadedFile("facture.pdf", contenu, content_type="application/pdf"))
        self.assertIn("son contenu ne correspond pas à son extension", str(ctx.exception))

    def test_executable_renomme_en_txt_ou_docx_refuse(self):
        contenu = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 64
        for nom in ("notes.txt", "export.csv", "bareme.docx", "ancien.xls"):
            with self.subTest(nom=nom), self.assertRaises(ValidationError):
                valider_document(SimpleUploadedFile(nom, contenu))

    def test_texte_commencant_par_mz_accepte(self):
        for nom in ("codes.csv", "codes.txt"):
            with self.subTest(nom=nom):
                valider_document(SimpleUploadedFile(nom, b"MZ-001;Pompe de cale\nMZ-002;Extincteur\n"))

    def test_vrai_entete_pe_refuse_en_txt(self):
        entete = bytearray(b"MZ" + b"A" * 62)  # octets imprimables : seule la signature PE trahit
        entete[0x3C:0x40] = (0x40).to_bytes(4, "little")
        contenu = bytes(entete) + b"PE\x00\x00" + b"\x00" * 16
        with self.assertRaises(ValidationError):
            valider_document(SimpleUploadedFile("notes.txt", contenu))

    def test_extension_en_majuscules(self):
        valider_document(SimpleUploadedFile("RAPPORT.PDF", b"%PDF-1.4 contenu"))
        with self.assertRaises(ValidationError):
            valider_document(SimpleUploadedFile("RAPPORT.PDF", b"MZ\x90\x00\x03\x00" + b"\x00" * 64))

    def test_double_extension_sans_entete_pdf_refusee(self):
        with self.assertRaises(ValidationError):
            valider_document(SimpleUploadedFile("rapport.exe.pdf", b"MZ\x90\x00\x03\x00" + b"\x00" * 64))

    def test_fichier_temporaire_curseur_restaure(self):
        fichier = TemporaryUploadedFile("cr.pdf", "application/pdf", 20, "utf-8")
        try:
            fichier.write(b"%PDF-1.4 contenu")
            fichier.seek(5)
            valider_document(fichier)
            self.assertEqual(fichier.tell(), 5)
        finally:
            fichier.close()

    def test_document_vide_refuse(self):
        for nom in ("vide.pdf", "vide.txt", "vide.docx"):
            with self.subTest(nom=nom), self.assertRaises(ValidationError) as ctx:
                valider_document(SimpleUploadedFile(nom, b""))
            self.assertIn("vide", str(ctx.exception))

    def test_document_tronque_refuse(self):
        # Début d'une signature ZIP coupée avant la fin de l'en-tête.
        with self.assertRaises(ValidationError):
            valider_document(SimpleUploadedFile("bareme.docx", b"PK\x03"))

    def test_position_du_curseur_restauree_apres_controle_document(self):
        fichier = SimpleUploadedFile("cr.pdf", b"%PDF-1.4 contenu")
        valider_document(fichier)
        self.assertEqual(fichier.tell(), 0)

    def test_document_image_reste_verifie_par_pillow(self):
        # Une extension d'image dans la liste des documents autorisés reste
        # soumise au contrôle Pillow (le validateur document accepte aussi
        # les images, mais ne relâche pas leur contrôle de contenu).
        with self.assertRaises(ValidationError):
            valider_document(_executable_renomme("faux.jpg"))

    def test_extension_absente_refusee(self):
        fichier = SimpleUploadedFile("sans_extension", b"contenu", content_type="application/octet-stream")
        with self.assertRaises(ValidationError):
            valider_photo(fichier)

    def test_message_erreur_fichier_renvoie_none_si_aucun_fichier(self):
        self.assertIsNone(message_erreur_fichier(None, valider_photo))

    def test_message_erreur_fichier_renvoie_none_si_valide(self):
        self.assertIsNone(message_erreur_fichier(_image_valide(), valider_photo))

    def test_message_erreur_fichier_renvoie_un_message_francais_si_invalide(self):
        message = message_erreur_fichier(_executable_renomme(), valider_photo)
        self.assertIsNotNone(message)
        self.assertIn("image valide", message)

    def test_deux_validateurs_aux_memes_parametres_sont_egaux(self):
        # Important pour la stabilité des migrations Django (deconstructible) :
        # deux instances construites avec les mêmes arguments doivent être
        # considérées égales, sous peine de migrations vides générées en boucle.
        a = ValidateurFichierTeleverse(EXTENSIONS_DOCUMENTS, 123, True)
        b = ValidateurFichierTeleverse(EXTENSIONS_DOCUMENTS, 123, True)
        self.assertEqual(a, b)
