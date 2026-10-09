// Sélection multiple des listes (matériels, installations) : la barre d'actions
// n'apparaît qu'après sélection ; les modales groupées reçoivent les identifiants cochés.
document.addEventListener('DOMContentLoaded', function () {
  var barre = document.getElementById('barreSelection');
  if (!barre) return;
  var nombre = document.getElementById('barreSelectionNombre');
  var tout = document.getElementById('selectAll');
  var vider = document.getElementById('barreSelectionVider');

  function cochees() { return document.querySelectorAll('.row-select:checked'); }
  function visibles() {
    return Array.prototype.filter.call(document.querySelectorAll('.row-select'), function (c) {
      var bloc = c.closest('[data-selectionnable]');
      return !bloc || bloc.style.display !== 'none';
    });
  }
  function majBarre() {
    var n = cochees().length;
    barre.classList.toggle('d-none', n === 0);
    nombre.textContent = n + ' ' + (n > 1 ? barre.dataset.pluriel : barre.dataset.singulier);
  }
  document.querySelectorAll('.row-select').forEach(function (c) { c.addEventListener('change', majBarre); });
  if (tout) {
    tout.addEventListener('change', function () {
      visibles().forEach(function (c) { c.checked = tout.checked; });
      majBarre();
    });
  }
  if (vider) {
    vider.addEventListener('click', function () {
      document.querySelectorAll('.row-select').forEach(function (c) { c.checked = false; });
      if (tout) tout.checked = false;
      majBarre();
    });
  }

  function champCache(form, nom, valeur) {
    var champ = document.createElement('input');
    champ.type = 'hidden'; champ.name = nom; champ.value = valeur;
    form.appendChild(champ);
  }
  function nettoyer(form) {
    form.querySelectorAll('input[name="selected_ids"], input[name="pk"]').forEach(function (el) { el.remove(); });
  }

  // Modale de modification groupée : un seul champ actif, les autres ne sont pas envoyés
  var modaleGroupee = document.getElementById('bulkModal');
  if (modaleGroupee) {
    modaleGroupee.addEventListener('show.bs.modal', function (e) {
      var cible = e.relatedTarget.dataset.bulk;
      document.getElementById('bulkTitre').textContent = e.relatedTarget.dataset.titre + ' (sélection)';
      document.getElementById('bulkAction').value = 'bulk_update_' + cible;
      modaleGroupee.querySelectorAll('[data-groupe]').forEach(function (g) {
        var actif = g.dataset.groupe === cible;
        g.classList.toggle('d-none', !actif);
        g.querySelector('select').disabled = !actif;
      });
      var form = document.getElementById('bulkForm');
      nettoyer(form);
      cochees().forEach(function (c) { champCache(form, 'selected_ids', c.value); });
    });
  }

  // Confirmation : suppression groupée (data-selection) ou d'un seul élément (data-pk)
  var confirmation = document.getElementById('bulkConfirmModal');
  if (confirmation) {
    confirmation.addEventListener('show.bs.modal', function (e) {
      var declencheur = e.relatedTarget.dataset;
      var form = document.getElementById('bulkConfirmForm');
      document.getElementById('bulkConfirmAction').value = declencheur.action || '';
      document.getElementById('bulkConfirmLabel').textContent = declencheur.label || 'Confirmer l\'action ?';
      nettoyer(form);
      if (declencheur.pk) champCache(form, 'pk', declencheur.pk);
      else cochees().forEach(function (c) { champCache(form, 'selected_ids', c.value); });
    });
  }

  majBarre();
});
