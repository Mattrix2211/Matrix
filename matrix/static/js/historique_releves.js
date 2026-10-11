/* Courbes de tendance des relevés d'un équipement (Chart.js local) : données lues dans le JSON de la page. */
(function () {
  if (!window.Chart) return;
  document.querySelectorAll('canvas[data-serie]').forEach(function (canvas) {
    var source = document.getElementById(canvas.getAttribute('data-serie'));
    if (!source) return;
    var donnees = JSON.parse(source.textContent);
    var jeux = [{
      label: donnees.libelle + (donnees.unite ? ' (' + donnees.unite + ')' : ''),
      data: donnees.valeurs, borderColor: matrixCouleur('--signal-ui'), backgroundColor: matrixCouleur('--signal') + '1F',
      tension: 0.1, pointRadius: 3, pointHoverRadius: 5, fill: true
    }];
    [['mini', 'Minimum attendu'], ['maxi', 'Maximum attendu']].forEach(function (borne) {
      if (donnees[borne[0]] === null) return;
      jeux.push({
        label: borne[1], data: donnees.dates.map(function () { return donnees[borne[0]]; }),
        borderColor: matrixCouleur('--red'), borderDash: [6, 4], pointRadius: 0, fill: false
      });
    });
    new Chart(canvas.getContext('2d'), {
      type: 'line',
      data: { labels: donnees.dates, datasets: jeux },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: jeux.length > 1 } },
        scales: { x: { grid: { display: false } }, y: { grid: { color: matrixCouleur('--border') } } }
      }
    });
  });
})();
