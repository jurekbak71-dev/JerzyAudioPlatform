# Audyt źródeł i architektury

Sprawdzono:

- JerzyRPiAudioLab, HEAD `e210a367d74a99ce7d9d1592f9f5ce97cf134e12`.
- Jego przypięty submoduł JerzyMemoryDelay, `38651e0f12c9410f23822ce40e1b65b001ee4c9d`, obejmujący MultiFX v0.4.
- JerzyBassAmbientVST3, `c050475ecb9095bc1bc65e6719f1367235a14b61`.

Dostęp Git HTTPS działał. API GitHub zwróciło Forbidden przy odczycie użytkownika; brak potwierdzonego uprawnienia do utworzenia repozytorium i publikacji. Nie zmieniono plików śledzonych ani lockfile projektów referencyjnych. Zainicjalizowano przypięty submoduł; nie przesunięto jego wskaźnika na nowszą gałąź.

W źródłach nie znaleziono deklaracji licencji. Użytkownik potwierdził 24.10.2026 posiadanie praw i zgodę na użycie i dystrybucję własnego DSP. To nie jest udzielenie praw do kodu osób trzecich. Nie przeniesiono JUCE ani cudzych bibliotek źródłowych. JACK jest zewnętrzną zależnością systemową; paczka nie zawiera jego kopii binarnej.

## BassAmbient

`modules/bass-ambient/OriginalCore.h` pochodzi bez zmian z `Source/Core.h` oryginalnego instrumentu. Zachowano modele basu, sekwencer, skale, akordy, obwiednie, głosy pad, Flow/Krell, seed, FX oraz trzy oddzielne racki. `Parameters.def` i `FXParameters.def` posłużyły do wygenerowania wszystkich parametrów, w tym kolejności FX. Warstwa VST obejmuje również sterowanie/smoothing; port realizuje 20 ms wygładzania jak oryginalny procesor, natywne MIDI i własny zegar. GUI VST nie zostało skopiowane. Test porównuje oryginalny rdzeń i moduł na identycznych parametrach float, seedzie, nucie i zegarze przy 44,1/48 kHz, uwzględniając jawną rampę bezpieczeństwa wyjścia 20 ms. Nie jest to pełny test wszystkich możliwych presetów ani porównanie odsłuchowe całego VST3.

Wyłączenie obu warstw pomija syntezę i natychmiast czyści aktywne nuty; wyjście modułu wygasza własna rampa 20 ms. W tej wersji zatrzymanie obu warstw odcina też ogony FX. Start/Stop pojedynczej warstwy zachowuje logikę oryginalnego rdzenia.

## Efekty

Stary MuffDSP opisuje się jako przybliżenie brzmień: zawiera dwa clippingi tanh i sieć tone. Nie uznano go za pomiarową emulację fizycznego Big Muff. Nowy moduł jest oddzielną implementacją z filtracją sprzęgającą, wzmocnieniem, dwoma przybliżonymi stopniami diodowymi i równoległym tone. Nie deklarujemy zgodności z konkretną kostką. Brakuje oversamplingu i analizy aliasingu wymaganej do odbioru jakościowego.

Stary Tape Drive ma wiele bloków i własną kompensację poziomu. Zamiast kopiować cały blok zależności przygotowano mały oddzielny procesor z saturacją zależną od poziomu, ograniczeniem pasma, pamięcią i usuwaniem DC. To model charakteru saturacji, nie fizyczna emulacja magnetyzacji taśmy ani zamiennik wszystkich opcji starej wtyczki.

Splot CAB/IR przeniesiono z własnego `multifx4/ir_cab.h` jako osobny moduł. WAV ładowany i resamplowany jest przed audio, a callback wykonuje przygotowany splot. Latencja 64 próbek jest raportowana. Nie dostarczono komercyjnych ani zmyślonych pomiarów kolumn.

## Host i real-time

Host napisano osobno; nie zawiera algorytmów wymienionych efektów ani instrumentu. Dwa tory mają liniowe łańcuchy, więc GUI nie może utworzyć pętli sprzężenia. Graf przygotowywany jest poza callbackiem i podmieniany po rampie wyciszenia; wcześniejsze obiekty zwalnia kontroler. Mutacje i odczyty grafu są sekwencjonowane atomikami; callback nie używa shared_ptr kopiowanych ani niszczonych w locie, mutexów ani operacji plikowych.

Bufory są alokowane wcześniej. Maksymalny wspierany blok to 8192 próbek; większy blok powoduje ciszę, nie zapis poza buforem. MIDI ma pojemność 256 zdarzeń na blok i licznik przepełnienia. To jawne ograniczenia implementacji, nie deklaracja limitu CPU/RAM Pi.

Nie ma jeszcze pełnego audytu worst-case czasu DSP, testu TSan grafu, formalnego dowodu lock-free wszystkich użytych atomików na wszystkich platformach ani wielogodzinnego wyniku ze sprzętu. Dynamiczne moduły wymagają zaufania do ich autora.

Metadane paczek modułów odczytują rzeczywiste wymagania GLIBC/GLIBCXX i DT_NEEDED za pomocą readelf; architektura wynika z nagłówka ELF. Nie przypisuje się zgodności z Bookworm dowolnemu binarium ARM64 tylko na podstawie jego nazwy.

Aktualizacja publikacji: dostęp do API GitHub został przywrócony. Przygotowano wydanie testowe oraz skróty CMD do aktywacji, panelu, diagnostyki i rollbacku. Wynik publikacji należy sprawdzić na stronie repozytorium.
