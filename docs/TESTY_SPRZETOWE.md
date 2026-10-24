# Lista odbioru fizycznego — wszystkie poniższe niewykonane

- Odczytać model Pi, OS, architekturę, glibc, libstdc++, wersję JACK, urządzenie i prawdziwe parametry serwera. Zapisać aplay -l, /proc/asound/cards, porty JACK i połączenia.
- Przetestować staging offline przy odłączonym WAN i działającym LAN. Sprawdzić, że v0.2 pozostaje aktywne i nie zmieniają się NetworkManager, Wi-Fi, hotspot ani presety.
- Sprawdzić Windows 10/11: dwuklik CMD, hasło SSH, host key, brak .local, ręczny IP, ścieżka ze spacjami i polskimi znakami, przerwane SCP, błędna SHA256, brak zależności, ponowienie stagingu.
- Zmierzyć wejścia/wyjścia HeadRush, mono/stereo, poziomy, szum, clip i bezpieczeństwo odsłuchu. Zacząć od małych głośności.
- Aktywować nowy system, sprawdzić routing, panel 8093, odzyskanie poprzednich usług przy błędzie i opcję PRZYWRÓĆ. Zweryfikować niezmienione porty 8090–8092 i sieć.
- Przeprowadzić 8 godzin grania/generowania z BassAmbient, fuzz/tape, długimi IR oraz zmianami parametrów/grafu. Zapisać CPU/RAM/temperaturę/throttling/XRUN co minutę dla 44,1/48 kHz i 64/128/256/512/1024 próbek.
- Zmierzyć round-trip latency fizyczną pętlą audio. Nie utożsamiać n*buffer/sample_rate z pomiarem latencji HeadRush.
- Sprawdzić niezależny Bass/Pad start/stop, nuty, style, skale, tempo, wszystkie racki, seed i porównanie odsłuchowe z oryginalnym VST3.
- Sprawdzić MIDI USB/hotplug, notes, CC Learn, zapis mapowań i przepełnienie bufora.
- Przetestować Safari iPhone 14 i iPad: dotyk, orientację, wszystkie widoczne przyciski, upload paczek i IR, presety.
- Sprawdzić zmianę bufora, odrzucenie wartości przez JACK, kontrolowany restart silnika oraz przywrócenie poprzedniego bufora/grafu/routingu.
- Sprawdzić restart Pi i świadomie skonfigurowany autostart po zatwierdzeniu testów. Sprawdzić rollback po ponownym uruchomieniu i po przerwaniu aktywacji.

Dopiero zapisane wyniki tych prób pozwolą ocenić gotowość produkcyjną.
