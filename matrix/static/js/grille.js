// Grille de saisie façon tableur (docs/UX.md §5.2) — JS vanille, sans dépendance.
// Gabarit : components/grille.html. Délégation d'événements sur le document :
// fonctionne aussi pour une grille chargée par HTMX.
(function () {
  'use strict';

  // ---- Logique pure (testée avec node : tests/grille.test.js) ----

  // Texte collé (Excel : colonnes séparées par tabulation, lignes par retour) -> tableau 2D.
  function decouperPresse(texte) {
    var lignes = String(texte).replace(/\r\n?/g, '\n').replace(/\n$/, '').split('\n');
    return lignes.map(function (ligne) { return ligne.split('\t'); });
  }

  // Position suivante pour une touche de navigation ; null si la touche ne déplace pas.
  // Les bords de la grille ne bouclent jamais : on reste sur la cellule.
  function deplacer(touche, ligne, colonne, nbLignes, nbColonnes) {
    var l = ligne, c = colonne;
    if (touche === 'ArrowUp') l -= 1;
    else if (touche === 'ArrowDown' || touche === 'Enter') l += 1;
    else if (touche === 'ArrowLeft') c -= 1;
    else if (touche === 'ArrowRight') c += 1;
    else return null;
    return {
      ligne: Math.max(0, Math.min(nbLignes - 1, l)),
      colonne: Math.max(0, Math.min(nbColonnes - 1, c))
    };
  }

  // « Tout conforme » : seules les valeurs vides passent à « conforme » ;
  // une valeur déjà saisie (non conforme, non applicable) est conservée.
  function toutConforme(valeurs) {
    return valeurs.map(function (v) { return v === '' ? 'conforme' : v; });
  }

  var API = { decouperPresse: decouperPresse, deplacer: deplacer, toutConforme: toutConforme };
  if (typeof module !== 'undefined' && module.exports) { module.exports = API; }
  if (typeof document === 'undefined') { return; }
  if (window.mx_grille) { return; } // script chargé deux fois : pas de double écouteur
  window.mx_grille = true;

  // ---- DOM ----

  function grilleDe(el) { return el && el.closest ? el.closest('[data-grille]') : null; }

  function cellules(grille) {
    return Array.prototype.map.call(grille.querySelectorAll('tbody tr'), function (tr) {
      return Array.prototype.slice.call(tr.querySelectorAll('[data-grille-champ]'));
    });
  }

  function position(grille, champ) {
    var m = cellules(grille);
    for (var l = 0; l < m.length; l++) {
      var c = m[l].indexOf(champ);
      if (c !== -1) return { ligne: l, colonne: c, matrice: m };
    }
    return null;
  }

  function fixer(champ, valeur) {
    if (champ.tagName === 'SELECT') {
      var existe = Array.prototype.some.call(champ.options, function (o) { return o.value === valeur; });
      if (!existe) return;
    }
    champ.value = valeur;
    marquer(champ);
  }

  function marquer(champ) {
    var modifiee = champ.value !== (champ.getAttribute('data-initial') || '');
    var td = champ.closest('td');
    if (td) td.classList.toggle('mx-grille__cellule--modifiee', modifiee);
    var grille = grilleDe(champ);
    if (!grille) return;
    var n = grille.querySelectorAll('.mx-grille__cellule--modifiee').length;
    var compteur = grille.querySelector('[data-grille-compteur]');
    if (compteur) {
      compteur.textContent = n === 0 ? 'Aucune modification'
        : n + (n === 1 ? ' cellule modifiée' : ' cellules modifiées');
    }
  }

  function aller(grille, ligne, colonne) {
    var m = cellules(grille);
    var cible = m[ligne] && m[ligne][colonne];
    if (!cible) return;
    cible.focus();
    if (cible.select && cible.tagName === 'INPUT') cible.select();
  }

  function recopierVersLeBas(grille, champ) {
    var p = position(grille, champ);
    if (!p) return;
    for (var l = p.ligne + 1; l < p.matrice.length; l++) {
      if (p.matrice[l][p.colonne]) fixer(p.matrice[l][p.colonne], champ.value);
    }
  }

  function appliquerToutConforme(grille) {
    var m = cellules(grille);
    if (!m.length) return;
    m[0].forEach(function (_, c) {
      if (!m[0][c].hasAttribute('data-conformite')) return;
      var colonne = m.map(function (ligne) { return ligne[c]; });
      var nouvelles = toutConforme(colonne.map(function (ch) { return ch.value; }));
      colonne.forEach(function (ch, i) { fixer(ch, nouvelles[i]); });
    });
  }

  // Valeur d'une cellule liste : on accepte la valeur ou le libellé collé.
  function valeurPourListe(champ, texte) {
    var t = texte.trim().toLowerCase();
    var trouvee = null;
    Array.prototype.forEach.call(champ.options, function (o) {
      if (o.value.toLowerCase() === t || o.text.trim().toLowerCase() === t) trouvee = o.value;
    });
    return trouvee;
  }

  function coller(grille, champ, texte) {
    var p = position(grille, champ);
    if (!p) return;
    decouperPresse(texte).forEach(function (ligne, i) {
      ligne.forEach(function (valeur, j) {
        var cible = p.matrice[p.ligne + i] && p.matrice[p.ligne + i][p.colonne + j];
        if (!cible) return;
        var v = cible.tagName === 'SELECT' ? valeurPourListe(cible, valeur) : valeur;
        if (v !== null) fixer(cible, v);
      });
    });
  }

  document.addEventListener('focusin', function (evt) {
    var champ = evt.target;
    var grille = grilleDe(champ);
    if (!grille || !champ.hasAttribute('data-grille-champ')) return;
    champ.setAttribute('data-avant', champ.value); // valeur restaurée par Échap
    grille.mx_actif = champ;
  });

  document.addEventListener('input', function (evt) {
    if (evt.target.hasAttribute && evt.target.hasAttribute('data-grille-champ')) marquer(evt.target);
  });
  document.addEventListener('change', function (evt) {
    if (evt.target.hasAttribute && evt.target.hasAttribute('data-grille-champ')) marquer(evt.target);
  });

  document.addEventListener('keydown', function (evt) {
    var champ = evt.target;
    var grille = grilleDe(champ);
    if (!grille || !champ.hasAttribute || !champ.hasAttribute('data-grille-champ')) return;

    if (evt.key === 'Escape') {
      fixer(champ, champ.getAttribute('data-avant') || '');
      return;
    }
    if ((evt.ctrlKey || evt.metaKey) && !evt.shiftKey && !evt.altKey && (evt.key === 'd' || evt.key === 'D')) {
      evt.preventDefault();
      recopierVersLeBas(grille, champ);
      return;
    }
    if (evt.ctrlKey || evt.metaKey || evt.altKey || evt.shiftKey) return;

    var horizontal = evt.key === 'ArrowLeft' || evt.key === 'ArrowRight';
    if (horizontal && champ.tagName === 'INPUT') {
      // Dans un texte, les flèches gauche/droite ne quittent la cellule qu'au bord du texte.
      var debut = champ.selectionStart, fin = champ.selectionEnd;
      var auBord = evt.key === 'ArrowLeft' ? (debut === 0 && fin === 0)
        : (debut === champ.value.length && fin === champ.value.length);
      var toutSelectionne = debut === 0 && fin === champ.value.length;
      if (!auBord && !toutSelectionne) return;
    }
    var p = position(grille, champ);
    if (!p) return;
    var cible = deplacer(evt.key, p.ligne, p.colonne, p.matrice.length, p.matrice[p.ligne].length);
    if (!cible) return;
    evt.preventDefault(); // Entrée n'envoie jamais le formulaire ; ↑/↓ ne changent pas une liste
    aller(grille, cible.ligne, cible.colonne);
  });

  document.addEventListener('paste', function (evt) {
    var champ = evt.target;
    var grille = grilleDe(champ);
    if (!grille || !champ.hasAttribute || !champ.hasAttribute('data-grille-champ')) return;
    var texte = evt.clipboardData && evt.clipboardData.getData('text');
    if (!texte || !/[\t\n\r]/.test(texte.replace(/[\r\n]+$/, ''))) return; // collage simple : comportement normal
    evt.preventDefault();
    coller(grille, champ, texte);
  });

  document.addEventListener('click', function (evt) {
    var bouton = evt.target.closest && evt.target.closest('[data-grille-action]');
    var grille = grilleDe(bouton);
    if (!bouton || !grille) return;
    if (bouton.getAttribute('data-grille-action') === 'tout-conforme') {
      appliquerToutConforme(grille);
    } else if (grille.mx_actif) {
      recopierVersLeBas(grille, grille.mx_actif);
      grille.mx_actif.focus();
    }
  });

  // Sans JavaScript, les boutons de la barre ne feraient rien : ils restent masqués.
  function afficherBarres(racine) {
    racine.querySelectorAll('[data-grille-barre][hidden]').forEach(function (b) { b.hidden = false; });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { afficherBarres(document); });
  } else {
    afficherBarres(document);
  }
  document.addEventListener('htmx:afterSwap', function (evt) { afficherBarres(evt.target); });
})();
