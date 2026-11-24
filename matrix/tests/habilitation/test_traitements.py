"""Tâches planifiées exécutées pour de bon ; le cloisonnement par périmètre n'est éprouvé que pour l'alerte de stock (lot L29)."""
from matrix.celery import app
from django.conf import settings
from django.contrib.contenttypes.models import ContentType

from logistics.models import StockPiece
from notifications.models import Notification
from org.models import ModuleActivation

from .outils import MondeFictif


class TraitementsTests(MondeFictif):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        app.loader.import_default_modules()

    def test_chaque_tache_planifiee_s_execute_sans_erreur_sur_le_monde_fictif(self):
        for nom in sorted({e["task"] for e in settings.CELERY_BEAT_SCHEDULE.values()}):
            with self.subTest(nom):
                app.tasks[nom]()

    def _piece_en_rupture(self, service, secteur, navire, reference):
        return StockPiece.objects.create(reference=reference, designation="Filtre", quantite=0, quantite_minimale=2,
                                         ship=navire, service=service, sector=secteur)

    def _destinataires(self, piece):
        type_piece = ContentType.objects.get_for_model(StockPiece)
        return set(Notification.objects.filter(content_type=type_piece, object_id=str(piece.pk)).values_list("user__username", flat=True))

    def test_une_alerte_de_stock_ne_touche_que_le_perimetre_de_la_piece(self):
        from notifications.tasks import notify_low_stock

        piece = self._piece_en_rupture(self.service2, self.secteur2, self.navire, "F-SEC")
        notify_low_stock()
        destinataires = self._destinataires(piece)
        self.assertIn("chef_service_sec", destinataires)
        self.assertFalse(destinataires & {"chef_service_b", "equipier_abe", "equipier_b1"}, destinataires)

    def test_ecart_connu_un_module_desactive_declenche_encore_ses_notifications(self):
        """Écart A25 enregistré tel quel (lot L34) : la désactivation du module Logistique n'arrête pas la tâche planifiée."""
        from notifications.tasks import notify_low_stock

        ModuleActivation.objects.create(ship=self.navire, module="logistics", active=False)
        piece = self._piece_en_rupture(self.service2, self.secteur2, self.navire, "F-SEC-2")
        notify_low_stock()
        self.assertIn("chef_service_sec", self._destinataires(piece),
                      "Si ce test échoue, l'écart A25 est corrigé pour cette tâche : retirer la mention du registre.")
