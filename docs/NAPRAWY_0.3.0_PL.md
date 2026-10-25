# Jerzy Audio Platform 0.3.0 — wersja testowa

Instalacja: rozpakuj pełny Windows-Installer.zip, uruchom START-INSTALACJA.cmd, podaj adres Pi (w domowej sieci bassambient.local) i potwierdź aktywację. Instalator dodaje usługę sprzętową oraz most Bluetooth MIDI. Instalacja brakującego BlueZ wymaga Internetu na Pi. Ustawienia domowego Wi-Fi pozostają zachowane.

Bass Ambient PRO: przycisk Start JAM włącza źródło JAM i generowanie. Samo włączenie BAS przy wyłączonym autoPlay nie uruchamia sekwencji. Stop JAM zatrzymuje generator. Ochrona CPU jest oddzielona od ręcznego bypassu; przywracanie sesji nie zapisuje automatycznej ochrony jako ręcznego wyłączenia efektu. Koszt modułów jest mierzony czasem CPU wątku audio, niezależnie od opóźnień planisty.

Pełny modalny DSP PRO pozostaje zachowany. Optymalizacje obejmują dokładne buforowanie współczynników, usunięcie powtarzanych obliczeń i aktywne rampy parametrów. Testy porównują wynik z niezmienionym oryginałem. Big Muff zachowuje oryginalny DSP; poprawiona ochrona hosta nie traktuje samego czasu oczekiwania jako przeciążenia CPU. Pełny solver nadal może przekroczyć możliwości Pi przy wielu modułach lub małym buforze.

SYSTEM: rzeczywista konfiguracja JACK — częstotliwość, bufor, liczba okresów; restart audio z odtworzeniem sesji i routingu. Nieudana zmiana przywraca poprzednią konfigurację. Panel pozostaje dostępny również po zatrzymaniu silnika. Zmiana audio na chwilę przerywa dźwięk. Parametry sterownika HeadRush wymagają próby na urządzeniu.

BLUETOOTH / MIDI: wyszukaj Hotone Ampero Control, ustaw w nim transmisję Bluetooth MIDI i zamknij aplikację Hotone, jeśli zajmuje połączenie. Wybierz Połącz MIDI. System sprawdza standardową charakterystykę BLE MIDI; samo sparowanie nie oznacza działającego MIDI. Cztery przypisania obsługują uczenie CC/PC, bypass oraz presety. Bypass działa w silniku JACK. BLE MIDI nie musi wymagać parowania.

Panel na iPhonie: włącz Hotspot osobisty i pozostaw otwarty jego ekran, wybierz telefon w panelu Pi, sparuj z potwierdzeniem kodu, następnie połącz PAN. Otwórz wskazany adres panelu. Pi jest klientem PAN telefonu; nie zmienia domyślnej trasy Wi-Fi. iPad bez funkcji Hotspot osobisty korzysta z Wi-Fi. Safari nie otwiera tego panelu przez sam BLE.

W chmurze można sprawdzić DSP, HTTP, JACK i kontrakt D-Bus BlueZ. Radio Bluetooth, połączenie iPhone PAN i Hotone wymagają testu na rzeczywistym Pi. To wydanie testowe, bez potwierdzenia sprzętowego.

Przywrócenie poprzedniej platformy odtwarza jej usługi i routing. Zainstalowana systemowa usługa sprzętowa pozostaje na Pi; nie przełącza toru audio samoczynnie.
