# LCD 1602A — plan po naprawie audio

Uzgodniona kolejność: najpierw stabilne audio na Pi, następnie wyświetlacz. Nie wdrażamy teraz obsługi GPIO ani I²C.

Na zdjęciu: moduł 1602A, 16 znaków × 2 wiersze, 16-pinowy interfejs równoległy, bez adaptera I²C. Zgodność kontrolera z HD44780 i kolejność wyprowadzeń trzeba potwierdzić przed podłączeniem.

Proponowane elementy: adapter PCF8574 do LCD1602 z regulacją kontrastu oraz dwukierunkowy konwerter poziomów I²C 3,3 V ↔ 5 V. Typowy adapter zasilany 5 V podciąga SDA/SCL do 5 V, dlatego nie łączymy go bezpośrednio z GPIO Pi.

Plan magistrali: GPIO2/SDA (pin fizyczny 3) i GPIO3/SCL (pin 5) po stronie 3,3 V konwertera; wspólna masa (np. pin 6); strona LCD/adaptera na 5 V. Dokładny schemat dopiero po wyborze adaptera i sprawdzeniu jego napięć/oznaczeń. Adres I²C zostanie wykryty, a nie założony na sztywno.

Ekran: nazwa presetu i aktywny efekt, osobna strona stanu audio/CPU/XRUN/IP. Tekst ograniczony do 16 znaków; polskie znaki przez transliterację lub własne glify. Aktualizacja przez oddzielną usługę, maksymalnie kilka razy na sekundę, bez I²C w callbacku JACK. Awaria lub odłączenie LCD nie może zatrzymać audio.
