// Contrôle « Internet n'existe pas » : charge chaque écran capturé et consigne toute requête qui ne vise pas l'instance locale.
// Usage : MDP=... NODE_PATH=$(npm root -g) node sonde_reseau.js <captures/manifeste.json> <sortie.json>
const { chromium } = require('playwright');
const fs = require('fs');
const B = 'http://127.0.0.1:8800';
const LANCEMENT = { channel: 'chromium', args: ['--lang=fr'], env: { ...process.env, LANGUAGE: 'fr_FR', LC_ALL: 'fr_FR.UTF-8', LANG: 'fr_FR.UTF-8' } };
(async () => {
  const ms = JSON.parse(fs.readFileSync(process.argv[2], 'utf8')).filter(m => m.url && m.statut === 'ok' && !m.url.includes('signaler'));
  const b = await chromium.launch(LANCEMENT);
  const externes = {}, pages = new Set();
  const sessions = {};
  for (const m of ms) {
    if (!sessions[m.profil]) {
      const c = await b.newContext({ locale: 'fr-FR' });
      const p = await c.newPage();
      await p.goto(B + '/accounts/login/');
      await p.fill('input[name=username]', m.profil);
      await p.fill('input[name=password]', process.env.MDP);
      await Promise.all([p.waitForNavigation(), p.click('button[type=submit]')]);
      p.on('request', r => { const u = r.url(); if (!u.startsWith(B) && !u.startsWith('data:') && !u.startsWith('blob:')) (externes[u] = externes[u] || new Set()).add(p._cur || ''); });
      sessions[m.profil] = p;
    }
    const p = sessions[m.profil];
    p._cur = m.url;
    try { await p.goto(B + m.url); await p.waitForLoadState('networkidle').catch(() => {}); pages.add(m.url); } catch (e) {}
  }
  await b.close();
  const rapport = { pages_chargees: pages.size, requetes_externes: Object.keys(externes).map(u => ({ url: u, pages: [...externes[u]].slice(0, 3) })) };
  fs.writeFileSync(process.argv[3], JSON.stringify(rapport, null, 1));
  console.log(JSON.stringify(rapport));
})();
