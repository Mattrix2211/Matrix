"""Enrichit une base de démonstration déjà préparée par `seed_demo` : volumes et liens réalistes pour juger les interfaces
chargées (tâches, anomalies liées à des tickets, maintenances, programme, documents, RETEX, postes, absences, notifications,
quarts à la mer et service à quai, échanges de tours à tous les états).

Isolée : refuse toute base qui n'est pas une base de démonstration (compte `equipier_a` au mot de passe fictif).
Reproductible : graine fixe, dates relatives à aujourd'hui, identités entièrement fictives, idempotente.
N'introduit aucune organisation non validée : elle réutilise les services, secteurs et sections existants de la Bretagne,
et aucune double affectation (quart à la mer et service à quai au même moment) : les périodes sont disjointes."""
import random
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from absences import services as absences_services
from absences.models import TypeAbsence
from accounts.models import AuditLog, FonctionQuartChoice, ServiceFunctionChoice
from annonces import services as annonces_services
from assets.models import Asset, Installation
from demandes import services as demandes_services
from documentation import services as documentation_services
from logistics.models import Anomalie, AnomalieStatutLog, CorrectiveTicket, TicketStatusLog
from maintenance.models import MaintenanceExecution, MaintenanceOccurrence, MaintenancePlan
from notifications.models import Notification, NotificationLevel
from org.models import Sector, Service, Ship
from postes import services as postes_services
from programme import services as programme_services
from quarts import echanges as echanges_services
from quarts.models import ChefDeListe, CreneauQuart, CreneauServiceGarde, Quart, ServiceGarde
from retex import services as retex_services
from taches import services as taches_services
from taches.models import Tache

User = get_user_model()
MOT_DE_PASSE = "pass"
MARQUEUR = "seed_demo_dense"
GRAINE = 20261103

# Identités entièrement fictives : aucun nom de rôle, grades cohérents avec le référentiel de démonstration.
IDENTITES = [
    ("Lucas", "Marchand", "Matelot"), ("Inès", "Garnier", "Matelot"), ("Théo", "Bernard", "Matelot"), ("Sarah", "Colin", "Quartier-maître"),
    ("Yanis", "Roussel", "Matelot"), ("Élise", "Faure", "Second-maître"), ("Maël", "Dubois", "Matelot"), ("Nina", "Perrin", "Quartier-maître"),
    ("Hugo", "Lefèvre", "Second-maître"), ("Camille", "Girard", "Matelot"), ("Zoé", "Lambert", "Matelot"), ("Noé", "Fontaine", "Quartier-maître"),
    ("Jade", "Moreau", "Matelot"), ("Louis", "Chevalier", "Maître"), ("Manon", "Renard", "Matelot"), ("Adam", "Blanchard", "Quartier-maître"),
    ("Léa", "Guérin", "Matelot"), ("Nathan", "Boyer", "Second-maître"),
]
INDEX_CONVERTIS = (1, 2, 4, 5, 8, 10)
PARCOURS_TICKETS = (
    ["REPORTED"], ["REPORTED", "DIAGNOSED"], ["REPORTED", "DIAGNOSED", "IN_REPAIR"],
    ["REPORTED", "DIAGNOSED", "IN_REPAIR", "TESTING", "RETURNED_TO_SERVICE", "CLOSED"],
)
# (service, secteur, section, chef qui attribue)
AFFECTATIONS = (
    [("Propulsion", "Moteurs", "Moteurs bâbord", "chef_secteur_a")] * 5
    + [("Propulsion", "Auxiliaires", "Pompes", "chef_service_a")] * 3
    + [("Énergie", "Électricité", "Tableaux", "chef_secteur_elec_a")] * 4
    + [("Sécurité", "Pompiers", "Sections incendie", "chef_secteur_incendie_a")] * 3
    + [("Opérations", "Passerelle", "Veille", "coma_comops")] * 3
)


def doubles_affectations(marins=None):
    """Couples (marin, créneau, créneau) qui se chevauchent entre quarts à la mer et services à quai publiés."""
    creneaux = [("garde", c) for c in CreneauServiceGarde.objects.filter(service_garde__statut="PUBLIEE", marin__isnull=False)]
    creneaux += [("quart", c) for c in CreneauQuart.objects.filter(quart__statut="PUBLIEE", marin__isnull=False)]
    if marins is not None:
        creneaux = [x for x in creneaux if x[1].marin_id in marins]
    par_marin = {}
    for genre, c in creneaux:
        par_marin.setdefault(c.marin_id, []).append((genre, c))
    conflits = []
    for marin_id, lignes in par_marin.items():
        lignes.sort(key=lambda x: x[1].debut)
        for i, (g1, c1) in enumerate(lignes):
            for g2, c2 in lignes[i + 1:]:
                if c2.debut >= c1.fin:
                    break
                conflits.append((marin_id, c1.pk, c2.pk))
    return conflits


class Command(BaseCommand):
    help = "Enrichit la base de démonstration (volumes, liens, échanges) ; refuse toute autre base."

    def add_arguments(self, parser):
        parser.add_argument("--forcer", action="store_true", help="Regénère même si le marqueur existe (ajoute des données).")

    def handle(self, *args, **options):
        self.alea = random.Random(GRAINE)
        self.aujourdhui = timezone.localdate()
        self._verifier_base_de_demonstration()
        if AuditLog.objects.filter(action=MARQUEUR).exists() and not options["forcer"]:
            self.stdout.write("Jeu dense déjà généré : rien à faire.")
            return
        avant = {u.pk for u in User.objects.all()}
        with transaction.atomic():
            self._charger_contexte()
            self._marins()
            self._taches()
            self._anomalies_et_tickets()
            self._maintenance()
            self._programme_annonces_demandes()
            self._documents_et_retex()
            self._postes_et_absences()
            self._quai_et_echanges()
            self._quart_a_la_mer()
            self._notifications()
            AuditLog.objects.create(action=MARQUEUR, details=f"Jeu dense généré le {self.aujourdhui} (graine {GRAINE}).")
        creees = User.objects.exclude(pk__in=avant).count()
        conflits = doubles_affectations({u.pk for u in User.objects.filter(username__startswith="m_")})
        self.stdout.write(self.style.SUCCESS(
            f"Jeu dense généré : {creees} marins fictifs, {Tache.objects.count()} tâches, {Anomalie.objects.count()} anomalies, "
            f"{CorrectiveTicket.objects.count()} tickets, {MaintenanceOccurrence.objects.count()} occurrences. "
            f"Doubles affectations mer/quai des marins ajoutés : {len(conflits)}."))

    # ---------- Garde-fous ----------

    def _verifier_base_de_demonstration(self):
        marin = User.objects.filter(username="equipier_a").first()
        if marin is None or not marin.check_password(MOT_DE_PASSE) or not Ship.objects.filter(name="Bretagne", code="BRE").exists():
            raise CommandError("Refus : ce n'est pas une base de démonstration (seed_demo absent ou mots de passe non fictifs).")

    def _charger_contexte(self):
        self.bre = Ship.objects.get(code="BRE")
        self.services = {s.name: s for s in Service.objects.filter(ship=self.bre)}
        self.secteurs = {s.name: s for s in Sector.objects.filter(service__ship=self.bre)}
        self.u = lambda nom: User.objects.get(username=nom)  # noqa: E731
        self.hier, self.demain = self.aujourdhui - timedelta(days=1), self.aujourdhui + timedelta(days=1)
        self.installations = list(Installation.objects.filter(ship=self.bre).order_by("designation"))
        self.materiels = list(Asset.objects.filter(ship=self.bre).order_by("internal_id"))

    def _jour(self, decalage, heure=0):
        return timezone.make_aware(datetime.combine(self.aujourdhui + timedelta(days=decalage), datetime.min.time())) + timedelta(hours=heure)

    # ---------- Marins ----------

    def _marins(self):
        from org.models import Section
        self.marins = []
        for (prenom, nom, grade), (service, secteur, section, chef) in zip(IDENTITES, AFFECTATIONS):
            user, cree = User.objects.get_or_create(username=f"m_{nom.lower().replace('è', 'e').replace('é', 'e').replace('ï', 'i')}", defaults={
                "first_name": prenom, "last_name": nom})
            if cree:
                user.set_password(MOT_DE_PASSE)
                user.save()
            profil = user.profile
            profil.role, profil.ship, profil.equipage, profil.grade = "EQUIPIER", self.bre, "A", grade
            profil.service, profil.sector = self.services[service], self.secteurs[secteur]
            profil.section = Section.objects.get(sector=self.secteurs[secteur], name=section)
            profil.save()
            self.marins.append((user, chef))

    # ---------- Tâches ----------

    def _taches(self):
        titres = [
            "Relever les températures des paliers", "Contrôler le niveau d'huile du réducteur", "Purger le circuit de refroidissement",
            "Inventorier les pièces de rechange du magasin", "Vérifier l'étanchéité de la porte de coupée", "Nettoyer le local des batteries",
            "Contrôler les extincteurs du pont 2", "Mettre à jour le registre des rondes machine", "Tester l'éclairage de secours",
            "Vérifier les gilets de sauvetage", "Relever les compteurs d'heures des groupes", "Graisser les charnières des portes étanches",
            "Préparer le dossier d'exercice avaries", "Contrôler la pression des bouteilles d'air", "Étalonner les sondes de température",
            "Ranger l'armoire des EPI", "Remplacer le joint de la pompe de cale", "Vérifier les feux de navigation",
            "Mettre à jour la fiche de consignation", "Contrôler les câbles de remorquage", "Inspecter les sacs de matériel de lutte",
            "Réviser le manuel de poste incendie", "Nettoyer les filtres de ventilation", "Noter les relevés de vibrations",
            "Mettre à jour le tableau des habilitations", "Contrôler les sirènes d'alarme", "Vérifier les purges du compresseur",
            "Rédiger le compte rendu de l'exercice",
        ]
        for i, titre in enumerate(titres):
            marin, chef = self.marins[i % len(self.marins)]
            decalage = self.alea.choice([-6, -3, -1, 0, 1, 2, 3, 5, 8, 12])
            urgente = i % 5 == 0
            tache = taches_services.creer_tache(
                self.u(chef), marin, titre, self.aujourdhui + timedelta(days=decalage),
                "Tâche de démonstration (données fictives).",
                priorite=Tache.PRIORITE_URGENTE if urgente else Tache.PRIORITE_NORMALE)
            avancement = i % 6
            if avancement in (1, 2, 3, 4):
                taches_services.demarrer(tache, marin)
            if avancement == 3:
                taches_services.signaler_blocage(tache, marin, "Pièce ou accès indisponible : en attente d'un interlocuteur.")
            if avancement in (4, 5):
                if avancement == 5:
                    taches_services.demarrer(tache, marin)
                taches_services.rendre_compte(tache, marin, "Réalisé, rien à signaler (compte rendu fictif).")

    # ---------- Anomalies, tickets ----------

    def _ticket(self, cible, description, gravite, parcours, auteur, assignes=(), **extra):
        attribut = {"installation": cible} if isinstance(cible, Installation) else {"asset": cible}
        ticket = CorrectiveTicket.objects.create(
            description=description, severity=gravite, status=parcours[-1], created_by=auteur,
            reported_at=self._jour(-len(parcours) - 1), **attribut, **extra)
        ticket.assignees.set(assignes)
        ancien = "REPORTED"
        for i, statut in enumerate(parcours):
            TicketStatusLog.objects.create(ticket=ticket, old_status=ancien if i else "REPORTED", new_status=statut, user=auteur, note="")
            ancien = statut
        return ticket

    def _anomalies_et_tickets(self):
        sujets = [
            ("Suintement d'huile au palier arrière", 3), ("Bruit anormal sur la ventilation du local machine", 2),
            ("Éclairage de coursive défaillant", 2), ("Porte étanche difficile à manœuvrer", 3), ("Fuite d'eau sous le tableau électrique", 4),
            ("Extincteur déchargé dans le couloir tribord", 4), ("Vibration sur la ligne d'arbre à haut régime", 4),
            ("Sonde de température hors service", 2), ("Odeur de brûlé près du groupe électrogène", 5), ("Main courante desserrée", 1),
            ("Alarme incendie intempestive", 3), ("Joint de hublot fendu", 2), ("Écoulement lent de la cale", 3), ("Voyant de pression clignotant", 2),
        ]
        statuts = ["SIGNALEE", "SIGNALEE", "PRISE_EN_COMPTE", "PRISE_EN_COMPTE", "TRAITEE", "CLOTUREE", "SIGNALEE"]
        equipements = self.installations + self.materiels
        for i, (titre, gravite) in enumerate(sujets):
            cible = equipements[i % len(equipements)]
            marin, chef = self.marins[(i * 3) % len(self.marins)]
            service = getattr(cible, "service", None) or self.services["Propulsion"]
            secteur = getattr(cible, "sector", None) or self.secteurs["Moteurs"]
            attribut = {"installation": cible} if isinstance(cible, Installation) else {"asset": cible}
            anomalie = Anomalie.objects.create(
                titre=titre, description="Constat de démonstration (données fictives).", gravite=gravite, localisation="À bord",
                ship=self.bre, service=service, sector=secteur, created_by=marin, statut="SIGNALEE", **attribut)
            statut = statuts[i % len(statuts)]
            if i in INDEX_CONVERTIS:  # conversion en ticket : lien anomalie → ticket, rattachement et suivi à plusieurs états
                parcours = PARCOURS_TICKETS[INDEX_CONVERTIS.index(i) % len(PARCOURS_TICKETS)]
                ticket = self._ticket(cible, f"{titre}\nConstat de démonstration (données fictives).", gravite, parcours, self.u(chef),
                                      assignes=[marin] if len(parcours) > 1 else [])
                TicketStatusLog.objects.filter(ticket=ticket, old_status="REPORTED", new_status="REPORTED").update(note=f"Créé depuis l'anomalie « {titre} »")
                anomalie.ticket = ticket
                statut = "PRISE_EN_COMPTE" if statut == "SIGNALEE" else statut
            if statut != "SIGNALEE":
                anomalie.statut = statut
                anomalie.save(update_fields=["statut", "ticket"] if anomalie.ticket_id else ["statut"])
                AnomalieStatutLog.objects.create(anomalie=anomalie, ancien_statut="SIGNALEE", nouveau_statut=statut, user=self.u(chef),
                                                 note="Convertie en ticket correctif" if anomalie.ticket_id else "")
        # Tickets directs, sans anomalie d'origine.
        for i, (description, gravite, parcours) in enumerate([
            ("Remplacement préventif d'un filtre à air", 2, ["REPORTED", "DIAGNOSED", "IN_REPAIR"]),
            ("Capteur de niveau en dérive", 3, ["REPORTED", "DIAGNOSED", "WAITING_PARTS"]),
            ("Courroie d'alternateur usée", 3, ["REPORTED", "DIAGNOSED", "IN_REPAIR", "TESTING"]),
            ("Vanne d'isolement grippée", 4, ["REPORTED", "DIAGNOSED", "BLOCKED"]),
        ]):
            marin, chef = self.marins[(i * 5 + 2) % len(self.marins)]
            self._ticket(self.installations[(i + 2) % len(self.installations)], description, gravite, parcours, self.u(chef), [marin])

    # ---------- Maintenance ----------

    def _maintenance(self):
        statuts = ["PLANNED", "PLANNED", "ASSIGNED", "OVERDUE", "WAITING_VALIDATION", "DONE", "PLANNED", "ASSIGNED"]
        for i, materiel in enumerate(self.materiels[:6]):
            plan, _ = MaintenancePlan.objects.get_or_create(
                scope="ASSET", asset=materiel, name=f"Contrôle périodique — {materiel.designation or materiel.internal_id}",
                defaults={"every_n_days": 30 + 15 * (i % 3)})
            for k in range(4):
                statut = statuts[(i + k) % len(statuts)]
                decalage = {"PLANNED": 5 + 9 * k, "ASSIGNED": 1 + 2 * k, "OVERDUE": -4 - 3 * k, "WAITING_VALIDATION": -2, "DONE": -10 - 5 * k}[statut]
                occurrence = MaintenanceOccurrence.objects.create(plan=plan, asset=materiel, status=statut, scheduled_for=self.aujourdhui + timedelta(days=decalage))
                marin, _chef = self.marins[(i + k) % len(self.marins)]
                if statut in ("ASSIGNED", "WAITING_VALIDATION", "DONE", "OVERDUE"):
                    occurrence.assignees.add(marin)
                if statut in ("WAITING_VALIDATION", "DONE"):
                    MaintenanceExecution.objects.create(
                        occurrence=occurrence, started_at=self._jour(decalage, 9), completed_at=self._jour(decalage, 10), executed_by=marin,
                        conformity="CONFORME", notes="Exécution de démonstration, aucun écart.")

    # ---------- Programme, annonces, demandes ----------

    def _programme_annonces_demandes(self):
        types = {t.nom: t for t in programme_services.types_du_navire(self.bre.pk)}
        nom_type = list(types)
        second = self.u("second_a")
        evenements = [("Escale technique à Brest", 6, 2), ("Exercice d'avarie de barre", 9, 0), ("Arrêt technique des groupes", 14, 4),
                      ("Réunion de coordination", 3, 0), ("Appareillage", 20, 0), ("Exercice homme à la mer", 11, 0),
                      ("Visite de sécurité", 16, 0), ("Escale à Toulon", 24, 3)]
        for i, (titre, decalage, duree) in enumerate(evenements):
            debut = self._jour(decalage, 8 + (i % 3) * 2)
            programme_services.creer_evenement(
                second, titre, types[nom_type[i % len(nom_type)]].pk, debut, debut + timedelta(days=duree) if duree else None,
                f"ship:{self.bre.pk}", lieu="À bord (démonstration)")
        for i, (titre, corps, niveau) in enumerate([
            ("Rappel : port des EPI en zone machine", "Le port des EPI est obligatoire en zone machine.", NotificationLevel.WARNING),
            ("Menu de la semaine", "Le menu est affiché au carré.", NotificationLevel.INFO),
            ("Fermeture exceptionnelle de la coupée", "Passage par la coupée arrière jusqu'à demain.", NotificationLevel.INFO),
            ("Exercice incendie vendredi", "Rassemblement à 14 h, tenue de travail.", NotificationLevel.WARNING)]):
            annonces_services.publier(self.u("cdt_a"), titre, corps, niveau, f"ship:{self.bre.pk}", accuse_requis=(i % 2 == 0))
        taches = list(Tache.objects.filter(statut__in=["A_FAIRE", "EN_COURS"]).order_by("pk")[:3])
        for i, tache in enumerate(taches):
            chef = self.u(self.marins[i][1])
            if chef.pk == tache.assigne_id:
                continue
            demandes_services.creer_demande(tache.assigne, tache, f"Besoin d'un renfort pour « {tache.titre[:40]} »",
                                            "Demande de démonstration vers le responsable.", chef)

    # ---------- Documents, RETEX ----------

    def _documents_et_retex(self):
        auteur, valideur, chef_service = self.u("cdt_a"), self.u("coma_comaeq"), self.u("chef_service_a")
        for i, (titre, domaine) in enumerate([
            ("Consigne de rondes en zone machine", "Machine"), ("Procédure de mise en route du groupe de secours", "Énergie"),
            ("Fiche réflexe départ de feu", "Sécurité"), ("Plan de rangement du magasin", "Logistique"),
            ("Mémento des alarmes de la passerelle", "Opérations"), ("Guide d'accueil d'un nouvel embarqué", "Vie à bord")]):
            document = documentation_services.creer_document(
                auteur, titre, f"ship:{self.bre.pk}", f"{titre}\n\nContenu de démonstration (données fictives).", domaine=domaine)
            version = document.versions.first()
            if i % 3 != 2:
                documentation_services.soumettre(auteur, version)
            if i % 3 == 0:
                documentation_services.valider(valideur, version)
        domaines = list(retex_services.domaines_du_navire(self.bre.pk))
        for i, (titre, constat, enseignement) in enumerate([
            ("Délai de remplacement d'un filtre", "Le filtre de rechange n'était pas au magasin.", "Prévoir un stock minimal."),
            ("Exercice d'avarie de barre", "La relève à la barre de secours a pris plus de temps que prévu.", "Répéter la procédure chaque mois."),
            ("Coupure électrique lors d'un essai", "Un essai non annoncé a coupé l'éclairage.", "Annoncer tout essai à la passerelle."),
            ("Fiche de maintenance incomplète", "Une étape de sécurité manquait.", "Relire les fiches avant diffusion."),
            ("Communication entre quarts", "Une consigne n'a pas été transmise à la relève.", "Formaliser la passation.")]):
            marin, _chef = self.marins[(i * 2) % len(self.marins)]
            retex = retex_services.proposer(marin, titre, constat, enseignement, domaines[i % len(domaines)].pk)
            if i % 2 == 0:
                retex_services.valider(chef_service, retex, "Retenu pour diffusion.")

    # ---------- Postes, absences ----------

    def _postes_et_absences(self):
        chef_service = self.u("cdt_a")  # postes du bâtiment : cible bâtiment, donc niveau commandement
        for i, (intitule, effectif) in enumerate([("Chef de quart machine", 2), ("Rondier", 3), ("Chef de garde", 1), ("Gradé de coupée", 3), ("Équipe d'intervention incendie", 4)]):
            poste = postes_services.creer_poste(chef_service, intitule, f"ship:{self.bre.pk}", effectif)
            for marin, _chef in self.marins[i * 2:i * 2 + min(effectif, 2)]:
                postes_services.affecter(chef_service, poste, marin)
        types = [TypeAbsence.objects.get_or_create(name=n)[0] for n in ("Permission", "Stage", "Repos compensateur", "Mission")]
        for i in range(6):
            marin, chef = self.marins[(i * 3 + 1) % len(self.marins)]
            debut = self.aujourdhui + timedelta(days=4 + 5 * i)
            absences_services.declarer_absence(self.u(chef), marin, types[i % len(types)], debut, debut + timedelta(days=1 + i % 3))

    # ---------- Service à quai et échanges ----------

    def _quai_et_echanges(self):
        """Liste de service à quai de cinq jours à partir de J+21 : trois postes par jour, tournants sur six marins.
        Les marins concernés n'ont aucun quart à la mer sur la période (voir `_quart_a_la_mer`)."""
        chef = self.u("chef_secteur_a")
        for type_liste in (ChefDeListe.TYPE_QUARTS, ChefDeListe.TYPE_QUAI):
            ChefDeListe.objects.get_or_create(user=chef, ship=self.bre, service=None, sector=None, section=None, type_liste=type_liste)
        fonction = ServiceFunctionChoice.objects.get_or_create(name="Service à quai")[0]
        debut = self.aujourdhui + timedelta(days=21)
        liste = ServiceGarde.objects.create(
            nom=f"Service à quai — semaine du {debut:%d/%m}", ship=self.bre, equipage="A", date_debut=debut, date_fin=debut + timedelta(days=4),
            type_service="Service à quai", duree_creneau_heures=24, fonction=fonction, created_by=chef)
        equipe = [m for m, _c in self.marins[:6]]  # jours pairs : trois premiers marins ; jours impairs : trois suivants
        self.tours = {}
        for jour in range(5):
            for rang, poste in enumerate(("Gradé de coupée 1", "Gradé de coupée 2", "Gradé de coupée 3")):
                marin = equipe[(jour * 3 + rang) % len(equipe)]
                debut_creneau = self._jour(21 + jour, 8)
                self.tours[(jour, rang)] = CreneauServiceGarde.objects.create(
                    service_garde=liste, poste=poste, marin=marin, debut=debut_creneau, fin=debut_creneau + timedelta(hours=24))
        liste.publier(chef)
        t = self.tours
        # Échange réussi : demande → acceptation → validation du chef de liste.
        e1 = echanges_services.proposer_echange(t[(0, 0)].marin, t[(0, 0)], t[(1, 1)], "Rendez-vous médical")
        echanges_services.accepter_echange(e1, e1.cible)
        echanges_services.valider_echange(e1, chef)
        # Refus du marin sollicité.
        e2 = echanges_services.proposer_echange(t[(1, 0)].marin, t[(1, 0)], t[(2, 2)], "Permission de dernière minute")
        echanges_services.refuser_echange(e2, e2.cible, "Indisponible ce jour-là")
        # Rejet du chef de liste après acceptation.
        e3 = echanges_services.proposer_echange(t[(2, 0)].marin, t[(2, 0)], t[(3, 2)], "Souhait personnel")
        echanges_services.accepter_echange(e3, e3.cible)
        echanges_services.rejeter_echange(e3, chef, "Effectif insuffisant ce jour-là")
        # En attente de réponse ; accepté en attente de validation ; annulé par le demandeur.
        echanges_services.proposer_echange(t[(3, 0)].marin, t[(3, 0)], t[(4, 1)], "Échange de week-end")
        e5 = echanges_services.proposer_echange(t[(4, 0)].marin, t[(4, 0)], t[(3, 1)], "Visite familiale")
        echanges_services.accepter_echange(e5, e5.cible)
        e6 = echanges_services.proposer_echange(t[(1, 2)].marin, t[(1, 2)], t[(2, 1)], "Changement de plan")
        echanges_services.annuler_echange(e6, e6.demandeur, "Finalement non")

    # ---------- Quart à la mer ----------

    def _quart_a_la_mer(self):
        """Quart à la mer de sept jours à partir de J+28 (appareillage), disjoint du service à quai : huit marins, deux postes,
        jamais deux postes au même créneau pour un même marin."""
        chef = self.u("chef_service_a")
        fonction = FonctionQuartChoice.objects.get_or_create(name="Machine avant")[0]
        debut = self.aujourdhui + timedelta(days=28)
        quart = Quart.objects.create(
            nom=f"Quart machine — mer, semaine du {debut:%d/%m}", service=self.services["Propulsion"], equipage="A", date_debut=debut,
            date_fin=debut + timedelta(days=6), fonction=fonction, duree_creneau_heures=4, created_by=chef)
        equipe = [m for m, _c in self.marins[6:14]]
        for jour in range(7):
            for rang in range(6):
                debut_creneau = self._jour(28 + jour, 4 * rang)
                for poste, decalage in (("Machine avant", 0), ("Machine arrière", 4)):
                    CreneauQuart.objects.create(
                        quart=quart, poste=poste, marin=equipe[(jour * 6 + rang + decalage) % len(equipe)],
                        debut=debut_creneau, fin=debut_creneau + timedelta(hours=4))
        quart.publier(chef)

    # ---------- Notifications ----------

    def _notifications(self):
        modeles = [
            ("Maintenance en retard : contrôle périodique à reprendre.", NotificationLevel.WARNING),
            ("Ticket assigné : voir votre liste.", NotificationLevel.INFO), ("Anomalie grave signalée dans votre secteur.", NotificationLevel.DANGER),
            ("Nouvelle annonce publiée par le commandant.", NotificationLevel.INFO), ("Échange de service : réponse attendue.", NotificationLevel.WARNING),
        ]
        destinataires = [m for m, _c in self.marins[:8]] + [self.u(n) for n in ("chef_secteur_a", "chef_service_a", "second_a")]
        for i, user in enumerate(destinataires):
            for k in range(3):
                verbe, niveau = modeles[(i + k) % len(modeles)]
                Notification.objects.create(user=user, verb=verbe, level=niveau, is_read=(i + k) % 3 == 0)
