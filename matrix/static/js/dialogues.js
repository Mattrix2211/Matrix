// Confirmation intégrée : un seul dialogue, déclaré par attributs sur le formulaire (voir
// components/dialogue_confirmation.html). Annuler ou Échap ne soumet rien et rend le focus au déclencheur.
(function () {
  var racine = document.getElementById('dialogue-confirmation');
  if (!racine || !window.bootstrap) return;
  var dialogue = bootstrap.Modal.getOrCreateInstance(racine);
  var titre = document.getElementById('dialogue-confirmation-titre');
  var message = document.getElementById('dialogue-confirmation-message');
  var objet = document.getElementById('dialogue-confirmation-objet');
  var zoneMotif = document.getElementById('dialogue-confirmation-motif-zone');
  var motif = document.getElementById('dialogue-confirmation-motif');
  var valider = document.getElementById('dialogue-confirmation-valider');
  var annuler = document.getElementById('dialogue-confirmation-annuler');
  var enAttente = null;

  function ouvrir(formulaire, declencheur) {
    var d = formulaire.dataset;
    var destructif = d.mxConfirmer === 'destructif';
    titre.textContent = d.mxTitre || 'Confirmer cette action ?';
    message.textContent = d.mxMessage || '';
    message.hidden = !d.mxMessage;
    objet.textContent = d.mxObjet || '';
    objet.hidden = !d.mxObjet;
    zoneMotif.hidden = d.mxMotif !== 'obligatoire';
    motif.value = '';
    motif.classList.remove('is-invalid');
    valider.textContent = d.mxAction || 'Confirmer';
    valider.className = 'btn ' + (destructif ? 'btn-danger' : 'btn-primary');
    enAttente = { formulaire: formulaire, declencheur: declencheur };
    dialogue.show();
  }

  // Focus initial : le motif s'il est demandé, « Annuler » pour une suppression, sinon l'action.
  racine.addEventListener('shown.bs.modal', function () {
    if (!zoneMotif.hidden) motif.focus();
    else if (enAttente && enAttente.formulaire.dataset.mxConfirmer === 'destructif') annuler.focus();
    else valider.focus();
  });
  racine.addEventListener('hidden.bs.modal', function () {
    if (enAttente && enAttente.declencheur && enAttente.declencheur.focus) enAttente.declencheur.focus();
    enAttente = null;
  });

  valider.addEventListener('click', function () {
    if (!enAttente) return;
    var formulaire = enAttente.formulaire;
    if (!zoneMotif.hidden) {
      if (!motif.value.trim()) { motif.classList.add('is-invalid'); motif.focus(); return; }
      var champ = formulaire.querySelector('input[name="motif"]');
      if (!champ) {
        champ = document.createElement('input');
        champ.type = 'hidden';
        champ.name = 'motif';
        formulaire.appendChild(champ);
      }
      champ.value = motif.value.trim();
    }
    formulaire.dataset.mxConfirme = '1';
    var declencheur = enAttente.declencheur;
    enAttente = null;
    dialogue.hide();
    if (formulaire.requestSubmit) formulaire.requestSubmit(declencheur && declencheur.form === formulaire ? declencheur : undefined);
    else formulaire.submit();
  });

  document.addEventListener('submit', function (evt) {
    var formulaire = evt.target;
    if (!formulaire.matches || !formulaire.matches('form[data-mx-confirmer]')) return;
    if (formulaire.dataset.mxConfirme) { delete formulaire.dataset.mxConfirme; return; }
    evt.preventDefault();
    evt.stopImmediatePropagation();
    ouvrir(formulaire, evt.submitter || document.activeElement);
  }, true);
})();
