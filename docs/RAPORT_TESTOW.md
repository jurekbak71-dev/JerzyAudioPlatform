# Raport walidacji — 24 października 2026

Wersja: **0.1.0, rozwojowa**. Nowe repozytorium nie zostało opublikowane; nie ma nowego commitu zdalnego ani uruchomienia GitHub Actions. Referencyjne commity i pochodzenie kodu podaje AUDYT.md.

## Wykonane i zaliczone

- Kompilacja hosta i pięciu modułów Linux x86_64 (GCC 14) oraz Linux AArch64 (GCC 12.2, sysroot Debian Bookworm).
- CTest: 1/1 zestaw nowych testów DSP na x86_64 i 1/1 pod QEMU AArch64. Pełny przebieg i wyniki: BUILD-TESTS.log oraz DSP-TESTS.log. Sprawdzono generowanie dźwięku, 44,1/48 kHz, bloki 64–1024, skończoność próbek, poziomy, działanie parametrów fuzz/tape, impuls splotu i zgłoszone 64 próbki latencji.
- Porównanie oryginalnego rdzenia BassAmbient z portem przy identycznej nucie, seedzie, parametrach float i wygładzaniu, uwzględniające jawny fade wyjścia. Nie jest to pełna macierz presetów VST3.
- 9 testów Pythona: import/aktualizacja/rollback/usunięcie modułu, odrzucanie złej SHA256, ABI, uszkodzonej zawartości, duplikatów i traversal; odzyskiwanie po przerwanym przełączeniu; rollback aktywacji z wymuszonym błędem gotowości. Ostatni test używa atrap systemd/JACK, nie fizycznego systemu.
- Integracja z rzeczywistym nazwanym JACK dummy: porty i unikalne nazwy klientów, przepływ audio gain/bypass, natywne MIDI CC Learn, graf, osobny tor instrumentu, HTTP, presety sesji i modułu z polskimi znakami, odrzucanie błędnych parametrów i transakcji.
- Test 30 sekund zmian grafu z rzeczywistym przechwytywaniem wyjścia i kontrolą postępu callbacków. Wynik i liczba cykli: INTEGRATION-TESTS.log. To nie test wielogodzinny. Wystąpiły XRUN w chmurze; nie ma podstaw do deklaracji beztrzaskowej pracy na Pi.
- Chromium z viewportem 390×844: sterowanie Ambient, mikser, zapis presetu, biblioteka i diagnostyka, brak błędów JS oraz przepełnienia szerokości. Nie jest to Safari/iOS. Zrzut: panel-mobile.png.
- Parser PowerShell 7.5.4 na Linux: wszystkie skrypty przechodzą. Runtime pobrano z oficjalnego wydania i sprawdzono z oficjalnym SHA256. Nie sprawdzono wykonania instalacji na Windows ani parsera Windows PowerShell 5.1.
- Osobny projekt wygenerowany przez SDK: samodzielna kompilacja, utworzenie .jamod, instalacja i załadowanie eksportu ABI bez przebudowy hosta.
- Powtórzenie instalacji lokalnego toolchainu i uruchomienia usług: zachowano źródła referencyjne; drugi start nie uruchomił duplikatów.

## Pomiary i zależności

POMIARY_DSP.json zawiera rzeczywiście zmierzone poziomy i THD harmonicznych 2–10 przy 44,1/48 kHz. Nie jest to kalibracja kostki Big Muff ani pomiar aliasingu. Czasy obejmują narzut testera Python i dotyczą maszyny x86_64.

Binarium hosta ARM64 wymaga symboli najwyżej GLIBC_2.34 i GLIBCXX_3.4.29; zbudowano je na bazie Bookworm/glibc 2.36. Dodatkowo wymaga systemowego libjack.so.0, libstdc++.so.6, libgcc_s.so.1, libm.so.6 i libc.so.6. Biblioteki modułów deklarują swoje odczytane wymagania w manifestach paczek. Serwer WWW wymaga Python >= 3.9, bez pipowych bibliotek aplikacyjnych. Nie zapakowano bibliotek systemowych ani serwera JACK; offline oznacza gotowe binaria przy wcześniej spełnionych zależnościach. Staging odmawia instalacji przy ich braku.

## Niewykonane lub zablokowane

- Cała lista TESTY_SPRZETOWE.md, prawdziwy Windows, systemd użytkownika na Pi, HeadRush i iOS Safari.
- Wielogodzinna stabilność, pełna macierz DSP i porównania odsłuchowe.
- GitHub Actions i publiczne pliki Release: api.github.com jest blokowane przez proxy CONNECT 403. Dodanie domeny zapisano w szkicu środowiska; wymaga zastosowania w ustawieniach. Nie jest to dowód braku uprawnień GitHub.
- Dalsze braki funkcjonalne podaje OGRANICZENIA.md. Produkt nie jest kompletnym spełnieniem WYMAGANIA.md i nie powinien otrzymać statusu stabilnego wydania.

## Pliki

Prawdziwe archiwa i pięć paczek modułów znajdują się w dist. SHA256.json i SHA256SUMS.txt zawierają sumy gotowych plików. Nie podajemy zmyślonych odnośników do GitHub.
