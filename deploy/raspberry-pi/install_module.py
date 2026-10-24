#!/usr/bin/env python3
"""Install trusted standalone modules without restarting audio or requiring WAN."""
import argparse,json,socket,sys,urllib.request,zipfile
from pathlib import Path
BASE=Path.home()/'.local/share/jerzy-audio-platform'
def main():
 p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('sha256');a=p.parse_args()
 try:
  with urllib.request.urlopen('http://127.0.0.1:8093/api/state',timeout=5) as response:state=json.load(response)
  if not state.get('version','').startswith('0.2.'):raise RuntimeError('Najpierw zaktualizuj i aktywuj system 0.2.0. Dane i presety zostaną zachowane.')
  active=BASE/'active-release.json'
  if not active.exists():raise RuntimeError('Brak potwierdzonej aktywnej wersji systemu.')
  release=Path(json.loads(active.read_text())['path']).resolve()
  if not release.is_relative_to(BASE/'releases'):raise RuntimeError('Niepoprawna ścieżka aktywnego systemu.')
  sys.path.insert(0,str(release/'module-manager'));from manager import Library
  with zipfile.ZipFile(a.package) as archive:manifest=json.loads(archive.read('manifest.json'))
  if not manifest['id'].endswith('-original'):raise RuntimeError('Ten instalator przyjmuje wyłącznie zweryfikowane paczki oryginalnego DSP.')
  if any(n['module']==manifest['id'] for n in state['nodes']):raise RuntimeError('Najpierw usuń instancje tego modułu z łańcuchów; pozostałe audio może działać.')
  Library(BASE/'modules').install(a.package,a.sha256)
  print('Zainstalowano: '+manifest['name']+' '+manifest['version']+'. Panel → ŁAŃCUCH → Dodaj moduł.')
 except Exception as e:print('BŁĄD: '+str(e),file=sys.stderr);return 1
 return 0
if __name__=='__main__':raise SystemExit(main())
