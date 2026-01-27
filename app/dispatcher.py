from __future__ import annotations

import logging
import os


SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
PANEL_LOG_PATH = os.path.join(LOGS_DIR, "panel.log")


def handle(button_id: str, silent: bool = True) -> None:
    """Handle a button click by checking for an assigned script."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    logging.basicConfig(
        filename=PANEL_LOG_PATH,
        level=logging.INFO,
        format="[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M",
    )
    script_path = os.path.join(SCRIPTS_DIR, f"{button_id}.py")
    if not os.path.isfile(script_path):
        logging.info("Brak przypisanego skryptu dla %s", button_id)
        if not silent:
            print(f"Brak przypisanego skryptu dla {button_id}")
        return

    if not silent:
        print(f"Znaleziono skrypt dla {button_id}: {script_path}")
