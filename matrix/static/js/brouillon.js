// Brouillons enregistrés automatiquement côté serveur (docs/UX.md §5.4) — JS vanille.
// Activation : <form data-brouillon="formulaire:objet"> ou tout conteneur (ex. la grille).
// Attributs facultatifs : data-brouillon-libelle (texte affiché dans « Mes brouillons »),
// data-brouillon-delai (millisecondes de temporisation, 2000 par défaut),
// data-brouillon-ignorer sur un champ à ne jamais conserver.
// Serveur : matrix/core/brouillons.py (endpoint /brouillons/).
(function () {
  'use strict';

  // ---- Logique pure (testée avec node : tests/brouillon.test.js) ----

  // Même règle que le serveur : « password » et « csrf » partout, les autres mots seulement entiers
  // (« passage » et « compass » restent conservés).
  var SENSIBLE = /password|passwd|csrf|(^|[^a-z])(passe?|mdp|pwd|token|jeton|secret|signature)([^a-z]|$)/i;

  // Un champ de mot de passe, un jeton ou une signature ne sont jamais conservés.
  function nomSensible(nom) { return SENSIBLE.test(String(nom || '')); }

  // Délai avant le nouvel essai après une coupure : 5 s, 10 s, 20 s, 40 s puis 60 s.
  function delaiReessai(essai) { return Math.min(60000, 5000 * Math.pow(2, Math.max(0, essai))); }

  function deuxChiffres(n) { return (n < 10 ? '0' : '') + n; }
  function formaterHeure(date) { return deuxChiffres(date.getHours()) + ':' + deuxChiffres(date.getMinutes()); }
  function formaterDateHeure(date) {
    return deuxChiffres(date.getDate()) + '/' + deuxChiffres(date.getMonth() + 1) + ' à ' + formaterHeure(date);
  }

  // Vrai si aucun champ ne contient de saisie (rien à conserver).
  function contenuVide(contenu) {
    return Object.keys(contenu).every(function (nom) {
      var v = contenu[nom];
      return Array.isArray(v) ? v.length === 0 : v === '';
    });
  }

  var API = {
    nomSensible: nomSensible, delaiReessai: delaiReessai, formaterHeure: formaterHeure,
    formaterDateHeure: formaterDateHeure, contenuVide: contenuVide
  };
  if (typeof module !== 'undefined' && module.exports) { module.exports = API; }
  if (typeof document === 'undefined') { return; }
  if (window.mx_brouillon) { return; } // script chargé deux fois : pas de double écouteur
  window.mx_brouillon = true;

  // ---- DOM ----

  var URL_BROUILLON = '/brouillons/';
  var CLE_ENVOYES = 'mx_brouillons_envoyes';
  var TYPES_IGNORES = ['password', 'hidden', 'file', 'submit', 'button', 'reset', 'image'];

  // Stockage de session : jamais bloquant (navigation privée, quota, valeur corrompue).
  function lireEnvoyes() {
    try {
      var liste = JSON.parse(sessionStorage.getItem(CLE_ENVOYES) || '[]');
      return Array.isArray(liste) ? liste : [];
    } catch (e) { return []; }
  }
  function ecrireEnvoyes(liste) {
    try {
      if (liste.length) sessionStorage.setItem(CLE_ENVOYES, JSON.stringify(liste));
      else sessionStorage.removeItem(CLE_ENVOYES);
    } catch (e) { /* stockage indisponible : le brouillon sera simplement purgé plus tard */ }
  }

  function csrf() {
    var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    if (m) return decodeURIComponent(m[1]);
    var champ = document.querySelector('input[name=csrfmiddlewaretoken]');
    return champ ? champ.value : '';
  }

  function appeler(methode, cle, corps) {
    var options = { method: methode, credentials: 'same-origin', headers: { 'X-CSRFToken': csrf() } };
    if (corps) {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(corps);
    }
    var url = URL_BROUILLON + (methode === 'POST' ? '' : '?cle=' + encodeURIComponent(cle));
    return fetch(url, options);
  }

  function champs(conteneur) {
    return Array.prototype.filter.call(conteneur.querySelectorAll('input, select, textarea'), function (el) {
      return el.name && !el.disabled && TYPES_IGNORES.indexOf(el.type) === -1
        && !nomSensible(el.name) && !el.hasAttribute('data-brouillon-ignorer');
    });
  }

  function collecter(conteneur) {
    var contenu = {};
    champs(conteneur).forEach(function (el) {
      if (el.type === 'checkbox' || el.type === 'radio') {
        contenu[el.name] = contenu[el.name] || [];
        if (el.checked) contenu[el.name].push(el.value);
      } else if (el.multiple) {
        contenu[el.name] = Array.prototype.filter.call(el.options, function (o) { return o.selected; })
          .map(function (o) { return o.value; });
      } else {
        contenu[el.name] = el.value;
      }
    });
    return contenu;
  }

  function appliquer(conteneur, contenu) {
    champs(conteneur).forEach(function (el) {
      if (!Object.prototype.hasOwnProperty.call(contenu, el.name)) return;
      var v = contenu[el.name];
      if (el.type === 'checkbox' || el.type === 'radio') {
        el.checked = Array.isArray(v) && v.indexOf(el.value) !== -1;
      } else if (el.multiple) {
        Array.prototype.forEach.call(el.options, function (o) { o.selected = Array.isArray(v) && v.indexOf(o.value) !== -1; });
      } else if (typeof v === 'string') {
        if (el.tagName === 'SELECT' && !Array.prototype.some.call(el.options, function (o) { return o.value === v; })) return;
        el.value = v;
      }
      // La grille (marquage des cellules modifiées) et les autres scripts écoutent ces événements.
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    });
  }

  function creer(classe, role, label) {
    var el = document.createElement('div');
    el.className = classe;
    if (role) el.setAttribute('role', role);
    if (label) el.setAttribute('aria-label', label);
    return el;
  }

  function demarrer(conteneur) {
    if (conteneur.mx_brouillon) return;
    var cle = conteneur.getAttribute('data-brouillon');
    if (!cle) return;
    conteneur.mx_brouillon = true;

    var statut = creer('mx-brouillon__statut');
    statut.setAttribute('role', 'status');
    statut.setAttribute('aria-live', 'polite');
    conteneur.parentNode.insertBefore(statut, conteneur);

    var delai = parseInt(conteneur.getAttribute('data-brouillon-delai'), 10) || 2000;
    var actif = false;      // vrai une fois la question « reprendre ? » réglée
    var restauration = false;
    var envoye = false;
    var minuteur = null, relance = null, essais = 0;

    function message(texte, erreur) {
      statut.textContent = texte;
      statut.classList.toggle('mx-brouillon__statut--erreur', !!erreur);
    }

    function enregistrer() {
      clearTimeout(relance);
      relance = null;
      if (!document.contains(conteneur)) return; // conteneur retiré de la page : plus rien à enregistrer
      var contenu = collecter(conteneur);
      var requete = contenuVide(contenu)
        ? appeler('DELETE', cle)
        : appeler('POST', cle, {
          cle: cle, contenu: contenu, url: location.pathname + location.search,
          libelle: conteneur.getAttribute('data-brouillon-libelle') || document.title
        });
      requete.then(function (rep) {
        if (rep.ok) {
          essais = 0;
          return rep.json().then(function (d) {
            message(d.existe ? 'Brouillon enregistré à ' + formaterHeure(new Date(d.mis_a_jour)) : '');
          });
        }
        if (rep.status === 413) { message('Saisie trop volumineuse : brouillon non enregistré.', true); return; }
        if (rep.status === 401 || rep.status === 403) {
          message('Session expirée : brouillon non enregistré. Reconnectez-vous dans un autre onglet ; votre saisie reste dans cette page.', true);
          return;
        }
        throw new Error('serveur');
      }).catch(function () {
        // Coupure réseau ou erreur serveur : rien n'est perdu, nouvel essai automatique.
        message('Brouillon non enregistré (réseau indisponible). Nouvel essai automatique…', true);
        if (document.contains(conteneur)) relance = setTimeout(enregistrer, delaiReessai(essais++));
      });
    }

    function planifier() {
      if (!actif || restauration || envoye) return;
      clearTimeout(minuteur);
      minuteur = setTimeout(enregistrer, delai);
    }

    conteneur.addEventListener('input', planifier);
    conteneur.addEventListener('change', planifier);
    conteneur.mx_reessayer = function () { if (relance) { clearTimeout(relance); enregistrer(); } };

    var formulaire = conteneur.tagName === 'FORM' ? conteneur : conteneur.closest('form');
    if (formulaire) {
      // Écouteur en capture + setTimeout(0) : on ne retient l'envoi que si aucun autre
      // écouteur ne l'a annulé (validation côté navigateur, confirmation…).
      formulaire.addEventListener('submit', function (evt) {
        setTimeout(function () {
          if (evt.defaultPrevented) return;
          // Le brouillon n'est supprimé qu'après un envoi réussi : voir nettoyerEnvoyes().
          envoye = true;
          clearTimeout(minuteur); clearTimeout(relance);
          var liste = lireEnvoyes();
          if (liste.indexOf(cle) === -1) liste.push(cle);
          ecrireEnvoyes(liste);
        }, 0);
      }, true);
    }

    // Proposition de reprise d'un brouillon existant.
    appeler('GET', cle).then(function (rep) { return rep.ok ? rep.json() : { existe: false }; })
      .then(function (d) {
        if (!d.existe || contenuVide(d.contenu)) { actif = true; return; }
        var quand = formaterDateHeure(new Date(d.mis_a_jour));
        var bandeau = creer('mx-brouillon__reprise', 'region', 'Brouillon à reprendre');
        var texte = document.createElement('span');
        texte.textContent = 'Un brouillon de cette saisie existe (' + quand + ').';
        var reprendre = document.createElement('button');
        reprendre.type = 'button';
        reprendre.className = 'btn btn-sm btn-outline-secondary';
        reprendre.textContent = 'Reprendre le brouillon du ' + quand;
        var abandonner = document.createElement('button');
        abandonner.type = 'button';
        abandonner.className = 'btn btn-sm btn-outline-secondary';
        abandonner.textContent = 'Abandonner';
        bandeau.appendChild(texte); bandeau.appendChild(reprendre); bandeau.appendChild(abandonner);
        statut.parentNode.insertBefore(bandeau, statut);
        reprendre.addEventListener('click', function () {
          restauration = true;
          appliquer(conteneur, d.contenu);
          restauration = false;
          actif = true;
          bandeau.remove();
          message('Brouillon repris (' + quand + ').');
        });
        abandonner.addEventListener('click', function () {
          appeler('DELETE', cle).catch(function () {});
          actif = true;
          bandeau.remove();
          message('Brouillon abandonné.');
        });
      }).catch(function () { actif = true; }); // hors ligne : la saisie reste possible, l'enregistrement réessaiera
  }

  // Après l'envoi d'un formulaire : si la page suivante ne contient plus ce formulaire,
  // l'envoi a réussi (redirection) et le brouillon est supprimé. Si le formulaire est
  // réaffiché (erreurs de validation), le brouillon est conservé.
  function nettoyerEnvoyes() {
    var liste = lireEnvoyes();
    if (!liste.length) return;
    ecrireEnvoyes([]);
    liste.forEach(function (cle) {
      var present = Array.prototype.some.call(document.querySelectorAll('[data-brouillon]'),
        function (el) { return el.getAttribute('data-brouillon') === cle; });
      if (!present) appeler('DELETE', cle).catch(function () {});
    });
  }

  // Formulaires envoyés par HTMX : suppression dès la réponse réussie.
  document.addEventListener('htmx:afterRequest', function (evt) {
    var el = evt.target;
    var porteur = el && el.closest ? el.closest('[data-brouillon]') : null;
    if (porteur && evt.detail && evt.detail.successful && el.tagName === 'FORM') {
      appeler('DELETE', porteur.getAttribute('data-brouillon')).catch(function () {});
    }
  });

  // Retour du réseau : relance immédiate des enregistrements en attente (un seul écouteur).
  window.addEventListener('online', function () {
    document.querySelectorAll('[data-brouillon]').forEach(function (c) { if (c.mx_reessayer) c.mx_reessayer(); });
  });

  function initialiser(racine) {
    racine.querySelectorAll('[data-brouillon]').forEach(demarrer);
  }
  function lancer() { nettoyerEnvoyes(); initialiser(document); }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', lancer);
  } else {
    lancer();
  }
  document.addEventListener('htmx:afterSwap', function (evt) { initialiser(evt.target); });
})();
