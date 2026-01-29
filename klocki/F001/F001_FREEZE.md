# F001 — Freeze

## Uruchamianie
- `RUN_F001.bat` (z konsolą)
- `RUN_F001.vbs` (cicho, bez konsoli)

## Dane wejściowe
- Portal (powiat) wybierany w panelu.
- Numer GK/GKN wpisywany w polu „Numer GKN”.

## Dane/efekty (gdzie się zapisują)
- **state:** `klocki/F001_runtime/state/F001_state.json`
- **shared:** `klocki/F001_runtime/shared/shared_state.json`
- **logi sesji:** `klocki/F001_runtime/sessions/.../logs/`
- **screenshoty:** `klocki/F001_runtime/sessions/.../screens/`
- **export:** jeśli generowany przez proces — w `klocki/F001_runtime/export/` lub `klocki/F001_runtime/exports/`

## Debugowanie
- Logi: `klocki/F001_runtime/sessions/.../logs/F001.log`
- Screeny: `klocki/F001_runtime/sessions/.../screens/*.png`
