"""Verrou des commandes de démonstration.

Les commandes `seed_demo*` créent des comptes fictifs : elles ne s'exécutent que sur une base explicitement
dédiée à cet usage. Les mots de passe ne sont jamais prévisibles : fournis par l'opérateur ou générés au hasard.
"""
import os
import secrets
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import CommandError
from django.db import OperationalError, connection

VARIABLE_ACTIVATION = "MATRIX_INSTANCE_DEMO"
VARIABLE_MOT_DE_PASSE = "MATRIX_DEMO_PASSWORD"
VARIABLE_MOT_DE_PASSE_ADMIN = "MATRIX_DEMO_ADMIN_PASSWORD"
VARIABLE_IDENTIFIANTS = "MATRIX_DEMO_IDENTIFIANTS"
SUFFIXE_MARQUEUR = ".instance_demo"  # fichier voisin de la base SQLite, écrit par la préparation de l'instance
SUFFIXE_IDENTIFIANTS = ".identifiants"  # un fichier d'identifiants par base : jamais partagé entre deux instances
MOTS_DE_PASSE_HERITES = ("pass", "admin")  # anciens mots de passe prévisibles des bases déjà créées
TABLE_MARQUEUR = "accounts_instancedemo"

# Comptes créés par les quatre générateurs ; un test vérifie que la liste reste exacte.
COMPTES_DEMO = frozenset((
    "admin", "admin_navire", "cdt_a", "cdt_abe", "cdt_b", "cdt_jch", "cdt_nor", "chef_liste_abe",
    "chef_liste_jch", "chef_secteur_a", "chef_secteur_b", "chef_secteur_elec_a", "chef_secteur_incendie_a",
    "chef_secteur_nor", "chef_section_a", "chef_service_a", "chefsecteur", "chefsection", "chefservice",
    "coma_comaeq", "coma_comanav", "coma_comops", "comaeq_abe", "comaeq_jch", "commandant", "equipier",
    "equipier_a", "equipier_a2", "equipier_elec_a", "equipier_incendie_a", "equipier_nor", "historique_abe",
    "m_bernard", "m_blanchard", "m_boyer", "m_chevalier", "m_colin", "m_dubois", "m_faure", "m_fontaine",
    "m_garnier", "m_girard", "m_guerin", "m_lambert", "m_lefevre", "m_marchand", "m_moreau", "m_perrin",
    "m_renard", "m_roussel", "marin_abe_1", "marin_abe_2", "marin_abe_3", "marin_b", "marin_jch_1",
    "marin_jch_2", "marin_jch_3", "second_a", "terre_chef_securite", "terre_classe", "terre_securite",
))

_cache = {}


def en_test():
    """Vrai dans un processus de tests Django (base de test jetable) : le verrou d'environnement n'y a pas lieu d'être."""
    from django.core import mail

    return hasattr(mail, "outbox")


def chemin_base():
    """Fichier de la base SQLite active, ou None (autre moteur, base en mémoire)."""
    if connection.vendor != "sqlite":
        return None
    nom = str(connection.settings_dict["NAME"])
    return None if nom == ":memory:" or nom.startswith("file:") else Path(nom)


def fichier_marqueur():
    base = chemin_base()
    return None if base is None else base.with_name(base.name + SUFFIXE_MARQUEUR)


def identifiant_instance():
    """Identifiant écrit par la préparation dans le fichier voisin de la base ; "" pour un fichier ancien (vide), None s'il est absent."""
    fichier = fichier_marqueur()
    if fichier is None or not fichier.is_file():
        return None
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        cle, separateur, valeur = ligne.partition(":")
        if separateur and cle.strip() == "instance":
            return valeur.strip()
    return ""


def _identifiant_en_base():
    from accounts.models import InstanceDemo

    ligne = InstanceDemo.objects.order_by("pk").first()
    return None if ligne is None else ligne.identifiant


def _rattacher_identifiant(identifiant):
    from accounts.models import InstanceDemo

    InstanceDemo.objects.filter(identifiant="").update(identifiant=identifiant)


def base_marquee():
    """Vrai si la base porte le marqueur de démonstration (faux si la table n'existe pas encore)."""
    try:
        if TABLE_MARQUEUR not in connection.introspection.table_names():
            return False
        from accounts.models import InstanceDemo

        return InstanceDemo.objects.exists()
    except OperationalError:
        return False


def marquer_base(commande):
    from accounts.models import InstanceDemo

    if not InstanceDemo.objects.exists():
        InstanceDemo.objects.create(commande=commande, identifiant=identifiant_instance() or "")


def adopter_ancienne_base():
    """Base préparée avant le verrou (fichier voisin vide) : écrit l'identifiant d'instance après contrôle objectif des comptes.

    Chaque compte doit être un compte de démonstration encore protégé par un ancien mot de passe prévisible, preuve qu'il a été
    créé par l'ancien générateur et jamais modifié. Retourne les comptes refusés (liste vide = adoption faite)."""
    refuses = [u.username for u in get_user_model().objects.order_by("username")
               if u.username not in COMPTES_DEMO or not any(u.check_password(m) for m in MOTS_DE_PASSE_HERITES)]
    if refuses or not get_user_model().objects.exists():
        return refuses or ["(aucun compte)"]
    fichier_marqueur().write_text(f"instance : {secrets.token_hex(16)}\n", encoding="utf-8")
    return []


def comptes_etrangers():
    """Noms des comptes qui ne sont pas des comptes de démonstration."""
    return sorted(set(get_user_model().objects.values_list("username", flat=True)) - COMPTES_DEMO)


def conditions_manquantes(exiger_preuve=True):
    """Conditions d'environnement non remplies (liste vide dans un processus de tests).

    La preuve de préparation est un identifiant d'instance NON VIDE dans le fichier voisin : un fichier vide ou créé à la main ne suffit pas."""
    if en_test():
        return []
    manque = []
    if not settings.DEBUG:
        manque.append("le mode DEBUG n'est pas actif (DJANGO_DEBUG=1)")
    if os.environ.get(VARIABLE_ACTIVATION) != "1":
        manque.append(f"la variable {VARIABLE_ACTIVATION}=1 n'est pas posée")
    if connection.vendor != "sqlite":
        manque.append(f"le moteur de base est {connection.vendor} et non SQLite")
    elif chemin_base() is None:
        manque.append("la base SQLite n'est pas un fichier")
    elif exiger_preuve and not identifiant_instance():
        manque.append(f"le fichier {fichier_marqueur().name}, écrit par la préparation de l'instance de démonstration, est absent ou vide")
    return manque


def exiger_base_demo(commande, creation=False):
    """Refuse (CommandError) sauf sur une base dédiée à la démonstration.

    `creation` : la commande peut remplir une base encore vide, qui reçoit alors le marqueur."""
    manque = conditions_manquantes()
    if manque:
        raise CommandError(
            f"Refus : {commande} ne s'exécute que sur une base dédiée à la démonstration. À corriger : "
            + " ; ".join(manque) + ". Préparer l'instance : python scripts/preparer_instance_test.py --reinitialiser.")
    if base_marquee():
        dans_le_fichier, en_base = identifiant_instance(), _identifiant_en_base()
        if dans_le_fichier and en_base and dans_le_fichier != en_base:
            raise CommandError(f"Refus : le fichier {fichier_marqueur().name} appartient à une autre instance que cette base ({commande}). "
                               "Aucune modification n'a été faite.")
        if dans_le_fichier and not en_base:
            _rattacher_identifiant(dans_le_fichier)
        return
    if creation and not get_user_model().objects.exists():
        marquer_base(commande)
        return
    raise CommandError(
        f"Refus : cette base n'est pas marquée comme base de démonstration et contient déjà des données ({commande}). "
        "Aucune modification n'a été faite. Utiliser une base neuve, ou marquer une base déjà fictive : "
        "python manage.py marquer_instance_demo.")


def erreur_base_de_demonstration_en_production():
    """Message d'erreur si une base marquée « démonstration » sert hors DEBUG, sinon chaîne vide."""
    if settings.DEBUG or en_test():
        return ""
    try:
        marquee = base_marquee()
    except Exception:  # base injoignable : ce n'est pas à ce contrôle d'en décider
        return ""
    return ("Cette base est marquée comme base de démonstration (comptes fictifs) : elle ne peut pas servir en production. "
            "Utiliser une base de production distincte.") if marquee else ""


def exiger_pas_de_base_de_demo_en_production():
    message = erreur_base_de_demonstration_en_production()
    if message:
        raise ImproperlyConfigured(message)


# ---------- Mots de passe ----------

def _fichier_identifiants():
    chemin = os.environ.get(VARIABLE_IDENTIFIANTS)
    if chemin:
        return Path(chemin)
    base = chemin_base()
    return None if base is None else base.with_name(base.name + SUFFIXE_IDENTIFIANTS)


def _lire_identifiants(chemin):
    valeurs = {}
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        cle, separateur, valeur = ligne.partition(":")
        if separateur and valeur.strip():
            valeurs[cle.strip()] = valeur.strip()
    if "comptes" not in valeurs or "admin" not in valeurs:
        raise CommandError(f"Fichier d'identifiants illisible : {chemin}. Le supprimer pour en générer un nouveau.")
    attendu = identifiant_instance()
    if attendu and valeurs.get("instance") and valeurs["instance"] != attendu:
        raise CommandError(f"Fichier d'identifiants d'une autre instance : {chemin}. Aucun mot de passe n'a été utilisé ni écrasé.")
    return valeurs


def _ecrire_identifiants(chemin, valeurs):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    descripteur = os.open(chemin, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)  # lisible par le seul propriétaire, jamais écrasé
    with os.fdopen(descripteur, "w", encoding="utf-8") as fichier:
        fichier.write("Mots de passe de l'instance de démonstration (fictifs). Ne pas versionner, ne pas partager.\n")
        if identifiant_instance():
            fichier.write(f"instance : {identifiant_instance()}\n")
        for cle, valeur in valeurs.items():
            fichier.write(f"{cle} : {valeur}\n")


def _mots_de_passe():
    if "valeurs" in _cache:
        return _cache["valeurs"]
    fournis = {"comptes": os.environ.get(VARIABLE_MOT_DE_PASSE, ""), "admin": os.environ.get(VARIABLE_MOT_DE_PASSE_ADMIN, "")}
    if all(fournis.values()):
        valeurs = fournis
    elif en_test():
        valeurs = {cle: valeur or secrets.token_urlsafe(12) for cle, valeur in fournis.items()}
    else:
        chemin = _fichier_identifiants()
        if chemin is None:
            raise CommandError(f"Aucun emplacement pour les mots de passe : poser {VARIABLE_MOT_DE_PASSE} et {VARIABLE_MOT_DE_PASSE_ADMIN}, "
                               f"ou {VARIABLE_IDENTIFIANTS}.")
        if chemin.exists():
            valeurs = {**_lire_identifiants(chemin), **{cle: valeur for cle, valeur in fournis.items() if valeur}}
        else:
            valeurs = {cle: valeur or secrets.token_urlsafe(12) for cle, valeur in fournis.items()}
            _ecrire_identifiants(chemin, valeurs)
    _cache["valeurs"] = valeurs
    return valeurs


def mot_de_passe_commun():
    """Mot de passe des comptes de démonstration ordinaires : fourni, relu dans le fichier d'identifiants, ou généré."""
    return _mots_de_passe()["comptes"]


def mot_de_passe_admin():
    """Mot de passe du compte de flotte `admin`."""
    return _mots_de_passe()["admin"]


def oublier_mots_de_passe():
    _cache.clear()


def description_mots_de_passe():
    """Où trouver les mots de passe, sans jamais les afficher."""
    if os.environ.get(VARIABLE_MOT_DE_PASSE):
        return f"fournis par la variable {VARIABLE_MOT_DE_PASSE}"
    chemin = _fichier_identifiants()
    return f"dans le fichier {chemin}" if chemin else "non conservés (génération en mémoire)"


def comptes_a_mot_de_passe_herite():
    """Comptes actifs dont le mot de passe est l'un des anciens mots de passe prévisibles."""
    return [u.username for u in get_user_model().objects.filter(is_active=True).order_by("username")
            if any(u.check_password(m) for m in MOTS_DE_PASSE_HERITES)]


def regenerer_mots_de_passe_herites():
    """Remplace les anciens mots de passe prévisibles des comptes de démonstration. Ne touche aucun autre mot de passe."""
    modifies = []
    for compte in get_user_model().objects.filter(username__in=COMPTES_DEMO).order_by("username"):
        if any(compte.check_password(m) for m in MOTS_DE_PASSE_HERITES):
            compte.set_password(mot_de_passe_admin() if compte.username == "admin" else mot_de_passe_commun())
            compte.save(update_fields=["password"])
            modifies.append(compte.username)
    return modifies
