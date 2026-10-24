# Aktualizacja 0.2.0

Bieżący zakres i nadal otwarte ograniczenia opisuje [raport 0.2](ORYGINALNE_DSP_0.2.md). Poniższa lista jest historycznym stanem 0.1; oryginalne DSP, pojedyncze moduły i publikacja zostały od tego czasu uzupełnione.

# Co pozostaje do pełnego odbioru

To wydanie rozwojowe nie spełnia jeszcze całej specyfikacji WYMAGANIA.md.

1. Nie wykonano testu fizycznego Raspberry Pi 4B, HeadRush Core, Windows OpenSSH/PowerShell ani Safari na iPhonie. Nie można potwierdzić beztrzaskowej pracy, jakości odsłuchowej, rebootu ani zgodności wykrytego urządzenia.
2. Testy chmurowe JACK dummy zgłaszały XRUN. Wyników CPU chmury i emulacji QEMU nie wolno przenosić na Pi. Nie wykonano wielogodzinnego testu stabilności ani pełnych pomiarów THD/aliasingu i wszystkich kombinacji parametrów.
3. Istnieją skrypty stagingu, aktywacji i rollbacku, ale działanie prawdziwego systemd i przywrócenie faktycznej konfiguracji użytkownika wymaga testu sprzętowego. Nie uruchomiono ich przeciwko urządzeniu użytkownika. Automatyczna aktywacja wymaga już działającego JACK i rozpoznawalnych usług MultiFX; nie obsługuje dowolnych zewnętrznych supervisorów.
4. Bufor może być zmieniany przez opcjonalnego pomocnika usług. Zmiana sample rate i liczby okresów nie jest zaimplementowana; wartości te pozostają własnością istniejącej konfiguracji JACK. Latencja wyświetlana w GUI jest czasem jednego bufora, a nie pomiarem round-trip ani całkowitej latencji urządzenia. Brak kompensacji latencji między torami.
5. Moduły nie są sandboxowane. SHA256 wykrywa uszkodzenie tylko przy zaufanej sumie. Nie ma podpisanego zdalnego katalogu, automatycznych aktualizacji z GitHub Releases ani pobierania z Google Drive. Lokalny import, aktualizacja, rollback i usuwanie paczek są zaimplementowane.
6. JFX v2 i LV2 nie mają jeszcze adapterów. Ich biblioteki nie są akceptowane jako moduły ABI 1. Nie próbuje się ładować Windows VST3 na ARM.
7. Sesje zapisują graf, parametry, MIDI CC, mikser i zasoby IR. Są osobne presety modułów, ale nie ma migracji stanu między niezgodnymi wersjami ABI, ani dowolnego grafu z dodatkowymi torami. Nie ma MIDI clock slave ani pełnego zarządzania JACK transport.
8. BassAmbient zachowuje oryginalny rdzeń i parametry, ale dowód zgodności obejmuje określone scenariusze testowe. Brakuje pełnej macierzy porównania wszystkich funkcji oryginalnego VST3, testów odsłuchowych i oceny muzykalności. Fuzz i Tape Drive są modelami algorytmicznymi bez potwierdzonej zgodności ze sprzętem; nie są pełnymi modelami obwodowymi.
9. Paczka offline wymaga istniejących bibliotek JACK, glibc >= 2.36 i libstdc++ z GCC >= 12. Instalator nie pobiera ani nie udaje instalacji brakujących zależności; przerwie staging z komunikatem. Nie zmienia sieci, nie flashuje SD i nie instaluje systemu operacyjnego.
10. Repozytorium GitHub i Release nie zostały utworzone: API w tej sesji zwróciło Forbidden. Workflow jest przygotowany lokalnie, ale nie został wykonany przez GitHub Actions. Brak publicznych zweryfikowanych linków do artifactów; istnieją rzeczywiste paczki w katalogu dist.

Te braki uniemożliwiają oznaczenie produktu jako kompletnego, stabilnego v0.1.0. Należy pracować na osobnej kopii karty, zachowując CARD-00.

Aktualizacja publikacji: dostęp do API GitHub został przywrócony. Przygotowano wydanie testowe oraz skróty CMD do aktywacji, panelu, diagnostyki i rollbacku. Wynik publikacji należy sprawdzić na stronie repozytorium.
