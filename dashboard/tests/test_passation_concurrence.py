"""Partage simultané de la même information (double clic) : un seul partage actif par émetteur et par cible.

Scénario exécuté sur PostgreSQL 16 seulement (verrou de ligne de la synthèse) ; SQLite, réservé au développement, verrouille toute la
base en écriture : ce scénario n'y est pas validé et ne doit pas être présenté comme tel."""
import threading
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase

from accounts.models import UserProfile
from dashboard.passation import contenu_passation
from dashboard.passation_partage import partager, revoquer
from dashboard.passation_perimetre import contenu_visible
from org.models import PartagePassation, ParametresPassation, Section, Sector, Service, Ship, SynthesePassation
from taches.models import Tache

User = get_user_model()


@skipUnless(connection.vendor == "postgresql", "scénario validé sur PostgreSQL seulement")
class PartageConcurrentTests(TransactionTestCase):
    def test_six_partages_simultanes_laissent_un_seul_partage_actif_que_la_revocation_retire(self):
        ParametresPassation.objects.create(active=True)
        navire = Ship.objects.create(name="Bretagne", code="BRE", double_equipage=True, equipage_a_bord="A")
        service = Service.objects.create(ship=navire, name="Énergie")
        secteur = Sector.objects.create(service=service, name="Tableaux")
        section = Section.objects.create(sector=secteur, name="Tab-1")
        chef = User.objects.create_user("chef", password="x")
        marin = User.objects.create_user("marin", password="x")
        dest = User.objects.create_user("dest", password="x")
        UserProfile.objects.filter(user=chef).update(role="CHEF_SECTION", ship=navire, section=section)
        UserProfile.objects.filter(user=marin).update(role="EQUIPIER", ship=navire, section=section)
        UserProfile.objects.filter(user=dest).update(role="EQUIPIER", ship=navire, service=service)
        chef, marin, dest = (User.objects.get(pk=u.pk) for u in (chef, marin, dest))
        Tache.objects.create(titre="TACHE-CONC", assigne=marin, created_by=chef, statut="A_FAIRE")
        cdt = User.objects.create_user("cdt", password="x")
        UserProfile.objects.filter(user=cdt).update(role="COMMANDANT", ship=navire)
        cdt = User.objects.get(pk=cdt.pk)
        synthese = SynthesePassation.objects.create(ship=navire, equipage_montant="A", contenu=contenu_passation(cdt, navire))
        cle = next(l["cle"] for b in synthese.contenu["blocs"] for g in b["groupes"] for l in g["lignes"])
        erreurs = []

        def clic():
            try:
                partager(chef, synthese, cle, "SERVICE", service.pk)
            except Exception as exc:  # noqa: BLE001
                erreurs.append(exc)
            finally:
                connection.close()

        fils = [threading.Thread(target=clic) for _ in range(6)]
        [f.start() for f in fils]
        [f.join() for f in fils]
        self.assertEqual(erreurs, [])
        self.assertEqual(PartagePassation.objects.filter(revoque_le__isnull=True).count(), 1)
        self.assertIn("TACHE-CONC", {l["titre"] for b in contenu_visible(dest, synthese)["blocs"] for g in b["groupes"] for l in g["lignes"]})
        revoquer(chef, PartagePassation.objects.get())
        self.assertEqual(sum(b["total"] for b in contenu_visible(dest, synthese)["blocs"]), 0)
