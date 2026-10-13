"""Tâches : checklist, pièces jointes, attribution à une unité, recherche universelle."""
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from accounts.models import AuditLog
from matrix.core import recherche
from notifications.models import Notification
from org.models import Section
from taches import services
from taches.models import ElementChecklistTache, LotTaches, PieceJointeTache, Tache
from taches.tests.test_taches import TachesBase

PDF = b"%PDF-1.4\n%contenu de test\n"


class ChecklistTests(TachesBase):
    def setUp(self):
        super().setUp()
        self.tache = self._tache()

    def action(self, user, donnees):
        return self.post(user, "tache-action", [self.tache.pk], donnees)

    def test_assigne_ajoute_coche_et_avancement_affiche(self):
        self.action("marin", {"action": "checklist_ajouter", "texte": "Couper l'alimentation"})
        self.action("marin", {"action": "checklist_ajouter", "texte": "Ouvrir le capot"})
        premier = self.tache.elements_checklist.first()
        self.action("marin", {"action": "checklist_basculer", "element": premier.pk})
        self.assertEqual(Tache.objects.get().avancement_checklist, (1, 2))
        self.assertContains(self.client.get(reverse("tache-detail", args=[self.tache.pk])), "1/2")
        self.assertContains(self.client.get(reverse("taches-index")), "1/2")
        self.assertTrue(AuditLog.objects.filter(action="tache_checklist_fait").exists())

    def test_createur_peut_editer_mais_pas_un_autre_chef_ni_un_voisin(self):
        self.action("chef", {"action": "checklist_ajouter", "texte": "Point du chef"})
        self.assertEqual(self.tache.elements_checklist.count(), 1)
        self.action("voisin", {"action": "checklist_ajouter", "texte": "Intrus"})
        self.assertEqual(self.tache.elements_checklist.count(), 1)

    def test_tache_terminee_ou_privee_d_autrui_refusee(self):
        privee = self._tache(assigne=self.voisin, created_by=self.voisin, partagee=False)
        r = self.post("marin", "tache-action", [privee.pk], {"action": "checklist_ajouter", "texte": "x"})
        self.assertEqual(r.status_code, 404)
        self.assertFalse(privee.elements_checklist.exists())
        self.tache.statut = Tache.STATUT_TERMINEE
        self.tache.save()
        self.action("marin", {"action": "checklist_ajouter", "texte": "Trop tard"})
        self.assertFalse(self.tache.elements_checklist.exists())

    def test_element_d_une_autre_tache_introuvable(self):
        autre = self._tache(titre="Autre")
        element = ElementChecklistTache.objects.create(tache=autre, texte="Autre")
        r = self.action("marin", {"action": "checklist_basculer", "element": element.pk})
        self.assertEqual(r.status_code, 404)
        element.refresh_from_db()
        self.assertFalse(element.fait)

    def test_identifiant_invalide_donne_404(self):
        self.assertEqual(self.action("marin", {"action": "checklist_basculer", "element": "abc"}).status_code, 404)

    def test_creation_avec_checklist_initiale_et_aujourdhui(self):
        self.client.login(username="chef", password="pass")
        self.client.post(reverse("taches-index"), {
            "titre": "Visite", "assigne": self.marin.pk, "checklist": "Un\n\n  Deux  \nTrois"})
        tache = Tache.objects.get(titre="Visite")
        self.assertEqual(list(tache.elements_checklist.values_list("texte", flat=True)), ["Un", "Deux", "Trois"])
        from dashboard.aujourdhui import a_faire
        detail = [e["detail"] for e in a_faire(self.marin, self.aujourdhui) if e["objet"] == tache][0]
        self.assertIn("checklist 0/3", detail)

    def test_equipage_a_terre_ne_modifie_pas(self):
        tache = self._tache(assigne=self.terre)
        r = self.post("terre", "tache-action", [tache.pk], {"action": "checklist_ajouter", "texte": "x"})
        self.assertEqual(r.status_code, 403)
        self.assertFalse(tache.elements_checklist.exists())


class PiecesJointesTests(TachesBase):
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        surcharge = override_settings(MEDIA_ROOT=self.media)
        surcharge.enable()
        self.addCleanup(surcharge.disable)
        self.tache = self._tache()

    def joindre(self, user, fichier, tache=None):
        self.client.login(username=user, password="pass")
        return self.client.post(reverse("tache-action", args=[(tache or self.tache).pk]), {"action": "joindre", "fichier": fichier})

    def test_joindre_telecharger_et_supprimer(self):
        self.joindre("marin", SimpleUploadedFile("consigne.pdf", PDF))
        piece = PieceJointeTache.objects.get()
        self.assertEqual(piece.created_by, self.marin)
        r = self.client.get(reverse("tache-piece-jointe", args=[self.tache.pk, piece.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(b"".join(r.streaming_content), PDF)
        self.assertEqual(r["X-Content-Type-Options"], "nosniff")
        self.assertIn("attachment", r["Content-Disposition"])
        # Le créateur de la tâche supprime le fichier d'un autre ; un étranger n'y a pas accès.
        self.post("voisin", "tache-action", [self.tache.pk], {"action": "piece_supprimer", "piece": piece.pk})
        self.assertTrue(PieceJointeTache.objects.exists())
        self.post("chef", "tache-action", [self.tache.pk], {"action": "piece_supprimer", "piece": piece.pk})
        self.assertFalse(PieceJointeTache.objects.exists())
        self.assertTrue(AuditLog.objects.filter(action="tache_piece_jointe_suppression").exists())

    def test_extension_interdite_et_faux_pdf_refuses(self):
        self.joindre("marin", SimpleUploadedFile("virus.exe", b"MZ\x90\x00"))
        self.joindre("marin", SimpleUploadedFile("faux.png", b"pas une image"))
        self.joindre("marin", SimpleUploadedFile("faux.pdf", b"MZ\x90\x00 pas un pdf"))
        self.assertFalse(PieceJointeTache.objects.exists())

    @override_settings(DOCUMENT_TAILLE_MAX_MO=1)
    def test_fichier_trop_gros_refuse(self):
        self.joindre("marin", SimpleUploadedFile("gros.pdf", PDF + b"0" * (1024 * 1024 + 1)))
        self.assertFalse(PieceJointeTache.objects.exists())

    def test_telechargement_refuse_sans_droit_de_consultation(self):
        self.joindre("marin", SimpleUploadedFile("consigne.pdf", PDF))
        piece = PieceJointeTache.objects.get()
        self.client.login(username="voisin", password="pass")
        self.assertEqual(self.client.get(reverse("tache-piece-jointe", args=[self.tache.pk, piece.pk])).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("tache-piece-jointe", args=[self.tache.pk, piece.pk])).status_code, 302)

    def test_piece_d_une_autre_tache_introuvable_via_cette_tache(self):
        autre = self._tache(titre="Autre")
        self.joindre("marin", SimpleUploadedFile("a.pdf", PDF), tache=autre)
        piece = PieceJointeTache.objects.get()
        r = self.client.get(reverse("tache-piece-jointe", args=[self.tache.pk, piece.pk]))
        self.assertEqual(r.status_code, 404)

    def test_joindre_refuse_a_un_non_participant_et_a_terre(self):
        self.joindre("voisin", SimpleUploadedFile("a.pdf", PDF))
        tache_terre = self._tache(assigne=self.terre)
        r = self.joindre("terre", SimpleUploadedFile("a.pdf", PDF), tache=tache_terre)
        self.assertEqual(r.status_code, 403)
        self.assertFalse(PieceJointeTache.objects.exists())


class AttributionUniteTests(TachesBase):
    def setUp(self):
        super().setUp()
        self.s1 = Section.objects.create(sector=self.secteur, name="Section 1")
        self.s2 = Section.objects.create(sector=self.secteur, name="Section 2")
        self.s_voisin = Section.objects.create(sector=self.voisin.profile.sector, name="Section voisine")
        self.marin2 = self._marin("marin2", self.secteur, "EQUIPIER", "A")
        self.marin3 = self._marin("marin3", self.secteur, "EQUIPIER", "A")
        self.marin_b = self._marin("marin_b", self.secteur, "EQUIPIER", "B")
        for user, section in ((self.marin, self.s1), (self.marin2, self.s1), (self.marin3, self.s2),
                              (self.marin_b, self.s1), (self.voisin, self.s_voisin)):
            user.profile.section = section
            user.profile.save()

    def test_une_tache_par_marin_de_la_section_avec_lot_et_notifications(self):
        lot, taches = services.attribuer_a_unite(self.chef, f"section:{self.s1.pk}", "Ranger le local", elements=["Balayer"])
        self.assertEqual({t.assigne for t in taches}, {self.marin, self.marin2})  # équipage B et autre section exclus
        self.assertTrue(all(t.lot == lot and not t.personnelle for t in taches))
        self.assertEqual(Tache.objects.filter(lot=lot).count(), 2)
        self.assertEqual(ElementChecklistTache.objects.filter(tache__lot=lot).count(), 2)
        for marin in (self.marin, self.marin2):
            self.assertEqual(Notification.objects.filter(user=marin, verb__contains="Ranger le local").count(), 1)
        self.assertTrue(AuditLog.objects.filter(action="tache_attribution_unite").exists())

    def test_section_hors_perimetre_refusee(self):
        with self.assertRaises(PermissionError):
            services.attribuer_a_unite(self.chef, f"section:{self.s_voisin.pk}", "x")
        with self.assertRaises(PermissionError):
            services.attribuer_a_unite(self.chef, "section:99999", "x")
        self.assertFalse(Tache.objects.exists())
        self.assertFalse(LotTaches.objects.exists())

    def test_unite_invalide_et_marin_sans_droit(self):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            services.attribuer_a_unite(self.chef, "navire:1", "x")
        with self.assertRaises(PermissionError):
            services.attribuer_a_unite(self.marin, f"section:{self.s1.pk}", "x")

    def test_formulaire_et_avancement_du_lot(self):
        self.client.login(username="chef", password="pass")
        self.assertContains(self.client.get(reverse("taches-index")), f'value="section:{self.s1.pk}"')
        self.client.post(reverse("taches-index"), {"titre": "Ranger", "unite": f"section:{self.s1.pk}"})
        self.assertEqual(Tache.objects.filter(lot__isnull=False).count(), 2)
        self.post("marin", "tache-action", [Tache.objects.get(assigne=self.marin).pk],
                  {"action": "rendre_compte", "compte_rendu": "Fait"})
        self.client.login(username="chef", password="pass")
        avancement = services.avancement_equipe(self.chef)
        self.assertEqual([(l["terminees"], l["total"]) for l in avancement["lots"]], [(1, 2)])
        self.assertContains(self.client.get(reverse("taches-index")), "1/2 terminées")

    def test_unites_proposees_limitees_au_perimetre(self):
        cles = [c for c, _, _ in services.unites_assignables(self.chef)]
        self.assertIn(f"section:{self.s1.pk}", cles)
        self.assertNotIn(f"section:{self.s_voisin.pk}", cles)


class RechercheTachesTests(TachesBase):
    def trouvees(self, user, terme="ZEBRE"):
        groupes = recherche.rechercher(user, terme)
        return [r["libelle"] for g in groupes if g["cle"] == "taches" for r in g["resultats"]]

    def test_visibilite_identique_a_la_liste_et_privees_exclues(self):
        self._tache(titre="ZEBRE attribuée")
        self._tache(titre="ZEBRE privée", assigne=self.marin, created_by=self.marin, partagee=False)
        self._tache(titre="ZEBRE partagée", assigne=self.marin, created_by=self.marin, partagee=True)
        self._tache(titre="ZEBRE du voisin", assigne=self.voisin, created_by=self.voisin, partagee=False)
        self.assertCountEqual(self.trouvees(self.marin), ["ZEBRE attribuée", "ZEBRE privée", "ZEBRE partagée"])
        self.assertCountEqual(self.trouvees(self.chef), ["ZEBRE attribuée", "ZEBRE partagée"])
        self.assertEqual(self.trouvees(self.voisin), ["ZEBRE du voisin"])
        self.assertEqual(self.trouvees(self.etranger), [])

    def test_page_de_recherche_renvoie_vers_la_tache(self):
        tache = self._tache(titre="ZEBRE à rechercher")
        self.client.login(username="marin", password="pass")
        self.assertContains(self.client.get(reverse("recherche-rapide"), {"q": "ZEBRE"}), reverse("tache-detail", args=[tache.pk]))
        self.assertContains(self.client.get(reverse("global-search"), {"q": "ZEBRE"}), "ZEBRE à rechercher")
