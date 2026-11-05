const {chromium,B,R,login,flow}=require('./e2e_lib.js');
async function remplir(p,conf){await p.locator('select#conformity').selectOption(conf);await p.locator('textarea[name=body]').fill('E2E').catch(()=>{});for(const t of await p.locator('main input[type=text]:visible').all()){await t.fill('1').catch(()=>{});}}
(async()=>{const br=await chromium.launch();
 await flow('F3d_web_non_conforme_installation',async()=>{const o={};const {c,p}=await login(br,'equipier_a');await p.goto(B+'/maintenance/occurrences/37/execute/');await p.waitForLoadState('networkidle');await remplir(p,'NON_CONFORME');
  await p.locator('main button[type=submit]:visible').filter({hasText:/Terminer/}).click();await p.waitForTimeout(700);const m=p.locator('.modal.show button.btn-primary').first();if(await m.count()) await m.click();await p.waitForLoadState('networkidle');
  o.apres=(await p.innerText('main')).replace(/\s+/g,' ').slice(0,200);o.errs=[...new Set(p.errs)];await c.close();return o;});
 await flow('F3e_web_critique_sans_confirmation',async()=>{const o={};const {c,p}=await login(br,'cdt_a');await p.goto(B+'/maintenance/occurrences/1/execute/');await p.waitForLoadState('networkidle');await remplir(p,'CONFORME');
  o.case_confirmation=await p.locator('input[name=confirmation]').count();o.case_precochee=o.case_confirmation?await p.locator('input[name=confirmation]').first().isChecked():null;
  await p.locator('main button[type=submit]:visible').filter({hasText:/Terminer/}).click();await p.waitForTimeout(700);const m=p.locator('.modal.show button.btn-primary').first();if(await m.count()) await m.click();await p.waitForLoadState('networkidle');
  o.sans_case=(await p.innerText('main')).replace(/\s+/g,' ').match(/(Terminée|confirm[^.]{0,80}|Cochez[^.]{0,80}|valid[^.]{0,60})/i)?.[0];o.url=p.url().replace(B,'');
  if(o.case_confirmation){await p.goto(B+'/maintenance/occurrences/1/execute/');await p.waitForLoadState('networkidle');await remplir(p,'CONFORME');await p.locator('input[name=confirmation]').first().check();await p.locator('main button[type=submit]:visible').filter({hasText:/Terminer/}).click();await p.waitForTimeout(700);const m2=p.locator('.modal.show button.btn-primary').first();if(await m2.count()) await m2.click();await p.waitForLoadState('networkidle');o.avec_case=(await p.innerText('main')).replace(/\s+/g,' ').match(/(Terminée|valid[^.]{0,80})/i)?.[0];}
  o.errs=[...new Set(p.errs)];await c.close();return o;});
 console.log(JSON.stringify(R,null,1));await br.close();})();
