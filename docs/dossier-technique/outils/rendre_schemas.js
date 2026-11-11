// Exporte les schémas Mermaid (schemas/src/*.mmd) en SVG lisibles hors ligne (schemas/svg/*.svg).
// Usage : node rendre_schemas.js <dossier_mermaid_npm> <dossier_src> <dossier_svg>
// <dossier_mermaid_npm> contient node_modules/mermaid/dist/mermaid.min.js (npm install mermaid@10.9.1).
// Le navigateur est celui de Playwright ; aucune ressource distante n'est chargée.
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

(async () => {
  const [npmDir, src, sortie] = process.argv.slice(2);
  const mermaidJs = fs.readFileSync(path.join(npmDir, "node_modules/mermaid/dist/mermaid.min.js"), "utf8");
  fs.mkdirSync(sortie, { recursive: true });
  const navigateur = await chromium.launch();
  const page = await navigateur.newPage();
  await page.setContent("<html><body><div id='c'></div></body></html>");
  await page.addScriptTag({ content: mermaidJs });
  await page.evaluate(() => {
    mermaid.initialize({
      startOnLoad: false, securityLevel: "strict", theme: "base", flowchart: { htmlLabels: false },
      themeVariables: { fontFamily: "Arial, sans-serif", primaryColor: "#e8eef7", primaryBorderColor: "#1f3b63",
        primaryTextColor: "#10213a", lineColor: "#1f3b63", secondaryColor: "#f3f6fa", tertiaryColor: "#ffffff" },
    });
  });
  let echecs = 0;
  for (const f of fs.readdirSync(src).filter((n) => n.endsWith(".mmd")).sort()) {
    const code = fs.readFileSync(path.join(src, f), "utf8");
    try {
      const svg = await page.evaluate(async ([id, texte]) => (await mermaid.render(id, texte)).svg, ["s" + f.replace(/\W/g, ""), code]);
      fs.writeFileSync(path.join(sortie, f.replace(/\.mmd$/, ".svg")), svg);
      console.log("ok  ", f);
    } catch (e) {
      echecs++;
      console.log("ECHEC", f, String(e.message || e).split("\n")[0]);
    }
  }
  await navigateur.close();
  process.exit(echecs ? 1 : 0);
})();
