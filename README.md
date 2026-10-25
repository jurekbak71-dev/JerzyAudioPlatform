# Jerzy Audio Platform 0.3.0

Modułowy host JACK2 dla Raspberry Pi, pełne oryginalne DSP oraz polski panel WWW na porcie 8093. Dotychczasowe repozytoria i ich źródła pozostają bez zmian.

## Instalacja i aktualizacja

**[Pobierz instalator Windows 0.3.0](https://github.com/jurekbak71-dev/JerzyAudioPlatform/releases/download/v0.3.0-preview.1/JerzyAudioPlatform-v0.3.0-Windows-Installer.zip)** · [Wszystkie paczki](https://github.com/jurekbak71-dev/JerzyAudioPlatform/releases/tag/v0.3.0-preview.1)

1. Rozpakuj cały ZIP i kliknij `START-INSTALACJA.cmd`.
2. Podaj aktualne IP Pi i hasło. Po udanym stagingu wpisz `TAK`, aby aktywować aktualizację.
3. `WIFI-DOMOWE.cmd` przełącza Pi do domowego Wi-Fi z potwierdzeniem i próbą powrotu po pięciu minutach. Nie kasuje hotspotu.
4. `INSTALUJ-MODUL.cmd` instaluje wybrane pojedyncze paczki z katalogu SHA256. W panelu: **ŁAŃCUCH → tor → Dodaj moduł**.

[Instrukcja modułów i Wi-Fi](docs/MODULY_I_WIFI_PL.html). JACK i systemowe biblioteki muszą być wcześniej dostępne. Instalacja brakującego BlueZ wymaga Internetu na Pi. Aktywacja zachowuje punkt przywracania poprzedniej wersji i ustawienia użytkownika.

## Naprawy po testach Pi

[Instrukcja aktualizacji i zakres napraw 0.3.0](docs/NAPRAWY_0.3.0_PL.md). SYSTEM stosuje profil przez kontrolowany restart JACK, odtwarza sesję i routing, a przy błędzie przywraca ustawienia. Panel ma przyciski odzyskiwania audio, ochronę przeciążenia, czytelny CAB/IR i nowe sekcje studyjne. Głośność instrumentów jest na górze, MX pokazuje tylko parametry wybranego algorytmu.

## Bluetooth i uruchamianie PRO

Bass Ambient: **Start JAM** uruchamia generator. **BLUETOOTH / MIDI** obsługuje standard BLE MIDI, cztery przypisania CC/PC i połączenie z Hotspotem osobistym iPhone przez PAN. iPad bez Hotspotu korzysta z Wi-Fi. Testy chmurowe nie potwierdzają połączenia radiowego Hotone ani iPhone.

## Oryginalne moduły

- **big-muff-original** — oryginalny procesor, 6 modeli legacy, 14 obwodów, solver, oversampling JUCE i wygładzanie.
- **tape-drive-original** — pełny Tape Drive, 18 parametrów, filtry, mechanika taśmy, przedwzmacniacze i opto.
- **mx-delay-original** — dwa silniki, 9 algorytmów, głowice, routing i cztery sekcje wet FX.
- **small-clone-original** — 14 modeli i synchronizacja.
- **atomic-cluster-original** — oryginalna analiza FFT i resynteza do 64 atomów.
- **memory-delay-original** — pełny oryginalny silnik Memory Delay.
- **bass-ambient-pro-original** — PRO z modalnym DSP: Bass, Ambient, Arp, Drums, Krell, racki FX i mikser. Źródło `673e0def70d0`, oddzielny wątek zasobów FX. Composer, eksport i funkcje hosta VST pozostają poza portem.
- **bass-ambient-original** — wcześniejszy instrument bez PRO, zachowany dla poprzednich sesji; nie jest oferowany do nowych łańcuchów.

Każdy moduł jest osobnym `.jamod`; można go instalować, usuwać i aktualizować bez przebudowy hosta. Raport porównania jest związany z SHA256 konkretnego ELF i przypiętym commitem źródłowym. Nowy interfejs nie oferuje dodawania wcześniejszych demonstracyjnych zamienników jako oryginalnych efektów. Istniejące sesje można nadal odtworzyć.

Zgodność dotyczy wykonanych porównań float32 DSP przy identycznych parametrach i zegarze; nie oznacza identycznego GUI VST, importu jego presetów ani gwarancji wszystkich możliwych automatyzacji. Nie potwierdzono pełnej wydajności tych oryginalnych modułów na fizycznym Pi/HeadRush. Szczegóły: [raport 0.2](docs/ORYGINALNE_DSP_0.2.md).

## Budowanie i sprawdzanie

CMake >= 3.24, kompilator C++20, pkg-config, JACK2 development, Python >= 3.9. JUCE 7.0.12 jest pobierany jako przypięte archiwum z weryfikacją SHA256. Budowane są tylko moduły DSP, bez GUI JUCE/VST SDK. Można przekazać `-DJERZY_JUCE_ROOT=/sciezka/JUCE` do lokalnego przypiętego źródła.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
python3 tests/certify_originals.py --build build
JERZY_TEST_BUILD="$PWD/build" python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 tests/integration.py --build build
python3 tools/package.py --build build --out dist --arch arm64
```

Ostatnia komenda wymaga rzeczywistych binariów ARM64; na x86 użyj `--arch x86_64`. Test integracyjny uruchamia swój osobny JACK dummy i sprząta własne procesy. Opcja `--browser` używa Chromium/Playwright, a nie Safari. Tylko po ukończonych testach można wygenerować raporty i paczki original.

Big Muff/JUCE korzystają z GPLv3. Źródła platformy, pochodzenie DSP, licencje oraz źródła przypiętego JUCE są udostępniane z wydaniem. Pozostałe importowane DSP zachowują informacje o autorze i zatwierdzonym użyciu w PROVENANCE.json.
