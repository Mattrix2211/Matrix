// Compte rendu de maintenance : contrôles immédiats, « Tout conforme », résumé et saisie au clavier.
// Activation : <form data-compte-rendu>. Lignes : [data-ligne] (data-type, data-min, data-max).
(function () {
  'use strict';

  // ---- Logique pure (testée avec node : tests/compte_rendu.test.js) ----

  // Nombre saisi avec virgule ou point ; null si vide, NaN si illisible.
  function lireNombre(texte) {
    var brut = String(texte || '').replace(/[\s ]/g, '').replace(',', '.');
    return brut === '' ? null : Number(brut);
  }

  function horsPlage(valeur, min, max) {
    if (valeur === null || isNaN(valeur)) return false;
    return (min !== null && valeur < min) || (max !== null && valeur > max);
  }

  // Conformité proposée : non conforme > à surveiller > conforme.
  function conformiteProposee(nonConformes, aSurveiller) {
    return nonConformes ? 'NON_CONFORME' : (aSurveiller ? 'A_SURVEILLER' : 'CONFORME');
  }

  function pluriel(n, mot) { return n + ' ' + mot + (n > 1 ? 's' : ''); }

  function resume(controles, faits, nonConformes, aSurveiller) {
    var parties = [];
    if (controles) parties.push(faits + '/' + controles + ' contrôles');
    if (nonConformes) parties.push(pluriel(nonConformes, 'non conforme'));
    if (aSurveiller) parties.push(pluriel(aSurveiller, 'relevé') + ' à surveiller');
    return parties.join(', ') || 'Aucun point à contrôler';
  }

  // Durée entre deux dates (millisecondes) en « 1 h 05 » ; vide si invalide.
  function formaterDuree(ms) {
    if (!(ms > 0)) return '';
    var minutes = Math.round(ms / 60000);
    var h = Math.floor(minutes / 60), m = minutes % 60;
    return h ? h + ' h ' + (m < 10 ? '0' : '') + m : m + ' min';
  }

  var API = { lireNombre: lireNombre, horsPlage: horsPlage, conformiteProposee: conformiteProposee, resume: resume, formaterDuree: formaterDuree };
  if (typeof module !== 'undefined' && module.exports) { module.exports = API; }
  if (typeof document === 'undefined') { return; }

  // ---- DOM ----

  function borne(valeur) { return valeur === '' || valeur === null ? null : Number(valeur); }

  function demarrer(form) {
    var lignes = Array.prototype.slice.call(form.querySelectorAll('[data-ligne]'));
    var conformite = form.querySelector('[name=conformity]');
    var motDePasse = form.querySelector('[data-signature]');
    var duree = form.querySelector('[data-duree]');
    var debut = form.querySelector('[name=debut]');
    var fin = form.querySelector('[name=fin]');
    var barre = document.querySelector('[data-barre-resume]');
    var operations = document.querySelector('[data-barre-operations]');
    var critique = form.hasAttribute('data-critique');
    var conformiteManuelle = !!(conformite && conformite.value);

    function evaluer() {
      var controles = 0, faits = 0, nonConformes = 0, aSurveiller = 0, realises = 0;
      lignes.forEach(function (ligne) {
        var type = ligne.getAttribute('data-type');
        if (type === 'checkbox') {
          controles++;
          var coche = ligne.querySelector('input[type=radio]:checked');
          var etat = coche ? coche.value : '';
          if (etat) { faits++; realises++; }
          if (etat === 'non_conforme') nonConformes++;
          var commentaire = ligne.querySelector('[data-commentaire]');
          if (commentaire) commentaire.hidden = etat !== 'non_conforme';
        } else {
          var champ = ligne.querySelector('input');
          if (champ && champ.value.trim() !== '') realises++;
          if (type === 'number') {
            var valeur = lireNombre(champ.value);
            var sorti = horsPlage(valeur, borne(ligne.getAttribute('data-min')), borne(ligne.getAttribute('data-max')));
            var illisible = valeur !== null && isNaN(valeur);
            if (sorti) aSurveiller++;
            ligne.classList.toggle('mx-cr-ligne--hors-plage', sorti);
            champ.classList.toggle('is-invalid', sorti || illisible);
            var alerte = ligne.querySelector('[data-alerte]');
            if (alerte) alerte.hidden = !(sorti || illisible);
            if (alerte) alerte.textContent = illisible ? 'Valeur illisible' : 'Hors plage';
          }
        }
      });
      if (barre) barre.textContent = resume(controles, faits, nonConformes, aSurveiller);
      if (operations) operations.textContent = realises + ' / ' + lignes.length + ' opérations réalisées';
      if (conformite && !conformiteManuelle) conformite.value = realises ? conformiteProposee(nonConformes, aSurveiller) : '';
      // Mot de passe demandé seulement à la clôture d'une installation critique.
      if (motDePasse) motDePasse.hidden = !(critique && conformite && conformite.value && conformite.value !== 'NON_CONFORME');
      if (duree && debut && fin) {
        duree.textContent = debut.value && fin.value ? formaterDuree(new Date(fin.value) - new Date(debut.value)) : '';
      }
    }

    form.addEventListener('input', evaluer);
    form.addEventListener('change', evaluer);
    if (conformite) conformite.addEventListener('change', function () { conformiteManuelle = true; });

    var toutConforme = document.querySelector('[data-tout-conforme]');
    if (toutConforme) {
      toutConforme.addEventListener('click', function () {
        lignes.forEach(function (ligne) {
          if (ligne.getAttribute('data-type') !== 'checkbox' || ligne.querySelector('input[type=radio]:checked')) return;
          var conforme = ligne.querySelector('input[value=conforme]');
          if (conforme) conforme.checked = true;
        });
        form.dispatchEvent(new Event('change', { bubbles: true }));
      });
    }

    // Entrée passe à la ligne suivante au lieu d'envoyer le formulaire.
    form.addEventListener('keydown', function (evt) {
      var cible = evt.target;
      if (evt.key !== 'Enter' || cible.tagName === 'TEXTAREA' || cible.tagName === 'BUTTON' || cible.type === 'submit') return;
      evt.preventDefault();
      var ligne = cible.closest('[data-ligne]');
      var suivante = ligne ? lignes[lignes.indexOf(ligne) + 1] : null;
      var champ = suivante && suivante.querySelector('input:not([type=hidden]):not([hidden])');
      if (suivante && suivante.querySelector('input[type=radio]')) {
        champ = suivante.querySelector('input[type=radio]:checked') || suivante.querySelector('input[type=radio]');
      }
      if (champ) champ.focus();
    });

    evaluer();
  }

  document.querySelectorAll('form[data-compte-rendu]').forEach(demarrer);
})();
