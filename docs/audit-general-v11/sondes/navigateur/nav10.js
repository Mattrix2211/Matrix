const { chromium } = require('playwright');
const B='http://127.0.0.1:8800';
(async()=>{ const browser=await chromium.launch(); const out={};
 for(const u of ['admin_navire','chef_service_a','admin']){ const ctx=await browser.newContext({viewport:{width:1366,height:768}}); const p=await ctx.newPage();
  await p.goto(B+'/accounts/login/'); await p.fill('#id_username',u); await p.fill('input[name=password]','pass'); await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]);
  await p.goto(B+'/parametre/?tab=notifications'); await p.waitForLoadState('networkidle');
  const tabs=await p.evaluate(()=>[...document.querySelectorAll('a[href*="tab="]')].map(a=>a.innerText.trim().replace(/\s+/g,' ')+' → '+a.getAttribute('href')));
  const res={};
  for(const t of [...new Set(tabs.map(x=>x.split('tab=')[1]))]){ const r=await p.goto(B+'/parametre/?tab='+t); await p.waitForLoadState('networkidle'); res[t]={s:r.status(),h:await p.evaluate(()=>[...document.querySelectorAll('main h1,main h2,main h3')].map(e=>e.innerText.trim()).filter(Boolean).slice(0,6)),forms:await p.evaluate(()=>[...document.querySelectorAll('main form')].map(f=>[...f.querySelectorAll('input[name],select[name],textarea[name]')].map(i=>i.name).filter(n=>n!=='csrfmiddlewaretoken').join(',')).filter(Boolean).slice(0,6))}; }
  out[u]={tabs,res}; await ctx.close(); }
 console.log(JSON.stringify(out,null,1)); await browser.close(); })();
