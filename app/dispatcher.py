from __future__ import annotations

import os


SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")


def handle(button_id: str) -> None:
    """Handle a button click by checking for an assigned script."""
    script_path = os.path.join(SCRIPTS_DIR, f"{button_id}.py")
    if not os.path.isfile(script_path):
        print(f"Brak przypisanego skryptu dla {button_id}")
        return

    print(f"Znaleziono skrypt dla {button_id}: {script_path}")
