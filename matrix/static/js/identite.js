// Identité de la page sur un poste partagé : toute écriture porte le marin pour qui la page a été
// ouverte (le serveur refuse si un autre est connecté entre-temps), et une session expirée ramène à la
// connexion au lieu de laisser une requête échouer en silence. JS vanille.
(function () {
  'use strict';
  var corps = document.body;
  var utilisateur = corps && corps.getAttribute('data-utilisateur');
  if (!utilisateur) { return; }
  var SURES = /^(GET|HEAD|OPTIONS|TRACE)$/i;

  function memeOrigine(url) {
    try { return new URL(url, window.location.href).origin === window.location.origin; } catch (e) { return false; }
  }

  function versConnexion() {
    window.location.assign('/accounts/login/?expire=1&next=' + encodeURIComponent(window.location.pathname + window.location.search));
  }

  // htmx : en-tête sur toute requête qui écrit.
  document.addEventListener('htmx:configRequest', function (evt) {
    if (!SURES.test(evt.detail.verb || 'get')) { evt.detail.headers['X-Mx-Utilisateur'] = utilisateur; }
  });

  // Formulaires classiques : champ ajouté à l'envoi.
  document.addEventListener('formdata', function (evt) {
    var formulaire = evt.target;
    if (formulaire && formulaire.method && !SURES.test(formulaire.method) && !evt.formData.has('mx_utilisateur')) {
      evt.formData.append('mx_utilisateur', utilisateur);
    }
  });

  // fetch : en-tête sur les écritures de même origine ; session expirée = retour à la connexion,
  // sauf requêtes automatiques (brouillons, durée de session), qui gèrent elles-mêmes ce cas.
  var originale = window.fetch;
  if (typeof originale !== 'function') { return; }
  window.fetch = function (entree, options) {
    var url = typeof entree === 'string' ? entree : (entree && entree.url) || '';
    var methode = ((options && options.method) || (entree && entree.method) || 'GET').toUpperCase();
    var local = memeOrigine(url);
    var enTetes = new Headers((options && options.headers) || (entree && entree.headers) || {});
    if (local && !SURES.test(methode) && !enTetes.has('X-Mx-Utilisateur')) {
      enTetes.set('X-Mx-Utilisateur', utilisateur);
      options = Object.assign({}, options, { headers: enTetes });
    }
    return originale.call(this, entree, options).then(function (reponse) {
      var automatique = enTetes.has('X-Mx-Automatique');
      if (local && !automatique && (reponse.status === 401 || (reponse.redirected && /\/accounts\/login\//.test(reponse.url)))) {
        versConnexion();
      }
      return reponse;
    });
  };
})();
