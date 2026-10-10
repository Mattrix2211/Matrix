"""Page de démonstration des composants (styleguide, docs/UX.md §26.1).

Réservée aux administrateurs (ADMIN_NAVIRE et MASTER_ADMIN, via ``user_role_level``).
Rien n'est copié : chaque exemple est un gabarit ``{% ... %}`` réellement rendu,
et le code affiché est exactement celui qui a été rendu. Les paramètres sont lus
dans l'en-tête de chaque gabarit de ``components/`` et les contrastes sont calculés
sur les variables de ``matrix.css``. Le styleguide ne peut donc pas dériver.
"""
import re
from datetime import datetime

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.template import TemplateDoesNotExist, engines
from django.template.loader import get_template
from django.views.generic import TemplateView

from matrix.core.icones import ICONES
from matrix.core.roles import RoleLevel, user_role_level

CSS = settings.BASE_DIR / "matrix" / "static" / "css" / "matrix.css"

ETAPES = ["Choix de l'article", "Quantité", "Synthèse"]
COLONNES_GRILLE = [
    {"nom": "serie", "libelle": "N° de série"},
    {"nom": "controle", "libelle": "Date de contrôle", "type": "date"},
    {"nom": "pression", "libelle": "Pression (bar)", "type": "nombre"},
    {"nom": "etat", "libelle": "État", "type": "conformite"},
]
LIGNES_GRILLE = [
    {"cle": "1", "libelle": "Extincteur 1", "valeurs": {"serie": "EX-0412", "controle": "02/10/2026"}},
    {"cle": "2", "libelle": "Extincteur 2", "valeurs": {"serie": "EX-0413", "etat": "non_conforme"}},
    {"cle": "3", "libelle": "Extincteur 3", "valeurs": {"serie": "EX-0414"}},
]
LIGNES_GRILLE_ERREUR = [
    {"cle": "1", "libelle": "Extincteur 1", "valeurs": {"serie": "EX-0412", "controle": "31/02/2026"},
     "erreurs": {"controle": "Date invalide (JJ/MM/AAAA)"}},
    {"cle": "2", "libelle": "Extincteur 2", "valeurs": {"serie": "EX-0413", "etat": "conforme"}},
]

# Données de l'exemple « en-tête de fiche ».
INDICATEURS_FICHE = [
    {"libelle": "Heures de marche", "valeur": "1 248", "unite": "h", "url": "#entete"},
    {"libelle": "Vibrations", "valeur": "État B", "etat": "attention", "url": "#entete"},
    {"libelle": "Isolement", "valeur": "72", "unite": "MΩ", "etat": "ok"},
]
ACTION_FICHE = {"libelle": "Signaler une anomalie", "icone": "anomalie", "url": "#entete"}
MENU_FICHE = [
    {"libelle": "Modifier les infos", "icone": "modification", "url": "#entete", "ecriture": True},
    {"libelle": "Imprimer la fiche", "icone": "impression", "url": "#entete"},
    {"libelle": "Supprimer", "icone": "suppression", "url": "#entete", "danger": True, "ecriture": True},
]
OBJET_FICHE = {"created_by": {"username": "dupont"}, "created_at": datetime(2026, 9, 12, 8, 15),
               "updated_by": {"username": "durand"}, "updated_at": datetime(2026, 10, 1, 16, 40)}


def ex(libelle, code, note="", formulaire=False, vue=""):
    """Un exemple : ``code`` est rendu tel quel puis affiché tel quel."""
    return {"libelle": libelle, "code": code.strip(), "note": note, "formulaire": formulaire, "vue": vue}


COMPOSANTS = [
    {
        "nom": "fiche_entete", "titre": "En-tête de fiche", "balise": False,
        "quand": "Le haut de toute grande fiche métier : identité, indicateurs, une seule action principale, Discussion, menu, version et traçabilité.",
        "quand_pas": "Pour une liste ou un écran sans objet unique. Jamais deux actions principales : les autres vont dans le menu.",
        "exemples": [
            ex("Fiche complète",
               '{% include "components/fiche_entete.html" with titre="Pompe incendie tribord" sous_titre="Installation critique · Mécanique" badge_libelle="Opérationnelle" badge_etat="ok" indicateurs=indicateurs action=action menu=menu commentaires=commentaires commentaire_action_url="#entete" objet=objet historique_url="#entete" %}',
               "Le bouton Discussion ouvre le panneau latéral ; l'action principale et les entrées d'écriture du menu disparaissent pour l'équipage à terre.", False,
               "indicateurs = [{libelle, valeur, unite, etat, url}, ...]  ·  action = {libelle, icone, url}  ·  menu = [{libelle, icone, url, danger, ecriture}, ...]"),
            ex("Avec bandeau de version",
               '{% include "components/fiche_entete.html" with titre="Fiche de maintenance" sous_titre="Plan hebdomadaire" version=version %}',
               "", False, "version = {publiee_le, proposition_par, proposition_le}"),
        ],
    },
    {
        "nom": "surface", "titre": "Surface", "balise": True,
        "quand": "Regrouper des informations d'un même sujet dans un cadre neutre (mesures, détail d'une fiche).",
        "quand_pas": "Pour un élément cliquable (carte interactive) ou une alerte (attention). Une surface n'a jamais de survol.",
        "exemples": [
            ex("Avec titre et icône", '{% surface titre="Mesures" icone="maintenance" %}<p class="mb-0">Heures de marche : 1 248 h</p>{% fin_surface %}',
               "Aucun survol : un cadre non cliquable ne réagit pas à la souris."),
            ex("Sans titre", '{% surface %}<p class="mb-0">Contenu libre.</p>{% fin_surface %}'),
        ],
    },
    {
        "nom": "carte_interactive", "titre": "Carte interactive", "balise": True,
        "quand": "Un élément entier mène à sa fiche (matériel, installation, formation).",
        "quand_pas": "Si rien ne se passe au clic (utiliser une surface) ; ne pas imbriquer de bouton ou de lien dans la carte.",
        "exemples": [
            ex("Normal", '{% carte_interactive url="#carte" titre="Pompe d\'assèchement P1" sous_titre="Local machine 2" icone="piece" %}{% fin_carte_interactive %}',
               "Survol et focus clavier : bordure Signal et ombre légère ; la flèche à droite annonce le lien."),
            ex("Sans icône, avec précision", '{% carte_interactive url="#carte" titre="Extincteurs CO2" contenu="12 en service, 1 à contrôler" %}{% fin_carte_interactive %}'),
        ],
    },
    {
        "nom": "carte_action", "titre": "Carte d'action", "balise": True,
        "quand": "Une action est attendue de l'utilisateur (signer, valider, saisir un compte rendu).",
        "quand_pas": "Pour une simple information (surface) ; une seule action principale (Signal) par vue.",
        "exemples": [
            ex("Action secondaire (par défaut)", '{% carte_action titre="2 comptes rendus à saisir" libelle="Ouvrir" url="#action" icone="maintenance" %}{% fin_carte_action %}'),
            ex("Action principale de la vue", '{% carte_action titre="Fiche à valider" libelle="Valider" url="#action" principale=True %}Proposée par le chef de secteur{% fin_carte_action %}',
               "Le bouton est le seul en Signal plein : n'en mettre qu'un par vue."),
        ],
    },
    {
        "nom": "metric", "titre": "Indicateur (Metric)", "balise": False,
        "quand": "Une valeur chiffrée compacte : heures de marche, nombre d'anomalies, isolement.",
        "quand_pas": "Pour une évolution dans le temps (graphique) ou un taux (jauge).",
        "exemples": [
            ex("Neutre", '{% include "components/metric.html" with libelle="Heures de marche" valeur="1 248" unite="h" icone="historique" detail="+42 h / mois" %}'),
            ex("États (écrits en toutes lettres)",
               '{% include "components/metric.html" with libelle="Isolement" valeur="72" unite="MΩ" etat="ok" %}'
               '{% include "components/metric.html" with libelle="Vibrations" valeur="B" etat="attention" %}'
               '{% include "components/metric.html" with libelle="Anomalies" valeur="4" etat="danger" icone="anomalie" %}'),
            ex("Avec popover (devient un bouton)", '{% include "components/metric.html" with libelle="Dernier relevé" valeur="72" unite="MΩ" popover="Relevé du 02/10/2026 par le chef de secteur." %}',
               "Seul cas où une Metric réagit au survol et au focus."),
        ],
    },
    {
        "nom": "attention", "titre": "Attention", "balise": True,
        "quand": "Une vraie anomalie, un retard ou un danger demande l'attention.",
        "quand_pas": "Pour une information courante ou un succès ; ne pas multiplier les alertes sur une même vue.",
        "exemples": [
            ex("Attention (ambre)", '{% attention titre="Contrôle à prévoir sous 7 jours" %}Extincteur 4, local machine.{% fin_attention %}'),
            ex("Danger (rouge)", '{% attention niveau="danger" titre="Installation critique hors service" icone="retard" %}Pompe P1 : ticket ouvert.{% fin_attention %}',
               "Le niveau est dit par l'icône et le mot « Danger », jamais par la couleur seule."),
        ],
    },
    {
        "nom": "badge_etat", "titre": "Badge d'état", "balise": False,
        "quand": "Dire l'état d'un objet en une pastille (opérationnel, à surveiller, en panne, terminé).",
        "quand_pas": "Pour un texte long ; ne jamais coder l'état par la couleur seule (libellé et icône toujours présents).",
        "exemples": [
            ex("Les quatre états",
               '{% include "components/badge_etat.html" with etat="ok" libelle="Opérationnel" %} '
               '{% include "components/badge_etat.html" with etat="attention" libelle="À surveiller" %} '
               '{% include "components/badge_etat.html" with etat="danger" libelle="En panne" %} '
               '{% include "components/badge_etat.html" with libelle="Terminé" %}'),
        ],
    },
    {
        "nom": "jauge", "titre": "Jauge", "balise": False,
        "quand": "Une progression ou un taux de 0 à 100, avec la valeur écrite.",
        "quand_pas": "Pour une valeur sans maximum (indicateur) ou une série dans le temps (graphique).",
        "exemples": [
            ex("Neutre et trois états",
               '{% include "components/jauge.html" with libelle="Avancement" valeur=40 %}'
               '{% include "components/jauge.html" with libelle="Stock" valeur=90 etat="ok" %}'
               '{% include "components/jauge.html" with libelle="Durée de vie restante" valeur=55 etat="attention" %}'
               '{% include "components/jauge.html" with libelle="Pièces disponibles" valeur=12 etat="danger" %}'),
            ex("Valeur invalide ou hors bornes", '{% include "components/jauge.html" with libelle="Hors bornes" valeur=250 %}{% include "components/jauge.html" with libelle="Valeur invalide" valeur="abc" %}',
               "La valeur est bornée de 0 à 100 ; une valeur non numérique donne 0."),
        ],
    },
    {
        "nom": "etat_vide", "titre": "État vide", "balise": False,
        "quand": "Une liste ou un écran sans donnée : dire pourquoi et proposer la suite logique.",
        "quand_pas": "Pendant un chargement ou pour une erreur (utiliser attention).",
        "exemples": [
            ex("Avec la suite logique", '{% include "components/etat_vide.html" with icone="maintenance" titre="Aucune maintenance à faire" texte="Tout est à jour pour cette semaine." url="#vide" libelle="Voir le calendrier" %}'),
            ex("Minimal", '{% include "components/etat_vide.html" with titre="Aucun résultat" %}'),
        ],
    },
    {
        "nom": "popover", "titre": "Popover", "balise": False,
        "quand": "Une petite information ou précision sans quitter la page.",
        "quand_pas": "Pour un formulaire ou une information indispensable (la mettre à l'écran).",
        "exemples": [
            ex("Normal", '{% include "components/popover.html" with libelle="Dernier relevé" titre="Isolement" texte="72 MΩ le 02/10/2026" icone="information" %}',
               "S'ouvre au clic, au survol et au focus clavier ; se ferme avec Échap. Le texte est du texte brut."),
        ],
    },
    {
        "nom": "menu_contextuel", "titre": "Menu contextuel (et entrée de menu)", "balise": True,
        "quand": "Les actions secondaires d'un objet : modifier, imprimer, archiver, supprimer.",
        "quand_pas": "Pour l'action principale de la vue. L'action destructive (danger) vient toujours en dernier.",
        "gabarit_extra": "menu_item",
        "exemples": [
            ex("Avec action destructive", '{% menu_contextuel libelle="Actions sur la pompe P1" %}'
               '{% include "components/menu_item.html" with libelle="Modifier" url="#menu" icone="modification" %}'
               '{% include "components/menu_item.html" with libelle="Imprimer la fiche" url="#menu" icone="impression" %}'
               '{% include "components/menu_item.html" with libelle="Supprimer" url="#menu" icone="suppression" danger=True %}'
               "{% fin_menu_contextuel %}",
               "Flèches pour naviguer, Échap pour fermer."),
        ],
    },
    {
        "nom": "modale", "titre": "Modale", "balise": True,
        "quand": "Une action courte demandant une concentration : confirmation, mot de passe, signalement rapide.",
        "quand_pas": "Pour un formulaire métier (panneau latéral, assistant ou page).",
        "exemples": [
            ex("Confirmation", '<button type="button" class="btn btn-outline-secondary" data-bs-toggle="modal" data-bs-target="#sg-modale">Archiver la fiche</button>\n'
               '{% modale id="sg-modale" titre="Archiver la fiche ?" %}<p>La fiche reste consultable dans l\'historique.</p>'
               '<button type="button" class="btn btn-primary" data-bs-dismiss="modal">Archiver</button>{% fin_modale %}',
               "Le focus reste dans la modale ; Échap la ferme."),
        ],
    },
    {
        "nom": "panneau_lateral", "titre": "Panneau latéral", "balise": True,
        "quand": "Plusieurs champs ou une consultation en gardant le contexte : filtres, affectation, discussion.",
        "quand_pas": "Pour une simple confirmation (modale) ou un parcours en plusieurs étapes (assistant).",
        "exemples": [
            ex("À droite (par défaut)", '<button type="button" class="btn btn-outline-secondary" data-bs-toggle="offcanvas" data-bs-target="#sg-panneau" aria-controls="sg-panneau">Ouvrir la discussion</button>\n'
               '{% panneau_lateral id="sg-panneau" titre="Discussion" icone="discussion" %}<p>Aucun message pour l\'instant.</p>{% fin_panneau_lateral %}',
               "Bouton Fermer, clic hors du panneau ou Échap."),
            ex("À gauche", '<button type="button" class="btn btn-outline-secondary" data-bs-toggle="offcanvas" data-bs-target="#sg-panneau-gauche" aria-controls="sg-panneau-gauche">Filtres</button>\n'
               '{% panneau_lateral id="sg-panneau-gauche" titre="Filtres" cote="start" %}<p>Champs de filtre.</p>{% fin_panneau_lateral %}'),
        ],
    },
    {
        "nom": "assistant", "titre": "Assistant", "balise": True,
        "quand": "Création d'un objet isolé et complexe en plusieurs étapes (ajout de matériel, signalement d'anomalie).",
        "quand_pas": "Pour une saisie en série (grille) ou un objet simple (formulaire). Revenir en arrière ne perd aucune donnée.",
        "exemples": [
            ex("Étape intermédiaire", '{% assistant id="sg-assistant-2" titre="Ajout de matériel" etapes=etapes etape=2 %}<p>Contenu de l\'étape.</p>{% fin_assistant %}',
               "Dans le formulaire de la vue ; Suivant précède Précédent dans le DOM (Entrée valide la suite).", True,
               "etapes = [\"Choix de l'article\", \"Quantité\", \"Synthèse\"]"),
            ex("Dernière étape (synthèse)", '{% assistant id="sg-assistant-3" titre="Ajout de matériel" etapes=etapes etape=3 libelle_final="Ajouter 12 extincteurs" %}<p>Synthèse métier.</p>{% fin_assistant %}',
               "", True, "etapes = [\"Choix de l'article\", \"Quantité\", \"Synthèse\"]"),
        ],
    },
    {
        "nom": "grille", "titre": "Grille de saisie", "balise": True,
        "quand": "Saisie ou contrôle en série de plusieurs lignes (20 extincteurs), façon tableur.",
        "quand_pas": "Pour un objet isolé (assistant ou formulaire simple).",
        "exemples": [
            ex("Fonctionnelle (brouillon désactivé)", '{% grille id="sg-grille" libelle="Contrôle des extincteurs" libelle_ligne="Extincteur" colonnes=colonnes lignes=lignes libelle_final="Enregistrer le contrôle" %}{% fin_grille %}',
               "Essayez : flèches, Entrée, Échap, Ctrl+D, « Tout conforme », collage depuis Excel. Sans paramètre brouillon, rien n'est enregistré côté serveur.", True,
               "colonnes = [{nom, libelle, type}, ...]  ·  lignes = [{cle, libelle, valeurs, erreurs}, ...]"),
            ex("Erreur dans une cellule", '{% grille id="sg-grille-erreur" libelle="Contrôle avec erreur" colonnes=colonnes lignes=lignes_erreur %}{% fin_grille %}',
               "L'erreur s'affiche dans la cellule concernée, ligne par ligne.", True),
            ex("Lecture seule (équipage à terre)", '{% grille id="sg-grille-ro" libelle="Contrôle en lecture seule" colonnes=colonnes lignes=lignes lecture_seule=True %}{% fin_grille %}',
               "Aucune saisie, aucun bouton.", True),
        ],
    },
]

# Groupes de couleurs : (titre, [(variable, rôle)])
COULEURS = [
    ("Fonds", [("bg", "Fond de page"), ("surface", "Cartes, panneaux, modales"), ("border", "Bordures")]),
    ("Textes", [("text", "Texte principal"), ("text-sec", "Texte secondaire"), ("text-ter", "Texte discret (indication non essentielle)")]),
    ("Accent", [("signal", "Action principale, sélection, focus"), ("signal-ui", "Bordures et remplissages Signal (contraste 3:1)"),
                ("wake", "Survol de Signal"), ("horizon", "Survol des boutons")]),
    ("États", [("green-tech", "Conforme, validé, opérationnel"), ("amber", "Attention, surveillance"), ("red", "Danger (bordures)"),
               ("red-plein", "Pastilles pleines rouges (texte blanc)"), ("red-texte", "Texte rouge, action destructive")]),
    ("Palette", [("navy", "Marine"), ("ocean", "Océan"), ("slate", "Ardoise"), ("mist", "Brume"), ("fog", "Brouillard"),
                 ("ink", "Encre (texte posé sur Signal ou vert)"), ("paper", "Papier")]),
]

# Paires testées : (usage, premier plan, arrière-plan, seuil WCAG)
PAIRES_CONTRASTE = [
    ("Texte principal sur le fond", "text", "bg", 4.5),
    ("Texte principal sur une surface", "text", "surface", 4.5),
    ("Texte secondaire sur une surface", "text-sec", "surface", 4.5),
    ("Texte secondaire sur le fond", "text-sec", "bg", 4.5),
    ("Texte discret sur une surface", "text-ter", "surface", 4.5),
    ("Texte du bouton principal (encre sur Signal)", "ink", "signal", 4.5),
    ("Texte d'un bouton vert (encre sur vert)", "ink", "green-tech", 4.5),
    ("Texte blanc sur pastille rouge pleine", "paper", "red-plein", 4.5),
    ("Texte rouge sur une surface", "red-texte", "surface", 4.5),
    ("Texte rouge sur le fond", "red-texte", "bg", 4.5),
    ("Bordure Signal sur une surface (non textuel)", "signal-ui", "surface", 3.0),
    ("Signal pur sur une surface (non textuel)", "signal", "surface", 3.0),
    ("Vert sur une surface (non textuel)", "green-tech", "surface", 3.0),
    ("Ambre sur une surface (non textuel)", "amber", "surface", 3.0),
]

POLICES = [
    ("f-display", "Space Grotesk", "Titres de section, cartes, navigation"),
    ("f-body", "Inter", "Corps de texte"),
    ("f-mono", "JetBrains Mono", "Données techniques, dates, codes"),
]
ESPACEMENTS = [("s1", 4), ("s2", 8), ("s3", 12), ("s4", 16), ("s5", 20), ("s6", 24), ("s8", 32), ("s10", 40), ("s12", 48), ("s16", 64)]


def variables_css():
    """Variables hexadécimales du mode clair et du mode sombre, lues dans matrix.css."""
    texte = CSS.read_text(encoding="utf-8")

    def lire(blocs):
        valeurs = {}
        for bloc in blocs:
            valeurs.update(re.findall(r"--([a-z0-9-]+):\s*([^;]+?)\s*;", bloc))
        return valeurs

    clair = lire(re.findall(r":root\s*\{(.*?)\n\}", texte, re.S))
    sombre = dict(clair)
    sombre.update(lire(re.findall(r'\[data-theme="sombre"\]\s*\{(.*?)\n\}', texte, re.S)))

    def resoudre(valeurs):
        resolu = {}
        for nom, valeur in valeurs.items():
            while (m := re.fullmatch(r"var\(--([a-z0-9-]+)\)", valeur)) and m.group(1) in valeurs:
                valeur = valeurs[m.group(1)]
            if re.fullmatch(r"#[0-9A-Fa-f]{6}", valeur):
                resolu[nom] = valeur.upper()
        return resolu

    return resoudre(clair), resoudre(sombre)


def luminance(hexa):
    canaux = [int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canaux]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def rapport_contraste(premier_plan, arriere_plan):
    """Rapport de contraste WCAG entre deux couleurs hexadécimales (de 1 à 21)."""
    a, b = sorted((luminance(premier_plan), luminance(arriere_plan)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def lire_parametres(nom):
    """Paramètres documentés dans l'en-tête du gabarit components/<nom>.html."""
    try:
        source = get_template(f"components/{nom}.html").template.source
    except TemplateDoesNotExist:
        return []
    trouve = re.search(r"\{% comment %\}(.*?)\{% endcomment %\}", source, re.S)
    if trouve is None:
        return []
    commentaire = trouve.group(1)
    parametres = []
    dans_bloc = False
    for ligne in commentaire.splitlines():
        if ligne.startswith("Paramètres"):
            dans_bloc = True
            continue
        if not dans_bloc:
            continue
        if ligne and not ligne.startswith(" "):
            break
        m = re.match(r"^  ([\w, ]+?)\s*:\s*(.*)$", ligne)
        if m:
            parametres.append([m.group(1), m.group(2)])
        elif ligne.strip() and parametres:
            parametres[-1][1] += " " + ligne.strip()
    return parametres


def tableau_contrastes():
    clair, sombre = variables_css()
    lignes = []
    for usage, premier, arriere, seuil in PAIRES_CONTRASTE:
        if any(nom not in couleurs for couleurs in (clair, sombre) for nom in (premier, arriere)):
            continue  # variable renommée : on saute la ligne plutôt que de casser la page
        ratios = []
        for couleurs in (clair, sombre):
            r = rapport_contraste(couleurs[premier], couleurs[arriere])
            ratios.append({"valeur": f"{r:.2f}".replace(".", ",") + ":1", "conforme": r >= seuil})
        lignes.append({
            "usage": usage, "premier": premier, "arriere": arriere,
            "seuil": f"{seuil:g}".replace(".", ",") + ":1", "clair": ratios[0], "sombre": ratios[1],
        })
    return lignes


def preparer_composants():
    moteur = engines["django"]
    composants = []
    for composant in COMPOSANTS:
        contexte = {
            "etapes": ETAPES, "colonnes": COLONNES_GRILLE, "lignes": LIGNES_GRILLE, "lignes_erreur": LIGNES_GRILLE_ERREUR,
            "indicateurs": INDICATEURS_FICHE, "action": ACTION_FICHE, "menu": MENU_FICHE, "objet": OBJET_FICHE,
            "commentaires": [], "csrf_token": "exemple",
            "version": {"publiee_le": datetime(2026, 9, 12), "proposition_par": "SM Durand", "proposition_le": datetime(2026, 10, 1)},
        }
        exemples = [
            dict(e, rendu=moteur.from_string("{% load composants icones %}" + e["code"]).render(contexte))
            for e in composant["exemples"]
        ]
        parametres = lire_parametres(composant["nom"])
        if composant.get("gabarit_extra"):
            parametres += [[f"{composant['gabarit_extra']} : {nom}", d] for nom, d in lire_parametres(composant["gabarit_extra"])]
        composants.append(dict(composant, exemples=exemples, parametres=parametres))
    return composants


class StyleguideView(LoginRequiredMixin, TemplateView):
    """Styleguide : administrateurs uniquement (403 pour un rôle inférieur)."""

    template_name = "styleguide/index.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and user_role_level(request.user) < RoleLevel.ADMIN_NAVIRE:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        clair, sombre = variables_css()
        groupes = [
            {"titre": titre, "couleurs": [
                {"nom": nom, "role": role, "clair": clair[nom], "sombre": sombre[nom]}
                for nom, role in couleurs if nom in clair and nom in sombre
            ]}
            for titre, couleurs in COULEURS
        ]
        return super().get_context_data(
            composants=preparer_composants(), groupes_couleurs=groupes, contrastes=tableau_contrastes(),
            icones=sorted(ICONES.items()), polices=POLICES, espacements=ESPACEMENTS, **kwargs,
        )
