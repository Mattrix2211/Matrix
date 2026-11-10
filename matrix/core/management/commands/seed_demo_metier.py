"""Démonstration métier approfondie de la Bretagne (données entièrement fictives), au-dessus de seed_demo, seed_demo_mer_quai
et seed_demo_dense : calendrier sur six semaines, quarts et services à tous les états, fiches de maintenance détaillées,
anomalies suivies, logistique et notifications réalistes.

Isolée : refuse toute base qui n'est pas une base de démonstration. Idempotente : une relance ne crée aucun doublon.
Passe par les services réels (programme, tâches, échanges, absences, mouvements) afin que notifications, traces et droits
soient ceux de l'application ; aucun contournement des permissions."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from absences import services as absences_services
from absences.models import Absence, TypeAbsence
from accounts.models import ServiceFunctionChoice
from assets import fiche_maintenance
from assets.models import Installation, InstallationMaintenance, Location
from logistics.models import Anomalie, AnomalieStatutLog, CorrectiveTicket, MouvementStock, PartLineItem, PartRequest, StockPiece, TicketStatusLog
from logistics.stock import enregistrer_mouvement
from maintenance.models import MaintenanceExecution, MaintenanceOccurrence
from matrix.core.instance_demo import exiger_base_demo
from notifications.models import Notification, NotificationLevel
from org.models import Ship
from programme import services as programme_services
from programme.models import EvenementProgramme
from quarts import echanges as echanges_services
from quarts.models import ChefDeListe, CreneauServiceGarde, RemplacementChefDeListe, ServiceGarde
from logistics.perimetre import perimetre_tickets_q
from maintenance.perimetre import perimetre_occurrences_q
from quarts.activation import publier_a_titre_previsionnel
from quarts.remplacement import designer_remplacant
from taches import services as taches_services
from taches.models import Tache

User = get_user_model()
MARQUEUR = "seed_demo_metier"

# Fiches génériques : aucune procédure militaire ni donnée sensible, valeurs fictives.
FICHES = [
    {
        "installation": ("Ventilation du local machine", "VENT-LM"), "titre": "Nettoyage des filtres de ventilation", "periodicite": "Mensuelle",
        "duree": 40, "personnes": 2, "description": "Dépoussiérage et contrôle de l'état des filtres d'air du local machine.",
        "preparations": [("outil", "Aspirateur d'atelier", 1, None), ("outil", "Brosse douce", 1, None), ("piece", "Filtre d'air (jeu)", 1, "FLT-VENT"),
                         ("epi", "Masque anti-poussière", 1, None), ("epi", "Gants de manutention", 1, None),
                         ("consigne", "Ventilation arrêtée et consignée avant démontage.", 1, None)],
        "etapes": [("Arrêter et consigner la ventilation.", "Contrôler l'absence de rotation avant toute intervention."), ("Déposer les filtres et les nettoyer ou les remplacer.", ""),
                   ("Remonter, remettre en service et contrôler le débit au ressenti.", "")],
        "lignes": [("Ventilation consignée", "checkbox", "", True), ("Filtres nettoyés ou remplacés", "checkbox", "", True),
                   ("Remise en service sans bruit anormal", "checkbox", "", True), ("Observations", "text", "", False)],
    },
    {
        "installation": ("Éclairage de secours du pont 2", "ECL-P2"), "titre": "Essai de l'éclairage de secours", "periodicite": "Mensuelle",
        "duree": 30, "personnes": 1, "description": "Essai de basculement et contrôle de l'autonomie des blocs de secours.",
        "preparations": [("outil", "Chronomètre", 1, None), ("outil", "Fiche d'essai", 1, None), ("epi", "Lampe frontale", 1, None),
                         ("consigne", "Prévenir le service de quart avant coupure de l'alimentation normale.", 1, None)],
        "etapes": [("Prévenir le poste de quart.", ""), ("Couper l'alimentation normale du circuit et noter les blocs qui s'allument.", "Ne jamais laisser une coursive sans éclairage."),
                   ("Rétablir l'alimentation et noter les blocs défaillants.", "")],
        "lignes": [("Blocs allumés à la coupure", "number", "blocs", True), ("Blocs défaillants", "number", "blocs", True), ("Observations", "text", "", False)],
    },
    {
        "installation": ("Dispositif d'alarme incendie", "ALM-INC"), "titre": "Essai des détecteurs et de l'alarme", "periodicite": "Trimestrielle",
        "duree": 90, "personnes": 2, "description": "Essai fonctionnel des détecteurs d'un secteur et du report d'alarme à la passerelle.",
        "preparations": [("outil", "Générateur d'essai (fictif)", 1, None), ("epi", "Protections auditives", 1, None),
                         ("consigne", "Prévenir la passerelle et le chef de quart avant l'essai.", 1, None)],
        "etapes": [("Prévenir la passerelle.", ""), ("Déclencher l'essai sur chaque détecteur du secteur.", "Rester en liaison avec la passerelle."),
                   ("Vérifier le report d'alarme et réarmer.", "")],
        "lignes": [("Détecteurs essayés", "number", "unités", True), ("Report d'alarme reçu à la passerelle", "checkbox", "", True), ("Observations", "text", "", False)],
    },
    {
        "installation": ("Treuil d'embarcation", "TRE-1"), "titre": "Contrôle et graissage du treuil", "periodicite": "Trimestrielle",
        "duree": 60, "personnes": 2, "description": "Contrôle visuel du câble et des freins, graissage des points prévus.",
        "preparations": [("outil", "Pompe à graisse manuelle", 1, None), ("piece", "Cartouche de graisse (exemple fictif)", 2, None),
                         ("epi", "Gants de manutention", 1, None), ("epi", "Casque", 1, None), ("consigne", "Treuil consigné, charge au sol.", 1, None)],
        "etapes": [("Consigner le treuil et vérifier qu'aucune charge n'est suspendue.", "Ne jamais intervenir sous une charge."), ("Contrôler le câble : brins rompus, écrasements.", ""),
                   ("Graisser les points prévus et essuyer l'excédent.", "")],
        "lignes": [("Treuil consigné", "checkbox", "", True), ("Câble sans défaut visible", "checkbox", "", True),
                   ("Graissage effectué", "checkbox", "", True), ("Observations", "text", "", False)],
    },
]

# Rattachement organisationnel des installations des fiches (service, secteur, section) : celui de leurs exécutants.
PLACEMENT = {"VENT-LM": ("Propulsion", "Moteurs", "Moteurs bâbord"), "ECL-P2": ("Propulsion", "Moteurs", "Moteurs bâbord"),
             "TRE-1": ("Propulsion", "Moteurs", "Moteurs bâbord"), "ALM-INC": ("Sécurité", "Pompiers", "Sections incendie")}

ANOMALIES = [  # titre, gravité, parcours de statuts, localisation, service, secteur, auteur, responsable, note finale
    ("Ventilateur de la cale arrière bruyant", 3, ["SIGNALEE", "PRISE_EN_COMPTE", "TRAITEE"], "Cale arrière", "Propulsion", "Moteurs", "equipier_a", "chef_secteur_a"),
    ("Hublot de la coursive pont 1 qui suinte", 2, ["SIGNALEE", "PRISE_EN_COMPTE"], "Coursive pont 1", "Opérations", "Passerelle", "equipier_a2", "coma_comops"),
    ("Réserve de gants de manutention épuisée", 2, ["SIGNALEE", "PRISE_EN_COMPTE", "TRAITEE", "CLOTUREE"], "Magasin machine", "Propulsion", "Moteurs", "equipier_a", "chef_service_a"),
    ("Odeur de brûlé près du tableau électrique", 5, ["SIGNALEE", "PRISE_EN_COMPTE"], "Local tableaux", "Énergie", "Électricité", "equipier_elec_a", "chef_secteur_elec_a"),
    ("Désaccord sur le passage de consigne entre deux quarts", 2, ["SIGNALEE"], "Passerelle", "Opérations", "Passerelle", "equipier_a2", "coma_comops"),
    ("Pompe de cale : débit insuffisant à l'essai", 4, ["SIGNALEE", "PRISE_EN_COMPTE"], "Cale machine", "Propulsion", "Moteurs", "chef_section_a", "chef_secteur_a"),
]

PIECES = [  # référence, désignation, quantité, minimum, critique
    ("FLT-VENT", "Filtre d'air du local machine (jeu)", 6, 3, 1), ("GRS-01", "Cartouche de graisse", 14, 6, 2), ("GNT-MAN", "Gants de manutention (paire)", 0, 10, 3),
    ("LNP-SEC", "Lampe de bloc de secours", 3, 4, 1), ("DET-FUM", "Détecteur de fumée (rechange)", 8, 4, 2), ("CBL-TRE", "Câble de treuil (longueur)", 1, 1, 0),
    ("JNT-20", "Joint torique assorti", 25, 10, 3), ("ETQ-EXT", "Étiquette de contrôle extincteur", 40, 20, 5),
]


class Command(BaseCommand):
    help = "Ajoute la démonstration métier approfondie (calendrier, quarts, maintenance, anomalies, logistique, notifications)."

    def u(self, nom):
        return User.objects.get(username=nom)

    def _verifier_base_de_demonstration(self):
        exiger_base_demo("seed_demo_metier")
        if not Ship.objects.filter(name="Bretagne").exists():
            raise CommandError("Lancez d'abord seed_demo.")

    def _jour(self, decalage, heure=8):
        base = timezone.localtime().replace(hour=heure, minute=0, second=0, microsecond=0)
        return base + timedelta(days=decalage)

    @transaction.atomic
    def handle(self, *args, **options):
        self._verifier_base_de_demonstration()
        self.bre = Ship.objects.get(name="Bretagne")
        if AuditLog_marqueur_present():
            self._complements()
            self.stdout.write("Démonstration métier déjà générée : compléments appliqués si nécessaire.")
            return
        self._absences_et_remplacement()
        self._calendrier()
        self._quarts_et_services()
        self._echanges_equipier_a()
        self._maintenance()
        self._anomalies()
        self._logistique()
        self._taches()
        self._notifications()
        self._complements()
        poser_marqueur()
        self.stdout.write(self.style.SUCCESS("Démonstration métier prête (calendrier, quarts, maintenance, anomalies, logistique, notifications)."))

    # ---------- Absences et remplacement ----------

    def _absences_et_remplacement(self):
        types = {t.name: t for t in TypeAbsence.objects.all()}
        chef = self.u("chef_secteur_a")
        for marin, type_, debut, fin, motif in (
            ("equipier_a2", "Permission", 12, 16, "Permission annuelle (démonstration)"),
            ("chef_section_a", "Stage", 5, 7, "Stage de qualification (démonstration)"),
            ("equipier_elec_a", "Repos compensateur", -2, -1, "Repos après une période de quart"),
        ):
            if Absence.objects.filter(marin=self.u(marin), date_debut=timezone.localdate() + timedelta(days=debut)).exists():
                continue
            absence = absences_services.declarer_absence(
                self.u(marin), self.u(marin), types[type_], timezone.localdate() + timedelta(days=debut),
                timezone.localdate() + timedelta(days=fin), motif)
            if marin != "equipier_a2":  # une absence reste « déclarée » pour montrer l'état en attente de validation
                absences_services.valider_absence(absence, self.u("chef_secteur_elec_a" if marin == "equipier_elec_a" else "chef_secteur_a"))
        # Le chef de liste est absent : son remplaçant temporaire peut activer, reporter ou retirer une prévision.
        designation = ChefDeListe.objects.filter(user=chef, type_liste=ChefDeListe.TYPE_QUAI).first()
        if designation and not RemplacementChefDeListe.objects.filter(titulaire=chef).exists():
            designer_remplacant(self.u("chef_service_a"), designation, self.u("equipier_a2"), timezone.now(), timezone.now() + timedelta(hours=60),
                                "Absence du chef de liste (démonstration)")

    # ---------- Calendrier : six semaines d'activité ----------

    def _calendrier(self):
        types = {t.nom: t.pk for t in programme_services.types_du_navire(self.bre.pk)}
        second, cible = self.u("second_a"), f"ship:{self.bre.pk}"
        evenements = [
            (-9, 8, 0, "Escale", "Escale à quai : approvisionnement (démonstration)"), (-6, 9, 0, "Exercice", "Exercice de lutte contre l'incendie"),
            (-3, 14, 0, "Réunion", "Réunion de service Propulsion"), (1, 9, 0, "Réunion", "Réunion de préparation de l'appareillage"),
            (2, 8, 0, "Exercice", "Préparation à l'appareillage : essais avant départ"), (4, 8, 1, "Arrêt technique", "Arrêt technique des auxiliaires"),
            (8, 7, 0, "Exercice", "Appareillage fictif et journée de mer : manœuvres"), (9, 8, 2, "Exercice", "Journées de mer : exercices de sécurité"),
            (13, 9, 0, "Escale", "Retour à quai et accostage prévu (démonstration)"), (17, 14, 0, "Réunion", "Revue des échéances de maintenance"),
            (21, 8, 3, "Arrêt technique", "Arrêt technique programmé du réducteur"), (26, 10, 0, "Réunion", "Réunion de coordination mensuelle"),
            (33, 8, 0, "Exercice", "Exercice d'abandon (démonstration)"),
        ]
        crees = {}
        for decalage, heure, duree, type_, titre in evenements:
            if EvenementProgramme.objects.filter(titre=titre).exists():
                crees[titre] = EvenementProgramme.objects.get(titre=titre)
                continue
            debut = self._jour(decalage, heure)
            crees[titre] = programme_services.creer_evenement(second, titre, types[type_], debut, debut + timedelta(days=duree) if duree else None, cible,
                                                              lieu="À bord (démonstration)")
        # Un événement annulé et un reporté, avec leur trace.
        annule = crees["Exercice d'abandon (démonstration)"]
        if not annule.annule:
            programme_services.annuler_evenement(second, annule, "Indisponibilité de l'embarcation (démonstration)")
        reporte = crees["Revue des échéances de maintenance"]
        if "Reporté" not in reporte.description:
            programme_services.modifier_evenement(second, reporte, reporte.titre, reporte.debut + timedelta(days=2), reporte.fin,
                                                  lieu=reporte.lieu, description="Reporté de deux jours (démonstration).")

    # ---------- Quarts et services à quai à tous les états ----------

    def _quarts_et_services(self):
        chef, fonction = self.u("chef_secteur_a"), ServiceFunctionChoice.objects.get_or_create(name="Fraction de service à quai")[0]
        # Effectif sans quart ni service concurrent sur ces dates : aucune double affectation créée par la démonstration.
        equipe = [self.u(n) for n in ("equipier_elec_a", "equipier_incendie_a", "chef_section_a", "second_a", "coma_comanav")]
        postes = ("Officier de garde (OG)", "Gradé de coupée 1", "Gradé mécanicien", "Gradé électricien", "Gradé sécurité")

        def liste(nom, decalage, statut):
            if ServiceGarde.objects.filter(nom=nom).exists():
                return None
            debut = self._jour(decalage, 8)
            garde = ServiceGarde.objects.create(
                nom=nom, ship=self.bre, equipage="A", date_debut=debut.date(), date_fin=debut.date(), type_service="Service à quai",
                duree_creneau_heures=24, fonction=fonction, created_by=chef)
            for i, poste in enumerate(postes):
                marin = None if (statut == "BROUILLON" and i == 4) else equipe[(i + decalage) % len(equipe)]
                CreneauServiceGarde.objects.create(service_garde=garde, poste=poste, marin=marin, debut=debut, fin=debut + timedelta(hours=24))
            return garde

        passee = liste("Service à quai — effectué le mois dernier", -4, "PUBLIEE")
        if passee:
            passee.publier(chef)
        brouillon = liste("Service à quai — brouillon (poste non pourvu)", 9, "BROUILLON")
        proposee = liste("Service à quai — proposé, en attente de validation", 11, "PROPOSEE")
        if proposee:
            proposee.proposer(chef)

    # ---------- Échanges concernant equipier_a ----------

    def _echanges_equipier_a(self):
        a, a2 = self.u("equipier_a"), self.u("equipier_a2")
        if echanges_services.EchangeService.objects.filter(demandeur=a2, cible=a).exists():
            return
        limite = timezone.now() + timedelta(days=2)
        for creneau_a in CreneauServiceGarde.objects.filter(marin=a, debut__gt=limite, service_garde__statut="PUBLIEE",
                                                           service_garde__application="ACTIVE").order_by("debut"):
            creneau_a2 = CreneauServiceGarde.objects.filter(service_garde=creneau_a.service_garde, marin=a2).exclude(pk=creneau_a.pk).first()
            if creneau_a2 and creneau_a2.debut > limite:
                try:
                    echanges_services.proposer_echange(a2, creneau_a2, creneau_a, "Rendez-vous médical (démonstration)")
                except echanges_services.EchangeImpossible:
                    continue
                return

    # ---------- Maintenance : fiches détaillées et états variés ----------

    def _maintenance(self):
        chef, marin = self.u("chef_secteur_a"), self.u("equipier_a")
        local = Location.objects.filter(ship=self.bre).first()
        pieces = {p.reference: p.pk for p in StockPiece.objects.filter(ship=self.bre)}
        occurrences = {}
        for contenu in FICHES:
            designation, ref = contenu["installation"]
            service, secteur, section = self._placement(ref)
            installation, _ = Installation.objects.get_or_create(ship=self.bre, designation=designation, defaults=dict(
                service=service, sector=secteur, section=section, location=local, reference=ref, local=local.name if local else "",
                gisement="Pont 2", created_by=chef))
            fiche = InstallationMaintenance.objects.filter(installation=installation, title=contenu["titre"]).first()
            if fiche is None:
                fiche = InstallationMaintenance.objects.create(
                    installation=installation, periodicity=contenu["periodicite"], title=contenu["titre"], description=contenu["description"],
                    planned_duration_min=contenu["duree"], people_count=contenu["personnes"], mode_declenchement="CALENDRIER",
                    intervalle=1, unite_intervalle="M", created_by=chef)
                fiche_maintenance.enregistrer_version_directe(fiche, chef, "Fiche de démonstration")
                version = fiche.version_validee
                fiche_maintenance.remplacer_contenu(version, {
                    **fiche_maintenance.contenu_de(version),
                    "preparations": [{"type": t, "libelle": lib, "quantite": q, "piece": pieces.get(r)} for t, lib, q, r in contenu["preparations"]],
                    "etapes": [{"texte": texte, "attention": att} for texte, att in contenu["etapes"]],
                    "lignes": [{"label": lib, "field_type": champ, "unit": unite, "required": oblig} for lib, champ, unite, oblig in contenu["lignes"]],
                })
            occurrences[contenu["titre"]] = fiche
        if MaintenanceOccurrence.objects.filter(installation_maintenance__in=occurrences.values()).exists():
            return
        j = timezone.localdate()

        def occurrence(titre, decalage, statut, assignes=(), priorite=2):
            occ = MaintenanceOccurrence.objects.create(installation_maintenance=occurrences[titre], scheduled_for=j + timedelta(days=decalage), status=statut, priority=priorite)
            occ.assignees.set([self.u(n) for n in assignes])
            return occ

        terminee = occurrence("Essai de l'éclairage de secours", -14, "DONE", ["equipier_a"])
        MaintenanceExecution.objects.create(
            occurrence=terminee, started_at=self._jour(-14, 9), completed_at=self._jour(-14, 9) + timedelta(minutes=35), executed_by=marin,
            results={"Observations": {"etat": "conforme", "commentaire": "Deux blocs remplacés."}}, measurements={"Blocs allumés à la coupure": 18, "Blocs défaillants": 2},
            conformity="A_SURVEILLER", notes="Deux blocs de secours remplacés.", valide_par=chef, date_validation=self._jour(-13, 8))
        en_cours = occurrence("Contrôle et graissage du treuil", 0, "IN_PROGRESS", ["equipier_a"], 3)
        MaintenanceExecution.objects.create(occurrence=en_cours, started_at=timezone.now() - timedelta(minutes=25), executed_by=marin, notes="Câble contrôlé, graissage à faire.")
        occurrence("Nettoyage des filtres de ventilation", -6, "OVERDUE", ["equipier_a2"])
        occurrence("Essai des détecteurs et de l'alarme", 6, "ASSIGNED", ["equipier_incendie_a"], 3)
        occurrence("Essai de l'éclairage de secours", 24, "PLANNED")
        occurrence("Nettoyage des filtres de ventilation", 30, "CANCELLED")

    # ---------- Anomalies suivies ----------

    def _anomalies(self):
        for titre, gravite, parcours, lieu, service, secteur, auteur, responsable in ANOMALIES:
            if Anomalie.objects.filter(titre=titre).exists():
                continue
            svc = self.bre.services.get(name=service)
            anomalie = Anomalie.objects.create(
                titre=titre, description="Signalement de démonstration (données fictives).", gravite=gravite, statut=parcours[-1], localisation=lieu,
                ship=self.bre, service=svc, sector=svc.sectors.get(name=secteur), created_by=self.u(auteur))
            ancien = None
            for etape in parcours:
                AnomalieStatutLog.objects.create(anomalie=anomalie, ancien_statut=ancien or "", nouveau_statut=etape, user=self.u(auteur) if ancien is None else self.u(responsable),
                                                 note="Déclaration" if ancien is None else {"PRISE_EN_COMPTE": "Prise en compte", "TRAITEE": "Traitée", "CLOTUREE": "Clôture"}.get(etape, ""))
                ancien = etape

    # ---------- Logistique et inventaire ----------

    def _logistique(self):
        chef = self.u("chef_secteur_a")
        propulsion = self.bre.services.get(name="Propulsion")
        secteur = propulsion.sectors.get(name="Moteurs")
        for ref, designation, quantite, minimum, critique in PIECES:
            piece, creee = StockPiece.objects.get_or_create(ship=self.bre, reference=ref, defaults=dict(
                designation=designation, quantite_minimale=minimum, quantite_critique=critique, service=propulsion, sector=secteur, emplacement="Magasin machine"))
            if creee and quantite:
                enregistrer_mouvement(chef, piece, MouvementStock.INVENTAIRE, quantite, motif="Inventaire initial")
        # Consommations et réception : l'historique des mouvements raconte la vie du stock.
        for ref, type_, quantite, motif in (("GRS-01", MouvementStock.SORTIE, 2, "Graissage des paliers"), ("JNT-20", MouvementStock.SORTIE, 5, "Remplacement de joints"),
                                            ("DET-FUM", MouvementStock.ENTREE, 4, "Réception de la commande")):
            piece = StockPiece.objects.get(ship=self.bre, reference=ref)
            if not MouvementStock.objects.filter(piece=piece, motif=motif).exists():
                enregistrer_mouvement(chef, piece, type_, quantite, motif=motif)
        # Besoin de matériel relié à une fiche : ticket de ventilation en attente de pièces, commande en cours.
        ticket = CorrectiveTicket.objects.filter(description__startswith="Filtres de ventilation colmatés").first()
        if ticket is None:
            installation = Installation.objects.filter(ship=self.bre, reference="VENT-LM").first()
            ticket = CorrectiveTicket.objects.create(installation=installation, description="Filtres de ventilation colmatés : remplacement à prévoir.", severity=3,
                                                     status="WAITING_PARTS", created_by=self.u("equipier_a"), reported_at=self._jour(-8))
            ticket.assignees.set([self.u("equipier_a")])
            for ancien, nouveau, auteur in (("REPORTED", "REPORTED", "equipier_a"), ("REPORTED", "DIAGNOSED", "chef_secteur_a"), ("DIAGNOSED", "WAITING_PARTS", "chef_secteur_a")):
                TicketStatusLog.objects.create(ticket=ticket, old_status=ancien, new_status=nouveau, user=self.u(auteur), note="")
            demande = PartRequest.objects.create(ticket=ticket, requested_by=chef, needed_by_date=timezone.localdate() + timedelta(days=10))
            PartLineItem.objects.create(part_request=demande, reference="FLT-VENT", description="Filtre d'air du local machine (jeu)", qty=3, status="ORDERED",
                                        vendor="Fournisseur fictif", order_number="CMD-DEMO-017", estimated_cost=Decimal("84.00"), ordered_at=self._jour(-4))
            PartLineItem.objects.create(part_request=demande, reference="GNT-MAN", description="Gants de manutention (paire)", qty=20, status="TO_ORDER",
                                        estimated_cost=Decimal("60.00"))

    # ---------- Tâches de la journée ----------

    def _taches(self):
        chef, marin = self.u("chef_secteur_a"), self.u("equipier_a")
        for titre, echeance, priorite in (
            ("Préparer l'inventaire mensuel du magasin machine", 3, "NORMALE"), ("Mettre à jour la liste des consignes de quart", 6, "NORMALE"),
            ("Contrôler l'état des gilets de sauvetage du poste machine", 1, "URGENTE"),
        ):
            if not Tache.objects.filter(titre=titre).exists():
                taches_services.creer_tache(chef, marin, titre, echeance=timezone.localdate() + timedelta(days=echeance),
                                            description="Tâche de démonstration.", priorite=priorite)

    # ---------- Notifications : lues, non lues, à traiter ----------

    def _notifications(self):
        """Boîtes réalistes : des dates étalées sur dix jours, l'ancien est lu, le récent reste à lire ; les alertes
        prioritaires et les actions à traiter restent visibles. Matrix n'archive pas les notifications : lues / non lues seulement."""
        maintenant = timezone.now()
        a = self.u("equipier_a")
        if not Notification.objects.filter(user=a, verb__startswith="Alerte prioritaire (démonstration)").exists():
            Notification.objects.create(user=a, verb="Alerte prioritaire (démonstration) : exercice d'alerte incendie vendredi à 14 h, rassemblement au poste.",
                                        level=NotificationLevel.DANGER, url="/", regime="COMMUNES", categorie="anomalie")
        for user in User.objects.filter(notifications__isnull=False).distinct():
            notifications = list(Notification.objects.filter(user=user).order_by("created_at", "pk"))
            total = len(notifications)
            for rang, notification in enumerate(notifications):
                age = timedelta(days=10) * (total - rang) / total
                recente = rang >= total - 6
                garde_non_lue = notification.level == NotificationLevel.DANGER or (notification.action_requise and not notification.traitee_le)
                Notification.objects.filter(pk=notification.pk).update(
                    created_at=maintenant - age, is_read=notification.is_read or not (recente or garde_non_lue))


    # ---------- Compléments (rejouables, gardés par des tests d'existence) ----------

    def _complements(self):
        self._placer_les_installations()
        self._coherence_des_assignations()
        self._historiques_d_anomalies()
        self._conflit_d_activation()
        self._tache_bloquee_d_equipier_a()
        self._ticket_du_chef_de_secteur()

    def _ticket_du_chef_de_secteur(self):
        """Le chef de secteur a au moins un ticket à suivre dans « Mes tickets » (le plus avancé de son périmètre)."""
        chef = self.u("chef_secteur_a")
        if CorrectiveTicket.objects.filter(assignees=chef).exists():
            return
        ticket = CorrectiveTicket.objects.filter(perimetre_tickets_q(chef), status__in=("BLOCKED", "WAITING_PARTS", "IN_REPAIR")).order_by("pk").first()
        if ticket:
            ticket.assignees.add(chef)

    def _tache_bloquee_d_equipier_a(self):
        """Cas particulier visible depuis equipier_a : une tâche bloquée par la rupture de stock des gants (voir Logistique)."""
        titre = "Distribuer les gants de manutention neufs au poste machine"
        if Tache.objects.filter(titre=titre).exists():
            return
        chef, marin = self.u("chef_secteur_a"), self.u("equipier_a")
        tache = taches_services.creer_tache(chef, marin, titre, echeance=timezone.localdate() + timedelta(days=4), description="Tâche de démonstration.")
        taches_services.signaler_blocage(tache, marin, "Gants en rupture de stock : commande en attente (voir Logistique)")

    def _placement(self, reference):
        service_nom, secteur_nom, section_nom = PLACEMENT[reference]
        service = self.bre.services.get(name=service_nom)
        secteur = service.sectors.get(name=secteur_nom)
        return service, secteur, secteur.sections.filter(name=section_nom).first()

    def _placer_les_installations(self):
        for reference in PLACEMENT:
            service, secteur, section = self._placement(reference)
            Installation.objects.filter(ship=self.bre, reference=reference).update(service=service, sector=secteur, section=section)

    def _coherence_des_assignations(self):
        """Un tour de maintenance ou un ticket n'est jamais assigné à quelqu'un qui n'y a pas accès (il verrait une page introuvable) :
        l'assigné hors périmètre est remplacé par un collègue de même équipage et de même fonction ayant accès."""
        candidats = list(User.objects.filter(profile__ship=self.bre, is_active=True).select_related("profile").order_by("username"))
        for modele, filtre in ((CorrectiveTicket, perimetre_tickets_q), (MaintenanceOccurrence, perimetre_occurrences_q)):
            for objet in modele.objects.prefetch_related("assignees"):
                for assigne in list(objet.assignees.all()):
                    if modele.objects.filter(filtre(assigne), pk=objet.pk).exists():
                        continue
                    objet.assignees.remove(assigne)
                    eligibles = [c for c in candidats if c.pk != assigne.pk and modele.objects.filter(filtre(c), pk=objet.pk).exists()]
                    eligibles.sort(key=lambda c: (c.profile.role != assigne.profile.role, c.profile.equipage != assigne.profile.equipage, c.username))
                    if eligibles:
                        objet.assignees.add(eligibles[0])

    def _historiques_d_anomalies(self):
        """Toute anomalie a un historique cohérent avec son état (déclaration, prise en compte, traitement, clôture)."""
        parcours = ["SIGNALEE", "PRISE_EN_COMPTE", "TRAITEE", "CLOTUREE"]
        for anomalie in Anomalie.objects.exclude(pk__in=AnomalieStatutLog.objects.values("anomalie")):
            responsable = self.u("chef_secteur_a")
            auteur = anomalie.created_by or responsable
            ancien = ""
            for etape in parcours[:parcours.index(anomalie.statut) + 1]:
                AnomalieStatutLog.objects.create(
                    anomalie=anomalie, ancien_statut=ancien, nouveau_statut=etape, user=auteur if not ancien else responsable,
                    note="Déclaration" if not ancien else {"PRISE_EN_COMPTE": "Prise en compte", "TRAITEE": "Traitée", "CLOTUREE": "Clôture"}[etape])
                ancien = etape

    def _conflit_d_activation(self):
        """Une liste prévisionnelle dont un tour recouvre un service à quai déjà en vigueur : l'activation est bloquée tant que
        les responsables n'ont pas résolu le recouvrement (Matrix ne modifie aucune affectation)."""
        nom = "Permanence prévisionnelle — conflit d'affectation (démonstration)"
        if ServiceGarde.objects.filter(nom=nom).exists():
            return
        existant = CreneauServiceGarde.objects.filter(
            service_garde__ship=self.bre, service_garde__application=ServiceGarde.APPLICATION_ACTIVE, service_garde__statut="PUBLIEE",
            marin__isnull=False, debut__gt=timezone.now() + timedelta(days=1)).order_by("debut").first()
        if existant is None:
            return
        chef = self.u("chef_secteur_a")
        fonction = ServiceFunctionChoice.objects.get_or_create(name="Fraction de service à quai")[0]
        liste = ServiceGarde.objects.create(
            nom=nom, ship=self.bre, equipage="A", date_debut=existant.debut.date(), date_fin=existant.fin.date(), type_service="Service à quai",
            duree_creneau_heures=24, fonction=fonction, created_by=chef)
        CreneauServiceGarde.objects.create(service_garde=liste, poste="Gradé de coupée 1", marin=existant.marin, debut=existant.debut, fin=existant.fin)
        liste.proposer(chef)
        publier_a_titre_previsionnel(self.u("cdt_a"), liste, timezone.now() + timedelta(hours=3))


def AuditLog_marqueur_present():
    from accounts.models import AuditLog
    return AuditLog.objects.filter(action=MARQUEUR).exists()


def poser_marqueur():
    from accounts.models import AuditLog
    AuditLog.objects.create(action=MARQUEUR, details="Démonstration métier générée (données fictives).")
