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

// Popovers des indicateurs (composant « Metric », docs/UX.md §12) : activés
// par l'attribut data-bs-toggle="popover", y compris après un échange htmx.
(function () {
  function activerPopovers(racine) {
    if (!window.bootstrap) return;
    racine.querySelectorAll('[data-bs-toggle="popover"]').forEach(function (el) {
      bootstrap.Popover.getOrCreateInstance(el);
    });
  }
  document.addEventListener('DOMContentLoaded', function () { activerPopovers(document); });
  document.body.addEventListener('htmx:afterSwap', function (evt) { activerPopovers(evt.target); });
})();

// Échap ferme les popovers ouverts (la modale, le panneau latéral et le menu
// « ⋯ » se ferment déjà seuls avec Échap grâce à Bootstrap).
document.addEventListener('keydown', function (evt) {
  if (evt.key !== 'Escape' || !window.bootstrap) return;
  document.querySelectorAll('[data-bs-toggle="popover"]').forEach(function (el) {
    var popover = bootstrap.Popover.getInstance(el);
    if (popover) popover.hide();
  });
});

// Centre de notifications : après « Marquer comme lu », le bouton cliqué disparaît
// et le focus se perd ; on le rend au panneau pour que Échap le ferme toujours.
document.body.addEventListener('htmx:afterSwap', function (evt) {
  if (evt.detail.target && evt.detail.target.id === 'notif-liste' && document.activeElement === document.body) {
    document.getElementById('centre-notifications').focus();
  }
});
