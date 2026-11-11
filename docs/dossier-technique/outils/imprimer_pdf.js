// Imprime une page HTML locale en PDF avec Chromium (Playwright) : signets, numéros de page, bandeau de diffusion.
// Usage : node imprimer_pdf.js <fichier.html> <sortie.pdf> <texte_entete>
// Aucune ressource distante n'est chargée.
const { chromium } = require("playwright");
const path = require("path");

(async () => {
  const [entree, sortie, entete] = process.argv.slice(2);
  const navigateur = await chromium.launch();
  const page = await navigateur.newPage();
  await page.goto("file://" + path.resolve(entree), { waitUntil: "load" });
  const echapper = (t) => t.replace(/&/g, "&amp;").replace(/</g, "&lt;");
  await page.pdf({
    path: sortie, format: "A4", printBackground: true, outline: true, tagged: true, preferCSSPageSize: true,
    displayHeaderFooter: true,
    headerTemplate: `<div style="font-size:7pt;width:100%;text-align:center;color:#14202e;font-family:sans-serif;border-bottom:0.5px solid #b9c3d0;padding-bottom:1mm;margin:0 12mm">${echapper(entete)}</div>`,
    footerTemplate: `<div style="font-size:7pt;width:100%;text-align:center;color:#14202e;font-family:sans-serif">Page <span class="pageNumber"></span> / <span class="totalPages"></span></div>`,
    margin: { top: "18mm", bottom: "16mm", left: "15mm", right: "15mm" },
  });
  await navigateur.close();
  console.log("PDF écrit");
})();
