from __future__ import annotations

import importlib.util
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from runtime_utils import load_json, portals_path


@dataclass
class PortalRunResult:
    status: str
    last_step: str
    message: str
    detail: str
    found: bool
    screenshot_path: Optional[str] = None


def _log_event(log_path: str, message: str) -> None:
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"{message}\n")


def _log_critical(critical_path: str, message: str) -> None:
    os.makedirs(os.path.dirname(critical_path), exist_ok=True)
    with open(critical_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"- {message}\n")


def _take_screenshot(page: Any, screens_dir: str, step: str) -> Optional[str]:
    if page is None:
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{step}.png"
    os.makedirs(screens_dir, exist_ok=True)
    screenshot_path = os.path.join(screens_dir, filename)
    try:
        page.screenshot(path=screenshot_path, full_page=True)
        return screenshot_path
    except Exception:
        return None


def _load_portal_key(session_info: dict[str, str]) -> Optional[str]:
    run_path = session_info.get("run_path")
    if not run_path or not os.path.exists(run_path):
        return None
    try:
        with open(run_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data.get("portal_key")
    except Exception:
        return None


def _resolve_portal_data(portal_data: dict[str, Any], portal_key: Optional[str]) -> dict[str, Any]:
    if not portal_data:
        return {}
    if any(key in portal_data for key in ("url", "login", "password")):
        return portal_data
    if not portal_key:
        return {}
    candidates = [portal_key, portal_key.upper(), portal_key.lower()]
    for candidate in candidates:
        value = portal_data.get(candidate)
        if isinstance(value, dict):
            return value
    lowered = portal_key.lower()
    for key, value in portal_data.items():
        if isinstance(key, str) and key.lower() == lowered and isinstance(value, dict):
            return value
    return {}


def _first_visible(locator: Any) -> Any:
    try:
        count = locator.count()
    except Exception:
        return None
    for index in range(count):
        item = locator.nth(index)
        try:
            if item.is_visible():
                return item
        except Exception:
            continue
    return None


def _locator_from_selector(page: Any, selector: Optional[str]) -> Any:
    if not selector:
        return None
    return _first_visible(page.locator(selector))


def _auto_detect_username(page: Any) -> Any:
    for label in ("Użytkownik", "Uzytkownik"):
        locator = _first_visible(page.get_by_label(label, exact=False))
        if locator:
            return locator
    for label in ("Użytkownik", "Uzytkownik"):
        locator = _first_visible(
            page.locator(
                "xpath=//*[contains(normalize-space(.),"
                f" '{label}')]/following::input[not(@type='hidden')"
                " and not(@disabled)][1]"
            )
        )
        if locator:
            return locator
    return _first_visible(
        page.locator(
            "input:not([type='hidden']):not([type='password']):not([disabled])"
        )
    )


def _auto_detect_password(page: Any) -> Any:
    locator = _first_visible(page.locator("input[type='password']"))
    if locator:
        return locator
    for label in ("Hasło", "Haslo"):
        locator = _first_visible(
            page.locator(
                "xpath=//*[contains(normalize-space(.),"
                f" '{label}')]/following::input[not(@type='hidden')"
                " and not(@disabled)][1]"
            )
        )
        if locator:
            return locator
    return None


def _auto_detect_submit(page: Any) -> Any:
    locator = _first_visible(
        page.get_by_role("button", name=re.compile("Zaloguj|Loguj", re.I))
    )
    if locator:
        return locator
    return _first_visible(page.get_by_text("Zaloguj", exact=False))


def _locator_frame(locator: Any, fallback: Any) -> Any:
    if not locator:
        return fallback
    try:
        handle = locator.element_handle()
    except Exception:
        return fallback
    if not handle:
        return fallback
    try:
        return handle.owner_frame() or fallback
    except Exception:
        return fallback


def _same_element(first: Any, second: Any) -> bool:
    if not first or not second:
        return False
    try:
        first_handle = first.element_handle()
        second_handle = second.element_handle()
    except Exception:
        return False
    if not first_handle or not second_handle:
        return False
    try:
        return first_handle.evaluate("(el, other) => el === other", second_handle)
    except Exception:
        return False


def _visible_input_from_label(frame: Any, label: str) -> Any:
    return _first_visible(
        frame.locator(
            "xpath=//*[contains(normalize-space(),"
            f" '{label}')]/following::input[not(@type='hidden') and not(@disabled)][1]"
        )
    )


def find_login_in_any_frame(page: Any) -> Optional[tuple[Any, Any, Any, Any]]:
    frames = [page.main_frame]
    frames.extend(frame for frame in page.frames if frame != page.main_frame)
    for _ in range(30):
        for frame in frames:
            try:
                has_login_text = frame.locator("text=Użytkownik").count() > 0
                has_password = frame.locator("input[type='password']").count() > 0
            except Exception:
                continue
            if not (has_login_text or has_password):
                continue

            user_locator = _visible_input_from_label(frame, "Użytkownik")
            if not user_locator:
                user_locator = _visible_input_from_label(frame, "Uzytkownik")
            if not user_locator:
                user_locator = _first_visible(
                    frame.locator(
                        "input:not([type='hidden']):not([type='password']):not([type='submit']):not([type='button']):not([disabled])"
                    )
                )

            pass_locator = _first_visible(frame.locator("input[type='password']"))
            if not pass_locator:
                pass_locator = _visible_input_from_label(frame, "Hasło")
            if not pass_locator:
                pass_locator = _visible_input_from_label(frame, "Haslo")
            if not pass_locator:
                pass_locator = None

            submit_locator = _first_visible(frame.locator("button:has-text('Zaloguj')"))
            if not submit_locator:
                submit_locator = _first_visible(
                    frame.locator("input[type='submit'][value*='Zaloguj']")
                )
            if not submit_locator:
                submit_locator = _first_visible(
                    frame.locator("input[type='button'][value*='Zaloguj']")
                )

            if user_locator and pass_locator and not _same_element(user_locator, pass_locator):
                return frame, user_locator, pass_locator, submit_locator
        time.sleep(0.5)
    return None


def _login_form_visible(frame: Any) -> bool:
    if not frame:
        return False
    try:
        user_label = _first_visible(frame.locator("text=Użytkownik"))
        pass_label = _first_visible(frame.locator("text=Hasło"))
        submit = _first_visible(frame.get_by_role("button", name=re.compile("Zaloguj", re.I)))
        if not submit:
            submit = _first_visible(frame.locator("button:has-text('Zaloguj')"))
        return bool(user_label and pass_label and submit)
    except Exception:
        return False


def _click_okish_things(page: Any, log_path: str) -> None:
    okish_regex = re.compile(
        r"\b(OK|Dalej|Kontynuuj|Akceptuj|Zgadzam|Rozumiem|Zamknij)\b",
        re.I,
    )
    click_limit = 5
    clicked_total = 0
    frames = [page.main_frame]
    frames.extend(frame for frame in page.frames if frame != page.main_frame)
    for _ in range(click_limit):
        if clicked_total >= click_limit:
            break
        clicked_any = False
        for frame in frames:
            try:
                locator = frame.locator(
                    "button, [role='button'], input[type='button'], input[type='submit'], a"
                )
                count = locator.count()
            except Exception:
                continue
            for idx in range(count):
                if clicked_total >= click_limit:
                    break
                item = locator.nth(idx)
                try:
                    if not item.is_visible():
                        continue
                    text = (item.text_content() or "").strip()
                    value_text = (item.get_attribute("value") or "").strip()
                except Exception:
                    continue
                if not okish_regex.search(text) and not okish_regex.search(value_text):
                    continue
                try:
                    item.click()
                except Exception:
                    continue
                clicked_any = True
                clicked_total += 1
                _log_event(log_path, f"STEP_04_CLICK_OK_LOOP: Clicked okish ({text or value_text}).")
                try:
                    page.wait_for_timeout(800)
                except Exception:
                    pass
        if not clicked_any:
            break


def _write_login_probe(log_path: str, page: Any) -> None:
    logs_dir = os.path.dirname(log_path)
    os.makedirs(logs_dir, exist_ok=True)
    probe_path = os.path.join(logs_dir, "login_probe.json")
    if page is None:
        payload = {"title": "", "url": "", "frames": []}
        with open(probe_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return

    frames_payload: list[dict[str, Any]] = []
    for frame in page.frames:
        inputs_payload: list[dict[str, Optional[str]]] = []
        try:
            input_locator = frame.locator("input")
            input_count = input_locator.count()
            password_count = frame.locator("input[type='password']").count()
            has_user_text = frame.locator("text=Użytkownik").count() > 0
            has_haslo_text = frame.locator("text=Hasło").count() > 0
        except Exception:
            input_count = 0
            password_count = 0
            has_user_text = False
            has_haslo_text = False

        for idx in range(input_count):
            try:
                item = input_locator.nth(idx)
                inputs_payload.append(
                    {
                        "type": item.get_attribute("type"),
                        "id": item.get_attribute("id"),
                        "name": item.get_attribute("name"),
                        "placeholder": item.get_attribute("placeholder"),
                        "ariaLabel": item.get_attribute("aria-label"),
                    }
                )
            except Exception:
                continue

        frames_payload.append(
            {
                "url": frame.url,
                "inputs": inputs_payload,
                "passwordCount": password_count,
                "inputCount": input_count,
                "hasUserText": has_user_text,
                "hasHasloText": has_haslo_text,
            }
        )

    payload = {
        "title": page.title(),
        "url": page.url,
        "frames": frames_payload,
    }
    with open(probe_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _login_inputs_not_found(
    log_path: str,
    critical_path: str,
    page: Any,
    screens_dir: str,
) -> PortalRunResult:
    last_step = "STEP_02_LOGIN_INPUTS_NOT_FOUND"
    message = "Nie znalazłem pól logowania automatycznie"
    _log_event(log_path, f"{last_step}: {message}")
    _log_critical(critical_path, f"{last_step}: {message}")
    screenshot_path = _take_screenshot(page, screens_dir, last_step)
    _write_login_probe(log_path, page)
    return PortalRunResult(
        status="failed",
        last_step=last_step,
        message=message,
        detail="login_inputs",
        found=False,
        screenshot_path=screenshot_path,
    )


def _load_playwright():
    spec = importlib.util.find_spec("playwright.sync_api")
    if spec is None:
        return None, None
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    return sync_playwright, PlaywrightTimeout


def _missing_selector_result(
    step_label: str,
    selector_key: str,
    log_path: str,
    critical_path: str,
    page: Any,
    screens_dir: str,
) -> PortalRunResult:
    last_step = f"{step_label}_MISSING_SELECTOR"
    message = f"Brak selektora: {selector_key}"
    _log_event(log_path, f"{last_step}: {message}")
    _log_critical(critical_path, f"{last_step}: {message}")
    screenshot_path = _take_screenshot(page, screens_dir, last_step)
    return PortalRunResult(
        status="failed",
        last_step=last_step,
        message=message,
        detail=selector_key,
        found=False,
        screenshot_path=screenshot_path,
    )


def run_portal_flow(
    number: str,
    portal_data: dict[str, str],
    selectors: dict[str, Any],
    session_info: dict[str, str],
    debug: bool = False,
) -> PortalRunResult:
    log_path = session_info["log_path"]
    critical_path = session_info["critical_path"]
    screens_dir = session_info["screens_dir"]

    sync_playwright, PlaywrightTimeout = _load_playwright()
    if sync_playwright is None:
        _log_event(
            log_path,
            "STEP_00_IMPORT_PLAYWRIGHT: Missing Playwright dependency. Install playwright.",
        )
        return PortalRunResult(
            status="failed",
            last_step="STEP_00_IMPORT_PLAYWRIGHT",
            message="Brak Playwright – zainstaluj",
            detail="playwright.sync_api",
            found=False,
        )

    portal_key = _load_portal_key(session_info)
    portal_data = _resolve_portal_data(portal_data, portal_key)
    if not portal_data and portal_key:
        portals = load_json(portals_path(), {})
        portal_data = _resolve_portal_data(portals, portal_key)

    url = portal_data.get("url")
    login = portal_data.get("login")
    password = portal_data.get("password")
    if not url:
        _log_event(log_path, "STEP_00_MISSING_PORTAL_DATA: Missing portal credentials.")
        return PortalRunResult(
            status="failed",
            last_step="STEP_00_MISSING_PORTAL_DATA",
            message="Brak danych portalu",
            detail="url/login/password",
            found=False,
        )
    if not login or not password:
        last_step = "STEP_02_CREDENTIALS_MISSING"
        message = "Brak loginu lub hasła do portalu"
        _log_event(log_path, f"{last_step}: {message}")
        return PortalRunResult(
            status="failed",
            last_step=last_step,
            message=message,
            detail="login/password",
            found=False,
        )

    page = None
    try:
        with sync_playwright() as playwright:
            _log_event(log_path, "STEP_01_OPEN_URL: Launching browser.")
            browser = playwright.chromium.launch(headless=False)
            page = browser.new_page()
            page.on("dialog", lambda dialog: dialog.accept())
            page.goto(url, timeout=30_000)
            page.wait_for_load_state("domcontentloaded")
            if debug:
                _take_screenshot(page, screens_dir, "STEP_01_OPEN_URL")

            username_selector = selectors.get("login_username")
            password_selector = selectors.get("login_password")
            submit_selector = selectors.get("login_submit")
            if username_selector and password_selector and submit_selector:
                _log_event(
                    log_path,
                    f"STEP_02_LOGIN_DETECTION: Using selector login_username={username_selector}",
                )
            else:
                _log_event(log_path, "STEP_02_LOGIN_DETECTION: Using AUTO login detection")

            username_locator = _locator_from_selector(page, username_selector)
            password_locator = _locator_from_selector(page, password_selector)
            submit_locator = _locator_from_selector(page, submit_selector)

            login_frame = page.main_frame
            if not username_locator or not password_locator:
                detected = find_login_in_any_frame(page)
                if detected:
                    login_frame, username_locator, password_locator, detected_submit = detected
                    if not submit_locator:
                        submit_locator = detected_submit

            if not username_locator:
                username_locator = _auto_detect_username(page)
            if not password_locator:
                password_locator = _auto_detect_password(page)
            if not submit_locator:
                submit_locator = _auto_detect_submit(page)

            if _same_element(username_locator, password_locator):
                password_locator = None

            if not username_locator or not password_locator:
                return _login_inputs_not_found(
                    log_path, critical_path, page, screens_dir
                )

            login_frame = _locator_frame(username_locator, login_frame)

            _log_event(log_path, "STEP_02_LOGIN_FILL: Filling login form.")
            username_locator.click()
            username_locator.fill(login)
            password_locator.click()
            password_locator.fill(password)
            try:
                user_len = len(username_locator.input_value())
            except Exception:
                user_len = len(login or "")
            try:
                pass_len = len(password_locator.input_value())
            except Exception:
                pass_len = 0
            _log_event(
                log_path,
                f"STEP_02_LOGIN_FILL: user_len={user_len}, password_len={pass_len}",
            )
            if pass_len == 0:
                password_locator.click()
                password_locator.press("Control+A")
                password_locator.type(password, delay=25)
                try:
                    pass_len = len(password_locator.input_value())
                except Exception:
                    pass_len = 0
                _log_event(
                    log_path,
                    f"STEP_02_LOGIN_FILL: password_len={pass_len} after fallback",
                )
                if pass_len == 0:
                    last_step = "STEP_02_PASSWORD_NOT_SET"
                    message = "Nie udało się wpisać hasła w pole hasła"
                    _log_event(log_path, f"{last_step}: {message}")
                    screenshot_path = _take_screenshot(page, screens_dir, last_step)
                    return PortalRunResult(
                        status="failed",
                        last_step=last_step,
                        message=message,
                        detail="password",
                        found=False,
                        screenshot_path=screenshot_path,
                    )
            if debug:
                _take_screenshot(page, screens_dir, "STEP_02_LOGIN_FILL")

            _log_event(log_path, "STEP_03_LOGIN_SUBMIT: Submitting login form.")
            if submit_locator:
                submit_locator.click()
            else:
                try:
                    password_locator.press("Enter")
                except Exception:
                    page.keyboard.press("Enter")
            page.wait_for_load_state("domcontentloaded")
            start_time = time.time()
            while time.time() - start_time < 5:
                if not _login_form_visible(login_frame):
                    break
                page.wait_for_timeout(500)

            password_error_selector = selectors.get("password_error")
            if password_error_selector and page.locator(password_error_selector).count() > 0:
                _log_event(log_path, "STEP_03_LOGIN_SUBMIT: Password error detected.")
                screenshot_path = _take_screenshot(page, screens_dir, "STEP_03_LOGIN_SUBMIT")
                browser.close()
                return PortalRunResult(
                    status="password_error",
                    last_step="STEP_03_LOGIN_SUBMIT",
                    message="Błędne hasło",
                    detail="password_error",
                    found=False,
                    screenshot_path=screenshot_path,
                )

            if debug:
                _take_screenshot(page, screens_dir, "STEP_03_LOGIN_SUBMIT")

            if _login_form_visible(login_frame):
                last_step = "STEP_03_LOGIN_FAILED_STILL_ON_FORM"
                message = (
                    "Logowanie nie powiodło się (nadal widzę formularz). "
                    "Możliwe złe hasło albo nie kliknęło."
                )
                _log_event(log_path, f"{last_step}: {message}")
                screenshot_path = _take_screenshot(page, screens_dir, last_step)
                return PortalRunResult(
                    status="failed",
                    last_step=last_step,
                    message=message,
                    detail="login_form_visible",
                    found=False,
                    screenshot_path=screenshot_path,
                )

            ok_selector = selectors.get("ok_button")
            _log_event(log_path, "STEP_04_CLICK_OK_LOOP: Clicking OK dialogs.")
            if ok_selector:
                for _ in range(5):
                    if page.locator(ok_selector).count() == 0:
                        break
                    page.click(ok_selector)
                    page.wait_for_timeout(1_000)
            _click_okish_things(page, log_path)
            if debug:
                _take_screenshot(page, screens_dir, "STEP_04_CLICK_OK_LOOP")

            nav_selector = selectors.get("roboty_niezakonczone_link")
            if not nav_selector:
                return _missing_selector_result(
                    "STEP_05",
                    "roboty_niezakonczone_link",
                    log_path,
                    critical_path,
                    page,
                    screens_dir,
                )

            _log_event(log_path, "STEP_05_NAV_ROBOTY_NIEZAKONCZONE: Navigating.")
            page.click(nav_selector)
            page.wait_for_timeout(2_000)
            if debug:
                _take_screenshot(page, screens_dir, "STEP_05_NAV_ROBOTY_NIEZAKONCZONE")

            _log_event(log_path, "STEP_06_SEARCH_NUMBER: Searching for number.")
            search_selector = selectors.get("search_input")
            results_selector = selectors.get("results_container")
            found = False

            if search_selector:
                page.fill(search_selector, number)
                page.press(search_selector, "Enter")
                page.wait_for_timeout(2_000)
                container_text = ""
                if results_selector:
                    container_text = page.locator(results_selector).inner_text()
                else:
                    container_text = page.content()
                found = number in container_text
            elif results_selector:
                container_text = page.locator(results_selector).inner_text()
                found = number in container_text
            else:
                return _missing_selector_result(
                    "STEP_06",
                    "search_input/results_container",
                    log_path,
                    critical_path,
                    page,
                    screens_dir,
                )

            if debug:
                _take_screenshot(page, screens_dir, "STEP_06_SEARCH_NUMBER")

            _log_event(log_path, "STEP_07_VALIDATE_FOUND: Validating result.")
            if debug:
                _take_screenshot(page, screens_dir, "STEP_07_VALIDATE_FOUND")

            browser.close()
            return PortalRunResult(
                status="success",
                last_step="STEP_07_VALIDATE_FOUND",
                message="Znaleziono" if found else "Nie znaleziono",
                detail=number,
                found=found,
            )
    except PlaywrightTimeout as exc:
        _log_event(log_path, f"STEP_99_TIMEOUT: {exc}")
        screenshot_path = _take_screenshot(page, screens_dir, "STEP_99_TIMEOUT")
        return PortalRunResult(
            status="failed",
            last_step="STEP_99_TIMEOUT",
            message="Timeout podczas uruchamiania Playwright",
            detail=str(exc),
            found=False,
            screenshot_path=screenshot_path,
        )
    except Exception as exc:
        _log_event(log_path, f"STEP_98_ERROR: {exc}")
        screenshot_path = _take_screenshot(page, screens_dir, "STEP_98_ERROR")
        return PortalRunResult(
            status="failed",
            last_step="STEP_98_ERROR",
            message="Błąd podczas uruchamiania Playwright",
            detail=str(exc),
            found=False,
            screenshot_path=screenshot_path,
        )
