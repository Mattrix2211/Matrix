"""Compte rendu d'une intervention corrective, avec ou sans fiche (panne imprévue).

Même formulaire que le compte rendu préventif : intervenants, début, fin, temps passé comparé à l'estimé, constat,
diagnostic, action réalisée, pièces prélevées dans le stock, observations et conformité. Le diagnostic et l'action
reprennent `diagnostic_final` et `solution` du ticket, qui garde son propre cycle de vie.
"""
import json
import uuid

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from accounts.models import AuditLog
from assets import fiche_flotte
from assets.models import Asset, Installation
from logistics.models import CorrectiveTicket, StockPiece, TicketStatusLog
from logistics.stock import StockInsuffisant, prelever
from matrix.core.equipage import equipage_a_terre_lecture_seule, suivi_a_terre_sans_validation
from matrix.core.mixins import build_scope_q
from matrix.core.role_thresholds import niveau_requis_pour
from matrix.core.roles import RoleLevel, user_role_level
from matrix.core.saisie import entier_ou_none, sans_nul
from matrix.core.scopes import scope_filters_for_user
from threads.utils import ajouter_commentaire, contexte_discussion

from .compte_rendu import (
    ETATS, LONGUEUR_MOTIF, LONGUEUR_NOTES, differences, instantane, lignes_de_saisie, lire_saisie, resume,
)
from .diffusion import CONFORMITES, notifier_compte_rendu
from .formats import lire_datetime, valeur_datetime
from .historique import derniers_releves
from .models import CompteRenduCorrectif, ModificationCompteRendu
from .web_views import _etat_saisie

LONGUEUR_TEXTE = 5000
MAX_PIECES = 5
QUANTITE_MAX = 100_000


class _Conflit(Exception):
    """Le compte rendu a changé entre l'affichage du formulaire et son envoi."""


class _Rejeu(Exception):
    """Ce formulaire a déjà été enregistré (double envoi)."""


class _Refus(Exception):
    """Une règle métier refuse l'enregistrement (message affiché au marin)."""


def _uuid_ou_none(texte):
    try:
        return uuid.UUID(str(texte or "").strip())
    except ValueError:
        return None


def _fiches_possibles(installation, asset):
    """Versions de fiche que l'équipement peut suivre pour une intervention corrective."""
    if installation is not None:
        versions = [fiche.version_validee for fiche in installation.maintenances.all()]
    elif asset.article_catalogue_id:
        fiches = fiche_flotte.fiches_applicables(asset.article_catalogue.categorie)
        versions = [fiche_flotte.version_applicable(asset, fiche) for fiche in fiches.values()]
    else:
        versions = []
    return [v for v in versions if v is not None]


def _pieces_demandees(post):
    """[(identifiant de pièce, quantité)] des lignes remplies du formulaire ; None si une ligne est illisible."""
    demandes = []
    for brut_piece, brut_quantite in zip(post.getlist("piece_id")[:MAX_PIECES], post.getlist("piece_qte")[:MAX_PIECES]):
        if not (brut_piece.strip() or brut_quantite.strip()):
            continue
        piece, quantite = entier_ou_none(brut_piece), entier_ou_none(brut_quantite)
        if piece is None or not quantite or quantite > QUANTITE_MAX:
            return None
        demandes.append((piece, quantite))
    return demandes


class CompteRenduCorrectifView(LoginRequiredMixin, View):
    """Compte rendu correctif d'un ticket existant, ou d'une panne imprévue (`nouveau`, qui ouvre alors le ticket)."""
    template_name = "maintenance/correctif.html"

    @staticmethod
    def _charger(request, ticket_pk):
        """(ticket, compte rendu, installation, matériel) dans le périmètre de l'appelant ; 404 hors périmètre."""
        user = request.user
        if ticket_pk is None:
            source = request.POST if request.method == "POST" else request.GET
            cle_installation = _uuid_ou_none(source.get("installation"))
            installation = Installation.objects.filter(build_scope_q(user, "")).filter(pk=cle_installation).first() if cle_installation else None
            cle = _uuid_ou_none(source.get("asset"))
            asset = Asset.objects.filter(build_scope_q(user, "")).select_related("article_catalogue__categorie").filter(pk=cle).first() if cle else None
            if (installation is None) == (asset is None):
                raise Http404("Équipement introuvable")
            return None, None, installation, asset
        ticket = (CorrectiveTicket.objects.select_related("asset__article_catalogue__categorie", "installation")
                  .filter(build_scope_q(user, "asset__", "installation__")).filter(pk=ticket_pk).first())
        if ticket is None:
            raise Http404("Ticket introuvable")
        if user not in ticket.assignees.all() and user_role_level(user) < niveau_requis_pour(user, "maintenance_occurrence_gestion_tiers"):
            raise PermissionDenied
        cr = CompteRenduCorrectif.objects.filter(ticket=ticket).first()
        return ticket, cr, ticket.installation, ticket.asset

    @staticmethod
    def _version(request, cr, installation, asset):
        """Version de fiche suivie : celle du compte rendu, sinon celle demandée si l'équipement peut la suivre."""
        if cr is not None:
            return cr.version_fiche
        demandee = entier_ou_none((request.POST if request.method == "POST" else request.GET).get("fiche"))
        return next((v for v in _fiches_possibles(installation, asset) if v.pk == demandee), None) if demandee else None

    def get(self, request, ticket_pk=None):
        ticket, cr, installation, asset = self._charger(request, ticket_pk)
        version = self._version(request, cr, installation, asset)
        return render(request, self.template_name, self._contexte(request, ticket, cr, installation, asset, version))

    @staticmethod
    def _contexte(request, ticket, cr, installation, asset, version, valeurs=None, erreurs=None):
        user = request.user
        equipement = installation or asset
        items = list(version.items.order_by("order", "pk")) if version else []
        if valeurs is None:
            valeurs = {
                "constat": cr.constat if cr else "", "diagnostic": cr.diagnostic if cr else (ticket.diagnostic_final if ticket else ""),
                "action": cr.action_realisee if cr else (ticket.solution if ticket else ""),
                "notes": cr.notes if cr else "", "conformity": cr.conformity if cr else "",
                "debut": valeur_datetime(cr.started_at) if cr else "", "fin": valeur_datetime(cr.completed_at) if cr else "",
                "estime": (cr.duree_estimee_min or "") if cr else (version.duree_estimee_min or "" if version else ""),
                "gravite": "3",
                "results": cr.results if cr else {}, "mesures": cr.measurements if cr else {},
                "intervenants": {u.pk for u in cr.intervenants.all()} if cr else None,
            }
        lignes = lignes_de_saisie(items, valeurs["results"], valeurs["mesures"])
        derniers = derniers_releves(items, installation, asset)
        for ligne in lignes:
            ligne["dernier"] = derniers.get(str(ligne["item"].cle))
        candidats = list(ticket.assignees.all()) if ticket else []
        if user not in candidats:
            candidats.append(user)
        coches = valeurs["intervenants"]
        peut_prelever = user_role_level(user) >= RoleLevel.CHEF_SECTION
        deja_termine = cr is not None
        peut_corriger = user_role_level(user) >= niveau_requis_pour(user, "maintenance_compte_rendu_correction")
        if peut_prelever:
            filtres = scope_filters_for_user(user)
            pieces = (StockPiece.objects.filter(**filtres) if filtres else StockPiece.objects.all()).filter(quantite__gt=0).order_by("reference")
        else:
            pieces = []
        anomalie = f"{reverse('anomalie-create')}?{'installation' if installation else 'asset'}={equipement.pk}"
        return {
            "ticket": ticket, "cr": cr, "equipement": equipement, "installation": installation, "asset": asset,
            "version": version, "items": items, "lignes": lignes, "etats": ETATS, "valeurs": valeurs,
            "erreurs": erreurs or [], "anomalie_url": anomalie, "resume": resume(items, valeurs["results"], valeurs["mesures"]),
            "operations": {"faites": sum(1 for ligne in lignes if ligne["etat"] or ligne["valeur"]), "total": len(items)},
            "intervenants": [{"user": u, "coche": (u.pk in coches) if coches is not None else True} for u in candidats],
            "fiches": _fiches_possibles(installation, asset) if cr is None else [],
            "jeton": uuid.uuid4(), "deja_termine": deja_termine, "peut_prelever": peut_prelever, "pieces": pieces,
            "pieces_prelevees": cr.pieces if cr else [], "lignes_pieces": range(MAX_PIECES if peut_prelever else 0),
            "lecture_seule": equipage_a_terre_lecture_seule(user) or (deja_termine and not peut_corriger),
            "correction_reservee": deja_termine and not peut_corriger,
            "menu_fiche": [
                {"libelle": "Historique et relevés de l'équipement", "icone": "historique",
                 "url": reverse("historique-installation" if installation else "historique-materiel", args=[equipement.pk])},
                *([{"libelle": "Ouvrir le ticket", "icone": "ticket", "url": reverse("ticket-detail", args=[ticket.pk])}] if ticket else []),
            ],
            **(contexte_discussion(ticket, "ticket-comment-create") if ticket else {}),
        }

    def post(self, request, ticket_pk=None):
        user = request.user
        if equipage_a_terre_lecture_seule(user) or suivi_a_terre_sans_validation(user):
            raise PermissionDenied
        ticket, cr, installation, asset = self._charger(request, ticket_pk)
        deja_termine = cr is not None
        if deja_termine and user_role_level(user) < niveau_requis_pour(user, "maintenance_compte_rendu_correction"):
            if cr.executed_by_id != user.pk:
                raise PermissionDenied
            messages.warning(request, "Ce compte rendu est déjà enregistré : seule une correction par un chef de secteur peut le modifier.")
            return redirect("correctif-compte-rendu", ticket_pk=ticket.pk)

        jeton = _uuid_ou_none(request.POST.get("jeton"))
        if jeton is None:
            raise Http404("Formulaire périmé")
        if not deja_termine:
            existant = CompteRenduCorrectif.objects.filter(jeton=jeton, executed_by=user).first()
            if existant:
                messages.info(request, "Ce compte rendu est déjà enregistré.")
                return redirect("correctif-compte-rendu", ticket_pk=existant.ticket_id)

        version = self._version(request, cr, installation, asset)
        if cr is None and entier_ou_none(request.POST.get("fiche")) and version is None:
            raise Http404("Fiche inconnue pour cet équipement")
        items = list(version.items.order_by("order", "pk")) if version else []
        results, mesures, erreurs = lire_saisie(items, request.POST)
        texte = {c: sans_nul(request.POST.get(c, "")).strip() for c in ("constat", "diagnostic", "action", "notes", "motif")}
        for champ, libelle in (("constat", "Le constat"), ("diagnostic", "Le diagnostic"), ("action", "L'action réalisée")):
            if len(texte[champ]) > LONGUEUR_TEXTE:
                erreurs.append(f"{libelle} est limité à {LONGUEUR_TEXTE} caractères.")
        if len(texte["notes"]) > LONGUEUR_NOTES:
            erreurs.append(f"Les observations sont limitées à {LONGUEUR_NOTES} caractères.")
        if len(texte["motif"]) > LONGUEUR_MOTIF:
            erreurs.append(f"Le motif est limité à {LONGUEUR_MOTIF} caractères.")
        if ticket is None and not texte["constat"]:
            erreurs.append("Le constat est à renseigner : il décrit la panne.")
        conformity = request.POST.get("conformity", "")
        if conformity not in dict(CompteRenduCorrectif._meta.get_field("conformity").choices):
            erreurs.append("La conformité finale est à déclarer.")
        if deja_termine and not texte["motif"]:
            erreurs.append("Le motif de la modification est obligatoire.")
        debut, err_debut = lire_datetime(request.POST.get("debut"))
        fin, err_fin = lire_datetime(request.POST.get("fin"))
        erreurs += [e for e in (err_debut, err_fin) if e]
        if debut and fin and fin < debut:
            erreurs.append("La fin de l'intervention précède son début.")
        estime_brut = request.POST.get("estime", "").strip()
        estime = entier_ou_none(estime_brut)
        if estime_brut and (estime is None or estime > 100_000):
            erreurs.append("La durée estimée est un nombre entier de minutes.")
            estime = None
        gravite = entier_ou_none(request.POST.get("gravite")) or 3
        if not 1 <= gravite <= 5:
            gravite = 3

        autorises = {u.pk for u in ticket.assignees.all()} | {user.pk} if ticket else {user.pk}
        intervenants = {entier_ou_none(i) for i in request.POST.getlist("intervenants")} & autorises
        demandes = _pieces_demandees(request.POST)
        if demandes is None:
            erreurs.append("Une ligne de pièce est illisible : choisissez une pièce et une quantité entière.")
            demandes = []
        if demandes and user_role_level(user) < RoleLevel.CHEF_SECTION:
            raise PermissionDenied

        pieces = []
        if not erreurs and demandes:
            filtres = scope_filters_for_user(user)
            disponibles = StockPiece.objects.filter(**filtres) if filtres else StockPiece.objects.all()
            par_id = {p.pk: p for p in disponibles.filter(pk__in=[d[0] for d in demandes])}
            demande_par_piece = {}
            for pk, quantite in demandes:
                demande_par_piece[pk] = demande_par_piece.get(pk, 0) + quantite
            for pk, quantite in demande_par_piece.items():
                piece = par_id.get(pk)
                if piece is None:
                    erreurs.append("Pièce introuvable ou hors de votre périmètre.")
                elif quantite > piece.quantite:
                    erreurs.append(f"Stock insuffisant : {piece.quantite} unité(s) disponible(s) pour {piece.reference}.")
                else:
                    pieces.append((piece, quantite))

        valeurs = {
            "constat": texte["constat"], "diagnostic": texte["diagnostic"], "action": texte["action"], "notes": texte["notes"],
            "conformity": conformity, "debut": valeur_datetime(debut), "fin": valeur_datetime(fin), "estime": estime or "",
            "gravite": str(gravite), "results": results, "mesures": mesures, "intervenants": intervenants,
        }
        original = cr.executed_by if cr else None
        if not erreurs:
            try:
                with transaction.atomic():
                    ticket, cr, modifie = self._ecrire(
                        user, ticket, installation, asset, version, items, valeurs, (debut, fin), texte["motif"], jeton, gravite,
                        pieces, deja_termine,
                    )
            except _Rejeu:
                messages.info(request, "Ce compte rendu est déjà enregistré.")
                return redirect("historique-installation" if installation else "historique-materiel", pk=(installation or asset).pk)
            except (_Conflit, _Refus) as erreur:
                erreurs.append(str(erreur))
        if erreurs:
            return render(request, self.template_name, self._contexte(
                request, ticket, cr, installation, asset, version, valeurs, erreurs,
            ), status=400)

        synthese = resume(items, results, mesures)
        if deja_termine and not modifie:
            messages.info(request, "Aucun changement : le compte rendu n'a pas été modifié.")
            return redirect("correctif-compte-rendu", ticket_pk=ticket.pk)
        secteur = (installation or asset).sector_id
        notifier_compte_rendu(
            secteur, f"intervention corrective sur {installation or asset}", ticket, user, conformity,
            synthese["texte"] if items else (valeurs["constat"] or valeurs["action"])[:80] or "intervention corrective",
            synthese["a_surveiller"], modification=deja_termine, original=original,
        )
        ajouter_commentaire(ticket, user, f"{'Correction du compte rendu' if deja_termine else 'Compte rendu d’intervention'} : "
                                          f"{CONFORMITES[conformity]}" + (f" — {synthese['texte']}" if items else ""))
        messages.success(request, "Compte rendu enregistré." if not deja_termine else "Compte rendu corrigé, la saisie d'origine est conservée.")
        return redirect("ticket-detail", pk=ticket.pk)

    @staticmethod
    def _ecrire(user, ticket, installation, asset, version, items, valeurs, dates, motif, jeton, gravite, pieces, corrige):
        """Écrit le ticket (panne imprévue), le compte rendu et les prélèvements ; tout ou rien."""
        maintenant = timezone.now()
        if ticket is None:
            ticket = CorrectiveTicket.objects.create(
                asset=asset, installation=installation, description=valeurs["constat"], severity=gravite,
                created_by=user, updated_by=user,
            )
            ticket.assignees.add(user)
            TicketStatusLog.objects.create(ticket=ticket, old_status="REPORTED", new_status="REPORTED", user=user)
            AuditLog.objects.create(actor=user, action="create_ticket", details=f"ticket={ticket.pk}; {installation or asset}; compte rendu correctif")
            cr = None
        else:
            ticket = CorrectiveTicket.objects.select_for_update(of=("self",)).get(pk=ticket.pk)
            cr = CompteRenduCorrectif.objects.filter(ticket=ticket).select_related("executed_by").first()
        deja_termine = cr is not None
        if deja_termine != corrige:
            raise _Conflit("Ce compte rendu a été enregistré entre-temps : rechargez la page avant de continuer.")
        if cr is None:
            cr = CompteRenduCorrectif(ticket=ticket, jeton=jeton, executed_by=user, created_by=user, version_fiche=version)
        original = cr.executed_by if deja_termine else None
        avant = _etat_saisie(items, cr) if deja_termine else None
        origine_avant = instantane(original, cr) if deja_termine and cr.saisie_origine is None else None

        cr.started_at = dates[0] or cr.started_at or maintenant
        cr.completed_at = dates[1] or cr.completed_at or maintenant
        cr.duree_estimee_min = valeurs["estime"] or None
        cr.constat, cr.diagnostic, cr.action_realisee = valeurs["constat"], valeurs["diagnostic"], valeurs["action"]
        cr.notes, cr.conformity = valeurs["notes"], valeurs["conformity"]
        cr.results, cr.measurements = valeurs["results"], valeurs["mesures"]
        cr.updated_by = user
        if deja_termine:
            if origine_avant:
                cr.saisie_origine = origine_avant
        else:
            cr.saisie_origine = instantane(user, cr)
        try:
            with transaction.atomic():
                cr.save()
        except IntegrityError:
            raise _Rejeu()
        cr.intervenants.set(valeurs["intervenants"])

        lot = str(jeton)
        if pieces and not any(p.get("lot") == lot for p in cr.pieces):
            for piece, quantite in pieces:
                try:
                    prelever(user, piece, quantite, ticket)
                except StockInsuffisant:
                    raise _Refus(f"Stock insuffisant : la quantité disponible pour {piece.reference} a changé entre-temps, réessayez.")
                cr.pieces.append({"piece": piece.pk, "reference": piece.reference, "designation": piece.designation,
                                  "quantite": quantite, "lot": lot})
            cr.save(update_fields=["pieces", "updated_at"])

        # Le ticket reprend le diagnostic et la solution du compte rendu, avec trace de ce qui change.
        rex = (ticket.diagnostic_final, ticket.solution)
        if rex != (cr.diagnostic, cr.action_realisee):
            ticket.diagnostic_final, ticket.solution = cr.diagnostic, cr.action_realisee
            ticket.save(update_fields=["diagnostic_final", "solution", "updated_at"])
            AuditLog.objects.create(actor=user, action="ticket_rex_via_compte_rendu", details=f"ticket={ticket.pk}; avant={rex!r}")

        modifie = False
        if deja_termine:
            apres = _etat_saisie(items, cr)
            modifs = {c: {"avant": avant[c], "apres": apres[c]} for c in apres if avant[c] != apres[c]}
            modifie = bool(modifs)
            if modifie:
                ModificationCompteRendu.objects.create(correctif=cr, auteur=user, motif=motif, modifications=differences(avant, apres))
                AuditLog.objects.create(
                    actor=user, action="correctif_compte_rendu_modifie",
                    details=f"ticket={ticket.pk}; motif={motif}; modifications={json.dumps(modifs, ensure_ascii=False)}",
                )
        else:
            AuditLog.objects.create(
                actor=user, action="correctif_compte_rendu", details=f"ticket={ticket.pk}; conformite={cr.conformity}",
            )
        return ticket, cr, modifie
