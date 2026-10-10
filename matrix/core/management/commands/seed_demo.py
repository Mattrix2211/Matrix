"""Jeu de données de démonstration (idempotent : relançable sans doublon).

Tous les comptes ont le mot de passe « pass » (sauf `admin` : « admin »).
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import (
    FonctionQuartChoice, GradeChoice, ResponsableSpecialite, Roles, ServiceFunctionChoice,
    SpecialityChoice,
)
from assets.models import (
    ArticleCatalogue, Asset, AssetType, CategorieCatalogue, ChecklistItemTemplate, ChecklistTemplate,
    ChefResponsableSpecialite, Installation, InstallationBigrameChoice, InstallationEvent,
    InstallationExtraField, InstallationHourReading, InstallationIsolationReading,
    InstallationMaintenance, InstallationPart, InstallationVibrationReading, Location,
)
from assets import fiche_maintenance
from matrix.core.models import Brouillon
from logistics.models import (
    Anomalie, CorrectiveTicket, PartLineItem, PartRequest, StockPiece, TicketStatusLog,
)
from maintenance.models import MaintenanceExecution, MaintenanceOccurrence, MaintenancePlan
from notifications.models import Notification, NotificationLevel
from org.models import ReleveEquipage, ResponsableClasseNavire, Sector, Section, Service, Ship
from quarts.models import (
    ChefDeListe, CreneauQuart, CreneauServiceGarde, Quart, ServiceGarde,
)
from rondes.models import PointControle, RondeModele
from rondes import services as rondes_services
from taches import services as taches_services
from taches.models import Tache
from threads.models import Message, Thread
from training.models import (
    ReferentFormation, TrainingCourse, TrainingRecord, TrainingRequirement, TrainingSession,
)

MOT_DE_PASSE = "pass"


class Command(BaseCommand):
    help = "Crée (ou complète) les données de démonstration de Matrix"

    def handle(self, *args, **options):
        self.comptes = []
        self.maintenant = timezone.now()
        self.aujourdhui = timezone.localdate()
        self._referentiels()
        self._unite_historique()
        self._bretagne()
        self._normandie()
        self._a_terre()
        self._catalogue()
        self._materiel_et_installations()
        self._maintenance()
        self._tickets_et_anomalies()
        self._rondes()
        self._quarts()
        self._formations()
        self._taches()
        self._notifications_et_brouillons()
        self.stdout.write(self.style.SUCCESS("Données de démonstration prêtes. Comptes (mot de passe « pass ») :"))
        for ligne in self.comptes:
            self.stdout.write(ligne)

    # ---------- Outils ----------

    def _utilisateur(self, nom, role, prenom="", ship=None, service=None, sector=None, section=None,
                     equipage="", fonction_coma="", grade="", specialite="", mdp=MOT_DE_PASSE, superuser=False):
        user, cree = User.objects.get_or_create(username=nom, defaults={
            "first_name": prenom, "last_name": nom.replace("_", " ").title(), "is_superuser": superuser, "is_staff": superuser})
        if cree:
            user.set_password(mdp)
            user.save()
        profil = user.profile
        profil.role, profil.ship, profil.service, profil.sector, profil.section = role, ship, service, sector, section
        profil.equipage, profil.fonction_coma, profil.grade, profil.specialite = equipage, fonction_coma, grade, specialite
        profil.save()
        navire = ship or (service.ship if service else None) or (sector.service.ship if sector else None) \
            or (section.sector.service.ship if section else None)
        self.comptes.append(f"  {nom:<22} {role}{' ' + equipage if equipage else ''}{' ' + fonction_coma if fonction_coma else ''}"
                            f" — {navire or 'à terre'}")
        return user

    def _jour(self, decalage, heure=0):
        return self.maintenant.replace(hour=heure, minute=0, second=0, microsecond=0) + timedelta(days=decalage)

    # ---------- Référentiels ----------

    def _referentiels(self):
        for nom in ["Matelot", "Quartier-maître", "Second-maître", "Maître", "Lieutenant de vaisseau", "Capitaine de corvette",
                    "Capitaine de frégate"]:
            GradeChoice.objects.get_or_create(name=nom)
        self.spec = {n: SpecialityChoice.objects.get_or_create(name=n)[0]
                     for n in ["Mécanique", "Sécurité", "Électricité", "SIC", "Artillerie"]}
        for nom in ["Chef de garde", "Rondier"]:
            ServiceFunctionChoice.objects.get_or_create(name=nom)
        self.fonctions_quart = {n: FonctionQuartChoice.objects.get_or_create(name=n)[0]
                                for n in ["Barre", "Veille", "Machine avant"]}
        self.bigrames = {n: InstallationBigrameChoice.objects.get_or_create(name=n)[0] for n in ["Propulsion", "Énergie"]}

    # ---------- Unité historique (jeu de départ BordOps I) ----------

    def _unite_historique(self):
        ship, _ = Ship.objects.get_or_create(name="BordOps I", code="BO1")
        service, _ = Service.objects.get_or_create(ship=ship, name="Technique")
        sector_fire, _ = Sector.objects.get_or_create(service=service, name="Pompiers")
        sector_elec, _ = Sector.objects.get_or_create(service=service, name="Électricité")
        section_a, _ = Section.objects.get_or_create(sector=sector_fire, name="Section A")
        Section.objects.get_or_create(sector=sector_elec, name="Section B")
        self._utilisateur("admin", Roles.MASTER_ADMIN, mdp="admin", superuser=True)
        self._utilisateur("commandant", Roles.COMMANDANT, ship=ship)
        self._utilisateur("chefservice", Roles.CHEF_SERVICE, service=service)
        self._utilisateur("chefsecteur", Roles.CHEF_SECTEUR, sector=sector_fire)
        self._utilisateur("chefsection", Roles.CHEF_SECTION, section=section_a)
        self._utilisateur("equipier", Roles.EQUIPIER, section=section_a)
        location, _ = Location.objects.get_or_create(ship=ship, name="Pont 1", parent=None)
        at_fire, _ = AssetType.objects.get_or_create(name="Extincteur", sector=sector_fire, defaults={"category": "Fire"})
        at_san, _ = AssetType.objects.get_or_create(name="Évacuation sanitaire", sector=sector_elec, defaults={"category": "Sanitaire"})
        Asset.objects.get_or_create(internal_id="FX-001", ship=ship, defaults=dict(
            asset_type=at_fire, service=service, sector=sector_fire, section=section_a, location=location))
        Asset.objects.get_or_create(internal_id="SAN-001", ship=ship, defaults=dict(
            asset_type=at_san, service=service, sector=sector_elec, location=location))
        temp, _ = ChecklistTemplate.objects.get_or_create(name="Contrôle visuel extincteur", sector=sector_fire, asset_type=at_fire)
        ChecklistItemTemplate.objects.get_or_create(template=temp, label="Goupille présente", defaults=dict(
            field_type="checkbox", required=True, order=1))
        ChecklistItemTemplate.objects.get_or_create(template=temp, label="Pression (bar)", defaults=dict(
            field_type="number", unit="bar", order=2))
        MaintenancePlan.objects.get_or_create(scope="ASSET_TYPE", asset_type=at_fire, name="Contrôle trimestriel", defaults=dict(
            every_n_days=90, checklist_template=temp))

    # ---------- Frégate à double équipage ----------

    def _bretagne(self):
        ship, _ = Ship.objects.get_or_create(name="Bretagne", code="BRE", defaults=dict(
            classe_navire="FREMM", double_equipage=True, equipage_a_bord="A"))
        self.bre = ship
        s = {}
        for nom, coma in [("Propulsion", "COMANAV"), ("Énergie", "COMANAV"), ("Sécurité", "COMAEQ"), ("Opérations", "COMOPS")]:
            s[nom], _ = Service.objects.get_or_create(ship=ship, name=nom, defaults={"commandant_adjoint": coma})
            if s[nom].commandant_adjoint != coma:
                Service.objects.filter(pk=s[nom].pk).update(commandant_adjoint=coma)
        sec = {}
        for service, secteur, section, couleur in [
            ("Propulsion", "Moteurs", "Moteurs bâbord", "#0d6efd"), ("Propulsion", "Auxiliaires", "Pompes", "#6f42c1"),
            ("Énergie", "Électricité", "Tableaux", "#fd7e14"), ("Sécurité", "Pompiers", "Sections incendie", "#dc3545"),
            ("Opérations", "Passerelle", "Veille", "#20c997"),
        ]:
            sec[secteur], _ = Sector.objects.get_or_create(service=s[service], name=secteur, defaults={"color": couleur})
            sec[secteur + ".section"], _ = Section.objects.get_or_create(sector=sec[secteur], name=section)
        self.bre_s, self.bre_sec = s, sec
        moteurs, tableaux, pompiers = sec["Moteurs"], sec["Électricité"], sec["Pompiers"]
        sm, st, sp = sec["Moteurs.section"], sec["Électricité.section"], sec["Pompiers.section"]
        u = self._utilisateur
        self.cdt_a = u("cdt_a", Roles.COMMANDANT, "Anne", ship=ship, equipage="A", grade="Capitaine de frégate")
        self.cdt_b = u("cdt_b", Roles.COMMANDANT, "Benoît", ship=ship, equipage="B", grade="Capitaine de frégate")
        self.second_a = u("second_a", Roles.COMMANDANT_EN_SECOND, "Cécile", ship=ship, equipage="A", grade="Capitaine de corvette")
        u("coma_comanav", Roles.ETAT_MAJOR, "Denis", ship=ship, equipage="A", fonction_coma="COMANAV", grade="Capitaine de corvette")
        u("coma_comaeq", Roles.ETAT_MAJOR, "Éloïse", ship=ship, equipage="A", fonction_coma="COMAEQ", grade="Lieutenant de vaisseau")
        u("coma_comops", Roles.ETAT_MAJOR, "Fabien", ship=ship, equipage="A", fonction_coma="COMOPS", grade="Lieutenant de vaisseau")
        u("chef_service_a", Roles.CHEF_SERVICE, "Gaël", ship=ship, service=s["Propulsion"], equipage="A", grade="Maître")
        self.chef_secteur_a = u("chef_secteur_a", Roles.CHEF_SECTEUR, "Hélène", ship=ship, service=s["Propulsion"], sector=moteurs,
                                equipage="A", grade="Second-maître", specialite="Mécanique")
        u("chef_secteur_b", Roles.CHEF_SECTEUR, "Ivan", ship=ship, service=s["Propulsion"], sector=moteurs, equipage="B",
          grade="Second-maître", specialite="Mécanique")
        u("chef_secteur_elec_a", Roles.CHEF_SECTEUR, "Inès", ship=ship, service=s["Énergie"], sector=tableaux, equipage="A",
          grade="Second-maître", specialite="Électricité")
        u("chef_secteur_incendie_a", Roles.CHEF_SECTEUR, "Jules", ship=ship, service=s["Sécurité"], sector=pompiers, equipage="A",
          grade="Second-maître", specialite="Sécurité")
        u("chef_section_a", Roles.CHEF_SECTION, "Jade", ship=ship, service=s["Propulsion"], sector=moteurs, section=sm,
          equipage="A", grade="Quartier-maître")
        self.equipier_a = u("equipier_a", Roles.EQUIPIER, "Karim", ship=ship, service=s["Propulsion"], sector=moteurs, section=sm,
                            equipage="A", grade="Matelot", specialite="Mécanique")
        self.equipier_a2 = u("equipier_a2", Roles.EQUIPIER, "Lina", ship=ship, service=s["Propulsion"], sector=moteurs, section=sm,
                             equipage="A", grade="Matelot", specialite="Mécanique")
        self.marin_b = u("marin_b", Roles.EQUIPIER, "Marc", ship=ship, service=s["Propulsion"], sector=moteurs, section=sm,
                         equipage="B", grade="Matelot", specialite="Mécanique")
        self.equipier_elec = u("equipier_elec_a", Roles.EQUIPIER, "Nora", ship=ship, service=s["Énergie"], sector=tableaux, section=st, equipage="A",
          grade="Matelot", specialite="Électricité")
        self.equipier_incendie = u("equipier_incendie_a", Roles.EQUIPIER, "Omar", ship=ship, service=s["Sécurité"], sector=pompiers, section=sp, equipage="A",
          grade="Matelot", specialite="Sécurité")
        u("admin_navire", Roles.ADMIN_NAVIRE, "Paul", ship=ship, equipage="A")
        ChefDeListe.objects.get_or_create(user=self.chef_secteur_a, sector=moteurs, ship=None, service=None, section=None)
        # Visa et suivi : le commandant en second est désigné par l'administration.
        Location.objects.get_or_create(ship=ship, name="Local machine", parent=None)
        Location.objects.get_or_create(ship=ship, name="Local tableaux", parent=None)
        Location.objects.get_or_create(ship=ship, name="Coursive pont 2", parent=None)

    def _normandie(self):
        ship, _ = Ship.objects.get_or_create(name="Normandie", code="NOR", defaults=dict(classe_navire="FREMM"))
        self.nor = ship
        service, _ = Service.objects.get_or_create(ship=ship, name="Propulsion", defaults={"commandant_adjoint": "COMANAV"})
        secteur, _ = Sector.objects.get_or_create(service=service, name="Moteurs")
        section, _ = Section.objects.get_or_create(sector=secteur, name="Moteurs tribord")
        self.nor_secteur, self.nor_service = secteur, service
        self._utilisateur("cdt_nor", Roles.COMMANDANT, "Quentin", ship=ship, grade="Capitaine de frégate")
        self._utilisateur("chef_secteur_nor", Roles.CHEF_SECTEUR, "Rose", ship=ship, service=service, sector=secteur,
                          grade="Second-maître", specialite="Mécanique")
        self._utilisateur("equipier_nor", Roles.EQUIPIER, "Sami", ship=ship, service=service, sector=secteur, section=section,
                          grade="Matelot", specialite="Mécanique")
        Location.objects.get_or_create(ship=ship, name="Local machine", parent=None)

    # ---------- Utilisateurs à terre ----------

    def _a_terre(self):
        # Sans rattachement à un bâtiment : suivi de la classe FREMM (Bretagne et Normandie).
        classe = self._utilisateur("terre_classe", Roles.CHEF_SERVICE, "Tessa", grade="Capitaine de corvette")
        ResponsableClasseNavire.objects.get_or_create(classe_navire="FREMM", user=classe)
        responsable = self._utilisateur("terre_securite", Roles.CHEF_SERVICE, "Ugo", grade="Maître", specialite="Sécurité")
        chef = self._utilisateur("terre_chef_securite", Roles.CHEF_SERVICE, "Vera", grade="Capitaine de corvette", specialite="Sécurité")
        rs, _ = ResponsableSpecialite.objects.get_or_create(specialite=self.spec["Sécurité"], user=responsable)
        ChefResponsableSpecialite.objects.get_or_create(responsable=rs, defaults={"chef": chef})
        self.responsable_securite = responsable

    # ---------- Catalogue ----------

    def _catalogue(self):
        securite = self.spec["Sécurité"]
        parent, _ = CategorieCatalogue.objects.get_or_create(parent=None, nom="Sécurité incendie", defaults=dict(
            specialite=securite, created_by=self.responsable_securite))
        enfant, _ = CategorieCatalogue.objects.get_or_create(parent=parent, nom="Extincteurs", defaults=dict(
            specialite=securite, created_by=self.responsable_securite))
        self.articles = {}
        for cat, designation, marque, ref, vie in [
            (enfant, "Extincteur CO2 5 kg", "Sicli", "CO2-5", 120), (enfant, "Extincteur eau pulvérisée 9 L", "Sicli", "EP-9", 120),
            (parent, "Détecteur de fumée optique", "Securiton", "SD-O", 96),
        ]:
            self.articles[designation], _ = ArticleCatalogue.objects.get_or_create(categorie=cat, designation=designation, defaults=dict(
                marque=marque, reference=ref, duree_vie_mois=vie, created_by=self.responsable_securite,
                caracteristiques={"Agent extincteur": "CO2"} if "CO2" in designation else {}))

    # ---------- Matériel et installations ----------

    def _materiel_et_installations(self):
        ship, s, sec = self.bre, self.bre_s, self.bre_sec
        local = Location.objects.get(ship=ship, name="Local machine")
        pompiers, serv_sec, sect_elec = sec["Pompiers"], s["Sécurité"], sec["Électricité"]
        at_ext, _ = AssetType.objects.get_or_create(sector=pompiers, name="Extincteurs", defaults={"category": "Extincteurs"})
        at_mes, _ = AssetType.objects.get_or_create(sector=sect_elec, name="Instruments de mesure", defaults={"category": "Mesure"})
        self.at_ext = at_ext
        art = self.articles["Extincteur CO2 5 kg"]
        # Matériel équipé depuis l'article du catalogue (deux fiches restent à compléter).
        for i in range(1, 5):
            Asset.objects.get_or_create(internal_id=f"FX-B0{i}", ship=ship, defaults=dict(
                asset_type=at_ext, service=serv_sec, sector=pompiers, section=sec["Pompiers.section"], location=local,
                designation=art.designation, marque=art.marque, reference=art.reference, article_catalogue=art,
                serial_number=f"SN-{1000 + i}" if i <= 2 else "",
                status="OUT_OF_SERVICE" if i == 4 else "OK",
                date_dernier_controle=self.aujourdhui - timedelta(days=60 * i),
                date_peremption=self.aujourdhui + timedelta(days=20 if i == 2 else 900),
                created_by=self.chef_secteur_a))
        for i, (des, marque) in enumerate([("Multimètre numérique", "Fluke"), ("Mégohmmètre 1000 V", "Metrix"),
                                           ("Pince ampèremétrique", "Chauvin Arnoux")], start=1):
            Asset.objects.get_or_create(internal_id=f"MES-B0{i}", ship=ship, defaults=dict(
                asset_type=at_mes, service=s["Énergie"], sector=sect_elec, section=sec["Électricité.section"],
                designation=des, marque=marque, serial_number=f"M-{200 + i}", status="OK" if i != 3 else "FAULTY",
                date_dernier_controle=self.aujourdhui - timedelta(days=100 * i)))
        # Checklist de contrôle des extincteurs (compte rendu d'occurrence).
        modele, _ = ChecklistTemplate.objects.get_or_create(name="Contrôle extincteur", sector=pompiers, asset_type=at_ext)
        for ordre, (libelle, champ, obligatoire, unite, mini, maxi) in enumerate([
            ("Goupille et plomb présents", "checkbox", True, "", None, None),
            ("État du tuyau et de la buse", "checkbox", True, "", None, None),
            ("Pression (bar)", "number", False, "bar", 12, 16), ("Observations", "text", False, "", None, None),
        ], start=1):
            ChecklistItemTemplate.objects.get_or_create(template=modele, label=libelle, defaults=dict(
                field_type=champ, required=obligatoire, unit=unite, valeur_min=mini, valeur_max=maxi, order=ordre))
        self.checklist_ext = modele
        self.plan_ext, _ = MaintenancePlan.objects.get_or_create(scope="ASSET_TYPE", asset_type=at_ext, name="Contrôle trimestriel extincteurs", defaults=dict(
            every_n_days=90, checklist_template=modele, requires_validation=True, expected_duration_min=15))

        # Installations de la frégate.
        elec_service, moteurs = s["Énergie"], sec["Moteurs"]
        local_t = Location.objects.get(ship=ship, name="Local tableaux")
        self.inst = {}
        specs = [
            ("Groupe électrogène n°1", elec_service, sect_elec, sec["Électricité.section"], local_t, True, "Énergie", "GE-1"),
            ("Pompe de refroidissement bâbord", s["Propulsion"], moteurs, sec["Moteurs.section"], local, False, "Propulsion", "POMPE-RB"),
            ("Réducteur principal", s["Propulsion"], moteurs, sec["Moteurs.section"], local, True, "Propulsion", "RED-1"),
            ("Séparateur d'eau de cale", s["Propulsion"], moteurs, sec["Moteurs.section"], local, False, "Propulsion", "SEP-1"),
        ]
        for designation, service, secteur, section, lieu, critique, bigrame, ref in specs:
            self.inst[ref], _ = Installation.objects.get_or_create(ship=ship, designation=designation, defaults=dict(
                service=service, sector=secteur, section=section, location=lieu, critique=critique, reference=ref,
                marque="Wärtsilä" if ref == "GE-1" else "Alfa Laval", gisement="Pont 2", local=lieu.name,
                bigrame=self.bigrames[bigrame], isolation_seuil_ohms=500000, created_by=self.chef_secteur_a))
        pompe_graissage, _ = Installation.objects.get_or_create(ship=ship, designation="Pompe de graissage", defaults=dict(
            service=s["Propulsion"], sector=moteurs, section=sec["Moteurs.section"], location=local,
            parent=self.inst["RED-1"], reference="PG-1", created_by=self.chef_secteur_a))
        self.inst["PG-1"] = pompe_graissage
        self._releves()
        # Deux installations sur la Normandie (suivi à terre).
        for designation in ("Pompe d'eau de mer", "Compresseur d'air de lancement"):
            Installation.objects.get_or_create(ship=self.nor, designation=designation, defaults=dict(
                service=self.nor_service, sector=self.nor_secteur, location=Location.objects.get(ship=self.nor, name="Local machine"),
                critique=designation.startswith("Compresseur")))
        # Stock sous le seuil.
        for ref, des, qte, mini, crit in [("JNT-10", "Joint de pompe", 2, 6, 1), ("FLT-22", "Filtre à huile", 0, 4, 0), ("COU-05", "Courroie", 9, 4, None)]:
            StockPiece.objects.get_or_create(ship=ship, reference=ref, defaults=dict(
                designation=des, quantite=qte, quantite_minimale=mini, quantite_critique=crit,
                service=s["Propulsion"], sector=moteurs, emplacement="Magasin machine"))

    def _releves(self):
        ge, pompe, red = self.inst["GE-1"], self.inst["POMPE-RB"], self.inst["RED-1"]
        if not ge.hour_readings.exists():
            cumul = Decimal("4200")
            for semaines in range(12, -1, -1):
                cumul += Decimal(35 + (semaines % 3) * 5)
                InstallationHourReading.objects.create(installation=ge, date=self.aujourdhui - timedelta(weeks=semaines), hours=cumul)
            cumul = Decimal("1800")
            for semaines in range(8, -1, -1):
                cumul += Decimal(50)
                InstallationHourReading.objects.create(installation=pompe, date=self.aujourdhui - timedelta(weeks=semaines), hours=cumul)
        if not ge.vibration_readings.exists():
            for mois, etat in [(6, "A"), (4, "A"), (3, "B"), (2, "B"), (1, "C"), (0, "B")]:
                InstallationVibrationReading.objects.create(
                    installation=ge, date=self.aujourdhui - timedelta(days=30 * mois), state=etat, note="Relevé mensuel")
            for mois, etat in [(5, "A"), (2, "A"), (0, "A")]:
                InstallationVibrationReading.objects.create(installation=pompe, date=self.aujourdhui - timedelta(days=30 * mois), state=etat)
        if not ge.isolation_readings.exists():
            # Isolement en baisse régulière : la dérive doit apparaître avant le seuil.
            for mois, ohms in [(6, 2400000), (5, 1900000), (4, 1500000), (3, 1100000), (2, 850000), (1, 680000), (0, 560000)]:
                InstallationIsolationReading.objects.create(
                    installation=ge, date=self.aujourdhui - timedelta(days=30 * mois), ohms=Decimal(ohms))
        if not ge.events.exists():
            InstallationEvent.objects.create(installation=ge, date=self._jour(-40), label="Remplacement du filtre à air",
                                             notes="Effectué par le service énergie.", created_by=self.chef_secteur_a)
            InstallationEvent.objects.create(installation=ge, date=self._jour(-10), label="Alarme température d'huile",
                                             notes="Alarme acquittée, surveillance renforcée.", created_by=self.chef_secteur_a)
            InstallationExtraField.objects.create(installation=ge, label="Puissance nominale", value="800 kVA", order=1)
            InstallationExtraField.objects.create(installation=ge, label="Tension", value="440 V", order=2)
            for nom, ref in [("Filtre à air", "FA-220"), ("Joint de culasse", "JC-18"), ("Capteur de température", "CT-4")]:
                InstallationPart.objects.create(installation=ge, name=nom, reference=ref, marque="Wärtsilä")
        if not ge.maintenances.exists():
            self._fiche(
                installation=ge, periodicity="Mensuelle", title="Contrôle des niveaux et fuites", planned_duration_min=45,
                people_count=2, mode_declenchement="CALENDRIER", intervalle=1, unite_intervalle="M", created_by=self.chef_secteur_a)
            self._fiche(
                installation=ge, periodicity="Toutes les 500 h", title="Vidange et filtre à huile", planned_duration_min=180,
                people_count=2, competence="BORD", mode_declenchement="LES_DEUX", intervalle=6, unite_intervalle="M",
                seuil_heures=500, derniere_echeance_heures=Decimal("4200"), created_by=self.chef_secteur_a)
            self._fiche(
                installation=pompe, periodicity="Trimestrielle", title="Graissage des paliers", planned_duration_min=30,
                mode_declenchement="CALENDRIER", intervalle=3, unite_intervalle="M", created_by=self.chef_secteur_a)
            self._fiche(
                installation=red, periodicity="Annuelle", title="Analyse d'huile", competence="SLM", planned_duration_min=60,
                mode_declenchement="CALENDRIER", intervalle=1, unite_intervalle="A", created_by=self.chef_secteur_a)
            self._fiche(
                installation=self.inst["SEP-1"], periodicity="Hebdomadaire", title="Nettoyage du séparateur", planned_duration_min=20,
                mode_declenchement="CALENDRIER", intervalle=1, unite_intervalle="S", created_by=self.chef_secteur_a)

    def _fiche(self, **champs):
        """Fiche de démonstration : directement validée (version 1)."""
        fiche = InstallationMaintenance.objects.create(**champs)
        fiche_maintenance.enregistrer_version_directe(fiche, champs["created_by"], "Fiche de démonstration")

    # ---------- Maintenance ----------

    def _maintenance(self):
        if MaintenanceOccurrence.objects.filter(installation_maintenance__installation__ship=self.bre).exists():
            return
        j = self.aujourdhui
        gammes = {m.title: m for m in InstallationMaintenance.objects.filter(installation__ship=self.bre)}

        def occurrence_installation(titre, decalage, statut, assignes=()):
            occ = MaintenanceOccurrence.objects.create(
                installation_maintenance=gammes[titre], scheduled_for=j + timedelta(days=decalage), status=statut, priority=2)
            occ.assignees.set(assignes)
            return occ

        occurrence_installation("Contrôle des niveaux et fuites", -9, "OVERDUE")
        occurrence_installation("Graissage des paliers", -3, "OVERDUE", [self.equipier_a])
        occurrence_installation("Vidange et filtre à huile", 0, "ASSIGNED", [self.equipier_elec])
        occurrence_installation("Nettoyage du séparateur", 2, "PLANNED")
        occurrence_installation("Analyse d'huile", 30, "PLANNED")
        valid = occurrence_installation("Nettoyage du séparateur", -5, "WAITING_VALIDATION", [self.equipier_a])
        MaintenanceExecution.objects.create(
            occurrence=valid, started_at=self._jour(-5, 9), completed_at=self._jour(-5, 10), executed_by=self.equipier_a,
            conformity="CONFORME", notes="RAS, séparateur propre.")
        # Matériel mobile : occurrences avec checklist (compte rendu et fiche imprimable).
        ext = list(Asset.objects.filter(ship=self.bre, asset_type=self.at_ext).order_by("internal_id"))
        occ_retard = MaintenanceOccurrence.objects.create(plan=self.plan_ext, asset=ext[0], scheduled_for=j - timedelta(days=12), status="OVERDUE", priority=3)
        occ_assignee = MaintenanceOccurrence.objects.create(plan=self.plan_ext, asset=ext[1], scheduled_for=j + timedelta(days=1), status="ASSIGNED", priority=2)
        occ_assignee.assignees.set([self.equipier_incendie])
        MaintenanceOccurrence.objects.create(plan=self.plan_ext, asset=ext[2], scheduled_for=j + timedelta(days=20), status="PLANNED")
        occ_valid = MaintenanceOccurrence.objects.create(plan=self.plan_ext, asset=ext[3], scheduled_for=j - timedelta(days=2), status="WAITING_VALIDATION", priority=3)
        occ_valid.assignees.set([self.equipier_incendie])
        MaintenanceExecution.objects.create(
            occurrence=occ_valid, started_at=self._jour(-2, 14), completed_at=self._jour(-2, 14) + timedelta(minutes=20), executed_by=self.equipier_incendie,
            results={"Goupille et plomb présents": {"etat": "conforme", "commentaire": ""},
                     "État du tuyau et de la buse": {"etat": "conforme", "commentaire": ""}, "Observations": "Rien à signaler"},
            measurements={"Pression (bar)": 14}, conformity="CONFORME")
        occ_retard.assignees.set([self.equipier_incendie])

    # ---------- Tickets et anomalies ----------

    def _tickets_et_anomalies(self):
        if CorrectiveTicket.objects.filter(installation__ship=self.bre).exists():
            return
        ge, pompe, red = self.inst["GE-1"], self.inst["POMPE-RB"], self.inst["RED-1"]
        ext = Asset.objects.filter(ship=self.bre, asset_type=self.at_ext).order_by("internal_id")
        marin, chef = self.equipier_a, self.chef_secteur_a

        def ticket(cible, description, gravite, parcours, assignes=(), **extra):
            attribut = {"installation": cible} if isinstance(cible, Installation) else {"asset": cible}
            t = CorrectiveTicket.objects.create(
                description=description, severity=gravite, status=parcours[-1], created_by=marin,
                reported_at=self._jour(-len(parcours) - 2), **attribut, **extra)
            t.assignees.set(assignes)
            ancien = "REPORTED"
            for i, statut in enumerate(parcours):
                TicketStatusLog.objects.create(ticket=t, old_status=ancien if i else "REPORTED", new_status=statut,
                                               user=chef if i else marin, note="")
                ancien = statut
            return t

        ticket(ge, "Fuite d'huile au niveau du carter, goutte à goutte.", 4, ["REPORTED"])
        ticket(pompe, "Vibrations anormales à haut régime.", 3, ["REPORTED", "DIAGNOSED", "IN_REPAIR"], [marin])
        t_pieces = ticket(red, "Bruit de roulement côté sortie d'arbre.", 4, ["REPORTED", "DIAGNOSED", "WAITING_PARTS"], [marin])
        demande = PartRequest.objects.create(ticket=t_pieces, requested_by=chef, needed_by_date=self.aujourdhui + timedelta(days=15))
        PartLineItem.objects.create(part_request=demande, reference="RLT-66", description="Roulement 6310", qty=2, status="ORDERED", vendor="SKF")
        ticket(self.inst["SEP-1"], "Débit insuffisant sur la sortie huile.", 2, ["REPORTED", "DIAGNOSED", "IN_REPAIR", "TESTING"], [marin])
        ticket(ext[3], "Manomètre bloqué à zéro, extincteur déclaré hors service.", 3, ["REPORTED", "DIAGNOSED", "BLOCKED"], [chef])
        ticket(self.inst["PG-1"], "Pompe remise en service après remplacement du clapet.", 2,
               ["REPORTED", "DIAGNOSED", "IN_REPAIR", "TESTING", "RETURNED_TO_SERVICE", "CLOSED"], [marin],
               diagnostic_final="Clapet grippé.", solution="Clapet remplacé, essais concluants.")
        Anomalie.objects.get_or_create(titre="Fuite en coursive pont 2", defaults=dict(
            description="Eau au sol près du local tableaux.", gravite=3, localisation="Coursive pont 2", ship=self.bre,
            service=self.bre_s["Énergie"], sector=self.bre_sec["Électricité"], created_by=marin))
        Anomalie.objects.get_or_create(titre="Issue de secours encombrée", defaults=dict(
            description="Caisses stockées devant la porte.", gravite=4, statut="PRISE_EN_COMPTE", localisation="Pont 1 tribord",
            ship=self.bre, service=self.bre_s["Sécurité"], sector=self.bre_sec["Pompiers"], created_by=marin))
        Anomalie.objects.get_or_create(titre="Éclairage défaillant au magasin", defaults=dict(
            gravite=2, statut="TRAITEE", localisation="Magasin machine", ship=self.bre, service=self.bre_s["Propulsion"],
            sector=self.bre_sec["Moteurs"], installation=red, created_by=marin))
        # Quelques tickets à bord de la Normandie pour le suivi à terre.
        inst_nor = Installation.objects.filter(ship=self.nor).first()
        if inst_nor:
            ticket(inst_nor, "Joint d'étanchéité à remplacer.", 3, ["REPORTED", "DIAGNOSED", "BLOCKED"])
        # Fil de discussion sur le ticket de pièces.
        fil, _ = Thread.objects.get_or_create(content_type=ContentType.objects.get_for_model(t_pieces), object_id=str(t_pieces.pk))
        Message.objects.create(thread=fil, author=chef, body="Roulement commandé, livraison attendue sous quinze jours.")
        Message.objects.create(thread=fil, author=marin, body="Bien reçu, je surveille la température du palier.")

    # ---------- Rondes ----------

    def _rondes(self):
        modele, cree = RondeModele.objects.get_or_create(nom="Ronde machine du soir", ship=self.bre, defaults=dict(
            description="Tour des locaux machine avant la nuit.", service=self.bre_s["Propulsion"], sector=self.bre_sec["Moteurs"],
            periodicite_jours=1, responsable=self.equipier_a))
        if cree:
            for ordre, (libelle, cible, mesure, unite) in enumerate([
                ("Niveau d'huile du groupe", "GE-1", False, ""), ("Température d'eau de refroidissement", "POMPE-RB", True, "°C"),
                ("Absence de fuite au réducteur", "RED-1", False, ""), ("Propreté du séparateur", "SEP-1", False, "")], start=1):
                PointControle.objects.create(modele=modele, ordre=ordre, libelle=libelle, installation=self.inst[cible],
                                             avec_mesure=mesure, unite_mesure=unite, gravite=3)
        if not modele.rondes.exists():
            ronde = rondes_services.creer_ronde(modele, acteur=self.equipier_a)
            ronde.statut, ronde.debut = "EN_COURS", self.maintenant - timedelta(minutes=25)
            ronde.save()
            premier = ronde.resultats.order_by("ordre").first()
            premier.resultat, premier.saisi_par, premier.saisi_le = "CONFORME", self.equipier_a, self.maintenant
            premier.save()

    # ---------- Quarts et services ----------

    def _quarts(self):
        moteurs = self.bre_sec["Moteurs"]
        debut = self.aujourdhui - timedelta(days=self.aujourdhui.weekday())
        equipe = [self.equipier_a, self.equipier_a2, self.chef_secteur_a]
        brouillon, cree = Quart.objects.get_or_create(nom="Quarts machine — semaine prochaine", sector=moteurs, defaults=dict(
            date_debut=debut + timedelta(days=7), date_fin=debut + timedelta(days=13), statut="BROUILLON",
            fonction=self.fonctions_quart["Machine avant"], duree_creneau_heures=4, created_by=self.chef_secteur_a))
        if cree:
            for i in range(6):
                heure = 0 + 4 * (i % 6)
                jour = brouillon.date_debut + timedelta(days=i // 3)
                CreneauQuart.objects.create(
                    quart=brouillon, poste="Machine avant", marin=equipe[i % 3] if i < 5 else None,
                    debut=timezone.make_aware(timezone.datetime(jour.year, jour.month, jour.day, heure)),
                    fin=timezone.make_aware(timezone.datetime(jour.year, jour.month, jour.day, heure)) + timedelta(hours=4))
        publie, cree = Quart.objects.get_or_create(nom="Quarts machine — cette semaine", sector=moteurs, defaults=dict(
            date_debut=debut, date_fin=debut + timedelta(days=6), fonction=self.fonctions_quart["Barre"], duree_creneau_heures=4,
            created_by=self.chef_secteur_a))
        if cree:
            for i in range(12):
                jour = debut + timedelta(days=i // 3)
                heure = 8 * (i % 3)
                CreneauQuart.objects.create(
                    quart=publie, poste="Barre" if i % 2 else "Veille", marin=equipe[i % 3],
                    debut=timezone.make_aware(timezone.datetime(jour.year, jour.month, jour.day, heure)),
                    fin=timezone.make_aware(timezone.datetime(jour.year, jour.month, jour.day, heure)) + timedelta(hours=8))
            publie.publier(self.chef_secteur_a)
        garde, cree = ServiceGarde.objects.get_or_create(nom="Garde de nuit — Propulsion", service=self.bre_s["Propulsion"], defaults=dict(
            date_debut=debut, date_fin=debut + timedelta(days=6), type_service="Garde de nuit", duree_creneau_heures=12,
            fonction=ServiceFunctionChoice.objects.get(name="Chef de garde"), created_by=self.chef_secteur_a))
        if cree:
            for i in range(6):
                jour = debut + timedelta(days=i)
                CreneauServiceGarde.objects.create(
                    service_garde=garde, poste="Chef de garde", marin=equipe[i % 3],
                    debut=timezone.make_aware(timezone.datetime(jour.year, jour.month, jour.day, 20)),
                    fin=timezone.make_aware(timezone.datetime(jour.year, jour.month, jour.day, 20)) + timedelta(hours=12))
            garde.publier(self.chef_secteur_a)

    # ---------- Formations ----------

    def _formations(self):
        cours = {}
        for titre, cat, validite in [("Lutte contre l'incendie", "Sécurité", 730), ("Habilitation électrique", "Électricité", 1095),
                                     ("Conduite de la chaufferie", "Mécanique", 1825)]:
            cours[titre], _ = TrainingCourse.objects.get_or_create(title=titre, defaults=dict(
                category=cat, validity_days=validite, description=f"Formation « {titre} »."))
        cours["Conduite de la chaufferie"].prerequisites.add(cours["Lutte contre l'incendie"])
        if not TrainingSession.objects.filter(course__in=cours.values()).exists():
            incendie = TrainingSession.objects.create(
                course=cours["Lutte contre l'incendie"], scheduled_at=self._jour(12, 8), capacite_max=6, location="Centre de formation",
                instructor=self.chef_secteur_a)
            incendie.reservations.set([self.equipier_a2])
            incendie.attendees.set([self.equipier_a])
            TrainingSession.objects.create(course=cours["Habilitation électrique"], scheduled_at=self._jour(25, 9), capacite_max=2,
                                           location="Local formation du bord")
            TrainingSession.objects.create(course=cours["Lutte contre l'incendie"], scheduled_at=self._jour(-30, 8), status="DONE",
                                           capacite_max=6, location="Centre de formation")
            TrainingRecord.objects.create(user=self.equipier_a, course=cours["Lutte contre l'incendie"],
                                          completed_at=self.aujourdhui - timedelta(days=700), expires_at=self.aujourdhui + timedelta(days=30),
                                          validated_by=self.chef_secteur_a)
            TrainingRecord.objects.create(user=self.marin_b, course=cours["Lutte contre l'incendie"],
                                          completed_at=self.aujourdhui - timedelta(days=100), expires_at=self.aujourdhui + timedelta(days=630))
        ReferentFormation.objects.get_or_create(course=cours["Lutte contre l'incendie"], ship=self.bre, user=self.chef_secteur_a)
        TrainingRequirement.objects.get_or_create(course=cours["Lutte contre l'incendie"], applies_to_role="EQUIPIER", applies_to_ship=self.bre)

    # ---------- Tâches ----------

    def _taches(self):
        # Trois états : à jouer en direct (À faire), bloquée avec fil ouvert à l'équipage B, cycle complet terminé.
        chef, ivan = User.objects.get(username="chef_section_a"), User.objects.get(username="chef_secteur_b")
        demain, hier = self.aujourdhui + timedelta(days=1), self.aujourdhui - timedelta(days=1)
        if not Tache.objects.filter(titre="Contrôler le graissage des paliers de la ligne d'arbre").exists():
            taches_services.creer_tache(
                chef, self.equipier_a, "Contrôler le graissage des paliers de la ligne d'arbre", demain,
                "Relever l'état des graisseurs et signaler toute fuite.")
        if not Tache.objects.filter(titre="Remplacer le filtre du circuit d'huile").exists():
            tache = taches_services.creer_tache(
                chef, self.equipier_a2, "Remplacer le filtre du circuit d'huile", self.aujourdhui + timedelta(days=3))
            taches_services.demarrer(tache, self.equipier_a2)
            taches_services.signaler_blocage(tache, self.equipier_a2, "Filtre de rechange introuvable en magasin.")
            taches_services.ajouter_participant(tache, chef, ivan)
            taches_services.repondre(tache, ivan, "Une référence équivalente est au magasin de l'équipage B, je la fais passer.")
        if not Tache.objects.filter(titre="Vérifier l'étalonnage des sondes de température").exists():
            tache = taches_services.creer_tache(
                User.objects.get(username="chef_secteur_elec_a"), self.equipier_elec, "Vérifier l'étalonnage des sondes de température", hier)
            taches_services.demarrer(tache, self.equipier_elec)
            taches_services.rendre_compte(tache, self.equipier_elec, "Quatre sondes vérifiées, écart inférieur à 0,5 °C.")

    # ---------- Notifications et brouillons ----------

    def _notifications_et_brouillons(self):
        if not Notification.objects.filter(user=self.equipier_a, verb__startswith="Maintenance en retard").exists():
            for user, verbe, niveau, lue in [
                (self.equipier_a, "Maintenance en retard : Graissage des paliers (pompe de refroidissement bâbord).", NotificationLevel.WARNING, False),
                (self.equipier_a, "Ticket assigné : vibrations anormales à haut régime.", NotificationLevel.INFO, False),
                (self.equipier_a, "Vous êtes inscrit à la formation « Lutte contre l'incendie ».", NotificationLevel.INFO, True),
                (self.chef_secteur_a, "Anomalie grave : fuite d'huile sur le groupe électrogène n°1.", NotificationLevel.DANGER, False),
                (self.chef_secteur_a, "Occurrence à valider : nettoyage du séparateur d'eau de cale.", NotificationLevel.WARNING, False),
                (self.cdt_b, "Relève proposée : l'équipage B à bord. Votre validation est attendue.", NotificationLevel.WARNING, False),
                (self.second_a, "Stock sous le seuil : filtre à huile (rupture).", NotificationLevel.DANGER, False),
            ]:
                Notification.objects.create(user=user, verb=verbe, level=niveau, is_read=lue)
        ReleveEquipage.objects.get_or_create(ship=self.bre, statut="en_attente", defaults=dict(
            equipage_propose="B", propose_par=self.cdt_a))
        Brouillon.objects.get_or_create(user=self.equipier_a, cle="anomalie:nouvelle", defaults=dict(
            contenu={"titre": "Odeur de brûlé au local machine"}, libelle="Signalement d'anomalie", url="/anomalies/signaler/"))
