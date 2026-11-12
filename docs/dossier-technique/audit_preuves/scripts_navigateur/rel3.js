const {chromium}=require('playwright');const B='http://127.0.0.1:8800';const PW=process.env.PW;const fs=require('fs');
(async()=>{const b=await chromium.launch();
for(const u of ['equipier_a','chef_section_a','chef_secteur_a','chef_secteur_b','chef_service_a','cdt_b','cdt_abe']){
 const c=await b.newContext({viewport:{width:1366,height:900},deviceScaleFactor:1});const p=await c.newPage();
 await p.goto(B+'/accounts/login/');await p.fill('input[name=username]',u);await p.fill('input[name=password]',PW);await Promise.all([p.waitForNavigation(),p.click('button[type=submit]')]);
 const r=await p.goto(B+'/dashboard/passation/1/');
 const t=r.status()==200?await p.evaluate(()=>document.body.innerText.replace(/\s+/g,' ')):'';
 console.log(u,r.status(),r.status()==200?('len='+t.length+' '+(t.match(/Tâches.{0,260}/)||[''])[0]):'');
 if(u==='chef_section_a'){await p.screenshot({path:'audit/a14_chef_section.png',fullPage:true});fs.writeFileSync('audit/a14_text.txt',t);}
 await c.close();}
await b.close();})();
