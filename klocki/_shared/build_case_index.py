from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


def _find_repo_root(start_path: Path) -> Path:
    for parent in [start_path, *start_path.parents]:
        if (parent / ".git").exists():
            return parent
        if (parent / "klocki").exists():
            return parent
    return start_path.parent


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
RUNTIME_ROOT = REPO_ROOT / "klocki" / "F001_runtime"
CASES_DIR = RUNTIME_ROOT / "cases"
INDEX_PATH = RUNTIME_ROOT / "index_cases.json"


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _case_entry(case_dir: Path) -> dict[str, Any]:
    portal_key = case_dir.parent.name
    gkn = case_dir.name
    meta_path = case_dir / "meta.json"
    meta_payload = {}
    if meta_path.exists():
        try:
            meta_payload = _load_json(meta_path, {})
        except json.JSONDecodeError:
            meta_payload = {}
    timestamp = datetime.fromtimestamp(case_dir.stat().st_mtime).isoformat(timespec="seconds")
    return {
        "portal_key": portal_key,
        "gkn": gkn,
        "case_dir": os.fspath(case_dir),
        "meta_path": os.fspath(meta_path) if meta_path.exists() else "",
        "meta": meta_payload,
        "timestamp": timestamp,
    }


def _is_case_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    expected = [
        path / "meta.json",
        path / "polygon_coords.txt",
    ]
    if any(item.exists() for item in expected):
        return True
    if list(path.glob("GK_*_poligon.txt")):
        return True
    return False


def build_index() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    if CASES_DIR.exists():
        for portal_dir in CASES_DIR.iterdir():
            if not portal_dir.is_dir():
                continue
            for case_dir in portal_dir.iterdir():
                if _is_case_dir(case_dir):
                    cases.append(_case_entry(case_dir))
    cases.sort(key=lambda item: item.get("timestamp", ""), reverse=True)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(cases),
        "cases": cases,
    }
    os.makedirs(RUNTIME_ROOT, exist_ok=True)
    with INDEX_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return payload


def main() -> None:
    build_index()


if __name__ == "__main__":
    main()
