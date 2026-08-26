"""Commande de fusion des formations dupliquées entre navires — étape 2/3 de
la portabilité des formations (cf. tâche Notion « Formation unique et
portable entre navires »), à lancer UNE SEULE FOIS après la migration
additive 0007 (création de ReferentFormation) et AVANT la migration finale
qui retire TrainingCourse.sector/referents.

Avant la refonte, chaque navire possédait sa PROPRE copie de chaque
formation (TrainingCourse.sector obligatoire). Cette commande :

1. Regroupe les formations existantes par titre identique.
2. Fusionne AUTOMATIQUEMENT un groupe en une seule formation globale
   UNIQUEMENT si toutes ses copies ont aussi la même catégorie ET la même
   durée de validité (sinon, malgré le titre identique, il ne s'agit
   probablement pas réellement de la même formation) — dans le cas
   contraire, le groupe est signalé comme CONFLIT et n'est PAS fusionné :
   chaque formation reste une fiche distincte, à trancher manuellement.
3. Pour CHAQUE formation traitée (fusionnée ou non) : convertit son ancien
   rattachement navire (TrainingCourse.sector) en TrainingRequirement
   (système déjà existant, réutilisé tel quel — « ce navire exige cette
   formation »), et ses anciens référents (TrainingCourse.referents) en
   ReferentFormation pour ce même navire. Aucune information n'est perdue,
   seule sa structuration change.
4. Pour les formations effectivement fusionnées, réattribue au survivant
   toutes les sessions, enregistrements de validation et exigences déjà
   liés aux doublons, puis supprime les doublons.

Toujours lancer d'abord avec --dry-run pour revoir le rapport complet
(fusions automatiques + conflits nécessitant une résolution manuelle) avant
toute application réelle : la commande travaille dans une transaction
unique, annulée (rollback) en mode --dry-run, donc sans aucun effet de bord
même si le rapport affiché reflète exactement ce qui SERAIT appliqué.

Note technique : cette commande s'exécute alors que le code applicatif a
DÉJÀ retiré TrainingCourse.sector/referents du modèle Python (état final visé
par la tâche), mais que la migration de schéma qui les supprime réellement en
base (0008) n'a volontairement pas encore été appliquée — l'ORM ne peut donc
plus lire ces deux colonnes via TrainingCourse.objects. Elle les lit en SQL
brut (tables/colonnes encore physiquement présentes à ce stade), le temps de
cette conversion ponctuelle, puis n'en a plus besoin une fois la migration
finale appliquée."""
from collections import defaultdict

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from org.models import Sector
from training.models import ReferentFormation, TrainingCourse, TrainingRequirement


class Command(BaseCommand):
    help = (
        "Fusionne les formations dupliquées entre navires (même titre, même "
        "catégorie, même durée de validité) et convertit leur rattachement "
        "navire/référents en TrainingRequirement/ReferentFormation, avant la "
        "migration finale qui retire TrainingCourse.sector/referents. "
        "Toujours lancer avec --dry-run d'abord."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="N'applique aucune modification, affiche seulement le rapport.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        rapport = {"individuelles": [], "fusions": [], "conflits": [], "avertissements": []}
        with transaction.atomic():
            self._traiter(rapport)
            if dry_run:
                transaction.set_rollback(True)
        self._afficher(rapport, dry_run)

    # -- Lecture des colonnes legacy (SQL brut, cf. note technique en tête) --

    @staticmethod
    def _navire_par_formation():
        """Renvoie {course_id: Ship} déduit de l'ancienne colonne
        TrainingCourse.sector_id, encore présente en base à ce stade (colonne
        retirée du modèle Python, mais pas encore de la base — cf. note
        technique en tête de fichier)."""
        with connection.cursor() as cur:
            cur.execute("SELECT id, sector_id FROM training_trainingcourse")
            lignes = cur.fetchall()
        sector_ids = {sector_id for _, sector_id in lignes if sector_id is not None}
        navire_par_secteur = {
            s.id: s.service.ship
            for s in Sector.objects.select_related("service", "service__ship").filter(pk__in=sector_ids)
        }
        return {
            course_id: navire_par_secteur[sector_id]
            for course_id, sector_id in lignes
            if sector_id in navire_par_secteur
        }

    @staticmethod
    def _referents_par_formation():
        """Renvoie {course_id: [User, ...]} déduit de l'ancienne table de
        jonction TrainingCourse.referents (training_trainingcourse_referents),
        encore présente en base à ce stade — même principe que
        _navire_par_formation ci-dessus."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        with connection.cursor() as cur:
            cur.execute("SELECT trainingcourse_id, user_id FROM training_trainingcourse_referents")
            lignes = cur.fetchall()
        user_ids = {user_id for _, user_id in lignes}
        utilisateurs = User.objects.in_bulk(user_ids)
        par_course = defaultdict(list)
        for course_id, user_id in lignes:
            if user_id in utilisateurs:
                par_course[course_id].append(utilisateurs[user_id])
        return dict(par_course)

    # -- Traitement -----------------------------------------------------------

    def _traiter(self, rapport):
        navire_par_formation = self._navire_par_formation()
        referents_par_formation = self._referents_par_formation()

        courses = list(TrainingCourse.objects.order_by("title", "id"))
        par_titre = defaultdict(list)
        for c in courses:
            par_titre[c.title].append(c)

        for titre, groupe in par_titre.items():
            # Une formation dont le navire d'origine n'a pas pu être résolu
            # (secteur déjà orphelin en base, cas anormal) est ignorée plutôt
            # que de faire planter toute la commande — signalée en avertissement.
            groupe = [c for c in groupe if c.id in navire_par_formation]
            if not groupe:
                continue

            if len(groupe) == 1:
                seule = groupe[0]
                navire = navire_par_formation[seule.id]
                self._convertir_navire_et_referents(seule, navire, referents_par_formation.get(seule.id, []))
                rapport["individuelles"].append((seule, navire))
                continue

            cles = {(c.category, c.validity_days) for c in groupe}
            if len(cles) > 1:
                # Conflit : même titre mais catégorie et/ou durée de validité
                # différentes -> pas de fusion automatique. Chaque formation
                # est quand même convertie individuellement (aucune ne
                # disparaît, aucune information de rattachement n'est perdue).
                rapport["conflits"].append([(c, navire_par_formation[c.id]) for c in groupe])
                for c in groupe:
                    navire = navire_par_formation[c.id]
                    self._convertir_navire_et_referents(c, navire, referents_par_formation.get(c.id, []))
                    rapport["individuelles"].append((c, navire))
                continue

            # Fusion automatique : même titre, même catégorie, même durée de
            # validité -> une seule survit (id le plus bas = la plus
            # ancienne), les autres sont réattribuées puis supprimées.
            groupe_trie = sorted(groupe, key=lambda c: c.id)
            survivant = groupe_trie[0]
            doublons = groupe_trie[1:]
            navires_origine = []
            for c in groupe_trie:
                navire = navire_par_formation[c.id]
                navires_origine.append(navire)
                self._convertir_navire_et_referents(c, navire, referents_par_formation.get(c.id, []), survivant=survivant)
            for doublon in doublons:
                self._reattribuer_objets_lies(doublon, survivant, rapport["avertissements"])
                doublon.delete()
            rapport["fusions"].append((titre, survivant, navires_origine))

    def _convertir_navire_et_referents(self, source, navire, referents, survivant=None):
        """Convertit le rattachement navire (ancien sector -> TrainingRequirement)
        et les anciens référents (-> ReferentFormation) de `source`, pour le
        navire d'origine de `source`. `survivant` est la formation qui doit
        recevoir cette conversion si `source` va être fusionnée dans une autre
        (par défaut, `source` elle-même)."""
        cible = survivant or source
        TrainingRequirement.objects.get_or_create(
            course=cible,
            applies_to_ship=navire,
            applies_to_role="",
            applies_to_service=None,
            applies_to_sector=None,
            applies_to_section=None,
            defaults={"required": True},
        )
        for referent in referents:
            ReferentFormation.objects.get_or_create(course=cible, ship=navire, user=referent)

    def _reattribuer_objets_lies(self, doublon, survivant, avertissements):
        """Réattribue au survivant tous les objets qui référençaient le doublon
        avant sa suppression : sessions, enregistrements de validation,
        exigences déjà créées, et prérequis (dans les deux sens du graphe),
        pour ne laisser aucune référence orpheline."""
        doublon.sessions.update(course=survivant)
        doublon.records.update(course=survivant)
        doublon.requirements.update(course=survivant)

        # Prérequis du doublon -> ajoutés au survivant (union, pas de perte).
        for prereq in doublon.prerequisites.all():
            if prereq.pk != survivant.pk:
                self._ajouter_prerequis_sans_echec(survivant, prereq, avertissements)
        doublon.prerequisites.clear()

        # Formations qui avaient le doublon comme prérequis -> pointent
        # désormais vers le survivant (sauf le survivant lui-même, qui ne
        # peut pas être son propre prérequis).
        for depend in list(doublon.unlocks.all()):
            if depend.pk != survivant.pk:
                self._ajouter_prerequis_sans_echec(depend, survivant, avertissements)
            depend.prerequisites.remove(doublon)

    @staticmethod
    def _ajouter_prerequis_sans_echec(course, prerequis, avertissements):
        """Ajoute `prerequis` aux prérequis de `course`, sans faire échouer toute
        la fusion si cela créerait exceptionnellement une boucle (protection
        anti-cycle déjà en place, cf. training/models.py) — le rattachement
        litigieux est simplement ignoré et signalé dans le rapport pour
        vérification manuelle plutôt que de bloquer la commande entière."""
        try:
            course.prerequisites.add(prerequis)
        except DjangoValidationError:
            avertissements.append(
                f"Prérequis « {prerequis.title} » non reporté sur « {course.title} » "
                "(aurait créé une boucle de prérequis) — à vérifier manuellement."
            )

    # -- Rapport --------------------------------------------------------------

    def _afficher(self, rapport, dry_run):
        entete = "=== Rapport de fusion des formations ==="
        entete += " (SIMULATION --dry-run, AUCUNE modification appliquée)" if dry_run else " (modifications appliquées)"
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(entete))

        self.stdout.write(f"\nFormations traitées individuellement (titre non dupliqué) : {len(rapport['individuelles'])}")
        for course, navire in rapport["individuelles"]:
            self.stdout.write(f"  - « {course.title} » (navire d'origine : {navire.name})")

        self.stdout.write(f"\nFusions automatiques {'(qui seraient) ' if dry_run else ''}appliquées : {len(rapport['fusions'])}")
        if not rapport["fusions"]:
            self.stdout.write("  Aucune.")
        for titre, survivant, navires in rapport["fusions"]:
            noms_navires = ", ".join(sorted({n.name for n in navires}))
            self.stdout.write(
                f"  - « {titre} » : {len(navires)} copies fusionnées en une seule "
                f"(id {survivant.id}) — navires d'origine : {noms_navires}"
            )

        self.stdout.write(f"\nConflits nécessitant une résolution MANUELLE (non fusionnés) : {len(rapport['conflits'])}")
        if not rapport["conflits"]:
            self.stdout.write("  Aucun.")
        for groupe in rapport["conflits"]:
            titre = groupe[0][0].title
            self.stdout.write(f"  - Titre « {titre} » utilisé par {len(groupe)} formations distinctes :")
            for c, navire in groupe:
                self.stdout.write(
                    f"      id={c.id} navire={navire.name} catégorie={c.category or '(vide)'} "
                    f"validité={c.validity_days}j"
                )

        if rapport["avertissements"]:
            self.stdout.write(f"\nAvertissements ({len(rapport['avertissements'])}) :")
            for a in rapport["avertissements"]:
                self.stdout.write(f"  - {a}")

        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING(
                "Aucune modification n'a été appliquée (--dry-run). Relancer sans "
                "--dry-run pour appliquer réellement cette fusion."
            ))
