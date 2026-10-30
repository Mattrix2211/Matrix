"""Carte « À faire » de l'accueil : classement en prioritaires et autres, compteurs, visibilité, droits, repli, requêtes."""
import re
from datetime import timedelta
from types import SimpleNamespace

from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from annonces.models import Annonce
from assets.models import Asset, AssetType
from dashboard.a_faire_presentation import (
    ACTION, ALERTE, SEUIL_AUTRES_REPLIEES, SUIVI, URGENT, _nature, compteurs, presenter,
)
from dashboard.aujourdhui import a_faire
from demandes.models import Demande
from logistics.models import CorrectiveTicket
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from org.models import Sector, Service, Ship
from taches.models import Tache


class CarteAFaireBase(TestCase):
    def setUp(self):
        self.navire = Ship.objects.create(name="Frégate test", code="FT-CA", double_equipage=True, equipage_a_bord="A")
        self.service = Service.objects.create(ship=self.navire, name="Énergie")
        self.secteur = Sector.objects.create(service=self.service, name="Propulsion")
        self.marin = self._marin("martin", "A")
        self.terre = self._marin("terre", "B")
        self.autre = self._marin("autre", "A")
        self.type = AssetType.objects.create(name="Pompe", category="Incendie", sector=self.secteur)
        self.aujourdhui = timezone.localdate()
        self.client.login(username="martin", password="pass")

    def _marin(self, nom, equipage):
        user = User.objects.create_user(username=nom, password="pass", last_name=nom.capitalize())
        profil = user.profile
        profil.ship, profil.service, profil.sector, profil.equipage = self.navire, self.service, self.secteur, equipage
        profil.save()
        return user

    def _asset(self):
        return Asset.objects.create(asset_type=self.type, ship=self.navire, service=self.service, sector=self.secteur)

    def _occurrence(self, jours, statut="ASSIGNED", assigne=None):
        asset = self._asset()
        plan = MaintenancePlan.objects.create(scope="ASSET", asset=asset, name="Contrôle", every_n_days=30)
        occ = MaintenanceOccurrence.objects.create(
            plan=plan, asset=asset, scheduled_for=self.aujourdhui + timedelta(days=jours), status=statut,
        )
        occ.assignees.add(assigne or self.marin)
        return occ

    def _tache(self, titre, jours=3, priorite=Tache.PRIORITE_NORMALE, statut=Tache.STATUT_A_FAIRE, assigne=None):
        return Tache.objects.create(
            titre=titre, assigne=assigne or self.marin, echeance=self.aujourdhui + timedelta(days=jours),
            priorite=priorite, statut=statut,
        )

    def _lignes(self, user=None):
        user = user or self.marin
        return presenter(a_faire(user, self.aujourdhui), user)

    def _ligne(self, objet, user=None):
        return next(ligne for ligne in self._lignes(user) if ligne["objet"] == objet)

    @staticmethod
    def _carte(html):
        """La carte seule : la barre latérale contient aussi des balises <section>."""
        debut = html.index('<section class="mx-surface mx-afaire')
        return html[debut:html.index("</section>", debut)]

    def _identifiants(self, html, debut=None, fin=None):
        zone = self._carte(html)
        if debut and fin:
            zone = zone[zone.index(debut):zone.index(fin)] if fin in zone else zone[zone.index(debut):]
        return re.findall(r'data-action-id="([^"]+)"', zone)


class ClassementTests(CarteAFaireBase):
    def test_tache_urgente_non_en_retard_est_prioritaire_et_distincte_du_retard(self):
        urgente = self._tache("Dossier de formation", jours=5, priorite=Tache.PRIORITE_URGENTE)
        en_retard = self._tache("Relevé", jours=-2, priorite=Tache.PRIORITE_URGENTE)
        ordinaire = self._tache("Rangement", jours=4)
        lignes = {ligne["objet"]: ligne for ligne in self._lignes()}
        self.assertEqual((lignes[urgente]["zone"], lignes[urgente]["nature"], lignes[urgente]["repere"]), ("prioritaire", ACTION, "Urgence déclarée"))
        self.assertEqual((lignes[en_retard]["zone"], lignes[en_retard]["nature"], lignes[en_retard]["repere"]), ("prioritaire", URGENT, "Urgence déclarée"))
        self.assertEqual((lignes[ordinaire]["zone"], lignes[ordinaire]["nature"], lignes[ordinaire]["repere"]), ("autre", "", ""))

    def test_tache_urgente_d_un_autre_marin_n_est_pas_une_urgence_pour_soi(self):
        self._tache("Pour autrui", priorite=Tache.PRIORITE_URGENTE, assigne=self.autre)
        self.assertEqual(self._lignes(), [])

    def test_ticket_grave_garde_un_repere_neutre_sans_devenir_urgence(self):
        ticket = CorrectiveTicket.objects.create(asset=self._asset(), description="x", severity=4)
        ticket.assignees.add(self.marin)
        ligne = self._ligne(ticket)
        self.assertEqual((ligne["zone"], ligne["nature"], ligne["repere"]), ("autre", "", "Gravité 4"))

    def test_ticket_bloque_garde_son_statut_sans_nature_deduite(self):
        ticket = CorrectiveTicket.objects.create(asset=self._asset(), description="x", status="BLOCKED")
        ticket.assignees.add(self.marin)
        ligne = self._ligne(ticket)
        self.assertEqual((ligne["zone"], ligne["nature"]), ("prioritaire", ""))
        self.assertIn("Bloqué", ligne["etat"])

    def test_maintenance_en_validation_reste_descriptive_faute_de_workflow(self):
        occ = self._occurrence(2, statut="WAITING_VALIDATION")
        ligne = self._ligne(occ)
        self.assertEqual((ligne["zone"], ligne["nature"], ligne["etat"]), ("prioritaire", "", "En attente de validation"))

    def test_etat_de_maintenance_reflete_le_statut_reel(self):
        en_cours = self._occurrence(1, statut="IN_PROGRESS")
        assignee = self._occurrence(2, statut="ASSIGNED")
        retard_en_cours = self._occurrence(-1, statut="IN_PROGRESS")
        retard = self._occurrence(-2, statut="OVERDUE")
        self.assertEqual(self._ligne(en_cours)["etat"], "En cours")
        self.assertEqual(self._ligne(assignee)["etat"], "Assignée")
        self.assertEqual(self._ligne(retard_en_cours)["etat"], "En retard · en cours")
        self.assertEqual(self._ligne(retard)["etat"], "En retard")
        self.assertEqual(self._ligne(retard)["nature"], URGENT)

    def test_materiel_garde_son_identifiant_et_le_contexte_est_separe(self):
        occ = self._occurrence(1)
        ligne = self._ligne(occ)
        self.assertEqual(ligne["principal"], str(occ.asset))
        self.assertEqual(ligne["contexte"], "Frégate test / Énergie / Propulsion")

    def test_nature_des_sources_par_etat_existant(self):
        moi = SimpleNamespace(pk=1)
        attention = {"niveau": "attention", "criticite": 0}
        responsable_en_attente = Demande(responsable_id=1, declarant_id=2, etat=Demande.ETAT_EN_ATTENTE)
        declarant_en_attente = Demande(responsable_id=2, declarant_id=1, etat=Demande.ETAT_EN_ATTENTE)
        self.assertEqual(_nature({**attention, "objet": responsable_en_attente}, moi), SUIVI)
        self.assertEqual(_nature({**attention, "objet": declarant_en_attente}, moi), ACTION)
        self.assertEqual(_nature({**attention, "objet": Annonce(accuse_requis=True)}, moi), ACTION)
        self.assertEqual(_nature({**attention, "objet": Annonce(accuse_requis=False)}, moi), "")
        self.assertEqual(_nature({"niveau": "danger", "criticite": 0, "objet": Demande()}, moi), URGENT)

    def test_demande_a_suivre_garde_sa_classe_d_etat(self):
        entree = {"objet": Demande(responsable_id=self.marin.pk, declarant_id=self.autre.pk, etat=Demande.ETAT_EN_ATTENTE),
                  "niveau": "attention", "criticite": 0, "titre": "Dossier", "detail": "Demande · En attente d'information",
                  "classes": "mx-aujourdhui__tache--attention", "url": "/", "icone": "discussion"}
        ligne = presenter([entree], self.marin)[0]
        self.assertEqual((ligne["nature"], ligne["classes"]), (SUIVI, "mx-aujourdhui__tache--attention"))

    def test_responsable_et_declarant_a_la_fois_agit(self):
        moi = SimpleNamespace(pk=1)
        demande = Demande(responsable_id=1, declarant_id=1, etat=Demande.ETAT_EN_ATTENTE)
        self.assertEqual(_nature({"niveau": "attention", "criticite": 0, "objet": demande}, moi), ACTION)

    def _annonce_danger(self, accuse_requis):
        annonce = Annonce(pk=1, titre="Fuite", niveau="danger", accuse_requis=accuse_requis)
        entree = {"objet": annonce, "titre": "Fuite", "detail": "", "url": "/", "icone": "", "niveau": "danger",
                  "classes": "", "criticite": 4, "echeance": None}
        return presenter([entree], self.marin)[0]

    def test_annonce_danger_sans_accuse_est_une_alerte_prioritaire(self):
        ligne = self._annonce_danger(False)
        self.assertEqual((ligne["nature"], ligne["libelle_nature"], ligne["zone"]), (ALERTE, "Alerte", "prioritaire"))
        self.assertEqual(ligne["etat"], "Annonce")

    def test_annonce_danger_avec_accuse_reste_une_alerte_et_garde_l_accuse(self):
        ligne = self._annonce_danger(True)
        self.assertEqual((ligne["nature"], ligne["zone"]), (ALERTE, "prioritaire"))
        self.assertEqual(ligne["etat"], "Annonce · Accusé requis")

    def test_annonce_ordinaire_avec_accuse_reste_action_requise(self):
        annonce = Annonce(pk=2, titre="Note", niveau="warning", accuse_requis=True)
        entree = {"objet": annonce, "titre": "Note", "detail": "", "url": "/", "icone": "", "niveau": "attention",
                  "classes": "", "criticite": 0, "echeance": None}
        ligne = presenter([entree], self.marin)[0]
        self.assertEqual((ligne["nature"], ligne["libelle_nature"]), (ACTION, "Action requise"))
        self.assertIn("Accusé requis", ligne["etat"])

    def test_ticket_bloque_grave_garde_statut_et_repere(self):
        ticket = CorrectiveTicket.objects.create(asset=self._asset(), description="x", severity=4, status="BLOCKED")
        ticket.assignees.add(self.marin)
        ligne = self._ligne(ticket)
        self.assertEqual((ligne["nature"], ligne["repere"]), ("", "Gravité 4"))
        self.assertIn("Bloqué", ligne["etat"])

    def test_ticket_sans_equipement_ne_plante_pas(self):
        ticket = CorrectiveTicket.objects.create(description="x")
        ticket.assignees.add(self.marin)
        ligne = self._ligne(ticket)
        self.assertEqual((ligne["contexte"], ligne["principal"]), ("", ligne["titre"]))

    def test_ordre_de_a_faire_conserve(self):
        self._tache("A", jours=1)
        self._occurrence(-1, statut="OVERDUE")
        self._tache("B", jours=2, priorite=Tache.PRIORITE_URGENTE)
        brut = a_faire(self.marin, self.aujourdhui)
        self.assertEqual([ligne["objet"] for ligne in presenter(brut, self.marin)], [e["objet"] for e in brut])


class CompteursEtVisibiliteTests(CarteAFaireBase):
    def _page(self):
        return self.client.get(reverse("home"))

    def _charger(self, urgentes, ordinaires):
        for i in range(urgentes):
            self._occurrence(-1 - i, statut="OVERDUE")
        for i in range(ordinaires):
            self._tache(f"Ordinaire {i}", jours=2 + i)

    def test_compteurs_de_l_en_tete(self):
        self._charger(2, 4)
        r = self._page()
        self.assertEqual((r.context["nb_actions"], r.context["nb_prioritaires"], r.context["nb_autres"]), (6, 2, 4))
        self.assertContains(r, "6 actions · <strong>2 prioritaires</strong> · 4 autres")

    def test_aucune_action_perdue_ni_dupliquee_et_prioritaires_hors_de_la_section(self):
        self._charger(8, 11)
        self._tache("Urgente non en retard", priorite=Tache.PRIORITE_URGENTE)
        html = self._page().content.decode()
        attendus = {f"{e['objet']._meta.label_lower}:{e['objet'].pk}" for e in a_faire(self.marin, self.aujourdhui)}
        trouves = self._identifiants(html)
        self.assertEqual(len(trouves), len(set(trouves)))
        self.assertEqual(set(trouves), attendus)
        self.assertEqual(len(trouves), 20)
        prioritaires = self._identifiants(html, 'class="mx-afaire__priorites"', 'class="mx-afaire__autres"')
        self.assertEqual(len(prioritaires), 9)
        self.assertEqual(len(self._identifiants(html, 'class="mx-afaire__autres"', "FIN")), 11)

    def test_repli_au_seuil(self):
        self._charger(SEUIL_AUTRES_REPLIEES - 1, 5)
        r = self._page()
        self.assertFalse(r.context["autres_repliees"])
        self.assertContains(r, 'data-initial="apercu"')
        self.assertContains(r, ">Tout afficher</button>")
        self._occurrence(-20, statut="OVERDUE")
        r = self._page()
        self.assertTrue(r.context["autres_repliees"])
        self.assertContains(r, 'data-initial="replie"')
        self.assertContains(r, "mx-afaire--replie")
        self.assertContains(r, ">Afficher les autres actions</button>")
        self.assertContains(r, "· repliées")

    def test_repli_garde_toutes_les_actions_dans_la_page(self):
        self._charger(7, 3)
        html = self._page().content.decode()
        self.assertEqual(len(self._identifiants(html)), 10)

    def test_repli_et_masquage_mobile_exigent_javascript(self):
        """Sans script, rien ne doit rester masqué : les règles de masquage dépendent de la classe posée par la carte."""
        self._charger(7, 5)
        self.assertIn("classList.add('mx-js')", self._page().content.decode())
        with open("matrix/static/css/naval_premium.css", encoding="utf-8") as feuille:
            css = feuille.read()
        self.assertIn(".mx-js .mx-afaire--replie:not(.mx-afaire--ouvert) .mx-afaire__defilement { display: none; }", css)
        self.assertIn(".mx-js .mx-afaire:not(.mx-afaire--ouvert) .mx-afaire__ligne:nth-child(n+4) { display: none; }", css)

    def test_liste_courte_sans_bouton_ni_defilement(self):
        self._charger(1, 3)
        r = self._page()
        self.assertContains(r, "data-afaire")
        self.assertNotContains(r, "data-afaire-bascule")

    def test_liste_sans_priorite(self):
        self._charger(0, 5)
        r = self._page()
        self.assertNotContains(r, 'class="mx-afaire__priorites"')
        self.assertContains(r, "Actions · 5")
        self.assertContains(r, "5 actions · <strong>0 prioritaire</strong> · 5 autres")
        self.assertEqual(len(self._identifiants(r.content.decode())), 5)

    def test_liste_sans_autre_action(self):
        self._charger(3, 0)
        r = self._page()
        self.assertNotContains(r, 'class="mx-afaire__autres"')
        self.assertEqual(len(self._identifiants(r.content.decode())), 3)

    def test_liste_vide(self):
        r = self._page()
        self.assertEqual(r.context["a_faire_lignes"], [])
        self.assertNotContains(r, "data-afaire")
        self.assertContains(r, "Rien à faire pour le moment")

    def test_compteurs_sur_liste_vide(self):
        self.assertEqual(compteurs([]), {"nb_actions": 0, "nb_prioritaires": 0, "nb_autres": 0, "autres_repliees": False})


class DroitsEtRequetesTests(CarteAFaireBase):
    def test_equipage_a_terre_garde_la_consultation_seule(self):
        occ = self._occurrence(1, assigne=self.terre)
        occ.assignees.add(self.terre)
        self.client.login(username="terre", password="pass")
        html = self.client.get(reverse("home")).content.decode()
        zone = self._carte(html)
        self.assertIn("Consulter", zone)
        self.assertNotIn(">Ouvrir<", zone)

    def test_marin_a_bord_ouvre_ses_actions(self):
        self._occurrence(1)
        html = self.client.get(reverse("home")).content.decode()
        self.assertIn(">Ouvrir<", self._carte(html))

    def test_classes_d_etat_existantes_conservees(self):
        self._occurrence(-1, statut="OVERDUE")
        self._occurrence(2, statut="WAITING_VALIDATION")
        html = self.client.get(reverse("home")).content.decode()
        self.assertIn("mx-aujourdhui__tache--danger", html)
        self.assertIn("mx-aujourdhui__tache--attention", html)

    def test_la_presentation_ne_fait_aucune_requete(self):
        for i in range(5):
            self._occurrence(i - 2)
        entrees = a_faire(self.marin, self.aujourdhui)
        with self.assertNumQueries(0):
            presenter(entrees, self.marin)

    def _requetes(self, user):
        with CaptureQueriesContext(connection) as contexte:
            presenter(a_faire(user, self.aujourdhui), user)
        return len(contexte)

    def test_nombre_de_requetes_independant_du_nombre_d_actions(self):
        petit = self._marin("petit", "A")
        grand = self._marin("grand", "A")
        for i in range(2):
            self._occurrence(i - 1, assigne=petit)
            ticket = CorrectiveTicket.objects.create(asset=self._asset(), description="x")
            ticket.assignees.add(petit)
        for i in range(12):
            self._occurrence(i - 5, assigne=grand)
            ticket = CorrectiveTicket.objects.create(asset=self._asset(), description="x", status="BLOCKED")
            ticket.assignees.add(grand)
        self.assertEqual(self._requetes(petit), self._requetes(grand))


class ImpressionCarteTests(TestCase):
    def test_impression_deplie_toutes_les_actions(self):
        css = (settings.BASE_DIR / "matrix/static/css/naval_premium.css").read_text(encoding="utf-8")
        bloc = css[css.index("@media print"):]
        for regle in (".mx-afaire__defilement", "max-height: none", ".mx-afaire__bascule"):
            self.assertIn(regle, bloc)
