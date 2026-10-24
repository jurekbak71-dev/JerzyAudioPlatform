const { chromium } = require('playwright');
const fs=require('fs');
(async()=>{
 const url=process.argv[2],browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844},deviceScaleFactor:1,isMobile:true,hasTouch:true});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url);await page.getByText('● Silnik działa',{exact:true}).waitFor();
  await page.getByRole('button',{name:'INSTRUMENTY',exact:true}).click();
  await page.getByRole('button',{name:'Ambient START/STOP: WYŁ.',exact:true}).click();
  await page.getByRole('button',{name:'Ambient START/STOP: WŁ.',exact:true}).waitFor();
  await page.getByRole('button',{name:'MIKSER',exact:true}).click();await page.getByRole('heading',{name:'Mikser',exact:true}).waitFor();
  await page.getByRole('button',{name:'PRESETY',exact:true}).click();await page.getByPlaceholder('Nazwa presetu').fill('Telefon żółć');await page.getByRole('button',{name:'Zapisz całą sesję',exact:true}).click();await page.getByRole('heading',{name:'Telefon żółć',exact:true}).waitFor();
  await page.getByRole('button',{name:'BIBLIOTEKA',exact:true}).click();await page.getByRole('heading',{name:'Biblioteka modułów'}).waitFor();
  await page.getByRole('button',{name:'SYSTEM',exact:true}).click();await page.locator('#diagnostics').filter({hasText:'JACK: działa'}).waitFor();
  await page.getByRole('button',{name:'ŁAŃCUCH',exact:true}).click();await page.getByRole('button',{name:'Instrumenty',exact:true}).click();
  await page.screenshot({path:process.argv[3],fullPage:true});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
  if(overflow)throw Error('Panel wychodzi poza szerokość telefonu');if(errors.length)throw Error(errors.join('\n'));
  console.log('PASS Chromium 390×844: instrument start, mixer, preset, library, diagnostics, no JS errors or horizontal overflow');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
