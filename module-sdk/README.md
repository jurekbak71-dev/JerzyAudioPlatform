# SDK modułów ABI 1

Jedynym obowiązkowym eksportem jest `const JAModule *ja_module(void)`. Granica ABI używa C, rozmiarów struktur, typów o stałej szerokości i wskaźników. Nie przekazuje klas C++, STL ani wyjątków. Biblioteki muszą być budowane dla architektury i systemowych bibliotek urządzenia.

Deskryptor podaje ABI, identyfikator, wersję, kategorię instrument/efekt, parametry oraz funkcje create/destroy/process/latency. Deskryptor i tablice muszą istnieć przez cały czas załadowania biblioteki. Parametry mają stabilne ID, polską etykietę, jednostkę, zakres, wartość domyślną, opcjonalne nazwy wyborów i flagę wartości całkowitej. Wartości przekazywane są w jednostkach parametru, nie zawsze w zakresie 0–1.

`create(sr,max_frames,asset)` przygotowuje pamięć i zasoby poza wątkiem audio. NULL oznacza odmowę inicjalizacji. `destroy` działa wyłącznie na wątku sterującym. `process` otrzymuje dwa planar­ne kanały, BPM/pozycję/stan transportu, parametry i ograniczoną tablicę zdarzeń MIDI z pozycją próbki. Instrument ignoruje wejście i generuje wyjście; efekt przetwarza wejście. Oba kanały wyjścia muszą zostać wypełnione. Mono można powielić do stereo. Wskazanych buforów nie wolno zachowywać po powrocie funkcji.

W `process` zabronione są alokacje i zwalnianie pamięci, mutexy, oczekiwanie, I/O, logowanie, sieć i wyjątki. Przygotuj pamięć w create; wygładzaj ciągłe parametry i obsłuż nieprawidłowe dane. Host usuwa NaN/Inf z wyników i wyłącza denormale na x86/ARM64, ale moduł nadal odpowiada za deterministyczny koszt obliczeń. Test wykrywania `operator new` jest wskaźnikiem regresji, nie formalnym dowodem braku wszystkich możliwych alokatorów.

Host ustawia cele parametrów atomowo, kopiuje je raz na blok, a moduły wygładzają wartości podczas przetwarzania. CC Learn działa z dokładnością bloku, natomiast natywne MIDI ma pozycje próbek. Host wygasza sygnał przez 20 ms, zmienia niezmienny graf i wznawia sygnał. Oczekiwanie i usuwanie poprzedniego grafu odbywa się w kontrolerze. Bypass jest rampą 10 ms; całkowicie wyłączone efekty nie wykonują process. BassAmbient pomija syntezę przy wyłączeniu obu warstw. Krótka przerwa po zmianie grafu jest celowa; nie jest to bezprzerwowe przenoszenie ogonów między grafami.

Stan ABI 1 składa się z parametrów i identyfikatora zasobu IR; host zapisuje je w sesji JSON. Nie ma jeszcze wersjonowanych binarnych blobów stanu modułu, kompensacji latencji równoległych torów ani adapterów JFX/LV2. Rozszerzenie struktur wymaga nowej wersji ABI.

Biblioteki to zaufany kod natywny wykonywany w procesie audio; sprawdzenie manifestu nie tworzy piaskownicy. Nie instaluj nieznanych modułów. Szablon osobnego projektu generuje `tools/new_module.py`.
