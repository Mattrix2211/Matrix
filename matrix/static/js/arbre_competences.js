/*
 * Arbre de compétences — dessine en SVG pur les traits reliant chaque formation
 * à ses prérequis directs, en lisant leur position réelle dans le DOM, et gère
 * le panoramique clic-glisser du cadre (remplace les multiples barres de
 * défilement par un déplacement à la souris, comme sur une carte interactive).
 * Aucune bibliothèque externe (principe hors-ligne du projet) : juste du
 * JavaScript auto-hébergé.
 *
 * Les niveaux sont empilés du haut vers le bas (niveau 0 en haut) : les
 * connecteurs partent donc du bas de la carte prérequise (niveau du dessus)
 * vers le haut de la carte débloquée (niveau du dessous), pour donner la
 * lecture d'un arbre qui descend, comme dans un jeu vidéo.
 *
 * L'affichage étant réparti par catégorie puis par composante connexe (une
 * section .arbre-competences-conteneur par composante, cf.
 * training/services.py::regrouper_par_composantes_connexes), chaque section
 * a ses propres connecteurs : un prérequis d'une autre catégorie ou d'une
 * autre composante n'a pas de carte dans cette section et son trait n'est
 * donc simplement pas tracé (un badge dans la carte renvoie déjà vers sa
 * catégorie).
 */
(function () {
  function dessinerConnecteurs(conteneur) {
    var svg = conteneur.querySelector('.arbre-connecteurs');
    if (!svg) return;

    var rectConteneur = conteneur.getBoundingClientRect();
    var largeur = conteneur.scrollWidth;
    var hauteur = conteneur.scrollHeight;
    svg.setAttribute('width', largeur);
    svg.setAttribute('height', hauteur);
    svg.setAttribute('viewBox', '0 0 ' + largeur + ' ' + hauteur);
    svg.innerHTML = '';

    var cartesParId = {};
    conteneur.querySelectorAll('.formation-card').forEach(function (carte) {
      cartesParId[carte.getAttribute('data-course-id')] = carte;
    });

    conteneur.querySelectorAll('.formation-card').forEach(function (cible) {
      var prerequisBruts = cible.getAttribute('data-prerequisites') || '';
      var prerequis = prerequisBruts.split(',').filter(Boolean);
      if (!prerequis.length) return;

      var rectCible = cible.getBoundingClientRect();
      // Point d'arrivée : haut-centre de la carte débloquée.
      var xCible = rectCible.left - rectConteneur.left + conteneur.scrollLeft + rectCible.width / 2;
      var yCible = rectCible.top - rectConteneur.top + conteneur.scrollTop;

      prerequis.forEach(function (id) {
        var source = cartesParId[id];
        if (!source) return;
        var rectSource = source.getBoundingClientRect();
        // Point de départ : bas-centre de la carte prérequise (niveau du dessus).
        var xSource = rectSource.left - rectConteneur.left + conteneur.scrollLeft + rectSource.width / 2;
        var ySource = rectSource.bottom - rectConteneur.top + conteneur.scrollTop;
        var yMilieu = (ySource + yCible) / 2;

        var chemin = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        var d = 'M ' + xSource + ' ' + ySource +
          ' C ' + xSource + ' ' + yMilieu + ', ' + xCible + ' ' + yMilieu + ', ' + xCible + ' ' + yCible;
        chemin.setAttribute('d', d);
        // Un prérequis déjà validé colore le trait en vert (chemin débloqué),
        // sinon en gris (chemin encore fermé) — même code couleur que les cartes.
        var estValide = source.classList.contains('formation-card--valide');
        chemin.setAttribute('class', 'arbre-connecteur ' + (estValide ? 'arbre-connecteur--valide' : 'arbre-connecteur--verrouille'));
        svg.appendChild(chemin);
      });
    });
  }

  function dessinerTousLesConnecteurs() {
    document.querySelectorAll('.arbre-competences-conteneur').forEach(dessinerConnecteurs);
  }

  // Distance de tolérance (en pixels) sous laquelle un mousedown suivi d'un
  // mouseup est considéré comme un simple clic plutôt qu'un glisser — permet
  // de continuer à distinguer clic (ouverture du détail d'une formation) et
  // panoramique (déplacement de la vue), qui utilisent le même bouton souris.
  var TOLERANCE_CLIC = 4;

  function initialiserPanoramique() {
    var cadre = document.getElementById('arbre-viewport');
    if (!cadre) return;
    var contenu = cadre.querySelector('.arbre-categories');
    if (!contenu) return;

    var position = { x: 0, y: 0 };
    var enGlissement = false;
    var aGlisse = false;
    var origine = { x: 0, y: 0 };
    var positionDepart = { x: 0, y: 0 };

    function appliquerTransformation() {
      contenu.style.transform = 'translate(' + position.x + 'px, ' + position.y + 'px)';
    }

    function debuterGlissement(e) {
      if (e.button !== 0) return; // uniquement le clic gauche
      enGlissement = true;
      aGlisse = false;
      origine.x = e.clientX;
      origine.y = e.clientY;
      positionDepart.x = position.x;
      positionDepart.y = position.y;
      cadre.classList.add('arbre-viewport--glisse');
    }

    function poursuivreGlissement(e) {
      if (!enGlissement) return;
      var dx = e.clientX - origine.x;
      var dy = e.clientY - origine.y;
      if (!aGlisse && (Math.abs(dx) > TOLERANCE_CLIC || Math.abs(dy) > TOLERANCE_CLIC)) {
        aGlisse = true;
      }
      if (!aGlisse) return;
      position.x = positionDepart.x + dx;
      position.y = positionDepart.y + dy;
      appliquerTransformation();
    }

    function terminerGlissement() {
      if (!enGlissement) return;
      enGlissement = false;
      cadre.classList.remove('arbre-viewport--glisse');
    }

    cadre.addEventListener('mousedown', debuterGlissement);
    window.addEventListener('mousemove', poursuivreGlissement);
    window.addEventListener('mouseup', terminerGlissement);
    // Si le bouton est relâché hors de la fenêtre (ex. sur une autre appli),
    // on arrête proprement le panoramique plutôt que de le laisser actif.
    window.addEventListener('blur', terminerGlissement);

    // Un clic qui a en réalité servi à glisser la vue ne doit pas déclencher
    // l'action normalement associée au clic (ex. ouverture du détail d'une
    // formation) : on l'intercepte en phase de capture, avant qu'il n'atteigne
    // la carte ou tout lien.
    cadre.addEventListener('click', function (e) {
      if (aGlisse) {
        e.preventDefault();
        e.stopPropagation();
      }
    }, true);

    // Les badges « Manque : ... » renvoient vers une autre catégorie via une
    // ancre (#cat-...). Le défilement natif du navigateur ne peut plus la
    // ramener dans le cadre visible puisque le déplacement se fait désormais
    // par transform (overflow: hidden) plutôt que par défilement : on
    // recentre donc nous-mêmes la section ciblée dans le cadre.
    cadre.querySelectorAll('a[href^="#cat-"]').forEach(function (lien) {
      lien.addEventListener('click', function (e) {
        var cible = document.querySelector(lien.getAttribute('href'));
        if (!cible) return;
        e.preventDefault();
        var rectCadre = cadre.getBoundingClientRect();
        var rectCible = cible.getBoundingClientRect();
        var marge = 24;
        var dx = 0;
        var dy = 0;
        if (rectCible.left < rectCadre.left + marge) {
          dx = (rectCadre.left + marge) - rectCible.left;
        } else if (rectCible.right > rectCadre.right - marge) {
          dx = (rectCadre.right - marge) - rectCible.right;
        }
        if (rectCible.top < rectCadre.top + marge) {
          dy = (rectCadre.top + marge) - rectCible.top;
        } else if (rectCible.bottom > rectCadre.bottom - marge) {
          dy = (rectCadre.bottom - marge) - rectCible.bottom;
        }
        if (!dx && !dy) return;
        position.x += dx;
        position.y += dy;
        appliquerTransformation();
      });
    });
  }

  window.addEventListener('load', dessinerTousLesConnecteurs);
  window.addEventListener('load', initialiserPanoramique);
  window.addEventListener('resize', dessinerTousLesConnecteurs);
})();
