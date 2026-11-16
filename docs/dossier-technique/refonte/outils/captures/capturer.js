// Captures du guide utilisateur (révision 2) : instance de démonstration isolée de l'état B (127.0.0.1:8800), données fictives,
// navigateur en français, 1366×768 ×2. Chaque capture porte son statut HTTP, ses assertions DOM et le texte visible (contrôle C9).
// Usage : MDP=<mot de passe de démonstration> NODE_PATH=$(npm root -g) node capturer.js <dossier_sortie> [filtre_id]
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const B = 'http://127.0.0.1:8800';
const LANCEMENT = { channel: 'chromium', args: ['--lang=fr'], env: { ...process.env, LANGUAGE: 'fr_FR', LC_ALL: 'fr_FR.UTF-8', LANG: 'fr_FR.UTF-8' } };

const OUT = process.argv[2];
const FILTRE = process.argv[3] || '';
const MDP = process.env.MDP;
const MDP_ADMIN = process.env.MDP_ADMIN || '';

const C = [];
const cap = (dossier, id, profil, titre, url, o = {}) => C.push({ dossier, id, profil, titre, url, ...o });
const present = (sel, note) => ({ type: 'present', sel, note });
const absent = (sel, note) => ({ type: 'absent', sel, note });
const cliquer = (sel, ms = 700) => async p => { await p.click(sel); await p.waitForTimeout(ms); };
const rechercher = (terme) => async p => { await p.keyboard.press('Control+K'); await p.keyboard.type(terme, { delay: 60 }); await p.waitForTimeout(1200); };

// 01 — Prise en main
cap('01_prise_en_main', 'accueil_marin', 'equipier_a', "Accueil « Aujourd'hui » du marin", '/', { assertions: [present('text=À FAIRE'), present('text=MA JOURNÉE')] });
cap('01_prise_en_main', 'accueil_marin_bas', 'equipier_a', "Bas de l'accueil du marin", '/', { avant: async p => { await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); await p.waitForTimeout(500); } });
cap('01_prise_en_main', 'accueil_marin_suivi', 'equipier_a', 'Accueil, onglet « Suivi »', '/demandes/');
cap('01_prise_en_main', 'menu_deplie', 'equipier_a', 'Menu latéral déplié', '/', { avant: async p => { await p.click('text=ÉQUIPEMENTS'); await p.click('text=MAINTENANCE'); } });
cap('01_prise_en_main', 'notifications', 'equipier_a', 'Cloche des notifications', '/', { avant: async p => { await p.click('button:has(.bi-bell), a:has(.bi-bell), [aria-label*="otification"]'); await p.waitForTimeout(700); } });
cap('01_prise_en_main', 'recherche_equipement', 'equipier_a', 'Recherche globale : un équipement', '/', { avant: rechercher('pompe') });
cap('01_prise_en_main', 'recherche_personne', 'chef_secteur_a', 'Recherche globale : une personne', '/', { avant: rechercher('Lucas') });
cap('01_prise_en_main', 'recherche_information', 'equipier_a', 'Recherche globale : une information', '/', { avant: rechercher('incendie') });
cap('01_prise_en_main', 'calendrier_mois', 'equipier_a', 'Calendrier du marin (mois)', '/calendar/');
cap('01_prise_en_main', 'annonces', 'equipier_a', "Annonces avec accusé de réception", '/annonces/');
cap('01_prise_en_main', 'annonce_accuser', 'equipier_a', "Annonce à accuser réception", '/annonces/', { avant: cliquer('text=Rappel : port des EPI en zone machine', 600) });

// 02 — Tâches
cap('02_taches', 'taches_liste', 'equipier_a', 'Mes tâches', '/taches/');
cap('02_taches', 'tache_detail', 'equipier_a', "Détail d'une tâche et compte rendu", '/taches/', { avant: cliquer("text=Contrôler le graissage des paliers de la ligne d'arbre", 600) });
cap('02_taches', 'tache_synthese', 'chef_section_a', 'Synthèse du chef de section', '/', { avant: async p => { await p.click('text=Synthèse'); await p.waitForTimeout(900); await p.evaluate(() => window.scrollTo(0, 0)); await p.waitForTimeout(300); } });

// 03 — Quarts et services
cap('03_quarts_services', 'tours_par_jour', 'equipier_a', 'Quarts et tours de service (par jour)', '/quarts/');
cap('03_quarts_services', 'tours_par_marin', 'chef_secteur_a', 'Tours de service (par marin, vue du chef)', '/quarts/', { avant: cliquer('text=Par marin (responsables)') });
cap('03_quarts_services', 'listes', 'chef_secteur_a', 'Listes de quarts et de services', '/quarts/', { avant: cliquer('a:has-text("Listes"), button:has-text("Listes")') });
cap('03_quarts_services', 'feuille_service', 'equipier_a', 'Feuille de service du jour', '/quarts/feuille-service/');
cap('03_quarts_services', 'echanges', 'chef_secteur_a', "Échanges de service à traiter", '/quarts/echanges/');
cap('03_quarts_services', 'echange_marin', 'equipier_a', "Échange de tour : vue du marin", '/quarts/echanges/');
cap('03_quarts_services', 'absences', 'chef_service_a', "Absences de l'équipe", '/absences/');

// 04 — Maintenance
cap('04_maintenance', 'occurrences', 'equipier_a', 'Gestion de la maintenance : occurrences', '/maintenance/gestion/occurrences/', { assertions: [present('text=Exécuter', 'NE-01 : bouton affiché même sans droit sur la ligne')] });
cap('04_maintenance', 'occurrences_retard', 'chef_secteur_a', 'Maintenances en retard (vue du chef de secteur)', '/maintenance/gestion/occurrences/?retard=1');
cap('04_maintenance', 'execution_fiche', 'equipier_a', 'Exécution guidée : fiche et consignes de sécurité', '/maintenance/occurrences/2/execute/', { assertions: [present('text=Points à contrôler')] });

// 05 — Anomalies et tickets
cap('05_anomalies_tickets', 'anomalies_liste', 'equipier_a', "Mes signalements d'anomalies", '/logistics/anomalies/');
cap('05_anomalies_tickets', 'anomalie_detail', 'chef_secteur_a', "Détail d'une anomalie", '/logistics/anomalies/?statut=ouvertes&vue=perimetre', { avant: cliquer("text=Pompe de cale : débit insuffisant à l'essai", 600) });
cap('05_anomalies_tickets', 'tickets_liste', 'chef_secteur_a', 'Tickets correctifs du secteur', '/logistics/tickets/', { avant: cliquer('text=Tout le secteur') });

// 06 — Matériel, installations, stock
cap('06_materiel_stock', 'materiels', 'chef_secteur_a', 'Matériels', '/assets/');
cap('06_materiel_stock', 'materiel_detail', 'chef_secteur_a', "Fiche d'un matériel", '/assets/', { avant: cliquer('text=Extincteur CO2 5 kg', 600) });
cap('06_materiel_stock', 'installations', 'equipier_a', 'Installations', '/installations/');
cap('06_materiel_stock', 'installation_detail', 'equipier_a', "Fiche d'une installation (relevés et entretien)", '/installations/', { avant: cliquer('text=Pompe de refroidissement', 600) });
cap('06_materiel_stock', 'catalogue', 'equipier_a', 'Catalogue du matériel de la flotte', '/catalogue/');
cap('06_materiel_stock', 'plan_navire', 'chef_secteur_a', 'Plan du navire et épingles', '/assets/plan-navire/', { avant: async p => { try { await p.click('text=Pont principal', { timeout: 3000 }); } catch (e) {} await p.waitForTimeout(800); } });
cap('06_materiel_stock', 'stock', 'chef_secteur_a', 'Stock de pièces', '/logistics/stock/');

// 07 — Supervision
cap('07_supervision', 'accueil_chef_secteur', 'chef_secteur_a', 'Accueil du chef de secteur', '/');
cap('07_supervision', 'accueil_chef_secteur_bas', 'chef_secteur_a', "Bas de l'accueil du chef : bloc Supervision", '/', { avant: async p => { await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); await p.waitForTimeout(500); } });
cap('07_supervision', 'equipe_calendrier', 'chef_section_a', "Calendrier de l'équipe", '/calendar/?user=equipe');
cap('07_supervision', 'vue_secteur', 'chef_secteur_a', "Vue d'ensemble du secteur", '/dashboard/flotte/');
cap('07_supervision', 'vue_unite', 'chef_service_a', "Vue d'ensemble du service", '/dashboard/flotte/');
cap('07_supervision', 'difficultes', 'chef_secteur_a', 'Difficultés signalées à traiter', '/demandes/');

// 08 — Compétences, documentation, programme
cap('08_autres_ecrans', 'formations', 'equipier_a', 'Formations et qualifications', '/formations/');
cap('08_autres_ecrans', 'formation_detail', 'equipier_a', "Fiche d'une formation", '/formations/1/');
cap('08_autres_ecrans', 'postes', 'chef_secteur_a', 'Postes du bord', '/postes/');
cap('08_autres_ecrans', 'documentation', 'equipier_a', 'Documentation et procédures', '/documentation/');
cap('08_autres_ecrans', 'retex', 'equipier_a', 'RETEX', '/retex/');
cap('08_autres_ecrans', 'programme', 'equipier_a', 'Programme du bâtiment', '/programme/');
cap('08_autres_ecrans', 'pret_appareillage', 'chef_service_a', 'Prêt à appareiller (aucune session ouverte)', '/dashboard/pret-appareillage/');
cap('08_autres_ecrans', 'profil', 'equipier_a', 'Profil et qualifications', '/users/profil/');
cap('08_autres_ecrans', 'parametres', 'equipier_a', 'Paramètres de notification', '/parametre/?tab=notifications');

// 09 — Limites de l'état B
cap('09_limites', 'en_validation_liste', 'chef_secteur_a', 'Occurrences « En validation » (A20)', '/maintenance/gestion/occurrences/?statut=WAITING_VALIDATION');
cap('09_limites', 'en_validation_execution', 'chef_secteur_a', 'Occurrence « En validation » : fiche ouverte (A20)', '/maintenance/gestion/occurrences/?statut=WAITING_VALIDATION', { avant: async p => { await p.click('a:has-text("Exécuter")'); await p.waitForTimeout(800); }, assertions: [present('text=Enregistrer la correction', 'chef de secteur : bouton présent')] });
cap('09_limites', 'en_validation_execution_marin', 'equipier_a', "Occurrence « En validation » : l'exécutant ne voit pas le bouton (A20)", '/maintenance/gestion/occurrences/?statut=WAITING_VALIDATION', { sansImage: true, avant: async p => { const l = p.locator('a:has-text("Exécuter")'); if (await l.count()) { await l.first().click(); await p.waitForTimeout(800); } }, assertions: [absent('text=Enregistrer la correction', 'exécutant : bouton absent')] });

// 10 — Vues mobiles émulées (appareil réel non essayé)
cap('10_mobile', 'mobile_accueil', 'equipier_a', 'Accueil sur écran de téléphone (émulation)', '/', { mobile: true });
cap('10_mobile', 'mobile_maintenance', 'equipier_a', 'Maintenance sur écran de téléphone (émulation)', '/maintenance/gestion/occurrences/', { mobile: true });


// Repères numérotés : posés dans le PDF (jamais dans l'image), positions mesurées dans la page réelle au moment de la capture.
const REPERES = {
  accueil_marin: [['text=À FAIRE', 'Actions à faire, urgentes en tête'], ['text=MA JOURNÉE', 'Journée : quarts, services, maintenances'], ['text=MES TOURS DE SERVICE', 'Prochains tours de service'], ['.bi-bell >> nth=0', 'Cloche des notifications']],
  occurrences: [['tr:has(button:has-text("M\'assigner")) a:has-text("Exécuter") >> nth=0', 'NE-01 : « Exécuter » affiché pour une échéance non assignée à ce marin'], ['button:has-text("M\'assigner") >> nth=0', '« M\'assigner » : prendre l\'échéance']],
  execution_fiche: [['text=Points à contrôler', 'Contrôles : Conforme, Non conforme ou Sans objet'], ["text=Sécurité de l'intervention", 'Consignes de sécurité de la fiche'], ['text=opérations réalisées', 'Progression et enregistrement']],
  en_validation_execution: [['button:has-text("Enregistrer la correction")', 'A20 : bouton réservé au chef de secteur ou plus']],
  plan_navire: [['text=Légende', 'Légende des couleurs'], ['text=Matériel positionné', 'Matériels épinglés sur le pont']],
  vue_secteur: [['text=Maintenances en retard', 'Indicateurs du secteur'], ['text=Tickets correctifs ouverts par statut', 'Répartition des tickets par statut']],
  tache_detail: [['text=Rendre compte', 'Compte rendu de la tâche'], ['text=Un problème sur cette tâche', "Signalement d'un blocage"]],
  feuille_service: [['text=En-tête', "En-tête de la journée"], ['text=CIRCUIT DE VALIDATION', 'Circuit de validation : rédaction, visas, publication']],
};
for (const c of C) if (REPERES[c.id]) c.reperes = REPERES[c.id];

const MOTIFS_LOCALE = [/mm\/dd\/yyyy/i, /Choose File/i, /No file chosen/i, /\b\d{1,2}:\d{2}\s?(AM|PM)\b/];
const MOTIFS_SENSIBLES = [/[\w.+-]+@[\w-]+\.[\w.]+/, /password|mot de passe\s*:/i, /Bearer [\w-]{16,}/, /\/home\/|\/tmp\//];

(async () => {
  const b = await chromium.launch(LANCEMENT);
  const manifeste = [];
  const sessions = {};
  // Sonde de langue : le rendu natif des champs date, heure et fichier prouve que le navigateur est en français.
  {
    const c = await b.newContext({ locale: 'fr-FR', viewport: { width: 520, height: 110 } });
    const p = await c.newPage();
    await p.setContent('<html lang="fr"><body style="font:15px sans-serif;margin:12px"><input type="date"> <input type="time"><br><br><input type="file"></body></html>');
    await p.screenshot({ path: path.join(OUT, '_sonde_locale.png') });
    const meta = { version: b.version(), langue_navigateur: await p.evaluate(() => navigator.language), langues: await p.evaluate(() => navigator.languages), format_date: await p.evaluate(() => new Intl.DateTimeFormat().format(new Date(2026, 10, 16))), arguments: LANCEMENT.args };
    fs.mkdirSync(OUT, { recursive: true });
    fs.writeFileSync(path.join(OUT, 'manifeste_meta.json'), JSON.stringify(meta, null, 1));
    console.log('sonde', JSON.stringify(meta));
    await c.close();
  }
  const ouvrirContexte = async (profil, mobile) => {
    const ctx = await b.newContext(mobile
      ? { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'fr-FR', timezoneId: 'Europe/Paris', extraHTTPHeaders: { 'Accept-Language': 'fr-FR,fr;q=0.9' } }
      : { viewport: { width: 1366, height: 768 }, deviceScaleFactor: 2, locale: 'fr-FR', timezoneId: 'Europe/Paris', extraHTTPHeaders: { 'Accept-Language': 'fr-FR,fr;q=0.9' } });
    const p = await ctx.newPage();
    p.setDefaultTimeout(7000);
    await p.goto(B + '/accounts/login/');
    await p.fill('input[name=username]', profil);
    await p.fill('input[name=password]', profil === 'admin' ? MDP_ADMIN : MDP);
    await Promise.all([p.waitForNavigation(), p.click('button[type=submit]')]);
    return p;
  };
  const session = async (profil, mobile) => {
    const k = profil + (mobile ? ':m' : '');
    return sessions[k] || (sessions[k] = await ouvrirContexte(profil, mobile));
  };
  for (const c of C) {
    if (FILTRE && !c.id.includes(FILTRE)) continue;
    const p = await session(c.profil, c.mobile);
    const dossier = path.join(OUT, c.dossier);
    fs.mkdirSync(dossier, { recursive: true });
    let statut = 0;
    const suivre = r => { if (r.request().isNavigationRequest() && r.frame() === p.mainFrame()) statut = r.status(); };
    p.on('response', suivre);
    try {
      await p.goto(B + c.url);
      await p.waitForLoadState('networkidle').catch(() => {});
      await p.waitForTimeout(500);
      const statutPage = statut;
      if (c.avant) await c.avant(p);
      const texte = await p.evaluate(() => document.body.innerText + '\n' + [...document.querySelectorAll('input,textarea')].map(e => e.value).join('\n'));
      const reperes = [];
      for (const [sel, texte] of c.reperes || []) {
        const bb = await p.locator(sel).first().boundingBox().catch(() => null);
        if (bb) reperes.push({ n: reperes.length + 1, x: (bb.width < 160 ? bb.x + bb.width + 34 : bb.x) / 1366, y: (bb.y + bb.height / 2) / 768, texte });
      }
      const verifs = [];
      for (const a of c.assertions || []) {
        const n = await p.locator(a.sel).count();
        verifs.push({ ...a, ok: a.type === 'present' ? n > 0 : n === 0 });
      }
      const locale = MOTIFS_LOCALE.filter(r => r.test(texte)).map(String);
      const sensibles = MOTIFS_SENSIBLES.filter(r => r.test(texte)).map(String);
      const m = {
        id: c.id, dossier: c.dossier, profil: c.profil, titre: c.titre, url: c.url, urlFinale: p.url().replace(B, ''),
        statutHttp: statutPage, assertions: verifs, reperes, localeProblemes: locale, motifsSensibles: sensibles,
        mobile: !!c.mobile, emulation: !!c.mobile, texteVisible: texte.slice(0, 20000), statut: 'ok',
      };
      if (!c.sansImage) {
        const fichier = path.join(dossier, c.id + '.png');
        await p.screenshot({ path: fichier });
        m.fichier = path.relative(OUT, fichier);
        m.sha256 = crypto.createHash('sha256').update(fs.readFileSync(fichier)).digest('hex');
      }
      manifeste.push(m);
      const bad = verifs.filter(v => !v.ok).length + locale.length + sensibles.length + (statutPage && statutPage !== 200 ? 1 : 0);
      console.log(bad ? 'ALERTE' : 'ok    ', c.dossier + '/' + c.id, '<-', c.profil, statutPage, bad ? JSON.stringify({ verifs: verifs.filter(v => !v.ok), locale, sensibles }) : '');
    } catch (e) {
      console.log('ÉCHEC ', c.id, String(e.message).split('\n')[0]);
      manifeste.push({ id: c.id, dossier: c.dossier, profil: c.profil, url: c.url, statut: 'échec : ' + String(e.message).split('\n')[0] });
    }
    p.off('response', suivre);
  }
  fs.writeFileSync(path.join(OUT, 'manifeste_statique' + (FILTRE ? '_' + FILTRE : '') + '.json'), JSON.stringify(manifeste, null, 1));
  await b.close();
})();
