# Changelog

## 2026-01-28
- Przeniesiono pliki runtime do `klocki/F001/_runtime/` i dodano obsługę sesji z rotacją 14 dni.
- Dodano panel `F001_panel.py` z wyborem powiatu, danymi portalu i obsługą błędów ze screenshotem.
- Zaktualizowano runner Playwright o kroki automatyzacji, logi sesji oraz brakujące selektory.
- Dodano skrypty pomocnicze w `tools/` oraz `.gitignore` dla danych runtime.
- Jak testować: uruchom `RUN_F001.bat` lub `RUN_F001.vbs`, wybierz powiat, wpisz numer GKN i kliknij START.

## 2026-01-29
- Naprawa: logowanie działa bez selectors.json (auto wykrywanie Użytkownik/Hasło/Zaloguj).
- Powód: STEP_02_MISSING_SELECTOR.
