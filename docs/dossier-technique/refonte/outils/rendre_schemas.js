// Rendu des schémas Mermaid de la refonte : police de 18 px, bandeau « CIBLE » dans l'image pour les circuits non développés.
// Usage : node rendre_schemas.js <dossier_mermaid_npm> <dossier_src> <dossier_svg> [liste_cibles_separees_par_virgule]
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");
(async () => {
  const [npmDir, src, sortie, cibles = ""] = process.argv.slice(2);
  const CIBLES = new Set(cibles.split(",").filter(Boolean));
  const js = fs.readFileSync(path.join(npmDir, "node_modules/mermaid/dist/mermaid.min.js"), "utf8");
  fs.mkdirSync(sortie, { recursive: true });
  const nav = await chromium.launch();
  const page = await nav.newPage();
  await page.setContent("<html><body><div id='c'></div></body></html>");
  await page.addScriptTag({ content: js });
  await page.evaluate(() => {
    mermaid.initialize({
      startOnLoad: false, securityLevel: "strict", theme: "base", flowchart: { htmlLabels: false, nodeSpacing: 36, rankSpacing: 46, padding: 10 },
      sequence: { actorFontSize: 18, messageFontSize: 16, noteFontSize: 16, width: 170, wrap: true },
      themeVariables: { fontFamily: "DejaVu Sans, Arial, sans-serif", fontSize: "18px", primaryColor: "#e8eef7", primaryBorderColor: "#1f3b63",
        primaryTextColor: "#10213a", lineColor: "#1f3b63", secondaryColor: "#f3f6fa", tertiaryColor: "#ffffff" },
    });
  });
  let echecs = 0;
  for (const f of fs.readdirSync(src).filter((n) => n.endsWith(".mmd")).sort()) {
    const id = f.slice(0, 3);
    try {
      let svg = await page.evaluate(async ([i, t]) => (await mermaid.render(i, t)).svg, ["s" + f.replace(/\W/g, ""), fs.readFileSync(path.join(src, f), "utf8")]);
      if (CIBLES.has(id)) {
        const m = svg.match(/viewBox="([\d.\-]+) ([\d.\-]+) ([\d.]+) ([\d.]+)"/);
        let [x, y, w, h] = [parseFloat(m[1]), parseFloat(m[2]), parseFloat(m[3]), parseFloat(m[4])];
        const bandeau = 54, marge = 14;
        const nx = x - marge, ny = y - bandeau - marge, nw = w + 2 * marge, nh = h + bandeau + 2 * marge;
        svg = svg.replace(m[0], `viewBox="${nx} ${ny} ${nw} ${nh}"`).replace(/max-width:\s*[\d.]+px/, `max-width: ${nw}px`);
        const cadre = `<rect x="${nx + 3}" y="${ny + 3}" width="${nw - 6}" height="${nh - 6}" fill="none" stroke="#1f5fbf" stroke-width="3" stroke-dasharray="12 7"/>` +
          `<rect x="${nx + 3}" y="${ny + 3}" width="${nw - 6}" height="${bandeau}" fill="#1f5fbf"/>` +
          `<text x="${nx + nw / 2}" y="${ny + 3 + bandeau / 2 + 7}" text-anchor="middle" fill="#ffffff" font-size="22" font-weight="700" font-family="DejaVu Sans, Arial, sans-serif">CIBLE VALIDÉE PAR LE PO — NON DÉVELOPPÉ DANS L'ÉTAT B</text>`;
        svg = svg.replace(/<\/svg>\s*$/, cadre + "</svg>");
      }
      fs.writeFileSync(path.join(sortie, f.replace(/\.mmd$/, ".svg")), svg);
    } catch (e) {
      echecs++;
      console.log("ECHEC", f, String(e.message || e).split("\n")[0]);
    }
  }
  await nav.close();
  process.exit(echecs ? 1 : 0);
})();
