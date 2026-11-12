const {chromium}=require('playwright');const B='http://127.0.0.1:8800';
(async()=>{const b=await chromium.launch();
for(const u of ['equipier_a','chef_section_a','chef_secteur_a']){
 const c=await b.newContext({viewport:{width:1366,height:768}});const p=await c.newPage();
 await p.goto(B+'/accounts/login/');await p.fill('input[name=username]',u);await p.fill('input[name=password]',process.env.PW);await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]);
 const r=await p.goto(B+'/maintenance/occurrences/6/execute/');
 const btn=await p.$$eval('button',bs=>bs.map(x=>x.innerText.trim()).filter(t=>t&&t.length<40&&!/Déconnexion|Replier|Annuler|Confirmer|Rester|Quitter|Se |J'ai/.test(t)));
 console.log(u,r.status(),JSON.stringify(btn));await c.close();}
await b.close();})();
