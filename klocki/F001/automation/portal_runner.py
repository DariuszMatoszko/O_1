from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Optional

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except Exception as e:  # pragma: no cover - fallback for missing dependency
    sync_playwright = None
    PlaywrightTimeout = Exception
    _PLAYWRIGHT_IMPORT_ERROR = e
else:
    _PLAYWRIGHT_IMPORT_ERROR = None


LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "F001.log")


@dataclass
class PortalRunResult:
    status: str
    last_step: str
    message: str
    detail: str
    found: bool


def _log_event(message: str) -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(f"{message}\n")


def load_selectors() -> dict[str, Any]:
    selectors_path = os.path.join(os.path.dirname(__file__), "selectors.json")
    if not os.path.exists(selectors_path):
        return {}
    with open(selectors_path, "r", encoding="utf-8") as selectors_file:
        return json.load(selectors_file)


def run_portal_flow(number: str, selectors: Optional[dict[str, Any]] = None) -> PortalRunResult:
    if sync_playwright is None:
        _log_event(
            "STEP_00_IMPORT_PLAYWRIGHT: Missing Playwright dependency. "
            "Install playwright to continue."
        )
        return PortalRunResult(
            status="failed",
            last_step="STEP_00_IMPORT_PLAYWRIGHT",
            message="Brak Playwright – zainstaluj",
            detail=str(_PLAYWRIGHT_IMPORT_ERROR),
            found=False,
        )

    selectors = selectors or load_selectors()

    _log_event("STEP_01_START: Starting portal flow.")
    try:
        with sync_playwright() as playwright:
            _log_event("STEP_02_BROWSER: Launching browser.")
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            _log_event("STEP_03_NAVIGATE: Placeholder navigation.")
            page.goto("about:blank", timeout=10_000)
            browser.close()
    except PlaywrightTimeout as exc:
        _log_event(f"STEP_99_TIMEOUT: {exc}")
        return PortalRunResult(
            status="failed",
            last_step="STEP_99_TIMEOUT",
            message="Timeout podczas uruchamiania Playwright",
            detail=str(exc),
            found=False,
        )
    except Exception as exc:  # pragma: no cover - safeguard
        _log_event(f"STEP_98_ERROR: {exc}")
        return PortalRunResult(
            status="failed",
            last_step="STEP_98_ERROR",
            message="Błąd podczas uruchamiania Playwright",
            detail=str(exc),
            found=False,
        )

    _log_event("STEP_04_NOT_FOUND: Portal entry not found.")
    return PortalRunResult(
        status="success",
        last_step="STEP_04_NOT_FOUND",
        message="Portal entry not found",
        detail=f"NOT FOUND: {number}",
        found=False,
    )
