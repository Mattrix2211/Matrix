"""Accès sensibles exécutés pour de bon, avec le résultat attendu par profil (preuve d'application, lot L29).

`attendu` est la CIBLE des décisions du PO. Quand le code actuel s'en écarte, `ecarts_connus` enregistre le résultat
réellement observé et `lot_correctif` nomme le lot qui le corrige : l'écart n'est ni masqué ni toléré en silence.
"""

from datetime import timedelta

from django.utils import timezone

from org.models import ModuleActivation
from taches.models import Tache

from .outils import MARQUEUR_S2, Verification

AUTRE_BATIMENT = {"equipier_abe": "refus", "cdt_abe": "refus", "admin_abe": "refus", "soutien_terre": "refus"}
REFUS_HORS_SERVICE = {
    "equipier_b1": "refus", "chef_section_b1": "refus", "chef_secteur_b": "refus", "chef_service_b": "refus",
    "equipier_a": "refus", **AUTRE_BATIMENT,
}


def _demain():
    return (timezone.localdate() + timedelta(days=1)).isoformat()


def _effet_role(attribut, role="COMMANDANT"):
    return lambda monde: type(getattr(monde, attribut).profile).objects.get(pk=getattr(monde, attribut).profile.pk).role == role


def _effet_demande_de_reinitialisation(attribut):
    from accounts.models import DemandeReinitialisation
    return lambda monde: DemandeReinitialisation.objects.filter(user=getattr(monde, attribut)).exists()


def _effet_module_desactive(monde):
    return ModuleActivation.objects.filter(ship=monde.navire, module="logistics", active=False).exists()



def _effet_tache_assignee(monde):
    return Tache.objects.get(pk=monde.tache_service2.pk).assigne_id == monde.equipier_sec2.pk


def _effet_tache_demarree(pk_attr):
    return lambda monde: Tache.objects.get(pk=getattr(monde, pk_attr).pk).statut != "A_FAIRE"


VERIFICATIONS = (
    Verification(
        "V01-passation-par-perimetre", "WEB-PASSATION", "get", lambda m: f"/dashboard/passation/{m.synthese.pk}/",
        contenu=MARQUEUR_S2,
        attendu={
            "equipier_b1": "refus", "equipier_a": "refus", "equipier_abe": "refus",
            "chef_section_b1": "acces-", "chef_section_b2": "acces+", "chef_secteur_b": "acces+", "chef_service_b": "acces+",
            "chef_service_sec": "acces-", "comanav_b": "acces+", "comaeq_b": "acces-", "cdt_b": "acces+", "second_b": "acces+",
            "admin_navire": "refus", "bsc_admin": "refus", "cdt_admin": "acces+", "master_admin": "refus",
        },
        ecarts_connus={"chef_section_b1": "acces+", "chef_service_sec": "acces+", "comaeq_b": "acces+"},
        lot_correctif="L30 (confidentialité par périmètre)",
    ),
    Verification(
        "V02-tache-privee", "WEB-TACHES", "get", lambda m: f"/taches/{m.tache_privee.pk}/", contenu="TACHE-PRIVEE-SECTION-2",
        attendu={
            "equipier_b2": "acces+", "chef_section_b2": "acces+", "equipier_b1": "refus", "chef_section_b1": "refus",
            "chef_secteur_b": "refus", "chef_service_b": "refus", "comanav_b": "refus", "comaeq_b": "refus", "second_b": "refus",
            "cdt_b": "refus", "admin_navire": "refus", "master_admin": "refus", "equipier_a": "refus", "equipier_abe": "refus",
        },
    ),
    Verification(
        "V03-annuaire-api-par-batiment", "API-COMPTES", "get", "/api/accounts/users/", contenu="equipier_abe",
        attendu={
            "equipier_b1": "acces-", "chef_service_b": "acces-", "cdt_b": "acces-", "second_b": "acces-",
            "admin_navire": "acces-", "equipier_a": "acces-", "equipier_abe": "acces+", "master_admin": "acces+",
            "cdt_abe": "acces+", "admin_abe": "acces+", "soutien_terre": "acces+",  # soutien à terre : consultation de toute la flotte, par conception
        },
    ),
    Verification(
        "V04-ticket-api-par-service", "API-LOGISTIQUE", "get", lambda m: f"/api/logistics/tickets/{m.ticket_sec.pk}/",
        attendu={**REFUS_HORS_SERVICE, "cdt_a": "acces", "soutien_terre": "acces", "chef_section_b2": "refus", "comaeq_b": "acces",
                 "cdt_b": "acces"},
    ),
    Verification(
        "V05-calendrier-deplacement-ticket", "WEB-CALENDRIER", "post", "/calendar/events/move/",
        donnees=lambda m: {"type": "ticket", "id": str(m.ticket_sec.pk), "date": _demain()},
        attendu={**REFUS_HORS_SERVICE, "comanav_b": "refus", "second_b": "refus", "comaeq_b": "acces", "cdt_b": "acces",
                 "admin_navire": "refus", "bsc_admin": "refus", "master_admin": "refus"},
    ),
    Verification(
        "V06-ticket-transition-api", "API-LOGISTIQUE", "post", lambda m: f"/api/logistics/tickets/{m.ticket_sec.pk}/transition/",
        donnees={"status": "IN_REPAIR"},
        attendu={**REFUS_HORS_SERVICE, "comanav_b": "refus", "second_b": "refus", "comaeq_b": "acces", "cdt_b": "acces",
                 "admin_navire": "refus", "bsc_admin": "refus", "master_admin": "refus"},
    ),
    Verification(
        "V07-elevation-de-role-api", "API-COMPTES", "patch", lambda m: f"/api/accounts/profiles/{m.equipier_b1.profile.pk}/",
        donnees={"role": "COMMANDANT"},
        attendu={
            "equipier_b1": "refus", "chef_section_b1": "refus", "chef_secteur_b": "refus", "chef_service_b": "refus",
            "comanav_b": "refus", "comaeq_b": "refus", "second_b": "refus", "cdt_b": "refus", "equipier_a": "refus",
            "cdt_a": "refus", "equipier_abe": "refus", "cdt_abe": "refus", "admin_abe": "refus", "soutien_terre": "refus",
            "cdt_admin": "refus", "admin_navire": "refus", "master_admin": "acces",
        },
        effet=_effet_role("equipier_b1"),
    ),
    Verification(
        "V08-auto-attribution-administrateur", "API-COMPTES", "patch", lambda m: f"/api/accounts/profiles/{m.admin_navire.profile.pk}/",
        donnees={"role": "COMMANDANT"}, attendu={"admin_navire": "refus", "bsc_admin": "refus"}, effet=_effet_role("admin_navire"),
        codes={"admin_navire": 403, "bsc_admin": 403},
    ),
    Verification(
        "V09-auto-attribution-equipier", "API-COMPTES", "patch", lambda m: f"/api/accounts/profiles/{m.equipier_b1.profile.pk}/",
        donnees={"role": "COMMANDANT"}, attendu={"equipier_b1": "refus", "admin_navire": "refus"}, effet=_effet_role("equipier_b1"),
        codes={"equipier_b1": 403},
    ),
    Verification(
        "V10-tache-autre-service-adjoint", "WEB-TACHES", "post", lambda m: f"/taches/{m.tache_service2.pk}/action/",
        donnees=lambda m: {"action": "modifier", "assigne": str(m.equipier_sec2.pk), "echeance": "2027-01-01", "priorite": "NORMALE"},
        effet=_effet_tache_assignee,
        attendu={"equipier_b1": "refus", "chef_service_b": "refus", "equipier_a": "refus", "comaeq_b": "acces",
                 "chef_service_sec": "acces", "comanav_b": "refus"},
        ecarts_connus={"comanav_b": "acces"},
        lot_correctif="L32 (écriture bornée au périmètre dans tous les modules)",
    ),
    Verification(
        "V11-ecriture-equipage-a-terre", "WEB-TACHES", "post", lambda m: f"/taches/{m.tache_a.pk}/action/",
        donnees={"action": "demarrer"}, effet=_effet_tache_demarree("tache_a"), attendu={"equipier_a": "refus"}, codes={"equipier_a": 403},
    ),
    Verification(
        "V12-ecriture-equipage-a-bord", "WEB-TACHES", "post", lambda m: f"/taches/{m.tache_b1.pk}/action/",
        donnees={"action": "demarrer"}, effet=_effet_tache_demarree("tache_b1"), attendu={"equipier_b1": "acces"},
    ),
    Verification(
        "V13-configuration-organisation-api", "API-ORG", "post", "/api/org/services/",
        donnees=lambda m: {"name": "Service d'essai", "ship": m.navire.pk},
        attendu={
            "equipier_b1": "refus", "chef_section_b1": "refus", "chef_secteur_b": "refus", "chef_service_b": "refus",
            "comanav_b": "refus", "comaeq_b": "refus", "second_b": "refus", "equipier_a": "refus",
            "equipier_abe": "refus", "cdt_abe": "erreur 400",  # 400 : bâtiment hors du périmètre du commandant
            "admin_abe": "refus", "soutien_terre": "refus", "admin_navire": "refus", "bsc_admin": "refus", "cdt_b": "acces", "cdt_admin": "acces",
        },
    ),
    Verification(
        "V14-administration-django", "ADMIN-COMPTES", "get", "/admin/accounts/userprofile/",
        attendu={
            "equipier_b1": "refus", "chef_service_b": "refus", "cdt_b": "refus", "second_b": "refus", "admin_navire": "refus",
            "staff_sans_droit": "refus", "master_admin": "acces",
        },
    ),
    Verification(
        "V15-activation-de-module", "WEB-REGLAGES", "post", "/parametre/",
        donnees=lambda m: {"action": "toggle_module", "cle_module": "logistics", "ship_id": m.navire.pk},
        effet=_effet_module_desactive,
        attendu={
            "equipier_b1": "refus", "chef_service_b": "refus", "comaeq_b": "refus", "equipier_a": "refus",
            "cdt_a": "refus", "equipier_abe": "refus", "soutien_terre": "refus", "second_b": "refus", "admin_navire": "refus",
            "bsc_admin": "refus", "cdt_b": "acces", "cdt_admin": "acces", "master_admin": "refus",
        },
    ),
    Verification(
        "V16-attribution-de-role-web", "WEB-COMPTES", "post", "/users/",
        donnees=lambda m: {"action": "bulk_update_role", "role": "COMMANDANT", "selected_ids": [m.equipier_b1.pk]},
        effet=_effet_role("equipier_b1"),
        attendu={
            "equipier_b1": "refus", "chef_service_b": "refus", "comaeq_b": "refus", "second_b": "refus", "cdt_b": "refus",
            "equipier_a": "refus", "cdt_abe": "refus", "admin_abe": "refus", "admin_navire": "refus", "bsc_admin": "refus", "master_admin": "acces",
        },
    ),
    Verification(
        "V17-auto-attribution-administrateur-web", "WEB-COMPTES", "post", "/users/",
        donnees=lambda m: {"action": "bulk_update_role", "role": "COMMANDANT", "selected_ids": [m.admin_navire.pk]},
        effet=_effet_role("admin_navire"), attendu={"admin_navire": "refus", "cdt_admin": "refus", "master_admin": "acces"},
    ),
    Verification(
        "V18-designation-legitime-api", "API-COMPTES", "patch", lambda m: f"/api/accounts/profiles/{m.equipier_b1.profile.pk}/",
        donnees={"role": "CHEF_SECTION"}, effet=_effet_role("equipier_b1", "CHEF_SECTION"),
        attendu={
            "cdt_b": "acces", "cdt_admin": "acces", "chef_service_b": "acces", "equipier_b1": "refus", "second_b": "refus",
            "admin_navire": "refus", "bsc_admin": "refus", "admin_abe": "refus", "cdt_abe": "refus", "master_admin": "refus",
        },
    ),
    Verification(
        "V19-attribution-des-droits-techniques", "API-COMPTES", "patch", lambda m: f"/api/accounts/profiles/{m.equipier_b2.profile.pk}/",
        donnees={"administrateur_technique": True, "justification": "besoin d'exploitation"}, effet=lambda m: type(m.equipier_b2.profile).objects.get(pk=m.equipier_b2.profile.pk).administrateur_technique,
        attendu={
            "master_admin": "acces", "admin_navire": "refus", "cdt_admin": "refus", "cdt_b": "refus", "second_b": "refus",
            "chef_service_b": "refus", "equipier_b1": "refus", "admin_abe": "refus", "cdt_abe": "refus", "soutien_terre": "refus",
        },
    ),
    Verification(
        "V27-designation-du-commandant-en-second-api", "API-COMPTES", "patch", lambda m: f"/api/accounts/profiles/{m.equipier_b1.profile.pk}/",
        donnees={"role": "COMMANDANT_EN_SECOND"}, effet=_effet_role("equipier_b1", "COMMANDANT_EN_SECOND"),
        attendu={"cdt_b": "acces", "cdt_admin": "acces", "master_admin": "acces", "second_b": "refus", "admin_navire": "refus",
                 "bsc_admin": "refus", "comanav_b": "refus", "chef_service_b": "refus", "equipier_b1": "refus", "cdt_abe": "refus",
                 "admin_abe": "refus"},
    ),
    Verification(
        "V28-creation-d-un-batiment-gouvernance", "WEB-REGLAGES", "post", "/parametre/",
        donnees={"action": "add_ship", "name": "Unité nouvelle", "code": "NEW", "fuseau_horaire": "Europe/Paris"},
        effet=lambda m: __import__("org.models", fromlist=["Ship"]).Ship.objects.filter(code="NEW").exists(),
        attendu={"master_admin": "acces", "cdt_b": "refus", "cdt_admin": "refus", "admin_navire": "refus", "second_b": "refus",
                 "equipier_b1": "refus"},
    ),
    Verification(
        "V20-auto-attribution-droits-techniques", "API-COMPTES", "patch", lambda m: f"/api/accounts/profiles/{m.equipier_b1.profile.pk}/",
        donnees={"administrateur_technique": True}, effet=lambda m: type(m.equipier_b1.profile).objects.get(pk=m.equipier_b1.profile.pk).administrateur_technique,
        attendu={"equipier_b1": "refus", "chef_service_b": "refus", "cdt_b": "refus"}, codes={"equipier_b1": 403},
    ),
    Verification(
        "V21-abaissement-du-plancher-d-un-seuil", "WEB-REGLAGES", "post", "/parametre/",
        donnees=lambda m: {"action": "update_role_threshold", "cle_action": "module_gestion", "nouveau_role": "EQUIPIER", "ship_id": m.navire.pk},
        effet=lambda m: __import__("matrix.core.role_thresholds", fromlist=["x"]).seuil_role("module_gestion", m.navire.pk) < 7,
        attendu={"admin_navire": "refus", "cdt_admin": "refus", "cdt_b": "refus", "master_admin": "refus"},
        codes={"admin_navire": 403, "cdt_admin": 302},  # redirection avec message ; le jumeau V24 prouve que l'adresse et l'action sont valides
    ),
    Verification(
        "V24-seuil-metier-sans-plancher-reste-reglable-par-le-commandement", "WEB-REGLAGES", "post", "/parametre/",
        donnees=lambda m: {"action": "update_role_threshold", "cle_action": "asset_ecriture_simple", "nouveau_role": "CHEF_SERVICE", "ship_id": m.navire.pk},
        effet=lambda m: __import__("matrix.core.role_thresholds", fromlist=["x"]).seuil_role("asset_ecriture_simple", m.navire.pk) == 4,
        attendu={"cdt_b": "acces", "cdt_admin": "acces", "admin_navire": "refus", "equipier_b1": "refus", "admin_abe": "refus"},
    ),
    Verification(
        "V26-seuil-de-circuit-fermé-à-l-administrateur-technique-seul", "WEB-REGLAGES", "post", "/parametre/",
        donnees=lambda m: {"action": "update_role_threshold", "cle_action": "liste_service_publication", "nouveau_role": "EQUIPIER", "ship_id": m.navire.pk},
        effet=lambda m: __import__("matrix.core.role_thresholds", fromlist=["x"]).seuil_role("liste_service_publication", m.navire.pk) < 2,
        attendu={"admin_navire": "refus", "bsc_admin": "refus", "admin_abe": "refus", "cdt_admin": "acces", "master_admin": "refus"},
    ),
    Verification(
        "V22-reinitialisation-mot-de-passe-d-un-equipier", "WEB-COMPTES", "post", "/users/",
        donnees=lambda m: {"action": "set_password", "pk": m.equipier_b1.pk}, effet=_effet_demande_de_reinitialisation("equipier_b1"),
        attendu={"admin_navire": "acces", "cdt_admin": "acces", "master_admin": "acces", "cdt_b": "refus", "second_b": "refus",
                 "equipier_b1": "refus", "admin_abe": "refus", "chef_service_b": "refus"},
    ),
    Verification(
        "V23-reinitialisation-mot-de-passe-d-une-autorite", "WEB-COMPTES", "post", "/users/",
        donnees=lambda m: {"action": "set_password", "pk": m.cdt_b.pk}, effet=_effet_demande_de_reinitialisation("cdt_b"),
        attendu={"admin_navire": "refus", "bsc_admin": "refus", "cdt_b": "refus", "master_admin": "acces"},
    ),
    Verification(
        "V25-designation-legitime-web", "WEB-COMPTES", "post", "/users/",
        donnees=lambda m: {"action": "bulk_update_role", "role": "CHEF_SECTION", "selected_ids": [m.equipier_b1.pk]},
        effet=_effet_role("equipier_b1", "CHEF_SECTION"),
        attendu={"cdt_b": "acces", "cdt_admin": "acces", "master_admin": "refus", "admin_navire": "refus", "second_b": "refus",
                 "bsc_admin": "refus", "equipier_b1": "refus", "admin_abe": "refus", "cdt_abe": "refus"},
    ),
)
