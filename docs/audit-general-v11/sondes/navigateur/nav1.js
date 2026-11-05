const { chromium } = require('playwright');
const B='http://127.0.0.1:8800', S=process.argv[2];
async function login(browser,user){
  const ctx=await browser.newContext({viewport:{width:1366,height:768}});
  const p=await ctx.newPage(); const errs=[], bad=[];
  p.on('console',m=>{ if(m.type()==='error') errs.push(m.text().slice(0,160)); });
  p.on('pageerror',e=>errs.push('PAGEERROR '+String(e).slice(0,160)));
  p.on('response',r=>{ const u=r.url(); if(u.startsWith(B)&&r.status()>=400) bad.push(r.status()+' '+u.replace(B,'')); });
  p.on('requestfailed',r=>{ if(!r.url().startsWith(B)) bad.push('EXTERNE '+r.url().slice(0,100)); });
  await p.goto(B+'/accounts/login/'); await p.fill('#id_username',user); await p.fill('input[name=password]','pass');
  await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]);
  return {ctx,p,errs,bad};
}
(async()=>{
  const browser=await chromium.launch();
  const out={};
  for(const user of ['equipier_a','chef_secteur_a','coma_comaeq','cdt_a','second_a','admin_navire','terre_classe']){
    const {ctx,p,errs,bad}=await login(browser,user);
    const t0=Date.now(); await p.goto(B+'/',{waitUntil:'networkidle'}); const ms=Date.now()-t0;
    const m=await p.evaluate(()=>({titre:document.title,h1:(document.querySelector('h1')||{}).innerText,overflow:document.documentElement.scrollWidth>document.documentElement.clientWidth,cartes:document.querySelectorAll('.mx-carte').length,liens:document.querySelectorAll('a').length}));
    await p.screenshot({path:`${S}/shots/accueil_${user}.png`});
    out[user]={...m,ms,errs:[...new Set(errs)],bad:[...new Set(bad)]};
    await ctx.close();
  }
  console.log(JSON.stringify(out,null,1));
  await browser.close();
})();
