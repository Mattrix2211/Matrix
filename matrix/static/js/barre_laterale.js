// Barre latérale : replier / déplier sans recharger la page, état mémorisé dans le
// profil du marin. Sans JavaScript, le formulaire fonctionne tel quel (rechargement).
// Sur téléphone, elle sert de tiroir (offcanvas Bootstrap) ouvert par le bouton « Menu ».
(function () {
  var form = document.querySelector('[data-barre-laterale-bascule]');
  var barre = document.getElementById('barre-laterale');
  if (!barre) return;
  var declencheur = document.querySelector('[data-bs-target="#barre-laterale"][aria-expanded]');
  function synchroniser(ouvert) { if (declencheur) declencheur.setAttribute('aria-expanded', ouvert ? 'true' : 'false'); }
  barre.addEventListener('show.bs.offcanvas', function () {
    synchroniser(true);
    // Un seul panneau à la fois : les notifications se ferment.
    var notifications = document.querySelector('#centre-notifications.show');
    var instance = notifications && window.bootstrap && bootstrap.Offcanvas.getInstance(notifications);
    if (instance) instance.hide();
  });
  barre.addEventListener('hidden.bs.offcanvas', function () { synchroniser(false); });
  // Écran bas : l'entrée courante reste visible dans le menu défilant.
  var courante = barre.querySelector('[aria-current="page"]');
  // Défilement direct : scrollIntoView déplacerait le point de départ de la touche Tab (lien d'évitement).
  function montrerCourante() {
    var menu = barre.querySelector('nav');
    if (!courante || !menu) return;
    var c = courante.getBoundingClientRect(), m = menu.getBoundingClientRect();
    if (c.bottom > m.bottom) menu.scrollTop += c.bottom - m.bottom;
    else if (c.top < m.top) menu.scrollTop -= m.top - c.top;
  }
  montrerCourante();
  barre.addEventListener('shown.bs.offcanvas', montrerCourante);
  // Groupes repliables : choix explicite de l'utilisateur, mémorisé dans ce navigateur (prototype).
  // Par défaut ouverts : « Mon quotidien », « Activité » et le groupe de la page courante. Replié, le menu icônes les montre tous.
  var CLE_GROUPES = 'mx-menu-groupes';
  var etat = {};
  try { etat = JSON.parse(window.localStorage.getItem(CLE_GROUPES) || '{}'); } catch (e) { etat = {}; }
  function appliquer(groupe, ouvert) {
    groupe.classList.toggle('mx-lateral__groupe--ferme', !ouvert);
    groupe.querySelector('.mx-lateral__bouton-groupe').setAttribute('aria-expanded', ouvert ? 'true' : 'false');
  }
  barre.querySelectorAll('.mx-lateral__groupe').forEach(function (groupe) {
    var nom = groupe.dataset.groupe;
    if (nom in etat && !groupe.querySelector('[aria-current="page"]')) appliquer(groupe, !!etat[nom]);
    groupe.querySelector('.mx-lateral__bouton-groupe').addEventListener('click', function () {
      var ouvert = groupe.classList.contains('mx-lateral__groupe--ferme');
      appliquer(groupe, ouvert);
      etat[nom] = ouvert;
      try { window.localStorage.setItem(CLE_GROUPES, JSON.stringify(etat)); } catch (e) { /* stockage indisponible */ }
    });
  });
  if (!form) return;
  var bouton = form.querySelector('button');
  var champ = form.querySelector('input[name="repliee"]');
  var libelle = form.querySelector('.mx-lateral__libelle');
  var icone = form.querySelector('.mx-lateral__icone');

  function afficher(replie) {
    barre.classList.toggle('mx-lateral--repliee', replie);
    var texte = replie ? 'Déplier le menu' : 'Replier le menu';
    bouton.setAttribute('aria-expanded', replie ? 'false' : 'true');
    bouton.title = texte;
    libelle.textContent = texte;
    icone.className = 'bi ' + (replie ? 'bi-chevron-bar-right' : 'bi-chevron-bar-left') + ' mx-lateral__icone';
    champ.value = replie ? '0' : '1';
  }

  // Message discret quand l'état n'a pas pu être enregistré.
  function avertir() {
    var message = document.createElement('div');
    message.className = 'small text-danger px-2 pt-1';
    message.setAttribute('role', 'alert');
    message.textContent = 'Préférence non enregistrée.';
    form.appendChild(message);
    setTimeout(function () { message.remove(); }, 4000);
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var replier = champ.value === '1';
    var envoye = new FormData(form);
    afficher(replier);
    fetch(form.action, { method: 'POST', body: envoye, headers: { 'X-Requested-With': 'fetch' }, credentials: 'same-origin' })
      .then(function (reponse) { if (!reponse.ok) throw new Error(); })
      .catch(function () { afficher(!replier); avertir(); });
  });
})();
