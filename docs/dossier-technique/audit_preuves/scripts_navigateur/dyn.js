const {chromium}=require('playwright');
const B='http://127.0.0.1:8800';const PW=process.env.PW;
(async()=>{const b=await chromium.launch();
const login=async(u)=>{const c=await b.newContext({viewport:{width:1366,height:768}});const p=await c.newPage();await p.goto(B+'/accounts/login/');await p.fill('input[name=username]',u);await p.fill('input[name=password]',PW);await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]);return p;};
const get=async(p,u)=>{const r=await p.goto(B+u);return [r.status(),p.url().replace(B,''),(await p.title())];};
const urls=['/dashboard/flotte/','/assets/plan/','/maintenance/occurrences/4/execute/','/rapports/bilan/','/taches/synthese/','/admin/','/parametre/?tab=modules','/parametre/?tab=seuils','/users/','/org/','/documentation/nouveau/','/retex/proposer/','/logistics/stock/','/quarts/echanges/','/dashboard/comanav/','/dashboard/passation/'];
for(const u of ['equipier_a','chef_section_a','chef_secteur_a','chef_service_a','cdt_a']){
 const p=await login(u);console.log('==',u);
 for(const x of urls){try{console.log(JSON.stringify(await get(p,x)),x);}catch(e){console.log('ERR',x,e.message.slice(0,50));}}
 await p.context().close();}
await b.close();})();
