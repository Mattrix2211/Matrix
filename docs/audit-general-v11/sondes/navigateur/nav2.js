const { chromium } = require('playwright');
const B='http://127.0.0.1:8800', S=process.argv[2];
async function login(browser,user,vp={width:1366,height:768}){
  const ctx=await browser.newContext({viewport:vp}); const p=await ctx.newPage(); const bad=[],errs=[];
  p.on('response',r=>{ if(r.url().startsWith(B)&&r.status()>=400) bad.push(r.status()+' '+r.url().replace(B,'')); });
  p.on('console',m=>{ if(m.type()==='error') errs.push(m.text().slice(0,140)); });
  await p.goto(B+'/accounts/login/'); await p.fill('#id_username',user); await p.fill('input[name=password]','pass');
  await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]); return {ctx,p,bad,errs};
}
(async()=>{
  const browser=await chromium.launch(); const R={};
  // P1 : ticket du chef de secteur
  {const {ctx,p,bad}=await login(browser,'chef_secteur_a');
   const carte=p.locator('a.btn:has-text("Ouvrir")', {has:undefined}).filter({hasText:'Ouvrir'});
   const href=await p.locator('a[href*="/logistics/tickets/1a696760"]').first().getAttribute('href').catch(()=>null);
   await p.locator('a[href*="/logistics/tickets/1a696760"]').first().click();
   await p.waitForLoadState('networkidle');
   R.P1={href,url:p.url().replace(B,''),titre:await p.title(),texte:(await p.innerText('body')).replace(/\s+/g,' ').slice(0,260),bad};
   await p.screenshot({path:S+'/shots/p1_404.png'}); await ctx.close();}
  // P2 : brouillon de signalement d'anomalie
  {const {ctx,p,bad}=await login(browser,'equipier_a');
   await p.goto(B+'/logistics/anomalies/signaler/'); await p.waitForLoadState('networkidle');
   const champs=await p.evaluate(()=>[...document.querySelectorAll('form input,form select,form textarea')].filter(e=>e.offsetParent&&e.type!=='hidden').map(e=>e.name+':'+e.type));
   const etape=await p.evaluate(()=>(document.body.innerText.match(/[ÉE]tape \d+ ?(sur|\/) ?\d+/)||[''])[0]);
   R.P2={champs,etape};
   // saisir du texte dans le premier champ texte/textarea, attendre l'enregistrement auto, quitter
   const zone=p.locator('form textarea:visible, form input[type=text]:visible').first();
   if(await zone.count()){ await zone.fill('Fuite à la pompe de cale tribord (audit)'); await p.waitForTimeout(3500); }
   await p.goto(B+'/'); await p.waitForLoadState('networkidle');
   const reprendre=p.locator('a:has-text("Reprendre")').first();
   R.P2.carteReprendre=await reprendre.count();
   if(R.P2.carteReprendre){ const h=await reprendre.getAttribute('href'); await reprendre.click(); await p.waitForLoadState('networkidle');
     R.P2.apresReprise={href:h,url:p.url().replace(B,''),titre:await p.title(),valeurRestauree:await p.evaluate(()=>{const z=document.querySelector('form textarea, form input[type=text]');return z?z.value:null;})}; }
   R.P2.bad=bad; await p.screenshot({path:S+'/shots/p2_reprise.png'}); await ctx.close();}
  // P3 : interface de la feuille de service selon le profil
  for(const u of ['equipier_a','equipier_a2','chef_secteur_a','coma_comaeq','admin_navire']){
   const {ctx,p}=await login(browser,u); await p.goto(B+'/quarts/feuille-service/2/2027-08-02/'); await p.waitForLoadState('networkidle');
   const btn=await p.locator('button:has-text("Créer"), button:has-text("brouillon"), button:has-text("Commencer")').allInnerTexts();
   (R.P3=R.P3||{})[u]={statut:(await p.title()),boutonsCreation:btn,texte:(await p.innerText('main').catch(()=>'')).replace(/\s+/g,' ').slice(0,140)}; await ctx.close();}
  console.log(JSON.stringify(R,null,1)); await browser.close();
})();
