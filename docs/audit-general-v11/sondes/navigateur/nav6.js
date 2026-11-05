const { chromium } = require('playwright');
const B='http://127.0.0.1:8800', URL=B+'/quarts/feuille-service/2/2027-09-01/';
(async()=>{
  const browser=await chromium.launch(); const ctx=await browser.newContext({viewport:{width:1366,height:768}}); const p=await ctx.newPage();
  const dialogs=[]; p.on('dialog',async d=>{dialogs.push(d.type()+': '+d.message()); await d.accept();});
  const reqs=[]; p.on('request',r=>{ if(r.method()==='POST') reqs.push(r.method()+' '+r.url().replace(B,'')+' '+(r.postData()||'').slice(0,120)); });
  p.on('response',r=>{ if(r.request().method()==='POST') reqs.push('-> '+r.status()); });
  await p.goto(B+'/accounts/login/'); await p.fill('#id_username','chef_secteur_a'); await p.fill('input[name=password]','pass');
  await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]);
  await p.goto(URL); await p.waitForLoadState('networkidle');
  const b=p.locator('button:has-text("Viser (chef de secteur)")').first();
  console.log('formHTML:', await b.evaluate(e=>e.closest('form')?e.closest('form').outerHTML.slice(0,700):'pas de form'));
  await b.click(); await p.waitForTimeout(2500);
  console.log(JSON.stringify({dialogs,reqs,url:p.url().replace(B,''),messages:await p.evaluate(()=>[...document.querySelectorAll('.alert,.toast,[role=alert],[role=status]')].map(e=>e.innerText.trim()).filter(Boolean))}));
  await p.screenshot({path:process.argv[2]+'/shots/viser_secteur.png'});
  await browser.close();
})();
