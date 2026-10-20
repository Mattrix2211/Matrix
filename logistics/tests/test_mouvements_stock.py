"""Mouvements de stock : quantité calculée, sortie automatique, refus de stock négatif, droits, traçabilité, périmètre."""
import threading

from django.contrib.auth.models import User
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from accounts.models import AuditLog, UserProfile
from assets.models import Asset, AssetType
from logistics.models import CorrectiveTicket, MouvementStock, PartLineItem, PartRequest, StockPiece
from logistics.stock import MotifRequis, StockInsuffisant, enregistrer_mouvement, prelever
from org.models import Sector, Service, Ship


def _navire(code):
    navire = Ship.objects.create(name=f"Navire {code}", code=code)
    service = Service.objects.create(ship=navire, name=f"Service {code}")
    secteur = Sector.objects.create(service=service, name=f"Secteur {code}")
    return navire, service, secteur


def _marin(nom, role, secteur):
    user = User.objects.create_user(username=nom, password="pass")
    UserProfile.objects.filter(user=user).update(role=role, sector=secteur)
    return user


class BaseMouvements(TestCase):
    def setUp(self):
        self.navire, self.service, self.secteur = _navire("MV")
        self.piece = StockPiece.objects.create(
            reference="JNT-1", designation="Joint", quantite_minimale=2,
            ship=self.navire, service=self.service, sector=self.secteur,
        )
        self.chef = _marin("chef_mv", "CHEF_SECTION", self.secteur)
        self.equipier = _marin("equipier_mv", "EQUIPIER", self.secteur)
        asset = Asset.objects.create(
            asset_type=AssetType.objects.create(name="Pompe", category="Méca", sector=self.secteur),
            ship=self.navire, service=self.service, sector=self.secteur,
        )
        self.ticket = CorrectiveTicket.objects.create(asset=asset, description="Fuite")

    def recharger(self):
        self.piece.refresh_from_db()
        return self.piece


class CalculQuantiteTests(BaseMouvements):
    def test_quantite_egale_somme_des_mouvements(self):
        enregistrer_mouvement(self.chef, self.piece, MouvementStock.ENTREE, 10)
        enregistrer_mouvement(self.chef, self.piece, MouvementStock.SORTIE, 3)
        enregistrer_mouvement(self.chef, self.piece, MouvementStock.CORRECTION, -1, motif="Casse")
        piece = self.recharger()
        self.assertEqual(piece.quantite, 6)
        self.assertEqual(piece.quantite_calculee(), 6)
        self.assertEqual([m.solde_apres for m in piece.mouvements.all()], [10, 7, 6])

    def test_inventaire_calcule_l_ecart(self):
        enregistrer_mouvement(self.chef, self.piece, MouvementStock.ENTREE, 10)
        mouvement = enregistrer_mouvement(self.chef, self.piece, MouvementStock.INVENTAIRE, 7, motif="Comptage magasin")
        self.assertEqual(mouvement.quantite, -3)
        self.assertEqual(self.recharger().quantite, 7)

    def test_inventaire_et_correction_exigent_un_motif(self):
        for type_mouvement in (MouvementStock.INVENTAIRE, MouvementStock.CORRECTION):
            with self.assertRaises(MotifRequis):
                enregistrer_mouvement(self.chef, self.piece, type_mouvement, 1, motif="  ")
        self.assertFalse(self.piece.mouvements.exists())

    def test_mouvement_non_modifiable_ni_supprimable(self):
        mouvement = enregistrer_mouvement(self.chef, self.piece, MouvementStock.ENTREE, 4)
        mouvement.motif = "Réécrit"
        with self.assertRaises(Exception):
            mouvement.save()
        with self.assertRaises(Exception):
            mouvement.delete()


class StockNegatifTests(BaseMouvements):
    def test_sortie_superieure_au_stock_refusee(self):
        enregistrer_mouvement(self.chef, self.piece, MouvementStock.ENTREE, 2)
        with self.assertRaises(StockInsuffisant):
            prelever(self.chef, self.piece, 3, self.ticket)
        self.assertEqual(self.recharger().quantite, 2)
        self.assertEqual(self.piece.mouvements.count(), 1)

    def test_correction_negative_trop_forte_refusee(self):
        with self.assertRaises(StockInsuffisant):
            enregistrer_mouvement(self.chef, self.piece, MouvementStock.CORRECTION, -1, motif="Perte")
        self.assertEqual(self.recharger().quantite, 0)


class SortieAutomatiqueTests(BaseMouvements):
    def test_prelevement_cree_une_sortie_liee_au_ticket(self):
        enregistrer_mouvement(self.chef, self.piece, MouvementStock.ENTREE, 5)
        self.client.force_login(self.chef)
        reponse = self.client.post(reverse("ticket-stock-prelevement", args=[self.ticket.pk]), {"piece_id": self.piece.pk, "quantite": 2})
        self.assertEqual(reponse.status_code, 302)
        sortie = self.piece.mouvements.get(type=MouvementStock.SORTIE)
        self.assertEqual((sortie.quantite, sortie.solde_apres, sortie.ticket, sortie.auteur), (-2, 3, self.ticket, self.chef))
        self.assertEqual(self.recharger().quantite, 3)

    def _ligne(self, reference="JNT-1", qty=2):
        demande = PartRequest.objects.create(ticket=self.ticket, requested_by=self.chef)
        return PartLineItem.objects.create(part_request=demande, reference=reference, description="Joint", qty=qty, status="RECEIVED")

    def test_ligne_consommee_cree_une_sortie_une_seule_fois(self):
        enregistrer_mouvement(self.chef, self.piece, MouvementStock.ENTREE, 5)
        ligne = self._ligne()
        self.client.force_login(self.chef)
        url = reverse("part-line-status", args=[ligne.pk])
        self.client.post(url, {"status": "CONSUMED"})
        self.client.post(url, {"status": "RETURNED"})
        self.client.post(url, {"status": "CONSUMED"})
        sortie = self.piece.mouvements.get(type=MouvementStock.SORTIE)
        self.assertEqual((sortie.quantite, sortie.ligne_pieces, sortie.ticket), (-2, ligne, self.ticket))
        self.assertEqual(self.recharger().quantite, 3)

    def test_ligne_consommee_sans_stock_suffisant_ou_sans_piece_ne_sort_rien(self):
        enregistrer_mouvement(self.chef, self.piece, MouvementStock.ENTREE, 1)
        self.client.force_login(self.chef)
        trop = self._ligne(qty=4)
        inconnue = self._ligne(reference="ZZZ")
        for ligne in (trop, inconnue):
            reponse = self.client.post(reverse("part-line-status", args=[ligne.pk]), {"status": "CONSUMED"})
            self.assertEqual(reponse.status_code, 302)
            ligne.refresh_from_db()
            self.assertEqual(ligne.status, "CONSUMED")
        self.assertEqual(self.recharger().quantite, 1)
        self.assertEqual(self.piece.mouvements.count(), 1)


    def test_ligne_consommee_apres_prelevement_du_meme_ticket_ne_sort_pas_deux_fois(self):
        enregistrer_mouvement(self.chef, self.piece, MouvementStock.ENTREE, 5)
        prelever(self.chef, self.piece, 2, self.ticket)
        ligne = self._ligne()
        self.client.force_login(self.chef)
        reponse = self.client.post(reverse("part-line-status", args=[ligne.pk]), {"status": "CONSUMED"}, follow=True)
        self.assertContains(reponse, "aucune sortie en double")
        self.assertEqual(self.piece.mouvements.filter(type=MouvementStock.SORTIE).count(), 1)
        self.assertEqual(self.recharger().quantite, 3)

    def test_seuil_stock_releve_message_explicite_sans_sortie(self):
        from org.models import RoleThresholdConfig
        from matrix.core.role_thresholds import invalidate_cache
        RoleThresholdConfig.objects.create(ship=self.navire, thresholds={"stock_ecriture": "CHEF_SERVICE"})
        UserProfile.objects.filter(user=self.chef).update(ship=self.navire)
        invalidate_cache(self.navire.pk)
        self.addCleanup(invalidate_cache, self.navire.pk)
        enregistrer_mouvement(self.chef, self.piece, MouvementStock.ENTREE, 5)
        ligne = self._ligne()
        self.client.force_login(self.chef)
        reponse = self.client.post(reverse("part-line-status", args=[ligne.pk]), {"status": "CONSUMED"}, follow=True)
        self.assertContains(reponse, "gestion du stock est réservée")
        self.assertEqual(self.recharger().quantite, 5)


class SaisieManuelleTests(BaseMouvements):
    def url(self, piece=None):
        return reverse("stock-piece-mouvements", args=[(piece or self.piece).pk])

    def test_chef_saisit_une_entree_tracee(self):
        self.client.force_login(self.chef)
        self.client.post(self.url(), {"type": "ENTREE", "quantite": "8", "motif": "Livraison"})
        mouvement = self.piece.mouvements.get()
        self.assertEqual((mouvement.type, mouvement.quantite, mouvement.auteur, mouvement.motif), ("ENTREE", 8, self.chef, "Livraison"))
        self.assertEqual(self.recharger().quantite, 8)
        journal = AuditLog.objects.get(action="stock_mouvement")
        self.assertEqual(journal.actor, self.chef)
        self.assertIn("variation=+8", journal.details)

    def test_inventaire_sans_motif_refuse(self):
        self.client.force_login(self.chef)
        self.client.post(self.url(), {"type": "INVENTAIRE", "quantite": "5", "motif": ""})
        self.assertFalse(self.piece.mouvements.exists())

    def test_correction_negative_excessive_refusee_avec_message(self):
        self.client.force_login(self.chef)
        reponse = self.client.post(self.url(), {"type": "CORRECTION", "quantite": "-2", "motif": "Perte"}, follow=True)
        self.assertContains(reponse, "Stock insuffisant")
        self.assertFalse(self.piece.mouvements.exists())

    def test_quantites_invalides_refusees(self):
        self.client.force_login(self.chef)
        for type_mouvement, quantite in (("ENTREE", "0"), ("ENTREE", "-1"), ("CORRECTION", "0"), ("INVENTAIRE", "-1"), ("ENTREE", "x"), ("SORTIE", "1")):
            self.client.post(self.url(), {"type": type_mouvement, "quantite": quantite, "motif": "m"})
        self.assertFalse(self.piece.mouvements.exists())

    def test_equipier_peut_lire_mais_pas_ecrire(self):
        self.client.force_login(self.equipier)
        self.assertEqual(self.client.get(self.url()).status_code, 200)
        self.assertEqual(self.client.post(self.url(), {"type": "ENTREE", "quantite": "5"}).status_code, 403)
        self.assertFalse(self.piece.mouvements.exists())

    def test_historique_affiche_solde_auteur_et_lien_intervention(self):
        enregistrer_mouvement(self.chef, self.piece, MouvementStock.ENTREE, 5)
        prelever(self.chef, self.piece, 2, self.ticket)
        self.client.force_login(self.chef)
        reponse = self.client.get(self.url())
        self.assertContains(reponse, "voir l'intervention")
        self.assertContains(reponse, reverse("ticket-detail", args=[self.ticket.pk]))
        self.assertContains(reponse, "chef_mv")

    def test_perimetre_autre_navire_introuvable(self):
        _, _, autre_secteur = _navire("AU")
        etranger = _marin("chef_autre", "CHEF_SECTION", autre_secteur)
        self.client.force_login(etranger)
        self.assertEqual(self.client.get(self.url()).status_code, 404)
        self.assertEqual(self.client.post(self.url(), {"type": "ENTREE", "quantite": "5"}).status_code, 404)
        self.assertFalse(self.piece.mouvements.exists())

    def test_equipage_a_terre_ecriture_refusee(self):
        self.navire.double_equipage, self.navire.equipage_a_bord = True, "A"
        self.navire.save()
        UserProfile.objects.filter(user=self.chef).update(ship=self.navire, equipage="B")
        self.client.force_login(self.chef)
        self.assertEqual(self.client.get(self.url()).status_code, 200)
        self.assertEqual(self.client.post(self.url(), {"type": "ENTREE", "quantite": "5"}).status_code, 403)
        self.assertFalse(self.piece.mouvements.exists())


class CreationPieceTests(BaseMouvements):
    def test_creation_avec_quantite_cree_un_inventaire_initial(self):
        self.client.force_login(self.chef)
        self.client.post(reverse("stock-piece-list"), {
            "action": "create_piece", "reference": "NEW-1", "designation": "Neuf", "quantite": "6",
            "quantite_minimale": "2", "sector_id": self.secteur.pk,
        })
        piece = StockPiece.objects.get(reference="NEW-1")
        mouvement = piece.mouvements.get()
        self.assertEqual((mouvement.type, mouvement.quantite, mouvement.motif), ("INVENTAIRE", 6, "Inventaire initial"))
        self.assertEqual((piece.quantite, piece.quantite_calculee()), (6, 6))

    def test_modification_n_ecrase_pas_la_quantite(self):
        enregistrer_mouvement(self.chef, self.piece, MouvementStock.ENTREE, 4)
        self.client.force_login(self.chef)
        self.client.post(reverse("stock-piece-list"), {
            "action": "edit_piece", "pk": self.piece.pk, "reference": "JNT-1", "designation": "Joint bis",
            "quantite": "99", "quantite_minimale": "2", "sector_id": self.secteur.pk,
        })
        piece = self.recharger()
        self.assertEqual((piece.designation, piece.quantite), ("Joint bis", 4))

    def test_fiche_ouverte_avant_un_mouvement_ne_l_ecrase_pas(self):
        # Scénario D-08 : quantité 9, mouvement +5, puis enregistrement d'une fiche ouverte avant.
        enregistrer_mouvement(self.chef, self.piece, MouvementStock.ENTREE, 9)
        fiche_perimee = StockPiece.objects.get(pk=self.piece.pk)
        enregistrer_mouvement(self.chef, self.piece, MouvementStock.ENTREE, 5)
        self.client.force_login(self.chef)
        self.client.post(reverse("stock-piece-list"), {
            "action": "edit_piece", "pk": fiche_perimee.pk, "reference": "JNT-1", "designation": "Joint ter",
            "quantite": str(fiche_perimee.quantite), "quantite_minimale": "2", "sector_id": self.secteur.pk,
        })
        piece = self.recharger()
        self.assertEqual((piece.designation, piece.quantite), ("Joint ter", 14))
        self.assertEqual(piece.quantite, piece.quantite_calculee())

    def test_inventaire_apres_modification_de_fiche_garde_l_invariant(self):
        enregistrer_mouvement(self.chef, self.piece, MouvementStock.ENTREE, 9)
        self.client.force_login(self.chef)
        self.client.post(reverse("stock-piece-list"), {
            "action": "edit_piece", "pk": self.piece.pk, "reference": "JNT-1", "designation": "Joint",
            "quantite_minimale": "2", "sector_id": self.secteur.pk,
        })
        enregistrer_mouvement(self.chef, self.piece, MouvementStock.INVENTAIRE, 7, motif="Comptage")
        piece = self.recharger()
        self.assertEqual((piece.quantite, piece.quantite_calculee()), (7, 7))


class ConcurrenceStockTests(TransactionTestCase):
    """Vrais accès concurrents (deux connexions) : propre à PostgreSQL, SQLite verrouillant la base entière."""

    def test_mouvements_et_fiches_concurrents_gardent_l_invariant(self):
        if connection.vendor != "postgresql":
            self.skipTest("Concurrence réelle testée sur PostgreSQL seulement.")
        navire, service, secteur = _navire("CC")
        chef = _marin("chef_cc", "CHEF_SECTION", secteur)
        piece = StockPiece.objects.create(reference="CC-1", designation="Joint", ship=navire, service=service, sector=secteur)
        erreurs = []

        def mouvements():
            try:
                for _ in range(10):
                    enregistrer_mouvement(chef, StockPiece.objects.get(pk=piece.pk), MouvementStock.ENTREE, 1)
            except Exception as exc:  # remonté dans le thread principal
                erreurs.append(exc)
            finally:
                connection.close()

        def fiches():
            from django.test import Client
            try:
                client = Client()
                client.force_login(chef)
                for i in range(10):
                    client.post(reverse("stock-piece-list"), {
                        "action": "edit_piece", "pk": piece.pk, "reference": "CC-1", "designation": f"Joint {i}",
                        "quantite": "0", "quantite_minimale": "2", "sector_id": secteur.pk,
                    })
            except Exception as exc:
                erreurs.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=f) for f in (mouvements, mouvements, fiches, fiches)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(erreurs, [])
        piece.refresh_from_db()
        self.assertEqual((piece.quantite, piece.quantite_calculee()), (20, 20))


class MigrationInventaireInitialTests(TransactionTestCase):
    def test_migration_cree_un_mouvement_par_piece_et_est_reversible(self):
        executor = MigrationExecutor(connection)
        executor.migrate([("logistics", "0012_validation_fichiers_televerses")])
        anciennes = executor.loader.project_state([("logistics", "0012_validation_fichiers_televerses")]).apps
        Piece = anciennes.get_model("logistics", "StockPiece")
        navire, service, secteur = _navire("MIG")
        for ref, quantite in (("A", 5), ("B", 0)):
            Piece.objects.create(
                reference=ref, designation=ref, quantite=quantite, ship_id=navire.pk, service_id=service.pk, sector_id=secteur.pk,
            )

        executor = MigrationExecutor(connection)
        executor.migrate([("logistics", "0014_mouvements_stock_initiaux")])
        nouvelles = executor.loader.project_state([("logistics", "0014_mouvements_stock_initiaux")]).apps
        Mouvement = nouvelles.get_model("logistics", "MouvementStock")
        mouvement = Mouvement.objects.get()
        self.assertEqual((mouvement.piece.reference, mouvement.type, mouvement.quantite, mouvement.solde_apres), ("A", "INVENTAIRE", 5, 5))

        executor = MigrationExecutor(connection)
        executor.migrate([("logistics", "0013_mouvement_stock")])
        retour = executor.loader.project_state([("logistics", "0013_mouvement_stock")]).apps
        self.assertFalse(retour.get_model("logistics", "MouvementStock").objects.exists())
        self.assertEqual(retour.get_model("logistics", "StockPiece").objects.get(reference="A").quantite, 5)

        MigrationExecutor(connection).migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())
