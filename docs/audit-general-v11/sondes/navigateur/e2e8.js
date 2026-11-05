const {chromium,B,R,login,flow}=require('./e2e_lib.js');
const msgs=p=>p.evaluate(()=>[...document.querySelectorAll('.alert,.invalid-feedback,.text-danger,[role=alert],.toast')].map(e=>e.innerText.trim().replace(/\s+/g,' ')).filter(Boolean).slice(0,6));
(async()=>{const br=await chromium.launch();
 await flow('F3f_occ37_nc',async()=>{const o={};const {c,p}=await login(br,'equipier_a');await p.goto(B+'/maintenance/occurrences/37/execute/');await p.waitForLoadState('networkidle');
  o.items=await p.evaluate(()=>[...document.querySelectorAll('main input,main select,main textarea')].filter(e=>e.offsetParent).map(e=>e.name+':'+e.type+(e.required?'*':'')).slice(0,20));
  await p.locator('button:has-text("Tout conforme")').click().catch(()=>{});await p.locator('select#conformity').selectOption('NON_CONFORME');
  const sub=p.locator('main button[type=submit]:visible').filter({hasText:/Terminer/});o.submit=await sub.count();await sub.click();await p.waitForTimeout(900);
  o.modale=await p.evaluate(()=>{const m=document.querySelector('.modal.show,dialog[open]');return m?m.innerText.replace(/\s+/g,' ').slice(0,200):null;});
  if(o.modale){await p.locator('.modal.show button.btn-primary,dialog[open] button.btn-primary').first().click();await p.waitForLoadState('networkidle');}
  o.messages=await msgs(p);o.statut=(await p.innerText('main')).replace(/\s+/g,' ').match(/(Terminée|En cours|En validation|En retard)/)?.[0];o.errs=[...new Set(p.errs)];await c.close();return o;});
 console.log(JSON.stringify(R,null,1));await br.close();})();
