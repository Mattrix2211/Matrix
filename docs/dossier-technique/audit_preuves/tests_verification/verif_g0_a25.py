"""VÉRIFICATION TEMPORAIRE G0 / A25 — copie isolée de l'état B ; données fictives ; non conservée dans le dépôt."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Roles, UserProfile
from assets.models import Asset, AssetType, ChecklistItemTemplate, ChecklistTemplate
from logistics.models import CorrectiveTicket, StockPiece
from maintenance.models import MaintenanceOccurrence, MaintenancePlan
from maintenance import tasks as mtasks
from notifications import tasks as ntasks
from notifications.models import Notification
from org.models import ModuleActivation, Sector, Service, Ship


def p(*a):
    print("   ", *a)


class A25(TestCase):
    def setUp(self):
        self.ship = Ship.objects.create(name="N A25", code="A25")
        self.service = Service.objects.create(ship=self.ship, name="S")
        self.sector = Sector.objects.create(service=self.service, name="Sec")
        def u(nom, role):
            x = User.objects.create_user(username=nom, password="pw")
            UserProfile.objects.update_or_create(user=x, defaults={"ship": self.ship, "role": role, "sector": self.sector, "service": self.service})
            return x
        self.marin, self.chef = u("marin", Roles.EQUIPIER), u("chef", Roles.CHEF_SECTEUR)
        self.root = User.objects.create_superuser("root", "r@x.fr", "pw")
        t = AssetType.objects.create(name="Ext", category="Inc", sector=self.sector)
        self.asset = Asset.objects.create(asset_type=t, ship=self.ship, service=self.service, sector=self.sector)
        modele = ChecklistTemplate.objects.create(name="G", sector=self.sector)
        ChecklistItemTemplate.objects.create(template=modele, label="X", field_type="checkbox", order=1)
        self.plan = MaintenancePlan.objects.create(scope="ASSET", asset=self.asset, name="PlanSecret", every_n_days=30, checklist_template=modele)
        self.occ = MaintenanceOccurrence.objects.create(plan=self.plan, asset=self.asset, scheduled_for=timezone.localdate() - timedelta(days=3), status="OVERDUE")
        self.occ.assignees.add(self.marin)
        self.ticket = CorrectiveTicket.objects.create(asset=self.asset, description="TicketSecret", severity=4)
        self.ticket.assignees.add(self.marin)
        StockPiece.objects.create(reference="PX", designation="PieceSecret", quantite=0, quantite_minimale=3, ship=self.ship, service=self.service, sector=self.sector)
        for m in ("maintenance", "logistics"):
            ModuleActivation.objects.create(ship=self.ship, module=m, active=False)

    def login(self, nom):
        self.client.logout(); self.client.login(username=nom, password="pw")

    def test_observations(self):
        print("\n=== A25 : modules « maintenance » et « logistics » désactivés pour le bâtiment ===")
        self.login("chef")
        for nom, url in (("web maintenance", reverse("maintenance-occurrences")), ("web tickets", reverse("ticket-list")),
                         ("web stock", reverse("stock-piece-list")), ("web exécution", reverse("occurrence-execute", args=[self.occ.pk])),
                         ("web fiche ticket", reverse("ticket-detail", args=[self.ticket.pk]))):
            r = self.client.get(url); p(nom, "->", r.status_code, r.headers.get("Location", ""))
        r = self.client.post(reverse("ticket-transition", args=[self.ticket.pk]), {"status": "DIAGNOSED"}); p("web écriture ticket ->", r.status_code)
        for nom, url in (("API occurrences", "/api/maintenance/occurrences/"), ("API tickets", "/api/logistics/tickets/"),
                         ("API pièces/lignes", "/api/logistics/part-lines/"), ("API plans", "/api/maintenance/plans/")):
            r = self.client.get(url); p(nom, "->", r.status_code, len(r.json()) if r.status_code == 200 and isinstance(r.json(), list) else (r.json().get("count") if r.status_code == 200 and isinstance(r.json(), dict) else ""))
        r = self.client.post(f"/api/maintenance/occurrences/{self.occ.pk}/start/"); p("API écriture (démarrer une occurrence) ->", r.status_code)
        r = self.client.post(f"/api/logistics/tickets/{self.ticket.pk}/transition/", {"status": "IN_REPAIR"}, content_type="application/json"); p("API transition ticket ->", r.status_code)
        self.login("root")
        for url in ("/admin/maintenance/maintenanceoccurrence/", "/admin/logistics/stockpiece/"):
            r = self.client.get(url); p("admin", url, "->", r.status_code)
        self.login("marin")
        r = self.client.get("/"); c = r.content.decode()
        p("accueil : « TicketSecret » affiché :", "TicketSecret" in c, "; titre de l'occurrence (plan) affiché :", "PlanSecret" in c, "; ligne « En retard » :", "En retard" in c, "; occurrence listée (Ext #) :", "Ext #" in c, "; lien vers la fiche d'exécution :", "/execute/" in c)
        r = self.client.get("/search/?q=PX"); c = r.content.decode(); p("recherche (requête « PX », désignation « PieceSecret » = résultat) ->", r.status_code, "PieceSecret" in c)
        r = self.client.get("/search/?q=icketSecr"); c = r.content.decode(); p("recherche ticket (requête partielle) -> résultat affiché :", "TicketSecret" in c, "; lien vers /tickets/ ou /logistics :", "/tickets/" in c)
        r = self.client.get("/calendar/events/"); c = r.content.decode(); p("calendrier /calendar/events/ ->", r.status_code, "; titre du plan présent :", "PlanSecret" in c, "; contenu :", c[:160].replace("\n", " "))
        # tâches planifiées
        Notification.objects.all().delete()
        ntasks.notify_overdue_occurrences(); n1 = Notification.objects.count(); p("tâche retards de maintenance -> notifications créées :", n1)
        Notification.objects.all().delete(); ntasks.notify_low_stock(); p("tâche stock bas -> notifications créées :", Notification.objects.count())
        avant = MaintenanceOccurrence.objects.count(); mtasks.generate_occurrences(90); p("tâche génération d'occurrences -> créées :", MaintenanceOccurrence.objects.count() - avant)
        # enchaînement interne : non conforme -> ticket (module logistics désactivé)
        avant = CorrectiveTicket.objects.count()
        self.login("chef")
        r = self.client.post(f"/api/maintenance/occurrences/{self.occ.pk}/complete/", {"conformity": "NON_CONFORME"}, content_type="application/json")
        p("API clôture non conforme ->", r.status_code, "; tickets créés :", CorrectiveTicket.objects.count() - avant)
        # le menu masque l'entrée
        self.login("chef"); r = self.client.get("/")
        noms = [e["libelle"] for g in r.context["navigation_laterale"] for e in g["entrees"]]
        p("menu rendu pour le chef (entrées) :", noms)
        p("entrées Maintenance / Tickets correctifs / Anomalies / Logistique présentes :", [n in noms for n in ("Maintenance", "Tickets correctifs", "Anomalies", "Logistique")], "; Matériels (module assets actif) :", "Matériels" in noms)

    def test_taches_planifiees_avant_toute_ecriture(self):
        print("\n=== A25 bis : tâches planifiées seules (aucune écriture API avant) ===")
        Notification.objects.all().delete()
        ntasks.notify_overdue_occurrences(); p("retards de maintenance -> notifications :", Notification.objects.filter(user=self.marin).count())

    def test_controle_recherche_module_actif_puis_inactif(self):
        print("\n=== A25 ter : contrôle de la recherche ===")
        self.login("chef")
        ModuleActivation.objects.filter(module="logistics").update(active=True)
        c = self.client.get("/search/?q=icketSecr").content.decode(); p("logistics ACTIF : ticket trouvé :", "TicketSecret" in c)
        ModuleActivation.objects.filter(module="logistics").update(active=False)
        c = self.client.get("/search/?q=icketSecr").content.decode(); p("logistics INACTIF : ticket trouvé :", "TicketSecret" in c)
