const {chromium}=require('playwright');const B='http://127.0.0.1:8800';const PW=process.env.PW;
(async()=>{const b=await chromium.launch();
const login=async(u)=>{const c=await b.newContext({viewport:{width:1366,height:900}});const p=await c.newPage();await p.goto(B+'/accounts/login/');await p.fill('input[name=username]',u);await p.fill('input[name=password]',PW);await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]);return p;};
const txt=async(p)=>p.evaluate(()=>document.body.innerText.replace(/\s+/g,' '));
const cb=await login('cdt_b');await cb.goto(B+'/parametre/?tab=equipage');
let t=await txt(cb);console.log('cdt_b voit:',(t.match(/Relève — .{0,420}/)||[''])[0]);
console.log('boutons:',await cb.$$eval('form button',bs=>bs.map(x=>x.innerText.trim()+'|'+(x.closest('form').querySelector('[name=decision]')?.value||'')).join(' ; ')));
const btn=cb.locator('button:has-text("Valider")').first();
if(await btn.count()){await btn.click();await cb.waitForLoadState('networkidle');}
t=await txt(cb);console.log('après:',(t.match(/Relève — .{0,520}/)||[''])[0]);
console.log('alertes:',await cb.$$eval('.alert',e=>e.map(x=>x.innerText.trim()).join(' | ')));
const links=await cb.$$eval('a[href*="/dashboard/passation/"]',a=>a.map(x=>x.getAttribute('href')+':'+x.innerText.trim()));console.log('liens passation:',links);
await b.close();})();
