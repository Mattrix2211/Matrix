const {chromium}=require('playwright');const B='http://127.0.0.1:8800';const PW=process.env.PW;
(async()=>{const b=await chromium.launch();
const login=async(u)=>{const c=await b.newContext();const p=await c.newPage();await p.goto(B+'/accounts/login/');await p.fill('input[name=username]',u);await p.fill('input[name=password]',PW);await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]);return p;};
const e=await login('equipier_a');await e.goto(B+'/taches/');
await e.click('text=Ma tâche personnelle');await e.waitForTimeout(500);
console.log(await e.$$eval('form input:not([type=hidden]),form textarea,form select',els=>els.filter(x=>x.offsetParent).map(x=>x.name+':'+x.type+(x.checked?'(coché)':''))));
await e.fill('input[name=titre]','AUDIT tâche privée de test');
const cb=e.locator('input[name=partagee]');if(await cb.count()) console.log('case partagée cochée par défaut:',await cb.first().isChecked());
await e.locator('form:has(input[name=titre]) button[type=submit]').first().click();await e.waitForLoadState('networkidle');
await e.goto(B+'/taches/');
const link=await e.$$eval('a[href^="/taches/"]',a=>a.filter(x=>/AUDIT tâche privée/.test(x.innerText)).map(x=>x.getAttribute('href')));console.log('lien:',link);
for(const u of ['chef_section_a','chef_secteur_a','chef_service_a','cdt_a']){const p=await login(u);const r=await p.goto(B+link[0]);await p.goto(B+'/taches/');const t=await p.evaluate(()=>document.body.innerText);console.log(u,r.status(),'dans la liste:',/AUDIT tâche privée/.test(t));}
await b.close();})();
