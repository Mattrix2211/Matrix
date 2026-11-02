"""Importe le référentiel des bâtiments (circulaire 2025 et mises à jour) : idempotent, sans jamais écraser une saisie
faite en administration, sans rien supprimer. Les unités Matrix portant le même nom sont reliées à leur référence."""
from django.core.management.base import BaseCommand
from django.db import transaction

from org.data import referentiel_batiments as donnees
from org.models import ReferenceBatiment, Ship, TypeBatiment

Statut = ReferenceBatiment.Statut


class Command(BaseCommand):
    help = "Importe le référentiel des bâtiments de la Marine nationale (idempotent, rien n'est supprimé)."

    def handle(self, *args, **options):
        bilan = {"crees": 0, "existants": 0, "mis_a_jour": 0, "unites_reliees": 0}
        with transaction.atomic():
            types = {}
            for rang, code in enumerate(self._codes_de_types()):
                types[code], _ = TypeBatiment.objects.get_or_create(code=code, defaults={"libelle": code, "ordre": rang})
            for type_, nom, coque, trigramme, port in donnees.INVENTAIRE_2025:
                self._creer(bilan, types[type_], nom, coque, trigramme, port, ReferenceBatiment.Famille.MARINE)
            for type_, nom, coque, trigramme, port in donnees.GENDARMERIE_2025:
                self._creer(bilan, types[type_], nom, coque, trigramme, port, ReferenceBatiment.Famille.GENDARMERIE)
            for type_, nom, coque, trigramme, date_statut, commentaire, avec_equipage in donnees.ESSAIS_2025:
                self._creer(
                    bilan, types[type_], nom, coque, trigramme, "", ReferenceBatiment.Famille.MARINE,
                    statut=Statut.ESSAIS, statut_au=date_statut, commentaire=commentaire, avec_equipage=avec_equipage,
                )
            for nom, coque, statut, date_statut, source, commentaire in donnees.MISES_A_JOUR:
                self._mettre_a_jour(bilan, coque, statut, date_statut, source, commentaire)
            self._de_grasse(bilan, types.get("SNA"))
            self._relier_unites(bilan)
        self.stdout.write(
            f"Référentiel : {bilan['crees']} créé(s), {bilan['existants']} déjà présent(s), "
            f"{bilan['mis_a_jour']} mis à jour, {bilan['unites_reliees']} unité(s) Matrix reliée(s)."
        )

    @staticmethod
    def _codes_de_types():
        vus = []
        for ligne in (*donnees.INVENTAIRE_2025, *donnees.GENDARMERIE_2025, *donnees.ESSAIS_2025):
            if ligne[0] not in vus:
                vus.append(ligne[0])
        return vus

    @staticmethod
    def _creer(bilan, type_, nom, coque, trigramme, port, famille, statut=Statut.REFERENCE_2025, statut_au=None,
               commentaire="", avec_equipage=True):
        _, cree = ReferenceBatiment.objects.get_or_create(
            numero_coque=coque,
            defaults={
                "nom": nom, "trigramme": trigramme, "type_batiment": type_, "port_base": port, "famille": famille,
                "statut": statut, "statut_au": statut_au or (donnees.SOURCE_DATE if statut == Statut.REFERENCE_2025 else None),
                "avec_equipage": avec_equipage, "source_url": donnees.SOURCE_URL, "source_date": donnees.SOURCE_DATE,
                "commentaire": commentaire,
            },
        )
        bilan["crees" if cree else "existants"] += 1

    @staticmethod
    def _mettre_a_jour(bilan, coque, statut, date_statut, source, commentaire):
        reference = ReferenceBatiment.objects.filter(numero_coque=coque).first()
        # Une saisie manuelle déjà passée à un autre statut n'est jamais écrasée.
        if reference is None or reference.statut not in (Statut.REFERENCE_2025, Statut.ESSAIS):
            return
        reference.statut, reference.statut_au, reference.source_url, reference.commentaire = statut, date_statut, source, commentaire
        reference.save(update_fields=["statut", "statut_au", "source_url", "commentaire", "updated_at"])
        bilan["mis_a_jour"] += 1

    @staticmethod
    def _de_grasse(bilan, type_sna):
        entree = donnees.SNA_DE_GRASSE
        _, cree = ReferenceBatiment.objects.get_or_create(
            nom=entree["nom"], numero_coque="",
            defaults={"type_batiment": type_sna, "statut": entree["statut"], "statut_au": entree["statut_au"],
                      "source_url": entree["source_url"], "commentaire": entree["commentaire"]},
        )
        bilan["crees" if cree else "existants"] += 1

    @staticmethod
    def _relier_unites(bilan):
        for unite in Ship.objects.filter(reference_batiment__isnull=True):
            reference = ReferenceBatiment.objects.filter(nom__iexact=unite.name, unite__isnull=True).first()
            if reference is None:
                continue
            reference.unite = unite
            reference.save(update_fields=["unite", "updated_at"])
            champs = []
            if unite.type_batiment_id is None and reference.type_batiment_id:
                unite.type_batiment, champs = reference.type_batiment, [*champs, "type_batiment"]
            if not unite.numero_coque and reference.numero_coque:
                unite.numero_coque, champs = reference.numero_coque, [*champs, "numero_coque"]
            if not unite.trigramme and reference.trigramme:
                unite.trigramme, champs = reference.trigramme, [*champs, "trigramme"]
            if champs:
                unite.save(update_fields=champs)
            bilan["unites_reliees"] += 1
