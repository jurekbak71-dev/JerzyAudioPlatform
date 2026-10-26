# Jerzy Audio Platform 0.4.0 — host LV2 FX + Synth

To nasz panel i silnik JACK do uruchamiania wtyczek LV2. Poprzednie wbudowane DSP i paczki JAMOD zostały zastąpione przez LV2. Nie są dołączane do nowego instalatora. Twoje wtyczki są rozwijane i kompilowane w ich dotychczasowych repozytoriach VST, a gotowe katalogi .lv2 dodajesz do hosta.

## Instalacja na Pi

Rozpakuj cały Windows-Installer.zip do nowego folderu. Uruchom START-INSTALACJA.cmd, wpisz bassambient.local lub IP Pi i aktywuj przez TAK. Host wymaga 64-bitowego Linux ARM64, istniejącego JACK2 i bibliotek systemowych zgodnych z Debianem Bookworm. Biblioteki środowiska LV2 są dołączone do paczki; poprzednie DSP i JUCE nie są potrzebne.

Aktualizacja zachowuje możliwość przywrócenia poprzedniego wydania. Stara sesja z natywnymi modułami jest archiwizowana jako session-before-lv2-*.json. Pierwsza sesja LV2 zaczyna się z pustym łańcuchem; gitara może nadal przechodzić przez mikser. Nie zmieniamy automatycznie bufora JACK ani sieci.

## Dodawanie własnych wtyczek

1. W repozytorium wtyczki zbuduj LV2 dla **Linux ARM64**. Windows VST/VST3 nie działa na Pi.
2. Spakuj do ZIP jeden kompletny katalog `Nazwa.lv2`, zawierający manifest.ttl, metadane Turtle, bibliotekę .so i potrzebne zasoby. Zachowaj strukturę katalogów.
3. W panelu otwórz BIBLIOTEKA → Instalacja lub aktualizacja LV2, wybierz ZIP, podaj SHA256 otrzymane z repozytorium/wydania wtyczki i potwierdź zaufanie do autora.
4. W ŁAŃCUCH dodaj efekt na tor gitary lub w INSTRUMENTY dodaj syntezator. Parametry są odczytywane z metadanych LV2. SYNTH otrzymuje nuty z klawiatury w panelu lub wejścia MIDI JACK, w tym istniejącego mostka BLE MIDI.

Przed aktualizacją paczki usuń aktywne instancje z łańcucha. Host sprawdza architekturę i sumę paczki, odrzuca ścieżki wychodzące z ZIP i dowiązania symboliczne. Instalacja nie nadpisuje plików aktualnie załadowanej biblioteki. Wtyczki nie są sandboxowane; instaluj kod z zaufanych źródeł.

Host wykrywa także standardowe katalogi ~/.lv2, /usr/lib/lv2 i /usr/local/lib/lv2 oraz LV2_PATH. Paczki z panelu trafiają do ~/.local/share/jerzy-audio-platform/lv2. Ścieżkę własnego katalogu można zmienić przez JERZY_LV2_PATH; w chmurze ustaw ten sam katalog dla silnika i panelu.

## Obsługiwany zakres

- Efekty i generatory mono/stereo. Wejście mono otrzymuje średnią obu kanałów; wyjście mono jest kopiowane na lewy i prawy kanał.
- Porty wejściowe Control: zakresy, wartości początkowe, przełączniki/liczby całkowite i listy wartości Scale Points.
- MIDI Note/CC/Program Change/Pitch Bend przez Atom Sequence; znaczniki czasu nut w bloku, wybór kanału odbioru na instancję i klawiatura ekranowa.
- Informacje o tempie/pozycji przez Atom Time Position, URID map/unmap, opcje częstotliwości i maksymalnego bloku, LV2 Worker z ograniczonymi kolejkami.
- Sesje i presety parametrów oraz snapshoty rozszerzenia LV2 State do plików state.ttl. Zapis/odtworzenie stanu odbywa się przy wstrzymanej instancji, poza callbackiem audio. Pozostałe instancje mogą działać.
- Obecny mikser, bypass, ochrona CPU, ustawienia JACK, Bluetooth i mapowanie MIDI CC.

Host pokazuje parametry we własnym panelu WWW. Nie uruchamia okien GUI wtyczek. Obowiązkowe nieobsługiwane funkcje/typy portów są wykrywane przed uruchomieniem i opisane w bibliotece. Nie obsługujemy portów CV, starego rozszerzenia Event, wyjść ponad stereo, routingu wyjściowego MIDI wtyczki ani edytora komunikatów Patch do wyboru plików. Wtyczki wymagające własnego interfejsu do ładowania sampli lub specjalnych funkcji hosta mogą potrzebować dalszej obsługi. LV2 samo w sobie nie gwarantuje małego CPU.

## Budowanie i testy

Debian/Bookworm: g++, CMake >= 3.24, pkg-config, libjack-jackd2-dev, jackd2, liblilv-dev, lv2-dev, Python >= 3.11, Node.js i dbus-daemon do testów. Domyślna kompilacja buduje host LV2, bez wcześniejszych modułów i bez pobierania JUCE.

```
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
python3 tests/lv2_integration.py --build build
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tools/package_lv2.py --build build --out dist --arch arm64
```

Na x86_64 użyj --arch x86_64. Testowe wtyczki Gain/Synth/Worker są wyłącznie fixture'ami, nie są instalowane na Pi. Test integracyjny uruchamia własny JACK dummy i sprawdza faktyczne audio oraz MIDI przez panel HTTP. Testy chmurowe nie zastępują odsłuchu i testów sprzętu Pi/HeadRush.
