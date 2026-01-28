# F001 FREEZE RUNBOOK (FROZEN)

## A) Co robi F001
F001 to stabilny panel automatyzujący logowanie do geoportal2 i wyszukiwanie numeru GKN w wybranym powiecie. Po uruchomieniu loguje się na portal, przechodzi komunikaty OK, dochodzi do widoku pracy i eksportuje dane dla podanego numeru. Wynikiem działania są logi kroków, zrzuty ekranu (gdy DEBUG jest włączony) oraz pliki HTML/TXT z widoku pracy i metadanymi. Panel pokazuje status ostatniego kroku oraz zapisuje ścieżkę do ostatniego case z danymi.

## B) Jak uruchomić (krok po kroku dla laika)
1. **Uruchom panel F001**:
   - Windows: `RUN_F001.vbs` (bez konsoli) lub `RUN_F001.bat` (z konsolą). Pliki znajdują się w `klocki/F001/`.【F:klocki/F001/README.md†L7-L12】
   - Po uruchomieniu widzisz okno z tytułem **F001**.
2. **Wybierz powiat**:
   - W sekcji **Wybór powiatu** kliknij przycisk powiatu (np. „Powiat sokólski” lub „Powiat augustowski”).【F:klocki/F001/F001_panel.py†L50-L71】
3. **Uzupełnij dane portalu (jeśli trzeba)**:
   - Jeśli panel pokaże „Podaj URL, login i hasło.” – wpisz dane w sekcji **Dane portalu** i kliknij **Zapisz**. Panel zapisze je lokalnie w runtime i nie wymaga ponownego wpisywania przy kolejnych uruchomieniach.【F:klocki/F001/F001_panel.py†L82-L138】
4. **Wpisz numer GKN**:
   - W sekcji **Numer GKN** wpisz numer w polu tekstowym i kliknij **START**.【F:klocki/F001/F001_panel.py†L99-L112】
5. **Opcja DEBUG**:
   - Checkbox **DEBUG (screenshot po każdym kroku)** powoduje zapis zrzutu ekranu po każdym kroku automatyzacji (do folderu sesji).【F:klocki/F001/F001_panel.py†L105-L112】
6. **Gdzie zobaczyć wynik**:
   - Sekcja **Status** pokazuje „Ostatni krok”, „Komunikat” i „Wynik”. Jeśli jest screenshot, przycisk **Otwórz screenshot** otwiera plik. 【F:klocki/F001/F001_panel.py†L114-L146】【F:klocki/F001/F001_panel.py†L286-L306】
   - Sekcja **Dane pobrane** pokazuje folder case (GKN) i daje szybkie przyciski do `meta.json` i `polygon_coords.txt`.【F:klocki/F001/F001_panel.py†L167-L192】【F:klocki/F001/F001_panel.py†L317-L339】

## C) Struktura folderów i plików
### Kluczowe pliki kodu F001
- `klocki/F001/F001_panel.py` – główny panel GUI (wybór powiatu, wpis numeru, start, status).【F:klocki/F001/F001_panel.py†L1-L355】
- `klocki/F001/automation/portal_runner.py` – logika automatyzacji Playwright (kroki STEP, eksporty, obsługa błędów).【F:klocki/F001/automation/portal_runner.py†L1-L1148】
- `klocki/F001/runtime_utils.py` – katalogi runtime, pliki stanu i sesji (tworzenie sesji, run.json, manifest).【F:klocki/F001/runtime_utils.py†L1-L151】
- `klocki/F001/F001_app.py` – tryb CLI (uruchomienie bez GUI, zapis logu).【F:klocki/F001/F001_app.py†L1-L83】
- `klocki/F001/README.md` – opis uruchamiania i runtime (warto mieć pod ręką).【F:klocki/F001/README.md†L1-L55】

### Runtime F001 (sesje, screeny, logi, eksporty)
Runtime jest w `klocki/F001_runtime/`. Zawiera konfigurację, stan, sesje i dane case. Struktura (minimum):
- `klocki/F001_runtime/config/selectors.json` – selektory (login, hasło, submit, itp.).【F:klocki/F001/runtime_utils.py†L33-L75】
- `klocki/F001_runtime/state/portals.json` – dane portalu per powiat (URL/login/hasło).【F:klocki/F001/runtime_utils.py†L37-L78】
- `klocki/F001_runtime/state/F001_state.json` – stan panelu (np. ostatni folder case).【F:klocki/F001/runtime_utils.py†L41-L84】【F:klocki/F001/F001_panel.py†L68-L76】【F:klocki/F001/F001_panel.py†L335-L340】
- `klocki/F001_runtime/shared/shared_state.json` – wspólny stan (obecnie pusty, ale utrzymywany).【F:klocki/F001/runtime_utils.py†L39-L80】
- `klocki/F001_runtime/sessions/YYYY-MM-DD/HHMMSS_PORTAL_GKN/` – jedna sesja uruchomienia:
  - `logs/F001.log` – log kroków.
  - `logs/F001_start.log` – log startu sesji.
  - `logs/F001_critical.md` – krytyczne błędy.
  - `screens/*.png` – screeny (gdy DEBUG lub błędy).
  - `exports/main.html`, `exports/main.txt`, `exports/frame_centr.html`, `exports/frame_centr.txt` – eksporty widoku pracy i frame’a po otwarciu numeru.【F:klocki/F001/automation/portal_runner.py†L564-L639】
  - `dumps/main.html`, `dumps/main.txt`, `dumps/frame_centr.html`, `dumps/frame_centr.txt` – kopie HTML/TXT do dalszego przetwarzania (case).【F:klocki/F001/automation/portal_runner.py†L647-L718】
  - `downloads/` – pobrane pliki z portalu (np. ZIP z poligonem).【F:klocki/F001/automation/portal_runner.py†L748-L776】
  - `manifest.json` – status i lista plików wyjściowych.
  - `run.json` – stan uruchomienia (portal, numer, last_step).【F:klocki/F001/runtime_utils.py†L69-L133】
- `klocki/F001_runtime/cases/<portal_key>/<SANIT_GKN>/` – dane case (wynik):
  - `main.html`, `main.txt` – zrzut widoku głównego.
  - `work_frame.html`, `work_frame.txt` – zrzut ramki z danymi pracy.
  - `meta.json` – kluczowe pola z tabelki w portalu.
  - `polygon_coords.txt`, `polygon_coords.json` – współrzędne.
  - `downloads/` – pobrane pliki (np. ZIP).【F:klocki/F001/automation/portal_runner.py†L647-L799】
- `klocki/F001_runtime/LATEST.txt` – ścieżka do ostatniej sesji.【F:klocki/F001/runtime_utils.py†L31-L111】

#### Mini-drzewko (tree)
```
klocki/
  F001/
    F001_panel.py
    F001_app.py
    automation/
      portal_runner.py
    runtime_utils.py
  F001_runtime/
    config/selectors.json
    state/portals.json
    state/F001_state.json
    shared/shared_state.json
    sessions/YYYY-MM-DD/HHMMSS_PORTAL_GKN/
      logs/
      screens/
      exports/
      dumps/
      downloads/
      run.json
      manifest.json
    cases/<portal_key>/<SANIT_GKN>/
      main.html
      main.txt
      work_frame.html
      work_frame.txt
      meta.json
      polygon_coords.txt
      polygon_coords.json
      downloads/
    LATEST.txt
```

## D) Stan i kontrakt danych dla innych klocków
### Pliki stanu
- `klocki/F001_runtime/state/portals.json` – dane portalu per powiat (URL/login/hasło).【F:klocki/F001/runtime_utils.py†L37-L78】
- `klocki/F001_runtime/state/F001_state.json` – stan panelu (np. `last_case_dir`, `last_case_files`).【F:klocki/F001/F001_panel.py†L68-L76】【F:klocki/F001/F001_panel.py†L335-L340】
- `klocki/F001_runtime/sessions/.../run.json` – stan uruchomienia sesji.【F:klocki/F001/runtime_utils.py†L69-L133】
- `klocki/F001_runtime/sessions/.../manifest.json` – status i lista plików sesji (po postprocess).【F:klocki/F001/runtime_utils.py†L94-L133】【F:klocki/F001/automation/portal_runner.py†L788-L825】

### Pola w `run.json`
- `portal_key` – klucz powiatu wybrany w panelu.
- `gkn` – numer GKN (raw) użyty do nazwy sesji.
- `last_number` – numer GKN wpisany w polu.
- `last_status` – status ostatniego przebiegu (`success`, `failed`, `password_error`).
- `last_step` – ostatni krok automatyzacji (np. `STEP_07_NUMBER_FOUND`).
- `session_started_at`, `run_count` – metadane sesji.
- Plik jest tworzony przy starcie sesji i aktualizowany po uruchomieniu flow.【F:klocki/F001/runtime_utils.py†L69-L151】【F:klocki/F001/F001_panel.py†L248-L276】

### Gdzie F002 ma szukać eksportów
- Eksporty „widoku pracy” w sesji: `klocki/F001_runtime/sessions/.../exports/main.html`, `main.txt`, `frame_centr.html`, `frame_centr.txt`.【F:klocki/F001/automation/portal_runner.py†L564-L639】
- Dla danych docelowych per numer GKN: `klocki/F001_runtime/cases/<portal_key>/<SANIT_GKN>/`:
  - `main.html`, `main.txt`, `work_frame.html`, `work_frame.txt`.
  - `meta.json`, `polygon_coords.txt`, `polygon_coords.json`.
  - `downloads/` (np. ZIP).【F:klocki/F001/automation/portal_runner.py†L647-L799】
- Dodatkowo w sesji: `dumps/` zawiera kopię HTML/TXT używaną do tworzenia case (przydatne do debugu).【F:klocki/F001/automation/portal_runner.py†L647-L718】

## E) Logi i błędy
### Gdzie są logi
- `logs/F001_start.log` – zapis startu sesji (data/czas).【F:klocki/F001/runtime_utils.py†L103-L111】
- `logs/F001.log` – log kroków automatyzacji (STEP_XX_*).【F:klocki/F001/runtime_utils.py†L120-L133】
- `logs/F001_critical.md` – krytyczne błędy (wypisane punktami).【F:klocki/F001/runtime_utils.py†L120-L133】

### Format kroków (STEP_XX_...)
- Logika zapisuje kroki w formacie `STEP_XX_OPIS`, np.:
  - `STEP_01_OPEN_URL` – otwarcie portalu.
  - `STEP_02_LOGIN_FILL` – wypełnienie formularza logowania.
  - `STEP_03_LOGIN_SUBMIT` – wysłanie formularza.
  - `STEP_04_CLICK_OK_LOOP` – klikanie komunikatów OK.
  - `STEP_05_NAV_ROBOTY_NIEZAKONCZONE` / `STEP_06_NAV_ROBOTY_ZAKONCZONE` – nawigacja list prac.
  - `STEP_07_NUMBER_FOUND` / `STEP_07_NUMBER_NOT_FOUND` – wynik wyszukiwania numeru.
  - `STEP_08_EXPORT_WORK` – eksport HTML/TXT i screenshot po otwarciu pracy.
  - `STEP_98_ERROR` / `STEP_99_TIMEOUT` – wyjątki ogólne lub timeout Playwright. 【F:klocki/F001/automation/portal_runner.py†L881-L1145】

### Interpretacja typowych błędów
- `STEP_02_LOGIN_INPUTS_NOT_FOUND` – nie wykryto pól loginu/hasła (sprawdź selektory lub stronę logowania).【F:klocki/F001/automation/portal_runner.py†L452-L481】【F:klocki/F001/automation/portal_runner.py†L924-L928】
- `STEP_02_*_MISSING_SELECTOR` – brak selektora w `selectors.json` dla wymaganego kroku (np. login/hasło).【F:klocki/F001/automation/portal_runner.py†L484-L510】
- `STEP_07_NUMBER_NOT_FOUND` – numer GKN nie został znaleziony w listach prac (sprawdź numer lub zakres list).【F:klocki/F001/automation/portal_runner.py†L1067-L1085】
- `password_error` (status) – wykryto błędne hasło; panel prosi o ponowne wpisanie i „Zapisz i ponów”.【F:klocki/F001/automation/portal_runner.py†L990-L1003】【F:klocki/F001/F001_panel.py†L293-L314】
- **DEBUG**: jeśli włączony, zapisuje zrzut po każdym kroku, co ułatwia diagnozę.【F:klocki/F001/F001_panel.py†L105-L112】【F:klocki/F001/automation/portal_runner.py†L881-L1010】

## F) Czyszczenie i brak konfliktów w GitHub Desktop
- **Bezpieczne do kasowania**: całe `klocki/F001_runtime/` (sesje, screeny, logi, downloads, exports, dumps). To dane runtime i nie są częścią kodu. 【F:klocki/F001/runtime_utils.py†L26-L47】【F:klocki/F001/README.md†L14-L43】
- **Nie commituj**: `__pycache__/`, `*.pyc`, oraz całe `klocki/F001_runtime/` (runtime, logi, screeny, exports, dumps, downloads). Repo ma to ignorować w `.gitignore`.
- **Zasada**: do gita trafia tylko kod i dokumenty (np. ten runbook), a nie dane sesji.

## G) ZAMROŻENIE
**F001 jest FROZEN.** Nie zmieniamy logiki, selektorów ani kroków automatyzacji. Jeśli kiedykolwiek trzeba wprowadzić zmiany w logice F001, robimy nową wersję/branch (np. `F001_v2`) zamiast ingerować w stabilną wersję.
