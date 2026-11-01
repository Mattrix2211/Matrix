"""Vocabulaire visible : le niveau d'organisation réel (secteur, service, section, bâtiment) remplace « périmètre » ;
teintes provisoires du bandeau et leurs contrastes."""
import ast
import re
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounts.models import UserProfile
from matrix.core.organisation import niveau_de, votre_niveau
from org.models import Sector, Section, Service, Ship


class NiveauDeTests(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Frégate", code="FRG")
        self.service = Service.objects.create(ship=self.navire, name="Propulsion")
        self.secteur = Sector.objects.create(service=self.service, name="Moteurs")
        self.section = Section.objects.create(sector=self.secteur, name="Moteurs bâbord")

    def _marin(self, nom, role="EQUIPIER", **champs):
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={"role": role, **champs})
        return User.objects.get(pk=user.pk)

    def test_niveau_selon_le_rattachement_le_plus_precis(self):
        cas = (
            ({"ship": self.navire}, "votre bâtiment", "Bâtiment", "Tout le bâtiment", "Mon bâtiment"),
            ({"ship": self.navire, "service": self.service}, "votre service", "Service", "Tout le service", "Mon service"),
            ({"ship": self.navire, "service": self.service, "sector": self.secteur}, "votre secteur", "Secteur", "Tout le secteur", "Mon secteur"),
            ({"ship": self.navire, "service": self.service, "sector": self.secteur, "section": self.section},
             "votre section", "Section", "Toute la section", "Ma section"),
        )
        for i, (champs, votre, libelle, tout, mon) in enumerate(cas):
            niveau = niveau_de(self._marin(f"m{i}", **champs))
            self.assertEqual((niveau["votre"], niveau["libelle"], niveau["tout"], niveau["mon"]), (votre, libelle, tout, mon))

    def test_accords_et_nom(self):
        niveau = niveau_de(self._marin("chef", "CHEF_SECTEUR", ship=self.navire, service=self.service, sector=self.secteur), avec_nom=True)
        self.assertEqual((niveau["du"], niveau["de_votre"], niveau["nom"]), ("du secteur", "de votre secteur", "Moteurs"))
        section = niveau_de(self._marin("sec", ship=self.navire, service=self.service, sector=self.secteur, section=self.section))
        self.assertEqual((section["du"], section["le"]), ("de la section", "la section"))

    def test_sans_rattachement_repli_neutre_sans_inventer_de_niveau(self):
        self.assertEqual(votre_niveau(self._marin("libre")), "votre rattachement")

    def test_accueil_du_chef_de_secteur_parle_de_son_secteur(self):
        self._marin("chef2", "CHEF_SECTEUR", ship=self.navire, service=self.service, sector=self.secteur)
        self.client.login(username="chef2", password="pass")
        page = self.client.get(reverse("home")).content.decode()
        self.assertIn("Mon secteur", page)
        self.assertIn("Bilan du secteur", page)
        self.assertIn("Secteur : Moteurs", page)
        self.assertNotRegex(page, r"[Pp]érimètre")

    def test_accueil_du_commandant_parle_du_batiment(self):
        self._marin("cdt", "COMMANDANT", ship=self.navire)
        self.client.login(username="cdt", password="pass")
        page = self.client.get(reverse("home")).content.decode()
        self.assertNotRegex(page, r"[Pp]érimètre")

    def test_listes_de_tickets_et_d_anomalies(self):
        self._marin("chef3", "CHEF_SECTION", ship=self.navire, service=self.service, sector=self.secteur, section=self.section)
        self.client.login(username="chef3", password="pass")
        tickets = self.client.get(reverse("ticket-list")).content.decode()
        self.assertIn("Toute la section", tickets)
        self.assertNotRegex(tickets, r"[Pp]érimètre")
        self.assertNotRegex(self.client.get(reverse("anomalie-list")).content.decode(), r"[Pp]érimètre")


class AucunPerimetreVisibleTests(SimpleTestCase):
    """Garde : plus aucune phrase « votre périmètre » ou « Périmètre » en libellé dans les textes visibles (le périmètre
    d'autorisation technique, lui, garde son nom dans le code)."""

    RACINE = Path(settings.BASE_DIR)
    IGNORES = {"venv", "tests", "migrations", "node_modules", "design", "docs", "staticfiles", ".git"}

    def _fichiers(self, suffixe):
        return [p for p in self.RACINE.rglob(f"*{suffixe}") if not self.IGNORES & set(p.relative_to(self.RACINE).parts)]

    def test_aucune_chaine_python_ne_dit_votre_perimetre(self):
        fautes = []
        for chemin in self._fichiers(".py"):
            for noeud in ast.walk(ast.parse(chemin.read_text(encoding="utf-8"))):
                if isinstance(noeud, ast.Constant) and isinstance(noeud.value, str) and re.search(r"votre périmètre", noeud.value):
                    fautes.append(f"{chemin.relative_to(self.RACINE)}:{noeud.lineno}")
        self.assertEqual(fautes, [])

    def test_aucun_gabarit_ne_dit_perimetre_en_libelle(self):
        motif = re.compile(r"(votre périmètre|>\s*Périmètre\s*<|Mon périmètre|Tout le périmètre|Bilan du périmètre)")
        fautes = [str(p.relative_to(self.RACINE)) for p in self._fichiers(".html") if motif.search(p.read_text(encoding="utf-8"))]
        self.assertEqual(fautes, [])


def _luminance(hexa):
    r, g, b = (int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _contraste(a, b):
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class BandeauTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="marin", password="pass")
        self.client.login(username="marin", password="pass")
        self.css = (Path(settings.BASE_DIR) / "matrix/static/css/naval_premium.css").read_text(encoding="utf-8")

    def test_teinte_ardoise_retenue_et_identique_dans_les_deux_themes(self):
        self.assertIn("--bandeau-fond: #344A63", self.css)
        self.assertNotIn("#536F80", self.css)  # variante acier écartée
        self.assertNotIn("data-bandeau", self.css)
        self.assertNotRegex(self.css, r"\[data-theme=\"sombre\"\][^{]*\.mx-barre")  # aucune teinte propre au thème sombre
        page = self.client.get(reverse("home")).content.decode()
        self.assertNotIn("data-bandeau", page)

    def test_contrastes_du_texte_au_moins_4_5_pour_1(self):
        fond = "#344A63"
        self.assertGreaterEqual(_contraste("#FFFFFF", fond), 4.5)
        self.assertGreaterEqual(_contraste("#F2F6F9", fond), 4.5)
        champ = "#%02X%02X%02X" % tuple(round(c * 0.84 + 255 * 0.16) for c in (0x34, 0x4A, 0x63))  # champ translucide composé
        self.assertGreaterEqual(_contraste("#F2F6F9", champ), 4.5)

    def test_recherche_centree_et_fonctions_conservees(self):
        page = self.client.get(reverse("home")).content.decode()
        for marque in ('class="mx-barre__gauche"', "mx-recherche", "centre-notifications", "Déconnexion", "theme-toggle"):
            self.assertIn(marque, page)
        self.assertRegex(self.css, r"\.mx-barre \.mx-recherche \{[^}]*margin: 0 auto")


class TableauEnCartesTests(TestCase):
    def test_la_liste_des_demandes_se_replie_en_cartes_sur_mobile(self):
        gabarit = (Path(settings.BASE_DIR) / "matrix/templates/demandes/_liste.html").read_text(encoding="utf-8")
        for libelle in ("Demande", "Sur", "Responsable", "État"):
            self.assertIn(f'data-libelle="{libelle}"', gabarit)
        css = (Path(settings.BASE_DIR) / "matrix/static/css/naval_premium.css").read_text(encoding="utf-8")
        self.assertIn(".mx-table-cartes td { padding", css)
        self.assertIn("overflow-wrap: anywhere", css)
