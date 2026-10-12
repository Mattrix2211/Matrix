"""Vue COMANAV : vue d'ensemble du bâtiment pour l'adjoint chargé de la conservation du bâtiment et des équipements.

Aucun moteur propre : elle assemble l'existant (agrégats de la Vue flotte, historique des comptes rendus,
détection de dérive, circuits de visa) sur le seul bâtiment consulté, avec l'étanchéité par équipage.
Le COMANAV est le titulaire de la fonction « COMANAV » (état-major) ; le commandement y accède aussi.
"""
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from accounts.models import Roles
from assets.fiche_validation import versions_a_viser
from assets.mesures import derives_de
from assets.models import Asset, Installation
from assets.proposition_article import propositions_a_viser
from dashboard.aujourdhui import LIGNES_SUPERVISION, STATUTS_ASSET_INDISPONIBLES, qualifications_equipe
from dashboard.web_views import _agrege_maintenance_ticket_stock, _disponibilite_par_navire
from logistics.anomalie_views import GRAVITE_CRITIQUE
from logistics.models import STATUTS_ANOMALIE_OUVERTS, Anomalie, CorrectiveTicket
from logistics.perimetre import equipage_tickets_q
from maintenance.historique import frise, sources_du_perimetre
from maintenance.models import MaintenanceOccurrence
from matrix.core.commandants_adjoints import est_titulaire
from matrix.core.contexte_batiment import batiment_courant, batiments_du_perimetre
from matrix.core.equipage import ROLES_COMMANDEMENT
from matrix.core.scopes import assignes_equipage_q, is_master_admin, navire_q
from org.models import CommandantAdjoint
from rondes.models import Ronde
from training.models import navire_de

JOURS_INTERVENTIONS = 30


def peut_voir_vue_comanav(user):
    """COMANAV désigné, commandement (commandant, commandant en second, admin du navire) ou administrateur général."""
    if is_master_admin(user):
        return True
    profil = getattr(user, "profile", None)
    if profil and profil.role in (*ROLES_COMMANDEMENT, Roles.ADMIN_NAVIRE) and profil.navire_id_effectif:
        return True
    return est_titulaire(user, CommandantAdjoint.COMANAV)


def _navire_consulte(request):
    """Bâtiment de l'utilisateur ; l'administrateur général consulte le bâtiment courant de la barre supérieure."""
    user = request.user
    if not is_master_admin(user):
        return navire_de(user)
    batiments = list(batiments_du_perimetre(user))
    return batiment_courant(request, batiments) or (batiments[0] if len(batiments) == 1 else None)


def _indicateur(libelle, valeur, url, etat="", detail=""):
    return {"libelle": libelle, "valeur": valeur, "url": url, "etat": etat, "detail": detail}


def _etat(valeur, niveau="attention"):
    return niveau if valeur else "ok"


def _bloc(titre, icone, indicateurs, lignes, vide, jauges=()):
    return {"titre": titre, "icone": icone, "indicateurs": indicateurs, "lignes": lignes, "vide": vide, "jauges": list(jauges)}


def _interventions(user, occurrences, tickets, agregat):
    depuis = timezone.now() - timedelta(days=JOURS_INTERVENTIONS)
    sources = sources_du_perimetre(
        MaintenanceOccurrence.objects.filter(occurrences), CorrectiveTicket.objects.filter(tickets), depuis
    )
    avec_reserve = sum(1 for s in sources if s.conformity != "CONFORME")
    liste = reverse("maintenance-occurrences")
    lignes = [
        {"titre": e["titre"], "detail": f"{e['date']:%d/%m/%Y} · {e['conformite_libelle']}", "url": e["lien"] or liste,
         "etat": "attention" if e["attention"] else ""}
        for e in frise(sources[-LIGNES_SUPERVISION:], user)
    ]
    return _bloc(
        "Interventions", "maintenance",
        [
            _indicateur(f"Comptes rendus ({JOURS_INTERVENTIONS} derniers jours)", len(sources), liste),
            _indicateur("Avec réserve ou non conformes", avec_reserve, liste, _etat(avec_reserve)),
            _indicateur("Maintenances en retard", agregat["maintenances_en_retard"], f"{liste}?retard=1",
                        _etat(agregat["maintenances_en_retard"], "danger")),
            _indicateur("Tickets correctifs ouverts", sum(t["total"] for t in agregat["tickets_par_statut"]),
                        f"{reverse('ticket-list')}?vue=perimetre"),
        ],
        lignes,
        {"icone": "maintenance", "titre": "Aucune intervention récente", "texte": "Les derniers comptes rendus apparaîtront ici."},
        [{"libelle": "Part de maintenances en retard", "valeur": agregat["maintenances_en_retard_pct"],
          "etat": _etat(agregat["maintenances_en_retard"], "danger")}],
    )


def _derives(navire):
    installations = Installation.objects.filter(navire_q(navire.pk)).prefetch_related(
        "isolation_readings", "maintenances", "hour_readings"
    )
    derives = []
    for installation in installations:
        for genre, objet, jours in derives_de(installation):
            if jours is None:
                continue
            nature = "de l'isolement" if genre == "ISOLEMENT" else f"des heures de marche ({objet.title})"
            derives.append({
                "titre": installation.designation, "jours": jours, "etat": "attention",
                "detail": f"Dérive {nature} : seuil estimé atteint dans {jours} j",
                "url": f"{reverse('installation-detail', args=[installation.pk])}?tab=mesures",
            })
    derives.sort(key=lambda d: d["jours"])
    return _bloc(
        "Dérives", "installation",
        [_indicateur("Dérives détectées", len(derives), reverse("installation-list"), _etat(derives))],
        derives[:LIGNES_SUPERVISION],
        {"icone": "terminee", "titre": "Aucune dérive détectée", "texte": "Isolement et heures de marche restent loin de leur seuil."},
    )


def _indisponibilites(user, navire):
    dispo = _disponibilite_par_navire([navire], user)[0]
    par_statut = dict(
        Asset.objects.filter(navire_q(navire.pk), status__in=STATUTS_ASSET_INDISPONIBLES)
        .values("status").annotate(n=Count("pk")).values_list("status", "n")
    )
    liste_materiel = reverse("asset-list")
    hors_service, defectueux = par_statut.get("OUT_OF_SERVICE", 0), par_statut.get("FAULTY", 0)
    critiques = dispo["installations_critiques_hors_service"]
    return _bloc(
        "Indisponibilités", "materiel",
        [
            _indicateur("Matériels hors service", hors_service, f"{liste_materiel}?status=OUT_OF_SERVICE", _etat(hors_service, "danger")),
            _indicateur("Matériels défectueux", defectueux, f"{liste_materiel}?status=FAULTY", _etat(defectueux, "danger")),
            _indicateur("Installations critiques en retard", critiques, reverse("installation-list"), _etat(critiques, "danger"),
                        detail=f"sur {dispo['installations_critiques_total']} installation(s) critique(s)"),
        ],
        [],
        None,
        [{"libelle": "Matériels avec un ticket correctif ouvert", "valeur": dispo["taux_pannes_pct"], "etat": _etat(dispo["taux_pannes_pct"])}],
    )


def _gestion_technique(user, navire, agregat):
    fiches = [v for v in versions_a_viser(user) if v.ship_id == navire.pk]
    propositions = [p for p in propositions_a_viser(user) if p.ship_id == navire.pk]
    lignes = [
        {"titre": v.name, "detail": f"Fiche à valider · {v.get_etat_display()}", "etat": "attention",
         "url": f"{reverse('fiche-detail', args=[v.fiche_id])}?v={v.numero}"}
        for v in fiches[:LIGNES_SUPERVISION]
    ]
    lignes += [
        {"titre": p.designation, "detail": f"Proposition d'article · {p.get_etat_display()}", "etat": "attention",
         "url": reverse("catalogue-proposition", args=[p.pk])}
        for p in propositions[:max(0, LIGNES_SUPERVISION - len(lignes))]
    ]
    return _bloc(
        "Gestion technique des matériels", "catalogue",
        [
            _indicateur("Fiches à valider à votre niveau", len(fiches), reverse("home"), _etat(fiches)),
            _indicateur("Propositions d'article à viser", len(propositions), reverse("catalogue-propositions"), _etat(propositions)),
        ],
        lignes,
        {"icone": "terminee", "titre": "Rien à valider", "texte": "Aucune fiche ni proposition n'attend votre visa."},
    )


def _chaine_securite(user, navire, aujourdhui):
    anomalies = Anomalie.objects.filter(navire_q(navire.pk), statut__in=STATUTS_ANOMALIE_OUVERTS)
    ouvertes = anomalies.count()
    critiques = anomalies.filter(gravite__gte=GRAVITE_CRITIQUE).count()
    perimetre_ronde = Q(ship_id=navire.pk) | Q(service__ship_id=navire.pk) | Q(sector__service__ship_id=navire.pk)
    rondes = Ronde.objects.filter(
        perimetre_ronde, assignes_equipage_q(user, Ronde, "assigne_a"),
        statut__in=Ronde.STATUTS_OUVERTS, date_prevue__lt=aujourdhui,
    ).count()
    qualifications = qualifications_equipe(user, aujourdhui, navire)
    return _bloc(
        "Chaîne sécurité", "ronde",
        [
            _indicateur("Anomalies ouvertes", ouvertes, f"{reverse('anomalie-list')}?vue=perimetre", _etat(ouvertes),
                        detail=f"dont {critiques} critique(s)" if critiques else ""),
            _indicateur("Rondes en retard", rondes, reverse("rondes-index"), _etat(rondes, "danger")),
            _indicateur("Qualifications à renouveler", len(qualifications), reverse("formation-list"),
                        _etat(any(q["expiree"] for q in qualifications), "danger") if qualifications else "ok"),
        ],
        [{"titre": q["titre"], "detail": q["detail"], "url": q["url"], "etat": "danger" if q["expiree"] else "attention"}
         for q in qualifications[:LIGNES_SUPERVISION]],
        {"icone": "terminee", "titre": "Aucune qualification à renouveler"},
    )


def _logistique(agregat):
    en_attente = next((t["total"] for t in agregat["tickets_par_statut"] if t["statut"] == "WAITING_PARTS"), 0)
    pieces = agregat["pieces_sous_seuil"]
    return _bloc(
        "Logistique", "logistique",
        [
            _indicateur("Tickets en attente de pièces", en_attente, f"{reverse('ticket-list')}?vue=perimetre", _etat(en_attente)),
            _indicateur("Pièces sous le seuil", len(pieces), reverse("stock-piece-list"), _etat(pieces)),
        ],
        [{"titre": f"{p.reference} — {p.designation}", "detail": f"{p.quantite} en stock, minimum {p.quantite_minimale}",
          "url": reverse("stock-piece-list"), "etat": "attention"} for p in pieces[:LIGNES_SUPERVISION]],
        {"icone": "terminee", "titre": "Stock conforme", "texte": "Aucune pièce sous son seuil minimal."},
        [{"libelle": "Part du stock sous le seuil", "valeur": agregat["pieces_sous_seuil_pct"], "etat": _etat(pieces)}],
    )


def blocs_comanav(user, navire):
    """Blocs de la vue, bornés au bâtiment : occurrences, tickets et stock puis le reste, tous étanches par équipage."""
    occurrences = (navire_q(navire.pk, "asset__") | navire_q(navire.pk, "installation_maintenance__installation__")) & (
        assignes_equipage_q(user, MaintenanceOccurrence, "assignees")
    )
    tickets = (navire_q(navire.pk, "asset__") | navire_q(navire.pk, "installation__")) & equipage_tickets_q(user)
    agregat = _agrege_maintenance_ticket_stock(occurrences, tickets, navire_q(navire.pk))
    return [
        _interventions(user, occurrences, tickets, agregat),
        _derives(navire),
        _indisponibilites(user, navire),
        _gestion_technique(user, navire, agregat),
        _chaine_securite(user, navire, timezone.localdate()),
        _logistique(agregat),
    ]


class VueComanavView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/comanav.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not peut_voir_vue_comanav(request.user):
            raise PermissionDenied("Réservé au COMANAV et au commandement.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        navire = _navire_consulte(self.request)
        if navire is None:
            if not is_master_admin(self.request.user):
                raise PermissionDenied("Aucun bâtiment ne vous est rattaché.")
            contexte["navire"] = None
            return contexte
        contexte["navire"] = navire
        contexte["blocs"] = blocs_comanav(self.request.user, navire)
        return contexte
