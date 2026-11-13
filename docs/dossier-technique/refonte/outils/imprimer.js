// Impression PDF par Chromium. Usage : node imprimer.js <entree.html> <sortie.pdf> <config.json>
// config : { "entete_gauche": "...", "entete_centre": "...", "pied_gauche": "..." }
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
(async () => {
  const [entree, sortie, cfgf] = process.argv.slice(2);
  const cfg = JSON.parse(fs.readFileSync(cfgf, "utf8"));
  const e = (t) => String(t).replace(/&/g, "&amp;").replace(/</g, "&lt;");
  const nav = await chromium.launch();
  const page = await nav.newPage();
  await page.goto("file://" + path.resolve(entree), { waitUntil: "load" });
  await page.pdf({
    path: sortie, format: "A4", printBackground: true, outline: true, tagged: true, preferCSSPageSize: true,
    displayHeaderFooter: true,
    headerTemplate: `<div style="width:100%;font-family:sans-serif;color:#14202e;margin:0 12mm;padding-bottom:1mm;border-bottom:.5px solid #b9c3d0;display:flex;justify-content:space-between;align-items:baseline"><span style="font-size:7pt">${e(cfg.entete_gauche)}</span><span style="font-size:8pt;font-weight:700;letter-spacing:.3px">${e(cfg.entete_centre)}</span><span style="font-size:7pt">${e(cfg.entete_droite || "")}</span></div>`,
    footerTemplate: `<div style="width:100%;font-family:sans-serif;color:#14202e;margin:0 12mm;font-size:7pt;display:flex;justify-content:space-between"><span>${e(cfg.pied_gauche)}</span><span>Page <span class="pageNumber"></span> / <span class="totalPages"></span></span></div>`,
    margin: { top: "20mm", bottom: "19mm", left: "17mm", right: "17mm" },
  });
  await nav.close();
})();
