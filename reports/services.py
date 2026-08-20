"""Service de génération des bilans PDF (rapport de synthèse pour la hiérarchie).

Deux modes :
- Mode Instantané : photo de l'état du périmètre au moment de la génération, sans dates.
- Mode Période : bilan de l'activité réalisée sur une fenêtre [date_debut, date_fin],
  avec des taux de conformité que le mode instantané ne peut pas montrer.

Réutilise scope_filters_for_user (aucun nouveau système de permission ni de scope).
"""
from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import F
from django.template.loader import render_to_string
from django.utils import timezone

# WeasyPrint est une dépendance optionnelle : le paquet Python peut être installé
# (requirements.txt) sans que les bibliothèques natives GTK le soient (cas par
# défaut sous Windows), ce qui lève une OSError (et non une ImportError) à
# l'import. Cette OSError ne doit jamais faire planter le démarrage de Django
# (migrate/runserver) : seul l'export PDF doit être indisponible, avec repli
# possible vers le CSV (voir pdf_disponible() ci-dessous, même modèle que
# xlsx_disponible() dans matrix/core/export.py).
try:
    import weasyprint
except (ImportError, OSError):  # pragma: no cover - dépend des libs GTK de la machine
    weasyprint = None

from assets.models import (
    Installation,
    InstallationHourReading,
    InstallationIsolationReading,
    InstallationVibrationReading,
)
from logistics.models import CorrectiveTicket, PartLineItem, StockPiece
from maintenance.models import MaintenanceExecution, MaintenanceOccurrence
from matrix.core.export import rendre_csv_sections, rendre_xlsx_sections
from matrix.core.scopes import scope_filters_for_user
from org.models import Section, Sector, Service, Ship
from training.models import TrainingRecord

# Statuts considérés comme clos : à exclure des listes "en cours"/"ouverts".
STATUTS_TICKET_FERMES = ("CLOSED", "CANCELLED")
STATUTS_OCCURRENCE_TERMINEES = ("DONE", "CANCELLED")

# Fenêtre de "proche expiration" pour les qualifications, alignée sur le plus large
# des seuils déjà utilisés par notifications.tasks.notify_expiring_training (30/60/90 j).
JOURS_ALERTE_QUALIFICATION = 90

MODELES_PERIMETRE = {"ship": Ship, "service": Service, "sector": Sector, "section": Section}

# Base locale (file://) pour que WeasyPrint résolve les polices auto-hébergées et le
# logo référencés en chemin relatif dans le CSS inline des templates de bilan (T20) —
# aucune requête réseau, conforme au fonctionnement hors-ligne du bord.
_BASE_URL_STATIQUE = f"file://{settings.STATICFILES_DIRS[0]}/"


class PerimetreNonAutorise(PermissionError):
    """Levée quand le périmètre demandé pour le bilan ne correspond pas au
    périmètre propre de l'utilisateur connecté (pas de drill-down hiérarchique :
    un utilisateur ne peut générer le bilan que de son propre périmètre)."""


def pdf_disponible() -> bool:
    """Indique si le rendu PDF est disponible (WeasyPrint installé, bibliothèques
    natives GTK présentes sur la machine)."""
    return weasyprint is not None


def _dernier_par_installation(queryset, champ_installation="installation_id"):
    """Retourne {installation_id: dernier enregistrement} à partir d'un queryset
    déjà trié du plus récent au plus ancien (ordering par défaut des modèles de
    relevés d'installation)."""
    resultat = {}
    for obj in queryset:
        cle = getattr(obj, champ_installation)
        if cle not in resultat:
            resultat[cle] = obj
    return resultat


def _fmt_date(valeur):
    """Formate une date ou un datetime en JJ/MM/AAAA (JJ/MM/AAAA HH:MM pour un
    datetime), chaîne vide si aucune valeur — même mise en forme pour les
    exports CSV et XLSX des bilans."""
    if valeur is None:
        return ""
    if isinstance(valeur, datetime):
        return timezone.localtime(valeur).strftime("%d/%m/%Y %H:%M")
    return valeur.strftime("%d/%m/%Y")


def _nom_utilisateur(utilisateur):
    """Nom affiché d'un marin dans les exports (nom complet, ou identifiant à
    défaut)."""
    return utilisateur.get_full_name() or utilisateur.username


def _nom_materiel(asset):
    """Désignation affichée d'un matériel mobile dans les exports (désignation,
    ou représentation par défaut du modèle si non renseignée)."""
    return asset.designation or str(asset)


def _resoudre_perimetre(scope_type, scope_id):
    """Récupère l'objet (Navire/Service/Secteur/Section) correspondant au
    périmètre demandé, pour affichage dans l'en-tête du bilan."""
    modele = MODELES_PERIMETRE.get(scope_type)
    if modele is None:
        return None
    return modele.objects.filter(pk=scope_id).first()


def construire_contexte_instantane(scope_type: str, scope_id, utilisateur) -> dict:
    """Construit le contexte du bilan PDF Mode Instantané pour le périmètre
    scope_type/scope_id (ex: "sector", 5).

    Le filtrage des données réutilise scope_filters_for_user : le périmètre demandé
    doit correspondre exactement au périmètre propre de l'utilisateur, sinon une
    PerimetreNonAutorise est levée.
    """
    filtre_scope = scope_filters_for_user(utilisateur)
    if not filtre_scope or filtre_scope.get(f"{scope_type}_id") != scope_id:
        raise PerimetreNonAutorise(
            "Le périmètre demandé ne correspond pas au périmètre de l'utilisateur."
        )

    today = timezone.localdate()

    installations = list(
        Installation.objects.filter(**filtre_scope)
        .select_related("ship", "service", "sector", "section")
        .order_by("designation")
    )
    installation_ids = [inst.id for inst in installations]

    derniers_heures = _dernier_par_installation(
        InstallationHourReading.objects.filter(installation_id__in=installation_ids)
    )
    dernieres_visites = _dernier_par_installation(
        InstallationHourReading.objects.filter(
            installation_id__in=installation_ids, is_visit=True
        )
    )
    derniers_vibrations = _dernier_par_installation(
        InstallationVibrationReading.objects.filter(installation_id__in=installation_ids)
    )
    derniers_isolements = _dernier_par_installation(
        InstallationIsolationReading.objects.filter(installation_id__in=installation_ids)
    )

    # Échéances de maintenance (calendaire/compteur) des installations du périmètre,
    # non terminées, triées par date prévue : les retards (date passée) remontent
    # naturellement en premier.
    occurrences = (
        MaintenanceOccurrence.objects.filter(
            installation_maintenance__installation_id__in=installation_ids
        )
        .exclude(status__in=STATUTS_OCCURRENCE_TERMINEES)
        .select_related("installation_maintenance", "installation_maintenance__installation")
        .order_by("scheduled_for")
    )
    echeances = []
    installations_en_retard = set()
    for occ in occurrences:
        en_retard = occ.status == "OVERDUE" or occ.scheduled_for < today
        if en_retard:
            installations_en_retard.add(occ.installation_maintenance.installation_id)
        echeances.append(
            {
                "installation": occ.installation_maintenance.installation,
                "titre": occ.installation_maintenance.title,
                "date_prevue": occ.scheduled_for,
                "statut": occ.get_status_display(),
                "en_retard": en_retard,
            }
        )

    lignes_installations = [
        {
            "installation": inst,
            "statut": "En retard" if inst.id in installations_en_retard else "À jour",
            "derniere_visite": dernieres_visites.get(inst.id),
            "dernier_releve_heures": derniers_heures.get(inst.id),
            "dernier_releve_vibration": derniers_vibrations.get(inst.id),
            "dernier_releve_isolement": derniers_isolements.get(inst.id),
        }
        for inst in installations
    ]

    # Tickets correctifs ouverts sur le matériel mobile du périmètre.
    filtre_tickets = {f"asset__{cle}": valeur for cle, valeur in filtre_scope.items()}
    tickets_ouverts = list(
        CorrectiveTicket.objects.filter(**filtre_tickets)
        .exclude(status__in=STATUTS_TICKET_FERMES)
        .select_related("asset", "asset__asset_type")
        .order_by("reported_at")
    )
    for ticket in tickets_ouverts:
        ticket.anciennete_jours = (timezone.now() - ticket.reported_at).days

    # Qualifications proches d'expiration : TrainingRecord n'a pas de périmètre
    # propre, on le déduit du profil du marin titulaire de la qualification.
    filtre_qualifications = {
        f"user__profile__{cle}": valeur for cle, valeur in filtre_scope.items()
    }
    date_limite = today + timedelta(days=JOURS_ALERTE_QUALIFICATION)
    qualifications_proches_expiration = list(
        TrainingRecord.objects.filter(
            expires_at__gte=today, expires_at__lte=date_limite, **filtre_qualifications
        )
        .select_related("user", "user__profile", "course")
        .order_by("expires_at")
    )

    # Pièces en stock passées sous leur seuil d'alerte (quantite_minimale), pour
    # anticiper une rupture avant qu'elle ne bloque une intervention.
    stock_alerte = list(
        StockPiece.objects.filter(quantite__lt=F("quantite_minimale"), **filtre_scope)
        .select_related("ship", "service", "sector", "section")
        .order_by("reference")
    )

    return {
        "mode": "INSTANTANE",
        "perimetre": _resoudre_perimetre(scope_type, scope_id),
        "genere_par": utilisateur,
        "genere_le": timezone.now(),
        "installations": lignes_installations,
        "echeances": echeances,
        "tickets_ouverts": tickets_ouverts,
        "qualifications_proches_expiration": qualifications_proches_expiration,
        "stock_alerte": stock_alerte,
    }


def generer_bilan_instantane_pdf(scope_type: str, scope_id, utilisateur) -> bytes | None:
    """Génère le bilan PDF Mode Instantané pour le périmètre demandé et renvoie
    le contenu binaire du PDF (WeasyPrint, génération 100% côté serveur — aucune
    dépendance CDN, compatible fonctionnement hors-ligne).

    Renvoie None si WeasyPrint n'est pas disponible (bibliothèques natives GTK
    absentes) : l'appelant doit alors se rabattre sur le CSV."""
    if not pdf_disponible():
        return None
    contexte = construire_contexte_instantane(scope_type, scope_id, utilisateur)
    html = render_to_string("reports/bilan_instantane.html", contexte)
    return weasyprint.HTML(string=html, base_url=_BASE_URL_STATIQUE).write_pdf()


def _sections_bilan_instantane(contexte: dict) -> list:
    """Découpe le contexte du bilan Mode Instantané en sections (titre, en-têtes,
    lignes) pour un rendu tableur — même données que le PDF (aucune requête
    supplémentaire), juste un rendu différent."""
    lignes_installations = []
    for ligne in contexte["installations"]:
        dv, dh, dvib, diso = (
            ligne["derniere_visite"],
            ligne["dernier_releve_heures"],
            ligne["dernier_releve_vibration"],
            ligne["dernier_releve_isolement"],
        )
        lignes_installations.append(
            [
                ligne["installation"].designation,
                ligne["statut"],
                _fmt_date(dv.date) if dv else "",
                dh.hours if dh else "",
                _fmt_date(dh.date) if dh else "",
                dvib.state if dvib else "",
                _fmt_date(dvib.date) if dvib else "",
                diso.ohms if diso else "",
                _fmt_date(diso.date) if diso else "",
            ]
        )

    lignes_echeances = [
        [
            ech["installation"].designation,
            ech["titre"],
            _fmt_date(ech["date_prevue"]),
            ech["statut"],
            "Oui" if ech["en_retard"] else "Non",
        ]
        for ech in contexte["echeances"]
    ]

    lignes_tickets = [
        [
            _nom_materiel(ticket.asset),
            ticket.asset.asset_type.name,
            ticket.get_status_display(),
            _fmt_date(ticket.reported_at),
            ticket.anciennete_jours,
        ]
        for ticket in contexte["tickets_ouverts"]
    ]

    lignes_qualifications = [
        [
            _nom_utilisateur(qualif.user),
            qualif.course.title,
            _fmt_date(qualif.expires_at),
        ]
        for qualif in contexte["qualifications_proches_expiration"]
    ]

    lignes_stock = [
        [piece.reference, piece.designation, piece.quantite, piece.quantite_minimale, piece.emplacement]
        for piece in contexte["stock_alerte"]
    ]

    return [
        (
            "Installations",
            [
                "Désignation", "Statut", "Dernière visite",
                "Heures - dernier relevé", "Heures - date",
                "Vibration - dernier état", "Vibration - date",
                "Isolement - dernière valeur (Ω)", "Isolement - date",
            ],
            lignes_installations,
        ),
        (
            "Échéances de maintenance",
            ["Installation", "Titre", "Date prévue", "Statut", "En retard"],
            lignes_echeances,
        ),
        (
            "Tickets correctifs ouverts",
            ["Matériel", "Type de matériel", "Statut", "Signalé le", "Ancienneté (jours)"],
            lignes_tickets,
        ),
        (
            "Qualifications proches d'expiration",
            ["Marin", "Formation", "Date d'expiration"],
            lignes_qualifications,
        ),
        (
            "Stock sous le seuil d'alerte",
            ["Référence", "Désignation", "Quantité", "Quantité minimale", "Emplacement"],
            lignes_stock,
        ),
    ]


def generer_bilan_instantane_csv(scope_type: str, scope_id, utilisateur) -> bytes:
    """Génère le bilan Mode Instantané au format CSV (même contexte que le PDF)."""
    contexte = construire_contexte_instantane(scope_type, scope_id, utilisateur)
    return rendre_csv_sections(_sections_bilan_instantane(contexte))


def generer_bilan_instantane_xlsx(scope_type: str, scope_id, utilisateur):
    """Génère le bilan Mode Instantané au format XLSX (même contexte que le PDF).
    Renvoie None si openpyxl n'est pas installé."""
    contexte = construire_contexte_instantane(scope_type, scope_id, utilisateur)
    return rendre_xlsx_sections(_sections_bilan_instantane(contexte))


def construire_contexte_periode(
    scope_type: str, scope_id, utilisateur, date_debut, date_fin
) -> dict:
    """Construit le contexte du bilan PDF Mode Période pour le périmètre
    scope_type/scope_id, sur la fenêtre [date_debut, date_fin] (bornes incluses).

    Même règle de périmètre que le Mode Instantané (PerimetreNonAutorise si le
    périmètre demandé ne correspond pas exactement à celui de l'utilisateur).

    Une maintenance est considérée "réalisée à temps" si son occurrence est passée
    au statut Terminée et que la date de fin d'exécution associée (MaintenanceExecution.
    completed_at) est antérieure ou égale à la date prévue (scheduled_for). Les
    occurrences Annulées sont exclues du décompte (elles ne représentent plus un
    engagement de maintenance à honorer).
    """
    if date_debut > date_fin:
        raise ValueError("La date de début doit être antérieure ou égale à la date de fin.")

    filtre_scope = scope_filters_for_user(utilisateur)
    if not filtre_scope or filtre_scope.get(f"{scope_type}_id") != scope_id:
        raise PerimetreNonAutorise(
            "Le périmètre demandé ne correspond pas au périmètre de l'utilisateur."
        )

    installations = list(
        Installation.objects.filter(**filtre_scope).select_related(
            "ship", "service", "sector", "section"
        )
    )
    installation_ids = [inst.id for inst in installations]

    # Taux de conformité maintenance : occurrences d'installation prévues dans la
    # fenêtre, hors annulées, comparées à leur exécution réelle.
    occurrences_periode = (
        MaintenanceOccurrence.objects.filter(
            installation_maintenance__installation_id__in=installation_ids,
            scheduled_for__range=(date_debut, date_fin),
        )
        .exclude(status="CANCELLED")
        .select_related("installation_maintenance", "installation_maintenance__installation")
        .order_by("scheduled_for")
    )
    dates_achevement = dict(
        MaintenanceExecution.objects.filter(occurrence__in=occurrences_periode).values_list(
            "occurrence_id", "completed_at"
        )
    )
    maintenances_periode = []
    nb_realisees_a_temps = 0
    for occ in occurrences_periode:
        date_achevement = dates_achevement.get(occ.id)
        realisee_a_temps = (
            occ.status == "DONE"
            and date_achevement is not None
            and date_achevement.date() <= occ.scheduled_for
        )
        if realisee_a_temps:
            nb_realisees_a_temps += 1
        maintenances_periode.append(
            {
                "installation": occ.installation_maintenance.installation,
                "titre": occ.installation_maintenance.title,
                "date_prevue": occ.scheduled_for,
                "statut": occ.get_status_display(),
                "realisee_a_temps": realisee_a_temps,
            }
        )
    nb_maintenances_planifiees = len(maintenances_periode)
    taux_conformite = (
        (nb_realisees_a_temps / nb_maintenances_planifiees) * 100
        if nb_maintenances_planifiees
        else None
    )

    # Tickets correctifs sur le matériel mobile du périmètre.
    filtre_tickets = {f"asset__{cle}": valeur for cle, valeur in filtre_scope.items()}
    tickets_ouverts_periode = list(
        CorrectiveTicket.objects.filter(
            reported_at__date__range=(date_debut, date_fin), **filtre_tickets
        )
        .select_related("asset", "asset__asset_type")
        .order_by("reported_at")
    )
    tickets_fermes_periode = list(
        CorrectiveTicket.objects.filter(
            status="CLOSED", updated_at__date__range=(date_debut, date_fin), **filtre_tickets
        )
        .select_related("asset", "asset__asset_type")
        .order_by("updated_at")
    )
    for ticket in tickets_fermes_periode:
        ticket.delai_resolution_jours = (ticket.updated_at - ticket.reported_at).days
    delai_moyen_resolution = (
        sum(t.delai_resolution_jours for t in tickets_fermes_periode)
        / len(tickets_fermes_periode)
        if tickets_fermes_periode
        else None
    )
    # Snapshot au dernier statut connu : tickets signalés avant/pendant la fenêtre
    # et toujours non clos à ce jour.
    tickets_encore_ouverts_fin_periode = list(
        CorrectiveTicket.objects.filter(reported_at__date__lte=date_fin, **filtre_tickets)
        .exclude(status__in=STATUTS_TICKET_FERMES)
        .select_related("asset", "asset__asset_type")
        .order_by("reported_at")
    )

    # Relevés techniques effectués sur la fenêtre (preuve du suivi, pas juste le
    # dernier chiffre).
    releves_heures = list(
        InstallationHourReading.objects.filter(
            installation_id__in=installation_ids, date__range=(date_debut, date_fin)
        )
        .select_related("installation")
        .order_by("installation__designation", "date")
    )
    releves_vibration = list(
        InstallationVibrationReading.objects.filter(
            installation_id__in=installation_ids, date__range=(date_debut, date_fin)
        )
        .select_related("installation")
        .order_by("installation__designation", "date")
    )
    releves_isolement = list(
        InstallationIsolationReading.objects.filter(
            installation_id__in=installation_ids, date__range=(date_debut, date_fin)
        )
        .select_related("installation")
        .order_by("installation__designation", "date")
    )

    # Pièces consommées : PartLineItem passées en statut CONSUMED sur la fenêtre.
    filtre_pieces = {
        f"part_request__ticket__asset__{cle}": valeur for cle, valeur in filtre_scope.items()
    }
    pieces_consommees = list(
        PartLineItem.objects.filter(
            status="CONSUMED", received_at__range=(date_debut, date_fin), **filtre_pieces
        )
        .select_related("part_request", "part_request__ticket", "part_request__ticket__asset")
        .order_by("-received_at")
    )

    # Qualifications obtenues/expirées sur la fenêtre, scopées par le profil du marin.
    filtre_qualifications = {
        f"user__profile__{cle}": valeur for cle, valeur in filtre_scope.items()
    }
    qualifications_obtenues = list(
        TrainingRecord.objects.filter(
            completed_at__range=(date_debut, date_fin), **filtre_qualifications
        )
        .select_related("user", "user__profile", "course")
        .order_by("completed_at")
    )
    qualifications_expirees = list(
        TrainingRecord.objects.filter(
            expires_at__range=(date_debut, date_fin), **filtre_qualifications
        )
        .select_related("user", "user__profile", "course")
        .order_by("expires_at")
    )

    return {
        "mode": "PERIODE",
        "perimetre": _resoudre_perimetre(scope_type, scope_id),
        "genere_par": utilisateur,
        "genere_le": timezone.now(),
        "date_debut": date_debut,
        "date_fin": date_fin,
        "maintenances_periode": maintenances_periode,
        "nb_maintenances_planifiees": nb_maintenances_planifiees,
        "nb_maintenances_realisees_a_temps": nb_realisees_a_temps,
        "taux_conformite": taux_conformite,
        "tickets_ouverts_periode": tickets_ouverts_periode,
        "tickets_fermes_periode": tickets_fermes_periode,
        "delai_moyen_resolution": delai_moyen_resolution,
        "tickets_encore_ouverts_fin_periode": tickets_encore_ouverts_fin_periode,
        "releves_heures": releves_heures,
        "releves_vibration": releves_vibration,
        "releves_isolement": releves_isolement,
        "pieces_consommees": pieces_consommees,
        "qualifications_obtenues": qualifications_obtenues,
        "qualifications_expirees": qualifications_expirees,
    }


def generer_bilan_periode_pdf(
    scope_type: str, scope_id, utilisateur, date_debut, date_fin
) -> bytes | None:
    """Génère le bilan PDF Mode Période pour le périmètre et la fenêtre demandés
    et renvoie le contenu binaire du PDF (WeasyPrint, génération 100% côté serveur).

    Renvoie None si WeasyPrint n'est pas disponible (bibliothèques natives GTK
    absentes) : l'appelant doit alors se rabattre sur le CSV."""
    if not pdf_disponible():
        return None
    contexte = construire_contexte_periode(scope_type, scope_id, utilisateur, date_debut, date_fin)
    html = render_to_string("reports/bilan_periode.html", contexte)
    return weasyprint.HTML(string=html, base_url=_BASE_URL_STATIQUE).write_pdf()


def _sections_bilan_periode(contexte: dict) -> list:
    """Découpe le contexte du bilan Mode Période en sections (titre, en-têtes,
    lignes) pour un rendu tableur — même données que le PDF (aucune requête
    supplémentaire), juste un rendu différent."""
    lignes_maintenances = [
        [
            m["installation"].designation,
            m["titre"],
            _fmt_date(m["date_prevue"]),
            m["statut"],
            "Oui" if m["realisee_a_temps"] else "Non",
        ]
        for m in contexte["maintenances_periode"]
    ]

    lignes_tickets_ouverts = [
        [_nom_materiel(t.asset), t.asset.asset_type.name, t.get_status_display(), _fmt_date(t.reported_at)]
        for t in contexte["tickets_ouverts_periode"]
    ]

    lignes_tickets_fermes = [
        [
            _nom_materiel(t.asset),
            t.asset.asset_type.name,
            _fmt_date(t.reported_at),
            _fmt_date(t.updated_at),
            t.delai_resolution_jours,
        ]
        for t in contexte["tickets_fermes_periode"]
    ]

    lignes_tickets_encore_ouverts = [
        [_nom_materiel(t.asset), t.asset.asset_type.name, t.get_status_display(), _fmt_date(t.reported_at)]
        for t in contexte["tickets_encore_ouverts_fin_periode"]
    ]

    lignes_releves_heures = [
        [r.installation.designation, _fmt_date(r.date), r.hours] for r in contexte["releves_heures"]
    ]
    lignes_releves_vibration = [
        [r.installation.designation, _fmt_date(r.date), r.state] for r in contexte["releves_vibration"]
    ]
    lignes_releves_isolement = [
        [r.installation.designation, _fmt_date(r.date), r.ohms] for r in contexte["releves_isolement"]
    ]

    lignes_pieces = [
        [
            p.reference,
            p.description,
            p.qty,
            _nom_materiel(p.part_request.ticket.asset),
            _fmt_date(p.received_at),
        ]
        for p in contexte["pieces_consommees"]
    ]

    lignes_qualifications_obtenues = [
        [_nom_utilisateur(q.user), q.course.title, _fmt_date(q.completed_at)]
        for q in contexte["qualifications_obtenues"]
    ]
    lignes_qualifications_expirees = [
        [_nom_utilisateur(q.user), q.course.title, _fmt_date(q.expires_at)]
        for q in contexte["qualifications_expirees"]
    ]

    return [
        (
            "Maintenances de la période",
            ["Installation", "Titre", "Date prévue", "Statut", "Réalisée à temps"],
            lignes_maintenances,
        ),
        (
            "Tickets ouverts sur la période",
            ["Matériel", "Type de matériel", "Statut", "Signalé le"],
            lignes_tickets_ouverts,
        ),
        (
            "Tickets fermés sur la période",
            ["Matériel", "Type de matériel", "Signalé le", "Fermé le", "Délai de résolution (jours)"],
            lignes_tickets_fermes,
        ),
        (
            "Tickets encore ouverts en fin de période",
            ["Matériel", "Type de matériel", "Statut", "Signalé le"],
            lignes_tickets_encore_ouverts,
        ),
        ("Relevés heures de marche", ["Installation", "Date", "Heures"], lignes_releves_heures),
        ("Relevés vibration", ["Installation", "Date", "État"], lignes_releves_vibration),
        ("Relevés isolement", ["Installation", "Date", "Isolement (Ω)"], lignes_releves_isolement),
        (
            "Pièces consommées",
            ["Référence", "Description", "Quantité", "Ticket (matériel)", "Reçue le"],
            lignes_pieces,
        ),
        (
            "Qualifications obtenues",
            ["Marin", "Formation", "Date d'obtention"],
            lignes_qualifications_obtenues,
        ),
        (
            "Qualifications expirées",
            ["Marin", "Formation", "Date d'expiration"],
            lignes_qualifications_expirees,
        ),
    ]


def generer_bilan_periode_csv(
    scope_type: str, scope_id, utilisateur, date_debut, date_fin
) -> bytes:
    """Génère le bilan Mode Période au format CSV (même contexte que le PDF)."""
    contexte = construire_contexte_periode(scope_type, scope_id, utilisateur, date_debut, date_fin)
    return rendre_csv_sections(_sections_bilan_periode(contexte))


def generer_bilan_periode_xlsx(scope_type: str, scope_id, utilisateur, date_debut, date_fin):
    """Génère le bilan Mode Période au format XLSX (même contexte que le PDF).
    Renvoie None si openpyxl n'est pas installé."""
    contexte = construire_contexte_periode(scope_type, scope_id, utilisateur, date_debut, date_fin)
    return rendre_xlsx_sections(_sections_bilan_periode(contexte))
