# Jerzy Audio Platform 0.1.0 — wersja rozwojowa

## Pobierz i zainstaluj na Windows

**[Pobierz ZIP instalatora — wydanie testowe preview.2](https://github.com/jurekbak71-dev/JerzyAudioPlatform/releases/download/v0.1.0-preview.2/JerzyAudioPlatform-v0.1.0-Windows-Installer.zip)**

1. Rozpakuj cały ZIP.
2. Kliknij dwukrotnie `START-INSTALACJA.cmd`.
3. Podaj IP Raspberry Pi, jeśli nie zostanie odnalezione automatycznie, i hasło użytkownika `jerzy`.

Instalator najpierw sprawdzi pliki i zależności; aktywację potwierdzasz wpisaniem `TAK`. Po sukcesie otworzy panel. Powrót do poprzedniego systemu: `PRZYWROC-MULTIFX.cmd`.

Wydanie zbudowało GitHub Actions po testach x86_64, ARM64 oraz parsera PowerShell na Windows. Nie wykonano instalacji na fizycznym Windows/Pi/HeadRush ani testów Safari. Używaj osobnej kopii karty, zachowując działającą CARD-00.


Oddzielny host JACK2, moduły ELF `.so` z ABI C, lokalny menedżer paczek i polski panel WWW na porcie 8093. Projekt powstaje obok MultiFX; nie zmienia jego źródeł ani konfiguracji sieci.

**To nie jest jeszcze kompletne wydanie spełniające całą specyfikację.** Patrz [ograniczenia](docs/OGRANICZENIA.md), [audyt](docs/AUDYT.md) i [testy sprzętowe](docs/TESTY_SPRZETOWE.md). Dostarczone paczki są przeznaczone do stagingu i kontrolowanych prób, nie do zastąpienia sprawnej karty CARD-00 bez pomiarów.

Działające elementy: dwa niezależne tory, ładowanie/usuwanie/przestawianie modułów bez przebudowy hosta, wygładzony bypass i parametry, mikser z mute/solo/pan, peak/RMS/clip, limiter ochronny, wejście MIDI i CC Learn, presety całej sesji, niezależny BassAmbient z oryginalnym rdzeniem DSP, fuzz, saturacja taśmowa, gain oraz splot CAB/IR. GUI działa bez frameworków; serwer używa biblioteki standardowej Pythona.

## Budowanie na Debianie Bookworm ARM64 / x86_64

Wymagane: CMake >= 3.24, kompilator C++20, pkg-config, nagłówki JACK2, Python >= 3.9. Nie potrzeba JUCE ani VST SDK.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
python3 tests/integration.py --build build
python3 -m unittest discover -s tests -p 'test_*.py'
```

Test integracyjny uruchamia własny nazwany JACK dummy i własne procesy. Nie używaj go jako testu fizycznego interfejsu. Opcja `--browser` wymaga Playwright i Chromium. Wyniki chmurowe nie opisują wydajności Pi.

```sh
# Uruchom istniejący JACK odpowiednią dla maszyny metodą. Nie uruchamiaj kolejnego JACK nad działającym serwerem.
./build/jerzy-audio-core /tmp/jerzy-audio-platform.sock
python3 web-ui/server.py --modules "$PWD/build/modules" --data "$HOME/.local/share/jerzy-audio-platform" --port 8093
```

Host nie łączy automatycznie portów fizycznych w trybie deweloperskim. Użyj routera JACK lub kontrolowanej aktywacji opisanej w instrukcji. Nie opieraj testu gotowości wyłącznie na otwartym porcie HTTP.

## Paczki

```sh
python3 tools/package.py --build build --out dist --arch arm64
```

Nazwa ARM64 jest akceptowana wyłącznie dla rzeczywistego ELF AArch64. Paczka zawiera skompilowany host i pięć bibliotek, testy DSP, GUI, skrypty staging/activation/rollback, instrukcję i sumy SHA256. `.jamod` to ZIP z manifestem, biblioteką i wewnętrznymi SHA256; przy imporcie wymagane są również zaufana zewnętrzna suma paczki oraz potwierdzenie autora. Suma kontrolna wykrywa uszkodzenie, ale sama nie dowodzi autorstwa.

## SDK i osobne repozytoria modułów

```sh
python3 tools/new_module.py moj-modul /tmp/MojModul
cmake -S /tmp/MojModul -B /tmp/MojModul-build
cmake --build /tmp/MojModul-build
python3 tools/package_module.py /tmp/MojModul/manifest.json /tmp/MojModul-build/moj-modul.so /tmp/moj-modul.jamod
```

[Opis ABI i real-time](module-sdk/README.md). [Instrukcja instalacji](docs/INSTRUKCJA_PL.html).
