const { chromium } = require('playwright');
const B='http://127.0.0.1:8800';
(async()=>{
  const browser=await chromium.launch(); const out={};
  for(const u of ['admin_navire','chef_service_a','cdt_a']){
    const ctx=await browser.newContext({viewport:{width:1366,height:768}}); const p=await ctx.newPage();
    await p.goto(B+'/accounts/login/'); await p.fill('#id_username',u); await p.fill('input[name=password]','pass'); await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]);
    const r=await p.goto(B+'/parametre/?tab=notifications'); await p.waitForLoadState('networkidle');
    out[u]={status:r.status(),onglets:await p.evaluate(()=>[...document.querySelectorAll('[role=tab],.nav-tabs a,.nav-pills a')].map(e=>e.innerText.trim()).filter(Boolean)),titres:await p.evaluate(()=>[...document.querySelectorAll('main h2,main h3,main summary')].map(e=>e.innerText.trim()).slice(0,30)),formulaires:await p.evaluate(()=>[...document.querySelectorAll('main form')].map(f=>(f.querySelector('button[type=submit]')||{}).innerText?.trim()+' ['+[...f.querySelectorAll('input:not([type=hidden]),select')].map(i=>i.name).join(',')+']').slice(0,25))};
    await p.screenshot({path:process.argv[2]+`/shots/parametre_${u}.png`,fullPage:true}); await ctx.close();
  }
  console.log(JSON.stringify(out,null,1)); await browser.close();
})();
