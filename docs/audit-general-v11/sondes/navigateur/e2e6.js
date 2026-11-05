const {chromium,B,R,login,flow}=require('./e2e_lib.js');
(async()=>{const br=await chromium.launch();
 await flow('F4c_anomalie_envoi',async()=>{const o={};const {c,p}=await login(br,'equipier_a');await p.goto(B+'/logistics/anomalies/signaler/');await p.waitForLoadState('networkidle');
  const ab=p.locator('button:has-text("Abandonner")');if(await ab.count()){await ab.first().click();await p.waitForTimeout(400);const m=p.locator('.modal.show button').filter({hasText:/Abandonner|Confirmer|Oui/}).first();if(await m.count()) await m.click();await p.waitForLoadState('networkidle');}
  const s=p.locator('select[name=installation]');const vs=await s.locator('option').evaluateAll(x=>x.map(o=>o.value).filter(v=>v));await s.selectOption(vs[0]);await p.locator('main button:has-text("Suivant")').click();await p.waitForLoadState('networkidle');
  await p.locator('input[name=titre]').fill('Fuite pompe cale (E2E complet)');await p.locator('main button:has-text("Suivant")').click();await p.waitForLoadState('networkidle');
  await p.locator('textarea').first().fill('Description E2E');await p.locator('main button:has-text("Suivant")').click();await p.waitForLoadState('networkidle');
  o.etape4=(await p.innerText('main')).replace(/\s+/g,' ').slice(0,300);o.boutons=await p.evaluate(()=>[...document.querySelectorAll('main button')].filter(e=>e.offsetParent).map(e=>e.innerText.trim()).filter(Boolean));
  const fin=p.locator('main button:visible').filter({hasText:/Envoyer|Signaler l|Confirmer|Enregistrer/}).last();if(await fin.count()){await Promise.all([p.waitForLoadState('networkidle'),fin.click()]);}
  o.apres=p.url().replace(B,'');o.texte=(await p.innerText('main')).replace(/\s+/g,' ').slice(0,200);o.errs=[...new Set(p.errs)];await c.close();return o;});
 await flow('F3c_maintenance_web_nc',async()=>{const o={};const {c,p}=await login(br,'equipier_a');await p.goto(B+'/maintenance/occurrences/2/execute/');await p.waitForLoadState('networkidle');
  const groupes=await p.evaluate(()=>[...new Set([...document.querySelectorAll('input[type=radio]')].map(r=>r.name))]);o.groupes=groupes.length;
  for(const n of groupes){await p.locator(`input[type=radio][name=${n}][value="non_conforme"]`).first().check({force:true}).catch(()=>{});}
  await p.locator('textarea[name=body]').fill('Fuite constatée (E2E)').catch(()=>{});for(const t of await p.locator('main input[type=text]:visible').all()){await t.fill('1').catch(()=>{});}
  o.boutons=await p.evaluate(()=>[...document.querySelectorAll('main button[type=submit]')].filter(e=>e.offsetParent).map(e=>e.innerText.trim()));
  const envoi=p.locator('main button[type=submit]:visible').filter({hasText:/Terminer|Clôturer|Valider|Enregistrer|Envoyer/}).last();o.bouton_envoi=await envoi.count()?await envoi.innerText():null;
  if(await envoi.count()){await envoi.click();await p.waitForTimeout(600);const m=p.locator('.modal.show button.btn-primary').first();if(await m.count()) await m.click();await p.waitForLoadState('networkidle');}
  o.apres=(await p.innerText('main')).replace(/\s+/g,' ').slice(0,240);o.errs=[...new Set(p.errs)];o.bad=[...new Set(p.bad)];await c.close();return o;});
 await flow('F9b_interface',async()=>{const {c,p}=await login(br,'marin_abe_1');const o={};await p.goto(B+'/');const get=()=>p.evaluate(()=>document.documentElement.getAttribute('data-theme')||document.documentElement.dataset.bsTheme||'clair');o.avant=await get();
  await p.locator('button[aria-label^="Passer en mode"]').first().click();await p.waitForTimeout(700);o.apres_bascule=await get();await p.reload();await p.waitForLoadState('networkidle');o.apres_rechargement=await get();
  const lisibilite=await p.evaluate(()=>{const b=getComputedStyle(document.body);return {fond:b.backgroundColor,texte:b.color};});o.couleurs=lisibilite;
  await p.emulateMedia({media:'print'});await p.goto(B+'/quarts/');o.impression_barre_laterale_masquee=await p.evaluate(()=>{const s=document.querySelector('.mx-sidebar,aside,nav');return s?getComputedStyle(s).display==='none':'élément introuvable';});await p.emulateMedia({media:'screen'});await c.close();
  const m=await login(br,'marin_abe_1',{width:375,height:667});await m.p.goto(B+'/');const b=m.p.locator('button[aria-controls][aria-expanded]').first();o.mobile={bouton:await b.count()};if(await b.count()){o.mobile.etiquette=((await b.innerText()).trim())||await b.getAttribute('aria-label');await b.click();await m.p.waitForTimeout(500);o.mobile.ouvert=await b.getAttribute('aria-expanded');await m.p.keyboard.press('Escape');await m.p.waitForTimeout(500);o.mobile.apres_echap=await b.getAttribute('aria-expanded');}await m.c.close();return o;});
 console.log(JSON.stringify(R,null,1));await br.close();})();
