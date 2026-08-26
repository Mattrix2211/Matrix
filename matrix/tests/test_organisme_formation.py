"""Tests de la tâche Notion « [FEAT] Modéliser un organisme de formation comme
une unité dédiée ».

Un organisme de formation (école, centre de formation) n'est PAS un nouveau
modèle : c'est simplement une Ship/« Unité » avec type_unite=ECOLE ou
CENTRE_FORMATION (cf. tâche préalable « Renommer Navire en Unité avec
typage »). Ces tests vérifient bout en bout que :
1. le parcours de création d'une unité de type école, avec sa propre
   hiérarchie Service/Secteur/Section, fonctionne exactement comme pour un
   navire (mécanisme générique déjà en place, non spécifique au type) ;
2. rien ne plante quand une unité de type école n'a aucune installation ni
   matériel mobile (relations optionnelles) ;
3. un ADMIN_NAVIRE rattaché à une école peut créer une formation via le
   mécanisme de permission déjà existant (RoleLevel.ADMIN_NAVIRE+), sans
   qu'aucune règle propre au type d'unité n'ait été ajoutée ;
4. les sélecteurs d'unité (accueil annuaire) et la liste des unités
   (Réglages) affichent un repère visuel (badge) par type, sans jamais
   exclure une unité école/centre de formation/bureau d'un sélecteur.
"""
from django.contrib.auth.models import User
from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from org.models import Section, Sector, Service, Ship
from training.models import TrainingCourse


class CreationEcoleAvecHierarchieTests(TestCase):
    """Une unité de type ÉCOLE se crée et se structure (Service/Secteur/
    Section) avec exactement le même formulaire des Réglages qu'un navire."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin_test", email="admin@navy.fr", password="pass",
        )
        self.client.login(username="admin_test", password="pass")

    def test_creation_ecole_puis_hierarchie_complete(self):
        settings_url = reverse("settings")

        # 1. Création de l'unité de type ÉCOLE.
        r = self.client.post(settings_url, {
            "action": "add_ship",
            "name": "École de Maistrance",
            "code": "EM",
            "type_unite": "ECOLE",
            "next_tab": "navires",
        })
        self.assertEqual(r.status_code, 302)
        ecole = Ship.objects.get(code="EM")
        self.assertEqual(ecole.type_unite, "ECOLE")

        # 2. Ajout d'un service, exactement le même mécanisme générique que
        # pour un navire (aucune restriction par type_unite).
        r = self.client.post(settings_url, {
            "action": "add_service",
            "name": "Formation initiale",
            "ship_id": ecole.id,
            "next_tab": "hierarchie",
        })
        self.assertEqual(r.status_code, 302)
        service = Service.objects.get(ship=ecole, name="Formation initiale")

        # 3. Ajout d'un secteur rattaché à ce service.
        r = self.client.post(settings_url, {
            "action": "add_sector",
            "name": "Filière mécanique",
            "service_id": service.id,
            "next_tab": "hierarchie",
        })
        self.assertEqual(r.status_code, 302)
        secteur = Sector.objects.get(service=service, name="Filière mécanique")

        # 4. Ajout d'une section rattachée à ce secteur.
        r = self.client.post(settings_url, {
            "action": "add_section",
            "name": "Promotion 2026",
            "sector_id": secteur.id,
            "next_tab": "hierarchie",
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Section.objects.filter(sector=secteur, name="Promotion 2026").exists())

    def test_onglet_hierarchie_liste_bien_lecole_dans_le_selecteur(self):
        ecole = Ship.objects.create(name="Centre Cherbourg", code="CC", type_unite="CENTRE_FORMATION")
        r = self.client.get(reverse("settings"), {"tab": "hierarchie", "ship": ecole.id})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Centre Cherbourg")
        # Regroupement par type (optgroup) : l'école doit apparaître dans son
        # propre groupe, sans être exclue du sélecteur.
        self.assertContains(r, '<optgroup label="Centre de formation">')


class EcoleSansInstallationNiMaterielTests(TestCase):
    """Une unité ÉCOLE sans aucune installation ni matériel mobile ne doit
    faire planter aucun écran courant (relations optionnelles)."""

    def setUp(self):
        self.ecole = Ship.objects.create(name="École Navale", code="ENAV", type_unite="ECOLE")
        self.user = User.objects.create_user(username="marin_ecole", password="pass")
        UserProfile.objects.update_or_create(
            user=self.user, defaults={"role": "EQUIPIER", "ship": self.ecole},
        )
        self.client.login(username="marin_ecole", password="pass")

    def test_tableau_de_bord_ne_plante_pas(self):
        r = self.client.get(reverse("home"))
        self.assertEqual(r.status_code, 200)

    def test_liste_materiel_ne_plante_pas(self):
        r = self.client.get(reverse("asset-list"))
        self.assertEqual(r.status_code, 200)

    def test_liste_installations_ne_plante_pas(self):
        r = self.client.get(reverse("installation-list"))
        self.assertEqual(r.status_code, 200)

    def test_liste_formations_ne_plante_pas(self):
        r = self.client.get(reverse("formation-list"))
        self.assertEqual(r.status_code, 200)


class CreationFormationParAdminEcoleTests(TestCase):
    """Un ADMIN_NAVIRE rattaché à une école crée une formation par le
    mécanisme de permission déjà existant (RoleLevel.ADMIN_NAVIRE+, cf.
    training/web_views.py::NIVEAU_REQUIS_CREATION_FORMATION) — aucune règle
    propre au type d'unité n'a été ajoutée ni n'est nécessaire."""

    def setUp(self):
        self.ecole = Ship.objects.create(name="Centre de formation Brest", code="CFB", type_unite="CENTRE_FORMATION")
        self.admin = User.objects.create_user(username="admin_ecole", password="pass")
        UserProfile.objects.update_or_create(
            user=self.admin, defaults={"role": "ADMIN_NAVIRE", "ship": self.ecole},
        )
        self.client.login(username="admin_ecole", password="pass")

    def test_admin_navire_dune_ecole_peut_creer_une_formation(self):
        r = self.client.post(reverse("formation-list"), {
            "action": "create_course",
            "title": "Sécurité incendie niveau 1",
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(TrainingCourse.objects.filter(title="Sécurité incendie niveau 1").exists())


class BadgeEtGroupementTypeUniteTests(TestCase):
    """Le filtre badge_type_unite et le tag unites_groupees_par_type (org/
    templatetags/org_extras.py) fournissent le repère visuel demandé sans
    jamais exclure d'unité."""

    def setUp(self):
        self.navire = Ship.objects.create(name="Richelieu", code="RIC", type_unite="NAVIRE")
        self.ecole = Ship.objects.create(name="École de Maistrance", code="EM", type_unite="ECOLE")
        self.centre = Ship.objects.create(name="Centre Cherbourg", code="CC", type_unite="CENTRE_FORMATION")
        self.bureau = Ship.objects.create(name="Bureau Toulon", code="BT", type_unite="BUREAU")

    def _rendu(self, template_str, **contexte):
        return Template(template_str).render(Context(contexte))

    def test_badge_affiche_icone_et_libelle_pour_chaque_type(self):
        rendu = self._rendu(
            "{% load org_extras %}{{ unite|badge_type_unite }}", unite=self.ecole,
        )
        self.assertIn("badge", rendu)
        self.assertIn("École", rendu)
        self.assertIn("bi-mortarboard-fill", rendu)

    def test_badge_vide_si_aucune_unite(self):
        rendu = self._rendu("{% load org_extras %}[{{ unite|badge_type_unite }}]", unite=None)
        self.assertEqual(rendu, "[]")

    def test_groupement_ne_perd_aucune_unite(self):
        toutes = [self.navire, self.ecole, self.centre, self.bureau]
        rendu = self._rendu(
            "{% load org_extras %}"
            "{% unites_groupees_par_type unites as groupes %}"
            "{% for libelle, liste in groupes %}{{ libelle }}:{% for u in liste %}{{ u.name }},{% endfor %}|{% endfor %}",
            unites=toutes,
        )
        for unite in toutes:
            self.assertIn(unite.name, rendu)
        # Ordre : Navire, École, Centre de formation, Bureau (ordre des choix
        # du modèle), pour un regroupement lisible dans les <optgroup>.
        self.assertLess(rendu.index("Navire"), rendu.index("École"))
        self.assertLess(rendu.index("École"), rendu.index("Centre de formation"))
        self.assertLess(rendu.index("Centre de formation"), rendu.index("Bureau"))

    def test_annuaire_regroupe_les_unites_par_type_dans_le_selecteur(self):
        superuser = User.objects.create_superuser(username="su", email="su@navy.fr", password="pass")
        self.client.login(username="su", password="pass")
        r = self.client.get(reverse("user-directory"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '<optgroup label="École">')
        self.assertContains(r, "École de Maistrance")

    def test_annuaire_affiche_le_badge_de_lunite_dun_marin(self):
        superuser = User.objects.create_superuser(username="su2", email="su2@navy.fr", password="pass")
        marin = User.objects.create_user(username="etudiant", password="pass")
        UserProfile.objects.update_or_create(user=marin, defaults={"role": "EQUIPIER", "ship": self.ecole})
        self.client.login(username="su2", password="pass")
        r = self.client.get(reverse("user-directory"))
        self.assertContains(r, "bi-mortarboard-fill")
