// Barre latérale : replier / déplier sans recharger la page, état mémorisé dans le
// profil du marin. Sans JavaScript, le formulaire fonctionne tel quel (rechargement).
(function () {
  var form = document.querySelector('[data-barre-laterale-bascule]');
  var barre = document.getElementById('barre-laterale');
  if (!form || !barre) return;
  var bouton = form.querySelector('button');
  var champ = form.querySelector('input[name="repliee"]');
  var libelle = form.querySelector('.mx-lateral__libelle');
  var icone = form.querySelector('.mx-lateral__icone');

  function afficher(replie) {
    barre.classList.toggle('mx-lateral--repliee', replie);
    var texte = replie ? 'Déplier le menu' : 'Replier le menu';
    bouton.setAttribute('aria-expanded', replie ? 'false' : 'true');
    bouton.title = texte;
    libelle.textContent = texte;
    icone.className = 'bi ' + (replie ? 'bi-chevron-bar-right' : 'bi-chevron-bar-left') + ' mx-lateral__icone';
    champ.value = replie ? '0' : '1';
  }

  // Message discret quand l'état n'a pas pu être enregistré.
  function avertir() {
    var message = document.createElement('div');
    message.className = 'small text-danger px-2 pt-1';
    message.setAttribute('role', 'alert');
    message.textContent = 'Préférence non enregistrée.';
    form.appendChild(message);
    setTimeout(function () { message.remove(); }, 4000);
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var replier = champ.value === '1';
    var envoye = new FormData(form);
    afficher(replier);
    fetch(form.action, { method: 'POST', body: envoye, headers: { 'X-Requested-With': 'fetch' }, credentials: 'same-origin' })
      .then(function (reponse) { if (!reponse.ok) throw new Error(); })
      .catch(function () { afficher(!replier); avertir(); });
  });
})();
