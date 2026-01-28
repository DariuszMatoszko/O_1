# F001

## Cel
F001 to panel automatyzujący logowanie do portalu i wyszukiwanie numeru GKN dla wybranego powiatu.

## Uruchamianie
- **Cicho (bez okna konsoli):** `RUN_F001.vbs`
- **Z oknem konsoli:** `RUN_F001.bat`

Uruchomienie tworzy nową sesję w `klocki/F001_runtime/sessions/...` i zapisuje ścieżkę do ostatniej sesji w `klocki/F001_runtime/LATEST.txt`.

## Struktura runtime (ignorowana przez Git)
Wszystkie dane runtime znajdują się w `klocki/F001_runtime/`:

```
F001_runtime/
  config/selectors.json
  state/portals.json
  shared/shared_state.json
  state/F001_state.json
  sessions/YYYY-MM-DD/HHMMSS_PORTAL_GKN/
    logs/F001.log
    logs/F001_start.log
    logs/F001_critical.md
    screens/*.png
    dumps/main.html
    dumps/main.txt
    dumps/frame_centr.html
    dumps/frame_centr.txt
    downloads/
    manifest.json
    run.json
  LATEST.txt
  cases/<portal_key_lower>/<SANIT_GKN>/
    main.html
    main.txt
    work_frame.html
    work_frame.txt
    meta.json
    polygon_coords.txt
    polygon_coords.json
    downloads/
```

Jeśli runtime był kiedyś dodany do repozytorium, usuń go jednorazowo z indeksu:

```
git rm --cached -r klocki/F001_runtime
```

## Czyszczenie sesji
Na starcie programu uruchamia się cleanup, który usuwa **sesje starsze niż 14 dni**. Pliki:
`portals.json`, `selectors.json`, `shared_state.json` są zachowane.

## Dane portalu
Jeśli dla wybranego powiatu brakuje danych w `portals.json`, panel wyświetli pola do uzupełnienia (URL, login, hasło) i zapisze je lokalnie.

## Dane pobrane (case)
Po znalezieniu numeru GKN panel zapisuje dane w `klocki/F001_runtime/cases/<portal_key>/<SANIT_GKN>/`.
Ścieżkę do ostatniego case widać w sekcji **Dane pobrane** — z tego panelu możesz od razu otworzyć folder, `meta.json` i `polygon_coords.txt`.

## Debug
Włącz checkbox **DEBUG**, aby zapisywać screenshot po każdym kroku automatyzacji.
