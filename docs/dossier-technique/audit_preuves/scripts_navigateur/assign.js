const {chromium}=require('playwright');const B='http://127.0.0.1:8800';
(async()=>{const b=await chromium.launch();const c=await b.newContext();const p=await c.newPage();
await p.goto(B+'/accounts/login/');await p.fill('input[name=username]','equipier_a');await p.fill('input[name=password]',process.env.PW);await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]);
for(const id of [4,5,40]){const r=await p.goto(B+'/maintenance/occurrences/'+id+'/execute/');console.log('occ',id,r.status());}
await p.goto(B+'/maintenance/gestion/occurrences/');
console.log(await p.$$eval('button,a.btn',x=>x.map(e=>e.innerText.trim()).filter(t=>/assign|prendre|Exécuter/i.test(t)).slice(0,12)));
await b.close();})();
