const { chromium } = require('playwright');
const B='http://127.0.0.1:8800', URL=B+'/quarts/feuille-service/2/2027-09-02/';
async function login(browser,user){ const ctx=await browser.newContext({viewport:{width:1366,height:768}}); const p=await ctx.newPage();
  await p.goto(B+'/accounts/login/'); await p.fill('#id_username',user); await p.fill('input[name=password]','pass');
  await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]); return {ctx,p}; }
(async()=>{
  const browser=await chromium.launch();
  {const {ctx,p}=await login(browser,'equipier_a2'); await p.goto(URL); await p.click('button:has-text("Créer le brouillon")'); await p.waitForLoadState('networkidle');
   await p.click('button:has-text("Proposer")'); await p.waitForTimeout(500); const m=p.locator('.modal.show button.btn-primary').first(); if(await m.count()) await m.click(); await p.waitForLoadState('networkidle'); await ctx.close();}
  const out={};
  for(const u of ['chef_secteur_a','chef_service_a','coma_comaeq','coma_comanav','second_a','cdt_a','admin_navire','equipier_a']){
    const {ctx,p}=await login(browser,u); await p.goto(URL); await p.waitForLoadState('networkidle');
    out[u]=await p.evaluate(()=>[...document.querySelectorAll('main button, main a.btn')].filter(e=>e.offsetParent).map(e=>e.innerText.trim().replace(/\s+/g,' ')).filter(t=>/Viser|Renvoyer|Proposer|Corriger/.test(t)));
    await ctx.close();}
  console.log(JSON.stringify(out)); await browser.close();
})();
