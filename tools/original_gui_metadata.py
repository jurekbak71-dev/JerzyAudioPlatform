from pathlib import Path
import json,re
R=Path(__file__).resolve().parents[1]
def save(id,choices):
 p=R/'modules'/id/'manifest.json';m=json.loads(p.read_text());m['gui_normalized_choices']=choices;p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n')
on=['Wył.','Wł.']
save('tape-drive-original',{'gainMode':['Normalny','Duże wzmocnienie'],'shift':['Niski','Środkowy','Wysoki'],'bypass':on,'preampMode':['Czysty','Lampowy','Tranzystorowy'],'optoBypass':on})
s=(R/'modules/small-clone-original/vendor/Dsp.h').read_text();table=s.split('circuits{{',1)[1].split('}};',1)[0];names=re.findall(r'\{"([^"]+)"',table);assert len(names)==14
beats=re.findall(r'\{"([^"]+)"',s.split('divisions{{',1)[1].split('}};',1)[0]);assert len(beats)==18
save('small-clone-original',{'model':names,'division':beats,'filter':on,'bypass':on,'sync':on})
save('atomic-cluster-original',{'smooth':on,'flat':on,'bypass':on,'sync':on,'tapEnabled':on,'division':['1/16','1/8','1/4','1/2','Takt'],'motion':['Klaster','Arpeggio','Losowe harmoniczne']})
s=(R/'modules/memory-delay-original/vendor/parameters.h').read_text();models=re.findall(r'"([^"]+)"',s.split('modelNames{{',1)[1].split('}};',1)[0]);beats=re.findall(r'\{"([^"]+)"',s.split('divisions{{',1)[1].split('}};',1)[0]);assert len(models)==6
save('memory-delay-original',{'model':models,'division':beats,'bypass':on,'boost':on,'modEnable':on,'tempoSync':on})
c={'routing':['Szeregowo','Równolegle','Podział L/R'],'bypass':on,'spill':on,'machineCondition':['Po serwisie','Używany','Zużyty','Uszkodzony']}
for i in range(4):c[f'fx{i}_type']=['Wył.','Chorus','Flanger','Lo-Fi','Overdrive','Granular'];c[f'fx{i}_route']=['Wejście / przed','Tylko efekt']
for i in range(2):
 c[f'slot{i}_algorithm']=['MultiHead Reel','Tape Echo','Oil Can','Tube Echo','BBD','Doubletrack','Dual Digital','Space Echo 202','BBD Machine 101'];c[f'slot{i}_enable']=on;c[f'slot{i}_sync']=on;c[f'slot{i}_division']=['1/1','1/2.','1/2','1/4.','1/4','1/8.','1/8','1/4T','1/16','1/8T']
 for k in range(6,14):c[f'slot{i}_algo0_{k}']=on
 for k in range(8,12):c[f'slot{i}_algo7_{k}']=on
 c[f'slot{i}_algo1_7']=['Fixed','Multi','Single'];c[f'slot{i}_algo4_0']=['3205','3005','Multi'];c[f'slot{i}_algo5_3']=['Sum','Invert','Bounce'];c[f'slot{i}_algo6_0']=['24/96','ADM','12 bit'];c[f'slot{i}_algo8_0']=['Classic','Vintage','Modern','Multi-head','Non-linear','Ambience','Reflect','Doubling+delay','Wide','Dual mod','Pan','Pattern']
save('mx-delay-original',c)
