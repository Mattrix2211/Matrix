// Aide progressive : une explication détaillée s'ouvre à la première visite et dès que le contexte
// d'autorisation change (équipage, rôle), puis reste repliée une fois fermée ; elle se rouvre à tout moment.
// L'état d'ouverture initial vient du serveur ; seule la bascule est enregistrée (profil du marin).
// Sans JavaScript, <details> fonctionne tel quel.
(function () {
  document.querySelectorAll('details[data-aide]').forEach(function (aide) {
    var etat = aide.open;
    aide.addEventListener('toggle', function () {
      if (aide.open === etat) return; // l'événement peut partir au chargement : rien à enregistrer
      etat = aide.open;
      window.mxPreference('aides_vues', aide.dataset.aide, etat ? '' : aide.dataset.signature);
    });
  });
})();
