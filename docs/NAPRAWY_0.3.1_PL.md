# Jerzy Audio Platform 0.3.1 — odzyskiwanie po ochronie CPU

## Aktualizacja preview.4

To wydanie zmienia wykonanie obliczeń PRO i Big Muff, a nie tylko diagnostykę. PRO 0.3.1 używa szybszej funkcji nasycenia w zakresie [-1,1], z błędem poniżej 1e-15 względem tanh w teście gęstej siatki; poza zakresem zachowuje oryginalną funkcję. Test z nakładaniem głosów Flow przez 20 sekund obejmuje pięć silników i porównanie wyjścia float32 z oryginałem. Nie ograniczono głosów, racków, oversamplingu ani ustawień użytkownika.

Na tej samej maszynie x86_64 dwie próby renderowania 20 sekund Bass + Ambient z domyślnymi FX zużyły przed zmianą 6.306 i 6.741 s CPU, po zmianie 4.289 i 4.405 s CPU (około 33% mniej). To pomiar kosztu obliczeń, nie gwarancja wydajności Pi. Powtarzalny pomiar: `g++ -std=c++20 -O3 -Imodule-sdk benchmarks/pro_cpu.cpp -pthread -o build/pro-cpu`, następnie `build/pro-cpu 20`.

Big Muff 0.2.2 zachowuje solver i wszystkie modele, ale przechowuje gotowe macierze dla powtarzających się liniowych części obwodu i częstotliwości adaptacyjnych podkroków. Oblicza też pary wykładniczych charakterystyk elementów wspólnie z użyciem instrukcji wektorowych. Porównanie obejmuje wszystkie 20 modeli; wynik musi nadal spełniać limit 1e-7 (w teście x86_64 różnica wyniosła zero). Zysk CPU w próbach obwodu Triangle był niewielki, około 5%, więc nie stanowi dowodu usunięcia trzasków ani gwarancji, że każdy model obwodu mieści się w czasie rzeczywistym na Pi.

Zakładka SYSTEM rozpoznaje proces JACK także wtedy, gdy MainPID usługi jest skryptem, a właściwy jackd/jackdmp działa jako proces potomny w tej samej grupie usługi. Obsługuje instalację administratora poza /usr/bin oraz samo `jackd` w argv. Wymaga pliku i katalogów należących do root, bez prawa zapisu dla grupy i innych użytkowników; nie wykonuje dowolnego wskazanego programu.

Pełny instalator podmienia PRO i Big Muff przy aktywacji dzięki nowym numerom wersji modułów. Zachowuje kopie do rollbacku. Nie zwiększa automatycznie bufora. Fizyczne odsłuchy, przeciążenia i trzaski nadal wymagają próby na Pi.

## Wcześniejsze poprawki preview.2–3

Pełna aktualizacja: rozpakuj Windows-Installer.zip do nowego folderu, uruchom START-INSTALACJA.cmd i potwierdź aktywację TAK. Zachowaj bufor używany do odtworzenia problemu. Nie zmieniamy automatycznie parametrów brzmienia ani liczby głosów.

Po ochronie CPU Start JAM i Włącz moduł tworzą świeżą instancję tego modułu poza wątkiem audio. Zachowują identyfikator, parametry, tor oraz mapowania MIDI; pozostałe instancje pozostają te same. Usuwa to zamrożone głosy/ogony, które wcześniej mogły natychmiast ponownie wywołać ochronę pomimo zmiany parametrów. Następuje krótkie wyciszenie grafu podczas bezpiecznej podmiany. Ta naprawa odzyskiwania nie zmniejsza stałego kosztu pełnego DSP.

Komunikat ochrony odróżnia stałe przeciążenie modułu, pojedynczy bardzo kosztowny blok i łączne przeciążenie łańcucha. Wyświetla ostatnie, średnie i szczytowe zużycie CPU, czas bloku i — dla przeciążenia łańcucha — koszt całego toru. SYSTEM → Pobierz raport diagnostyczny zapisuje te dane i parametry. Pozwala to diagnozować rzeczywiste Pi bez kolejnego polecenia PowerShell.

Ambient w trybie Flow nakłada nowe akordy na wybrzmienia starych; obciążenie po dłuższej grze może być większe niż tuż po starcie. Do porównania można ręcznie wybrać EFEKT → PRO → AMBIENT → Brzmienie → Ambient behaviour: Hold, następnie Start JAM. Jest to test ograniczenia nakładania głosów, nie zamiana oryginalnego DSP. Większy bufor może pomóc przy skokach obciążenia, ale nie usuwa stałego kosztu syntezy przekraczającego możliwości jednego wątku audio.

Nie zmieniono DSP względem 0.3.0. Próby dalszych optymalizacji nie wykazały istotnego zysku w wykonanym pomiarze, dlatego nie są częścią tej poprawki. Nie ograniczono głosów ani racków FX.

Przyczyna zgłoszonego wyłączenia na Pi przy 256 próbkach nadal wymaga rzeczywistych pomiarów. Nie potwierdzono sprzętowo naprawy trzasków. Funkcje Bluetooth i SYSTEM pozostają jak w 0.3.0; radio Hotone/iPhone i sterownik HeadRush wymagają próby sprzętowej.

Raport diagnostyczny zawiera teraz `hardware.host_health`: temperaturę w °C, bieżące taktowanie CPU w MHz oraz flagi `vcgencmd get_throttled`. Flagi bieżące są oddzielone od historycznych (`*_occurred`, od uruchomienia Pi). Brak odczytu ma wartość `null`, a nie zero. Odczyty są odświeżane co pięć sekund; nie zmieniają ustawień Pi, bufora ani DSP. Dane pomagają sprawdzić ograniczenia zasilania i temperatury, ale same nie potwierdzają przyczyny przeciążenia.

Monitor sprzętu ogranicza każdy odczyt statusu Bluetooth i PAN do trzech sekund. Zawieszony odczyt radiowy zgłasza błąd w odpowiedniej sekcji, zamiast zatrzymywać publikowanie statusu audio. Sprawdzenie terminu przywrócenia transakcji JACK następuje przed odczytami radiowymi. Testy używają lokalnego D-Bus i symulowanego BlueZ; nie potwierdzają działania radia na Pi.
