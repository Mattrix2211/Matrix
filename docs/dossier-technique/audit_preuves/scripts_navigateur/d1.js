const {chromium}=require('playwright');const B='http://127.0.0.1:8800';
(async()=>{const b=await chromium.launch();const c=await b.newContext({viewport:{width:1366,height:768}});const p=await c.newPage();
await p.goto(B+'/accounts/login/');await p.fill('input[name=username]','equipier_a');await p.fill('input[name=password]',process.env.PW);await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]);
await p.goto(B+'/maintenance/gestion/occurrences/');
const rows=await p.$$eval('tr',trs=>trs.map(t=>[t.innerText.replace(/\s+/g,' ').slice(0,90),[...t.querySelectorAll('a')].map(a=>a.getAttribute('href')+':'+a.textContent.trim()).join(' ')]));
rows.forEach(r=>console.log(r.join(' || ')));
await b.close();})();
