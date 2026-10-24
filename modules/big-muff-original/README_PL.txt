Jerzy Big Muff — oryginalny DSP — 0.2.0

Wymaga hosta Jerzy Audio Platform >= 0.2.0 i Linux ARM64.

1. Pobierz tę paczkę .jamod i instalator oryginalnych modułów z tego samego wydania.
2. Rozpakuj instalator i uruchom INSTALUJ-MODUL.cmd na Windows.
3. Podaj aktualny adres Pi. W oknie wyboru wskaż tę paczkę.
   Instalator sprawdzi zaufaną SHA256 i raport zgodności. Internet na Pi nie jest potrzebny.
4. W panelu wybierz ŁAŃCUCH → Gitara lub Instrumenty → Dodaj moduł.
5. Parametry są w EFEKCIE. BassAmbient ma dodatkowo ekran INSTRUMENTY.

Przy aktualizacji najpierw usuń instancje tego modułu z grafu.
Poprzednią wersję można przywrócić w BIBLIOTECE. Nie trzeba przebudowywać hosta.
Alternatywa: import .jamod w BIBLIOTECE z SHA256 z oficjalnego wydania.

Identyfikator: big-muff-original
Wzorzec: https://github.com/jurekbak71-dev/JerzyBigMuffCollectionVST3
Commit wzorca: d34128e75a9759c5847f5d93f8adbff9e7cf0549
Zakres testów i dokładna biblioteka: COMPATIBILITY.json.
To porównanie silnika float32, nie pełnego interfejsu/presetów VST ani pomiar XRUN na Pi.
