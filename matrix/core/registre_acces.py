"""Registre déclaratif des protections attendues par point d'entrée (lot L29).

Chaque point d'entrée de `points_entree.inventaire()` doit être couvert par une règle (la première qui correspond).
Le registre dit quels contrôles sont attendus ; il ne prouve rien par lui-même : la preuve est l'exécution des accès
(`matrix/tests/habilitation/`). Un écart connu nomme le lot qui le corrige : tant qu'il existe, un test d'exécution
l'enregistre tel quel, et il échoue le jour où l'écart disparaît pour obliger à retirer la mention.
"""
import re
from dataclasses import dataclass

from .habilitation import NOMS_FACTEURS

PUBLIC, AUTHENTIFIE, ADMINISTRATION, TRAITEMENT = "public", "authentifie", "administration", "traitement"
# Contrôles hors socle commun : bornage des listes, seuil de rôle d'une action, propriétaire d'un objet, droit d'admin Django.
CONTROLES_PROPRES = (
    "queryset_perimetre", "seuil_role", "proprietaire_objet", "droit_admin_django", "perimetre_batiment", "middleware_equipage_a_terre",
)
VOCABULAIRE = frozenset(NOMS_FACTEURS) | frozenset(CONTROLES_PROPRES)

ECART_A25 = "A25 : le module désactivé reste actif par ce point d'entrée → L34"
ECART_L32 = "ARB-06 : écriture non bornée au périmètre dans ce module → L32"


@dataclass(frozen=True)
class Regle:
    identifiant: str
    motif: str  # expression régulière appliquée à la clé du point d'entrée
    classe: str
    controles: tuple = ()
    module: str = None
    lecture_sensible: bool = False
    ecarts: tuple = ()
    justification: str = ""
    couverture: tuple = ()  # suites de tests déjà en place qui protègent ce domaine

    def correspond(self, cle):
        return re.search(self.motif, cle) is not None


def _r(identifiant, motif, classe=AUTHENTIFIE, controles=("authentifie",), **kw):
    return Regle(identifiant, motif, classe, tuple(controles), **kw)


_QUERYSET = ("authentifie", "queryset_perimetre")
_ECRITURE = ("authentifie", "queryset_perimetre", "seuil_role", "niveau_sur_service")

REGLES = (
    _r("PUB-CONNEXION", r"^(accounts/login/|login/|service-worker\.js)$", PUBLIC, (),
       justification="Connexion et script du service worker : nécessaires avant toute authentification."),
    _r("PUB-REINITIALISATION", r"^reinitialisation/$", PUBLIC, (),
       justification="Le titulaire sans accès définit son mot de passe avec ses codes à usage unique : essais limités par demande, "
                     "message d'erreur unique, aucune authentification par le code (AC-16)."),
    _r("WEB-DECONNEXION", r"^logout/$", justification="Déconnexion : sans effet pour un visiteur non connecté."),
    _r("WEB-MEDIA", r"^media/", controles=("authentifie", "proprietaire_objet", "perimetre_batiment"), lecture_sensible=True,
       couverture=("matrix.tests.test_etancheite_equipage_peripherie", "matrix.tests.test_etancheite_equipage_vues")),
    _r("WEB-PASSATION", r"^dashboard/passation/", controles=(*_QUERYSET, "proprietaire_objet"), lecture_sensible=True,
       couverture=("dashboard.tests.test_passation_cloisonnement",),
       justification="Le contenu figé porte la portée de chaque ligne ; le serveur ne rend que le périmètre de l'utilisateur et les "
                     "lignes qui lui sont partagées (ARB-02, AC-03). Écriture limitée au partage et à sa révocation."),
    _r("WEB-TABLEAUX", r"^dashboard/", controles=_QUERYSET, lecture_sensible=True,
       ecarts=("A25 : l'accueil et les tableaux affichent des données d'un module désactivé → L34",),
       couverture=("matrix.tests.test_etancheite_equipage_vues",)),
    _r("WEB-ECHANGES", r"^quarts/echanges/", controles=("authentifie", "queryset_perimetre", "seuil_role"), module="quarts",
       ecarts=("A2 : la validation revient à qui gère la liste, non au COMAEQ → L10",)),
    _r("WEB-FEUILLE-SERVICE", r"^quarts/feuille-service/", controles=("authentifie", "middleware_equipage_a_terre", "proprietaire_objet"),
       module="quarts", lecture_sensible=True,
       couverture=("quarts.tests.test_feuille_service_circuit_bsc", "matrix.tests.test_securite_ecritures")),
    _r("WEB-QUARTS", r"^quarts/", controles=_ECRITURE, module="quarts",
       ecarts=("A3, A4 : seuil de publication abaissable par bâtiment ; droits du commandant en second différents entre écran et API → L08",),
       couverture=("matrix.tests.test_securite_terre_second", "matrix.tests.test_etancheite_equipage_vues")),
    _r("WEB-ABSENCES", r"^absences/", controles=_QUERYSET, module="absences", lecture_sensible=True,
       ecarts=("ARB-06 : périmètre de lecture des absences et protection du motif à poser avant tout affichage du motif (non affiché aujourd'hui) → L32",)),
    _r("WEB-TACHES", r"^taches/", controles=_ECRITURE, module="taches", lecture_sensible=True,
       ecarts=(ECART_L32,)),
    _r("WEB-FORMATIONS", r"^formations/", controles=_ECRITURE, module="training", ecarts=(ECART_L32,)),
    _r("WEB-DOCUMENTATION", r"^documentation/", controles=_ECRITURE, module="documentation", ecarts=(ECART_L32,)),
    _r("WEB-RETEX", r"^retex/", controles=_ECRITURE, module="retex", ecarts=(ECART_L32,)),
    _r("WEB-DEMANDES", r"^demandes/", controles=_QUERYSET, module="demandes"),
    _r("WEB-ANNONCES", r"^annonces/", controles=_QUERYSET, module="annonces"),
    _r("WEB-PROGRAMME", r"^programme/", controles=_QUERYSET, module="programme"),
    _r("WEB-POSTES", r"^postes/", controles=_QUERYSET, module="postes"),
    _r("WEB-MAINTENANCE", r"^maintenance/", controles=_ECRITURE, module="maintenance", lecture_sensible=True,
       couverture=("matrix.tests.test_ecriture_commandants_adjoints", "maintenance.tests.test_web_scope_leak")),
    _r("WEB-LOGISTIQUE", r"^logistics/", controles=_ECRITURE, module="logistics", lecture_sensible=True,
       couverture=("matrix.tests.test_ecriture_commandants_adjoints", "logistics.tests.test_web_scope_leak")),
    _r("WEB-MATERIEL", r"^(assets|installations|catalogue|fiches|scan)/", controles=_ECRITURE, module="assets",
       lecture_sensible=True, couverture=("matrix.tests.test_ecriture_commandants_adjoints",)),
    _r("WEB-RAPPORTS", r"^rapports/", controles=_QUERYSET, module="reports", lecture_sensible=True),
    _r("WEB-CALENDRIER", r"^calendar/", controles=("authentifie", "queryset_perimetre", "niveau_sur_service"),
       lecture_sensible=True, ecarts=("A25 : le calendrier affiche des événements d'un module désactivé → L34",), couverture=("calendar_app.tests.test_calendar_event_move_perimetre",
                                          "calendar_app.tests.test_popover_permissions")),
    _r("WEB-COMPTES", r"^(users/|accounts/password_change/)", controles=("authentifie", "seuil_role", "queryset_perimetre"),
       lecture_sensible=True, couverture=("accounts.tests.test_scope_leak_users_web", "accounts.tests.test_directory_permissions")),
    _r("WEB-REGLAGES", r"^parametre/", controles=("authentifie", "seuil_role", "middleware_equipage_a_terre"), lecture_sensible=True),
    _r("WEB-PERSONNEL", r"^(notifications/|brouillons/|session/|styleguide/|search/|$)", controles=_QUERYSET, lecture_sensible=True,
       couverture=("matrix.tests.test_global_search",)),
    _r("API-COMPTES", r"^api/accounts/", controles=("authentifie", "seuil_role", "queryset_perimetre"), lecture_sensible=True,
       couverture=("accounts.tests.test_scope_leak_users_api", "accounts.tests.test_scope_leak_userprofile_api")),
    _r("API-ORG", r"^api/org/", controles=("authentifie", "seuil_role", "queryset_perimetre"), lecture_sensible=True,
       couverture=("org.tests.test_scope_navire",)),
    _r("API-MATERIEL", r"^api/assets/", controles=_ECRITURE, module="assets", lecture_sensible=True,
       ecarts=(ECART_A25,), couverture=("assets.tests.test_scope_leak",)),
    _r("API-MAINTENANCE", r"^api/maintenance/", controles=_ECRITURE, module="maintenance", lecture_sensible=True,
       ecarts=(ECART_A25,), couverture=("maintenance.tests.test_scope_leak",)),
    _r("API-LOGISTIQUE", r"^api/logistics/", controles=_ECRITURE, module="logistics", lecture_sensible=True,
       ecarts=(ECART_A25,), couverture=("logistics.tests.test_scope_leak",)),
    _r("API-FORMATIONS", r"^api/training/", controles=_ECRITURE, module="training", lecture_sensible=True,
       ecarts=(ECART_L32, ECART_A25), couverture=("training.tests.test_scope_requirements",)),
    _r("API-DISCUSSIONS", r"^api/threads/", controles=_QUERYSET, lecture_sensible=True,
       couverture=("threads.tests.test_scope_leak", "threads.tests.test_permissions")),
    _r("API-NOTIFICATIONS", r"^api/notifications/", controles=("authentifie", "proprietaire_objet")),
    _r("API-TABLEAUX", r"^api/dashboard/", controles=_QUERYSET, lecture_sensible=True),
    _r("ADMIN-COMPTES", r"^admin:(accounts|auth)\.", ADMINISTRATION, ("droit_admin_django",), lecture_sensible=True,
       justification="Réservé aux comptes « staff » ; droits d'ajout, de modification et de suppression propres à Django."),
    _r("ADMIN-ORGANISATION", r"^admin:org\.", ADMINISTRATION, ("droit_admin_django",), lecture_sensible=True,
       couverture=("org.tests.test_archivage", "org.tests.test_suppression_unites")),
    _r("ADMIN-AUTRES", r"^admin:", ADMINISTRATION, ("droit_admin_django",), lecture_sensible=True, ecarts=(ECART_A25,)),
    _r("TACHE-COMPTEURS", r"^accounts\.tasks\.", TRAITEMENT, (),
       justification="Purge des compteurs techniques de connexion inactifs : ne touche jamais le journal d'audit (AC-18)."),
    _r("TACHE-GLOBALE", r"^(matrix\.core\.tasks|quarts\.tasks)\.", TRAITEMENT, ("perimetre_batiment",),
       justification="Entretien technique (sessions, brouillons, relèves, échéances) : agit par bâtiment, sans acteur humain."),
    _r("TACHE-MAINTENANCE", r"^maintenance\.tasks\.", TRAITEMENT, ("perimetre_batiment",), module="maintenance", ecarts=(ECART_A25,),
       justification="Écart déclaré d'après l'audit A25 ; seule la tâche de stock est éprouvée par exécution (test_traitements)."),
    _r("TACHE-NOTIFICATIONS", r"^notifications\.tasks\.", TRAITEMENT, ("perimetre_batiment",), ecarts=(ECART_A25,),
       justification="Écart éprouvé par exécution pour notify_low_stock ; les autres tâches sont exécutées sans erreur seulement."),
    _r("TACHE-ANNONCES", r"^annonces\.tasks\.", TRAITEMENT, ("perimetre_batiment",), module="annonces", ecarts=(ECART_A25,),
       justification="Écart déclaré d'après l'audit A25, non éprouvé par exécution."),
)


def regle_de(point):
    """Règle applicable à un point d'entrée, ou None s'il n'est couvert par aucune."""
    cle = point.cle
    for regle in REGLES:
        if regle.correspond(cle):
            return regle
    return None
