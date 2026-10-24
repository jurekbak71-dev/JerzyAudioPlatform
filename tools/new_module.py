#!/usr/bin/env python3
import argparse,json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('id');p.add_argument('directory',type=Path);a=p.parse_args()
 if not re.fullmatch('[a-z][a-z0-9-]{0,63}',a.id):p.error('Niepoprawne ID modułu')
 if a.directory.exists():p.error('Katalog już istnieje; nie nadpisuję plików')
 a.directory.mkdir(parents=True)
 shutil.copy2(ROOT/'module-sdk/jerzy_module.h',a.directory/'jerzy_module.h')
 source=(ROOT/'modules/utility-gain-meter/module.cpp').read_text().replace('utility-gain-meter',a.id)
 (a.directory/'module.cpp').write_text(source)
 (a.directory/'manifest.json').write_text(json.dumps(dict(id=a.id,name=a.id,version='0.1.0',abi=1,library=a.id+'.so',instrument=False),indent=2))
 (a.directory/'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.24)\nproject(JerzyModule LANGUAGES CXX)\nset(CMAKE_CXX_STANDARD 20)\nadd_library('+a.id+' MODULE module.cpp)\nset_target_properties('+a.id+' PROPERTIES PREFIX "")\n')
 (a.directory/'README.md').write_text('# '+a.id+'\n\nNiezależny moduł ABI 1. Budowanie: `cmake -S . -B build && cmake --build build`.\n\nPakowanie narzędziem platformy: `python3 tools/package_module.py manifest.json build/'+a.id+'.so '+a.id+'.jamod`.\n\nNie wymaga przebudowy hosta. Callback nie może alokować, blokować ani wykonywać I/O.\n')
if __name__=='__main__':main()
