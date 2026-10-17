"""Jeu de données de recette V1, ajouté à `seed_demo` (idempotent, additif, entièrement fictif).

Ne s'exécute qu'en développement (`DJANGO_DEBUG=1`) ou avec `MATRIX_RECETTE=1`.
Tous les comptes ont le mot de passe « pass » ; tous les titres créés portent le préfixe « [Recette] ».
"""
import os
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from absences.models import Absence
from accounts.models import Roles, TypeAbsence
from annonces import services as annonces_services
from annonces.models import Annonce
from assets.models import Installation, InstallationMaintenance, Location
from assets import fiche_maintenance
from demandes import services as demandes_services
from demandes.models import Demande
from documentation import services as documentation_services
from documentation.models import Document
from maintenance.models import MaintenanceOccurrence
from matrix.core.management.commands.seed_demo import Command as SeedDemo
from notifications.models import Notification, NotificationLevel
from org.models import Section, Sector, Service, Ship
from quarts.models import CreneauQuart, Quart
from taches import services as taches_services
from taches.models import Tache
from threads.models import Message, Thread
from training.models import (
    CandidatureFormation, ReferentFormation, TrainingCourse, TrainingRecord, TrainingSession,
)

PREFIXE = "[Recette]"


class Command(SeedDemo):
    help = "Ajoute le jeu de données de recette V1 à la démonstration (fictif, idempotent, additif)"

    def handle(self, *args, **options):
        if not (settings.DEBUG or os.environ.get("MATRIX_RECETTE") == "1"):
            raise CommandError("seed_recette est réservé au développement : définir DJANGO_DEBUG=1 ou MATRIX_RECETTE=1.")
        # La démonstration n'est (re)jouée que si elle manque : on ne touche jamais à ses objets.
        if not (Ship.objects.filter(code="BRE").exists() and User.objects.filter(username="equipier_a").exists()):
            call_command("seed_demo", stdout=self.stdout)
        self.comptes = []
        self.maintenant = timezone.now()
        self.aujourdhui = timezone.localdate()
        self._charger()
        self._comptes_recette()
        self._coma_recette()
        self._formations_recette()
        self._pompe_incendie()
        self._planning_et_absences()
        self._taches_recette()
        self._communications()
        self._autres_perimetres()
        self.stdout.write(self.style.SUCCESS("Données de recette prêtes (mot de passe « pass »). Comptes ajoutés :"))
        for ligne in self.comptes:
            self.stdout.write(ligne)

    # ---------- Outils ----------

    def _titre(self, texte):
        return f"{PREFIXE} {texte}"

    def _charger(self):
        """Retrouve les objets de démonstration utilisés (lecture seule)."""
        self.bre = Ship.objects.get(code="BRE")
        self.nor = Ship.objects.get(code="NOR")
        self.u = {u.username: u for u in User.objects.all()}
        self.moteurs = Sector.objects.get(service__ship=self.bre, name="Moteurs")
        self.propulsion = self.moteurs.service
        self.section_moteurs = Section.objects.get(sector=self.moteurs, name="Moteurs bâbord")
        self.pompiers = Sector.objects.get(service__ship=self.bre, name="Pompiers")
        self.section_pompiers = Section.objects.get(sector=self.pompiers, name="Sections incendie")
        self.permission, _ = TypeAbsence.objects.get_or_create(name="Permission")

    def _absence(self, marin, decalage, duree, chef):
        debut = self.aujourdhui + timedelta(days=decalage)
        marque = self._titre(f"absence de {marin.username}")
        if not Absence.objects.filter(marin=marin, motif=marque).exists():
            Absence.objects.create(
                marin=marin, type_absence=self.permission, date_debut=debut, date_fin=debut + timedelta(days=duree - 1),
                statut=Absence.STATUT_VALIDEE, motif=marque, created_by=chef)

    def _tache(self, chef, marin, titre, decalage, description="", **options):
        titre = self._titre(titre)
        tache = Tache.objects.filter(titre=titre).first()
        if tache is None:
            tache = taches_services.creer_tache(
                chef, marin, titre, self.aujourdhui + timedelta(days=decalage), description, **options)
        return tache

    def _notification(self, user, verbe, niveau=NotificationLevel.INFO):
        verbe = self._titre(verbe)
        Notification.objects.get_or_create(user=user, verb=verbe, defaults=dict(level=niveau))

    # ---------- Comptes ----------

    def _comptes_recette(self):
        u = self._utilisateur
        self.a3 = u("equipier_a3", Roles.EQUIPIER, "Julien", ship=self.bre, service=self.propulsion, sector=self.moteurs,
                    section=self.section_moteurs, equipage="A", grade="Quartier-maître", specialite="Mécanique")
        # Référent « pur » : ni fonction de chef, ni ChefDeListe.
        self.referent = u("referent_formation_a", Roles.EQUIPIER, "Solène", ship=self.bre, service=self.pompiers.service,
                          sector=self.pompiers, section=self.section_pompiers, equipage="A", grade="Second-maître",
                          specialite="Sécurité")
        self.u.update(equipier_a3=self.a3, referent_formation_a=self.referent)

    def _coma_recette(self):
        """COMA fictifs de l'équipage B (Bretagne) et de la Normandie, désignés par `fonction_coma` comme en démonstration.

        Volontairement sans titulaire : COMOPS de l'équipage B (service Opérations), pour tester un visa en attente.
        """
        u = self._utilisateur
        u("coma_comanav_b", Roles.ETAT_MAJOR, "Thibault", ship=self.bre, equipage="B", fonction_coma="COMANAV",
          grade="Capitaine de corvette")
        u("coma_comaeq_b", Roles.ETAT_MAJOR, "Margaux", ship=self.bre, equipage="B", fonction_coma="COMAEQ",
          grade="Lieutenant de vaisseau")
        # La Normandie n'a que Propulsion en démonstration : on y ajoute un service Sécurité dépendant du COMAEQ.
        Service.objects.get_or_create(ship=self.nor, name="Sécurité", defaults={"commandant_adjoint": "COMAEQ"})
        u("coma_comanav_nor", Roles.ETAT_MAJOR, "Olivier", ship=self.nor, fonction_coma="COMANAV", grade="Capitaine de corvette")
        u("coma_comaeq_nor", Roles.ETAT_MAJOR, "Pauline", ship=self.nor, fonction_coma="COMAEQ", grade="Lieutenant de vaisseau")
        self.u.update({nom: User.objects.get(username=nom) for nom in (
            "coma_comanav_b", "coma_comaeq_b", "coma_comanav_nor", "coma_comaeq_nor")})

    # ---------- Formations, qualifications et candidatures ----------

    def _formations_recette(self):
        chef = self.u["chef_secteur_a"]
        self.cours_pompes, _ = TrainingCourse.objects.get_or_create(title=self._titre("Entretien des pompes d'incendie"), defaults=dict(
            category="Mécanique", validity_days=1095, description="Formation fictive d'entretien des pompes du réseau incendie."))
        self.cours_reseau, _ = TrainingCourse.objects.get_or_create(title=self._titre("Conduite du réseau incendie"), defaults=dict(
            category="Sécurité", validity_days=730, description="Formation fictive de conduite du réseau incendie."))
        self.cours_hauteur, _ = TrainingCourse.objects.get_or_create(title=self._titre("Travaux en hauteur"), defaults=dict(
            category="Sécurité", validity_days=730, description="Formation fictive, hors du ressort du référent."))
        j = self.aujourdhui
        # Qualification utilisée par la maintenance (valide) et qualification qui arrive à échéance.
        TrainingRecord.objects.get_or_create(user=self.a3, course=self.cours_pompes, defaults=dict(
            completed_at=j - timedelta(days=400), expires_at=j + timedelta(days=695), validated_by=chef))
        TrainingRecord.objects.get_or_create(user=self.a3, course=self.cours_reseau, defaults=dict(
            completed_at=j - timedelta(days=710), expires_at=j + timedelta(days=20), validated_by=chef))
        ReferentFormation.objects.get_or_create(course=self.cours_reseau, ship=self.bre, user=self.referent)
        if not TrainingSession.objects.filter(course=self.cours_reseau).exists():
            TrainingSession.objects.create(course=self.cours_reseau, scheduled_at=self._jour(18, 8), capacite_max=4,
                                           location="Centre de formation", instructor=self.referent)
        # Deux candidatures déjà validées par la hiérarchie et le BRH : l'une dans le ressort du référent, l'autre non.
        for marin, cours in ((self.u["equipier_incendie_a"], self.cours_reseau), (self.u["equipier_a"], self.cours_hauteur)):
            if not CandidatureFormation.objects.filter(marin=marin, course=cours).exists():
                CandidatureFormation.objects.create(
                    course=cours, marin=marin, statut="TRANSMITTED", created_by=marin,
                    hierarchie_validee_par=self.u["chef_secteur_incendie_a"], date_validation_hierarchie=self.maintenant,
                    brh_validee_par=self.u["second_a"], date_validation_brh=self.maintenant)
        self._notification(self.referent, "Une candidature à « Conduite du réseau incendie » attend votre instruction.",
                           NotificationLevel.WARNING)

    # ---------- Maintenance trimestrielle de la pompe incendie ----------

    def _pompe_incendie(self):
        chef, chef_section = self.u["chef_secteur_a"], self.u["chef_section_a"]
        local = Location.objects.get(ship=self.bre, name="Local machine")
        pompe, _ = Installation.objects.get_or_create(ship=self.bre, designation=self._titre("Pompe d'incendie principale"), defaults=dict(
            service=self.propulsion, sector=self.moteurs, section=self.section_moteurs, location=local, critique=True,
            reference="REC-PI-1", marque="Fictive & Cie", gisement="Pont 2", local=local.name, created_by=chef))
        self.pompe = pompe
        trimestrielle = InstallationMaintenance.objects.filter(installation=pompe, title=self._titre("Contrôle trimestriel de la pompe incendie")).first()
        if trimestrielle is None:
            self._fiche(
                installation=pompe, periodicity="Trimestrielle", title=self._titre("Contrôle trimestriel de la pompe incendie"),
                description="Contrôle du débit, des garnitures et du clapet de la pompe d'incendie.", planned_duration_min=90,
                people_count=1, mode_declenchement="CALENDRIER", intervalle=3, unite_intervalle="M", created_by=chef)
            trimestrielle = InstallationMaintenance.objects.get(installation=pompe, title=self._titre("Contrôle trimestriel de la pompe incendie"))
            version = trimestrielle.version_validee
            version.qualification = self.cours_pompes
            version.save(update_fields=["qualification"])
        hebdomadaire = InstallationMaintenance.objects.filter(installation=pompe, title=self._titre("Essai hebdomadaire de la pompe incendie")).first()
        if hebdomadaire is None:
            self._fiche(
                installation=pompe, periodicity="Hebdomadaire", title=self._titre("Essai hebdomadaire de la pompe incendie"),
                planned_duration_min=20, mode_declenchement="CALENDRIER", intervalle=1, unite_intervalle="S", created_by=chef)
            hebdomadaire = InstallationMaintenance.objects.get(installation=pompe, title=self._titre("Essai hebdomadaire de la pompe incendie"))
        # Une intervention du jour et un essai de la veille dont le compte rendu reste à saisir.
        for fiche, decalage, statut, priorite in ((trimestrielle, 0, "ASSIGNED", 4), (hebdomadaire, -1, "ASSIGNED", 2)):
            if not MaintenanceOccurrence.objects.filter(installation_maintenance=fiche).exists():
                occ = MaintenanceOccurrence.objects.create(
                    installation_maintenance=fiche, scheduled_for=self.aujourdhui + timedelta(days=decalage), status=statut, priority=priorite)
                occ.assignees.set([self.a3])
        # Documentation publiée par le circuit normal (rédaction, validation du chef de service), liée à la pompe.
        titre_doc = self._titre("Procédure de contrôle de la pompe d'incendie")
        document = Document.objects.filter(titre=titre_doc).first()
        if document is None:
            document = documentation_services.creer_document(
                chef, titre_doc, f"sector:{self.moteurs.pk}",
                "1. Isoler la pompe.\n2. Relever le débit et la pression au refoulement.\n3. Contrôler les garnitures.\n"
                "4. Remettre en service et consigner les valeurs.",
                domaine="Sécurité incendie", origine=Document.ORIGINE_OFFICIELLE, reference_source="Fiche fictive de recette REC-PI-01")
            version = document.versions.get(numero=1)
            documentation_services.soumettre(chef, version)
            documentation_services.valider(self.u["chef_service_a"], version)
        documentation_services.lier(chef, document, pompe)
        fil, _ = Thread.objects.get_or_create(content_type=ContentType.objects.get_for_model(pompe), object_id=str(pompe.pk))
        if not fil.messages.exists():
            Message.objects.create(thread=fil, author=chef, body="Contrôle trimestriel à faire cette semaine, pensez à relever la pression au refoulement.")
            Message.objects.create(thread=fil, author=self.a3, body="Bien reçu, je prépare l'outillage et la procédure.")
        self._notification(self.a3, "Maintenance assignée : contrôle trimestriel de la pompe d'incendie principale.", NotificationLevel.WARNING)
        self._tache(chef_section, self.a3, "Préparer l'outillage du contrôle de la pompe incendie", 2,
                    "Rassembler les manomètres et les garnitures de rechange.")

    # ---------- Planning publié et absences ----------

    def _planning_et_absences(self):
        chef_service = self.u["chef_service_a"]
        debut = self.aujourdhui + timedelta(days=1)
        quart, cree = Quart.objects.get_or_create(
            nom=self._titre("Planning Propulsion — semaine prochaine"), service=self.propulsion, defaults=dict(
                date_debut=debut, date_fin=debut + timedelta(days=6), duree_creneau_heures=8, created_by=chef_service))
        if cree:
            equipe = [self.a3, self.u["equipier_a2"], self.a3, self.u["equipier_a"]]
            for i, marin in enumerate(equipe):
                jour = debut + timedelta(days=i)
                moment = timezone.make_aware(timezone.datetime(jour.year, jour.month, jour.day, 8))
                CreneauQuart.objects.create(quart=quart, poste="Machine avant", marin=marin, debut=moment, fin=moment + timedelta(hours=8))
            quart.publier(chef_service)
        # Absence de Julien recouvrant son quart publié du surlendemain : conflit de planning.
        self._absence(self.a3, 3, 1, self.u["chef_section_a"])
        self._absence(self.u["equipier_a2"], -1, 3, self.u["chef_section_a"])
        self._notification(self.a3, "Un de vos quarts coïncide avec une absence validée.", NotificationLevel.WARNING)

    # ---------- Tâches ----------

    def _taches_recette(self):
        chef_section, chef_secteur = self.u["chef_section_a"], self.u["chef_secteur_a"]
        self._tache(chef_section, self.a3, "Mettre à jour le cahier de quart machine", -3, "Reporter les relevés de la semaine.")
        self._tache(chef_section, self.u["equipier_a2"], "Contrôler les vannes d'isolement de la cale", 1)
        self._tache(chef_secteur, self.u["equipier_a"], "Remplacer la garniture de la pompe de cale", -2,
                    priorite=Tache.PRIORITE_URGENTE)
        # Équipage B : une tâche en retard et une absence.
        self._tache(self.u["chef_secteur_b"], self.u["marin_b"], "Relever les niveaux d'huile des lignes d'arbre", -1)
        self._absence(self.u["marin_b"], 2, 4, self.u["chef_secteur_b"])
        self._notification(self.u["marin_b"], "Tâche en retard : relever les niveaux d'huile des lignes d'arbre.", NotificationLevel.WARNING)

    # ---------- Communications ----------

    def _communications(self):
        titre = self._titre("Consigne : essai des pompes d'incendie vendredi")
        if not Annonce.objects.filter(titre=titre).exists():
            annonces_services.publier(
                self.u["cdt_a"], titre, "Essai de toutes les pompes d'incendie vendredi à 10 h. Accusez réception.",
                NotificationLevel.WARNING, f"ship:{self.bre.pk}", equipage="A", accuse_requis=True)
        tache = self._tache(self.u["chef_section_a"], self.a3, "Consigne de la pompe : relever le débit de référence", 1,
                            "Relever le débit de référence avant le contrôle trimestriel.")
        titre_demande = self._titre("Garniture de rechange introuvable pour la pompe incendie")
        if not Demande.objects.filter(titre=titre_demande).exists():
            demande = demandes_services.creer_demande(
                self.a3, tache, titre_demande, "Il manque une garniture de 40 mm au magasin machine.", self.u["chef_section_a"])
            demandes_services.repondre(demande, self.u["chef_section_a"], "Je fais la demande de pièce au magasin, je vous tiens informé.")

    # ---------- Autre service et autre bâtiment ----------

    def _autres_perimetres(self):
        # Énergie › Électricité (Bretagne).
        chef_elec, nora = self.u["chef_secteur_elec_a"], self.u["equipier_elec_a"]
        self._tache(chef_elec, nora, "Relever l'isolement des tableaux principaux", -4)
        self._tache(chef_elec, nora, "Vérifier le serrage des barres du tableau 2", 2)
        self._absence(nora, 5, 2, chef_elec)
        self._notification(nora, "Tâche en retard : relever l'isolement des tableaux principaux.", NotificationLevel.WARNING)
        # Normandie.
        chef_nor, sami = self.u["chef_secteur_nor"], self.u["equipier_nor"]
        self._tache(chef_nor, sami, "Contrôler le joint de la pompe d'eau de mer", -2)
        self._tache(chef_nor, sami, "Purger le compresseur d'air de lancement", 1)
        self._absence(sami, 1, 2, chef_nor)
        titre = self._titre("Consigne Normandie : visite de sécurité mardi")
        if not Annonce.objects.filter(titre=titre).exists():
            annonces_services.publier(
                self.u["cdt_nor"], titre, "Visite de sécurité mardi matin, locaux machine rangés.",
                NotificationLevel.INFO, f"ship:{self.nor.pk}", accuse_requis=True)
        self._notification(sami, "Tâche en retard : contrôler le joint de la pompe d'eau de mer.", NotificationLevel.WARNING)
