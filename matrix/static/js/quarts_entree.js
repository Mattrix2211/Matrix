// Page d'entrée des quarts : filtre « mes créneaux », volets du jour repliés sur petit écran, un seul menu ouvert.
(function () {
  var filtre = document.querySelector('[data-mx-qt-moi]');
  if (filtre) {
    filtre.addEventListener('change', function () {
      document.querySelectorAll('[data-mx-qt-ligne]').forEach(function (ligne) {
        ligne.hidden = filtre.checked && !ligne.classList.contains('mx-qt__ligne--moi');
      });
    });
  }
  if (window.matchMedia('(max-width: 860px)').matches) {
    document.querySelectorAll('details.mx-qt__jour').forEach(function (d) {
      if (!d.classList.contains('mx-qt__jour--aujourdhui')) d.removeAttribute('open');
    });
  }
  document.addEventListener('click', function (e) {
    document.querySelectorAll('details.mx-qt__menu[open]').forEach(function (d) { if (!d.contains(e.target)) d.removeAttribute('open'); });
  });
})();
