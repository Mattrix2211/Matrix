/*
 * Service Worker Matrix — réception des notifications Web Push.
 * Vanilla JS, aucune dépendance externe/CDN (fonctionne hors-ligne sur le
 * réseau du bord). Servi à la racine du site (/service-worker.js) pour
 * couvrir l'ensemble des pages (scope "/").
 */

self.addEventListener("push", function (event) {
  var donnees = {};
  if (event.data) {
    try {
      donnees = event.data.json();
    } catch (erreur) {
      donnees = { corps: event.data.text() };
    }
  }
  var titre = donnees.titre || "Matrix — Alerte critique";
  var options = {
    body: donnees.corps || "",
    icon: "/static/img/IMG_5292.PNG",
    badge: "/static/img/IMG_5292.PNG",
    data: { url: donnees.url || "/" },
  };
  event.waitUntil(self.registration.showNotification(titre, options));
});

self.addEventListener("notificationclick", function (event) {
  event.notification.close();
  var url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window" }).then(function (listeClients) {
      for (var i = 0; i < listeClients.length; i++) {
        var client = listeClients[i];
        if (client.url.indexOf(url) !== -1 && "focus" in client) {
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(url);
      }
    })
  );
});
