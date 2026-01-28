from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timedelta
from typing import Any

RUNTIME_ROOT = os.path.join(os.path.dirname(__file__), "_runtime")
CONFIG_DIR = os.path.join(RUNTIME_ROOT, "config")
STATE_DIR = os.path.join(RUNTIME_ROOT, "state")
SHARED_DIR = os.path.join(RUNTIME_ROOT, "shared")
SESSIONS_DIR = os.path.join(RUNTIME_ROOT, "sessions")
LATEST_PATH = os.path.join(RUNTIME_ROOT, "LATEST.txt")


def ensure_runtime_dirs() -> None:
    for path in (CONFIG_DIR, STATE_DIR, SHARED_DIR, SESSIONS_DIR):
        os.makedirs(path, exist_ok=True)


def load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def selectors_path() -> str:
    return os.path.join(CONFIG_DIR, "selectors.json")


def portals_path() -> str:
    return os.path.join(STATE_DIR, "portals.json")


def shared_state_path() -> str:
    return os.path.join(SHARED_DIR, "shared_state.json")


def ensure_runtime_files() -> None:
    ensure_runtime_dirs()
    if not os.path.exists(selectors_path()):
        save_json(
            selectors_path(),
            {
                "login_username": "",
                "login_password": "",
                "login_submit": "",
                "ok_button": "",
                "roboty_niezakonczone_link": "",
                "search_input": "",
                "results_container": "",
                "password_error": "",
            },
        )
    if not os.path.exists(portals_path()):
        save_json(portals_path(), {})
    if not os.path.exists(shared_state_path()):
        save_json(shared_state_path(), {})


def _session_root(date_str: str, time_str: str, portal_key: str) -> str:
    folder_name = f"{time_str}_{portal_key}"
    return os.path.join(SESSIONS_DIR, date_str, folder_name)


def create_session(portal_key: str = "UNKNOWN") -> str:
    ensure_runtime_files()
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H%M%S")
    session_root = _session_root(date_str, time_str, portal_key)
    logs_dir = os.path.join(session_root, "logs")
    screens_dir = os.path.join(session_root, "screens")
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(screens_dir, exist_ok=True)
    run_path = os.path.join(session_root, "run.json")
    save_json(
        run_path,
        {
            "session_started_at": now.isoformat(timespec="seconds"),
            "portal_key": portal_key,
            "run_count": 0,
            "last_number": None,
            "last_status": None,
            "last_step": None,
        },
    )
    start_log_path = os.path.join(logs_dir, "F001_start.log")
    with open(start_log_path, "a", encoding="utf-8") as handle:
        handle.write(f"Session started at {now.isoformat(timespec='seconds')}\n")
    with open(LATEST_PATH, "w", encoding="utf-8") as handle:
        handle.write(session_root)
    return session_root


def update_run_info(session_root: str, updates: dict[str, Any]) -> None:
    run_path = os.path.join(session_root, "run.json")
    data = load_json(run_path, {})
    data.update(updates)
    save_json(run_path, data)


def session_paths(session_root: str) -> dict[str, str]:
    logs_dir = os.path.join(session_root, "logs")
    screens_dir = os.path.join(session_root, "screens")
    return {
        "session_root": session_root,
        "logs_dir": logs_dir,
        "screens_dir": screens_dir,
        "log_path": os.path.join(logs_dir, "F001.log"),
        "critical_path": os.path.join(logs_dir, "F001_critical.md"),
        "run_path": os.path.join(session_root, "run.json"),
    }


def cleanup_sessions(max_age_days: int = 14) -> int:
    """Remove session folders older than max_age_days."""
    if not os.path.exists(SESSIONS_DIR):
        return 0
    cutoff = datetime.now() - timedelta(days=max_age_days)
    removed = 0
    for date_name in os.listdir(SESSIONS_DIR):
        date_path = os.path.join(SESSIONS_DIR, date_name)
        if not os.path.isdir(date_path):
            continue
        try:
            date_value = datetime.strptime(date_name, "%Y-%m-%d")
        except ValueError:
            date_value = datetime.fromtimestamp(os.path.getmtime(date_path))
        if date_value >= cutoff:
            continue
        shutil.rmtree(date_path, ignore_errors=True)
        removed += 1
    return removed


def clear_sessions() -> None:
    if not os.path.exists(SESSIONS_DIR):
        return
    for date_name in os.listdir(SESSIONS_DIR):
        date_path = os.path.join(SESSIONS_DIR, date_name)
        if os.path.isdir(date_path):
            shutil.rmtree(date_path, ignore_errors=True)


def read_latest_session() -> str | None:
    if not os.path.exists(LATEST_PATH):
        return None
    with open(LATEST_PATH, "r", encoding="utf-8") as handle:
        return handle.read().strip() or None
