# Stały panel GUI

## Zasady niezmienności
- Panel jest stały i niezmienny: po utworzeniu nie wolno go refaktoryzować ani przebudowywać.
- Numer przycisku jest semantyką pola operatu i **nigdy** się nie zmienia.
- Konfiguracja przycisków w `app/config_buttons.json` jest jedynym źródłem prawdy.
- Wszystkie uruchomienia są domyślnie ciche (silent), bez okien dialogowych.

## Zasady rozwoju
- Dalszy rozwój polega **wyłącznie** na dopinaniu skryptów w katalogu `scripts/`.
- Panel nie zawiera logiki biznesowej, zapisu danych ani generowania dokumentów.
- Panel jedynie emituje zdarzenie kliknięcia poprzez `dispatcher.handle("F0XX")`.
- Dziennik `logs/critical_changes.log` jest niezmienną historią krytycznych zmian w projekcie.

## Uruchomienie
- Uruchom panel poleceniem: `python app/panel.py`.
