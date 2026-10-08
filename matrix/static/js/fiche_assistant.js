// Assistant de fiche de maintenance : étapes successives, lignes à ajouter, retirer, déplacer ou dupliquer.
(function () {
  var formulaire = document.querySelector("[data-assistant-fiche]");
  if (!formulaire) { return; }
  var panneaux = [].slice.call(formulaire.querySelectorAll("[data-etape]"));
  var frise = formulaire.querySelector("[data-frise]");
  var navigation = formulaire.querySelector("[data-navigation]");
  var precedent = formulaire.querySelector("[data-precedent]");
  var suivant = formulaire.querySelector("[data-suivant]");
  var courante = 0;

  function afficher(index) {
    courante = Math.max(0, Math.min(panneaux.length - 1, index));
    panneaux.forEach(function (p, i) { p.hidden = i !== courante; });
    [].slice.call(frise.children).forEach(function (li, i) {
      li.classList.toggle("mx-frise__etape--faite", i < courante);
      li.classList.toggle("mx-frise__etape--actuelle", i === courante);
      if (i === courante) { li.setAttribute("aria-current", "step"); } else { li.removeAttribute("aria-current"); }
    });
    precedent.hidden = courante === 0;
    suivant.hidden = courante === panneaux.length - 1;
  }

  // Les champs du bloc courant sont vérifiés avant de passer au suivant.
  suivant.addEventListener("click", function () {
    var invalide = [].slice.call(panneaux[courante].querySelectorAll("input, select, textarea")).filter(function (c) { return !c.checkValidity(); })[0];
    if (invalide) { invalide.reportValidity(); return; }
    afficher(courante + 1);
  });
  precedent.addEventListener("click", function () { afficher(courante - 1); });

  formulaire.addEventListener("click", function (evenement) {
    var ajout = evenement.target.closest("[data-ajouter]");
    if (ajout) {
      var modele = formulaire.querySelector('[data-modele="' + ajout.dataset.ajouter + '"]');
      var conteneur = formulaire.querySelector('[data-lignes="' + ajout.dataset.ajouter + '"]');
      conteneur.appendChild(modele.content.cloneNode(true));
      var champ = conteneur.lastElementChild.querySelector("input:not([type=hidden]), textarea");
      if (champ && evenement.isTrusted) { champ.focus(); }
      return;
    }
    var bouton = evenement.target.closest("[data-retirer], [data-monter], [data-descendre], [data-dupliquer]");
    if (!bouton) { return; }
    var ligne = bouton.closest("[data-ligne]");
    if (bouton.hasAttribute("data-retirer")) { ligne.remove(); return; }
    if (bouton.hasAttribute("data-monter") && ligne.previousElementSibling) {
      ligne.parentNode.insertBefore(ligne, ligne.previousElementSibling);
    } else if (bouton.hasAttribute("data-descendre") && ligne.nextElementSibling) {
      ligne.parentNode.insertBefore(ligne.nextElementSibling, ligne);
    } else if (bouton.hasAttribute("data-dupliquer")) {
      var copie = ligne.cloneNode(true);
      // La copie est une nouvelle ligne : elle ne reprend pas l'identité de l'originale.
      [].slice.call(copie.querySelectorAll('input[name="ligne_cle"]')).forEach(function (c) { c.value = ""; });
      ligne.parentNode.insertBefore(copie, ligne.nextSibling);
    }
    // Le bouton déplacé garde le focus pour enchaîner les déplacements au clavier.
    if (!bouton.hasAttribute("data-dupliquer") && evenement.isTrusted) { bouton.focus(); }
  });

  // Une ligne vide au départ pour ne pas démarrer devant un écran sans champ.
  ["preparation", "etape", "ligne"].forEach(function (nom) {
    var conteneur = formulaire.querySelector('[data-lignes="' + nom + '"]');
    if (!conteneur.children.length) { formulaire.querySelector('[data-ajouter="' + nom + '"]').click(); }
  });

  frise.hidden = false;
  navigation.hidden = false;
  afficher(0);
})();
