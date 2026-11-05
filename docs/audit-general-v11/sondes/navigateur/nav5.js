const { chromium } = require('playwright');
const B='http://127.0.0.1:8800', S=process.argv[2], URL=B+'/quarts/feuille-service/2/2027-09-01/';
async function login(browser,user){ const ctx=await browser.newContext({viewport:{width:1366,height:768}}); const p=await ctx.newPage(); const bad=[];
  p.on('response',r=>{ if(r.url().startsWith(B)&&r.status()>=400) bad.push(r.status()+' '+r.url().replace(B,'')); });
  await p.goto(B+'/accounts/login/'); await p.fill('#id_username',user); await p.fill('input[name=password]','pass');
  await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]); return {ctx,p,bad}; }
async function etat(p){ return p.evaluate(()=>({statut:(document.body.innerText.match(/(Brouillon|Visa chef de secteur|Visa chef de service|Visa COMAEQ|Publiée|À viser[^\n]*|En attente[^\n]*)/i)||[''])[0],boutons:[...document.querySelectorAll('main button, main a.btn')].filter(e=>e.offsetParent).map(e=>e.innerText.trim().replace(/\s+/g,' ')).filter(Boolean)})); }
(async()=>{
  const browser=await chromium.launch(); const J=[]; const t0=Date.now();
  const etapes=[['chef_secteur_a',/Viser/],['chef_service_a',/Viser/],['coma_comaeq',/(Viser|Valider|Publier)/]];
  for(const [u,re] of etapes){
    const {ctx,p,bad}=await login(browser,u); await p.goto(URL); await p.waitForLoadState('networkidle');
    const avant=await etat(p); const b=p.locator('button,a.btn').filter({hasText:re}).first();
    let clique=false;
    if(await b.count()&&await b.isVisible()){ const cases=p.locator('input[type=checkbox][name=confirmation]'); if(await cases.count()) await cases.first().check().catch(()=>{});
      await b.click(); await p.waitForTimeout(400); const m=p.locator('.modal.show button.btn-primary, .modal.show button:has-text("Viser"), dialog[open] button:has-text("Viser")').first(); if(await m.count()&&await m.isVisible()){ await Promise.all([p.waitForNavigation().catch(()=>{}),m.click()]); } await p.waitForLoadState('networkidle'); clique=true; }
    const apres=await etat(p); J.push({acteur:u,cherche:String(re),clique,avant:avant.boutons.slice(0,8),apresStatut:apres.statut,apresBoutons:apres.boutons.slice(0,6),bad});
    await p.screenshot({path:`${S}/shots/feuille_${J.length}_${u}.png`}); await ctx.close();
  }
  console.log(JSON.stringify({duree_s:(Date.now()-t0)/1000,J},null,1)); await browser.close();
})();
