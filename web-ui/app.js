'use strict';
let state,token,tab='ŁAŃCUCH',selected=null,route=0;
const tabs=['ŁAŃCUCH','EFEKT','INSTRUMENTY','MIKSER','BIBLIOTEKA','PRESETY','SYSTEM'];
const $=s=>document.querySelector(s);
function el(tag,text,cls){const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;return x;}
function button(text,fn,cls){const b=el('button',text,cls);b.onclick=()=>Promise.resolve(fn()).catch(error);return b;}
function error(e){$('#message').textContent=e.message||String(e);}
async function request(action,extra={}){const r=await fetch('/api/action',{method:'POST',headers:{'Content-Type':'application/json','X-Jerzy-Token':token},body:JSON.stringify({action,...extra})});const data=await r.json();if(!r.ok)throw Error(data.error);$('#message').textContent=data.message||'Zapisano';return data;}
async function refresh(renderPage=true){const r=await fetch('/api/state');const v=await r.json();if(!r.ok)throw Error(v.error);const changed=!state||JSON.stringify(v.nodes.map(n=>[n.id,n.bypass,n.fault]))!==JSON.stringify(state.nodes.map(n=>[n.id,n.bypass,n.fault]));state=v;if(state.session_restore_error)$('#message').textContent='Nie odtworzono sesji: '+state.session_restore_error;$('#connection').textContent='● Silnik działa';if(renderPage||changed)render();updateMeters();}
async function action(name,data){const r=await request(name,data);await refresh();return r;}
function panel(name){const s=el('section');s.append(el('h2',name));$('#content').append(s);return s;}
function row(...children){const r=el('div',undefined,'row');r.append(...children);return r;}
function select(options,value,fn){const s=el('select');for(const [v,label]of options){const o=el('option',label);o.value=v;s.append(o);}s.value=value;s.onchange=()=>Promise.resolve(fn(s.value)).catch(error);return s;}
function slider(label,value,min,max,step,fn,unit=''){const l=el('label');const head=el('b');const format=v=>Number(v).toLocaleString('pl-PL',{maximumSignificantDigits:4})+' '+unit;const out=el('span',format(value));head.append(el('span',label),out);l.append(head);const i=el('input');i.type='range';i.min=min;i.max=max;i.step=step;i.value=value;i.oninput=()=>{out.textContent=format(i.value);};i.onchange=()=>Promise.resolve(fn(Number(i.value))).catch(error);l.append(i);return l;}
function render(){
 $('#tabs').replaceChildren(...tabs.map(t=>button(t,()=>{tab=t;render();},tab===t?'active':'')));$('#content').replaceChildren();
 if(!state)return;
 if(tab==='ŁAŃCUCH')chain();if(tab==='EFEKT')effect();if(tab==='INSTRUMENTY')instruments();if(tab==='MIKSER')mixer();if(tab==='BIBLIOTEKA')library();if(tab==='PRESETY')presets();if(tab==='SYSTEM')system();
}
function addControl(s,instrumentsOnly=false){
 const entries=state.library.filter(x=>x.id!=='bass-ambient-original'&&(!instrumentsOnly||x.instrument)&&(x.id==='utility-gain-meter'||x.id==='cab-ir'||x.compatibility?.passed));
 if(!entries.length){s.append(el('p','Brak modułów. Zainstaluj paczkę w Bibliotece.'));return;}
 let module='',asset='';
 const ir=select([['','Wybierz plik IR'],...state.irs.map(n=>[n,n])],'',v=>{asset=v;add.disabled=!module||(module==='cab-ir'&&!asset);});ir.hidden=true;ir.setAttribute('aria-label','Plik IR dla nowego CAB');
 const picker=select([['','Wybierz moduł do dodania'],...entries.map(x=>[x.id,x.name])],'',v=>{module=v;ir.hidden=v!=='cab-ir';hint.hidden=v!=='cab-ir'||state.irs.length>0;add.disabled=!v||(v==='cab-ir'&&!asset);});picker.setAttribute('aria-label','Nowy moduł');
 const hint=el('p','Najpierw wgraj WAV w BIBLIOTECE → Import impulsu CAB / IR.');hint.hidden=true;
 const add=button('＋ Dodaj moduł',async()=>{if(!module)throw Error('Wybierz moduł');const result=await action('add',{module,route:instrumentsOnly?1:route,asset:module==='cab-ir'?asset:''});selected=result.id;render();},'primary');add.disabled=true;s.append(row(picker,ir,add),hint);
}
function chain(){const s=panel('Łańcuch brzmienia');s.append(row(...['Gitara','Instrumenty'].map((t,i)=>button(t,()=>{route=i;render();},i===route?'active':''))));s.append(el('p',route===0?'HeadRush → efekty → CAB / IR → mikser':'Instrumenty → efekty → mikser'));const grid=el('div',undefined,'chain');state.nodes.forEach((n,index)=>{if(n.route!==route)return;const c=el('article',undefined,'card node'+(n.bypass?' off':'')+(selected===n.id?' selected':''));if(n.fault)c.append(el('p',n.fault===1?'Ochrona CPU — bypass':'Błąd sygnału — bypass','fault'));c.append(el('span',n.instrument?'INSTRUMENT':'EFEKT','badge'),el('h3',n.name),el('p',n.bypass?'BYPASS — sygnał bez efektu':'AKTYWNY'),...(n.asset?[el('p','IR: '+n.asset.split('/').pop())]:[]));c.append(row(button('Parametry',()=>{selected=n.id;tab='EFEKT';render();}),button(n.bypass?'Włącz':'Bypass',()=>action('bypass',{id:n.id,value:n.bypass?0:1}))));c.append(row(button('←',()=>action('move',{id:n.id,value:Math.max(0,index-1)})),button('→',()=>action('move',{id:n.id,value:Math.min(state.nodes.length-1,index+1)})),button('Usuń',()=>action('remove',{id:n.id}),'danger')));grid.append(c);});s.append(grid);addControl(s);}
function choiceControl(label,options,value,fn){const l=el('label',label),input=select(options,value,fn);input.setAttribute('aria-label',label);l.append(input);return l;}
function parameter(n,p,i){const fn=value=>action('param',{id:n.id,index:i,value});if(n.module==='atomic-cluster-original'&&p.id==='atoms'){const l=el('label','Liczba atomów');l.append(select(Array.from({length:64},(_,k)=>[k+1,String(k+1)]),Math.round(64**p.value),v=>fn(Math.log(Number(v))/Math.log(64))));return l;}if(p.normalized_choices){const names=p.normalized_choices;return choiceControl(p.label,names.map((name,k)=>[k,name]),Math.round(p.value*(names.length-1)),v=>fn(Number(v)/(names.length-1)));}if(p.choices){return choiceControl(p.label,p.choices.split('|').map((t,k)=>[k,t]),p.value,v=>fn(Number(v)));}if(p.integer&&p.min===0&&p.max===1)return button(p.label+': '+(p.value?'WŁ.':'WYŁ.'),async()=>{await fn(p.value?0:1);await refresh();},p.value?'active':'');if(p.id==='root'){const names=['C','C♯','D','D♯','E','F','F♯','G','G♯','A','A♯','H'];const l=el('label','Nuta podstawowa');l.append(select(Array.from({length:p.max-p.min+1},(_,k)=>{const v=k+p.min;return[v,names[v%12]+(Math.floor(v/12)-1)];}),p.value,v=>fn(Number(v))));return l;}if(!p.integer&&p.min===0&&p.max===1)return slider(p.label,p.value*100,0,100,.1,v=>fn(v/100),'%');return slider(p.label,p.value,p.min,p.max,p.integer?1:(p.max-p.min)/1000,fn,p.unit);}
function controls(container,n,predicate){const grid=el('div',undefined,'grid controls');n.parameters.forEach((p,i)=>{if(predicate(p,i))grid.append(parameter(n,p,i));});container.append(grid);}
function orderedControls(container,n,ids){const grid=el('div',undefined,'grid controls');for(const id of ids){const i=n.parameters.findIndex(p=>p.id===id);if(i>=0)grid.append(parameter(n,n.parameters[i],i));}container.append(grid);}
function rackPanel(parent,n,title,predicate){const card=el('article',undefined,'rack');card.append(el('h3',title));controls(card,n,predicate);parent.append(card);return card;}
function nodeHeading(s,n){s.append(el('p',(n.route===0?'TOR GITARY':'TOR INSTRUMENTÓW')+' · #'+n.id,'eyebrow'));if(n.asset)s.append(el('h3','IR: '+n.asset.split('/').pop()));s.append(button(n.bypass?'Włącz moduł':'Bypass',()=>action('bypass',{id:n.id,value:n.bypass?0:1}),n.bypass?'':'active'));if(n.fault)s.append(el('p',n.fault===1?'Ochrona audio: moduł przekroczył budżet CPU i został pominięty. Zwiększ bufor lub zmniejsz obciążenie przed ponownym włączeniem.':'Ochrona audio: nieprawidłowy poziom wyjściowy; moduł pominięty.','fault'));}
function mxControls(s,n){
 rackPanel(s,n,'Wejście i wyjście',p=>['outputTrim','inputTrim','mix','routing','spill','machineCondition'].includes(p.id));
 const engines=el('div',undefined,'engine-grid');
 for(let slot=0;slot<2;slot++){
  const prefix='slot'+slot+'_',algorithm=n.parameters.find(p=>p.id===prefix+'algorithm');
  const chosen=Math.round(algorithm.value*8),card=el('article',undefined,'rack engine');card.append(el('h3','SILNIK '+['A','B'][slot]));
  controls(card,n,p=>[prefix+'enable',prefix+'algorithm'].includes(p.id));
  card.append(el('h4',algorithm.normalized_choices?.[chosen]||'Parametry algorytmu'));
  controls(card,n,p=>p.id.startsWith(prefix+'algo'+chosen+'_'));
  const sync=n.parameters.find(p=>p.id===prefix+'sync').value>=.5;
  card.append(el('h4','Ustawienia silnika'));
  controls(card,n,p=>['level','feedback','pan','duck','sync',sync?'division':'time'].some(k=>p.id===prefix+k));
  if(chosen===0){const heads=el('details');heads.append(el('summary','Panorama czterech głowic'));controls(heads,n,p=>p.id.startsWith(prefix+'headPan'));card.append(heads);}
  engines.append(card);
 }
 s.append(engines);
 const fx=el('details');fx.append(el('summary','Dodatkowe efekty wet — 4 sloty'));
 for(let slot=0;slot<4;slot++){
  const prefix='fx'+slot+'_',type=n.parameters.find(p=>p.id===prefix+'type'),card=el('article',undefined,'rack');card.append(el('h3','WET FX '+(slot+1)));controls(card,n,p=>p.id===prefix+'type');
  if(type.value>.01){const chosen=Math.round(type.value*5),fields=['amount','route',...([1,2].includes(chosen)?['rate','depth']:chosen===4?['drive']:['depth'])];controls(card,n,p=>fields.some(k=>p.id===prefix+k));}fx.append(card);
 }s.append(fx);
}
let proPart='bass',proPage='Brzmienie',drumSound=0;
function proControls(s,n){
 rackPanel(s,n,'GŁOŚNOŚĆ WYJŚCIOWA',p=>p.id==='master');
 const source=n.parameters.find(p=>p.id==='performanceSource').value;const play=el('article',undefined,'rack');play.append(el('h3','Gra i generatory'));orderedControls(play,n,['performanceSource',...(source===1?[]:['autoPlay',source===2?'harmonyRoot':'autoRoot']),...(n.parameters.find(p=>p.id==='clockSource').value===0?['internalTempo']:[]),'fxEnabled']);s.append(play);const global=el('details');global.append(el('summary','Harmonia i sterowanie MIDI'));controls(global,n,p=>['autoHarmony','harmonyBars','harmonyLink',...(source===0?['modularMidi']:[]),'clockSource'].includes(p.id));s.append(global);
 s.append(row(...[['bass','BAS'],['pad','AMBIENT'],['arp','ARP'],['drums','PERKUSJA'],['krell','KRELL'],['mix','MIKSER'],['master','MASTER FX']].map(([id,label])=>button(label,()=>{proPart=id;render();},proPart===id?'active':''))));
 if(proPart==='mix'){
  for(let track=0;track<8;track++)rackPanel(s,n,['Bas','Ambient','Arp','Kick','Snare','Hi-hat','Aux','Krell'][track],p=>p.id.startsWith('mix'+track));
  rackPanel(s,n,'Powroty efektów',p=>p.group===21);return;
 }
 const part=proPart;if(part==='master')proPage='Efekty';const prefix=part==='bass'?'':part+'_',level=part==='drums'?'drumLevel':part+'Level';
 rackPanel(s,n,'GŁOŚNOŚĆ INSTRUMENTU',p=>p.id===level);
 controls(s,n,p=>p.id===part);
 s.append(row(...(part==='master'?['Efekty']:['Brzmienie','Generator','Efekty']).map(name=>button(name,()=>{proPage=name;render();},proPage===name?'active':''))));
 const group={bass:[0,1],pad:[2],arp:[6],drums:[7,8,9,10,11,12],krell:[23],master:[]}[part];
 const isFX=p=>part==='bass'?p.group===3:(p.id.startsWith(prefix)&&/^(fx|chorus|delay|grain|reverb|comp|feedback|wow|flutter|damage|freeze|width|order)/.test(p.id.slice(prefix.length)));
 if(proPage==='Efekty'){

  controls(s,n,p=>p.id===part+'FX');
  const fxTypes=[['Drive / Comp','fxDrive',/^(fxSaturation|comp)/],['Chorus','fxChorus',/^chorus/],['Delay','fxDelay',/^(delay|feedback|wow|flutter|damage|freeze)/],['Granular','fxGrain',/^grain/],['Reverb','fxReverb',/^reverb/],['Stereo','fxWidth',/^width/]];
  for(const [name,powerId,pattern] of fxTypes){const powerKey=prefix+powerId,enabled=n.parameters.find(p=>p.id===powerKey);const card=rackPanel(s,n,name,p=>p.id===powerKey);if(enabled?.value)controls(card,n,p=>p.id.startsWith(prefix)&&pattern.test(p.id.slice(prefix.length)));}
  rackPanel(s,n,'Kolejność FX',p=>p.id.startsWith(prefix+'order'));return;
 }
 if(proPage==='Generator'&&source===1&&n.parameters.find(p=>p.id===part+'MidiMode')?.value===0){controls(s,n,p=>p.id===part+'MidiMode');s.append(el('p','Tryb nut MIDI: generator jest wyłączony. Wybierz Generator / Sequencer powyżej, aby zobaczyć jego parametry.'));return;}
 const generatorIds=/^(arp(Pattern|Division|Octaves|Steps|Pulses|Range|Gate|PitchRandom|Swing|Velocity|PanMode)|drum(Length|Division|Swing|Humanize)|krell(Cycle|Space|PitchRange)|style|scale|division|bars|meter|numerator|denominator|seed|chord|density|movement|gate|swing|variation|slide|accent|latch|restart|evolve|humanize|fill|bassOctaves|autoHarmony|harmonyBars|harmonyRoot|harmonyLink)/;
 controls(s,n,p=>group.includes(p.group)&&!(p.id==='direct'&&source!==0)&&!(part==='pad'&&p.id.startsWith('krell')&&n.parameters.find(p=>p.id==='padMode').value!==2)&&!(part==='bass'&&p.id.startsWith('guitar')&&n.parameters.find(p=>p.id==='model').value!==3)&&!(part==='drums'&&p.group>=8&&p.group<=12)&&!/^drum[0-3]_step/.test(p.id)&&p.id!==level&&p.id!==part&&!isFX(p)&&((proPage==='Generator')===generatorIds.test(p.id)));
 if(proPage==='Generator')controls(s,n,p=>p.id===part+'MidiMode');
 if(part==='drums'&&proPage==='Brzmienie'){s.append(choiceControl('Brzmienie perkusji',[[0,'Kick'],[1,'Snare'],[2,'Hi-hat'],[3,'Aux']],drumSound,v=>{drumSound=Number(v);render();}));rackPanel(s,n,'Głośność brzmienia',p=>p.id==='drum'+drumSound+'_level');controls(s,n,p=>p.id.startsWith('drum'+drumSound+'_')&&!p.id.includes('_step')&&!p.id.endsWith('_level'));}
 // Drum grid stays in a compact dedicated section, rather than 256 scattered sliders.
 if(part==='drums'&&proPage==='Generator')for(let lane=0;lane<4;lane++){
  const card=el('article',undefined,'rack');card.append(el('h3',['Kick','Snare','Hi-hat','Aux'][lane]));
  const length=Math.round(n.parameters.find(p=>p.id==='drumLength').value);const grid=el('div',undefined,'step-grid');
  n.parameters.forEach((p,i)=>{const match=p.id.match(new RegExp('^drum'+lane+'_step(\\d+)$'));if(match&&Number(match[1])<length)grid.append(button(String(Number(match[1])+1),()=>action('param',{id:n.id,index:i,value:p.value?0:100}),p.value?'active':''));});card.append(grid);s.append(card);
 }
 if(part==='bass'||part==='pad')rackPanel(s,n,'MODAL — rezonans i atak',p=>p.id===part+'Body'||p.id===part+'AttackTransient');
}
function effect(){const s=panel('Parametry modułu');if(!state.nodes.length){s.append(el('p','Dodaj moduł do łańcucha.'));return;}const n=state.nodes.find(x=>x.id===selected)||state.nodes[0];selected=n.id;s.append(select(state.nodes.map(x=>[x.id,x.name+' #'+x.id]),n.id,v=>{selected=Number(v);render();}));nodeHeading(s,n);
 if(n.module==='mx-delay-original')mxControls(s,n);
 else if(n.module==='bass-ambient-pro-original')proControls(s,n);
 else{
  const levelIds=n.instrument?['master','bassLevel','padLevel']:['level','volume'];rackPanel(s,n,'GŁOŚNOŚĆ',p=>levelIds.includes(p.id));
  if(n.module==='big-muff-original'){
   rackPanel(s,n,'Model obwodu',p=>p.id==='circuit');
   const circuit=n.parameters.find(p=>p.id==='circuit').value;
   if(circuit===0)rackPanel(s,n,'Model klasyczny',p=>p.id==='model');
   s.append(el('p','Model klasyczny działa po wybraniu Legacy w Modelu obwodu. Pełny solver obwodowy wymaga znacznie więcej CPU.'));
  }
  controls(s,n,p=>!levelIds.includes(p.id)&&!(n.module==='big-muff-original'&&['model','circuit'].includes(p.id)));
 }
 const midi=el('details');midi.append(el('summary','Mapowanie MIDI CC'));let learnIndex=0;midi.append(row(select(n.parameters.map((p,i)=>[i,p.label,p.group]).filter(x=>n.module!=='bass-ambient-pro-original'||x[2]!==13),0,v=>{learnIndex=Number(v);}),button('Ucz MIDI CC',()=>request('learn',{id:n.id,index:learnIndex}))));s.append(midi,el('p','Latencja modułu: '+n.latency+' próbek.'));
 const presetName=el('input');presetName.type='text';presetName.placeholder='Nazwa presetu modułu';s.append(presetName,button('Zapisz preset modułu',()=>action('module-preset-save',{name:presetName.value,id:n.id})));
 const available=state.module_presets.filter(x=>x.module===n.module);if(available.length){let preset=available[0].name;s.append(row(select(available.map(x=>[x.name,x.name]),preset,v=>{preset=v;}),button('Wczytaj preset modułu',()=>action('module-preset-load',{name:preset,id:n.id}))));}
}
function instruments(){const s=panel('Instrumenty');state.nodes.filter(n=>n.instrument).forEach(n=>{
 const c=el('article',undefined,'card');c.append(el('h3',n.name));
 if(n.module==='bass-ambient-pro-original'){
  orderedControls(c,n,['master']);orderedControls(c,n,['performanceSource','autoPlay','internalTempo']);
  const strips=el('div',undefined,'instrument-strips');
  for(const [part,label,level] of [['bass','BAS','bassLevel'],['pad','AMBIENT','padLevel'],['arp','ARP','arpLevel'],['drums','PERKUSJA','drumLevel'],['krell','KRELL','krellLevel']]){
   const strip=el('article',undefined,'channel-strip rack');strip.append(el('h3',label));orderedControls(strip,n,[level,part]);strip.append(button('Parametry',()=>{selected=n.id;proPart=part;proPage='Brzmienie';tab='EFEKT';render();}));strips.append(strip);
  }c.append(strips);
 }else{orderedControls(c,n,['master','bassLevel','padLevel']);controls(c,n,p=>['bass','pad','auto_root'].includes(p.id));c.append(button('Otwórz instrument',()=>{selected=n.id;tab='EFEKT';render();}));}
 s.append(c);
 });addControl(s,true);}
function mixer(){const s=panel('Mikser');const grid=el('div',undefined,'grid');state.buses.forEach((b,i)=>{const c=el('article',undefined,'card');const change=extra=>{Object.assign(b,extra);return request('mix',{route:i,...b});};c.append(el('h3',i===0?'Gitara':'Instrumenty'),slider('Poziom',b.gain,0,2,.01,gain=>change({gain})),slider('Panorama',b.pan,-1,1,.01,pan=>change({pan})),row(button(b.mute?'Wyciszony':'MUTE',async()=>{await change({mute:!b.mute});await refresh();},b.mute?'active':''),button('SOLO',async()=>{await change({solo:!b.solo});await refresh();},b.solo?'active':'')));const meter=el('meter');meter.min=0;meter.max=1;meter.id='bus'+i;c.append(meter);grid.append(c);});s.append(grid,slider('Suma',state.master,0,2,.01,value=>request('master',{value})),slider('Wspólne tempo',state.bpm,20,400,1,value=>request('bpm',{value})),button('Limiter ochronny: '+(state.limiter?'WŁ.':'WYŁ.'),()=>action('limiter',{value:state.limiter?0:1}),state.limiter?'active':''),slider('Próg zabezpieczenia',state.ceiling,.1,1,.01,value=>request('ceiling',{value})));s.append(el('p','Limiter ogranicza szczyty do wybranego progu. Licznik clip pokazuje przekroczenia przed ograniczeniem.'));}
async function readBase64(file){const data=new Uint8Array(await file.arrayBuffer());let text='';for(let i=0;i<data.length;i+=8192)text+=String.fromCharCode(...data.subarray(i,i+8192));return btoa(text);}
function library(){const s=panel('Biblioteka modułów');state.library.forEach(x=>{const c=el('article',undefined,'card');c.append(el('h3',x.name+(x.id==='bass-ambient-original'?' — bez PRO, stare sesje':'')),el('p',x.compatibility&&x.compatibility.passed?'DSP porównany z oryginałem · źródło '+x.compatibility.reference_commit.slice(0,8):'Moduł narzędziowy lub wcześniejsza wersja bez potwierdzenia oryginalnego DSP'),el('p','Wersja '+x.version+' · ABI '+x.abi),button('Odinstaluj',()=>action('module-remove',{module:x.id}),'danger'));if(x.previous)c.append(button('Przywróć poprzednią wersję',()=>action('module-rollback',{module:x.id})));s.append(c);});const f=el('input');f.type='file';f.accept='.jamod';const sum=el('input');sum.type='text';sum.placeholder='SHA256 paczki z zaufanego źródła';const trust=el('input');trust.type='checkbox';const label=el('label','Ufam autorowi tego wykonywalnego modułu ');label.append(trust);s.append(el('h3','Instalacja lub aktualizacja z paczki'),f,sum,label,button('Sprawdź i zainstaluj',async()=>{if(!f.files[0])throw Error('Wybierz paczkę');await action('module-import',{data:await readBase64(f.files[0]),sha256:sum.value.trim(),trust:trust.checked});},'primary'));const ir=el('input');ir.type='file';ir.accept='.wav';s.append(el('h3','Import impulsu CAB / IR'),ir,button('Dodaj IR',async()=>{if(!ir.files[0])throw Error('Wybierz WAV');await action('ir-import',{name:ir.files[0].name,data:await readBase64(ir.files[0])});}));s.append(el('p','Paczki pobieraj z oficjalnych wydań JerzyAudioPlatform. Instalator modułów sprawdza katalog SHA256; Pi nie potrzebuje internetu.'));}
function presets(){const s=panel('Presety sesji');const name=el('input');name.type='text';name.placeholder='Nazwa presetu';s.append(name,button('Zapisz całą sesję',()=>action('preset-save',{name:name.value}),'primary'));state.presets.forEach(name=>s.append(el('h3',name),button('Wczytaj',()=>action('preset-load',{name}))));}
function system(){const s=panel('System i audio');s.append(button(state.thru_jack_disabled?'Przywróć THRU JACK':'Wyłącz THRU JACK',()=>action('thru',{value:state.thru_jack_disabled?1:0})),el('p','THRU JACK dotyczy bezpośrednich połączeń wejście → wyjście. Wewnętrzny monitoring HeadRush wymaga ustawienia na urządzeniu.'));s.append(el('p',state.client+' · '+state.sample_rate+' Hz · '+state.buffer+' próbek · '+state.buffer_ms.toFixed(2)+' ms na bufor'),el('p','Profil zmienia rozmiar bufora, pozostawiając częstotliwość i konfigurację urządzenia JACK.'));s.append(row(...[['Niska latencja',64],['Zrównoważony',256],['Duża stabilność',512]].map(([name,value])=>button(name,()=>action('buffer',{value})))));s.append(select([64,128,256,512,1024].map(x=>[x,x+' próbek']),state.buffer,v=>action('buffer',{value:Number(v)})));s.append(el('p','Dla pełnych DSP zacznij od 256 lub 512 próbek. Bufor jest zapamiętywany po restarcie. Zmiana wymaga zainstalowanej usługi. Zmiana częstotliwości i liczby okresów nie jest jeszcze obsługiwana przez panel.'));const diag=el('pre');diag.id='diagnostics';s.append(diag,el('p','Wersja '+state.version+' · '+state.platform));}
function updateMeters(){if(!state)return;$('#meter').textContent='CPU '+state.cpu.toFixed(1)+'% · XRUN '+state.xruns+' · Peak '+state.peak.toFixed(3)+' · Clip '+state.clips;state.buses.forEach((b,i)=>{const meter=$('#bus'+i);if(meter)meter.value=b.peak;});if($('#diagnostics'))$('#diagnostics').textContent='JACK: działa\nCPU audio: '+state.cpu.toFixed(1)+'%\nXRUN: '+state.xruns+'\nRMS: '+state.rms.toFixed(4)+'\nNaN/Inf: '+state.invalid_samples+'\nBloki: '+state.blocks+'\nRAM panelu: '+(state.web_ram_mb||0).toFixed(1)+' MB';}
const recovery=row(button('Restart audio',()=>action('restart-audio',{})),button('Odzyskaj audio bez efektów',()=>action('recover-audio',{}),'danger'));recovery.classList.add('recovery');$('header').append(recovery);
(async()=>{try{token=(await(await fetch('/api/session')).json()).token;await refresh().catch(error);setInterval(()=>refresh(!state).catch(e=>{$('#connection').textContent='● Brak silnika';error(e);}),1000);}catch(e){error(e);}})();
