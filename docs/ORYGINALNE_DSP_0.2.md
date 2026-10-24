# Oryginalne DSP — raport wersji 0.2.0

Wzorzec: oryginalne pełne wtyczki wskazane przez użytkownika, nie uproszczone moduły MultiFX. Pliki DSP skopiowano bez zmian; adaptery ABI są oddzielne. Big Muff zachowuje oryginalny kod prepare/process, solver i ten sam JUCE 7.0.12.

| Moduł | Commit źródła | Próbki x86 | Maks. błąd x86 | Maks. błąd ARM64/QEMU |
|---|---|---:|---:|---:|
| atomic-cluster-original | `1cd1beeeb5ec` | 809472 | 0 | 0 |
| bass-ambient-original | `c050475ecb90` | 380928 | 0 | 0 |
| big-muff-original | `d34128e75a97` | 158720 | 0 | 0 |
| memory-delay-original | `3a3c42384636` | 523776 | 0 | 0 |
| mx-delay-original | `aed456883fce` | 987648 | 0 | 0 |
| small-clone-original | `0aa20a4f0584` | 492032 | 0 | 0 |
| tape-drive-original | `3ee7f10f69b9` | 452352 | 0 | 0 |

Wszystkie siedem porównań przeszło w obu architekturach. W wykonanych przypadkach uzyskano identyczne próbki float32. To wynik konkretnej macierzy, nie dowód zgodności dla każdego możliwego sygnału i ciągu automatyzacji.

## Zakres

- 44,1 i 48 kHz; rozmiary bloków 64/128/256/512/1024.
- Parametry minimalne, pośrednie i maksymalne; wszystkie modele Clone, Memory Delay i Big Muff oraz wybory algorytmów MX; rozmaite konfiguracje stereo, tempa i bypassu.
- BassAmbient: modele/style/skale/seed, pad Flow/Krell, MIDI note/CC, wygładzanie jak oryginalny procesor i racki FX. Ścisły test używa natywnych nut MIDI; dodatkowy tryb samoczynnego grania jest funkcją platformy.
- W testowanym process nie zaobserwowano wywołań new/malloc/calloc/realloc ani zwalniania pamięci. Hooki obejmują wykonane ścieżki; nie zastępują pełnego audytu wszystkich możliwych ścieżek.
- Ukryto symbole C++ modułów, zachowując jedynie jawny eksport ABI. Eliminuje to przypadkową podmianę symboli DSP między modułami i procesem testowym.
- Weryfikowane są SHA256 importowanych plików oraz użytych modułów JUCE z archiwum przypiętego do konkretnego commitu.

## Poprawki systemu

- Importer obsługuje licencję, pochodzenie i raport porównania. Raport musi odpowiadać bibliotece i źródłu. Katalog instalatora Windows dodaje zewnętrzną zaufaną SHA256.
- Odtwarzanie poprzedniej sesji dopuszcza zachowane stare moduły; nowe dodawanie efektów wymaga potwierdzonego DSP original. Narzędzia Gain i CAB/IR są odrębnymi modułami użytkowymi.
- Każda aktywacja ma własny punkt przywracania bieżących usług i plików jednostek, zamiast nadpisywać jedyny historyczny checkpoint. Przerwana transakcja jest odzyskiwana przed kolejną próbą.
- Aktywny katalog wersji jest zapisywany dopiero po gotowości. Usługi użytkownika mogą działać po wylogowaniu SSH dzięki linger, gdy było to potrzebne.
- Dołączono osobny instalator NetworkManager: nowy profil domowy, potwierdzenie z nowej sieci, limit pięciu minut i przywracanie poprzedniego profilu; bez usuwania hotspotu. Hasło jest wpisywane na Pi i zapisywane w standardowym pliku NetworkManager z prawami 0600.

## Granice potwierdzenia

Nie wykonano z tej sesji fizycznej zmiany Wi-Fi ani pomiarów CPU/XRUN nowych modułów na Pi użytkownika. Testy Wi-Fi korzystają z wstrzykniętych odpowiedzi NetworkManager i obejmują błąd połączenia, brak potwierdzenia, potwierdzenie i zachowanie starego profilu. Rzeczywista dostępność domowego routera wymaga próby użytkownika.

Oryginalne algorytmy mogą być znacznie cięższe od demonstracyjnych zamienników. Nie zmniejszono oversamplingu ani liczby funkcji, aby ukryć koszt CPU. Hostowe poziomy/mikser/limiter są poza porównaniem surowego DSP. Nie jest to pełna zgodność GUI, formatów presetów VST ani trybu obliczeń audio 64-bit.

Stare raporty 0.1 w docs są historyczne. Bieżące przebiegi CI i osadzone COMPATIBILITY.json określają dokładne zbudowane biblioteki.
