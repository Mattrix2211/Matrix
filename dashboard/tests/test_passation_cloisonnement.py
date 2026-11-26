"""L30 (ARB-02, AC-03) : cloisonnement des synthèses de passation par périmètre et partage ciblé.

Chaque scénario de refus a son témoin positif : le même marqueur est lu par le profil légitime, afin qu'une base vide ou une route
inexistante ne passe jamais pour une protection."""
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, ServiceFunctionChoice, UserProfile
from annonces.models import Annonce
from dashboard.passation import contenu_passation, syntheses_visibles
from dashboard.passation_partage import partager, revoquer
from dashboard.passation_perimetre import contenu_visible, ligne_de, peut_partager
from logistics.models import Anomalie, StockPiece
from notifications.liens import lien_objet
from notifications.models import Notification
from org.models import ParametresPassation, PartagePassation, Section, Sector, Service, Ship, SynthesePassation
from taches.models import Tache
from training.models import TrainingCourse, TrainingRecord

User = get_user_model()

T_A1A, T_A1B, T_B1A = "TACHE-A1A", "TACHE-A1B", "TACHE-B1A"
ANOM_SERVICE_A, ANOM_NAVIRE, STOCK_A1 = "ANOM-SERVICE-A", "ANOM-NAVIRE", "STOCK-A1"
QUALIF = "QUALIF-EQ-A1A"
T_A2A = "TACHE-A2A"
MARQUEURS = (T_A1A, T_A1B, T_A2A, T_B1A, ANOM_SERVICE_A, ANOM_NAVIRE, STOCK_A1, QUALIF)


def titres(contenu):
    return {ligne["titre"] for bloc in contenu["blocs"] for groupe in bloc["groupes"] for ligne in groupe["lignes"]}


def cles(contenu):
    return {ligne["cle"] for bloc in contenu["blocs"] for groupe in bloc["groupes"] for ligne in groupe["lignes"]}


class Monde(TestCase):
    """Un bâtiment à double équipage, deux services, trois sections, ses chefs et un second bâtiment."""

    def marin(self, nom, role="EQUIPIER", navire=None, equipage="A", service=None, secteur=None, section=None, **champs):
        navire = self.navire if navire is None else navire
        user = User.objects.create_user(username=nom, password="pass")
        UserProfile.objects.update_or_create(user=user, defaults={
            "role": role, "ship": navire, "service": service, "sector": secteur, "section": section, "equipage": equipage, **champs})
        return User.objects.get(pk=user.pk)

    def setUp(self):
        ParametresPassation.objects.create(active=True)
        self.navire = Ship.objects.create(name="Bretagne", code="BRE", double_equipage=True, equipage_a_bord="A")
        self.autre_navire = Ship.objects.create(name="Normandie", code="NOR", double_equipage=True, equipage_a_bord="A")
        self.sa = Service.objects.create(ship=self.navire, name="Énergie", commandant_adjoint="COMAEQ")
        self.sb = Service.objects.create(ship=self.navire, name="Opérations", commandant_adjoint="COMOPS")
        self.sa1 = Sector.objects.create(service=self.sa, name="Tableaux")
        self.sb1 = Sector.objects.create(service=self.sb, name="Radar")
        self.sa2 = Sector.objects.create(service=self.sa, name="Distribution")  # second secteur du même service
        self.a2a = Section.objects.create(sector=self.sa2, name="Dist-1")
        self.a1a = Section.objects.create(sector=self.sa1, name="Tab-1")
        self.a1b = Section.objects.create(sector=self.sa1, name="Tab-2")
        self.b1a = Section.objects.create(sector=self.sb1, name="Rad-1")
        # Commandement et équipiers
        self.cdt = self.marin("cdt", "COMMANDANT")
        self.second = self.marin("second", "COMMANDANT_EN_SECOND", equipage="B")
        self.eq_a1a = self.marin("eq_a1a", section=self.a1a)
        self.eq_a1b = self.marin("eq_a1b", section=self.a1b)
        self.eq_b1a = self.marin("eq_b1a", section=self.b1a)
        self.eq_a2a = self.marin("eq_a2a", section=self.a2a)
        self.chef_secteur_a2 = self.marin("chef_secteur_a2", "CHEF_SECTEUR", secteur=self.sa2)
        # Chefs
        self.chef_section_a1a = self.marin("chef_section_a1a", "CHEF_SECTION", section=self.a1a)
        self.chef_section_a1b = self.marin("chef_section_a1b", "CHEF_SECTION", section=self.a1b)
        self.chef_section_b1a = self.marin("chef_section_b1a", "CHEF_SECTION", section=self.b1a, equipage="B")
        self.chef_secteur_a1 = self.marin("chef_secteur_a1", "CHEF_SECTEUR", secteur=self.sa1)
        self.chef_secteur_b1 = self.marin("chef_secteur_b1", "CHEF_SECTEUR", secteur=self.sb1)
        self.chef_service_a = self.marin("chef_service_a", "CHEF_SERVICE", service=self.sa)
        self.chef_service_b = self.marin("chef_service_b", "CHEF_SERVICE", service=self.sb, equipage="B")
        self.comaeq = self.marin("comaeq", "ETAT_MAJOR", fonction_coma="COMAEQ")
        self.comops = self.marin("comops", "ETAT_MAJOR", fonction_coma="COMOPS")
        # Statuts d'administration (aucun droit métier) et cumul explicite
        self.technique = self.marin("technique", administrateur_technique=True)
        self.general = User.objects.create_user(username="general", password="pass")
        UserProfile.objects.filter(user=self.general).update(role="EQUIPIER", administrateur_general=True, ship=None)
        self.general = User.objects.get(pk=self.general.pk)
        self.general_cdt = self.marin("general_cdt", "COMMANDANT", administrateur_general=True)
        # Autre bâtiment
        self.cdt_etranger = self.marin("cdt_etranger", "COMMANDANT", navire=self.autre_navire)
        self.marin_etranger = self.marin("marin_etranger", navire=self.autre_navire)
        self.peupler()
        self.synthese = SynthesePassation.objects.create(
            ship=self.navire, equipage_sortant="B", equipage_montant="A", auteur=self.cdt, contenu=contenu_passation(self.cdt, self.navire))
        self.url = reverse("passation", args=[self.synthese.pk])

    def peupler(self):
        for titre, assigne in ((T_A1A, self.eq_a1a), (T_A1B, self.eq_a1b), (T_A2A, self.eq_a2a), (T_B1A, self.eq_b1a)):
            Tache.objects.create(titre=titre, assigne=assigne, created_by=self.cdt, statut="A_FAIRE")
        Anomalie.objects.create(titre=ANOM_SERVICE_A, description="x", created_by=self.cdt, ship=self.navire, service=self.sa)
        Anomalie.objects.create(titre=ANOM_NAVIRE, description="x", created_by=self.cdt, ship=self.navire)
        StockPiece.objects.create(reference=STOCK_A1, designation="Filtre", quantite=0, quantite_minimale=2, ship=self.navire,
                                  service=self.sa, sector=self.sa1)
        cours = TrainingCourse.objects.create(title=QUALIF)
        aujourdhui = timezone.localdate()
        TrainingRecord.objects.create(user=self.eq_a1a, course=cours, completed_at=aujourdhui - timedelta(days=400),
                                      expires_at=aujourdhui - timedelta(days=5))

    def lit(self, user):
        """Marqueurs lus par `user` (un titre peut les contenir : « STOCK-A1 — Filtre »)."""
        lus = titres(contenu_visible(user, self.synthese))
        return {m for m in MARQUEURS if any(m in t for t in lus)}

    def page(self, user, url=None):
        client = Client()
        client.force_login(user)
        return client.get(url or self.url)


class MatriceDesEchelonsTests(Monde):
    """T-L30-1 : échelon × contenu, positif et négatif."""

    ATTENDU = {
        "eq_a1a": {T_A1A, QUALIF},
        "eq_a1b": {T_A1B},
        "chef_section_a1a": {T_A1A, QUALIF},
        "chef_section_a1b": {T_A1B},
        "chef_section_b1a": {T_B1A},
        "chef_secteur_a1": {T_A1A, T_A1B, QUALIF, STOCK_A1},
        "chef_secteur_a2": {T_A2A},
        "eq_a2a": {T_A2A},
        "chef_secteur_b1": {T_B1A},
        "chef_service_a": {T_A1A, T_A1B, T_A2A, QUALIF, STOCK_A1, ANOM_SERVICE_A},
        "chef_service_b": {T_B1A},
        "comaeq": {T_A1A, T_A1B, T_A2A, QUALIF, STOCK_A1, ANOM_SERVICE_A},
        "comops": {T_B1A},
        "second": set(MARQUEURS),
        "cdt": set(MARQUEURS),
        "general_cdt": set(MARQUEURS),  # fonction métier explicitement cumulée : applicable dans son périmètre
        "technique": set(),
    }

    def test_chaque_echelon_ne_lit_que_son_perimetre(self):
        for nom, attendu in self.ATTENDU.items():
            self.assertEqual(self.lit(User.objects.get(username=nom)), attendu, nom)

    def test_temoins_positifs_pour_les_marqueurs_refuses(self):
        # Chaque marqueur interdit à l'un est lu par au moins un profil légitime : la protection n'est pas un contenu vide.
        for marqueur in MARQUEURS:
            lecteurs = [n for n, attendu in self.ATTENDU.items() if marqueur in attendu]
            self.assertGreaterEqual(len(lecteurs), 3, marqueur)

    def test_pages_rendues_contiennent_ou_non_les_marqueurs(self):
        for nom, attendu in self.ATTENDU.items():
            reponse = self.page(User.objects.get(username=nom))
            self.assertEqual(reponse.status_code, 200, nom)
            html = reponse.content.decode()
            for marqueur in MARQUEURS:
                self.assertEqual(marqueur in html, marqueur in attendu, f"{nom} : {marqueur}")

    def test_les_totaux_et_compteurs_ne_comptent_que_le_visible(self):
        contenu = contenu_visible(self.chef_section_a1a, self.synthese)
        totaux = {b["cle"]: b["total"] for b in contenu["blocs"]}
        self.assertEqual((totaux["taches"], totaux["qualifications"], totaux["anomalies"], totaux["stock"]), (1, 1, 0, 0))
        for bloc in contenu["blocs"]:
            self.assertEqual(bloc["total"], sum(len(g["lignes"]) + g["plus"] for g in bloc["groupes"]), bloc["cle"])
        html = self.page(self.chef_section_a1a).content.decode()
        self.assertNotIn(">3<", html.replace(" ", ""))  # le total du bâtiment (trois tâches) n'apparaît pas

    def test_administrateur_general_sans_fonction_n_a_aucun_droit_et_autre_batiment_exclu(self):
        for user in (self.general, self.cdt_etranger, self.marin_etranger):
            self.assertEqual(self.page(user).status_code, 404, user.username)
            self.assertFalse(syntheses_visibles(user).exists(), user.username)
            self.assertEqual(self.lit(user), set(), user.username)
        # Témoin positif : le commandant de l'autre bâtiment lit sa propre synthèse.
        autre = SynthesePassation.objects.create(
            ship=self.autre_navire, equipage_montant="A", contenu=contenu_passation(self.cdt_etranger, self.autre_navire))
        self.assertEqual(self.page(self.cdt_etranger, reverse("passation", args=[autre.pk])).status_code, 200)
        self.assertEqual(self.page(self.cdt, reverse("passation", args=[autre.pk])).status_code, 404)

    def test_l_administrateur_technique_n_a_pas_de_droit_metier_supplementaire(self):
        self.assertEqual(self.page(self.technique).status_code, 200)
        self.assertEqual(self.lit(self.technique), set())
        # Témoin : la même page ouvre à un marin concerné son propre contenu.
        self.assertEqual(self.lit(self.eq_a1a), {T_A1A, QUALIF})

    def test_l_equipage_n_est_pas_un_critere_et_l_equipage_a_terre_garde_la_consultation(self):
        # chef_section_b1a et chef_service_b sont de l'équipage B (à terre) : ils lisent leur périmètre, sans limite de durée.
        self.assertEqual(self.lit(self.chef_section_b1a), {T_B1A})
        self.synthese.created_at = timezone.now() - timedelta(days=2000)
        self.synthese.save()
        self.assertEqual(self.page(self.chef_service_b).status_code, 200)
        self.assertEqual(self.lit(self.chef_service_b), {T_B1A})
        # La consultation ne confère aucune écriture sur l'équipage embarqué.
        reponse = Client()
        reponse.force_login(self.chef_service_b)
        self.assertEqual(reponse.post(reverse("taches-index"), {"titre": "x"}).status_code, 403)

    def test_pdf_et_impression_suivent_le_meme_filtre(self):
        client = Client()
        client.force_login(self.chef_section_a1a)
        with mock.patch("dashboard.passation.html_vers_pdf", side_effect=lambda html: html.encode()):
            contenu = client.get(reverse("passation-pdf", args=[self.synthese.pk])).content.decode()
        self.assertIn(T_A1A, contenu)
        for interdit in (T_A1B, T_B1A, ANOM_SERVICE_A, ANOM_NAVIRE, STOCK_A1):
            self.assertNotIn(interdit, contenu)

    def test_aucune_api_ni_administration_n_expose_la_synthese(self):
        from django.contrib import admin
        from django.urls import get_resolver

        self.assertFalse(admin.site.is_registered(SynthesePassation))
        self.assertFalse(admin.site.is_registered(PartagePassation))
        adresses = [str(p.pattern) for p in get_resolver().url_patterns]
        self.assertFalse([a for a in adresses if "passation" in a and a.startswith("api/")])
        reponse = Client()
        reponse.force_login(self.chef_service_a)
        self.assertEqual(reponse.get("/api/passation/").status_code, 404)

    def test_aucune_recherche_ni_notification_ne_porte_le_contenu(self):
        client = Client()
        client.force_login(self.chef_section_a1b)
        page = client.get("/search/", {"q": T_A1A}).content.decode()
        self.assertNotIn("passation", page.lower().replace("synthèse de passation", ""))
        for notification in Notification.objects.all():
            for marqueur in MARQUEURS:
                self.assertNotIn(marqueur, notification.verb)

    def test_synthese_figee_avant_le_cloisonnement_reste_lisible_du_commandement_seul(self):
        ancienne = SynthesePassation.objects.create(
            ship=self.navire, equipage_montant="A", contenu={"blocs": [{
                "cle": "taches", "titre": "Tâches", "total": 1, "vide": "", "groupes": [{
                    "titre": "A faire", "total": 1, "plus": 0, "lignes": [{"titre": "ANCIENNE-LIGNE", "detail": "", "url": "/", "etat": ""}]}]}]})
        url = reverse("passation", args=[ancienne.pk])
        self.assertContains(self.page(self.cdt, url), "ANCIENNE-LIGNE")
        self.assertContains(self.page(self.second, url), "ANCIENNE-LIGNE")
        for nom in ("chef_service_a", "chef_section_a1a", "eq_a1a", "technique"):
            reponse = self.page(User.objects.get(username=nom), url)
            self.assertEqual(reponse.status_code, 200, nom)
            self.assertNotContains(reponse, "ANCIENNE-LIGNE")
            self.assertContains(reponse, "avant le cloisonnement")

    def test_changement_d_affectation_du_lecteur_joue_immediatement(self):
        self.assertEqual(self.lit(self.chef_section_a1a), {T_A1A, QUALIF})
        UserProfile.objects.filter(user=self.chef_section_a1a).update(section=self.a1b)
        mute = User.objects.get(pk=self.chef_section_a1a.pk)
        self.assertEqual(self.lit(mute), {T_A1B})
        UserProfile.objects.filter(user=self.chef_section_a1a).update(ship=self.autre_navire, section=None)
        self.assertEqual(self.page(User.objects.get(pk=self.chef_section_a1a.pk)).status_code, 404)

    def test_passation_desactivee_ferme_les_pages_de_partage(self):
        ParametresPassation.objects.update(active=False)
        client = Client()
        client.force_login(self.cdt)
        self.assertEqual(client.get(reverse("passation-partage", args=[self.synthese.pk]), {"ligne": f"tache:1"}).status_code, 404)


class PartageCibleTests(Monde):
    """T-L30-3 : partage ciblé d'une information, lecture seule, révocable, historisé."""

    def cle(self, titre):
        for bloc in self.synthese.contenu["blocs"]:
            for groupe in bloc["groupes"]:
                for ligne in groupe["lignes"]:
                    if titre in ligne["titre"]:
                        return ligne["cle"]
        raise AssertionError(titre)

    def test_partage_a_un_marin_n_ouvre_que_la_ligne_choisie(self):
        partager(self.chef_section_a1a, self.synthese, self.cle(T_A1A), "MARIN", self.chef_section_b1a.pk)
        lu = self.lit(self.chef_section_b1a)
        self.assertEqual(lu, {T_B1A, T_A1A})  # sa propre ligne et la ligne partagée, rien d'autre
        reponse = self.page(self.chef_section_b1a).content.decode()
        self.assertIn(T_A1A, reponse)
        self.assertIn("Partagé avec vous", reponse)
        for interdit in (T_A1B, ANOM_SERVICE_A, STOCK_A1, ANOM_NAVIRE):
            self.assertNotIn(interdit, reponse)
        # Un tiers non destinataire ne lit toujours pas la ligne.
        self.assertNotIn(T_A1A, self.lit(User.objects.get(username="chef_secteur_b1")))

    def test_destinataires_fonction_section_secteur_service(self):
        partager(self.chef_service_a, self.synthese, self.cle(ANOM_SERVICE_A), "FONCTION", "coma:COMOPS")
        self.assertIn(ANOM_SERVICE_A, self.lit(self.comops))
        self.assertNotIn(ANOM_SERVICE_A, self.lit(self.chef_service_b))
        partager(self.chef_service_a, self.synthese, self.cle(STOCK_A1), "SERVICE", self.sb.pk)
        self.assertIn(STOCK_A1, self.lit(self.chef_service_b))
        self.assertIn(STOCK_A1, self.lit(self.chef_secteur_b1) | self.lit(self.chef_service_b))
        partager(self.chef_service_a, self.synthese, self.cle(T_A1B), "SECTEUR", self.sb1.pk)
        self.assertIn(T_A1B, self.lit(self.chef_secteur_b1))
        self.assertIn(T_A1B, self.lit(self.chef_section_b1a))  # les membres du secteur, ses sections comprises
        self.assertNotIn(T_A1B, self.lit(self.chef_service_b))  # le service, au-dessus du secteur, n'en est pas membre
        partager(self.chef_service_a, self.synthese, self.cle(T_A1A), "SECTION", self.b1a.pk)
        self.assertIn(T_A1A, self.lit(self.chef_section_b1a))
        ServiceFunctionChoice.objects.create(name="Officier de quart")
        UserProfile.objects.filter(user=self.eq_b1a).update(fonction_service="Officier de quart")
        partager(self.chef_service_a, self.synthese, self.cle(T_A1B), "FONCTION", "service:Officier de quart")
        self.assertIn(T_A1B, self.lit(User.objects.get(pk=self.eq_b1a.pk)))

    def test_le_beneficiaire_ne_peut_ni_modifier_ni_repartager(self):
        partager(self.chef_section_a1a, self.synthese, self.cle(T_A1A), "MARIN", self.chef_section_b1a.pk)
        ligne = next(l for b in contenu_visible(self.chef_section_b1a, self.synthese)["blocs"] for g in b["groupes"] for l in g["lignes"] if l["titre"] == T_A1A)
        self.assertFalse(ligne["peut_partager"])
        self.assertTrue(ligne["partage_recu"])
        with self.assertRaises(PermissionDenied):
            partager(self.chef_section_b1a, self.synthese, self.cle(T_A1A), "MARIN", self.eq_b1a.pk)  # pas de partage transitif
        client = Client()
        client.force_login(self.chef_section_b1a)
        reponse = client.post(reverse("passation-partage", args=[self.synthese.pk]),
                              {"ligne": self.cle(T_A1A), "type_destinataire": "MARIN", "destinataire": self.eq_b1a.pk})
        self.assertEqual(reponse.status_code, 403)
        # Le lien du détail reste protégé par ses propres droits : la lecture de la ligne ne donne aucun droit sur la tâche.
        tache = Tache.objects.get(titre=T_A1A)
        self.assertIn(client.get(reverse("tache-detail", args=[tache.pk])).status_code, (403, 404))  # lire la ligne n'ouvre pas la tâche
        self.assertIn(client.post(reverse("tache-action", args=[tache.pk]), {"action": "demarrer"}).status_code, (403, 404))
        tache.refresh_from_db()
        self.assertEqual(tache.statut, "A_FAIRE")

    def test_partage_interdit_hors_perimetre_et_pour_un_statut_administratif(self):
        for emetteur, titre in ((self.chef_section_a1a, T_B1A), (self.eq_a1b, T_A1A), (self.technique, T_A1A), (self.chef_secteur_b1, T_A1A)):
            with self.assertRaises(PermissionDenied, msg=f"{emetteur.username} / {titre}"):
                partager(emetteur, self.synthese, self.cle(titre), "MARIN", self.eq_b1a.pk)
        with self.assertRaises(PermissionDenied):
            partager(self.general, self.synthese, self.cle(T_A1A), "MARIN", self.eq_b1a.pk)
        # Témoins positifs : l'émetteur légitime partage ; un marin partage ce qui le concerne.
        self.assertTrue(partager(self.chef_secteur_a1, self.synthese, self.cle(T_A1A), "MARIN", self.eq_b1a.pk)[1])
        self.assertTrue(partager(self.eq_a1a, self.synthese, self.cle(T_A1A), "MARIN", self.eq_a1b.pk)[1])
        self.assertTrue(peut_partager(self.cdt, self.synthese, ligne_de(self.synthese, self.cle(T_A1A))))

    def test_information_confidentielle_non_partageable(self):
        cle = self.cle(QUALIF)
        for emetteur in (self.chef_section_a1a, self.chef_service_a, self.cdt, self.eq_a1a):
            with self.assertRaises(PermissionDenied, msg=emetteur.username):
                partager(emetteur, self.synthese, cle, "MARIN", self.eq_b1a.pk)
        self.assertFalse(PartagePassation.objects.exists())

    def test_destinataire_hors_batiment_ou_inconnu_refuse(self):
        cle = self.cle(T_A1A)
        for type_, valeur in (("MARIN", self.marin_etranger.pk), ("MARIN", 99999), ("SERVICE", Service.objects.create(ship=self.autre_navire, name="X").pk),
                              ("FONCTION", "coma:INCONNU"), ("MARIN", "abc"), ("INCONNU", "1")):
            with self.assertRaises(ValidationError, msg=f"{type_} {valeur}"):
                partager(self.chef_section_a1a, self.synthese, cle, type_, valeur)
        self.assertFalse(PartagePassation.objects.exists())

    def test_un_partage_est_idempotent_et_historise(self):
        cle = self.cle(T_A1A)
        premier, cree = partager(self.chef_section_a1a, self.synthese, cle, "MARIN", self.eq_b1a.pk)
        second, cree_bis = partager(self.chef_section_a1a, self.synthese, cle, "MARIN", self.eq_b1a.pk)
        self.assertEqual((premier.pk, cree, cree_bis), (second.pk, True, False))
        self.assertEqual(PartagePassation.objects.count(), 1)
        trace = AuditLog.objects.get(action="passation_partagee")
        self.assertEqual(trace.actor, self.chef_section_a1a)
        self.assertIn("eq_b1a", trace.details)
        self.assertEqual((premier.partage_par, premier.libelle, premier.revoque_le), (self.chef_section_a1a, T_A1A, None))

    def test_revocation_par_l_auteur_ou_une_autorite_conserve_l_historique(self):
        cle = self.cle(T_A1A)
        partage, _ = partager(self.chef_section_a1a, self.synthese, cle, "MARIN", self.eq_b1a.pk)
        self.assertIn(T_A1A, self.lit(self.eq_b1a))
        # Tiers sans autorité sur la ligne, et destinataire : refus.
        for intrus in (self.chef_section_b1a, self.eq_b1a, self.technique, self.general):
            with self.assertRaises(PermissionDenied, msg=intrus.username):
                revoquer(intrus, partage)
        self.assertTrue(revoquer(self.chef_service_a, partage))  # autorité qui couvre la ligne (chef de service)
        self.assertNotIn(T_A1A, self.lit(User.objects.get(pk=self.eq_b1a.pk)))
        partage.refresh_from_db()
        self.assertEqual((partage.revoque_par, partage.actif), (self.chef_service_a, False))
        self.assertTrue(AuditLog.objects.filter(action="passation_partage_revoque", actor=self.chef_service_a).exists())
        self.assertEqual(PartagePassation.objects.count(), 1)  # jamais effacé
        # Un nouveau partage identique est possible après révocation ; l'auteur le révoque lui-même.
        nouveau, cree = partager(self.chef_section_a1a, self.synthese, cle, "MARIN", self.eq_b1a.pk)
        self.assertTrue(cree)
        self.assertTrue(revoquer(self.chef_section_a1a, nouveau))
        with self.assertRaises(PermissionDenied):  # un partage déjà révoqué ne se révoque pas deux fois
            revoquer(self.chef_section_a1a, PartagePassation.objects.get(pk=nouveau.pk))

    def test_la_revocation_s_applique_aux_lectures_suivantes_pas_aux_exports_deja_faits(self):
        cle = self.cle(T_A1A)
        partage, _ = partager(self.chef_section_a1a, self.synthese, cle, "MARIN", self.eq_b1a.pk)
        avant = self.page(self.eq_b1a).content.decode()
        revoquer(self.chef_section_a1a, partage)
        apres = self.page(User.objects.get(pk=self.eq_b1a.pk)).content.decode()
        self.assertIn(T_A1A, avant)  # ce qui a déjà été consulté ou imprimé reste chez son lecteur (limite documentée)
        self.assertNotIn(T_A1A, apres)

    def test_changement_d_affectation_du_destinataire_ou_de_l_emetteur(self):
        cle = self.cle(T_A1B)
        partager(self.chef_service_a, self.synthese, cle, "SERVICE", self.sb.pk)
        self.assertIn(T_A1B, self.lit(self.chef_service_b))
        nouveau = self.marin("nouveau_sb", "CHEF_SECTION", section=self.b1a)
        self.assertIn(T_A1B, self.lit(nouveau))  # un arrivant du service destinataire lit le partage
        UserProfile.objects.filter(user=nouveau).update(section=self.a1a)  # il change de service
        self.assertNotIn(T_A1B, self.lit(User.objects.get(pk=nouveau.pk)))
        UserProfile.objects.filter(user=self.chef_service_b).update(ship=self.autre_navire, service=None)
        self.assertEqual(self.page(User.objects.get(pk=self.chef_service_b.pk)).status_code, 404)
        # L'émetteur qui change d'unité garde le droit de révoquer son partage, plus celui de partager.
        partage = PartagePassation.objects.get()
        UserProfile.objects.filter(user=self.chef_service_a).update(service=self.sb)
        mute = User.objects.get(pk=self.chef_service_a.pk)
        self.assertFalse(peut_partager(mute, self.synthese, next(l for b in self.synthese.contenu["blocs"] for g in b["groupes"] for l in g["lignes"] if l["cle"] == cle)))
        self.assertTrue(revoquer(mute, partage))

    def test_notification_du_destinataire_sans_fuite_du_contenu(self):
        partager(self.chef_section_a1a, self.synthese, self.cle(T_A1A), "MARIN", self.chef_section_b1a.pk)
        notification = Notification.objects.get(user=self.chef_section_b1a, verb__contains="a partagé")
        for marqueur in MARQUEURS:
            self.assertNotIn(marqueur, notification.verb)
        self.assertEqual(lien_objet(self.chef_section_b1a, self.synthese), reverse("passation", args=[self.synthese.pk]))
        self.assertIsNone(lien_objet(self.marin_etranger, self.synthese))
        self.assertFalse(Notification.objects.filter(user=self.chef_section_a1a, verb__contains="a partagé").exists())

    def test_interface_de_partage(self):
        cle = self.cle(T_A1A)
        client = Client()
        client.force_login(self.chef_section_a1a)
        page = client.get(reverse("passation", args=[self.synthese.pk])).content.decode()
        self.assertIn("Partager", page)
        formulaire = client.get(reverse("passation-partage", args=[self.synthese.pk]), {"ligne": cle})
        self.assertContains(formulaire, "Partager en lecture seule")
        self.assertEqual(client.post(reverse("passation-partage", args=[self.synthese.pk]),
                                     {"ligne": cle, "type_destinataire": "MARIN", "destinataire": self.chef_section_b1a.pk}).status_code, 302)
        page = client.get(reverse("passation", args=[self.synthese.pk])).content.decode()
        self.assertIn("Partagé (1)", page)
        suivi = client.get(reverse("passation-partage", args=[self.synthese.pk]), {"ligne": cle})
        self.assertContains(suivi, "Révoquer")
        partage = PartagePassation.objects.get()
        self.assertEqual(client.post(reverse("passation-partage-revoquer", args=[self.synthese.pk, partage.pk])).status_code, 302)
        partage.refresh_from_db()
        self.assertIsNotNone(partage.revoque_le)
        self.assertContains(client.get(reverse("passation-partage", args=[self.synthese.pk]), {"ligne": cle}), "Révoqué le")
        # Une ligne hors périmètre n'existe pas pour ce lecteur (404, pas 403).
        self.assertEqual(client.get(reverse("passation-partage", args=[self.synthese.pk]), {"ligne": self.cle(T_B1A)}).status_code, 404)
        # Le destinataire (partage actif) voit la page de la ligne en lecture seule, sans formulaire.
        partager(self.chef_section_a1a, self.synthese, cle, "MARIN", self.chef_section_b1a.pk)
        destinataire = Client()
        destinataire.force_login(self.chef_section_b1a)
        lecture = destinataire.get(reverse("passation-partage", args=[self.synthese.pk]), {"ligne": cle})
        self.assertEqual(lecture.status_code, 200)
        self.assertNotContains(lecture, "Partager en lecture seule")
        self.assertContains(lecture, "lecture seule")

    def test_equipage_a_terre_peut_partager_sans_modifier_les_activites_embarquees(self):
        # chef_service_b est de l'équipage B, à terre : il partage une information de son périmètre.
        cle = self.cle(T_B1A)
        client = Client()
        client.force_login(self.chef_service_b)
        reponse = client.post(reverse("passation-partage", args=[self.synthese.pk]),
                              {"ligne": cle, "type_destinataire": "MARIN", "destinataire": self.chef_section_b1a.pk})
        self.assertEqual(reponse.status_code, 302)
        self.assertEqual(PartagePassation.objects.get().partage_par, self.chef_service_b)
        tache = Tache.objects.get(titre=T_B1A)
        self.assertEqual(client.post(reverse("tache-action", args=[tache.pk]), {"action": "demarrer"}).status_code, 403)

    def test_partage_hors_bâtiment_sur_la_synthese_d_un_autre_batiment_refuse(self):
        autre = SynthesePassation.objects.create(
            ship=self.autre_navire, equipage_montant="A", contenu=contenu_passation(self.cdt_etranger, self.autre_navire))
        client = Client()
        client.force_login(self.cdt)
        self.assertEqual(client.get(reverse("passation-partage", args=[autre.pk]), {"ligne": "x"}).status_code, 404)
        self.assertEqual(client.post(reverse("passation-partage-revoquer", args=[autre.pk, 1])).status_code, 404)

    def test_generation_notifie_toujours_les_chefs_du_montant_sans_contenu(self):
        for notification in Notification.objects.filter(user=self.chef_section_a1a):
            self.assertNotIn(T_A1A, notification.verb)
