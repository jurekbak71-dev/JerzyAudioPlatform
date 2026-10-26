# Jerzy Audio Platform 0.4.0 — LV2 FX + Synth

Nasz host JACK2 dla Raspberry Pi z polskim panelem WWW na porcie 8093. Wczytuje efekty i syntezatory **LV2**, zamiast poprzednich wbudowanych modułów. Zachowuje łańcuch audio, mikser, MIDI, Bluetooth i sterowanie JACK.

Twoje wtyczki LV2 pozostają w repozytoriach poszczególnych wtyczek VST. Host odczytuje ich metadane, pokazuje parametry i uruchamia bibliotekę Linux dla odpowiedniej architektury. Nie zawiera własnych syntezatorów ani zamienników efektów.

**[Pobierz instalator Windows 0.4.0](https://github.com/jurekbak71-dev/JerzyAudioPlatform/releases/download/v0.4.0-preview.2/JerzyAudioPlatform-v0.4.0-Windows-Installer.zip)** · [Wydanie testowe LV2](https://github.com/jurekbak71-dev/JerzyAudioPlatform/releases/tag/v0.4.0-preview.2)

[Instrukcja LV2, instalacji i budowania](docs/LV2_PL.md) · [Kontrakt dla repozytoriów wtyczek](docs/LV2_PLUGIN_CONTRACT.md)

Domyślne budowanie wymaga C++20, CMake, JACK2 i Lilv/LV2; nie pobiera JUCE i nie kompiluje poprzednich DSP. Testy sprawdzają wykrywanie LV2, efekt audio, syntezator MIDI, Worker, sesje, presety i import paczek.

Poprzednie źródła DSP pozostają w repozytorium jako archiwum. Nie są oferowane ani pakowane w wersji 0.4.0. Przy pierwszym przejściu na LV2 poprzednia sesja jest zachowywana w kopii, a nowy łańcuch zaczyna się pusty.
