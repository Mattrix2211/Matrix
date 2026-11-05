const { chromium } = require('playwright');
const B='http://127.0.0.1:8800', S=process.argv[2];
(async()=>{
  const browser=await chromium.launch(); const ctx=await browser.newContext({viewport:{width:1366,height:768}}); const p=await ctx.newPage(); const bad=[];
  p.on('response',r=>{ if(r.url().startsWith(B)&&r.status()>=400) bad.push(r.status()+' '+r.url().replace(B,'')); });
  await p.goto(B+'/accounts/login/'); await p.fill('#id_username','equipier_a'); await p.fill('input[name=password]','pass');
  await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]);
  const t0=Date.now(); const log=[];
  await p.goto(B+'/logistics/anomalies/signaler/'); await p.waitForLoadState('networkidle');
  for(let i=1;i<=4;i++){
    const info=await p.evaluate(()=>({etape:(document.body.innerText.match(/[ÉE]tape \d+ sur \d+/)||[''])[0],champs:[...document.querySelectorAll('form input,form select,form textarea')].filter(e=>e.offsetParent&&e.type!=='hidden').map(e=>e.name+':'+e.type+(e.required?'*':'')),boutons:[...document.querySelectorAll('form button')].filter(e=>e.offsetParent).map(e=>e.innerText.trim()),banniere:!!(document.body.innerText.match(/brouillon/i))}));
    log.push(info); await p.screenshot({path:`${S}/shots/p2_etape${i}.png`});
    // remplissage minimal
    for(const sel of await p.locator('form select:visible').all()){ const opts=await sel.locator('option').evaluateAll(o=>o.map(x=>x.value).filter(v=>v)); if(opts.length) await sel.selectOption(opts[0]); }
    for(const t of await p.locator('form textarea:visible').all()) await t.fill('Fuite à la pompe de cale (audit navigateur)');
    for(const t of await p.locator('form input[type=text]:visible').all()){ const n=await t.getAttribute('name'); if(n!=='q') await t.fill('Local pompes'); }
    const suiv=p.locator('form button:visible:has-text("Suivant"), form button:visible:has-text("Continuer")').first();
    if(i<3 && await suiv.count()){ await Promise.all([p.waitForLoadState('networkidle'),suiv.click()]); } else break;
  }
  const brouillonServeur=await p.evaluate(async()=>{const r=await fetch('/brouillons/');return r.status+' '+(await r.text()).slice(0,300);});
  console.log(JSON.stringify({log,brouillonServeur,bad,duree_s:(Date.now()-t0)/1000},null,1));
  await browser.close();
})();
