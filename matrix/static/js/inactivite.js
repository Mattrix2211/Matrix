// Déconnexion automatique après inactivité (docs/UX.md §2.3) — JS vanille.
// Aucun délai ici : ils viennent du serveur (data-delai et data-avertissement, en secondes, sur
// #mx-inactivite). Le serveur reste l'autorité ; ce script prévient, prolonge et enregistre les brouillons.
(function () {
  'use strict';

  // ---- Logique pure (testée avec node : tests/inactivite.test.js) ----

  // Phase selon l'heure du dernier renouvellement serveur : « actif », « avertissement » ou « expire ».
  function phase(maintenant, dernier, delai, avertissement) {
    var reste = dernier + delai - maintenant;
    if (reste <= 0) return 'expire';
    return reste <= avertissement ? 'avertissement' : 'actif';
  }

  // Secondes affichées au compte à rebours (arrondi au-dessus, jamais négatif).
  function secondesRestantes(maintenant, dernier, delai) {
    return Math.max(0, Math.ceil((dernier + delai - maintenant) / 1000));
  }

  // Une activité ne renouvelle la session serveur qu'après la moitié du préavis : pas d'inondation.
  function renouvellementUtile(maintenant, dernier, avertissement) {
    return maintenant - dernier >= avertissement / 2;
  }

  // Au terme du délai, le serveur peut avoir été prolongé par un autre onglet : on se fie à lui.
  function serveurToujoursValide(restantMs, avertissement) {
    return restantMs > avertissement / 2;
  }

  // La session du serveur doit appartenir au marin qui a ouvert la page (cookies partagés entre onglets).
  function memeUtilisateur(page, serveur) {
    return page !== '' && page != null && String(page) === String(serveur);
  }

  var API = {
    phase: phase, secondesRestantes: secondesRestantes, memeUtilisateur: memeUtilisateur,
    renouvellementUtile: renouvellementUtile, serveurToujoursValide: serveurToujoursValide
  };
  if (typeof module !== 'undefined' && module.exports) { module.exports = API; }
  if (typeof document === 'undefined') { return; }

  // ---- DOM ----

  var racine = document.getElementById('mx-inactivite');
  if (!racine || racine.mx_inactivite || !window.bootstrap) { return; }
  racine.mx_inactivite = true;

  var delai = (parseInt(racine.getAttribute('data-delai'), 10) || 0) * 1000;
  var avertissement = (parseInt(racine.getAttribute('data-avertissement'), 10) || 0) * 1000;
  if (delai <= 0) { return; }

  var URL_SESSION = racine.getAttribute('data-url-session');
  var URL_DECONNEXION = racine.getAttribute('data-url-deconnexion');
  var UTILISATEUR = racine.getAttribute('data-utilisateur'); // identifiant du marin de la page, pas un jeton
  var CLASSE_MASQUE = 'mx-inactivite--bloque'; // cache la page derrière le dialogue
  var CLE_PARTAGE = 'mx_session_renouvelee'; // synchronise les onglets (localStorage, facultatif)

  var modale = bootstrap.Modal.getOrCreateInstance(racine);
  var compte = racine.querySelector('[data-inactivite-compte]');
  var annonce = racine.querySelector('[data-inactivite-annonce]');
  var piedAvertissement = racine.querySelector('[data-inactivite-pied-avertissement]');
  var piedBloque = racine.querySelector('[data-inactivite-pied-bloque]');
  var titre = racine.querySelector('[data-inactivite-titre]');
  var texte = racine.querySelector('[data-inactivite-texte]');
  var aide = racine.querySelector('[data-inactivite-aide]');
  var texteAvertissement = texte.innerHTML;

  var dernier = Date.now();   // dernier renouvellement connu de la session serveur
  var affiche = false;
  var bloque = false;         // déconnexion suspendue : saisie non enregistrée
  var termine = false;        // déconnexion en cours
  var autreSession = false;   // la session du serveur appartient à un autre marin
  var enCours = false;        // requête de renouvellement en cours
  var precedentFocus = null;
  var derniereAnnonce = 0;

  function csrf() {
    var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  function partager(heure) {
    try { localStorage.setItem(CLE_PARTAGE, String(heure)); } catch (e) { /* onglets alors indépendants */ }
  }
  function noter(heure) {
    dernier = heure;
    partager(heure);
  }

  function enregistrerTout() {
    return window.mx_brouillon_enregistrer_tout ? window.mx_brouillon_enregistrer_tout() : Promise.resolve(true);
  }

  function appelerSession(methode) {
    var options = { method: methode, credentials: 'same-origin', headers: { 'Accept': 'application/json', 'X-CSRFToken': csrf() } };
    if (methode === 'GET') options.headers['X-Mx-Automatique'] = '1'; // consulter n'est pas une activité
    return fetch(URL_SESSION, options);
  }

  function afficher() {
    if (affiche) return;
    affiche = true;
    precedentFocus = document.activeElement;
    modale.show();
  }
  function masquer() {
    if (!affiche) return;
    affiche = false;
    bloque = false;
    document.body.classList.remove(CLASSE_MASQUE);
    modale.hide();
    if (precedentFocus && precedentFocus.focus && document.contains(precedentFocus)) precedentFocus.focus();
  }
  racine.addEventListener('show.bs.modal', function () {
    racine.setAttribute('role', 'alertdialog'); // Bootstrap le remplace par « dialog »
  });
  racine.addEventListener('shown.bs.modal', function () {
    racine.setAttribute('role', 'alertdialog');
    var bouton = racine.querySelector(bloque ? '[data-inactivite-reessayer]' : '[data-inactivite-rester]');
    if (bouton) bouton.focus();
  });

  // Renouvelle la session serveur. En cas d'échec d'authentification, la déconnexion suit.
  function prolonger() {
    if (enCours || termine) return Promise.resolve();
    enCours = true;
    var envoi = Date.now();
    return appelerSession('POST').then(function (rep) {
      if (rep.ok) {
        return rep.json().then(function (d) {
          if (memeUtilisateur(UTILISATEUR, d.utilisateur)) { noter(envoi); masquer(); } else { montrerAutreSession(); }
        });
      }
      if (rep.status === 401 || rep.status === 403) { return terminer(); }
    }).catch(function () { /* réseau indisponible : l'échéance locale reste la référence */ })
      .then(function () { enCours = false; });
  }

  // Retour à la page quittée demandé seulement pour une déconnexion automatique ; le serveur
  // décide seul si la session a réellement expiré (message et traçabilité).
  function soumettreDeconnexion(avecRetour) {
    var formulaire = document.createElement('form');
    formulaire.method = 'post';
    formulaire.action = URL_DECONNEXION;
    [['csrfmiddlewaretoken', csrf()]].concat(avecRetour ? [['next', location.pathname + location.search]] : []).forEach(function (c) {
      var champ = document.createElement('input');
      champ.type = 'hidden'; champ.name = c[0]; champ.value = c[1];
      formulaire.appendChild(champ);
    });
    document.body.appendChild(formulaire);
    formulaire.submit();
  }

  function montrerBloque() {
    bloque = true;
    termine = false;
    document.body.classList.add(CLASSE_MASQUE);
    titre.textContent = 'Session expirée';
    texte.textContent = 'Votre session a expiré et votre saisie n’a pas pu être enregistrée.';
    aide.textContent = 'Elle reste dans cette page : reconnectez-vous dans un nouvel onglet, puis revenez ici.';
    piedAvertissement.hidden = true;
    piedBloque.hidden = false;
    afficher();
    var bouton = racine.querySelector('[data-inactivite-reessayer]');
    if (bouton) bouton.focus();
  }

  // Un autre marin a ouvert une session : la page ne doit rien lui montrer ni enregistrer pour lui.
  function montrerAutreSession() {
    autreSession = true;
    montrerBloque();
    titre.textContent = 'Autre session ouverte';
    texte.textContent = 'Une autre session est ouverte : quittez cette page.';
    aide.textContent = '';
    racine.querySelector('[data-inactivite-reessayer]').hidden = true;
    racine.querySelector('[data-inactivite-nouvel-onglet]').hidden = true;
    piedBloque.querySelector('[data-inactivite-quitter]').focus();
  }

  // Échéance atteinte : on vérifie le serveur, on enregistre les brouillons, puis on déconnecte.
  function terminer() {
    if (termine) return Promise.resolve();
    termine = true;
    afficher();
    return appelerSession('GET').then(function (rep) { return rep.ok ? rep.json() : { restant: 0 }; })
      .catch(function () { return { restant: 0 }; })
      .then(function (etat) {
        if (etat.utilisateur !== undefined && !memeUtilisateur(UTILISATEUR, etat.utilisateur)) { montrerAutreSession(); return null; }
        var restant = (etat.restant || 0) * 1000;
        if (serveurToujoursValide(restant, avertissement)) { // prolongée ailleurs
          noter(Date.now() - (delai - restant));
          termine = false;
          masquer();
          return null;
        }
        return enregistrerTout().then(function (ok) {
          if (!ok) { montrerBloque(); return; }
          // Le serveur n'expire qu'après le délai complet : on attend ce reste (plus une marge d’une seconde et demie) avant de déconnecter.
          setTimeout(function () { soumettreDeconnexion(true); }, restant + 1500);
        });
      });
  }

  function mettreAJour() {
    if (termine || bloque) return;
    var maintenant = Date.now();
    var etat = phase(maintenant, dernier, delai, avertissement);
    if (etat === 'actif') { masquer(); return; }
    if (etat === 'expire') { terminer(); return; }
    if (!affiche) {
      derniereAnnonce = 0;
      enregistrerTout(); // la session est encore valide : on met la saisie à l'abri dès le préavis
      afficher();
    }
    var secondes = secondesRestantes(maintenant, dernier, delai);
    compte.textContent = secondes;
    // Annonce vocale espacée (toutes les 10 s, puis à 5 s) pour ne pas saturer le lecteur d'écran.
    if (derniereAnnonce === 0 || (secondes <= 5 ? derniereAnnonce > secondes : derniereAnnonce - secondes >= 10)) {
      derniereAnnonce = secondes;
      annonce.textContent = 'Vous allez être déconnecté dans ' + secondes + ' secondes.';
    }
  }

  // Activité réelle : renouvelle la session serveur, au plus une fois par demi-préavis.
  function activite() {
    if (affiche || termine || bloque) return;
    if (renouvellementUtile(Date.now(), dernier, avertissement)) prolonger();
  }
  ['keydown', 'mousedown', 'mousemove', 'wheel', 'touchstart', 'scroll'].forEach(function (nom) {
    document.addEventListener(nom, activite, { passive: true, capture: true });
  });

  racine.querySelector('[data-inactivite-rester]').addEventListener('click', prolonger);
  racine.querySelectorAll('[data-inactivite-quitter]').forEach(function (b) {
    b.addEventListener('click', function () {
      termine = true;
      if (autreSession) { location.replace(racine.querySelector('[data-inactivite-nouvel-onglet]').href); return; } // ne pas déconnecter l'autre marin
      soumettreDeconnexion(piedBloque.contains(b));
    });
  });
  racine.querySelector('[data-inactivite-reessayer]').addEventListener('click', function () {
    // Session rouverte ailleurs : on la renouvelle ici, puis on remet la saisie à l'abri.
    // On vérifie d'abord (sans prolonger) que la session rouverte est bien celle du marin de la page.
    appelerSession('GET').then(function (rep) {
      if (!rep.ok) return null;
      return rep.json().then(function (d) {
        if (!memeUtilisateur(UTILISATEUR, d.utilisateur)) { montrerAutreSession(); return null; }
        return appelerSession('POST').then(function (r) { return r.ok ? noter(Date.now()) || true : null; });
      });
    }).then(function (reouverte) {
      if (!reouverte) return;
      return enregistrerTout().then(function (ok) {
        if (!ok) return;
        document.body.classList.remove(CLASSE_MASQUE);
        titre.textContent = 'Inactivité détectée';
        texte.innerHTML = texteAvertissement;
        compte = racine.querySelector('[data-inactivite-compte]');
        aide.textContent = 'Votre saisie en cours est enregistrée en brouillon.';
        piedAvertissement.hidden = false;
        piedBloque.hidden = true;
        masquer();
      });
    }).catch(function () { /* réseau indisponible : l'utilisateur peut réessayer */ });
  });

  // Autre onglet : un renouvellement plus récent prolonge celui-ci.
  window.addEventListener('storage', function (evt) {
    var heure = evt.key === CLE_PARTAGE ? parseInt(evt.newValue, 10) : 0;
    if (heure > dernier && !termine && !bloque) { dernier = heure; mettreAJour(); }
  });
  document.addEventListener('visibilitychange', function () { if (!document.hidden) mettreAJour(); });
  window.addEventListener('pageshow', function (evt) { if (evt.persisted) mettreAJour(); });

  partager(dernier);
  setInterval(mettreAJour, 1000);
})();
