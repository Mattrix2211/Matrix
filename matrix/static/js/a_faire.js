// Carte « À faire » : bascule de la section « Autres actions » (aperçu, repliée, développée) et accessibilité
// de la zone défilante. L'état développé n'est pas mémorisé. Sans JavaScript, toutes les actions restent visibles.
(function () {
  var carte = document.querySelector('[data-afaire]');
  if (!carte) return;
  var zone = carte.querySelector('[data-afaire-zone]');
  var bouton = carte.querySelector('[data-afaire-bascule]');
  var annonce = carte.querySelector('[data-afaire-annonce]');
  var initial = carte.dataset.initial;
  var total = zone ? zone.querySelectorAll('.mx-afaire__ligne').length : 0;
  var grandEcran = window.matchMedia('(min-width: 768px)');

  // Zone défilante : nommée et focalisable seulement quand elle défile réellement (PC, section en aperçu).
  function ajusterZone() {
    if (!zone) return;
    var defile = grandEcran.matches && !carte.classList.contains('mx-afaire--ouvert') && !carte.classList.contains('mx-afaire--replie')
      && zone.scrollHeight > zone.clientHeight + 1;
    zone.setAttribute('aria-label', defile ? 'Autres actions, zone défilante' : 'Autres actions');
    if (defile) zone.setAttribute('tabindex', '0'); else zone.removeAttribute('tabindex');
  }

  if (bouton) {
    bouton.addEventListener('click', function () {
      var ouvert = carte.classList.toggle('mx-afaire--ouvert');
      carte.classList.toggle('mx-afaire--replie', !ouvert && initial === 'replie');
      bouton.setAttribute('aria-expanded', ouvert ? 'true' : 'false');
      bouton.textContent = ouvert ? bouton.dataset.libelleOuvert : (initial === 'replie' ? bouton.dataset.libelleReplie : bouton.dataset.libelleApercu);
      if (annonce) {
        annonce.textContent = ouvert ? 'Les ' + total + ' autres actions sont affichées.'
          : initial === 'replie' ? 'Les autres actions sont repliées.' : 'Liste réduite : les autres actions restent dans la section.';
      }
      ajusterZone();
    });
  }
  if (grandEcran.addEventListener) grandEcran.addEventListener('change', ajusterZone);
  window.addEventListener('resize', ajusterZone);
  ajusterZone();
})();
