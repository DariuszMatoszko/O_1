# F001

## Cel
F001 to panel automatyzujący logowanie do portalu i wyszukiwanie numeru GKN dla wybranego powiatu.

## Uruchamianie
- **Cicho (bez okna konsoli):** `RUN_F001.vbs`
- **Z oknem konsoli:** `RUN_F001.bat`

Uruchomienie tworzy nową sesję w `_runtime/sessions/...` i zapisuje ścieżkę do ostatniej sesji w `_runtime/LATEST.txt`.

## Struktura runtime (ignorowana przez Git)
Wszystkie dane runtime znajdują się w `klocki/F001/_runtime/`:

```
_runtime/
  config/selectors.json
  state/portals.json
  shared/shared_state.json
  sessions/YYYY-MM-DD/HHMMSS_PORTALKEY/
    logs/F001.log
    logs/F001_start.log
    logs/F001_critical.md
    screens/*.png
    run.json
  LATEST.txt
```

## Czyszczenie sesji
Na starcie programu uruchamia się cleanup, który usuwa **sesje starsze niż 14 dni**. Pliki:
`portals.json`, `selectors.json`, `shared_state.json` są zachowane.

## Dane portalu
Jeśli dla wybranego powiatu brakuje danych w `portals.json`, panel wyświetli pola do uzupełnienia (URL, login, hasło) i zapisze je lokalnie.

## Debug
Włącz checkbox **DEBUG**, aby zapisywać screenshot po każdym kroku automatyzacji.
