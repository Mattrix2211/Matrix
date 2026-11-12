const {chromium}=require('playwright');const B='http://127.0.0.1:8800';
(async()=>{const b=await chromium.launch();const c=await b.newContext({viewport:{width:1366,height:900}});const p=await c.newPage();
await p.goto(B+'/accounts/login/');await p.fill('input[name=username]','chef_section_a');await p.fill('input[name=password]',process.env.PW);await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]);
await p.goto(B+'/taches/');const t=await p.evaluate(()=>document.body.innerText.replace(/\s+/g,' '));
for(const k of ['pendant','échéances','absent','Absences','Charge par marin']) console.log(k,'->',(t.match(new RegExp('.{0,60}'+k+'.{0,60}','i'))||['(absent)'])[0]);
await p.goto(B+'/');const h=await p.evaluate(()=>document.body.innerText.replace(/\s+/g,' '));
console.log('accueil chef_section: « Supervision » présent?',/Supervision/.test(h.replace(/SUPERVISION ADMINISTRATION/,'')),' | alerte retard en tête?',/retard/i.test(h.slice(0,900)));
await b.close();})();
