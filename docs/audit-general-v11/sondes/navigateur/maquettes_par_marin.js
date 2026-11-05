const { chromium } = require('playwright'); const B='http://127.0.0.1:8800';
(async()=>{ const br=await chromium.launch(); const ctx=await br.newContext({viewport:{width:1366,height:768}}); const p=await ctx.newPage();
 await p.goto(B+'/accounts/login/'); await p.fill('#id_username','chef_secteur_a'); await p.fill('input[name=password]','pass'); await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]);
 await p.goto(B+'/quarts/'); await p.click('a:has-text("Par marin")'); await p.waitForLoadState('networkidle'); await p.screenshot({path:process.argv[2]+'/shots/reel_B_parmarin.png'});
 console.log(p.url().replace(B,''), (await p.innerText('main')).replace(/\s+/g,' ').slice(0,200)); await br.close(); })();
