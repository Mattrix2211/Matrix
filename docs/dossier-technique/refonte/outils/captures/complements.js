// Captures complémentaires avec écriture dans la base de démonstration isolée : appareillage avec session ouverte.
// Usage : MDP=... NODE_PATH=$(npm root -g) node complements.js <dossier_sortie>
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const B = 'http://127.0.0.1:8800';
const LANCEMENT = { channel: 'chromium', args: ['--lang=fr'], env: { ...process.env, LANGUAGE: 'fr_FR', LC_ALL: 'fr_FR.UTF-8', LANG: 'fr_FR.UTF-8' } };

const OUT = process.argv[2];
const MDP = process.env.MDP;
(async () => {
  const b = await chromium.launch(LANCEMENT);
  const ctx = await b.newContext({ viewport: { width: 1366, height: 768 }, deviceScaleFactor: 2, locale: 'fr-FR', timezoneId: 'Europe/Paris', extraHTTPHeaders: { 'Accept-Language': 'fr-FR,fr;q=0.9' } });
  const p = await ctx.newPage();
  p.setDefaultTimeout(7000);
  await p.goto(B + '/accounts/login/');
  await p.fill('input[name=username]', 'chef_secteur_a');
  await p.fill('input[name=password]', MDP);
  await Promise.all([p.waitForNavigation(), p.click('button[type=submit]')]);
  await p.goto(B + '/dashboard/pret-appareillage/');
  await p.click('button:has-text("Ouvrir une session")');
  await p.waitForLoadState('networkidle').catch(() => {});
  await p.waitForTimeout(600);
  const f = path.join(OUT, '08_autres_ecrans', 'appareillage_session_ouverte.png');
  await p.screenshot({ path: f });
  const texte = await p.evaluate(() => document.body.innerText);
  const m = [{ id: 'appareillage_session_ouverte', dossier: '08_autres_ecrans', profil: 'chef_secteur_a', titre: 'Prêt à appareiller : session ouverte', url: '/dashboard/pret-appareillage/', urlFinale: p.url().replace(B, ''), statutHttp: 200, assertions: [], localeProblemes: [], motifsSensibles: [], mobile: false, emulation: false, texteVisible: texte.slice(0, 20000), fichier: path.relative(OUT, f), sha256: crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex'), statut: 'ok' }];
  fs.writeFileSync(path.join(OUT, 'manifeste_complements.json'), JSON.stringify(m, null, 1));
  console.log('ok appareillage_session_ouverte');
  await b.close();
})();
