from django.core.management.base import BaseCommand, CommandError

from accounts.models import SpecialityChoice
from assets import catalogue_reprise


class Command(BaseCommand):
    help = (
        "Propose (par défaut, --dry-run) ou applique (--appliquer) la reprise des dossiers de matériel "
        "en catégories du catalogue. Rien n'est supprimé."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Rapport seul, sans écriture (défaut).")
        parser.add_argument("--appliquer", action="store_true", help="Crée les catégories et articles, en transaction.")
        parser.add_argument("--specialite", default="", help="Spécialité appliquée aux dossiers non listés dans le CSV.")
        parser.add_argument("--correspondance", default="", help="CSV `dossier;specialite` (chemin « Parent/Enfant »).")

    def handle(self, *args, **options):
        if options["appliquer"] and options["dry_run"]:
            raise CommandError("--appliquer et --dry-run s'excluent.")
        correspondance = catalogue_reprise.lire_correspondance(options["correspondance"]) if options["correspondance"] else {}
        connues = {s.name.lower() for s in SpecialityChoice.objects.all()}
        demandees = set(correspondance.values()) | ({options["specialite"]} if options["specialite"] else set())
        inconnues = sorted(n for n in demandees if n and n.lower() not in connues)
        if inconnues:
            raise CommandError("Spécialité(s) inconnue(s) : " + ", ".join(inconnues))

        rapport = catalogue_reprise.planifier(options["specialite"], correspondance)
        for ligne in rapport:
            self.stdout.write(
                f"{ligne['chemin']} -> {ligne['specialite'] or 'À qualifier'} : "
                f"{ligne['nb_materiels']} matériel(s), {len(ligne['articles'])} article(s) proposé(s)"
                + (f", {ligne['sans_designation']} sans désignation (catégorie seule)" if ligne["sans_designation"] else "")
            )
        a_qualifier = [ligne for ligne in rapport if not ligne["specialite"]]
        if a_qualifier:
            self.stdout.write(f"À qualifier ({len(a_qualifier)} dossier(s)) : "
                              "indiquez --specialite ou --correspondance.")
        if not options["appliquer"]:
            self.stdout.write("Simulation : rien n'a été écrit.")
            return
        if len(a_qualifier) == len(rapport):
            self.stdout.write("Aucun dossier qualifié : rien n'a été écrit.")
            return
        bilan = catalogue_reprise.appliquer(rapport)
        self.stdout.write(self.style.SUCCESS(
            f"Reprise appliquée : {bilan['categories']} catégorie(s), {bilan['articles']} article(s) créés, "
            f"{bilan['rattaches']} matériel(s) rattaché(s)."))
