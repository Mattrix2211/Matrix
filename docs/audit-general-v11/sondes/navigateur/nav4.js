const { chromium } = require('playwright');
const B='http://127.0.0.1:8800';
async function login(browser,user,vp){ const ctx=await browser.newContext({viewport:vp}); const p=await ctx.newPage(); const errs=[];
  p.on('pageerror',e=>errs.push(String(e).slice(0,120))); p.on('console',m=>{if(m.type()==='error')errs.push(m.text().slice(0,120));});
  await p.goto(B+'/accounts/login/'); await p.fill('#id_username',user); await p.fill('input[name=password]','pass');
  await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]); return {ctx,p,errs}; }
(async()=>{
  const browser=await chromium.launch(); const R={};
  for(const user of ['equipier_a','chef_secteur_a','admin_navire']){
    const {ctx,p,errs}=await login(browser,user,{width:1366,height:768});
    const nav=await p.evaluate(()=>[...document.querySelectorAll('nav a[href], aside a[href], .mx-sidebar a[href]')].map(a=>({h:a.getAttribute('href'),t:a.innerText.trim().replace(/\s+/g,' ')})).filter(x=>x.t&&x.h.startsWith('/')&&!x.h.includes('logout')));
    const uniq=[...new Map(nav.map(x=>[x.h,x])).values()];
    const pages=[]; 
    for(const l of uniq){ const r=await p.goto(B+l.h,{waitUntil:'domcontentloaded'}); await p.waitForLoadState('networkidle').catch(()=>{});
      pages.push({h:l.h,t:l.t,s:r.status(),title:await p.title(),h1:await p.evaluate(()=>(document.querySelector('h1')||{}).innerText||null),overflow:await p.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth)}); }
    const titres=pages.map(x=>x.title); 
    R[user]={liensMenu:uniq.length,titresDistincts:new Set(titres).size,titreMatrixSeul:titres.filter(t=>t==='Matrix').length,sansH1:pages.filter(x=>!x.h1).map(x=>x.h),erreursHTTP:pages.filter(x=>x.s>=400).map(x=>x.h+':'+x.s),debordements:pages.filter(x=>x.overflow).map(x=>x.h),erreursConsole:[...new Set(errs)].slice(0,5)};
    await ctx.close();
  }
  // clavier + sauter au contenu
  {const {ctx,p}=await login(browser,'equipier_a',{width:1366,height:768}); await p.goto(B+'/'); const tabs=[];
   for(let i=0;i<6;i++){ await p.keyboard.press('Tab'); tabs.push(await p.evaluate(()=>{const e=document.activeElement;const cs=getComputedStyle(e);return (e.tagName+' '+(e.innerText||e.getAttribute('aria-label')||e.getAttribute('href')||'').trim().replace(/\s+/g,' ').slice(0,40)+' | outline='+cs.outlineStyle+' '+cs.outlineWidth+' boxShadow='+(cs.boxShadow!=='none'?'oui':'non'));})); }
   R.clavier=tabs; await ctx.close();}
  // téléphone
  {const {ctx,p}=await login(browser,'equipier_a',{width:375,height:667}); const o=[];
   for(const h of ['/','/taches/','/quarts/','/calendar/','/logistics/anomalies/','/maintenance/gestion/occurrences/','/assets/','/formations/']){ const r=await p.goto(B+h,{waitUntil:'networkidle'}).catch(()=>null); if(!r) continue; o.push(h+':'+r.status()+(await p.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth)?' DEBORDE':' ok')); }
   R.telephone375=o; await ctx.close();}
  console.log(JSON.stringify(R,null,1)); await browser.close();
})();
