# Interfejs dla własnych repozytoriów LV2

Kod wtyczek jest utrzymywany w ich dotychczasowych repozytoriach VST. Ten projekt zawiera wyłącznie host. Nie importuj implementacji instrumentów/efektów do hosta.

- Dystrybuuj kompletny bundle `Nazwa.lv2` jako ZIP z jednym katalogiem na najwyższym poziomie i opublikuj SHA256 ZIP-a. Manifest wskazuje bibliotekę `.so` dla Linux ARM64 (Bookworm, GCC 12/glibc 2.36) na Pi; do testów hosta x86 użyj oddzielnej kompilacji x86_64.
- Utrzymuj stałe URI wtyczki i symbole portów między kompatybilnymi wydaniami. Parametry użytkownika przechodzą przez porty Control. Podaj poprawne wartości domyślne, zakresy, flagi integer/toggled i Scale Points.
- Audio: 0–2 wejścia, 1–2 wyjścia. Brak wejść audio oznacza instrument/generator dodawany do toru instrumentów; efekty przetwarzają aktualny sygnał toru.
- MIDI: port wejściowy Atom Sequence z atom:supports midi:MidiEvent. Przekazywane są krótkie komunikaty (Note On/Off, CC, PC, Pitch Bend) wraz z offsetem próbki w bloku. SysEx nie jest obsługiwany w tej wersji.
- Host zapewnia urid:map/unmap, options:options, buf-size:boundedBlockLength, lv2:isLive i worker:schedule. Nie wymagaj fixedBlockLength ani powerOf2BlockLength; bloki mogą się zmieniać. Maksymalny blok to 8192 próbek.
- Atom Time Position opisuje zegar i tempo hosta. Rytm hosta ma 4/4; nie jest to pełna synchronizacja JACK Transport.
- Do ciężkiej pracy użyj LV2 Worker. Żądania i odpowiedzi mają limit 64 KiB, kolejki po osiem pozycji. run() nie może alokować, czekać na blokadę, czytać plików ani wykonywać długich operacji.
- Stan inny niż parametry zapisuj przez LV2 State. Host robi snapshot poza callbackiem, przy wstrzymanej instancji. Nie ma edytora Patch/Path w panelu do wyboru plików, CV ani własnych okien UI wtyczek.
- Obowiązkowe nieobsługiwane feature URI skutkują czytelną odmową załadowania. Nie zastępuj brakującej funkcji cichym ignorowaniem jej w wymaganiach TTL.

Przetestuj efekt/syntezator w standardowym hoście LV2 przed integracją na Pi. Host sprawdza wymagania i architekturę paczki, ale sam format LV2 nie redukuje kosztu DSP.
