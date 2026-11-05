"""Page d'entrée « Quarts et tours de service » : vue quotidienne (A) et vue responsable (B) des maquettes validées."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from quarts.echanges import echanges_a_valider
from quarts.models import (
    AlerteActivation, CreneauQuart, CreneauServiceGarde, EchangeService, Quart, ServiceGarde, listes_de_l_equipage_q, peut_publier_liste,
)

JOURS = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
JOURS_COURTS = ("Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim")
MOIS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre")


def debut_de_semaine(valeur=None):
    """Lundi (00:00 local) de la semaine demandée (AAAA-MM-JJ), à défaut de la semaine courante."""
    jour = timezone.localdate()
    if valeur:
        try:
            jour = timezone.datetime.fromisoformat(valeur).date()
        except ValueError:
            pass
    lundi = jour - timedelta(days=jour.weekday())
    return timezone.make_aware(timezone.datetime(lundi.year, lundi.month, lundi.day))


def _libelle_jour(jour, court=False):
    if court:
        return f"{JOURS_COURTS[jour.weekday()]} {jour.day}"
    return f"{JOURS[jour.weekday()].capitalize()} {jour.day} {MOIS[jour.month - 1]}"


def _heure(creneau):
    debut, fin = timezone.localtime(creneau.debut), timezone.localtime(creneau.fin)
    duree = fin - debut
    if duree >= timedelta(hours=23):
        return "24 h" if duree == timedelta(hours=24) else f"{int(duree.total_seconds() // 3600)} h"
    return f"{debut:%H:%M}–{fin:%H:%M}{' +1' if fin.date() > debut.date() else ''}"


def _grade(marin):
    return getattr(getattr(marin, "profile", None), "grade", "") if marin else ""


def _nom(marin):
    return marin.get_full_name() or marin.username


def _ligne(creneau, liste, genre, user, peut_gerer):
    previsionnel = genre == "quai" and liste.application == ServiceGarde.APPLICATION_PREVISIONNELLE
    return {
        "creneau": creneau, "liste": liste, "genre": genre, "heure": _heure(creneau), "poste": creneau.poste,
        "marin": creneau.marin, "nom": _nom(creneau.marin) if creneau.marin else "", "grade": _grade(creneau.marin),
        "moi": creneau.marin_id == user.pk, "vide": creneau.marin_id is None, "previsionnel": previsionnel,
        "url": reverse("garde-detail" if genre == "quai" else "quart-detail", args=[liste.pk]),
        "peut_echanger": genre == "quai" and creneau.marin_id == user.pk and not previsionnel
        and liste.application != ServiceGarde.APPLICATION_TERMINEE and creneau.debut > timezone.now(),
        "peut_remplacer": peut_gerer(liste),
    }


def _creneaux(quarts, gardes, debut, fin):
    """Créneaux de la période des listes publiées données : (quarts à la mer, tours à quai)."""
    mer = CreneauQuart.objects.filter(quart__in=quarts, quart__statut="PUBLIEE", debut__lt=fin, fin__gt=debut) \
        .select_related("marin__profile", "quart")
    quai = CreneauServiceGarde.objects.filter(service_garde__in=gardes, service_garde__statut="PUBLIEE", debut__lt=fin, fin__gt=debut) \
        .exclude(service_garde__application=ServiceGarde.APPLICATION_TERMINEE).select_related("marin__profile", "service_garde")
    return list(mer.order_by("debut", "poste")), list(quai.order_by("debut", "poste"))


def _prochains_tours(user, quarts, gardes):
    """Créneaux à venir ou en cours du marin, tous types confondus, par ordre chronologique."""
    maintenant = timezone.now()
    mer = [(c.debut, "mer", c, c.quart) for c in CreneauQuart.objects.filter(
        quart__in=quarts, quart__statut="PUBLIEE", marin=user, fin__gt=maintenant).select_related("quart").order_by("debut")[:4]]
    quai = [(c.debut, "quai", c, c.service_garde) for c in CreneauServiceGarde.objects.filter(
        service_garde__in=gardes, service_garde__statut="PUBLIEE", marin=user, fin__gt=maintenant
    ).exclude(service_garde__application=ServiceGarde.APPLICATION_TERMINEE).select_related("service_garde").order_by("debut")[:4]]
    return sorted(mer + quai, key=lambda t: t[0])


def _libelle_quand(creneau):
    debut = timezone.localtime(creneau.debut)
    if debut <= timezone.localtime():
        return "En cours"
    if debut.date() == timezone.localdate():
        return f"Aujourd'hui {debut:%H:%M}"
    if debut.date() == timezone.localdate() + timedelta(days=1):
        return f"Demain {debut:%H:%M}"
    return f"{_libelle_jour(debut.date())} {debut:%H:%M}"


def _jusqua(creneau):
    fin = timezone.localtime(creneau.fin)
    return f"jusqu'à {fin:%H:%M}" if fin.date() == timezone.localdate() else f"jusqu'au {fin:%d/%m} à {fin:%H:%M}"


def _prochain_tour(user, quarts, gardes):
    tours = _prochains_tours(user, quarts, gardes)
    if not tours:
        return None
    _, genre, creneau, liste = tours[0]
    maintenant = timezone.now()
    suivants = [t for t in tours[1:] if t[0] > maintenant]
    return {
        "quand": _libelle_quand(creneau), "genre": "Quart à la mer" if genre == "mer" else "Tour à quai", "poste": creneau.poste,
        "jusqu_a": _jusqua(creneau),
        "echange_url": f"{reverse('garde-detail', args=[liste.pk])}?vue=echanges" if genre == "quai" and creneau.debut > maintenant
        and liste.application == ServiceGarde.APPLICATION_ACTIVE else "",
        "ensuite": f"{_libelle_quand(suivants[0][2])}, {suivants[0][2].poste} ({_heure(suivants[0][2])})" if suivants else None,
    }


def _a_traiter(user, gardes, peut_activer):
    elements = []
    a_repondre = EchangeService.objects.filter(cible=user, statut=EchangeService.STATUT_DEMANDE).count()
    if a_repondre:
        elements.append({"niveau": "att", "texte": f"{a_repondre} échange{'s' if a_repondre > 1 else ''} en attente de votre accord", "url": reverse("echanges-index")})
    a_valider = len(echanges_a_valider(user))
    if a_valider:
        elements.append({"niveau": "att", "texte": f"{a_valider} échange{'s' if a_valider > 1 else ''} à valider", "url": reverse("echanges-index")})
    en_cours = EchangeService.objects.filter(demandeur=user, statut__in=(EchangeService.STATUT_DEMANDE, EchangeService.STATUT_ACCEPTE)).count()
    if en_cours:
        elements.append({"niveau": "info", "texte": f"{en_cours} de vos demandes d'échange en cours", "url": reverse("echanges-index")})
    for modele, nom_url in ((ServiceGarde, "garde-detail"), (Quart, "quart-detail")):
        for liste in modele.objects.filter(statut="PROPOSEE").filter(listes_de_l_equipage_q(user)):
            if peut_publier_liste(user, liste):
                elements.append({"niveau": "att", "url": reverse(nom_url, args=[liste.pk]), "texte": f"« {liste.nom or 'Liste'} » : à publier"})
    for liste in gardes.filter(statut="PUBLIEE", application=ServiceGarde.APPLICATION_PREVISIONNELLE):
        if peut_activer(liste):
            retard = liste.prise_effet_prevue and liste.prise_effet_prevue <= timezone.now()
            elements.append({
                "niveau": "rouge" if retard else "att", "url": reverse("garde-detail", args=[liste.pk]),
                "texte": f"« {liste.nom or liste.type_service} » : {'activation attendue' if retard else 'à activer'}",
            })
    return elements


def _etat_listes(quarts, gardes, debut, fin, limite=4):
    etats = []
    for liste in list(quarts.filter(statut="PUBLIEE", date_debut__lt=fin.date(), date_fin__gte=debut.date()))[:limite]:
        etats.append({"nom": liste.nom or "Liste de quarts", "situation": "Publiée", "version": _version(liste),
                      "url": reverse("quart-detail", args=[liste.pk]), "genre": "Quarts à la mer"})
    for liste in list(gardes.filter(statut="PUBLIEE", date_debut__lt=fin.date(), date_fin__gte=debut.date()))[:limite]:
        etats.append({"nom": liste.nom or liste.type_service or "Services à quai", "situation": liste.situation_affichee,
                      "version": _version(liste), "url": reverse("garde-detail", args=[liste.pk]), "genre": "Tours à quai",
                      "previsionnelle": liste.application == ServiceGarde.APPLICATION_PREVISIONNELLE})
    return etats


def _version(liste):
    derniere = liste.versions.order_by("-numero").first()
    return derniere.numero if derniere else None


def vue_par_jour(user, quarts, gardes, debut, fin, mode, peut_gerer):
    mer, quai = _creneaux(quarts, gardes, debut, fin)
    jours = []
    aujourdhui = timezone.localdate()
    for i in range(7):
        jour = (debut + timedelta(days=i)).date()
        lignes_mer = [_ligne(c, c.quart, "mer", user, peut_gerer) for c in mer if timezone.localtime(c.debut).date() == jour]
        lignes_quai = [_ligne(c, c.service_garde, "quai", user, peut_gerer) for c in quai if timezone.localtime(c.debut).date() == jour]
        blocs = [("Quarts à la mer", lignes_mer), ("Tours à quai", lignes_quai)]
        if mode == "QUAI":
            blocs.reverse()
        jours.append({
            "date": jour, "libelle": _libelle_jour(jour), "aujourdhui": jour == aujourdhui, "blocs": blocs,
            "resume": f"{len(lignes_mer)} quart{'s' if len(lignes_mer) > 1 else ''} · {len(lignes_quai)} tour{'s' if len(lignes_quai) > 1 else ''}",
            "vide": not (lignes_mer or lignes_quai),
        })
    return jours


def vue_par_marin(user, quarts, gardes, debut, fin, peut_gerer):
    """Vue responsable : marins en lignes, jours en colonnes, postes à pourvoir en tête, charge de la semaine."""
    mer, quai = _creneaux(quarts, gardes, debut, fin)
    jours = [(debut + timedelta(days=i)).date() for i in range(7)]
    par_marin, a_pourvoir = {}, {jour: [] for jour in jours}
    for genre, creneaux in (("mer", mer), ("quai", quai)):
        for c in creneaux:
            liste = c.quart if genre == "mer" else c.service_garde
            jour = timezone.localtime(c.debut).date()
            if jour not in a_pourvoir:
                continue
            ligne = _ligne(c, liste, genre, user, peut_gerer)
            if c.marin_id is None:
                a_pourvoir[jour].append(ligne)
            else:
                par_marin.setdefault(c.marin, {j: [] for j in jours})[jour].append(ligne)
    marins = []
    for marin, cellules in par_marin.items():
        heures = sum((l["creneau"].fin - l["creneau"].debut).total_seconds() for ls in cellules.values() for l in ls) / 3600
        marins.append({"marin": marin, "nom": _nom(marin), "grade": _grade(marin), "heures": round(heures), "cellules": [cellules[j] for j in jours]})
    marins.sort(key=lambda m: (-m["heures"], m["nom"].lower()))
    moyenne = sum(m["heures"] for m in marins) / len(marins) if marins else 0
    maximum = max((m["heures"] for m in marins), default=0) or 1
    for m in marins:  # charge relative à l'équipe : aucun seuil codé en dur
        m["largeur"] = round(100 * m["heures"] / maximum)
        m["haute"] = len(marins) > 1 and m["heures"] > 1.25 * moyenne
    return {
        "jours": [{"libelle": _libelle_jour(j, court=True), "courant": j == timezone.localdate()} for j in jours],
        "a_pourvoir": [a_pourvoir[j] for j in jours], "marins": marins,
        "nb_a_pourvoir": sum(len(v) for v in a_pourvoir.values()),
        "alertes_pourvoir": [
            {"jour": _libelle_jour(j), "n": len(l), "postes": " et ".join(f"{x['poste']} {x['heure']}" for x in l[:3])}
            for j, l in a_pourvoir.items() if l
        ],
    }


def alertes_activation_ouvertes(gardes):
    return AlerteActivation.objects.filter(liste__in=gardes, fermee_le__isnull=True).count()


def contexte(user, quarts, gardes, debut, mode, peut_gerer, peut_activer, responsable, vue):
    fin = debut + timedelta(days=7)
    quarts, gardes = quarts.filter(statut="PUBLIEE"), gardes.filter(statut="PUBLIEE")
    ctx = {
        "semaine_debut": debut.date(), "semaine_fin": (fin - timedelta(days=1)).date(),
        "semaine_precedente": (debut - timedelta(days=7)).date().isoformat(), "semaine_suivante": (debut + timedelta(days=7)).date().isoformat(),
        "semaine_courante": debut.date() == debut_de_semaine().date(),
        "prochain_tour": _prochain_tour(user, quarts, gardes), "a_traiter": _a_traiter(user, gardes, peut_activer),
        "etat_listes": _etat_listes(quarts, gardes, debut, fin),
    }
    if vue == "jour":
        ctx["jours"] = vue_par_jour(user, quarts, gardes, debut, fin, mode, peut_gerer)
    elif vue == "marin" and responsable:
        ctx["grille"] = vue_par_marin(user, quarts, gardes, debut, fin, peut_gerer)
    return ctx
