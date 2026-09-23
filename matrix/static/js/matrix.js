// Aides globales HTMX et UI.

// Jeton CSRF automatique sur toutes les requêtes htmx (hx-post/hx-put/hx-patch/hx-delete) :
// sans ce listener, chaque formulaire htmx devrait porter son propre {% csrf_token %} et
// serait de toute façon inopérant pour un hx-post porté par un simple bouton (hors <form>).
// Django refuse alors la requête (403) même si la logique métier de la vue est correcte —
// ce correctif couvre tous les formulaires/boutons htmx du site, présents et futurs, en un
// seul endroit plutôt qu'au cas par cas dans chaque template.
(function () {
  function getCookie(name) {
    var value = '; ' + document.cookie;
    var parts = value.split('; ' + name + '=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  }
  document.body.addEventListener('htmx:configRequest', function (evt) {
    if (evt.detail.verb !== 'get') {
      evt.detail.headers['X-CSRFToken'] = getCookie('csrftoken');
    }
  });
})();
