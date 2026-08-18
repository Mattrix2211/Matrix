/*
 * Arbre de compétences — dessine en SVG pur les traits reliant chaque formation
 * à ses prérequis directs, en lisant leur position réelle dans le DOM.
 * Aucune bibliothèque de graphe externe (principe hors-ligne du projet) : juste
 * du JavaScript auto-hébergé, recalculé au chargement et au redimensionnement.
 *
 * L'affichage étant réparti par catégorie (une section .arbre-competences-
 * conteneur par catégorie), chaque section a ses propres connecteurs : un
 * prérequis d'une autre catégorie n'a pas de carte dans cette section et son
 * trait n'est donc simplement pas tracé (un badge dans la carte renvoie déjà
 * vers sa catégorie).
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
      var xCible = rectCible.left - rectConteneur.left + conteneur.scrollLeft;
      var yCible = rectCible.top - rectConteneur.top + conteneur.scrollTop + rectCible.height / 2;

      prerequis.forEach(function (id) {
        var source = cartesParId[id];
        if (!source) return;
        var rectSource = source.getBoundingClientRect();
        var xSource = rectSource.right - rectConteneur.left + conteneur.scrollLeft;
        var ySource = rectSource.top - rectConteneur.top + conteneur.scrollTop + rectSource.height / 2;
        var xMilieu = (xSource + xCible) / 2;

        var chemin = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        var d = 'M ' + xSource + ' ' + ySource +
          ' C ' + xMilieu + ' ' + ySource + ', ' + xMilieu + ' ' + yCible + ', ' + xCible + ' ' + yCible;
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

  window.addEventListener('load', dessinerTousLesConnecteurs);
  window.addEventListener('resize', dessinerTousLesConnecteurs);
})();
