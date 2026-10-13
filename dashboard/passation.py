"""Synthèse de passation du bâtiment à la relève du double équipage.

Aucun moteur propre : elle fige, à la relève, ce que les services existants (vue COMANAV, qualifications,
annonces, listes de service) savent déjà dire du bâtiment, pour l'équipage montant.
L'équipage montant lit tout (continuité de relève) : aucune étanchéité par équipage dans le contenu.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView

from accounts.models import AuditLog, UserProfile
from annonces.models import Annonce
from annonces.services import destinataires
from dashboard.aujourdhui import qualifications_equipe
from dashboard.web_views import _agrege_maintenance_ticket_stock
from demandes.models import Demande
from logistics.models import STATUTS_ANOMALIE_OUVERTS, STATUTS_TICKET_OUVERTS, Anomalie, CorrectiveTicket
from maintenance.models import MaintenanceOccurrence
from matrix.core.roles import NIVEAU_VISION_COMMANDEMENT, user_role_level
from matrix.core.scopes import is_master_admin, navire_q
from notifications.models import Notification
from org.models import ParametresPassation, ReleveEquipage, SynthesePassation
from quarts.models import Quart, ServiceGarde
from reports.services import html_vers_pdf, pdf_disponible
from taches.models import Tache
from taches.services import peut_attribuer

JOURS_A_VENIR = 14
LIGNES_PAR_GROUPE = 30


def passation_activee():
    """Activée par défaut ; l'administrateur général peut la désactiver pour la flotte."""
    return ParametresPassation.courants().active


def peut_generer_passation(user, navire):
    """Commandement du bâtiment (commandant, second, administrateur d'unité) ou administrateur général."""
    if is_master_admin(user):
        return True
    profil = getattr(user, "profile", None)
    return bool(profil and profil.navire_id_effectif == navire.pk and user_role_level(user) >= NIVEAU_VISION_COMMANDEMENT)


def syntheses_visibles(user):
    """Commandement du bâtiment ; chefs des deux équipages concernés par la relève ; jamais un autre bâtiment."""
    if is_master_admin(user):
        return SynthesePassation.objects.all()
    profil = getattr(user, "profile", None)
    navire_id = profil.navire_id_effectif if profil else None
    if not navire_id:
        return SynthesePassation.objects.none()
    du_navire = SynthesePassation.objects.filter(ship_id=navire_id)
    if user_role_level(user) >= NIVEAU_VISION_COMMANDEMENT:
        return du_navire
    if profil.equipage and peut_attribuer(user):
        return du_navire.filter(Q(equipage_sortant=profil.equipage) | Q(equipage_montant=profil.equipage))
    return SynthesePassation.objects.none()


def _ligne(titre, detail, url, etat=""):
    return {"titre": titre, "detail": detail, "url": url, "etat": etat}


def _groupe(titre, lignes, total=None):
    total = len(lignes) if total is None else total
    return {"titre": titre, "total": total, "lignes": lignes[:LIGNES_PAR_GROUPE], "plus": max(0, total - LIGNES_PAR_GROUPE)}


def _bloc(cle, titre, groupes, vide):
    return {"cle": cle, "titre": titre, "total": sum(g["total"] for g in groupes), "groupes": groupes, "vide": vide}


def _date(valeur):
    return f"{valeur:%d/%m/%Y}" if valeur else "sans échéance"


def _nom(marin):
    return (marin.get_full_name() or marin.get_username()) if marin else "personne"


def _taches(navire, aujourdhui):
    ouvertes = list(
        Tache.objects.filter(navire_q(navire.pk, "assigne__profile__"), partagee=True, statut__in=Tache.STATUTS_OUVERTS)
        .select_related("assigne")
    )
    libelles = dict(Tache.STATUT_CHOICES)
    groupes = []
    # Les tâches bloquées d'abord : ce sont elles que l'équipage montant doit débloquer.
    for statut in (Tache.STATUT_BLOQUEE, Tache.STATUT_EN_COURS, Tache.STATUT_A_FAIRE):
        lignes = [
            _ligne(
                t.titre,
                f"{_nom(t.assigne)} · échéance {_date(t.echeance)}" + (f" · {t.motif_blocage}" if t.motif_blocage else ""),
                reverse("tache-detail", args=[t.pk]),
                "danger" if t.en_retard_au(aujourdhui) else ("attention" if statut == Tache.STATUT_BLOQUEE else ""),
            )
            for t in ouvertes if t.statut == statut
        ]
        groupes.append(_groupe(libelles[statut], lignes))
    return _bloc("taches", "Tâches ouvertes et bloquées", groupes,
                 "Aucune tâche ouverte (les tâches personnelles non partagées ne figurent pas ici).")


def _maintenance_en_retard(occurrences, agregat):
    retards = (
        MaintenanceOccurrence.objects.filter(occurrences, status="OVERDUE")
        .select_related("installation_maintenance__installation", "plan", "asset").order_by("scheduled_for")
    )
    lignes = [
        _ligne(o.titre_affiche, f"Prévue le {_date(o.scheduled_for)}", reverse("occurrence-execute", args=[o.pk]), "danger")
        for o in retards[:LIGNES_PAR_GROUPE]
    ]
    return _bloc("maintenance", "Maintenances en retard", [_groupe("En retard", lignes, agregat["maintenances_en_retard"])],
                 "Aucune maintenance en retard.")


def _tickets(tickets, agregat):
    ouverts = list(
        CorrectiveTicket.objects.filter(tickets, status__in=STATUTS_TICKET_OUVERTS)
        .select_related("asset", "installation").order_by("-severity", "reported_at")
    )
    groupes = [
        _groupe(
            t["libelle"],
            [_ligne(str(o), o.description[:120], reverse("ticket-detail", args=[o.pk]), "attention" if o.severity >= 4 else "")
             for o in ouverts if o.status == t["statut"]],
        )
        for t in agregat["tickets_par_statut"] if t["total"]
    ]
    return _bloc("tickets", "Tickets correctifs ouverts", groupes, "Aucun ticket correctif ouvert.")


def _anomalies(navire):
    ouvertes = Anomalie.objects.filter(navire_q(navire.pk), statut__in=STATUTS_ANOMALIE_OUVERTS).order_by("-gravite", "created_at")
    lignes = [
        _ligne(a.titre, f"Gravité {a.gravite} · {a.get_statut_display()}" + (f" · {a.localisation}" if a.localisation else ""),
               reverse("anomalie-detail", args=[a.pk]), "attention")
        for a in ouvertes[:LIGNES_PAR_GROUPE]
    ]
    return _bloc("anomalies", "Anomalies ouvertes", [_groupe("Ouvertes", lignes, ouvertes.count())], "Aucune anomalie ouverte.")


def _stock(agregat):
    pieces = agregat["pieces_sous_seuil"]
    lignes = [
        _ligne(f"{p.reference} — {p.designation}", f"{p.quantite} en stock, minimum {p.quantite_minimale}",
               reverse("stock-piece-list"), "attention")
        for p in pieces
    ]
    return _bloc("stock", "Stock sous le seuil", [_groupe("Sous le seuil", lignes)], "Stock conforme.")


def _qualifications(user, navire, aujourdhui):
    lignes = [
        _ligne(q["titre"], q["detail"], q["url"], "danger" if q["expiree"] else "attention")
        for q in qualifications_equipe(user, aujourdhui, navire)
    ]
    return _bloc("qualifications", "Qualifications à renouveler à bord", [_groupe("À renouveler", lignes)],
                 "Aucune qualification à renouveler.")


def _listes_a_venir(navire):
    maintenant = timezone.now()
    horizon = maintenant + timedelta(days=JOURS_A_VENIR)
    groupes = []
    for titre, modele, route in (("Quarts", Quart, "quart-detail"), ("Services de garde", ServiceGarde, "garde-detail")):
        lignes = []
        for liste in modele.objects.filter(navire_q(navire.pk), statut=modele.STATUT_PUBLIEE).select_related("fonction"):
            creneaux = list(liste.creneaux.filter(debut__gte=maintenant, debut__lte=horizon).order_by("debut"))
            if creneaux:
                libelle = liste.nom or str(liste.fonction or titre)
                lignes.append(_ligne(
                    libelle + (f" (équipage {liste.equipage})" if liste.equipage else ""),
                    f"{len(creneaux)} créneau(x), du {timezone.localtime(creneaux[0].debut):%d/%m %H:%M} "
                    f"au {timezone.localtime(creneaux[-1].debut):%d/%m %H:%M}",
                    reverse(route, args=[liste.pk]),
                ))
        groupes.append(_groupe(titre, lignes))
    return _bloc("listes", f"Quarts et services à venir ({JOURS_A_VENIR} jours)", groupes,
                 "Aucune liste publiée n'a de créneau à venir.")


def _annonces_sans_accuse(navire, aujourdhui):
    actives = Annonce.objects.filter(
        ship=navire, accuse_requis=True, archivee=False, date_effet__lte=aujourdhui
    ).filter(Q(date_fin__isnull=True) | Q(date_fin__gte=aujourdhui))
    lignes = []
    for annonce in actives:
        accuses = set(annonce.lectures.filter(accuse=True, version_lue__gte=annonce.version).values_list("user_id", flat=True))
        concernes = list(destinataires(annonce))
        manquants = [m for m in concernes if m.pk not in accuses]
        if manquants:
            lignes.append(_ligne(annonce.titre, f"{len(manquants)} accusé(s) manquant(s) sur {len(concernes)} destinataire(s)",
                                 reverse("annonce-detail", args=[annonce.pk]), "attention"))
    return _bloc("annonces", "Annonces actives sans accusé complet", [_groupe("Accusés manquants", lignes)],
                 "Toutes les annonces à accusé sont acquittées.")


def _demandes(navire):
    en_cours = Demande.objects.filter(navire_q(navire.pk), etat__in=Demande.ETATS_OUVERTS).select_related("responsable").order_by("created_at")
    lignes = [
        _ligne(d.titre, f"{d.get_etat_display()} · responsable {_nom(d.responsable)}", reverse("demande-detail", args=[d.pk]),
               "attention" if d.priorite == Demande.PRIORITE_URGENTE else "")
        for d in en_cours
    ]
    return _bloc("demandes", "Demandes bord–terre en cours", [_groupe("En cours", lignes)], "Aucune demande en cours.")


def contenu_passation(user, navire):
    """Instantané JSON du bâtiment ; `user` doit relever du commandement (il borne les qualifications visibles)."""
    aujourdhui = timezone.localdate()
    occurrences = navire_q(navire.pk, "asset__") | navire_q(navire.pk, "installation_maintenance__installation__")
    tickets = navire_q(navire.pk, "asset__") | navire_q(navire.pk, "installation__")
    agregat = _agrege_maintenance_ticket_stock(occurrences, tickets, navire_q(navire.pk))
    return {
        "genere_le": timezone.now().isoformat(timespec="seconds"),
        "blocs": [
            _taches(navire, aujourdhui),
            _maintenance_en_retard(occurrences, agregat),
            _tickets(tickets, agregat),
            _anomalies(navire),
            _stock(agregat),
            _qualifications(user, navire, aujourdhui),
            _listes_a_venir(navire),
            _annonces_sans_accuse(navire, aujourdhui),
            _demandes(navire),
        ],
    }


def releve_courante(navire):
    """Dernière relève validée qui a mis l'équipage actuel à bord, ou None."""
    return ReleveEquipage.objects.filter(
        ship=navire, statut=ReleveEquipage.Statut.VALIDEE, equipage_propose=navire.equipage_a_bord
    ).order_by("-decide_le", "-pk").first()


def _chefs_equipage(navire, equipage):
    marins = get_user_model().objects.filter(is_active=True, profile__ship=navire, profile__equipage=equipage)
    return [m for m in marins if peut_attribuer(m)]


def generer_passation(auteur, navire, releve, equipage_sortant):
    """Fige la synthèse de la relève et prévient les chefs de l'équipage montant ; renvoie (synthèse, créée).

    Idempotent : une relève a au plus une synthèse. Sans effet (None) sur un bâtiment à équipage unique.
    """
    if not passation_activee() or not navire.double_equipage or not navire.equipage_a_bord:
        return None, False
    existante = SynthesePassation.objects.filter(releve=releve).first() if releve else None
    if existante:
        return existante, False
    try:
        with transaction.atomic():
            synthese = SynthesePassation.objects.create(
                ship=navire, releve=releve, equipage_sortant=equipage_sortant, equipage_montant=navire.equipage_a_bord,
                auteur=auteur, contenu=contenu_passation(auteur, navire),
            )
    except IntegrityError:
        # Double clic : une autre requête a créé la synthèse de cette relève.
        return SynthesePassation.objects.get(releve=releve), False
    AuditLog.objects.create(
        actor=auteur, action="passation_generee",
        details=f"navire={navire.name}; equipage_sortant={equipage_sortant or '—'}; equipage_montant={synthese.equipage_montant}",
    )
    for chef in _chefs_equipage(navire, synthese.equipage_montant):
        Notification.objects.create(
            user=chef, target=synthese,
            verb=f"Relève sur {navire.name} : la synthèse de passation de l'équipage {equipage_sortant or 'sortant'} est disponible.",
        )
    return synthese, True


def generer_passation_manuelle(auteur, navire):
    """Bouton du commandement : synthèse de la relève en cours si elle n'existe pas encore ; renvoie (synthèse, erreur)."""
    if not passation_activee():
        return None, "La synthèse de passation est désactivée (Réglages, onglet Seuils par rôle)."
    if not peut_generer_passation(auteur, navire):
        return None, "Seul le commandement de l'unité peut générer la synthèse de passation."
    if not navire.double_equipage or not navire.equipage_a_bord:
        return None, "Cette unité n'a pas de double équipage."
    releve = releve_courante(navire)
    if releve is None:
        return None, "Aucune relève validée n'a mis l'équipage actuel à bord : rien à passer."
    autre = (
        UserProfile.objects.filter(ship=navire).exclude(equipage__in=("", navire.equipage_a_bord))
        .order_by("equipage").values_list("equipage", flat=True).first()
    )
    synthese, _ = generer_passation(auteur, navire, releve, autre or "")
    return synthese, ""


class PassationView(LoginRequiredMixin, DetailView):
    """Page imprimable de la synthèse ; 404 hors du périmètre de l'utilisateur."""
    template_name = "dashboard/passation.html"
    context_object_name = "synthese"

    def get_queryset(self):
        if not passation_activee():
            raise Http404("La synthèse de passation est désactivée.")
        return syntheses_visibles(self.request.user).select_related("ship", "auteur")

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["genere_le"] = timezone.localtime(self.object.created_at)
        contexte["pdf_disponible"] = pdf_disponible()
        return contexte


class PassationPdfView(PassationView):
    template_name = "dashboard/passation_pdf.html"

    def render_to_response(self, contexte, **kwargs):
        reponse = super().render_to_response(contexte, **kwargs)
        reponse.render()
        pdf = html_vers_pdf(reponse.content.decode())
        if pdf is None:
            raise Http404("Export PDF indisponible sur ce poste.")
        synthese = self.object
        return HttpResponse(
            pdf, content_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="passation_{synthese.ship.code}_{synthese.pk}.pdf"'},
        )
