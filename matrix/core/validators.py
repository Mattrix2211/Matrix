"""Validation serveur commune des fichiers/images téléversés.

Aucun champ FileField/ImageField du projet ne doit se fier au seul nom du
fichier ou au Content-Type déclaré par le navigateur pour décider s'il s'agit
bien d'une image : ces deux informations viennent du client et se falsifient
trivialement (un exécutable renommé en « .png » les passe sans broncher).

Ce module centralise, pour l'ensemble des ~15 champs fichier du projet
(Asset.photo, Installation.photo, AssetFolder.photo, InstallationPart.photo,
Deck.image, StockPiece.photo, Anomalie.photo, AssetDocument.file, pièces
jointes de threads/training/maintenance...), un unique contrôle :
- l'extension du fichier fait partie d'une liste autorisée ;
- sa taille ne dépasse pas un maximum ;
- pour les images, son contenu est réellement décodable par Pillow (et pas
  seulement son extension qui le laisse penser).

Pillow est une dépendance obligatoire du projet (voir requirements.txt), à la
différence de WeasyPrint (export PDF, optionnel) ou pywebpush (Web Push,
optionnel) : son import n'a donc pas besoin d'être protégé ici.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from PIL import Image, UnidentifiedImageError

# Extensions d'images reconnues par Pillow, utilisées par les photos de
# matériel, d'installations, de pièces, d'anomalies et le plan du navire.
EXTENSIONS_IMAGES = ("jpg", "jpeg", "png", "gif", "webp", "bmp")

# Documents non-image acceptés en plus des images pour les pièces jointes
# (comptes rendus, barèmes de formation, certificats, plans d'installation).
# Volontairement restreint aux formats bureautiques usuels à bord.
EXTENSIONS_DOCUMENTS = EXTENSIONS_IMAGES + (
    "pdf", "doc", "docx", "xls", "xlsx", "odt", "ods", "txt", "csv",
)

# Tailles maximales par défaut, en octets. Un réseau LAN embarqué n'a pas
# besoin de fichiers plus lourds, et cela évite qu'un envoi malencontreux ne
# sature le stockage du bâtiment.
TAILLE_MAX_IMAGE = 10 * 1024 * 1024  # 10 Mo
TAILLE_MAX_DOCUMENT = 20 * 1024 * 1024  # 20 Mo

# Signatures d'en-tête (« magic bytes ») des documents non-image. Implémentées
# ici plutôt que via python-magic/libmagic : aucune dépendance système à
# installer hors ligne sur les postes du bâtiment. Le format Office récent
# (docx/xlsx) et OpenDocument (odt/ods) sont des archives ZIP.
_SIGNATURE_ZIP = (b"PK\x03\x04",)
_SIGNATURE_OLE2 = (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",)  # doc, xls anciens
SIGNATURES_DOCUMENTS = {
    "pdf": (b"%PDF-",),
    "doc": _SIGNATURE_OLE2,
    "xls": _SIGNATURE_OLE2,
    "docx": _SIGNATURE_ZIP,
    "xlsx": _SIGNATURE_ZIP,
    "odt": _SIGNATURE_ZIP,
    "ods": _SIGNATURE_ZIP,
}
# Les fichiers texte (txt, csv) n'ont pas de signature : on refuse seulement
# ceux qui commencent par l'en-tête d'un exécutable (PE, ELF) ou d'une archive.
SIGNATURES_INTERDITES_TEXTE = (b"\x7fELF", b"PK\x03\x04", b"%PDF-", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
EXTENSIONS_TEXTE = ("txt", "csv")
_OCTETS_CONTROLE_MZ = 64
_OCTETS_TEXTE_COURANTS = frozenset(b"\t\n\r")


def _ressemble_a_un_executable_windows(entete):
    """« MZ » seul ne suffit pas (un code « MZ-001 » est un texte légitime) :
    il faut une vraie signature PE à l'offset e_lfanew (octets 0x3C-0x3F) ou,
    à défaut, des octets de contrôle dans les premiers octets."""
    if not entete.startswith(b"MZ"):
        return False
    if len(entete) >= 0x40:
        decalage = int.from_bytes(entete[0x3C:0x40], "little")
        if entete[decalage:decalage + 4] == b"PE\x00\x00":
            return True
    return any(
        octet < 0x20 and octet not in _OCTETS_TEXTE_COURANTS
        for octet in entete[:_OCTETS_CONTROLE_MZ]
    )


# Le PDF tolère quelques octets avant « %PDF- » : on cherche dans le début.
_OCTETS_LUS_ENTETE = 1024


@deconstructible
class ValidateurFichierTeleverse:
    """Valide un fichier téléversé : extension autorisée, taille maximale et,
    pour les images, contenu réellement décodable par Pillow.

    Utilisable directement comme `validators=[...]` sur un champ de modèle
    (propagé automatiquement aux ModelForm et aux ModelSerializer de DRF), ou
    appelé directement dans une vue qui lit `request.FILES` (voir
    `message_erreur_fichier` ci-dessous).
    """

    code = "fichier_televerse_invalide"

    def __init__(self, extensions_autorisees=EXTENSIONS_IMAGES, taille_max_octets=TAILLE_MAX_IMAGE, verifier_image=True):
        self.extensions_autorisees = tuple(e.lower() for e in extensions_autorisees)
        self.taille_max_octets = taille_max_octets
        self.verifier_image = verifier_image

    def __call__(self, fichier):
        nom = getattr(fichier, "name", "") or ""
        extension = nom.rsplit(".", 1)[-1].lower() if "." in nom else ""
        if extension not in self.extensions_autorisees:
            raise ValidationError(
                "Extension de fichier non autorisée « .%(extension)s ». Formats acceptés : %(formats)s."
                % {"extension": extension or "?", "formats": ", ".join(self.extensions_autorisees)},
                code=self.code,
            )

        taille = getattr(fichier, "size", None)
        if taille is not None and taille > self.taille_max_octets:
            raise ValidationError(
                "Fichier trop volumineux (%(taille)s Mo). Taille maximale autorisée : %(max)s Mo."
                % {
                    "taille": round(taille / (1024 * 1024), 1),
                    "max": round(self.taille_max_octets / (1024 * 1024), 1),
                },
                code=self.code,
            )

        if self.verifier_image and extension in EXTENSIONS_IMAGES:
            position = fichier.tell() if hasattr(fichier, "tell") else 0
            try:
                fichier.seek(0)
                Image.open(fichier).verify()
            except (UnidentifiedImageError, OSError, ValueError):
                raise ValidationError(
                    "Ce fichier n'est pas une image valide : son contenu ne correspond pas à son extension.",
                    code=self.code,
                )
            finally:
                # Image.verify() consomme le lecteur : on repositionne le
                # curseur pour que l'enregistrement du fichier par Django,
                # juste après, relise son contenu depuis le début.
                try:
                    fichier.seek(position or 0)
                except Exception:
                    pass
        elif self.verifier_image:
            self._verifier_entete_document(fichier, extension)

    def _verifier_entete_document(self, fichier, extension):
        """Vérifie que l'en-tête du document correspond à son extension."""
        position = fichier.tell() if hasattr(fichier, "tell") else 0
        try:
            fichier.seek(0)
            entete = fichier.read(_OCTETS_LUS_ENTETE)
        finally:
            try:
                fichier.seek(position or 0)
            except Exception:
                pass
        if not entete:
            raise ValidationError("Ce fichier est vide.", code=self.code)
        if extension in EXTENSIONS_TEXTE:
            conforme = not (
                entete.startswith(SIGNATURES_INTERDITES_TEXTE)
                or _ressemble_a_un_executable_windows(entete)
            )
        elif extension == "pdf":
            conforme = any(s in entete for s in SIGNATURES_DOCUMENTS["pdf"])
        elif extension in SIGNATURES_DOCUMENTS:
            conforme = entete.startswith(SIGNATURES_DOCUMENTS[extension])
        else:
            conforme = True
        if not conforme:
            raise ValidationError(
                "Ce fichier n'est pas un document « .%(extension)s » valide : son contenu ne correspond pas à son extension."
                % {"extension": extension},
                code=self.code,
            )

    def __eq__(self, other):
        return (
            isinstance(other, ValidateurFichierTeleverse)
            and self.extensions_autorisees == other.extensions_autorisees
            and self.taille_max_octets == other.taille_max_octets
            and self.verifier_image == other.verifier_image
        )

    def __hash__(self):
        return hash((self.extensions_autorisees, self.taille_max_octets, self.verifier_image))


# Instances prêtes à l'emploi pour les deux cas d'usage du projet : une photo
# (toujours une image) ou une pièce jointe/document (image ou bureautique).
valider_photo = ValidateurFichierTeleverse(EXTENSIONS_IMAGES, TAILLE_MAX_IMAGE, verifier_image=True)
valider_document = ValidateurFichierTeleverse(EXTENSIONS_DOCUMENTS, TAILLE_MAX_DOCUMENT, verifier_image=True)


def message_erreur_fichier(fichier, validateur=valider_photo):
    """Retourne le message d'erreur français si `fichier` ne passe pas
    `validateur`, sinon None.

    Sert aux vues qui lisent `request.FILES` directement plutôt que de passer
    par un ModelForm (le cas le plus fréquent dans ce projet) : elles peuvent
    ainsi afficher un message propre via le framework `messages` de Django et
    annuler l'enregistrement, au lieu de laisser remonter une erreur brute
    (ou pire, enregistrer un fichier non vérifié) lors de la soumission.
    """
    if not fichier:
        return None
    try:
        validateur(fichier)
    except ValidationError as exc:
        return " ".join(exc.messages)
    return None
