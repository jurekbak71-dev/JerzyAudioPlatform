# Jerzy Audio Platform 0.2.1 — aktualizacja po testach Raspberry Pi

Wydanie testowe po zgłoszeniach utraty sterowania, XRUN, nieczytelnego GUI i użycia niewłaściwego Bass Ambient. Nie jest potwierdzeniem wydajności wszystkich kombinacji oryginalnych DSP na fizycznym Pi.

## Aktualizacja

1. Pobierz cały instalator Windows 0.2.1 i rozpakuj do nowego folderu.
2. Pozostań w działającym domowym Wi-Fi. Uruchom `START-INSTALACJA.cmd`; adres `bassambient.local` albo aktualne IP Pi. Po sprawdzeniu paczki wpisz `TAK`.
3. Aktywacja zatrzyma poprzedni host, zaktualizuje starsze oficjalne moduły i uruchomi nową wersję. Zachowa presety, IR, sieć i wcześniejszy wybór autostartu. Poprzednie moduły oraz jednostki mają kopię w historii aktywacji. Nie uruchamiaj ponownie konfiguracji Wi-Fi, jeśli sieć już działa.
4. Otwórz panel i użyj Ctrl+F5. W SYSTEMIE wybierz **256 próbek**, ewentualnie 512. Wartość jest zapamiętywana po restarcie. Nie zaczynaj testu ciężkich DSP od 64 próbek.
5. Testuj po jednym module. Zapisane stare ustawienia są zachowane; istniejący Muff z wybranym pełnym obwodem zachowa ten wybór. Do pierwszego testu ustaw **Model obwodu → Legacy**, a potem jeden z sześciu modeli klasycznych.
6. Stary `bass-ambient-original` to instrument bez PRO, zachowany wyłącznie dla poprzednich sesji. Usuń jego instancję z aktualnego łańcucha i dodaj **Jerzy Bass Ambient PRO — modalny DSP** na torze Instrumenty. Nowa instancja ma instrumenty wyłączone. Wybierz JAM, włącz jeden instrument i GENERATE; głośność jest na górze.

## Co zmieniono

- **Bufor:** wywołanie JACK bez zatrzymywania usług, usuwania gniazda i ponownego odtwarzania presetów. Graf, instancje, parametry i połączenia pozostają aktywne. Rozmiary 512 → 128 → 256 sprawdzono na rzeczywistym serwerze JACK dummy z zachowaniem dźwięku i identyfikatorów instancji.
- **Sterowanie i odzyskanie:** ograniczony czas oczekiwania przy podmianie grafu; poprawione zakończenie czytania zamkniętego gniazda. Panel ponawia łączenie również po początkowym błędzie. Entry usługi obserwuje postęp callbacków; jednostka ma ograniczony czas zatrzymania. Przyciski **Restart audio** oraz **Odzyskaj audio bez efektów** działają bez restartu Pi. Drugi odkłada poprzednią sesję do kopii i uruchamia pusty graf; zapisane presety i IR pozostają.
- **Ochrona:** czas przetwarzania pojedynczego modułu jest porównywany z budżetem bloku. Trzy przekroczenia 85% lub jedno ponad 400% przełączają moduł w bypass. Nieprawidłowy/niebezpieczny sygnał również uruchamia ochronę. Dodatkowo, sześć kolejnych przekroczeń 95% czasu całego callbacka omija najdroższy aktywny moduł, nawet jeśli każdy moduł osobno mieści się w limicie. Panel pokazuje powód. To zabezpieczenie, nie zwiększenie mocy procesora ani dowód bezproblemowego grania przy każdym buforze.
- **Big Muff:** nowe instancje zaczynają od oryginalnego Legacy zamiast kosztownego pełnego solvera. Model klasyczny jest widoczny tylko w Legacy; wybór pełnego obwodu pozostaje dostępny. Głośność, tone i sustain sprawdzono na renderowanym sygnale. Nie zmniejszono oversamplingu i nie zastąpiono obwodów uproszczonym DSP.
- **Atomic Cluster:** oryginalny rdzeń zachowany, czytelny wybór 1–64 atomów, zabezpieczenie przed przeciążeniem. Dwunastosekundowy test zmienia 16/64 głosy, pattern i flat dynamics oraz sprawdza ograniczenie wyjścia i brak alokacji callbacka. Trzaski na Pi wymagają sprawdzenia przy 256/512 i obserwacji XRUN; test programowy nie potwierdza fizycznej wydajności.
- **CAB / IR:** nazwa impulsu i stan aktywny/bypass w łańcuchu oraz parametrach. Głośność, udział IR i wygładzone odwrócenie polaryzacji; dry opóźnione o 64 próbki dla zgodności z wet. Presety z wcześniejszą pojedynczą kontrolką poziomu są migrowane przez dopuszczenie dopisanych parametrów z ich wartościami domyślnymi.
- **GUI:** grafitowy panel studyjny, uporządkowane sekcje i głośność instrumentów na górze. MX ma dwa osobne silniki, listy algorytmów i parametry tylko wybranego algorytmu. Nie pokazuje nieużywanych panoram głowic ani kontrolek wet FX. Bass PRO ma osobne sekcje BAS / AMBIENT / ARP / PERKUSJA / KRELL / MIKSER / MASTER FX, a wybory mają listy rozwijane.
- **THRU JACK:** wyłącza i przywraca wyłącznie bezpośrednie połączenia fizycznych wejść/wyjść audio JACK. Nie usuwa MIDI ani połączeń prowadzących przez host. **Wewnętrznego monitoringu HeadRush nie da się wyłączyć samym rozłączeniem JACK**; jeżeli suchy sygnał pozostaje, trzeba ustawić monitoring w samym urządzeniu.
- **Wi-Fi:** zawiera już poprawkę oczekiwania na DHCPv4. Aktualizacja nie przełącza działającej sieci.

## Bass Ambient PRO z modalnym DSP

Źródło: `JerzyBassAmbientVST3`, gałąź `feature/modal-dsp-on-pro-20261024`, commit `673e0def70d06e29d35ba3e69c40d04f0e9c9abf`. Oryginalne `Core.h`, `ProEngines.h`, `ModalExciter.h` i definicje parametrów są przypięte SHA256. Nie korzystamy tu z wcześniejszego rdzenia bez PRO.

Port obejmuje Bass (ACID / SUB / Classic / Bass Guitar), Ambient z dwiema warstwami, Arp, czterogłosowe Drums, osobny Krell, modalny rezonans i atak Bass/Ambient, racki instrumentów i master, powroty send oraz mikser ośmiu ścieżek do wspólnego stereo. 725 stabilnych identyfikatorów pozostaje w metadanych; sterowanie 724 porównano z odczytem oryginalnego procesora VST (wybór źródła ma osobną adaptację hosta). Ciągłe wartości zachowują oryginalne wygładzanie.

MIDI: kanał 1 Bass, 2 Ambient, 3 Arp, 4 Krell, 10 Drums. MIDI/JAM są dostępne w panelu. FX korzystają z oryginalnego zarządzania zasobami: ich bufory są przygotowywane i zwalniane w osobnym wątku, nie w callbacku. Test aktywacji/wyłączania racków sprawdza brak alokacji w wątku audio.

**Zakres portu:** nie przeniesiono edytora Composer/song, importu i eksportu MIDI/WAV, nagrywania LIVE, 11 wyjść VST ani odbiornika zewnętrznego MIDI CLOCK. Te funkcje nie są oferowane jako działające kontrolki. Bluetooth pozostaje na później. Surowe porównanie próbek PRO obejmuje pięć sekcji, modalne parametry i MIDI note/CC/bend przy wyłączonych FX; asynchroniczny start racków FX ma osobny test, bez deklaracji identycznego czasu ich przyłączenia względem Windows.

## Walidacja i granice

CMake/CTest: 10 testów, w tym osiem porównań rdzeni oryginalnych i test zdrowia Muff/Atomic. Testy Python obejmują paczki, aktywację/rollback, wymianę istniejących modułów oraz Wi-Fi. Integracja używa rzeczywistego JACK dummy i HTTP: audio, bypass, MIDI, live buffer, THRU, odtwarzanie grafu po ponownym starcie. Chromium sprawdza MX i PRO na desktopie oraz telefonie; nie jest to test Safari.

Ostateczne wyniki i dokładne binaria określa przebieg GitHub Actions dla danego taga oraz osadzone `COMPATIBILITY.json`. QEMU nie mierzy mocy Pi. Potrzebny pozostaje odsłuch na fizycznym HeadRush/Pi, szczególnie ciężkich modeli Muff, dużej liczby atomów i wielu warstw PRO. Jeżeli ochrona przełącza moduł w bypass, ogranicz łańcuch albo wybierz większy bufor; algorytmy pozostają oryginalne.
