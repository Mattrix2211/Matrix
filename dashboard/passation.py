"""Synthèse de passation du bâtiment à la relève du double équipage.

Aucun moteur propre : elle fige, à la relève, ce que les services existants (vue COMANAV, qualifications,
annonces, listes de service) savent déjà dire du bâtiment, ligne par ligne avec sa portée. Chacun ne lit que son périmètre de
responsabilité et ce qui lui est partagé (ARB-02, AC-03 : `dashboard/passation_perimetre.py`) ; l'équipage n'est pas un critère.
"""
import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from urllib.parse import quote

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView

from accounts.models import AuditLog, UserProfile
from annonces.models import Annonce
from annonces.services import destinataires
from dashboard.aujourdhui import qualifications_equipe
from dashboard.passation_partage import destinataires_proposes, partager, revoquer
from dashboard.passation_perimetre import (
    VERSION_CONTENU, Hierarchie, contenu_visible, couverture, partages_de_ligne, peut_revoquer, peut_voir_partage, portee_du_marin,
)
from demandes.models import Demande
from logistics.models import STATUTS_ANOMALIE_OUVERTS, STATUTS_TICKET_OUVERTS, Anomalie, CorrectiveTicket, StockPiece
from maintenance.models import MaintenanceOccurrence
from matrix.core.equipage import equipage_a_bord
from matrix.core.roles import NIVEAU_VISION_COMMANDEMENT, user_role_level
from matrix.core.scopes import navire_q
from notifications.models import Notification
from org.models import ParametresPassation, PartagePassation, ReleveEquipage, SynthesePassation
from quarts.models import Quart, ServiceGarde
from reports.services import html_vers_pdf, pdf_disponible
from taches.models import Tache
from taches.services import peut_superviser

logger = logging.getLogger(__name__)
JOURS_A_VENIR = 14
LIGNES_PAR_GROUPE = 30  # plafond d'affichage, appliqué à la lecture après filtrage
LIGNES_STOCKEES_PAR_GROUPE = 2000  # garde-fou du contenu figé


def passation_activee():
    """Activée par défaut ; l'administrateur général peut la désactiver pour la flotte."""
    return ParametresPassation.courants().active


def peut_generer_passation(user, navire):
    """Commandement du bâtiment (commandant, second) ; l'administrateur général n'y accède pas par son statut (AC-15)."""
    profil = getattr(user, "profile", None)
    return bool(profil and profil.navire_id_effectif == navire.pk and user_role_level(user) >= NIVEAU_VISION_COMMANDEMENT)


def syntheses_visibles(user):
    """Synthèses du bâtiment de l'utilisateur : tout marin du bâtiment peut ouvrir la page, qui ne lui rend que ce que son
    périmètre couvre ou qui lui est partagé (`passation_perimetre.contenu_visible`). Jamais un autre bâtiment ni, par son seul
    statut, l'administrateur technique ou général (aucune consultation systématique conférée, AC-15)."""
    couv = couverture(user)
    if couv is None:
        return SynthesePassation.objects.none()
    return SynthesePassation.objects.filter(ship_id=couv.navire_id)


def _ligne(cle, titre, detail, url, ligne_portee, etat="", partageable=True):
    return {"cle": cle, "titre": titre, "detail": detail, "url": url, "etat": etat, "portee": ligne_portee, "partageable": partageable}


def _groupe(titre, lignes):
    """Toutes les lignes sont conservées avec leur portée : le plafond d'affichage s'applique à la lecture, après filtrage."""
    if len(lignes) > LIGNES_STOCKEES_PAR_GROUPE:
        logger.warning("Synthèse de passation : groupe « %s » tronqué à %s lignes sur %s.", titre, LIGNES_STOCKEES_PAR_GROUPE, len(lignes))
        lignes = lignes[:LIGNES_STOCKEES_PAR_GROUPE]
    return {"titre": titre, "total": len(lignes), "lignes": lignes, "plus": 0}


def _bloc(cle, titre, groupes, vide):
    return {"cle": cle, "titre": titre, "total": sum(g["total"] for g in groupes), "groupes": groupes, "vide": vide}


def _date(valeur):
    return f"{valeur:%d/%m/%Y}" if valeur else "sans échéance"


def _nom(marin):
    return (marin.get_full_name() or marin.get_username()) if marin else "personne"


def _taches(navire, aujourdhui):
    ouvertes = list(
        Tache.objects.filter(navire_q(navire.pk, "assigne__profile__"), partagee=True, statut__in=Tache.STATUTS_OUVERTS)
        .select_related("assigne__profile").order_by("pk")
    )
    libelles = dict(Tache.STATUT_CHOICES)
    groupes = []
    memo = {}
    # Les tâches bloquées d'abord : ce sont elles que l'équipage montant doit débloquer.
    for statut in (Tache.STATUT_BLOQUEE, Tache.STATUT_EN_COURS, Tache.STATUT_A_FAIRE):
        lignes = [
            _ligne(
                f"tache:{t.pk}", t.titre,
                f"{_nom(t.assigne)} · échéance {_date(t.echeance)}" + (f" · {t.motif_blocage}" if t.motif_blocage else ""),
                reverse("tache-detail", args=[t.pk]), portee_du_marin(t.assigne, memo),
                "danger" if t.en_retard_au(aujourdhui) else ("attention" if statut == Tache.STATUT_BLOQUEE else ""),
            )
            for t in ouvertes if t.statut == statut
        ]
        groupes.append(_groupe(libelles[statut], lignes))
    return _bloc("taches", "Tâches ouvertes et bloquées", groupes,
                 "Aucune tâche ouverte (les tâches personnelles non partagées ne figurent pas ici).")


def _portee_du_materiel(h, o):
    """Portée d'un matériel ou d'une installation (service, secteur, section)."""
    return h.portee(service_id=o.service_id, sector_id=o.sector_id, section_id=o.section_id)


def _maintenance_en_retard(occurrences, h):
    retards = (
        MaintenanceOccurrence.objects.filter(occurrences, status="OVERDUE")
        .select_related("installation_maintenance__installation", "plan", "asset").prefetch_related("assignees")
        .order_by("scheduled_for")
    )
    lignes = []
    for o in retards:
        cible = o.asset or o.installation_maintenance.installation
        lignes.append(_ligne(
            f"maintenance:{o.pk}", o.titre_affiche, f"Prévue le {_date(o.scheduled_for)}", reverse("occurrence-execute", args=[o.pk]),
            {**_portee_du_materiel(h, cible), "marins": sorted(a.pk for a in o.assignees.all())}, "danger"))
    return _bloc("maintenance", "Maintenances en retard", [_groupe("En retard", lignes)], "Aucune maintenance en retard.")


def _tickets(tickets, h):
    ouverts = list(
        CorrectiveTicket.objects.filter(tickets, status__in=STATUTS_TICKET_OUVERTS)
        .select_related("asset", "installation").prefetch_related("assignees").order_by("-severity", "reported_at")
    )
    libelles = dict(CorrectiveTicket.STATUS)
    groupes = []
    for statut in STATUTS_TICKET_OUVERTS:
        lignes = [
            _ligne(f"ticket:{o.pk}", str(o), o.description[:120], reverse("ticket-detail", args=[o.pk]),
                   {**_portee_du_materiel(h, o.asset or o.installation), "marins": sorted(a.pk for a in o.assignees.all())},
                   "attention" if o.severity >= 4 else "")
            for o in ouverts if o.status == statut
        ]
        if lignes:
            groupes.append(_groupe(libelles.get(statut, statut), lignes))
    return _bloc("tickets", "Tickets correctifs ouverts", groupes, "Aucun ticket correctif ouvert.")


def _anomalies(navire, h):
    ouvertes = Anomalie.objects.filter(navire_q(navire.pk), statut__in=STATUTS_ANOMALIE_OUVERTS).order_by("-gravite", "created_at")
    lignes = [
        _ligne(f"anomalie:{a.pk}", a.titre,
               f"Gravité {a.gravite} · {a.get_statut_display()}" + (f" · {a.localisation}" if a.localisation else ""),
               reverse("anomalie-detail", args=[a.pk]),
               h.portee(service_id=a.service_id, sector_id=a.sector_id, section_id=a.section_id, marins=[a.created_by_id]), "attention")
        for a in ouvertes
    ]
    return _bloc("anomalies", "Anomalies ouvertes", [_groupe("Ouvertes", lignes)], "Aucune anomalie ouverte.")


def _stock(filtre_stock, h):
    pieces = StockPiece.objects.filter(filtre_stock, quantite__lt=F("quantite_minimale")).order_by("reference")
    lignes = [
        _ligne(f"stock:{p.pk}", f"{p.reference} — {p.designation}", f"{p.quantite} en stock, minimum {p.quantite_minimale}",
               reverse("stock-piece-list"), h.portee(service_id=p.service_id, sector_id=p.sector_id, section_id=p.section_id), "attention")
        for p in pieces
    ]
    return _bloc("stock", "Stock sous le seuil", [_groupe("Sous le seuil", lignes)], "Stock conforme.")


def _qualifications(user, navire, aujourdhui):
    """Dossiers individuels de formation : soumis à leurs propres habilitations, ils ne se partagent pas (AC-03)."""
    memo = {}
    lignes = [
        _ligne(f"qualification:{q['marin'].pk}:{q['cours']}", q["titre"], q["detail"], q["url"], portee_du_marin(q["marin"], memo),
               "danger" if q["expiree"] else "attention", partageable=False)
        for q in qualifications_equipe(user, aujourdhui, navire)
    ]
    return _bloc("qualifications", "Qualifications à renouveler à bord", [_groupe("À renouveler", lignes)],
                 "Aucune qualification à renouveler.")


def _listes_a_venir(navire, h):
    maintenant = timezone.now()
    horizon = maintenant + timedelta(days=JOURS_A_VENIR)
    groupes = []
    for titre, modele, route in (("Quarts", Quart, "quart-detail"), ("Services de garde", ServiceGarde, "garde-detail")):
        lignes = []
        for liste in modele.objects.filter(navire_q(navire.pk), statut=modele.STATUT_PUBLIEE).select_related("fonction"):
            creneaux = list(liste.creneaux.filter(debut__gte=maintenant, debut__lte=horizon).order_by("debut"))
            if creneaux:
                libelle = (liste.nom or str(liste.fonction or titre)) + (
                    " (prévisionnelle, non activée)" if getattr(liste, "application", "") == "PREVISIONNELLE" else ""
                )
                lignes.append(_ligne(
                    f"liste:{modele.__name__.lower()}:{liste.pk}",
                    libelle + (f" (équipage {liste.equipage})" if liste.equipage else ""),
                    f"{len(creneaux)} créneau(x), du {timezone.localtime(creneaux[0].debut):%d/%m %H:%M} "
                    f"au {timezone.localtime(creneaux[-1].debut):%d/%m %H:%M}",
                    reverse(route, args=[liste.pk]),
                    h.portee(service_id=liste.service_id, sector_id=liste.sector_id, section_id=liste.section_id),
                ))
        groupes.append(_groupe(titre, lignes))
    return _bloc("listes", f"Quarts et services à venir ({JOURS_A_VENIR} jours)", groupes,
                 "Aucune liste publiée n'a de créneau à venir.")


def _annonces_sans_accuse(navire, aujourdhui, h):
    actives = (Annonce.objects.filter(ship=navire, accuse_requis=True, archivee=False, date_effet__lte=aujourdhui)
               .filter(Q(date_fin__isnull=True) | Q(date_fin__gte=aujourdhui)))
    lignes = []
    for annonce in actives:
        accuses = set(annonce.lectures.filter(accuse=True, version_lue__gte=annonce.version).values_list("user_id", flat=True))
        concernes = list(destinataires(annonce))
        manquants = [m for m in concernes if m.pk not in accuses]
        if manquants:
            # Les compteurs portent sur tous les destinataires de l'annonce : la ligne n'est lue qu'avec la portée de l'annonce.
            lignes.append(_ligne(
                f"annonce:{annonce.pk}", annonce.titre,
                f"{len(manquants)} accusé(s) manquant(s) sur {len(concernes)} destinataire(s)",
                reverse("annonce-detail", args=[annonce.pk]),
                h.portee(service_id=annonce.service_id, sector_id=annonce.sector_id, section_id=annonce.section_id), "attention"))
    return _bloc("annonces", "Annonces actives sans accusé complet", [_groupe("Accusés manquants", lignes)],
                 "Toutes les annonces à accusé sont acquittées.")


def _demandes(navire, h):
    en_cours = (Demande.objects.filter(navire_q(navire.pk), etat__in=Demande.ETATS_OUVERTS)
                .select_related("responsable").order_by("created_at"))
    lignes = [
        _ligne(f"demande:{d.pk}", d.titre, f"{d.get_etat_display()} · responsable {_nom(d.responsable)}",
               reverse("demande-detail", args=[d.pk]),
               h.portee(service_id=d.service_id, sector_id=d.sector_id, section_id=d.section_id, marins=[d.declarant_id, d.responsable_id]),
               "attention" if d.priorite == Demande.PRIORITE_URGENTE else "")
        for d in en_cours
    ]
    return _bloc("demandes", "Difficultés signalées en cours", [_groupe("En cours", lignes)], "Aucune demande en cours.")


def contenu_passation(user, navire):
    """Instantané JSON du bâtiment, ligne par ligne avec sa portée ; `user` doit relever du commandement (il borne les
    qualifications). Le filtrage par périmètre se fait à la lecture (`passation_perimetre.contenu_visible`)."""
    aujourdhui = timezone.localdate()
    occurrences = navire_q(navire.pk, "asset__") | navire_q(navire.pk, "installation_maintenance__installation__")
    tickets = navire_q(navire.pk, "asset__") | navire_q(navire.pk, "installation__")
    h = Hierarchie(navire.pk)
    return {
        "version": VERSION_CONTENU,
        "genere_le": timezone.now().isoformat(timespec="seconds"),
        "blocs": [
            _taches(navire, aujourdhui),
            _maintenance_en_retard(occurrences, h),
            _tickets(tickets, h),
            _anomalies(navire, h),
            _stock(navire_q(navire.pk), h),
            _qualifications(user, navire, aujourdhui),
            _listes_a_venir(navire, h),
            _annonces_sans_accuse(navire, aujourdhui, h),
            _demandes(navire, h),
        ],
    }


def releve_courante(navire):
    """Dernière relève validée qui a mis l'équipage actuel à bord, ou None."""
    return ReleveEquipage.objects.filter(
        ship=navire, statut=ReleveEquipage.Statut.VALIDEE, equipage_propose=equipage_a_bord(navire)
    ).order_by("-decide_le", "-pk").first()


def _chefs_equipage(navire, equipage):
    marins = get_user_model().objects.filter(is_active=True, profile__ship=navire, profile__equipage=equipage)
    return [m for m in marins if peut_superviser(m)]


def generer_passation(auteur, navire, releve, equipage_sortant):
    """Fige la synthèse de la relève et prévient les chefs de l'équipage montant ; renvoie (synthèse, créée).

    Idempotent : une relève a au plus une synthèse. Sans effet (None) sur un bâtiment à équipage unique.
    """
    a_bord = equipage_a_bord(navire)
    if not passation_activee() or not navire.double_equipage or not a_bord:
        return None, False
    existante = SynthesePassation.objects.filter(releve=releve).first() if releve else None
    if existante:
        return existante, False
    try:
        with transaction.atomic():
            synthese = SynthesePassation.objects.create(
                ship=navire, releve=releve, equipage_sortant=equipage_sortant, equipage_montant=a_bord,
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
    a_bord = equipage_a_bord(navire)
    if not navire.double_equipage or not a_bord:
        return None, "Cette unité n'a pas de double équipage."
    releve = releve_courante(navire)
    if releve is None:
        return None, "Aucune relève validée n'a mis l'équipage actuel à bord : rien à passer."
    autre = (
        UserProfile.objects.filter(ship=navire).exclude(equipage__in=("", a_bord))
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
        contexte["contenu"] = contenu_visible(self.request.user, self.object, LIGNES_PAR_GROUPE)
        return contexte


class PassationPartageView(LoginRequiredMixin, View):
    """Partage ciblé d'une information (AC-03) : page de la ligne, de ses partages et du formulaire ; lecture seule pour le destinataire."""
    template_name = "dashboard/passation_partage.html"

    def _synthese(self, request, pk):
        if not passation_activee():
            raise Http404("La synthèse de passation est désactivée.")
        return get_object_or_404(syntheses_visibles(request.user).select_related("ship"), pk=pk)

    def _ligne_visible(self, request, synthese, cle):
        """Ligne rendue à `request.user` (périmètre ou partage) ; 404 sinon : l'existence d'une ligne ne se devine pas."""
        for bloc in contenu_visible(request.user, synthese, plafond=10 ** 6)["blocs"]:
            for groupe in bloc["groupes"]:
                for ligne in groupe["lignes"]:
                    if ligne.get("cle") == cle:
                        return ligne
        raise Http404("Information introuvable.")

    def _rendre(self, request, synthese, ligne, erreurs=(), statut=200):
        cle = ligne["cle"]
        partages = [(p, peut_revoquer(request.user, p)) for p in partages_de_ligne(synthese, cle) if peut_voir_partage(request.user, p)]
        contexte = {
            "synthese": synthese, "ligne": ligne, "partages": partages, "erreurs": list(erreurs),
            "choix": destinataires_proposes(synthese) if ligne.get("peut_partager") else None,
            "types": PartagePassation.Destinataire.choices,
        }
        return render(request, self.template_name, contexte, status=statut)

    def get(self, request, pk):
        synthese = self._synthese(request, pk)
        return self._rendre(request, synthese, self._ligne_visible(request, synthese, request.GET.get("ligne", "")))

    def post(self, request, pk):
        synthese = self._synthese(request, pk)
        cle = request.POST.get("ligne", "")
        ligne = self._ligne_visible(request, synthese, cle)
        try:
            partager(request.user, synthese, cle, request.POST.get("type_destinataire", ""), request.POST.get("destinataire", ""))
        except ValidationError as exc:
            return self._rendre(request, synthese, ligne, exc.messages, 400)
        messages.success(request, "Information partagée en lecture seule.")
        return redirect(f"{reverse('passation-partage', args=[synthese.pk])}?ligne={quote(cle)}")


class PassationRevocationView(LoginRequiredMixin, View):
    """Révocation d'un partage actif ; la trace du partage et de sa révocation est conservée."""

    def post(self, request, pk, partage_pk):
        if not passation_activee():
            raise Http404("La synthèse de passation est désactivée.")
        synthese = get_object_or_404(syntheses_visibles(request.user), pk=pk)
        partage = get_object_or_404(PartagePassation, pk=partage_pk, synthese=synthese)
        if not peut_revoquer(request.user, partage):
            raise Http404  # l'existence d'un partage ne se devine pas
        revoquer(request.user, partage)
        messages.success(request, "Partage révoqué : le destinataire ne le voit plus.")
        return redirect(f"{reverse('passation-partage', args=[synthese.pk])}?ligne={quote(partage.cle_ligne)}")


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
