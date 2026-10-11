// Couleurs du thème (clair / sombre) pour les graphiques Chart.js.
// Les couleurs viennent des variables CSS de matrix.css : aucune couleur en dur
// dans les templates, et le mode sombre s'applique aux graphiques comme au reste.
(function () {
  window.matrixCouleur = function (variable) {
    return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
  };
  // Couleur du thème avec transparence, quel que soit son format (#rgb, #rrggbb, rgb()).
  window.matrixCouleurAlpha = function (variable, alpha) {
    var c = window.matrixCouleur(variable), m;
    if ((m = /^#([0-9a-f]{3})$/i.exec(c))) c = '#' + m[1].replace(/./g, '$&$&');
    if ((m = /^#([0-9a-f]{6})$/i.exec(c))) {
      return 'rgba(' + parseInt(m[1].slice(0, 2), 16) + ',' + parseInt(m[1].slice(2, 4), 16) + ',' + parseInt(m[1].slice(4), 16) + ',' + alpha + ')';
    }
    return (m = /^rgb\(([^)]+)\)$/.exec(c)) ? 'rgba(' + m[1] + ',' + alpha + ')' : c;
  };
  if (window.Chart) {
    Chart.defaults.color = window.matrixCouleur('--text-sec');
    Chart.defaults.borderColor = window.matrixCouleur('--border');
  }
})();
