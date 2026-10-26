# Archiwalne testy formatu JAMOD

Testy paczek JAMOD i poprzedni `tests/integration.py` dotyczą formatu zastąpionego przez LV2 w wersji 0.4.0. Źródła i testy starych DSP zachowano do odtworzenia wcześniejszych wydań; nie są częścią instalatora LV2. Aby uruchomić testy archiwalne, zbuduj osobny katalog z `-DJERZY_BUILD_LEGACY=ON -DJERZY_BUILD_ORIGINALS=ON`, ustaw `JERZY_TEST_BUILD` na ten katalog i wykonaj `python3 -m unittest discover -s tests/legacy`.

Bieżący host weryfikują `lv2-tests`, `tests/lv2_integration.py` i testy `test_lv2_*.py`.
