const { chromium } = require('playwright'); const B='http://127.0.0.1:8800', S=process.argv[2];
(async()=>{ const br=await chromium.launch();
 for(const [u,nom] of [['equipier_a','A_equipier'],['chef_secteur_a','B_chef']]){
  const ctx=await br.newContext({viewport:{width:1366,height:768}}); const p=await ctx.newPage();
  await p.goto(B+'/accounts/login/'); await p.fill('#id_username',u); await p.fill('input[name=password]','pass'); await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]);
  await p.goto(B+'/quarts/'); await p.waitForLoadState('networkidle'); await p.screenshot({path:`${S}/shots/reel_${nom}.png`}); await ctx.close(); }
 for(const f of ['vue_quotidienne_A','vue_responsable_B']){ const ctx=await br.newContext({viewport:{width:1366,height:768}}); const p=await ctx.newPage(); await p.goto('file:///home/user/Matrix/docs/prototypes/quarts/'+f+'.html'); await p.waitForTimeout(500); await p.screenshot({path:`${S}/shots/maquette_${f}.png`}); await ctx.close(); }
 await br.close(); })();
