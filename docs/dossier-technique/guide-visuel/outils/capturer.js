// Captures du guide visuel : instance de démonstration isolée (127.0.0.1:8800), données fictives, 1366×768 ×2.
// Usage : MDP=<mot de passe de démonstration> NODE_PATH=$(npm root -g) node capturer.js <dossier_sortie> [filtre_id]
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const B = 'http://127.0.0.1:8800';
const OUT = process.argv[2];
const FILTRE = process.argv[3] || '';
const MDP = process.env.MDP;

// Chaque capture : id, dossier (fonctionnalité), profil, titre, url, étapes facultatives, repères numérotés (sélecteurs).
const C = [];
const cap = (dossier, id, profil, titre, url, o = {}) => C.push({ dossier, id, profil, titre, url, ...o });

// 01 — Prise en main
cap('01_prise_en_main', 'accueil_marin', 'equipier_a', 'Accueil « Aujourd\'hui » du marin', '/',
  { reperes: ['h1', 'text=À FAIRE', 'text=MA JOURNÉE', 'text=MES TOURS DE SERVICE'] });
cap('01_prise_en_main', 'accueil_marin_suivi', 'equipier_a', 'Accueil, onglet « Suivi »', '/demandes/');
cap('01_prise_en_main', 'menu_deplie', 'equipier_a', 'Menu latéral déplié', '/', { avant: async p => { await p.click('text=ÉQUIPEMENTS'); await p.click('text=MAINTENANCE'); } });
cap('01_prise_en_main', 'notifications', 'equipier_a', 'Cloche des notifications', '/', { avant: async p => { await p.click('button:has(.bi-bell), a:has(.bi-bell), [aria-label*="otification"]'); await p.waitForTimeout(700); } });
cap('01_prise_en_main', 'recherche_equipement', 'equipier_a', 'Recherche globale : un équipement', '/', { avant: async p => { await p.keyboard.press('Control+K'); await p.keyboard.type('pompe', { delay: 60 }); await p.waitForTimeout(1200); } });
cap('01_prise_en_main', 'recherche_personne', 'chef_secteur_a', 'Recherche globale : une personne', '/', { avant: async p => { await p.keyboard.press('Control+K'); await p.keyboard.type('Lucas', { delay: 60 }); await p.waitForTimeout(1200); } });
cap('01_prise_en_main', 'recherche_information', 'equipier_a', 'Recherche globale : une information', '/', { avant: async p => { await p.keyboard.press('Control+K'); await p.keyboard.type('incendie', { delay: 60 }); await p.waitForTimeout(1200); } });
cap('01_prise_en_main', 'calendrier_mois', 'equipier_a', 'Calendrier du marin (mois)', '/calendar/');
cap('01_prise_en_main', 'annonces', 'equipier_a', 'Annonces avec accusé de réception', '/annonces/');
cap('01_prise_en_main', 'annonce_detail', 'equipier_a', 'Détail d\'une annonce', '/annonces/', { avant: async p => { await p.click('text=Exercice incendie vendredi'); await p.waitForTimeout(600); } });

// 02 — Tâches
cap('02_taches', 'taches_liste', 'equipier_a', 'Mes tâches', '/taches/');
cap('02_taches', 'tache_detail', 'equipier_a', 'Détail d\'une tâche et compte rendu', '/taches/', { avant: async p => { await p.click('text=Contrôler le graissage des paliers de la ligne d\'arbre'); await p.waitForTimeout(600); } });
cap('02_taches', 'tache_synthese', 'chef_section_a', 'Synthèse du chef de section', '/', { avant: async p => { await p.click('text=Synthèse'); await p.waitForTimeout(900); await p.evaluate(() => window.scrollTo(0, 0)); await p.waitForTimeout(300); } });

// 03 — Quarts et services
cap('03_quarts_services', 'tours_par_jour', 'equipier_a', 'Quarts et tours de service (par jour)', '/quarts/');
cap('03_quarts_services', 'tours_par_marin', 'chef_secteur_a', 'Tours de service (par marin, vue du chef)', '/quarts/', { avant: async p => { await p.click('text=Par marin (responsables)'); await p.waitForTimeout(600); } });
cap('03_quarts_services', 'listes', 'chef_secteur_a', 'Listes de quarts et de services', '/quarts/', { avant: async p => { await p.click('a:has-text("Listes"), button:has-text("Listes")'); await p.waitForTimeout(600); } });
cap('03_quarts_services', 'feuille_service', 'equipier_a', 'Feuille de service du jour', '/quarts/feuille-service/');
cap('03_quarts_services', 'echanges', 'chef_secteur_a', 'Échanges de service à traiter', '/quarts/echanges/');
cap('03_quarts_services', 'absences', 'chef_service_a', 'Absences de l\'équipe', '/absences/');

// 04 — Maintenance
cap('04_maintenance', 'occurrences', 'equipier_a', 'Gestion de la maintenance : occurrences', '/maintenance/gestion/occurrences/');
cap('04_maintenance', 'occurrences_retard', 'chef_secteur_a', 'Maintenances en retard (vue du chef de secteur)', '/maintenance/gestion/occurrences/?retard=1');
cap('04_maintenance', 'execution_fiche', 'equipier_a', 'Exécution guidée : fiche et consignes de sécurité', '/maintenance/occurrences/2/execute/');
cap('04_maintenance', 'execution_saisie', 'equipier_a', 'Exécution guidée : contrôles renseignés', '/maintenance/occurrences/2/execute/',
  { avant: async p => { for (const b of await p.locator('button:has-text("Conforme"):not(:has-text("Non")), label:has-text("Conforme"):not(:has-text("Non"))').all()) { try { await b.click({ timeout: 1500 }); } catch (e) {} } await p.waitForTimeout(500); } });

// 05 — Anomalies et tickets
cap('05_anomalies_tickets', 'anomalies_liste', 'equipier_a', 'Mes signalements d\'anomalies', '/logistics/anomalies/');
cap('05_anomalies_tickets', 'anomalie_detail', 'chef_secteur_a', 'Détail d\'une anomalie', '/logistics/anomalies/?statut=ouvertes&vue=perimetre', { avant: async p => { await p.click('text=Pompe de cale : débit insuffisant à l\'essai'); await p.waitForTimeout(600); } });
cap('05_anomalies_tickets', 'tickets_liste', 'chef_secteur_a', 'Tickets correctifs du secteur', '/logistics/tickets/', { avant: async p => { await p.click('text=Tout le secteur'); await p.waitForTimeout(700); } });

// 06 — Matériel, installations, stock
cap('06_materiel_stock', 'materiels', 'chef_secteur_a', 'Matériels', '/assets/');
cap('06_materiel_stock', 'materiel_detail', 'chef_secteur_a', 'Fiche d\'un matériel', '/assets/', { avant: async p => { await p.click('text=Extincteur CO2 5 kg'); await p.waitForTimeout(600); } });
cap('06_materiel_stock', 'installations', 'equipier_a', 'Installations', '/installations/');
cap('06_materiel_stock', 'installation_detail', 'equipier_a', 'Fiche d\'une installation', '/installations/', { avant: async p => { await p.click('text=Pompe de refroidissement'); await p.waitForTimeout(600); } });
cap('06_materiel_stock', 'catalogue', 'equipier_a', 'Catalogue du matériel de la flotte', '/catalogue/');
cap('06_materiel_stock', 'plan_navire', 'chef_secteur_a', 'Plan du navire et épingles', '/assets/plan-navire/', { avant: async p => { try { await p.click('text=Pont principal', { timeout: 3000 }); } catch (e) {} await p.waitForTimeout(800); } });
cap('06_materiel_stock', 'stock', 'chef_secteur_a', 'Stock de pièces', '/logistics/stock/');

// 07 — Supervision
cap('07_supervision', 'accueil_chef_secteur', 'chef_secteur_a', 'Accueil du chef de secteur', '/');
cap('07_supervision', 'equipe_calendrier', 'chef_section_a', 'Calendrier de l\'équipe', '/calendar/?user=equipe');
cap('07_supervision', 'vue_secteur', 'chef_secteur_a', 'Vue d\'ensemble du secteur', '/dashboard/flotte/');
cap('07_supervision', 'vue_unite', 'chef_service_a', 'Vue d\'ensemble du service', '/dashboard/flotte/');
cap('07_supervision', 'difficultes', 'chef_secteur_a', 'Difficultés signalées à traiter', '/demandes/');

// 08 — Compétences, documentation, programme
cap('08_autres_ecrans', 'formations', 'equipier_a', 'Formations et qualifications', '/formations/');
cap('08_autres_ecrans', 'formation_detail', 'equipier_a', 'Fiche d\'une formation', '/formations/1/');
cap('08_autres_ecrans', 'postes', 'chef_secteur_a', 'Postes du bord', '/postes/');
cap('08_autres_ecrans', 'documentation', 'equipier_a', 'Documentation et procédures', '/documentation/');
cap('08_autres_ecrans', 'retex', 'equipier_a', 'RETEX', '/retex/');
cap('08_autres_ecrans', 'programme', 'equipier_a', 'Programme du bâtiment', '/programme/');
cap('08_autres_ecrans', 'pret_appareillage', 'chef_service_a', 'Prêt à appareiller (aucune session ouverte)', '/dashboard/pret-appareillage/');
cap('08_autres_ecrans', 'profil', 'equipier_a', 'Profil et qualifications', '/users/profil/');
cap('08_autres_ecrans', 'parametres', 'equipier_a', 'Paramètres de notification', '/parametre/?tab=notifications');

// 09 — Limites de l'état B
cap('09_limites', 'en_validation_execution', 'chef_secteur_a', 'Occurrence « En validation » : fiche ouverte (A20)', '/maintenance/gestion/occurrences/?statut=WAITING_VALIDATION', { avant: async p => { await p.click('a:has-text("Exécuter")'); await p.waitForTimeout(800); } });
cap('09_limites', 'en_validation_liste', 'chef_secteur_a', 'Occurrences « En validation » (A20)', '/maintenance/gestion/occurrences/?statut=WAITING_VALIDATION');

// Repères numérotés : posés dans le PDF (jamais dans la capture), positions mesurées dans la page réelle.
const REPERES = {
  accueil_marin: [['text=À FAIRE', "Actions à faire, urgentes en tête"], ['text=MA JOURNÉE', 'Journée : quarts, services, maintenance'], ['text=MES TOURS DE SERVICE', 'Prochains tours de service'], ['header .bi-bell, nav .bi-bell', 'Cloche des notifications'], ['input[placeholder^="Rechercher"], text=Rechercher...', 'Recherche globale (touche /)']],
  feuille_service: [['text=En-tête', 'En-tête de la journée'], ['text=CIRCUIT DE VALIDATION', 'Circuit de validation : rédaction, visas, publication']],
  execution_fiche: [['text=Points à contrôler', 'Contrôles : Conforme, Non conforme ou Sans objet'], ["text=Sécurité de l'intervention", 'Consignes de sécurité de la fiche'], ['text=opérations réalisées', 'Progression et enregistrement']],
  occurrences: [['text=À TRAITER', 'Compteurs à traiter'], ['text=Filtrer les retards', 'Filtre des retards']],
  plan_navire: [['text=Légende', 'Légende des couleurs'], ['text=Matériel positionné', 'Matériels épinglés sur le pont']],
  vue_secteur: [['text=Maintenances en retard', 'Indicateurs du secteur'], ['text=Tickets correctifs ouverts par statut', 'Répartition des tickets par statut']],
  tache_detail: [['text=Rendre compte', 'Compte rendu de la tâche'], ['text=Un problème sur cette tâche', 'Signalement d\'un blocage']],
  postes: [['th:has-text("Pourvu")', 'Effectif pourvu et qualifications manquantes']],
  en_validation_liste: [['span:has-text("En validation") >> nth=-1', 'Statut « En validation » (A20)']],
};
for (const c of C) if (REPERES[c.id]) c.reperes = REPERES[c.id];

(async () => {
  const b = await chromium.launch();
  const manifeste = [];
  const sessions = {};
  const ouvrir = async (profil) => {
    if (sessions[profil]) return sessions[profil];
    const ctx = await b.newContext({ viewport: { width: 1366, height: 768 }, deviceScaleFactor: 2, locale: 'fr-FR' });
    const p = await ctx.newPage();
    await p.goto(B + '/accounts/login/');
    await p.fill('input[name=username]', profil);
    await p.fill('input[name=password]', MDP);
    await Promise.all([p.waitForNavigation(), p.click('button[type=submit]')]);
    return (sessions[profil] = p);
  };
  for (const c of C) {
    if (FILTRE && !c.id.includes(FILTRE)) continue;
    const p = await ouvrir(c.profil);
    const dossier = path.join(OUT, c.dossier);
    fs.mkdirSync(dossier, { recursive: true });
    try {
      await p.goto(B + c.url);
      await p.waitForLoadState('networkidle').catch(() => {});
      await p.waitForTimeout(500);
      if (c.avant) await c.avant(p);
      const fichier = path.join(dossier, c.id + '.png');
      await p.screenshot({ path: fichier });
      const reperes = [];
      for (const [sel, texte] of c.reperes || []) {
        const bb = await p.locator(sel).first().boundingBox().catch(() => null);
        if (bb) reperes.push({ n: reperes.length + 1, x: bb.x / 1366, y: (bb.y + bb.height / 2) / 768, texte });
      }
      const m = { ...c, avant: undefined, reperes, fichier: path.relative(OUT, fichier), urlFinale: p.url().replace(B, ''), statut: 'ok' };
      manifeste.push(m);
      console.log('ok  ', c.dossier + '/' + c.id, '<-', c.profil);
    } catch (e) {
      console.log('ÉCHEC', c.id, String(e.message).split('\n')[0]);
      manifeste.push({ id: c.id, dossier: c.dossier, profil: c.profil, url: c.url, statut: 'échec : ' + String(e.message).split('\n')[0] });
    }
  }
  const cible = path.join(OUT, 'manifeste' + (FILTRE ? '_' + FILTRE : '') + '.json');
  fs.writeFileSync(cible, JSON.stringify(manifeste, null, 1));
  await b.close();
})();
