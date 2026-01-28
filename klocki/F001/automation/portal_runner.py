from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


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

    url = portal_data.get("url")
    login = portal_data.get("login")
    password = portal_data.get("password")
    if not url or not login or not password:
        _log_event(log_path, "STEP_00_MISSING_PORTAL_DATA: Missing portal credentials.")
        return PortalRunResult(
            status="failed",
            last_step="STEP_00_MISSING_PORTAL_DATA",
            message="Brak danych portalu",
            detail="url/login/password",
            found=False,
        )

    page = None
    try:
        with sync_playwright() as playwright:
            _log_event(log_path, "STEP_01_OPEN_URL: Launching browser.")
            browser = playwright.chromium.launch(headless=False)
            page = browser.new_page()
            page.goto(url, timeout=30_000)
            if debug:
                _take_screenshot(page, screens_dir, "STEP_01_OPEN_URL")

            username_selector = selectors.get("login_username")
            password_selector = selectors.get("login_password")
            submit_selector = selectors.get("login_submit")
            if not username_selector:
                return _missing_selector_result(
                    "STEP_02", "login_username", log_path, critical_path, page, screens_dir
                )
            if not password_selector:
                return _missing_selector_result(
                    "STEP_02", "login_password", log_path, critical_path, page, screens_dir
                )
            if not submit_selector:
                return _missing_selector_result(
                    "STEP_03", "login_submit", log_path, critical_path, page, screens_dir
                )

            _log_event(log_path, "STEP_02_LOGIN_FILL: Filling login form.")
            page.fill(username_selector, login)
            page.fill(password_selector, password)
            if debug:
                _take_screenshot(page, screens_dir, "STEP_02_LOGIN_FILL")

            _log_event(log_path, "STEP_03_LOGIN_SUBMIT: Submitting login form.")
            page.click(submit_selector)
            page.wait_for_timeout(2_000)

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

            ok_selector = selectors.get("ok_button")
            if not ok_selector:
                return _missing_selector_result(
                    "STEP_04", "ok_button", log_path, critical_path, page, screens_dir
                )

            _log_event(log_path, "STEP_04_CLICK_OK_LOOP: Clicking OK dialogs.")
            for _ in range(5):
                if page.locator(ok_selector).count() == 0:
                    break
                page.click(ok_selector)
                page.wait_for_timeout(1_000)
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
