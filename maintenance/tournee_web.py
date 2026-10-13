"""Tournée de matériel : fiche imprimée en un tableau par catégorie, puis compte rendu en série (grille).
Une validation unique crée un compte rendu par équipement, tout ou rien ; périmètre et droits sont
revérifiés équipement par équipement, comme pour le compte rendu individuel."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from accounts.models import AuditLog
from matrix.core.equipage import equipage_a_terre_lecture_seule, suivi_a_terre_sans_validation
from matrix.core.saisie import sans_nul
from threads.utils import ajouter_commentaire

from . import tournee
from .compte_rendu import LONGUEUR_NOTES, instantane, resume
from .models import MaintenanceExecution, MaintenanceOccurrence, OccurrenceStatusLog
from .web_views import _notifier_chefs_de_secteur, _qr_data_uri

CONFORMITES = dict(MaintenanceExecution.CONFORMITY)


class _Abandon(Exception):
    """Une ligne a changé entre l'affichage et la validation : rien n'est enregistré."""


def _identifiants_ou_404(request):
    ids = tournee.identifiants(request.GET.get("ids"))
    if not ids:
        raise Http404("Aucune tournée à afficher")
    return ids


class TourneeImprimerView(LoginRequiredMixin, View):
    """Fiche de tournée imprimable : le QR code de chaque tableau rouvre la grille dans le même ordre."""
    template_name = "maintenance/fiche_tournee.html"

    def get(self, request):
        ids = _identifiants_ou_404(request)
        occurrences = [o for o in tournee.charger(request.user, ids) if o.status != "CANCELLED"]
        groupes = tournee.groupes(occurrences)
        if not groupes:
            raise Http404("Aucune tournée à imprimer")
        for g in groupes:
            g["numero"] = "FT-" + tournee.empreinte([o.pk for o in g["occurrences"]])[:8].upper()
            g["qr"] = _qr_data_uri(request.build_absolute_uri(tournee.adresse("tournee-saisie", g["occurrences"])))
            g["lignes"] = [{
                "designation": o.asset.designation or o.asset.asset_type.name,
                "lieu": tournee.emplacement_de(o.asset),
                "repere": tournee.repere_de(o.asset),
            } for o in g["occurrences"]]
            g["entetes"] = [{"item": it, "libelle": tournee.libelle_colonne(it)} for it in g["items"]]
        return render(request, self.template_name, {
            "groupes": groupes, "grille_url": tournee.adresse("tournee-saisie", [o for g in groupes for o in g["occurrences"]]),
        })


class TourneeSaisieView(LoginRequiredMixin, View):
    """Compte rendu en série : une ligne par équipement, une colonne par ligne de fiche."""
    template_name = "maintenance/tournee_saisie.html"

    @staticmethod
    def _lecture_seule(user):
        return equipage_a_terre_lecture_seule(user) or suivi_a_terre_sans_validation(user)

    def _lot(self, request, ids):
        """(à renseigner, verrouillées) : les équipements que l'appelant peut saisir, et ceux déjà
        en validation ou terminés, que la grille n'écrase pas (fiche individuelle avec motif)."""
        lecture_seule = self._lecture_seule(request.user)
        candidates = [o for o in tournee.charger(request.user, ids)
                      if o.status != "CANCELLED" and (lecture_seule or tournee.peut_ecrire(request.user, o))]
        executions = {e.occurrence_id: e for e in MaintenanceExecution.objects.filter(occurrence__in=candidates)}
        verrouillees = [o for o in candidates if tournee.verrouillee(o, executions.get(o.pk))]
        return [o for o in candidates if o not in verrouillees], verrouillees

    def _afficher(self, request, ids, lot, verrouillees, valeurs=None, erreurs=None, statut=200):
        executions = {e.occurrence_id: e for e in MaintenanceExecution.objects.filter(occurrence__in=lot)}
        groupes = tournee.groupes(lot)
        for rang, g in enumerate(groupes):
            g["colonnes"] = tournee.colonnes_grille(g["items"])
            g["id"] = f"tournee-{rang}"
            g["brouillon"] = tournee.cle_brouillon(ids, rang)
            g["lignes"] = [{
                "cle": o.pk, "libelle": tournee.libelle_equipement(o),
                "titre": o.asset.designation or o.asset.asset_type.name,
                "details": [d for d in (tournee.emplacement_de(o.asset), tournee.repere_de(o.asset)) if d],
                "valeurs": (valeurs or {}).get(o.pk) or tournee.valeurs_enregistrees(g["items"], executions.get(o.pk)),
                "erreurs": (erreurs or {}).get(o.pk, {}),
            } for o in g["occurrences"]]
        statuts = dict(MaintenanceOccurrence.STATUS)
        return render(request, self.template_name, {
            "groupes": groupes, "lecture_seule": self._lecture_seule(request.user),
            "imprimer_url": tournee.adresse("tournee-imprimer", lot + verrouillees),
            "verrouillees": [{
                "libelle": tournee.libelle_equipement(o), "statut": statuts[o.status],
                "url": reverse("occurrence-execute", args=[o.pk]),
            } for g in tournee.groupes(verrouillees) for o in g["occurrences"]],
        }, status=statut)

    def get(self, request):
        ids = _identifiants_ou_404(request)
        lot, verrouillees = self._lot(request, ids)
        if not (lot or verrouillees):
            raise Http404("Aucun équipement à renseigner dans cette tournée")
        ecartes = len(ids) - len(lot) - len(verrouillees)
        if ecartes:
            messages.info(request, f"{ecartes} occurrence{'s' if ecartes > 1 else ''} écartée{'s' if ecartes > 1 else ''} : "
                                   "installation, annulée, hors de votre périmètre ou de vos droits.")
        return self._afficher(request, ids, lot, verrouillees)

    def post(self, request):
        if self._lecture_seule(request.user):
            raise PermissionDenied
        ids = _identifiants_ou_404(request)
        lot_liste, verrouillees = self._lot(request, ids)
        lot = {o.pk: o for o in lot_liste}
        deja = {o.pk for o in verrouillees}
        postes = {}
        for cle, valeur in request.POST.items():
            identifiant, _, colonne = cle.rpartition("__")
            if colonne and identifiant.isdigit():
                postes.setdefault(int(identifiant), {})[colonne] = sans_nul(valeur).strip()[:LONGUEUR_NOTES]
        if not set(postes) <= set(lot) | deja:
            messages.error(request, "Un équipement est introuvable ou hors de votre périmètre : rien n'a été enregistré.")
            return redirect("maintenance-occurrences")
        if postes and not set(postes) & set(lot):
            messages.info(request, "Cette tournée est déjà enregistrée : rien de plus n'a été fait.")
            return redirect("maintenance-occurrences")

        groupes = tournee.groupes(lot_liste)
        valeurs, erreurs, a_enregistrer, non_vus = {}, {}, [], []
        for g in groupes:
            for occ in g["occurrences"]:
                ligne = postes.get(occ.pk, {})
                valeurs[occ.pk] = {**tournee.valeurs_enregistrees(g["items"], None), **ligne}
                results, mesures, err = tournee.lire_ligne(g["items"], ligne)
                observation = ligne.get("observation", "")
                saisi = bool(results or mesures or err)
                # Contrôles saisis : le texte est une observation ; sinon, c'est le motif « non vu ».
                if saisi:
                    a_enregistrer.append((occ, g["items"], results, mesures, observation))
                elif observation:
                    non_vus.append((occ, observation))
                if err:
                    erreurs[occ.pk] = err
        if erreurs:
            messages.error(request, "Corrigez les cellules signalées : rien n'a été enregistré.")
            return self._afficher(request, ids, lot_liste, verrouillees, valeurs, erreurs, 400)
        if not (a_enregistrer or non_vus):
            messages.info(request, "Aucune ligne saisie : rien à enregistrer.")
            return redirect(request.get_full_path())

        try:
            with transaction.atomic():
                self._enregistrer(request.user, a_enregistrer, non_vus)
        except _Abandon as e:
            messages.error(request, f"{e} Rien n'a été enregistré : rouvrez la tournée.")
            return redirect("maintenance-occurrences")
        for occ, items, results, mesures, _ in a_enregistrer:
            conformity = tournee.conformite(items, results, mesures)
            _notifier_chefs_de_secteur(occ, request.user, conformity, resume(items, results, mesures), modification=False)
        faits = len(a_enregistrer)
        messages.success(request, f"{faits} compte{'s' if faits > 1 else ''} rendu{'s' if faits > 1 else ''} enregistré{'s' if faits > 1 else ''}"
                                  + (f", {len(non_vus)} équipement{'s' if len(non_vus) > 1 else ''} non vu{'s' if len(non_vus) > 1 else ''}." if non_vus else "."))
        return redirect("maintenance-occurrences")

    @staticmethod
    def _enregistrer(user, a_enregistrer, non_vus):
        """Un compte rendu par équipement, droits et statut revérifiés sous verrou."""
        concernees = {o.pk for o, *_ in a_enregistrer} | {o.pk for o, _ in non_vus}
        a_jour = {o.pk: o for o in MaintenanceOccurrence.objects.select_for_update().filter(pk__in=concernees)}
        executions = {e.occurrence_id: e for e in MaintenanceExecution.objects.filter(occurrence__in=a_jour.values())}
        for occ_pk in concernees:
            if occ_pk not in a_jour or tournee.verrouillee(a_jour[occ_pk], executions.get(occ_pk)) or not tournee.peut_ecrire(user, a_jour[occ_pk]):
                raise _Abandon("Une occurrence a changé (déjà enregistrée ?) ou n'est plus modifiable par vous.")
        maintenant = timezone.now()
        for occ, items, results, mesures, observation in a_enregistrer:
            occ = a_jour[occ.pk]
            conformity = tournee.conformite(items, results, mesures)
            execution = MaintenanceExecution.objects.filter(occurrence=occ).first() or MaintenanceExecution(occurrence=occ)
            execution.started_at = execution.started_at or maintenant
            execution.completed_at = maintenant
            execution.results, execution.measurements, execution.notes = results, mesures, observation
            execution.conformity = conformity
            execution.executed_by = user
            execution.saisie_origine = instantane(user, execution)
            execution.save()
            execution.intervenants.set([user])
            ancien, occ.status = occ.status, ("WAITING_VALIDATION" if conformity == "NON_CONFORME" else "DONE")
            occ.save(update_fields=["status"])
            OccurrenceStatusLog.objects.create(occurrence=occ, old_status=ancien, new_status=occ.status, user=user, note="Tournée")
            synthese = resume(items, results, mesures)["texte"]
            AuditLog.objects.create(
                actor=user, action="tournee_compte_rendu",
                details=f"occurrence={occ.pk}; {ancien} -> {occ.status}; conformite={conformity}; {synthese}",
            )
            ajouter_commentaire(occ, user, f"Exécution (tournée) : {CONFORMITES[conformity]} — {synthese}")
        for occ, motif in non_vus:
            details = f"occurrence={occ.pk}; motif={motif}"
            if AuditLog.objects.filter(actor=user, action="tournee_non_vu", details=details).exists():
                continue  # double envoi du même motif
            AuditLog.objects.create(actor=user, action="tournee_non_vu", details=details)
            ajouter_commentaire(occ, user, f"Non vu lors de la tournée : {motif}")
