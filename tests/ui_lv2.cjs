const {chromium}=require('playwright');
(async()=>{
 const url=process.argv[2];const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url);await page.getByText('● Silnik działa',{exact:true}).waitFor();
  await page.getByRole('button',{name:'BIBLIOTEKA',exact:true}).click();await page.getByRole('heading',{name:'Biblioteka LV2',exact:true}).waitFor();await page.getByText('Test LV2 Gain',{exact:true}).waitFor();
  await page.getByRole('button',{name:'EFEKT',exact:true}).click();await page.getByRole('heading',{name:'Parametry LV2',exact:true}).waitFor();
  const input=page.locator('#content input[type=range]').first();await input.evaluate(e=>{e.value='0.75';e.dispatchEvent(new Event('change',{bubbles:true}));});
  await page.waitForFunction(async()=>{const s=await(await fetch('/api/state')).json();return s.nodes.find(n=>n.module==='lv2:urn:jerzy:test:gain').parameters[0].value===.75;});
  await page.getByRole('button',{name:'INSTRUMENTY',exact:true}).click();await page.getByRole('heading',{name:'Syntezatory LV2',exact:true}).waitFor();await page.getByRole('heading',{name:'Klawiatura MIDI',exact:true}).waitFor();
  await page.getByLabel('Kanał odbioru MIDI',{exact:true}).selectOption('3');await page.waitForFunction(async()=>{const s=await(await fetch('/api/state')).json();return s.nodes.find(n=>n.instrument).midi_channel===3;});
  await page.waitForFunction(()=>state.nodes.find(n=>n.instrument).midi_channel===3);
  const note=page.getByRole('button',{name:'A4',exact:true});
  await Promise.all([page.waitForFunction(async()=>{const s=await(await fetch('/api/state')).json();return s.buses[1].peak>.001;}),note.click({delay:600})]);
  await page.waitForFunction(async()=>{const s=await(await fetch('/api/state')).json();return s.buses[1].peak===0;});
  await page.getByRole('button',{name:'SYSTEM',exact:true}).click();await page.locator('#diagnostics').filter({hasText:'JACK: działa'}).waitFor();
  await page.getByRole('button',{name:'BLUETOOTH / MIDI',exact:true}).click();await page.getByRole('heading',{name:'Bluetooth i MIDI',exact:true}).waitFor();
  if(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth))throw Error('Mobile horizontal overflow');
  if(errors.length)throw Error(errors.join('\n'));
  if(process.argv[3])await page.screenshot({path:process.argv[3],fullPage:true});
  console.log('PASS Chromium mobile: LV2 library, parameters, synth keyboard with real audio, MIDI channel, system and Bluetooth, no JS errors/overflow');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
