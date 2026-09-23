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
from django.core.files.uploadedfile import SimpleUploadedFile
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

    def test_document_bureautique_non_image_accepte_sans_decodage_pillow(self):
        # Un PDF n'est jamais decodé par Pillow : seules extension et taille
        # sont vérifiées pour les documents non-image.
        fichier = SimpleUploadedFile("compte_rendu.pdf", b"contenu pdf quelconque", content_type="application/pdf")
        valider_document(fichier)  # ne doit pas lever

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
