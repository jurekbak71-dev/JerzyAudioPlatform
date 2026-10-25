const { chromium } = require('playwright');
const fs=require('fs');
(async()=>{
 const url=process.argv[2],browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:390,height:844},deviceScaleFactor:1,isMobile:true,hasTouch:true});const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url);await page.getByText('● Silnik działa',{exact:true}).waitFor();
  await page.getByRole('button',{name:'INSTRUMENTY',exact:true}).click();
  await page.getByRole('button',{name:'AMBIENT enabled: WYŁ.',exact:true}).click();
  await page.getByRole('button',{name:'AMBIENT enabled: WŁ.',exact:true}).waitFor();
  await page.getByRole('button',{name:'MIKSER',exact:true}).click();await page.getByRole('heading',{name:'Mikser',exact:true}).waitFor();
  await page.getByRole('button',{name:'PRESETY',exact:true}).click();await page.getByPlaceholder('Nazwa presetu').fill('Telefon żółć');await page.getByRole('button',{name:'Zapisz całą sesję',exact:true}).click();await page.getByRole('heading',{name:'Telefon żółć',exact:true}).waitFor();
  await page.getByRole('button',{name:'BIBLIOTEKA',exact:true}).click();await page.getByRole('heading',{name:'Biblioteka modułów'}).waitFor();
  await page.getByRole('button',{name:'SYSTEM',exact:true}).click();await page.locator('#diagnostics').filter({hasText:'JACK: działa'}).waitFor();
  await page.getByRole('button',{name:'BLUETOOTH / MIDI',exact:true}).click();
  await page.getByRole('heading',{name:'Bluetooth i MIDI',exact:true}).waitFor();
  await page.getByRole('button',{name:'SYSTEM',exact:true}).click();
  await page.getByRole('button',{name:'ŁAŃCUCH',exact:true}).click();await page.getByRole('button',{name:'Instrumenty',exact:true}).click();
  const token=(await (await page.request.get(url+'/api/session')).json()).token;
  async function api(data){const r=await page.request.post(url+'/api/action',{headers:{'X-Jerzy-Token':token},data});if(!r.ok())throw Error(await r.text());return r.json();}
  const mx=await api({action:'add',module:'mx-delay-original',route:0});
  await page.getByRole('button',{name:'EFEKT',exact:true}).click();
  await page.locator('#content > section > select').selectOption(String(mx.id));
  await page.getByRole('heading',{name:'SILNIK A',exact:true}).waitFor();
  await page.getByLabel('Silnik A: Algorytm',{exact:true}).selectOption('1');
  await page.getByRole('heading',{name:'Tape Echo',exact:true}).waitFor();
  if(await page.locator('.engine').first().getByText('Silnik A: Volante — Wear',{exact:true}).count())throw Error('Inactive algorithm controls visible');
  await page.setViewportSize({width:1360,height:900});
  await page.screenshot({path:process.argv[3].replace('panel-mobile','panel-mx-studio'),fullPage:true});
  const current=await (await page.request.get(url+'/api/state')).json();const pro=current.nodes.find(n=>n.module==='bass-ambient-pro-original');
  await page.locator('#content > section > select').selectOption(String(pro.id));
  await page.getByRole('heading',{name:'GŁOŚNOŚĆ WYJŚCIOWA',exact:true}).waitFor();
  await page.getByRole('button',{name:'KRELL',exact:true}).click();
  await page.getByRole('heading',{name:'GŁOŚNOŚĆ INSTRUMENTU',exact:true}).waitFor();
  await page.getByRole('button',{name:'AMBIENT',exact:true}).click();
  await page.getByRole('heading',{name:'MODAL — rezonans i atak',exact:true}).waitFor();
  await page.screenshot({path:process.argv[3].replace('panel-mobile','panel-pro-studio'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:process.argv[3],fullPage:true});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
  if(overflow)throw Error('Panel wychodzi poza szerokość telefonu');if(errors.length)throw Error(errors.join('\n'));
  await page.route('**/api/state',async route=>{
   const response=await route.fetch();const value=await response.json();const node=value.nodes.find(n=>n.module==='bass-ambient-pro-original');
   if(node)Object.assign(node,{fault:1,bypass:true,user_bypass:false,fault_cause:3,cpu_percent:65.2,cpu_average_percent:61.4,cpu_peak_percent:88.7,fault_graph_cpu_percent:121.8,fault_budget_ms:5.80499});
   await route.fulfill({response,json:value});
  });
  await page.getByRole('button',{name:'INSTRUMENTY',exact:true}).click();
  await page.getByText(/łączne przeciążenie łańcucha/).waitFor();
  await page.getByText(/cały łańcuch 121.8%/).waitFor();
  if(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth))throw Error('Fault diagnostic overflows mobile viewport');
  if(errors.length)throw Error(errors.join('\n'));
  console.log('PASS Chromium desktop + 390×844: dynamic MX algorithm, PRO volume/modal tabs, instrument start, mixer, preset, library, diagnostics, no JS errors or horizontal overflow');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
