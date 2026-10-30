// Enregistre une préférence d'interface dans le profil du marin (serveur) ; un échec réseau est sans effet visible.
window.mxPreference = function (cle, sousCle, valeur) {
  var url = document.body.dataset.preferencesUrl;
  if (!url) return;
  var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  var champ = document.querySelector('input[name=csrfmiddlewaretoken]');
  var csrf = m ? decodeURIComponent(m[1]) : (champ ? champ.value : '');
  var corps = new URLSearchParams({ cle: cle, sous_cle: sousCle, valeur: valeur });
  fetch(url, { method: 'POST', body: corps, credentials: 'same-origin', headers: { 'X-CSRFToken': csrf } }).catch(function () {});
};
