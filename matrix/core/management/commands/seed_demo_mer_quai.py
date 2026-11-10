"""Scénarios de recette mer/quai sur les unités fictives de seed_demo (idempotent, données fictives)."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import Roles, ServiceFunctionChoice
from matrix.core.instance_demo import exiger_base_demo, mot_de_passe_commun
from org.models import Sector, Ship
from quarts.activation import publier_a_titre_previsionnel
from quarts.alertes_activation import traiter_echeances
from quarts.models import ChefDeListe, CreneauServiceGarde, ServiceGarde


class Command(BaseCommand):
    help = "Ajoute les listes prévisionnelles, l'alerte en retard et la désignation historique de la démonstration mer/quai."

    def _liste_previsionnelle(self, ship, nom, prise_effet, jours, marins, chef, publicateur):
        secteur = Sector.objects.get(service__ship=ship, name="Moteurs")  # périmètre du chef de liste désigné
        if ServiceGarde.objects.filter(sector=secteur, nom=nom).exists():
            return
        fonction = ServiceFunctionChoice.objects.get_or_create(name="Fraction de service à quai")[0]
        debut = (timezone.now() + timedelta(days=jours)).replace(hour=8, minute=0, second=0, microsecond=0)
        liste = ServiceGarde.objects.create(
            nom=nom, sector=secteur, date_debut=debut.date(), date_fin=debut.date(), type_service="Service à quai",
            duree_creneau_heures=24, fonction=fonction, created_by=chef)
        for poste, marin in zip(("Officier de garde (OG)", "Gradé de coupée 1", "Gradé mécanicien"), marins):
            CreneauServiceGarde.objects.create(service_garde=liste, poste=poste, marin=marin, debut=debut, fin=debut + timedelta(hours=24))
        liste.proposer(chef)
        publier_a_titre_previsionnel(publicateur, liste, prise_effet)

    def handle(self, *args, **options):
        exiger_base_demo("seed_demo_mer_quai")
        maintenant = timezone.now()
        try:
            chevallier = Ship.objects.get(name="Jacques Chevallier")
            benebig = Ship.objects.get(name="Auguste Bénébig")
        except Ship.DoesNotExist as exc:
            raise CommandError("Lancez d'abord seed_demo (unités fictives absentes).") from exc
        u = lambda nom: User.objects.get(username=nom)  # noqa: E731
        # Bénébig (à quai) : une liste à activer bientôt (confirmation anticipée), une en retard (alerte et escalade).
        marins = [u(f"marin_abe_{n}") for n in (1, 2, 3)]
        self._liste_previsionnelle(benebig, "Permanence prévisionnelle — Bénébig (activation anticipée)", maintenant + timedelta(hours=4), 3,
                                   marins, u("chef_liste_abe"), u("cdt_abe"))
        self._liste_previsionnelle(benebig, "Permanence en retard — Bénébig", maintenant - timedelta(minutes=40), 5,
                                   marins, u("chef_liste_abe"), u("cdt_abe"))
        # Chevallier (à la mer) : liste prête, activable seulement après l'accostage déclaré par le COMAEQ ou le commandant.
        self._liste_previsionnelle(chevallier, "Permanence prévisionnelle — Chevallier (après accostage)", maintenant + timedelta(hours=2), 2,
                                   [u(f"marin_jch_{n}") for n in (1, 2, 3)], u("chef_liste_jch"), u("cdt_jch"))
        # Désignation historique sans type : aucun droit tant que le commandant ne l'a pas qualifiée.
        secteur = Sector.objects.get(service__ship=benebig, name="Moteurs")
        historique, cree = User.objects.get_or_create(username="historique_abe", defaults={"first_name": "Yann", "last_name": "Historique"})
        if cree:
            historique.set_password(mot_de_passe_commun())
            historique.save()
        profil = historique.profile
        profil.role, profil.ship, profil.service, profil.sector = Roles.EQUIPIER, benebig, secteur.service, secteur
        profil.save()
        ChefDeListe.objects.get_or_create(user=historique, sector=secteur, ship=None, service=None, section=None, type_liste="")
        traiter_echeances()
        self.stdout.write("Scénarios mer/quai prêts (Bénébig, Chevallier).")
