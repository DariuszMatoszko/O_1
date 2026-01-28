from __future__ import annotations

import importlib.util
import json
import os
import re
import random
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


def _all_frames(page: Any) -> list[Any]:
    frames = [page.main_frame]
    frames.extend(frame for frame in page.frames if frame != page.main_frame)
    return frames


def dismiss_ok_dialogs(page: Any) -> None:
    okish_regex = re.compile(
        r"^\s*(OK|Dalej|Kontynuuj|Zamknij|Akceptuj|Zgadzam|Rozumiem)\s*$",
        re.I,
    )
    try:
        page.on("dialog", lambda dialog: dialog.accept())
    except Exception:
        pass

    try:
        page.wait_for_timeout(600)
    except Exception:
        pass

    deadline = time.time() + 8
    last_seen = time.time()
    while time.time() < deadline:
        clicked_any = False
        saw_dialog = False
        try:
            dialog_locator = page.locator("div.ui-dialog")
            dialog_count = dialog_locator.count()
        except Exception:
            dialog_count = 0

        for idx in range(dialog_count):
            dialog = dialog_locator.nth(idx)
            try:
                if not dialog.is_visible():
                    continue
            except Exception:
                continue
            saw_dialog = True
            try:
                button_locator = dialog.locator("div.ui-dialog-buttonpane button")
                button_count = button_locator.count()
            except Exception:
                continue
            for button_idx in range(button_count):
                button = button_locator.nth(button_idx)
                try:
                    if not button.is_visible():
                        continue
                    text = (button.text_content() or "").strip()
                except Exception:
                    continue
                if not okish_regex.match(text):
                    continue
                try:
                    button.scroll_into_view_if_needed()
                    button.click(force=True, timeout=1500)
                except Exception:
                    continue
                clicked_any = True
                last_seen = time.time()
                try:
                    page.wait_for_timeout(int(random.uniform(300, 700)))
                except Exception:
                    pass
                break

        if clicked_any:
            continue
        if not saw_dialog and time.time() - last_seen >= 1.0:
            break
        try:
            page.wait_for_timeout(250)
        except Exception:
            break


def get_frame_centr(page: Any) -> Any:
    deadline = time.time() + 8
    frame = None
    while time.time() < deadline:
        try:
            frame = page.frame(name="frame_centr")
        except Exception:
            frame = None
        if frame is not None:
            return frame
        try:
            page.wait_for_timeout(250)
        except Exception:
            break
    return frame


def open_list(page: Any, kind: str) -> bool:
    if kind == "unfinished":
        selector = "form#form_kerglista input[type=submit]"
    else:
        selector = "form#form_kerglistaz input[type=submit]"
    locator = _first_visible(page.locator(selector))
    if not locator:
        return False
    try:
        locator.click()
    except Exception:
        return False
    frame = get_frame_centr(page)
    if frame:
        try:
            frame.wait_for_load_state("domcontentloaded")
        except Exception:
            pass
    dismiss_ok_dialogs(page)
    return True


def find_number_in_frame(frame: Any, number: str) -> Any:
    if not frame:
        return None
    locator = _first_visible(frame.get_by_text(number, exact=False))
    if locator:
        return locator
    parts = [part for part in re.split(r"\W+", number) if part]
    if not parts:
        return None
    regex = re.compile(r"\W*".join(re.escape(part) for part in parts), re.I)
    return _first_visible(frame.get_by_text(regex, exact=False))


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


def _find_unfinished_link(page: Any, selector: Optional[str]) -> Any:
    frames = _all_frames(page)
    if selector:
        for frame in frames:
            locator = _first_visible(frame.locator(selector))
            if locator:
                return locator
    for frame in frames:
        locator = _first_visible(frame.get_by_text("Lista prac nieza", exact=False))
        if locator:
            return locator
        locator = _first_visible(
            frame.locator(
                "a:has-text('Lista prac nieza'),"
                " button:has-text('Lista prac nieza'),"
                " div:has-text('Lista prac nieza')"
            )
        )
        if locator:
            return locator
    return None


def _find_label_input(page: Any, label: str) -> Any:
    frames = _all_frames(page)
    for frame in frames:
        locator = _first_visible(
            frame.locator(
                "xpath=//*[contains(normalize-space(.),"
                f" '{label}')]/following::input[1]"
            )
        )
        if locator:
            return locator
    return None


def _find_submit_button(page: Any, label: str) -> Any:
    frames = _all_frames(page)
    for frame in frames:
        locator = _first_visible(frame.get_by_role("button", name=label))
        if locator:
            return locator
        locator = _first_visible(frame.get_by_text(label, exact=False))
        if locator:
            return locator
    return None


def _find_number_match(page: Any, number: str) -> Any:
    frames = _all_frames(page)
    for frame in frames:
        locator = _first_visible(frame.get_by_text(number, exact=False))
        if locator:
            return locator
    return None


def _export_work_artifacts(
    page: Any,
    frame: Any,
    session_root: str,
    screens_dir: str,
    log_path: str,
) -> Optional[str]:
    exports_dir = os.path.join(session_root, "exports")
    os.makedirs(exports_dir, exist_ok=True)
    main_html_path = os.path.join(exports_dir, "main.html")
    main_text_path = os.path.join(exports_dir, "main.txt")
    frame_html_path = os.path.join(exports_dir, "frame_centr.html")
    frame_text_path = os.path.join(exports_dir, "frame_centr.txt")
    screenshot_path = os.path.join(screens_dir, "work_opened.png")
    try:
        with open(main_html_path, "w", encoding="utf-8") as handle:
            handle.write(page.content())
        _log_event(log_path, f"STEP_08_EXPORT_WORK: saved {main_html_path}")
    except Exception as exc:
        _log_event(log_path, f"STEP_08_EXPORT_WORK: failed to save html ({exc})")
    try:
        with open(main_text_path, "w", encoding="utf-8") as handle:
            handle.write(page.locator("body").inner_text())
        _log_event(log_path, f"STEP_08_EXPORT_WORK: saved {main_text_path}")
    except Exception as exc:
        _log_event(log_path, f"STEP_08_EXPORT_WORK: failed to save text ({exc})")
    if frame:
        try:
            with open(frame_html_path, "w", encoding="utf-8") as handle:
                handle.write(frame.content())
            _log_event(log_path, f"STEP_08_EXPORT_WORK: saved {frame_html_path}")
        except Exception as exc:
            _log_event(
                log_path, f"STEP_08_EXPORT_WORK: failed to save frame html ({exc})"
            )
        try:
            with open(frame_text_path, "w", encoding="utf-8") as handle:
                handle.write(frame.locator("body").inner_text())
            _log_event(log_path, f"STEP_08_EXPORT_WORK: saved {frame_text_path}")
        except Exception as exc:
            _log_event(
                log_path, f"STEP_08_EXPORT_WORK: failed to save frame text ({exc})"
            )
    else:
        try:
            with open(frame_html_path, "w", encoding="utf-8") as handle:
                handle.write("")
            _log_event(log_path, f"STEP_08_EXPORT_WORK: saved {frame_html_path}")
        except Exception as exc:
            _log_event(
                log_path, f"STEP_08_EXPORT_WORK: failed to save frame html ({exc})"
            )
        try:
            with open(frame_text_path, "w", encoding="utf-8") as handle:
                handle.write("")
            _log_event(log_path, f"STEP_08_EXPORT_WORK: saved {frame_text_path}")
        except Exception as exc:
            _log_event(
                log_path, f"STEP_08_EXPORT_WORK: failed to save frame text ({exc})"
            )
    try:
        page.screenshot(path=screenshot_path, full_page=True)
        _log_event(log_path, f"STEP_08_EXPORT_WORK: saved {screenshot_path}")
        return screenshot_path
    except Exception as exc:
        _log_event(log_path, f"STEP_08_EXPORT_WORK: failed to save screenshot ({exc})")
    return None


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

            _log_event(log_path, "STEP_04_CLICK_OK_LOOP: Clicking OK dialogs.")
            dismiss_ok_dialogs(page)
            if debug:
                _take_screenshot(page, screens_dir, "STEP_04_CLICK_OK_LOOP")

            _log_event(log_path, "STEP_05_NAV_ROBOTY_NIEZAKONCZONE: Navigating.")
            if not open_list(page, "unfinished"):
                last_step = "STEP_05_NAV_UNFINISHED_NOT_FOUND"
                message = "Nie znalazłem przycisku Lista prac niezakończonych"
                _log_event(log_path, f"{last_step}: {message}")
                _log_critical(critical_path, f"{last_step}: {message}")
                screenshot_path = _take_screenshot(page, screens_dir, last_step)
                return PortalRunResult(
                    status="failed",
                    last_step=last_step,
                    message=message,
                    detail="form_kerglista",
                    found=False,
                    screenshot_path=screenshot_path,
                )

            frame = get_frame_centr(page)
            hit = find_number_in_frame(frame, number)
            if not hit:
                _log_event(log_path, "STEP_06_NAV_ROBOTY_ZAKONCZONE: Navigating.")
                if not open_list(page, "finished"):
                    last_step = "STEP_06_NAV_FINISHED_NOT_FOUND"
                    message = "Nie znalazłem przycisku Lista prac zakończonych"
                    _log_event(log_path, f"{last_step}: {message}")
                    _log_critical(critical_path, f"{last_step}: {message}")
                    screenshot_path = _take_screenshot(page, screens_dir, last_step)
                    return PortalRunResult(
                        status="failed",
                        last_step=last_step,
                        message=message,
                        detail="form_kerglistaz",
                        found=False,
                        screenshot_path=screenshot_path,
                    )
                frame = get_frame_centr(page)
                hit = find_number_in_frame(frame, number)

            if not hit:
                last_step = "STEP_07_NUMBER_NOT_FOUND"
                message = "Nie znaleziono numeru zgłoszenia"
                _log_event(log_path, f"{last_step}: {message}")
                _log_critical(critical_path, f"{last_step}: {message}")
                screenshot_path = _export_work_artifacts(
                    page,
                    frame,
                    session_info["session_root"],
                    screens_dir,
                    log_path,
                )
                browser.close()
                return PortalRunResult(
                    status="failed",
                    last_step=last_step,
                    message=message,
                    detail=number,
                    found=False,
                    screenshot_path=screenshot_path,
                )

            last_step = "STEP_07_NUMBER_FOUND"
            try:
                hit.click(force=True)
            except Exception:
                _log_event(log_path, f"{last_step}: failed to click match")
            if frame:
                try:
                    frame.wait_for_load_state("domcontentloaded")
                except Exception:
                    pass
            dismiss_ok_dialogs(page)

            screenshot_path = _export_work_artifacts(
                page,
                frame,
                session_info["session_root"],
                screens_dir,
                log_path,
            )
            browser.close()
            return PortalRunResult(
                status="success",
                last_step=last_step,
                message="Znaleziono",
                detail=number,
                found=True,
                screenshot_path=screenshot_path,
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
