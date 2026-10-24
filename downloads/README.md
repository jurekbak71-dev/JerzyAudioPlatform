# Instalator testowy Windows

Pobierz [ZIP instalatora](https://github.com/jurekbak71-dev/JerzyAudioPlatform/raw/refs/heads/main/downloads/JerzyAudioPlatform-v0.1.0-Windows-Installer.zip), rozpakuj cały ZIP i kliknij START-INSTALACJA.cmd.

Podaj IP Raspberry Pi i hasło użytkownika jerzy. Najpierw instalator sprawdzi pliki i zależności. Aktywacja wymaga wpisania TAK; po sukcesie otworzy panel. Przywracanie: PRZYWROC-MULTIFX.cmd.

Paczka zawiera rzeczywiste binaria ARM64 zbudowane lokalnie w chmurze i pięć modułów; nie jest artefaktem GitHub Actions. Kod paczki odpowiada commitowi d93fc38. Brak fizycznych testów Windows/Pi/HeadRush/Safari. Używaj osobnej kopii karty. Zależności JACK muszą być wcześniej dostępne; Pi nie potrzebuje internetu podczas instalacji.
