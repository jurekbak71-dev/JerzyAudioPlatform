# Walidacja 0.3.0

W chmurze wykonano 43 testy Python: rollback konfiguracji JACK, aktywacja/autostart, paczki modułów, Wi-Fi, parser BLE MIDI, prywatny prawdziwy D-Bus z symulowaną usługą BlueZ (skan, jawne potwierdzenie parowania, niebondowany MIDI GATT, PAN z własnym profilem), jawny Start JAM oraz stan panelu przy niedziałającym silniku.

Natywne 10 testów CTest przeszło. PRO modal: 198400 próbek, maksymalna różnica float32 względem niezmienionego oryginału 0 w sprawdzanych scenariuszach. Testy nie obejmują każdego możliwego presetu ani gwarancji czasu asynchronicznych zasobów FX.

Integracja z rzeczywistym JACK dummy: audio, bypass, CC learn, nowy most MIDI datagram → JACK → host, CC z detekcją zbocza, PC, ochrona rzeczywistego kosztu CPU i łącznego obciążenia, brak fałszywego wyłączenia tylko z powodu sleep, presety, restart silnika i odtworzenie sesji, THRU, dostępność HTTP po zatrzymaniu silnika. Chromium desktop i 390×844: MX, PRO, instrumenty, mikser, presety, biblioteka, SYSTEM i Bluetooth; bez błędów JavaScript i przewijania poziomego.

ARM64 jest również budowany i porównywany z oryginałami. Wyniki przypisane do konkretnych bibliotek znajdują się w compatibility/*.json paczki. CI przed publikacją wykonuje testy natywnie na ARM64 oraz parser PowerShell na Windows.

Nie przeprowadzono testów radiowych Hotone Ampero Control, Apple PAN ani sterownika HeadRush na fizycznym Pi. Wynik dummy/QEMU nie potwierdza wydajności lub stabilności urządzenia użytkownika.
