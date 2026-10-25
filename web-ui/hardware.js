'use strict';
let btSelected='',pairText='',midiDrafts={};
function hardwareViewStamp(s){const h=s.hardware||{},b=h.bluetooth||{};return JSON.stringify([s.engine_available,h.available,h.operation,b.devices,b.pairing,b.operations,h.operations,h.midi_learning,h.midi_bindings,b.midi?.connected,b.pan]);}
function transportControls(parent,n){
 const value=key=>n.parameters.find(p=>p.id===key)?.value||0;
 const playing=value('autoPlay')>0,mode=value('performanceSource');
 const card=el('article',undefined,'rack transport');card.append(el('h3','TRANSPORT'),el('p',n.bypass?'Instrument jest pominięty — użyj Start JAM albo Włącz moduł.':mode===1?'Źródło MIDI — instrument czeka na nuty kontrolera.':playing?'JAM gra.':'Generator STOP — samo włączenie warstwy nie uruchamia nut.'));
 card.append(row(button('▶ Start JAM',()=>action('instrument-transport',{id:n.id,command:'start'}),'primary'),button('■ Stop JAM',()=>action('instrument-transport',{id:n.id,command:'stop'}))));parent.append(card);
}
function downloadDiagnostics(){const value=structuredClone(state);if(value.hardware?.bluetooth)delete value.hardware.bluetooth.pairing;const file=new Blob([JSON.stringify(value,null,2)],{type:'application/json'}),a=el('a');a.href=URL.createObjectURL(file);a.download='Jerzy-diagnostyka-'+new Date().toISOString().replaceAll(':','-')+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
function renderSystem(){
 const s=panel('System i audio'),h=state.hardware||{},a=h.audio||{},op=h.operation||{};
 s.append(el('p',(state.engine_available===false?'Silnik niedostępny. ':'Silnik aktywny. ')+state.sample_rate+' Hz · '+state.buffer+' próbek · RT '+(state.rt_priority||0)));
 if(state.engine_error&&!op.pending)s.append(el('p',state.engine_error,'fault'));
 if(op.pending)s.append(el('p','Trwa '+op.name+' — audio może być chwilowo przerwane. Nie uruchamiaj kolejnej operacji.','notice'));
 if(op.error)s.append(el('p','Wynik ostatniej operacji: '+op.error,'fault'));
 const box=el('article',undefined,'rack');box.append(el('h3','Profil urządzenia JACK / HeadRush'));
 let rate=a.rate||state.sample_rate,buffer=state.buffer,periods=a.periods||3;
 const controls=el('div',undefined,'grid controls');controls.append(choiceControl('Częstotliwość',[[44100,'44,1 kHz'],[48000,'48 kHz']],rate,v=>{rate=Number(v);}),choiceControl('Bufor',[64,128,256,512,1024].map(v=>[v,v+' próbek']),buffer,v=>{buffer=Number(v);}),choiceControl('Liczba okresów',[[2,'2'],[3,'3']],periods,v=>{periods=Number(v);}));
 const apply=button('Zastosuj i uruchom audio',()=>action('audio-config',{rate,buffer,periods}),'primary');apply.disabled=!h.available||op.pending;
 box.append(controls,apply,el('p','Profil jest stosowany przez restart istniejącego JACK z zachowaniem urządzenia i kanałów. Połączenia i sesja są odtwarzane; błąd uruchamia przywracanie poprzednich ustawień.'));
 if(!h.available)box.append(el('p',h.error||'Brak działającej usługi sprzętowej — aktywuj kompletną paczkę 0.3.0.','fault'));
 if(a.running===false)box.append(el('p','JACK: '+(a.error||'nie działa'),'fault'));
 s.append(box);
 const repair=button('Uruchom / napraw JACK i audio',()=>action('repair-jack',{}));repair.disabled=!h.available||op.pending;
 s.append(row(repair,button('Pobierz raport diagnostyczny',downloadDiagnostics)),button(state.thru_jack_disabled?'Przywróć THRU JACK':'Wyłącz THRU JACK',()=>action('thru',{value:state.thru_jack_disabled?1:0})),el('p','THRU JACK nie zmienia wewnętrznego monitoringu HeadRush.'));
 const diag=el('pre');diag.id='diagnostics';s.append(diag,el('p','Wersja '+state.version+' · '+state.platform));
}
function numInput(label,value,min,max,fn){const l=el('label',label),input=el('input');input.type='number';input.min=min;input.max=max;input.step=1;input.value=value;input.oninput=()=>fn(Number(input.value));l.append(input);return l;}
function bluetooth(){
 const s=panel('Bluetooth i MIDI'),h=state.hardware||{},b=h.bluetooth||{};
 s.append(el('p','Panel iPhone: połączenie PAN z Hotspotem osobistym iPhone’a. Samo sparowanie nie tworzy sieci dla Safari. iPad bez funkcji Hotspot osobisty korzysta z Wi-Fi; BLE MIDI jest osobną funkcją.'));
 if(!h.available)s.append(el('p',h.error||'Usługa sprzętowa nie jest dostępna. Zainstaluj i aktywuj pełną wersję 0.3.0.','fault'));
 const scan=button(b.scanning?'Wyszukiwanie…':'Wyszukaj urządzenia',()=>action('bluetooth',{operation:'scan'}));scan.disabled=!h.available||b.scanning;s.append(scan);
 if(b.error)s.append(el('p','Bluetooth: '+b.error,'fault'));
 const devices=b.devices||[];if(!devices.some(d=>d.address===btSelected))btSelected=devices[0]?.address||'';
 s.append(choiceControl('Urządzenie Bluetooth',[['','Wybierz urządzenie'],...devices.map(d=>[d.address,d.name+' · '+d.address+(d.connected?' · połączone':d.paired?' · sparowane':'')])],btSelected,v=>{btSelected=v;render();}));
 const device=devices.find(d=>d.address===btSelected),buttons=row();
 for(const [label,operation] of [['Sparuj','pair'],['Połącz BLE MIDI','midi-connect'],['Połącz Hotspot iPhone przez BT','pan-connect']]){
  const buttonEl=button(label,()=>action('bluetooth',{operation,address:btSelected}));buttonEl.disabled=!h.available||!btSelected||(operation==='pair'&&device?.paired);buttons.append(buttonEl);
 }s.append(buttons,el('p','Hotone Ampero Control: ustaw wysyłanie komunikatów przez Bluetooth MIDI i zamknij aplikację Hotone na telefonie przed połączeniem Pi. BLE MIDI może nie wymagać parowania systemowego.'));
 if(b.pairing){const prompt=b.pairing,box=el('article',undefined,'rack');box.append(el('h3','Parowanie Bluetooth'));
  if(prompt.kind==='confirm'){box.append(el('p','Porównaj kod z urządzeniem: '+String(prompt.code).padStart(6,'0')),row(button('Kod jest zgodny',()=>action('bluetooth',{operation:'confirm',id:prompt.id,value:true})),button('Odrzuć',()=>action('bluetooth',{operation:'confirm',id:prompt.id,value:false}))));}
  else if(['pin','passkey'].includes(prompt.kind)){const input=el('input');input.type='text';input.value=pairText;input.oninput=()=>{pairText=input.value;};box.append(el('p','Wpisz kod wymagany przez urządzenie.'),input,button('Prześlij kod',()=>action('bluetooth',{operation:'confirm',id:prompt.id,value:prompt.kind==='passkey'?Number(pairText):pairText})));}
  else box.append(el('p','Wpisz na urządzeniu kod: '+prompt.code));s.append(box);
 }
 for(const [name,operation] of Object.entries(h.operations||{}))if(operation.pending||operation.error)s.append(el('p',name+': '+(operation.pending?'w toku':operation.error),operation.error?'fault':''));
 const pan=el('article',undefined,'rack');pan.append(el('h3','Panel przez Bluetooth PAN'));
 if(b.pan?.connected){pan.append(el('p','Na iPhone otwórz w Safari: '+b.pan.url),el('p','Bieżące Wi-Fi Pi pozostaje połączone.'),button('Rozłącz PAN',()=>action('bluetooth',{operation:'pan-disconnect'})));}
 else pan.append(el('p','Na iPhone włącz Hotspot osobisty i Bluetooth, otwórz Ustawienia → Bluetooth, sparuj z Pi, a następnie użyj Połącz Hotspot iPhone przez BT. Wymaga obsługi udostępniania internetu w telefonie.'));
 s.append(pan);
 const midi=el('article',undefined,'rack');midi.append(el('h3','BLE MIDI — Hotone Ampero Control'),el('p',b.midi?.connected?'Połączono BLE: '+b.midi.name:'BLE MIDI nie jest połączone.'),el('p',h.jack_midi?.connected?'Port MIDI jest połączony z silnikiem.':'Port MIDI nie jest jeszcze połączony z silnikiem.'));
 const last=el('p');last.id='midi-last';midi.append(last);if(b.midi?.delivery_error)midi.append(el('p',b.midi.delivery_error,'fault'));if(h.relay?.error)midi.append(el('p',h.relay.error,'fault'));
 if(b.midi?.connected)midi.append(button('Rozłącz BLE MIDI',()=>action('bluetooth',{operation:'midi-disconnect'})));
 midi.append(el('p','Najpierw Ucz i naciśnij przycisk kontrolera, potem wybierz akcję i Zapisz. PC/CC pokazujemy 0–127; numer w aplikacji kontrolera może być opisany 1–128. Bypass reaguje w wątku MIDI, bez żądań HTTP.'));
 if(h.midi_learning)midi.append(el('p','Oczekiwanie na przycisk '+h.midi_learning.slot+'…','notice'));
 const targets=[];const ordinals={};for(const n of state.nodes){const key=n.module+':'+n.route;const ordinal=ordinals[key]||0;ordinals[key]=ordinal+1;targets.push([JSON.stringify({module:n.module,route:n.route,ordinal}),n.name+' #'+n.id]);}
 const cards=el('div',undefined,'grid');for(const saved of h.midi_bindings||[]){let draft=midiDrafts[saved.slot];const sig=JSON.stringify([saved.bound,saved.type,saved.channel,saved.number]);if(!draft)draft=midiDrafts[saved.slot]={...structuredClone(saved),_sig:sig};else if(draft._sig!==sig)Object.assign(draft,{bound:saved.bound,type:saved.type,channel:saved.channel,number:saved.number,_sig:sig});const c=el('article',undefined,'rack');c.append(el('h3','PRZYCISK '+saved.slot),button('Ucz przycisk '+saved.slot,()=>action('midi-learn',{slot:saved.slot})),el('p',draft.bound?'Źródło przypisane':'Źródło nieprzypisane'));
  c.append(choiceControl('Typ', [['cc','CC'],['pc','PC']],draft.type,v=>{draft.type=v;}),numInput('Kanał',draft.channel,1,16,v=>{draft.channel=v;}),numInput('Numer CC / PC',draft.number,0,127,v=>{draft.number=v;}),choiceControl('Akcja',[['none','Brak akcji'],['bypass','Bypass modułu'],['preset','Wczytaj preset sesji']],draft.action,v=>{draft.action=v;render();}));
  if(draft.action==='bypass'){if(!draft.target&&targets.length)draft.target=JSON.parse(targets[0][0]);c.append(choiceControl('Moduł',targets,draft.target?JSON.stringify(draft.target):'',v=>{draft.target=JSON.parse(v);}),choiceControl('Tryb CC',[['toggle','Przełącz przy naciśnięciu'],['value','127 = efekt włączony, 0 = bypass']],draft.mode,v=>{draft.mode=v;}));}
  if(draft.action==='preset'){if(!draft.preset)draft.preset=state.presets[0]||'';c.append(choiceControl('Preset',state.presets.map(n=>[n,n]),draft.preset,v=>{draft.preset=v;}));}
  c.append(button('Zapisz przycisk '+saved.slot,()=>action('midi-binding',{...draft,bound:true}),'primary'));cards.append(c);
 }midi.append(cards);s.append(midi);
}
