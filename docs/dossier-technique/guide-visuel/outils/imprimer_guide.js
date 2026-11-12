// Imprime le HTML du guide (pages A4 paysage fixes) en PDF avec Chromium : aucune ressource distante.
// Usage : node imprimer_guide.js <fichier.html> <sortie.pdf>
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [entree, sortie] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto('file://' + path.resolve(entree), { waitUntil: 'load' });
  await p.pdf({ path: sortie, width: '297mm', height: '210mm', printBackground: true, outline: true, tagged: true, preferCSSPageSize: true, margin: { top: '0', bottom: '0', left: '0', right: '0' } });
  await b.close();
  console.log('PDF écrit');
})();
