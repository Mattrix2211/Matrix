// Couleurs du thème (clair / sombre) pour les graphiques Chart.js.
// Les couleurs viennent des variables CSS de matrix.css : aucune couleur en dur
// dans les templates, et le mode sombre s'applique aux graphiques comme au reste.
(function () {
  window.matrixCouleur = function (variable) {
    return getComputedStyle(document.documentElement).getPropertyValue(variable).trim();
  };
  if (window.Chart) {
    Chart.defaults.color = window.matrixCouleur('--text-sec');
    Chart.defaults.borderColor = window.matrixCouleur('--border');
  }
})();
