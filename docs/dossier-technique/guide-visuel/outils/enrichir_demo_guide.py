"""Complète la base de démonstration isolée avec quelques données fictives pour les captures du guide visuel.

Usage (depuis la racine de la copie de l'état B, avec l'environnement de preparer_instance_test.py) :
    python <chemin>/enrichir_demo_guide.py
Refuse de s'exécuter hors instance de démonstration marquée. Idempotent. Aucun code applicatif n'est modifié.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "matrix.settings")
sys.path.insert(0, os.getcwd())
import django

django.setup()
from django.conf import settings  # noqa: E402

base = Path(settings.DATABASES["default"]["NAME"])
if not (settings.DEBUG and os.environ.get("MATRIX_INSTANCE_DEMO") == "1" and base.with_name(base.name + ".instance_demo").exists()):
    sys.exit("Refus : base non marquée comme instance de démonstration.")

from django.contrib.auth import get_user_model  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from assets.models import Asset, AssetType, Deck, Location  # noqa: E402
from org.models import Sector, Ship  # noqa: E402
from postes.models import AffectationPoste, Poste  # noqa: E402
from training.models import TrainingCourse  # noqa: E402

User = get_user_model()
navire = Ship.objects.get(name="Bretagne")
secteur = Sector.objects.get(name="Moteurs", service__ship=navire, service__name="Propulsion")
service = secteur.service
chef = User.objects.get(username="chef_secteur_a")
section = secteur.sections.first()


def type_materiel(nom, categorie):
    return AssetType.objects.get_or_create(name=nom, sector=secteur, defaults={"category": categorie})[0]


MATERIELS = (
    ("Extincteur CO2 5 kg", "Extincteur", "Sécurité", "EXT-M01", "Local machine", 1, 24, 62, "OK"),
    ("Extincteur à poudre 9 kg", "Extincteur", "Sécurité", "EXT-M02", "Coursive bâbord", 1, 70, 40, "OK"),
    ("Multimètre de contrôle", "Instruments de mesure", "Mesure", "MES-014", "Atelier propulsion", 2, 45, 55, "OK"),
    ("Mégohmmètre d'isolement", "Instruments de mesure", "Mesure", "MES-021", "Atelier propulsion", 2, 52, 30, "FAULTY"),
    ("Pompe d'épuisement portable", "Pompe", "Auxiliaires", "PMP-07", "Local machine", 2, 33, 70, "OK"),
    ("Lampe torche étanche", "Éclairage", "Sécurité", "ECL-33", "Poste machine", 1, 60, 75, "OK"),
)
PONTS = (("Pont principal", 1), ("Pont inférieur", 2))
dossier_img = Path(settings.MEDIA_ROOT) / "deck_images"
dossier_img.mkdir(parents=True, exist_ok=True)
ponts = {}
for nom, ordre in PONTS:
    deck, _ = Deck.objects.get_or_create(ship=navire, name=nom, defaults={"order": ordre})
    chemin = dossier_img / f"fictif_{ordre}.png"
    im = Image.new("RGB", (1200, 420), "#eef2f6")
    d = ImageDraw.Draw(im)
    d.polygon([(40, 210), (260, 60), (1000, 60), (1160, 210), (1000, 360), (260, 360)], outline="#56667a", fill="#fbfcfd", width=4)
    for x in (360, 560, 760):
        d.line([(x, 60), (x, 360)], fill="#c3cbd6", width=3)
    d.text((70, 20), f"{nom} (plan fictif de démonstration)", fill="#2c3b4e")
    im.save(chemin)
    deck.image = f"deck_images/{chemin.name}"
    deck.save()
    ponts[ordre] = deck

for i, (des, typ, cat, ref, local, pont, x, y, statut) in enumerate(MATERIELS):
    Asset.objects.filter(designation=des, ship=navire, serial_number=f"FICTIF-{ref}").exists() or Asset.objects.create(
        designation=des, ship=navire, **dict(
            asset_type=type_materiel(typ, cat), location=Location.objects.get_or_create(ship=navire, name=local, parent=None)[0], internal_id=ref, serial_number=f"FICTIF-{ref}", local=local, gisement=f"Pont {pont}",
            service=service, sector=secteur, section=section, status=statut, criticality=2 if cat == "Mesure" else 1,
            plan_deck=ponts[pont], position_x=x, position_y=y, created_by=chef, updated_by=chef))

formation = TrainingCourse.objects.filter(title__icontains="incendie").first()
for intitule, eff, users in (
    ("Chef de quart machine", 1, ("chef_secteur_a",)),
    ("Opérateur machine", 2, ("equipier_a", "equipier_a2")),
    ("Mécanicien de ronde", 2, ("equipier_a",)),
):
    poste, cree = Poste.objects.get_or_create(intitule=intitule, ship=navire, service=service, sector=secteur,
                                              defaults={"effectif": eff, "created_by": chef, "updated_by": chef})
    if formation and cree:
        poste.formations.add(formation)
    for nom in users:
        AffectationPoste.objects.get_or_create(poste=poste, user=User.objects.get(username=nom), defaults={"affecte_par": chef})
print("Données fictives du guide prêtes :", Asset.objects.filter(ship=navire).count(), "matériels,", Deck.objects.filter(ship=navire).count(), "ponts,",
      Poste.objects.filter(ship=navire).count(), "postes.")
