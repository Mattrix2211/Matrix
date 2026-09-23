/*
 * Abonnement/désabonnement aux notifications Web Push (alertes critiques).
 * Vanilla JS, aucune dépendance externe/CDN (fonctionne hors-ligne sur le
 * réseau du bord). Pilote l'interrupteur "push-toggle" de la cloche de
 * notifications (base.html).
 */
(function () {
  "use strict";

  function getCookie(nom) {
    var valeur = "; " + document.cookie;
    var parties = valeur.split("; " + nom + "=");
    if (parties.length === 2) return parties.pop().split(";").shift();
    return "";
  }

  // Convertit la clé publique VAPID (base64 URL-safe) au format Uint8Array
  // attendu par PushManager.subscribe().
  function urlBase64VersUint8Array(base64) {
    var padding = "=".repeat((4 - (base64.length % 4)) % 4);
    var base64Standard = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
    var donneesBrutes = window.atob(base64Standard);
    var tableau = new Uint8Array(donneesBrutes.length);
    for (var i = 0; i < donneesBrutes.length; ++i) {
      tableau[i] = donneesBrutes.charCodeAt(i);
    }
    return tableau;
  }

  function disponible() {
    return "serviceWorker" in navigator && "PushManager" in window;
  }

  function majInterrupteur(interrupteur, actif) {
    if (interrupteur) interrupteur.checked = actif;
  }

  function activer(interrupteur) {
    return navigator.serviceWorker
      .register("/service-worker.js", { scope: "/" })
      .then(function (enregistrement) {
        return fetch("/api/notifications/push/public-key/")
          .then(function (r) { return r.json(); })
          .then(function (donnees) {
            return enregistrement.pushManager.subscribe({
              userVisibleOnly: true,
              applicationServerKey: urlBase64VersUint8Array(donnees.publicKey),
            });
          });
      })
      .then(function (abonnement) {
        return fetch("/api/notifications/push/subscribe/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken") },
          body: JSON.stringify(abonnement.toJSON()),
        });
      })
      .then(function () {
        majInterrupteur(interrupteur, true);
      });
  }

  function desactiver(interrupteur) {
    return navigator.serviceWorker
      .getRegistration("/")
      .then(function (enregistrement) {
        if (!enregistrement) return null;
        return enregistrement.pushManager.getSubscription();
      })
      .then(function (abonnement) {
        if (!abonnement) return null;
        return fetch("/api/notifications/push/unsubscribe/", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken") },
          body: JSON.stringify({ endpoint: abonnement.endpoint }),
        }).then(function () {
          return abonnement.unsubscribe();
        });
      })
      .then(function () {
        majInterrupteur(interrupteur, false);
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var interrupteur = document.getElementById("push-toggle");
    var messageIndispo = document.getElementById("push-indisponible");
    if (!interrupteur) return;

    if (!disponible()) {
      interrupteur.disabled = true;
      if (messageIndispo) messageIndispo.classList.remove("d-none");
      return;
    }

    // Reflète l'état réel de l'abonnement au chargement de la page.
    navigator.serviceWorker
      .register("/service-worker.js", { scope: "/" })
      .then(function (enregistrement) {
        return enregistrement.pushManager.getSubscription();
      })
      .then(function (abonnement) {
        majInterrupteur(interrupteur, !!abonnement);
      })
      .catch(function () {
        // Environnement sans contexte sécurisé (HTTP) ou navigateur non
        // compatible : l'interrupteur reste simplement inactif.
      });

    interrupteur.addEventListener("change", function () {
      var etatSouhaite = interrupteur.checked;
      var action = etatSouhaite ? activer(interrupteur) : desactiver(interrupteur);
      action.catch(function () {
        // Échec (refus de permission, abonnement déjà retiré, etc.) :
        // revient à l'état précédent pour ne pas afficher un état incohérent.
        majInterrupteur(interrupteur, !etatSouhaite);
      });
    });
  });
})();
