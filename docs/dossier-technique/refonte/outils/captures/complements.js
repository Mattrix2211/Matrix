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
  if (await p.locator('button:has-text("Ouvrir une session")').count()) await p.click('button:has-text("Ouvrir une session")');   // idempotent : session déjà ouverte lors d'un rejeu
  await p.waitForLoadState('networkidle').catch(() => {});
  await p.goto(B + '/dashboard/pret-appareillage/');   // recharge : le message vert « Session ouverte » ne doit pas figurer sur la capture
  await p.waitForLoadState('networkidle').catch(() => {});
  await p.waitForTimeout(600);
  const hp = await p.evaluate(() => document.documentElement.scrollHeight);
  const sortie = [];
  const prendre = async (id, titre, defile) => {
    if (defile) { await p.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight)); await p.waitForTimeout(400); }
    const f = path.join(OUT, '08_autres_ecrans', id + '.png');
    await p.screenshot({ path: f });
    const texte = await p.evaluate(() => document.body.innerText);
    sortie.push({ id, dossier: '08_autres_ecrans', profil: 'chef_secteur_a', titre, url: '/dashboard/pret-appareillage/', urlFinale: p.url().replace(B, ''), statutHttp: 200, assertions: [], localeProblemes: [], motifsSensibles: [], mobile: false, emulation: false, hauteur: 768, hauteurPage: hp, partieHaute: !defile && hp > 800, texteVisible: texte.slice(0, 20000), fichier: path.relative(OUT, f), sha256: crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex'), statut: 'ok' });
  };
  await prendre('appareillage_session_ouverte', 'Prêt à appareiller : session ouverte (haut)', false);
  await prendre('appareillage_session_ouverte_bas', 'Prêt à appareiller : session ouverte (bas, validation)', true);
  fs.writeFileSync(path.join(OUT, 'manifeste_complements.json'), JSON.stringify(sortie, null, 1));
  console.log('ok appareillage_session_ouverte');
  await b.close();
})();
