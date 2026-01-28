# Changelog

## 2026-02-01
- PATCH: multi-OK (1..N komunikatów), nawigacja do listy niezakończonych bez selektorów, wyszukiwanie po Zgłoszenie, eksport work.txt/html.

## 2026-02-02
- PATCH: dismiss_ok_dialogs (jQuery UI + polling), nawigacja list po submit, szukanie i eksport w iframe frame_centr.

## 2026-01-31
- PATCH: pewne logowanie (walidacja wpisania hasła) + auto-OK bez ok_button.

## 2026-01-28
- Przeniesiono pliki runtime do `klocki/F001/_runtime/` i dodano obsługę sesji z rotacją 14 dni.
- Dodano panel `F001_panel.py` z wyborem powiatu, danymi portalu i obsługą błędów ze screenshotem.
- Zaktualizowano runner Playwright o kroki automatyzacji, logi sesji oraz brakujące selektory.
- Dodano skrypty pomocnicze w `tools/` oraz `.gitignore` dla danych runtime.
- Jak testować: uruchom `RUN_F001.bat` lub `RUN_F001.vbs`, wybierz powiat, wpisz numer GKN i kliknij START.

## 2026-01-29
- Naprawa: logowanie działa bez selectors.json (auto wykrywanie Użytkownik/Hasło/Zaloguj).
- Powód: STEP_02_MISSING_SELECTOR.

## 2026-01-30
- PATCH: logowanie skanuje iframe + szuka po tekstach Użytkownik/Hasło/Zaloguj, dodano login_probe.json (bez haseł).
- Naprawa kroku: STEP_02_LOGIN_INPUTS_NOT_FOUND.
