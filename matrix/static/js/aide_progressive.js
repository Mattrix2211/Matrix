// Aide progressive : une explication détaillée s'ouvre à la première visite, puis reste
// repliée une fois fermée par l'utilisateur ; elle se rouvre à tout moment. Préférence
// mémorisée dans ce navigateur, par compte connecté (prototype : la cible reste une
// persistance côté serveur) ; sans JavaScript, <details> fonctionne tel quel.
(function () {
  var utilisateur = document.body.dataset.utilisateur || 'anonyme';
  function lire(cle) { try { return window.localStorage.getItem(cle); } catch (e) { return null; } }
  function ecrire(cle, valeur) { try { window.localStorage.setItem(cle, valeur); } catch (e) { /* stockage indisponible */ } }
  document.querySelectorAll('details[data-aide]').forEach(function (aide) {
    var cle = 'mx-aide-' + utilisateur + '-' + aide.dataset.aide;
    aide.open = lire(cle) !== 'vu';
    aide.addEventListener('toggle', function () { ecrire(cle, aide.open ? 'ouvert' : 'vu'); });
  });
})();
