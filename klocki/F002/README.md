# F002

F002 to panel, który odczytuje poligon z case F001 i wyznacza gminy oraz obręby przez ULDK.

## Uruchomienie
- Windows (bez konsoli): `RUN_F002.vbs`
- Windows (z konsolą): `RUN_F002.bat`
- Inne systemy: `python F002_panel.py`

## Dane wejściowe
- Domyślnie wybierany jest aktywny case z `klocki/F001_runtime/shared_state.json` (lub legacy `shared/shared_state.json`).
- Gdy brak aktywnego case, lista jest ładowana z `klocki/F001_runtime/index_cases.json`.
- Poligon:
  - Preferowany `GK_*_poligon.txt` (linie: `X Y`).
  - W przeciwnym razie `polygon_coords.txt`.

## Wyniki
Wyniki zapisywane są do folderu case:
- `f002_admin_units.json`
- `f002_admin_units.csv`
- `f002_summary.md`

Manifest case jest aktualizowany o sekcję `f002`.

## Runtime
Logi F002 trafiają do `klocki/F002_runtime/logs/F002.log`.
