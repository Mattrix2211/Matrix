const {chromium}=require('playwright');const B='http://127.0.0.1:8800';
(async()=>{const b=await chromium.launch();const c=await b.newContext({viewport:{width:1366,height:768}});const p=await c.newPage();
await p.goto(B+'/accounts/login/');await p.fill('input[name=username]','cdt_a');await p.fill('input[name=password]',process.env.PW);await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]);
await p.goto(B+'/parametre/?tab=equipage');
console.log(await p.evaluate(()=>document.body.innerText.replace(/\s+/g,' ').slice(0,1800)));
const bt=await p.locator('button:has-text("synthèse")').count();console.log('boutons synthèse:',bt);
await p.click('button:has-text("Générer la synthèse")');await p.waitForLoadState('networkidle');console.log('URL',p.url());console.log(await p.evaluate(()=>[...document.querySelectorAll('.alert,.toast,.messages')].map(e=>e.innerText.trim()).join(' | ')));console.log(await p.evaluate(()=>document.body.innerText.replace(/\s+/g,' ').match(/Synthèses de passation.{0,200}/)[0]));await b.close();})();
