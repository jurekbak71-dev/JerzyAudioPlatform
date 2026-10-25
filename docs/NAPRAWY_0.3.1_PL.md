# Jerzy Audio Platform 0.3.1 — odzyskiwanie po ochronie CPU

Pełna aktualizacja: rozpakuj Windows-Installer.zip do nowego folderu, uruchom START-INSTALACJA.cmd i potwierdź aktywację TAK. Zachowaj bufor używany do odtworzenia problemu. Nie zmieniamy automatycznie parametrów brzmienia ani liczby głosów.

Po ochronie CPU Start JAM i Włącz moduł tworzą świeżą instancję tego modułu poza wątkiem audio. Zachowują identyfikator, parametry, tor oraz mapowania MIDI; pozostałe instancje pozostają te same. Usuwa to zamrożone głosy/ogony, które wcześniej mogły natychmiast ponownie wywołać ochronę pomimo zmiany parametrów. Następuje krótkie wyciszenie grafu podczas bezpiecznej podmiany. Ta naprawa odzyskiwania nie zmniejsza stałego kosztu pełnego DSP.

Komunikat ochrony odróżnia stałe przeciążenie modułu, pojedynczy bardzo kosztowny blok i łączne przeciążenie łańcucha. Wyświetla ostatnie, średnie i szczytowe zużycie CPU, czas bloku i — dla przeciążenia łańcucha — koszt całego toru. SYSTEM → Pobierz raport diagnostyczny zapisuje te dane i parametry. Pozwala to diagnozować rzeczywiste Pi bez kolejnego polecenia PowerShell.

Ambient w trybie Flow nakłada nowe akordy na wybrzmienia starych; obciążenie po dłuższej grze może być większe niż tuż po starcie. Do porównania można ręcznie wybrać EFEKT → PRO → AMBIENT → Brzmienie → Ambient behaviour: Hold, następnie Start JAM. Jest to test ograniczenia nakładania głosów, nie zamiana oryginalnego DSP. Większy bufor może pomóc przy skokach obciążenia, ale nie usuwa stałego kosztu syntezy przekraczającego możliwości jednego wątku audio.

Nie zmieniono DSP względem 0.3.0. Próby dalszych optymalizacji nie wykazały istotnego zysku w wykonanym pomiarze, dlatego nie są częścią tej poprawki. Nie ograniczono głosów ani racków FX.

Przyczyna zgłoszonego wyłączenia na Pi przy 256 próbkach nadal wymaga rzeczywistych pomiarów. Nie potwierdzono sprzętowo naprawy trzasków. Funkcje Bluetooth i SYSTEM pozostają jak w 0.3.0; radio Hotone/iPhone i sterownik HeadRush wymagają próby sprzętowej.

Raport diagnostyczny zawiera teraz `hardware.host_health`: temperaturę w °C, bieżące taktowanie CPU w MHz oraz flagi `vcgencmd get_throttled`. Flagi bieżące są oddzielone od historycznych (`*_occurred`, od uruchomienia Pi). Brak odczytu ma wartość `null`, a nie zero. Odczyty są odświeżane co pięć sekund; nie zmieniają ustawień Pi, bufora ani DSP. Dane pomagają sprawdzić ograniczenia zasilania i temperatury, ale same nie potwierdzają przyczyny przeciążenia.
