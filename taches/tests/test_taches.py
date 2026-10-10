"""Tâches : attribution par un chef, blocage, fil contextuel, compte rendu, calendrier et « Aujourd'hui »."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.aujourdhui import a_faire
from notifications.models import Notification
from org.models import Sector, Service, Ship
from taches import services
from taches.models import Tache
from threads.utils import commentaires_de


class TachesBase(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="FREMM tâches", code="FT", double_equipage=True, equipage_a_bord="A")
        service = Service.objects.create(ship=self.navire, name="Énergie")
        self.secteur = Sector.objects.create(service=service, name="Propulsion")
        autre = Sector.objects.create(service=service, name="Électricité")
        self.chef = self._marin("chef", self.secteur, "CHEF_SECTION", "A")
        self.marin = self._marin("marin", self.secteur, "EQUIPIER", "A")
        self.voisin = self._marin("voisin", autre, "EQUIPIER", "A")
        self.terre = self._marin("terre", autre, "EQUIPIER", "B")
        autre_navire = Ship.objects.create(name="Autre bâtiment", code="AB")
        self.etranger = self._marin("etranger", None, "EQUIPIER", "", navire=autre_navire)
        self.aujourdhui = timezone.localdate()

    def _marin(self, nom, secteur, role, equipage, navire=None):
        user = User.objects.create_user(username=nom, password="pass")
        profil = user.profile
        profil.role, profil.sector, profil.equipage = role, secteur, equipage
        profil.ship = navire or self.navire
        if secteur:
            profil.service = secteur.service
        profil.save()
        return user

    def _tache(self, **kw):
        defauts = dict(titre="Contrôler la pompe", echeance=self.aujourdhui, assigne=self.marin, created_by=self.chef)
        return Tache.objects.create(**{**defauts, **kw})

    def post(self, user, nom, args, donnees):
        self.client.login(username=user, password="pass")
        return self.client.post(reverse(nom, args=args), donnees)


class ParcoursTests(TachesBase):
    def test_parcours_complet(self):
        self.client.login(username="chef", password="pass")
        r = self.client.post(reverse("taches-index"), {
            "titre": "Contrôler la pompe", "assigne": self.marin.pk, "echeance": self.aujourdhui.isoformat(),
        })
        tache = Tache.objects.get()
        self.assertRedirects(r, reverse("tache-detail", args=[tache.pk]))
        self.assertTrue(Notification.objects.filter(user=self.marin, object_id=str(tache.pk)).exists())

        self.assertEqual([e["objet"] for e in a_faire(self.marin, self.aujourdhui)], [tache])

        self.post("marin", "tache-action", [tache.pk], {"action": "demarrer"})
        self.post("marin", "tache-action", [tache.pk], {"action": "bloquer", "motif": "Vanne grippée"})
        tache.refresh_from_db()
        self.assertEqual(tache.statut, Tache.STATUT_BLOQUEE)
        self.assertTrue(Notification.objects.filter(user=self.chef, verb__contains="Vanne grippée").exists())
        entrees_chef = a_faire(self.chef, self.aujourdhui)
        self.assertIn("Blocage à lever", [e["detail"] for e in entrees_chef if e["objet"] == tache][0])

        self.post("chef", "tache-action", [tache.pk], {"action": "interlocuteur", "interlocuteur": self.terre.pk})
        self.post("terre", "tache-commentaire", [tache.pk], {"body": "Utilisez le dégrippant."})
        self.assertTrue(Notification.objects.filter(user=self.marin, verb__contains="a répondu").exists())
        self.post("chef", "tache-action", [tache.pk], {"action": "reprendre"})
        self.post("marin", "tache-action", [tache.pk], {"action": "rendre_compte", "compte_rendu": "Vanne dégrippée."})
        tache.refresh_from_db()
        self.assertEqual(tache.statut, Tache.STATUT_TERMINEE)
        self.assertTrue(Notification.objects.filter(user=self.chef, verb__contains="rendu compte").exists())
        self.assertEqual(commentaires_de(tache).filter(author=self.terre).count(), 1)
        self.assertEqual(a_faire(self.marin, self.aujourdhui), [])

    def test_tache_au_calendrier_du_marin(self):
        tache = self._tache()
        self.client.login(username="marin", password="pass")
        debut = (self.aujourdhui - timedelta(days=1)).isoformat()
        fin = (self.aujourdhui + timedelta(days=1)).isoformat()
        r = self.client.get(reverse("calendar-events"), {"start": debut, "end": fin})
        self.assertIn(f"tch-{tache.pk}", [e["id"] for e in r.json()])


class PermissionsTests(TachesBase):
    def test_marin_ne_peut_pas_attribuer(self):
        r = self.post("marin", "taches-index", [], {
            "titre": "x", "assigne": self.voisin.pk, "echeance": self.aujourdhui.isoformat(),
        })
        self.assertEqual(Tache.objects.count(), 0)
        self.assertEqual(r.status_code, 302)

    def test_chef_ne_peut_pas_attribuer_hors_perimetre_ni_hors_equipage(self):
        for cible in (self.voisin, self.terre, self.etranger):
            self.post("chef", "taches-index", [], {
                "titre": "x", "assigne": cible.pk, "echeance": self.aujourdhui.isoformat(),
            })
        self.assertEqual(Tache.objects.count(), 0)

    def test_tache_invisible_hors_dossier(self):
        tache = self._tache()
        for nom in ("voisin", "terre", "etranger"):
            self.client.login(username=nom, password="pass")
            self.assertEqual(self.client.get(reverse("tache-detail", args=[tache.pk])).status_code, 404, nom)
            self.assertEqual(self.client.post(reverse("tache-commentaire", args=[tache.pk]), {"body": "x"}).status_code, 404, nom)

    def test_seul_l_assigne_bloque_et_rend_compte(self):
        tache = self._tache()
        self.post("chef", "tache-action", [tache.pk], {"action": "bloquer", "motif": "x"})
        self.post("chef", "tache-action", [tache.pk], {"action": "rendre_compte", "compte_rendu": "x"})
        tache.refresh_from_db()
        self.assertEqual(tache.statut, Tache.STATUT_A_FAIRE)

    def test_interlocuteur_d_un_autre_navire_refuse(self):
        tache = self._tache()
        self.post("chef", "tache-action", [tache.pk], {"action": "interlocuteur", "interlocuteur": self.etranger.pk})
        self.assertFalse(tache.participants.exists())

    def test_interlocuteur_a_terre_repond_mais_ne_modifie_rien(self):
        tache = self._tache()
        tache.participants.add(self.terre)
        r = self.post("terre", "tache-commentaire", [tache.pk], {"body": "Conseil"})
        self.assertEqual(r.status_code, 302)
        r = self.post("terre", "tache-action", [tache.pk], {"action": "reprendre"})
        self.assertEqual(r.status_code, 403)
        r = self.post("terre", "taches-index", [], {"titre": "x", "assigne": self.marin.pk, "echeance": "2026-01-01"})
        self.assertEqual(r.status_code, 403)

    def test_interlocuteur_non_ajoute_ne_voit_pas_le_fil_a_terre(self):
        tache = self._tache()
        r = self.post("terre", "tache-commentaire", [tache.pk], {"body": "x"})
        self.assertEqual(r.status_code, 404)


class AffichageTests(TachesBase):
    def test_pages_s_affichent_pour_chaque_acteur(self):
        tache = self._tache(statut=Tache.STATUT_BLOQUEE, motif_blocage="Vanne grippée")
        tache.participants.add(self.terre)
        attendus = {"chef": "Lever le blocage", "marin": "Rendre compte", "terre": "Vanne grippée"}
        for nom, texte in attendus.items():
            self.client.login(username=nom, password="pass")
            self.assertContains(self.client.get(reverse("taches-index")), "Tâches")
            self.assertContains(self.client.get(reverse("tache-detail", args=[tache.pk])), texte)
        self.assertNotContains(self.client.get(reverse("tache-detail", args=[tache.pk])), "Lever le blocage")


class RelanceEcheanceTests(TachesBase):
    def relances(self, user):
        return Notification.objects.filter(user=user, verb__startswith=services.PREFIXE_RELANCE)

    def test_relance_unique_par_jour_meme_si_lue(self):
        self._tache(echeance=self.aujourdhui - timedelta(days=2))
        self.assertEqual(services.relancer_echeances_depassees(), 2)
        self.assertEqual(services.relancer_echeances_depassees(), 0)
        Notification.objects.filter(verb__startswith=services.PREFIXE_RELANCE).update(is_read=True)
        self.assertEqual(services.relancer_echeances_depassees(), 0)
        self.assertEqual(self.relances(self.marin).count(), 1)
        self.assertEqual(self.relances(self.chef).count(), 1)

    def test_nouvelle_relance_le_lendemain_si_non_traitee(self):
        self._tache(echeance=self.aujourdhui - timedelta(days=1))
        services.relancer_echeances_depassees()
        self.relances(self.marin).update(is_read=True)
        self.assertEqual(services.relancer_echeances_depassees(self.aujourdhui + timedelta(days=1)), 2)
        self.assertEqual(self.relances(self.marin).count(), 2)

    def test_pas_de_relance_pour_echeance_future_ou_tache_close(self):
        self._tache(echeance=self.aujourdhui)
        self._tache(echeance=self.aujourdhui - timedelta(days=1), statut=Tache.STATUT_TERMINEE)
        self.assertEqual(services.relancer_echeances_depassees(), 0)

    def test_blocage_en_retard_releve_les_chefs_du_perimetre_pas_le_marin(self):
        self._tache(echeance=self.aujourdhui - timedelta(days=1), statut=Tache.STATUT_BLOQUEE, motif_blocage="Vanne")
        self.assertEqual(services.relancer_echeances_depassees(), 1)
        self.assertEqual(self.relances(self.chef).count(), 1)
        self.assertIn("(bloquée)", self.relances(self.chef).get().verb)
        self.assertFalse(self.relances(self.marin).exists())

    def test_relances_soldees_quand_la_tache_est_traitee(self):
        tache = self._tache(echeance=self.aujourdhui - timedelta(days=1))
        services.relancer_echeances_depassees()
        services.rendre_compte(tache, self.marin, "Fait.")
        services.relancer_echeances_depassees()
        self.assertFalse(Notification.objects.filter(verb__startswith=services.PREFIXE_RELANCE, is_read=False).exists())


class AvancementTests(TachesBase):
    def test_synthese_du_chef(self):
        hier = self.aujourdhui - timedelta(days=1)
        self._tache(statut=Tache.STATUT_EN_COURS)
        retard = self._tache(echeance=hier)
        bloquee = self._tache(statut=Tache.STATUT_BLOQUEE, motif_blocage="Vanne grippée")
        self._tache(statut=Tache.STATUT_TERMINEE, terminee_le=timezone.now())
        self._tache(statut=Tache.STATUT_TERMINEE, terminee_le=timezone.now() - timedelta(days=45))
        self._tache(assigne=self.voisin)
        a = services.avancement_equipe(self.chef)
        self.assertEqual(a["comptes"], {"A_FAIRE": 1, "EN_COURS": 1, "BLOQUEE": 1, "TERMINEE": 1})
        self.assertEqual(a["total"], 4)
        self.assertEqual(a["retards"], [retard])
        self.assertEqual(a["blocages"], [bloquee])

    def test_marin_sans_vue_equipe_et_pas_de_ses_propres_taches(self):
        self._tache()
        self.assertEqual(services.avancement_equipe(self.marin)["total"], 0)
        self._tache(assigne=self.chef, created_by=self.chef)
        self.assertEqual(services.avancement_equipe(self.chef)["total"], 1)

    def test_page_affiche_la_vue_au_chef_seulement(self):
        self._tache(statut=Tache.STATUT_BLOQUEE, motif_blocage="Vanne grippée")
        self.client.login(username="chef", password="pass")
        self.assertContains(self.client.get(reverse("taches-index")), "Blocages à lever")
        self.client.login(username="marin", password="pass")
        self.assertNotContains(self.client.get(reverse("taches-index")), "Avancement de l'équipe")
