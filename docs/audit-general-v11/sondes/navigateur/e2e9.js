const {chromium,B,R,login,flow}=require('./e2e_lib.js');
(async()=>{const br=await chromium.launch();
 await flow('F7_formation',async()=>{const o={};const {c,p}=await login(br,'equipier_a');await p.goto(B+'/formations/');await p.waitForLoadState('networkidle');o.cartes=await p.locator('a[href*="/formations/"]').count();
  const lien=p.locator('main a[href^="/formations/"]').filter({hasNotText:/Arbre/}).first();o.lien=await lien.getAttribute('href');await lien.click();await p.waitForLoadState('networkidle');
  o.fiche=await p.evaluate(()=>({h1:(document.querySelector('h1')||{}).innerText,btn:[...document.querySelectorAll('main button,main a.btn')].filter(e=>e.offsetParent).map(e=>e.innerText.trim().replace(/\s+/g,' ')).filter(Boolean).slice(0,12)}));
  const act=p.locator('main button:visible').filter({hasText:/Candidater|Réserver|Demander|Postuler|Je souhaite/}).first();
  if(await act.count()){o.action=await act.innerText();await act.click();await p.waitForTimeout(600);const m=p.locator('.modal.show button.btn-primary').first();if(await m.count())await m.click();await p.waitForLoadState('networkidle');o.apres=(await p.innerText('main')).replace(/\s+/g,' ').slice(0,200);}
  o.errs=[...new Set(p.errs)];o.bad=[...new Set(p.bad)];await c.close();return o;});
 await flow('F5c_proposer_echange',async()=>{const o={};const {c,p}=await login(br,'equipier_a2');await p.goto(B+'/quarts/');await p.waitForLoadState('networkidle');
  o.boutons=await p.evaluate(()=>[...document.querySelectorAll('main button,main a.btn,main a')].filter(e=>e.offsetParent&&/chang/i.test(e.innerText)).map(e=>e.innerText.trim().replace(/\s+/g,' ')).slice(0,6));await c.close();return o;});
 console.log(JSON.stringify(R,null,1));await br.close();})();
