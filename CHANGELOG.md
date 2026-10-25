# 0.3.1-preview.1

Ochrona pokazuje przyczynę, średnie i szczytowe CPU oraz budżet bloku. Odświeżanie panelu uwzględnia nowe pomiary przy aktywnej ochronie. DSP i progi ochrony bez zmian względem 0.3.0. Wydajność fizycznego Pi niepotwierdzona; to poprawka diagnostyczna.

# 0.3.0-preview.2

Jawny transport JAM dla PRO; dokładne optymalizacje DSP; rozdzielenie ochrony CPU i ręcznego bypassu. Transakcyjna konfiguracja JACK i dostępny panel przy niedziałającym silniku. Usługa BlueZ, BLE MIDI → JACK, cztery mapowania CC/PC i klient PAN dla Hotspotu iPhone. Szczegóły i ograniczenia: docs/NAPRAWY_0.3.0_PL.md.

## 0.2.1 — naprawy po odsłuchu na Pi

Żywa zmiana bufora, odzyskiwanie audio z panelu, ochrona przed przeciążeniem modułu, poprawiony wybór modeli Muff, widoczny CAB/IR z dodatkowymi kontrolkami, PRO z modalnym DSP i uporządkowany studyjny GUI. Oficjalne starsze moduły są aktualizowane po zatrzymaniu hosta, z kopią do rollbacku. Szczegóły i zakres: docs/NAPRAWY_0.2.1_PL.md.

## Poprawka Wi-Fi po 0.2.0-preview.1

Oczekiwanie do 60 sekund na IPv4 po aktywacji NetworkManager (IPv6 może być gotowe wcześniej). Naprawia przedwczesne przywracanie hotspotu podczas DHCP/ACD. Dodano test opóźnionego DHCP i jego timeoutu. Mała paczka: downloads/Jerzy-WiFi-Domowe-Poprawka.zip.

# Zmiany

## 0.2.0 — pełne oryginalne DSP i domowe Wi-Fi

Siedem niezależnych modułów original z raportami porównań, zaufany katalog i instalator modułów offline, narzędzie Wi-Fi z potwierdzeniem i rollbackiem oraz checkpointy aktualizacji hosta. Szczegóły w docs/ORYGINALNE_DSP_0.2.md.

# Zmiany

## 0.1.0 — rozwojowa, 24 października 2026

- Osobny host JACK i wersjonowany SDK C ABI 1.
- Pięć oddzielnie kompilowanych modułów, dwa tory, mikser i MIDI CC Learn.
- Oryginalny rdzeń BassAmbient, bez JUCE i VST na Pi.
- Polski panel WWW, presety, lokalna biblioteka z kontrolą paczek.
- Narzędzia budowania i pakowania, staging offline, skrypty aktywacji i rollbacku.
- Testy natywne i ARM64/QEMU oraz testy integracyjne JACK i przeglądarki.
- Brak zatwierdzenia stabilnego wydania sprzętowego; lista braków w docs/OGRANICZENIA.md.
