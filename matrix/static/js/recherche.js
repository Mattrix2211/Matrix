// Recherche rapide de la barre supérieure (docs/UX.md §21) : raccourcis « / » et
// Ctrl+K, panneau de résultats (htmx), navigation au clavier. Sans JavaScript,
// Entrée envoie le formulaire vers la page de recherche complète.
(function () {
  var racine = document.querySelector('[data-recherche]');
  if (!racine) return;
  var champ = racine.querySelector('input[name="q"]');
  var panneau = document.getElementById('recherche-panneau');
  var annonce = racine.querySelector('[data-recherche-annonce]');
  var MIN = 2;
  var actif = -1;

  function options() {
    return Array.prototype.slice.call(panneau.querySelectorAll('[role="option"]'));
  }

  function choisir(index) {
    var liste = options();
    liste.forEach(function (o) { o.classList.remove('is-actif'); o.removeAttribute('aria-selected'); });
    actif = liste.length ? (index + liste.length) % liste.length : -1;
    if (actif < 0) { champ.removeAttribute('aria-activedescendant'); return; }
    var option = liste[actif];
    if (!option.id) option.id = 'recherche-option-' + actif;
    option.classList.add('is-actif');
    option.setAttribute('aria-selected', 'true');
    champ.setAttribute('aria-activedescendant', option.id);
    option.scrollIntoView({ block: 'nearest' });
  }

  function ouvrir() {
    panneau.hidden = false;
    champ.setAttribute('aria-expanded', 'true');
  }

  function fermer() {
    panneau.hidden = true;
    champ.setAttribute('aria-expanded', 'false');
    champ.removeAttribute('aria-activedescendant');
    actif = -1;
  }

  // Le raccourci ne doit jamais voler la frappe : champ de saisie, grille ou fenêtre ouverte.
  function dansZoneDeSaisie(cible) {
    return !!(cible && cible.closest && (cible.isContentEditable ||
      cible.closest('input, textarea, select, [contenteditable="true"], [data-grille], .modal, .offcanvas.show')));
  }

  document.addEventListener('keydown', function (evt) {
    var raccourci = (evt.key === '/' && !evt.ctrlKey && !evt.metaKey && !evt.altKey) ||
      ((evt.key === 'k' || evt.key === 'K') && evt.ctrlKey && !evt.metaKey && !evt.altKey);
    if (!raccourci || dansZoneDeSaisie(evt.target)) return;
    evt.preventDefault();
    champ.focus();
    champ.select();
  });

  champ.addEventListener('keydown', function (evt) {
    var liste = options();
    if (evt.key === 'Escape') {
      if (panneau.hidden) champ.blur(); else fermer();
      evt.preventDefault();
    } else if (evt.key === 'ArrowDown' || evt.key === 'ArrowUp') {
      if (!liste.length) return;
      evt.preventDefault();
      ouvrir();
      choisir(actif < 0 ? (evt.key === 'ArrowDown' ? 0 : -1) : actif + (evt.key === 'ArrowDown' ? 1 : -1));
    } else if (evt.key === 'Enter' && actif >= 0 && !panneau.hidden) {
      evt.preventDefault();
      liste[actif].click();
    }
  });

  // Moins de 2 caractères : pas de requête, panneau fermé.
  champ.addEventListener('htmx:configRequest', function (evt) {
    if (champ.value.trim().length < MIN) {
      evt.preventDefault();
      panneau.innerHTML = '';
      fermer();
      annonce.textContent = '';
    }
  });

  panneau.addEventListener('htmx:afterSwap', function () {
    var contenu = panneau.querySelector('[data-nombre]');
    var nombre = contenu ? parseInt(contenu.getAttribute('data-nombre'), 10) : 0;
    actif = -1;
    champ.removeAttribute('aria-activedescendant');
    ouvrir();
    annonce.textContent = nombre === 0 ? 'Aucun résultat.' :
      nombre + (nombre > 1 ? ' résultats disponibles.' : ' résultat disponible.');
  });

  // Un clic dans le panneau ne retire pas le focus du champ.
  panneau.addEventListener('mousedown', function (evt) { evt.preventDefault(); });

  // Fermeture quand le focus ou le clic sort de la recherche.
  racine.addEventListener('focusout', function (evt) {
    if (!evt.relatedTarget || !racine.contains(evt.relatedTarget)) fermer();
  });
  champ.addEventListener('focus', function () {
    if (panneau.children.length && champ.value.trim().length >= MIN) ouvrir();
  });
  document.addEventListener('click', function (evt) {
    if (!racine.contains(evt.target)) fermer();
  });
})();
