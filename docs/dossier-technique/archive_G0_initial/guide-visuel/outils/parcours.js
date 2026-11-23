// Parcours à plusieurs étapes (écritures dans la base de démonstration isolée) : anomalie → ticket, maintenance → compte rendu,
// tâche, tour de service. Usage : MDP=... NODE_PATH=$(npm root -g) node parcours.js <dossier_sortie>
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const B = 'http://127.0.0.1:8800';
const OUT = process.argv[2];
const MDP = process.env.MDP;
const manifeste = [];

(async () => {
  const b = await chromium.launch();
  const ouvrir = async (profil) => {
    const ctx = await b.newContext({ viewport: { width: 1366, height: 768 }, deviceScaleFactor: 2, locale: 'fr-FR' });
    const p = await ctx.newPage();
    await p.goto(B + '/accounts/login/');
    await p.fill('input[name=username]', profil);
    await p.fill('input[name=password]', MDP);
    await Promise.all([p.waitForNavigation(), p.click('button[type=submit]')]);
    p.profil = profil;
    return p;
  };
  const shot = async (p, dossier, id, titre) => {
    await p.waitForLoadState('networkidle').catch(() => {});
    await p.waitForTimeout(500);
    const d = path.join(OUT, dossier);
    fs.mkdirSync(d, { recursive: true });
    const f = path.join(d, id + '.png');
    await p.screenshot({ path: f });
    manifeste.push({ id, dossier, profil: p.profil, titre, fichier: path.relative(OUT, f), urlFinale: p.url().replace(B, ''), statut: 'ok' });
    console.log('ok  ', dossier + '/' + id, '<-', p.profil);
  };
  const essai = async (nom, fn) => { try { await fn(); } catch (e) { console.log('ÉCHEC', nom, String(e.message).split('\n')[0]); manifeste.push({ id: nom, statut: 'échec : ' + String(e.message).split('\n')[0] }); } };

  // Parcours 4 : anomalie signalée par le marin, prise en charge et ticket par le chef de secteur
  const marin = await ouvrir('equipier_a');
  await essai('anomalie', async () => {
    await marin.goto(B + '/logistics/anomalies/signaler/');
    try { await marin.click('button:has-text("Abandonner")', { timeout: 2000 }); await marin.waitForTimeout(500); } catch (e) {}
    await marin.selectOption('select[name=installation]', { label: 'Ventilation du local machine' });
    await marin.fill('input[name=localisation]', 'Local machine');
    await shot(marin, '05_anomalies_tickets', 'p_anomalie_1_objet', 'Signaler une anomalie : l\'objet concerné');
    await marin.click('button:has-text("Suivant")'); await marin.waitForTimeout(600);
    await marin.fill('input[name=titre]', 'Bruit anormal du ventilateur');
    await marin.selectOption('select[name=gravite]', { index: 2 });
    await shot(marin, '05_anomalies_tickets', 'p_anomalie_2_nature', 'Signaler une anomalie : nature et gravité');
    await marin.click('button:has-text("Suivant")'); await marin.waitForTimeout(600);
    const ta = marin.locator('textarea').first();
    if (await ta.count()) await ta.fill('Bruit métallique intermittent au démarrage (signalement de démonstration, données fictives).');
    await shot(marin, '05_anomalies_tickets', 'p_anomalie_3_description', 'Signaler une anomalie : description');
    await marin.click('button:has-text("Suivant")'); await marin.waitForTimeout(600);
    await shot(marin, '05_anomalies_tickets', 'p_anomalie_4_verification', 'Signaler une anomalie : vérification avant envoi');
    await marin.click('button[type=submit]:has-text("Signaler"), button[type=submit]:has-text("Envoyer"), button[type=submit]:has-text("Valider"), button[type=submit]:has-text("Créer")');
    await shot(marin, '05_anomalies_tickets', 'p_anomalie_5_suivi', 'Anomalie signalée : suivi par le marin');
  });
  const chef = await ouvrir('chef_secteur_a');
  await essai('anomalie_chef', async () => {
    await chef.goto(B + '/logistics/anomalies/?statut=ouvertes&vue=perimetre');
    await chef.click('text=Bruit anormal du ventilateur');
    await shot(chef, '05_anomalies_tickets', 'p_anomalie_6_chef', 'Anomalie vue par le chef de secteur');
    const btns = await chef.locator('button, a.btn').allTextContents();
  });
  await essai('anomalie_ticket', async () => {
    await chef.selectOption('select[name=statut]', { label: 'Prise en compte' });
    await chef.click('button:has-text("Mettre à jour")');
    await chef.waitForLoadState('networkidle').catch(() => {});
    await shot(chef, '05_anomalies_tickets', 'p_anomalie_7_prise_en_compte', 'Anomalie prise en compte par le chef');
    await chef.click('button:has-text("Convertir en ticket correctif")');
    await chef.waitForTimeout(700);
    try { await chef.click('button:has-text("Confirmer")', { timeout: 2500 }); } catch (e) {}
    await chef.waitForLoadState('networkidle').catch(() => {});
    await shot(chef, '05_anomalies_tickets', 'p_anomalie_8_ticket', 'Ticket correctif issu de l\'anomalie');
    await chef.goto(B + '/logistics/tickets/');
    try { await chef.click('text=Tout le secteur', { timeout: 2000 }); await chef.waitForTimeout(600); } catch (e) {}
    await shot(chef, '05_anomalies_tickets', 'p_anomalie_9_tickets', 'Tickets correctifs du secteur');
  });

  // Parcours 3 : exécution d'une maintenance et compte rendu
  await essai('maintenance', async () => {
    await marin.goto(B + '/maintenance/occurrences/2/execute/');
    for (const bt of await marin.locator('button:has-text("Conforme"):not(:has-text("Non")), label:has-text("Conforme"):not(:has-text("Non"))').all()) { try { await bt.click({ timeout: 1500 }); } catch (e) {} }
    await marin.evaluate(() => window.scrollTo(0, 0));
    await shot(marin, '04_maintenance', 'p_maintenance_1_saisie', 'Compte rendu : contrôles renseignés');
    await marin.click('button:has-text("Terminer la maintenance")');
    await marin.waitForTimeout(1200);
    await shot(marin, '04_maintenance', 'p_maintenance_2_termine', 'Compte rendu : après « Terminer la maintenance »');
    await marin.goto(B + '/maintenance/gestion/occurrences/');
    await shot(marin, '04_maintenance', 'p_maintenance_3_liste', 'Liste des occurrences après clôture');
  });

  // Parcours 2 : une tâche, du démarrage au compte rendu
  await essai('tache', async () => {
    await marin.goto(B + '/taches/1/');
    await shot(marin, '02_taches', 'p_tache_1_ouverte', 'Tâche ouverte par le marin');
    await marin.click('button:has-text("Démarrer")');
    await marin.waitForLoadState('networkidle').catch(() => {});
    await marin.fill('textarea >> nth=0', 'Graisseurs relevés, aucune fuite constatée (compte rendu de démonstration).');
    await shot(marin, '02_taches', 'p_tache_2_compte_rendu', 'Tâche démarrée : compte rendu rédigé');
    await marin.click('button:has-text("Terminer et rendre compte")');
    await marin.waitForLoadState('networkidle').catch(() => {});
    await shot(marin, '02_taches', 'p_tache_3_terminee', 'Tâche terminée');
  });

  fs.writeFileSync(path.join(OUT, 'manifeste_parcours.json'), JSON.stringify(manifeste, null, 1));
  await b.close();
})();
