# Recette visuelle

Contrôles faits au navigateur (Playwright, Chromium) sur la base de démonstration (`docs/DEMO.md`). À refaire avant chaque présentation.

## 1366×768 (poste du bord)

Compte chef de section : les 25 pages du menu latéral (Aujourd'hui, Calendrier, Matériels, Installations, Catalogue, Plan du navire, Maintenance, Tickets, Anomalies, Logistique, Tâches, Annonces, Programme, Demandes, Rondes, Quarts, Feuille de service, Absences, Formations, Postes, Documentation, RETEX, Prêt à appareiller, Flotte, Paramètres) : aucun débordement horizontal, aucune erreur console.

Parcours Formation : catalogue (cartes par catégorie, filtres, gestion de l'unité repliée), fiche formation (en-tête standard, sessions, candidature, demande de places), arbre de compétences (légende validé / disponible / verrouillé).

## 1024×768 tactile

Onze pages parcourues : zones cliquables de 44 px (règle `pointer: coarse`), rien d'essentiel au survol. Hors règle : liens dans le texte courant et barres d'événements du calendrier.

## Impression A4

Formations, quarts, feuille de service, tâches, matériels, calendrier : interface masquée, en-tête bâtiment / date / utilisateur, noir et blanc. Calendrier à la largeur de la page. À contrôler sur une impression réelle du navigateur.

## Aujourd'hui et calendrier (chef de section)

Centre des échéances : annonce à accuser, tâche bloquée à lever et demande en traitement affichées en tête de « Aujourd'hui », chacune avec son bouton « Ouvrir ». Calendrier : le filtre « Mon équipe » affiche les événements de l'équipe ; le clic sur un événement ouvre le panneau de détail avec fil de discussion.

## Non couvert

Un seul rôle parcouru en 1366×768 ; nom de bâtiment très long (info-bulle ajoutée, coupe par points de suspension). Constat sans correction : le graphique « Tickets correctifs » de la page d'accueil occupe beaucoup de hauteur.
