// Contrôle G8 : le fichier autonome fonctionne hors ligne (0 requête réseau), le filtre et le tri répondent, à 1024×768 et 1366×768.
// Usage : NODE_PATH=$(npm root -g) node verifier_annexes.js <index.html> <dossier_sortie>
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const [fichier, sortie] = [path.resolve(process.argv[2]), process.argv[3]];
(async () => {
  const b = await chromium.launch({ channel: 'chromium', args: ['--lang=fr'] });
  const rapport = { requetes_reseau: [], tests: [] };
  for (const [l, h] of [[1366, 768], [1024, 768]]) {
    const c = await b.newContext({ viewport: { width: l, height: h }, locale: 'fr-FR', offline: true });
    const p = await c.newPage();
    p.on('request', r => { if (!r.url().startsWith('file:') && !r.url().startsWith('data:') && !r.url().startsWith('blob:')) rapport.requetes_reseau.push(r.url()); });
    await p.goto('file://' + fichier);
    await p.waitForSelector('#nav button');
    const n = await p.locator('#nav button').count();
    await p.click('#nav button:has-text("C1 —")');
    const avant = await p.locator('tbody tr').count();
    await p.fill('#filtre', 'maintenance');
    const apres = await p.locator('tbody tr').count();
    await p.click('th >> nth=0');
    const tri = await p.locator('th[aria-sort]').count();
    await p.screenshot({ path: path.join(sortie, `annexes_${l}x${h}.png`) });
    await p.click('#nav button:has-text("Totaux")');
    const ecarts = await p.locator('td.ko').count();
    const identiques = await p.locator('td.ok').count();
    rapport.tests.push({ viewport: `${l}x${h}`, tables: n - 1, lignes_C1: avant, lignes_apres_filtre: apres, tri_actif: tri === 1, totaux_identiques: identiques, totaux_en_ecart: ecarts, defilement_horizontal_page: await p.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth) });
    await c.close();
  }
  await b.close();
  fs.writeFileSync(path.join(sortie, 'verification_annexes.json'), JSON.stringify(rapport, null, 1));
  console.log(JSON.stringify(rapport));
})();
