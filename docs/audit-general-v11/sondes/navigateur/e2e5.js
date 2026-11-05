const {chromium,B,R,login,flow}=require('./e2e_lib.js');
(async()=>{const br=await chromium.launch();
 await flow('F4b_anomalie_debug',async()=>{const o={};const {c,p}=await login(br,'equipier_a');await p.goto(B+'/logistics/anomalies/signaler/');await p.waitForLoadState('networkidle');
  const ab=p.locator('button:has-text("Abandonner")');if(await ab.count()){await ab.first().click();await p.waitForTimeout(400);const m=p.locator('.modal.show button').filter({hasText:/Abandonner|Confirmer|Oui/}).first();if(await m.count()) await m.click();await p.waitForLoadState('networkidle');}
  const s=p.locator('select[name=installation]');const vs=await s.locator('option').evaluateAll(x=>x.map(o=>o.value).filter(v=>v));await s.selectOption(vs[0]);await p.locator('main button:has-text("Suivant")').click();await p.waitForLoadState('networkidle');
  o.etape2=await p.evaluate(()=>[...document.querySelectorAll('main input,main select,main textarea,main button')].filter(e=>e.offsetParent||e.type==='radio').map(e=>e.tagName+':'+e.name+':'+e.type+':'+(e.value||'').slice(0,12)).slice(0,24));
  await p.locator('input[name=titre]').fill('Fuite pompe cale (E2E)');
  const g=p.locator('input[name=gravite][value="3"],label:has-text("3 — Moyenne")').first();if(await g.count()) await g.check({force:true}).catch(async()=>{await g.click();});
  await p.locator('main button:has-text("Suivant")').click();await p.waitForTimeout(800);o.apres_suivant=(await p.innerText('main')).replace(/\s+/g,' ').slice(0,260);o.erreurs=await p.evaluate(()=>[...document.querySelectorAll('.alert,.invalid-feedback,[role=alert]')].map(e=>e.innerText.trim()).filter(Boolean));
  o.etape_suivante=(await p.innerText('main')).match(/[ÉE]tape \d sur \d/)?.[0];await c.close();return o;});
 console.log(JSON.stringify(R,null,1));await br.close();})();
