# CODEX — JERZY AUDIO PLATFORM
## Kompletny system modułowy dla Raspberry Pi 4B — implementacja, testy, instalator i gotowa paczka

### TRYB PRACY

Jesteś głównym architektem i programistą C++/DSP/Linux audio, odpowiedzialnym za dostarczenie **działającego produktu**, a nie prototypu, opisu koncepcji czy samych fragmentów kodu.

**Nie kończ zadania na planie. Zaimplementuj system, uruchom automatyczne testy, zbuduj pakiety instalacyjne, skonfiguruj GitHub Actions i udostępnij rzeczywiste pliki do pobrania.**

Nie pytaj mnie o decyzje techniczne, które możesz rozstrzygnąć samodzielnie. Wybieraj rozwiązania stabilne, lekkie, przemyślane i odpowiednie dla Raspberry Pi 4B.

Nie deklaruj sukcesu, jeżeli test lub kompilacja się nie powiodły. Nie przedstawiaj nieprzetestowanego rozwiązania jako sprawdzonego na fizycznym sprzęcie.

Wymagany język interfejsu, instalatora, komunikatów i instrukcji: **polski**.

---

# 1. CEL PROJEKTU

Zbuduj od podstaw:

**JERZY AUDIO PLATFORM v0.1.0**

Lekki system do uruchamiania niezależnych efektów audio, syntezatorów, instrumentów generatywnych i procesorów sygnału na Raspberry Pi.

Nie chcę kolejnego monolitycznego MultiFX.

Chcę odpowiednik **systemu operacyjnego dla naszych modułów muzycznych**: stabilny, oszczędny, z jednym silnikiem audio, jednym intuicyjnym GUI i możliwością instalowania nowych instrumentów oraz efektów bez przebudowy całego programu.

Architektura docelowa:

```text
RASPBERRY PI OS LITE ARM64
          |
     JACK2 AUDIO
          |
  JERZY AUDIO CORE
          |
   MODULAR AUDIO GRAPH
          |
    +-----+------+----------+
    |            |          |
  GUITAR FX   SYNTHS    UTILITIES
    |            |          |
  CAB / IR   BASSAMBIENT  EQ/METERS
    |            |          |
    +------------+----------+
                 |
           AUDIO MIXER
                 |
          HEADRUSH CORE

WEB GUI + MODULE MANAGER + PRESETS
                |
          iPHONE / WINDOWS
```

Każdy instrument i efekt musi mieć możliwość niezależnej instalacji, aktualizacji, usunięcia i zastąpienia nowszą wersją.

---

# 2. SPRZĘT I ŚRODOWISKO

Docelowa konfiguracja użytkownika:

- Raspberry Pi 4B.
- Raspberry Pi OS Lite ARM64.
- Użytkownik Linuksa: `jerzy`.
- Hostname: `bassambient`.
- HeadRush Core jako interfejs USB Audio.
- JACK2.
- Aktualne parametry JACK: 44 100 Hz, bufor 64 próbki, 3 okresy.
- Windows jako komputer do instalacji i zarządzania.
- iPhone 14 jako urządzenie do sterowania GUI przez Safari.
- Raspberry Pi jest podłączane do domowej sieci LAN/Wi-Fi.
- Wcześniej używany hotspot: `Jerzy-MultiFX`, adres `10.42.0.1`.
- Dostęp SSH: `jerzy@bassambient.local` lub `jerzy@ADRES_IP`.

**Nie zakładaj z góry, że adres `.local` działa. Instalator ma wykrywać Raspberry Pi i pozwalać ręcznie wpisać IP.**

**Nie zakładaj, że Raspberry Pi ma internet.** Instalacja musi być możliwa przez lokalne połączenie SSH z Windows, na podstawie wcześniej pobranej paczki.

Przed instalacją wykryj rzeczywiste parametry urządzenia, wersję systemu, architekturę, dostępne biblioteki i konfigurację JACK.

Nie zmieniaj istniejącego Wi-Fi, NetworkManager ani hotspotu.

---

# 3. ISTNIEJĄCE PROJEKTY — OBOWIĄZKOWY AUDYT

Przeanalizuj istniejące repozytoria:

**Projekt nadrzędny:**
https://github.com/jurekbak71-dev/JerzyRPiAudioLab

**Dotychczasowy MultiFX i moduły DSP:**
https://github.com/jurekbak71-dev/JerzyMemoryDelay

**Gałąź eksperymentalnego MultiFX v0.4:**
https://github.com/jurekbak71-dev/JerzyMemoryDelay/tree/feature/jerzy-multifx-v04-dual-ir-midi

**Oryginalny instrument BassAmbient VST3:**
https://github.com/jurekbak71-dev/JerzyBassAmbientVST3

W istniejącym MultiFX występują między innymi:

- Modularne efekty `.so`.
- Własny interfejs modułów opisany w `multifx2/api.h`, obecnie `JFX_ABI_VERSION 2`.
- Host JACK w `multifx4/host.cpp`.
- Instrument BassAmbient zaadaptowany w `multifx4/bass_ambient.h`.
- Kopia kodu DSP instrumentu w `multifx4/vendor/BassAmbientCore.h`.
- Obsługa CAB/IR.
- Web GUI.
- MIDI Learn.
- Presety.
- Skrypty systemd i instalacyjne.

**Traktuj te projekty jako źródła wiedzy i kodu referencyjnego, nie jako fundament, który należy bezrefleksyjnie kopiować.**

Przed ponownym użyciem każdego fragmentu sprawdź:

1. Czy działa prawidłowo.
2. Czy jest zgodny z nową architekturą.
3. Czy nie powoduje trzasków, przesterowań i przeciążenia CPU.
4. Czy nie alokuje pamięci ani nie blokuje wątku audio.
5. Czy ma odpowiednią licencję.
6. Czy nie wprowadza zależności od starego monolitycznego hosta.

**Nie modyfikuj istniejących repozytoriów ani działającego MultiFX v0.2.**

Nowe repozytorium docelowe:

`jurekbak71-dev/JerzyAudioPlatform`

Utwórz je, jeśli masz odpowiednie uprawnienia. Jeżeli nie możesz utworzyć repozytorium z bieżącego środowiska, przygotuj pełną zawartość nowego repozytorium w katalogu roboczym i wskaż jedną konkretną czynność wymaganą do opublikowania.

---

# 4. ARCHITEKTURA MODUŁOWA

Zbuduj następujące niezależne elementy:

### A. Jerzy Audio Core

Niewielki host odpowiedzialny tylko za:

- JACK2.
- Wykrywanie urządzenia audio.
- Zarządzanie grafem sygnałowym.
- Ładowanie i usuwanie modułów.
- Routing audio i MIDI.
- Zarządzanie zegarem/BPM.
- Miksowanie.
- Presety.
- Monitorowanie CPU, pamięci i XRUN.
- Kontrolę poziomów audio.
- Obsługę komunikacji z GUI.

Host nie może zawierać na stałe algorytmów Big Muffa, Tape Drive ani BassAmbient.

### B. Jerzy Module SDK

Opracuj stabilne, wersjonowane API modułów.

Preferowany natywny format: lekki moduł ARM64 `.so` z jednoznacznym ABI C i manifestem JSON.

Dostarcz dokumentację i przykłady kompilacji.

Moduły muszą obsługiwać:

- Audio wejściowe i wyjściowe, mono/stereo.
- Instrument bez wejścia audio.
- MIDI notes/CC.
- Automatyzację parametrów.
- BPM/transport.
- Presety i stan modułu.
- Latencję i jej raportowanie.
- Bypass bez trzasków.
- Inicjalizację i zwolnienie pamięci.
- Wersję API.
- Metadane GUI.
- Zakresy parametrów i jednostki muzyczne.

Wprowadź kompatybilność ze starymi modułami JFX v2 poprzez osobny adapter, jeśli można ją zapewnić bezpiecznie.

### C. LV2

Zbadaj i zaimplementuj **opcjonalny host/adapter LV2**, jeżeli nie wymaga to nadmiernego obciążenia procesora i pamięci.

Nie buduj całego systemu na ciężkim frameworku tylko dlatego, że obsługuje LV2.

LV2 ma rozszerzać możliwości platformy, a nie być źródłem zależności i niestabilności.

Nie próbuj bezpośrednio ładować windowsowych plików VST3 na ARM64. Wykorzystuj przenośny kod DSP, jeśli jest dostępny i zgodny licencyjnie.

---

# 5. BEZWZGLĘDNE WYMAGANIA REAL-TIME AUDIO

To najważniejszy warunek techniczny.

W callbacku JACK:

- Zero `malloc`, `new`, `delete`.
- Zero mutexów, blokujących operacji i oczekiwania.
- Zero dostępu do dysku.
- Zero operacji sieciowych.
- Zero logowania do plików.
- Zero budowania struktur wymagających alokacji.
- Zero niekontrolowanych wyjątków.
- Zero przebudowy grafu na wątku audio.
- Bezpieczne przekazywanie parametrów między GUI i silnikiem.
- Deterministyczne czasy przetwarzania.
- Obsługa denormali.
- Ochrona przed NaN/Inf.
- Bezpieczne przełączanie, usuwanie i zastępowanie instancji efektów.

Stosuj bufory przygotowane wcześniej, odpowiednie techniki atomowe i bezpieczne mechanizmy wymiany grafu.

Nie twórz rozwiązań, które działają przez kilka sekund, a następnie zaczynają trzeszczeć lub zawieszają dźwięk.

Wprowadź testy stabilności wielogodzinnej możliwe do automatycznego uruchomienia oraz testy dużego obciążenia grafu.

---

# 6. BUFOR JACK — REGULACJA Z GUI

Obecnie bufor 64 próbek może być za mały dla bardziej wymagających procesorów audio.

W GUI dodaj:

**SYSTEM → AUDIO**

- Bufor: 64 / 128 / 256 / 512 / 1024 próbek.
- Częstotliwość próbkowania.
- Liczba okresów.
- Obliczone opóźnienie bufora.
- Raportowaną latencję modułów.
- CPU audio.
- RAM.
- Licznik XRUN.
- Stan JACK.
- Wykryty interfejs audio.
- Diagnostykę wejść i wyjść.

Zmiana parametrów bufora wymaga bezpiecznego zatrzymania i ponownego uruchomienia odpowiednich usług.

Przed zmianą:

1. Zachowaj działającą konfigurację.
2. Sprawdź poprawność wybranych wartości.
3. Zatrzymaj silnik w kontrolowany sposób.
4. Zastosuj konfigurację.
5. Uruchom JACK i silnik.
6. Zweryfikuj gotowość oraz porty audio.
7. Przy niepowodzeniu automatycznie przywróć poprzednie ustawienia.

**Nie resetuj ustawień sieciowych i nie usuwaj konfiguracji HeadRush.**

Zaimplementuj prosty wybór profili:

- Niska latencja.
- Zrównoważony.
- Duża stabilność.

Nie obiecuj zerowych XRUN bez pomiarów na rzeczywistym Pi.

---

# 7. TOR AUDIO I MIKSER

Domyślnie dwa niezależne tory:

**GUITAR**
`HeadRush Input → Effects → CAB/IR → Mixer`

**INSTRUMENTS**
`BassAmbient / inne instrumenty → Effects → Mixer`

Do tego możliwość tworzenia kolejnych torów w przyszłości.

Wymagania:

- Osobne poziomy wejścia, wyjścia i miksowania.
- Wskaźniki peak i RMS.
- Wskaźnik clip.
- Headroom.
- Kontrolowane wyrównywanie głośności przy włączaniu efektu.
- Niezależne MUTE i SOLO.
- Panoramowanie.
- Wygładzanie zmian parametrów.
- Unikanie klików przy bypassie i zmianach presetów.
- Kontrola sprzężeń.
- Bezpieczny limiter ochronny na wyjściu z możliwością świadomej konfiguracji.
- Brak podwójnego podbijania sygnału i przypadkowej kompresji.

Nie ukrywaj wad DSP za agresywnym limiterem.

Zaimplementuj testy poziomów sygnału przy różnych konfiguracjach łańcucha.

---

# 8. BASSAMBIENT — PRIORYTET INSTRUMENTALNY

Dotychczasowa wersja na Raspberry Pi:

- Trzeszczy.
- Często nie generuje poprawnej muzyki.
- Brzmieniowo znacznie odbiega od oryginalnego VST3.
- Ma zbyt ograniczone sterowanie.
- Może przeciążać CPU.

**Nie akceptuję uproszczonego generatora udającego BassAmbient.**

Przeanalizuj dokładnie oryginalny instrument VST3 i odtwórz jego prawdziwą logikę:

- Oscylatory.
- Filtry i obwiednie.
- Sekwencje.
- Modele basu.
- Style muzyczne.
- Skale i tonacje.
- Akordy.
- Silniki ambient/pad.
- Generatywność.
- Krell.
- Ewolucję brzmień.
- Modulacje.
- FX.
- Transport i tempo.
- Długości nut, groove, dynamikę i artykulację.

Przenieś go do osobnego modułu instrumentu.

Bass i Ambient muszą mieć niezależny START/STOP.

Wymagam:

- Własnego tempa lub synchronizacji z hostem.
- Niezależnych poziomów.
- Sterowania wysokością dźwięku nazwami nut.
- Wybierania stylu i skali.
- Muzykalnego generowania fraz.
- Zachowania wszystkich istotnych funkcji oryginalnego VST.
- Braku trzasków podczas pracy.
- Niewykorzystywania CPU, kiedy instrument jest nieaktywny.

**Przeprowadź testy porównawcze DSP oryginału i portu** przy identycznych parametrach, nutach, częstotliwości próbkowania i seedzie, z uwzględnieniem dopuszczalnych różnic numerycznych.

Najpierw zapewnij poprawne działanie brzmienia, potem dopiero optymalizuj.

Nie usuwaj funkcji instrumentu w imię oszczędności procesora.

---

# 9. EFEKTY — JAKOŚĆ, NIE ATRAPY

W obecnym systemie Big Muff Pi, Tape Drive i inne efekty brzmią bardzo słabo. Część nie spełnia podstawowej funkcji, np. nie generuje prawdziwego fuzzu.

Nowa platforma nie może kopiować tych błędów.

Na początek dostarcz osobne moduły demonstracyjne o rzeczywistym, słyszalnym działaniu:

1. **Jerzy BassAmbient** — instrument.
2. **Jerzy Big Muff Pi** — właściwy efekt fuzz.
3. **Jerzy Tape Drive** — właściwe nasycenie i charakter taśmy.
4. **Jerzy Utility Gain/Meter** — narzędzie do weryfikacji sygnału.
5. **Jerzy CAB/IR** — niezależny procesor impulsów.

Każdy jako instalowany niezależnie pakiet.

W szczególności:

### Big Muff Pi

Zweryfikuj architekturę klasycznego efektu typu Big Muff: kaskadowe stopnie wzmocnienia i clippingu, filtrację, charakterystyczny układ tone oraz odpowiednie poziomy sygnału.

Sam `tanh()` z trzema potencjometrami nie jest wystarczającą emulacją.

Parametry Gain/Sustain, Tone i Level muszą rzeczywiście zmieniać odpowiednie aspekty brzmienia.

### Tape Drive

Zaimplementuj słyszalną, kontrolowaną saturację o charakterze taśmowym, odpowiedź częstotliwościową i nieliniowość zależną od poziomu sygnału.

Unikaj przypadkowego clippingu cyfrowego i nadmiernego wzrostu głośności.

### Testy efektów

Każdy moduł musi przejść testy:

- Działanie wszystkich parametrów.
- Poprawny bypass.
- Stabilność poziomu sygnału.
- Brak NaN/Inf.
- Test sinusoidalny i wielotonowy.
- Reakcja na dynamikę wejścia.
- Pomiar THD/charakterystyki częstotliwościowej tam, gdzie ma zastosowanie.
- Zachowanie przy 44,1 i 48 kHz.
- Test różnych rozmiarów bufora.
- Brak klików przy zmianie parametrów.

Nie twierdź, że uzyskano pełną zgodność brzmieniową z konkretnym urządzeniem lub VST, jeśli nie przeprowadzono odpowiednich porównań odsłuchowych i pomiarowych.

---

# 10. NOWE GUI — ZAPROJEKTUJ OD POCZĄTKU

Dotychczasowe GUI to chaos. Nie chcę jego kosmetycznej poprawki.

Zaprojektuj nowy, ergonomiczny interfejs dla iPhone 14, tabletów i komputerów.

Ma wyglądać i działać jak profesjonalny procesor muzyczny, a nie panel diagnostyczny programisty.

Wymagane ekrany:

**ŁAŃCUCH**
- Graficzny przepływ sygnału.
- Dodawanie i usuwanie efektów.
- Zmiana kolejności.
- Bypass.
- Wybór toru.
- Jednoznacznie widoczny aktywny moduł.

**EFEKT**
- Parametry wybranego efektu.
- Czytelne gałki/suwaki.
- Nazwy muzyczne.
- Jednostki Hz, dB, ms, BPM itd.
- Wartości aktualne i domyślne.

**INSTRUMENTY**
- BassAmbient i przyszłe instrumenty.
- Osobne sekcje Bass/Pad.
- Duże przyciski START/STOP.
- Parametry generatywności i brzmienia.
- Presety instrumentów.

**MIKSER**
- Guitar.
- Instruments.
- Master.
- Peak/RMS/Clip.
- Mute/Solo.

**BIBLIOTEKA**
- Lista zainstalowanych modułów.
- Dostępne aktualizacje.
- Dodawanie z katalogu.
- Import pakietu lokalnego.
- Odinstalowywanie.

**PRESETY**
- Szybkie zapisywanie i wczytywanie.
- Presety efektów.
- Presety instrumentów.
- Presety całej sesji.

**SYSTEM**
- JACK.
- Bufor audio.
- CPU/RAM.
- XRUN.
- HeadRush.
- MIDI.
- Informacje o wersji.
- Diagnostyka.

Interfejs powinien być responsywny, szybki, czytelny w świetle dziennym i wygodny dla palców.

Nie odświeżaj całej strony przy każdej zmianie parametru.

Nie generuj ciężkich animacji obciążających Raspberry Pi.

GUI ma być oddzielone od silnika DSP.

---

# 11. MENEDŻER MODUŁÓW I REPOZYTORIUM

Zaimplementuj bibliotekę zdalnych i lokalnych modułów.

Podstawowy kanał dystrybucji:

**GitHub Releases**

Menedżer powinien obsługiwać:

- Przeglądanie katalogu.
- Wersję modułu.
- Opis i kategorię.
- Wymagania sprzętowe.
- Wymaganą wersję ABI.
- Instalację.
- Aktualizację.
- Wyłączenie.
- Usunięcie.
- Przywrócenie poprzedniej wersji.
- Import modułu przez ZIP/paczkę lokalną.

Zaproponuj prosty format paczki, np.:

`JerzyModuleName-1.0.0-linux-arm64.jamod`

Powinna zawierać skompilowany moduł, manifest, dane GUI, metadane kompatybilności i sumy kontrolne.

Nie instaluj przypadkowych repozytoriów GitHub jako wykonywalnego kodu bez sprawdzenia ich kompatybilności i pochodzenia.

**GitHub** — główny katalog kodu i wydań.

**Google Drive** — opcjonalny import kopii zapasowych, presetów, sampli oraz IR; nie jest wymagany do działania systemu.

**Reddit** — źródło odkrywania projektów, a nie kanał instalowania wykonywalnych modułów.

Zaimplementuj lokalny indeks i lokalne instalowanie paczek bez internetu na Pi.

Każdy moduł powinien móc być rozwijany i budowany w osobnym repozytorium za pomocą dostarczonego szablonu SDK.

---

# 12. PAMIĘĆ I CPU

System ma być możliwie lekki.

Cele architektoniczne:

- Nieużywane moduły nie są przetwarzane.
- Wyłączone instrumenty nie wykonują niepotrzebnej syntezy.
- Bufory i pamięć są alokowane przed uruchomieniem przetwarzania.
- GUI nie obciąża nadmiernie procesora.
- Nie stosuj zbędnych procesów i frameworków.
- Nie uruchamiaj drugiego silnika audio dla każdego efektu.
- Minimalizuj kopiowanie buforów.
- Zachowuj cache poprawnie załadowanych zasobów.
- Stosuj oszczędne struktury danych i wydajny kod DSP.

Nie wprowadzaj arbitralnych limitów RAM/CPU bez pomiarów.

Dodaj benchmarki i raportuj zmierzone wyniki na środowisku testowym, wyraźnie rozróżniając je od pomiarów na prawdziwym Raspberry Pi 4B.

---

# 13. INSTALATOR WINDOWS — OBOWIĄZKOWY

To warunek odbioru projektu.

Użytkownik nie chce ręcznie wpisywać dziesiątek poleceń do Raspberry Pi.

Dostarcz:

**`JerzyAudioPlatform-v0.1.0-Windows-Installer.zip`**

W środku:

- `START-INSTALACJA.cmd`
- Skrypt instalacyjny PowerShell.
- Gotowa paczka systemu ARM64.
- Instrukcja `START_TUTAJ.txt`.
- Instrukcja `INSTRUKCJA_PL.pdf` lub czytelny HTML.
- Skrypt diagnostyki.
- Skrypt odinstalowania/przywrócenia.
- Manifest wersji i sumy kontrolne.

Uruchomienie ma wyglądać tak:

1. Rozpakowuję ZIP na Windows.
2. Dwukrotnie klikam `START-INSTALACJA.cmd`.
3. Instalator odnajduje Raspberry Pi w domowej sieci lub prosi o IP.
4. Podaję hasło SSH, jeśli jest wymagane.
5. Instalator przesyła paczkę na Pi.
6. Sprawdza zależności i architekturę.
7. Instaluje program.
8. Testuje JACK, moduły, GUI i routing.
9. Wyświetla adres panelu.
10. Informuje jednoznacznie, czy instalacja się udała.

Skrypt `.cmd` musi rzeczywiście uruchamiać instalator, a nie otwierać się w Notatniku.

Zapewnij działanie z katalogów o ścieżkach zawierających spacje i polskie znaki.

**Raspberry Pi nie może być zmuszone do pobierania kodu z GitHuba.**

Jeśli kompilacja na Pi jest konieczna, instalator musi wcześniej sprawdzić dostępność narzędzi i zależności. Nie może próbować fikcyjnej instalacji offline.

Preferuj gotowe binaria ARM64 zbudowane dla zgodnej wersji Raspberry Pi OS i biblioteki systemowej. Zweryfikuj zależności runtime.

Nie uznawaj automatycznie binariów skompilowanych na nowym Ubuntu za kompatybilne z Raspberry Pi OS.

Jeżeli środowisko nie pozwala zbudować w pełni kompatybilnych pakietów, wyraźnie wskaż konkretny brak i przygotuj alternatywną, rzeczywiście wykonalną ścieżkę.

---

# 14. BEZPIECZNA INSTALACJA I ROLLBACK

Zainstalowany obecnie MultiFX v0.2 działa i nie wolno go uszkodzić.

Nowa platforma ma:

- Własny katalog.
- Własne usługi systemd.
- Własny katalog ustawień.
- Własny port GUI.
- Własne dane i moduły.

Proponowany port GUI nowej platformy: **8093**.

Dotychczasowe porty:

- v0.2: 8090.
- v0.3: 8091.
- v0.4: 8092.

Nie nadpisuj tych usług.

Instalacja musi przebiegać w dwóch etapach:

**STAGING** — przygotowanie i testowanie plików bez wyłączania sprawnego systemu.

**ACTIVATION** — kontrolowane przełączenie toru audio na nową platformę.

Podczas aktywacji unikaj konfliktów klientów i routingu JACK.

W przypadku błędu:

- Przywróć poprzednie usługi.
- Przywróć poprzedni routing.
- Nie zmieniaj Wi-Fi.
- Nie zmieniaj konfiguracji HeadRush.
- Nie kasuj presetów.
- Zapisz czytelny log błędu.

Dodaj polecenie lub opcję w instalatorze:

**PRZYWRÓĆ POPRZEDNI MULTIFX**

Instalator musi działać również po przerwaniu wcześniejszej próby.

Nie wyłączaj aktywnej wersji na stałe, dopóki nowy system nie przejdzie kontroli gotowości.

---

# 15. GITHUB ACTIONS I GOTOWE PLIKI

Przygotuj automatyczny proces CI/CD.

Ma obejmować:

1. Build C++.
2. Testy DSP.
3. Testy hosta i grafu.
4. Testy modułów.
5. Testy zapisywania presetów.
6. Testy instalatora i skryptów.
7. Kontrolę zależności.
8. Budowanie pakietów ARM64.
9. Generowanie paczki instalacyjnej Windows.
10. Generowanie SHA256.
11. Publikację artifactów.
12. Publikację GitHub Release dla wersji wydaniowych.

Utwórz kompletny workflow, który kończy się **realnymi plikami do pobrania**, nie tylko zielonym komunikatem kompilacji.

Jeśli potrzebne jest uprawnienie do utworzenia Release, wykorzystaj standardowe uprawnienia GitHub Actions i prawidłową konfigurację `permissions`.

Nie dodawaj do pakietu pustych katalogów zamiast skompilowanych programów.

---

# 16. OBOWIĄZKOWE TESTY ODBIORCZE

Nie uznaj zadania za wykonane, zanim nie przejdą dostępne automatyczne testy.

Sprawdź:

### Host
- Uruchamia się.
- Otwiera klienta JACK z unikalną nazwą.
- Tworzy wymagane porty.
- Ładuje i usuwa moduły.
- Przełącza graf bez zawieszania audio.
- Poprawnie zapisuje stan.

### Instrument
- BassAmbient generuje rzeczywisty dźwięk.
- Bass i Pad uruchamiają się niezależnie.
- Stop zatrzymuje generowanie nowych nut.
- Zmiany root/scale/BPM działają.
- Nie występuje cyfrowe przesterowanie przy normalnych ustawieniach.

### Efekty
- Big Muff wytwarza wyraźny fuzz.
- Tone i Sustain realnie zmieniają wynik.
- Tape Drive daje kontrolowaną saturację.
- Bypass działa.
- Poziomy sygnału nie rosną niekontrolowanie.
- CAB/IR prawidłowo przetwarza sygnał.

### GUI
- Działa w przeglądarce.
- Wszystkie przyciski mają rzeczywiste funkcje.
- Parametry GUI odpowiadają parametrom DSP.
- Presety zapisują i odtwarzają ustawienia.
- Instalator modułów działa.
- Nie ma atrap przycisków.

### Instalacja
- ZIP zawiera wszystkie deklarowane pliki.
- CMD uruchamia PowerShell.
- Paczki nie wymagają internetu na Pi.
- Instalacja respektuje istniejące usługi.
- Rollback działa.
- Można ponowić przerwaną instalację.

### Sprzęt fizyczny

Przygotuj osobną listę testów wymagających Raspberry Pi 4B + HeadRush Core.

Nie oznaczaj ich jako wykonane bez rzeczywistego dostępu do sprzętu.

---

# 17. STRUKTURA REPOZYTORIUM

Zaprojektuj czytelną strukturę zbliżoną do:

```text
JerzyAudioPlatform/
├── core/
├── audio/
├── routing/
├── midi/
├── module-sdk/
├── module-host/
├── lv2-adapter/
├── modules/
│   ├── utility-gain-meter/
│   ├── bass-ambient/
│   ├── big-muff/
│   ├── tape-drive/
│   └── cab-ir/
├── module-manager/
├── web-ui/
├── presets/
├── deploy/
│   ├── raspberry-pi/
│   └── windows/
├── tests/
├── benchmarks/
├── docs/
├── .github/workflows/
├── README.md
└── CHANGELOG.md
```

Wskazana struktura jest propozycją, nie obowiązkiem. Możesz ją ulepszyć, jeśli uzasadnia to architektura.

Przygotuj również szablon osobnego repozytorium modułu, tak aby przyszły efekt można było utworzyć i opublikować bez modyfikacji kodu platformy.

---

# 18. CZEGO NIE ROBIĆ

Nie wolno:

- Rozbudować starego monolitu pod nową nazwą.
- Przepisywać wszystkiego od zera bez sprawdzenia istniejącego kodu DSP.
- Kopiować wadliwych efektów bez poprawek.
- Gubić funkcjonalności BassAmbient VST.
- Ukrywać przesterowania limiterem.
- Zakładać, że Raspberry Pi ma internet.
- Zakładać sztywnego adresu IP.
- Psuć hotspotu i sieci domowej.
- Nadpisywać istniejącego MultiFX v0.2.
- Wymagać ręcznego uruchamiania kilkunastu skryptów.
- Wysyłać samego kodu zamiast pakietu.
- Udawać, że sprzętowe testy zakończyły się sukcesem.
- Umieszczać pustych lub niedziałających funkcji w GUI.
- Ładować dowolnego kodu z internetu bez sprawdzenia.
- Bez uzasadnienia używać ciężkich frameworków.

---

# 19. WYNIK KOŃCOWY — KONKRETNE PLIKI

Na koniec oczekuję:

**A. Repozytorium GitHub**

`https://github.com/jurekbak71-dev/JerzyAudioPlatform`

**B. Paczka instalacyjna**

`JerzyAudioPlatform-v0.1.0-Windows-Installer.zip`

**C. Pakiet Raspberry Pi**

`JerzyAudioPlatform-v0.1.0-RPi4-arm64.tar.gz`

**D. Pakiety modułów**

Osobne, instalowalne pakiety BassAmbient, Big Muff, Tape Drive, CAB/IR i Utility Gain/Meter.

**E. Instrukcja**

`INSTRUKCJA_INSTALACJI_PL.pdf` lub czytelny dokument HTML, zawierający:

- Instalację na Windows.
- Łączenie z Raspberry Pi.
- Uruchomienie GUI.
- Dodawanie modułów.
- Regulację bufora JACK.
- Przywracanie poprzedniego systemu.
- Rozwiązywanie najczęstszych błędów.

**F. Raport testów**

Podaj:

- Wersję i commit.
- Wyniki testów.
- Zbudowane architektury.
- Rzeczywiste zależności.
- Sumy SHA256.
- Znane ograniczenia.
- Testy sprzętowe pozostające do wykonania.

**G. Gotowe linki**

W ostatniej odpowiedzi pokaż bezpośrednie, zweryfikowane linki do pobrania paczek z GitHub Actions lub GitHub Releases.

Nie twórz wymyślonych linków.

Jeżeli jakiś artifact nie powstał, wyraźnie napisz, dlaczego, i napraw proces budowania, jeżeli leży to w Twoich możliwościach.

---

# 20. KRYTERIUM SUKCESU

Użytkownik ma móc:

1. Pobrać ZIP na Windows.
2. Rozpakować go.
3. Uruchomić jeden instalator.
4. Połączyć się z Raspberry Pi przez sieć domową.
5. Zainstalować i aktywować system.
6. Otworzyć panel na iPhonie.
7. Dodać instrument BassAmbient.
8. Dodać Big Muff lub Tape Drive.
9. Zmieniać kolejność efektów i parametry.
10. Zapisywać presety.
11. Regulować bufor i monitorować XRUN.
12. W przyszłości doinstalować nową wtyczkę bez przebudowy hosta.

**Najważniejsze: stabilne audio, prawdziwe działanie efektów, muzykalność instrumentów, minimalne zużycie zasobów i ergonomiczne GUI.**

Nie interesuje mnie demonstracja technologii. Interesuje mnie użyteczna, modularna platforma audio.

## START

Przeanalizuj repozytoria, zaprojektuj architekturę, zaimplementuj system, przeprowadź testy, zbuduj pakiety i dostarcz gotowy instalator.

Pracuj samodzielnie aż do uzyskania kompletnego, zweryfikowanego wyniku albo jasno udokumentowanego ograniczenia środowiska.

**Nie kończ na napisaniu planu. Dostarcz kod, buildy, paczkę instalacyjną i instrukcję.**