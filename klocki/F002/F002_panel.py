from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
import tkinter as tk
from tkinter import ttk


def _find_repo_root(start_path: Path) -> Path:
    for parent in [start_path, *start_path.parents]:
        if (parent / ".git").exists():
            return parent
        if (parent / "klocki").exists():
            return parent
    return start_path.parent


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
F001_RUNTIME = REPO_ROOT / "klocki" / "F001_runtime"
F002_RUNTIME = REPO_ROOT / "klocki" / "F002_runtime"
F002_LOG = F002_RUNTIME / "logs" / "F002.log"
F002_STATE = F002_RUNTIME / "state" / "F002_state.json"
INDEX_CASES = F001_RUNTIME / "index_cases.json"
SHARED_STATE = F001_RUNTIME / "shared_state.json"
SHARED_STATE_LEGACY = F001_RUNTIME / "shared" / "shared_state.json"

ULDK_BASE_URL = "https://uldk.gugik.gov.pl/"


def _ensure_runtime() -> None:
    os.makedirs(F002_RUNTIME / "logs", exist_ok=True)
    os.makedirs(F002_RUNTIME / "state", exist_ok=True)
    if not F002_STATE.exists():
        _save_json(F002_STATE, {})


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _save_json(path: Path, payload: Any) -> None:
    os.makedirs(path.parent, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _log(message: str) -> None:
    os.makedirs(F002_LOG.parent, exist_ok=True)
    timestamp = datetime.now().isoformat(timespec="seconds")
    with F002_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def _open_path(path: str) -> None:
    if not path:
        return
    if os.name == "nt":
        os.startfile(path)
    else:
        os.system(f'xdg-open "{path}"')


def _build_case_index() -> None:
    script_path = REPO_ROOT / "klocki" / "_shared" / "build_case_index.py"
    if script_path.exists():
        subprocess.run(["python", os.fspath(script_path)], check=False)


def _load_cases() -> list[dict[str, Any]]:
    if not INDEX_CASES.exists():
        _build_case_index()
    payload = _load_json(INDEX_CASES, {})
    cases = payload.get("cases", []) if isinstance(payload, dict) else []
    return cases


def _find_active_case_dir(cases: list[dict[str, Any]]) -> str:
    for shared_path in (SHARED_STATE, SHARED_STATE_LEGACY):
        data = _load_json(shared_path, {})
        if isinstance(data, dict):
            for key in ("case_dir", "last_case_dir"):
                value = data.get(key)
                if value:
                    return value
    if cases:
        return cases[0].get("case_dir", "")
    return ""


def _format_case_label(case: dict[str, Any]) -> str:
    portal = (case.get("portal_key") or "").upper()
    gkn = case.get("gkn") or ""
    timestamp = case.get("timestamp") or ""
    return f"{portal} | {gkn} | {timestamp}"


def _parse_gk_poligon(path: Path) -> list[list[float]]:
    points: list[list[float]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            numbers = [item.replace(",", ".") for item in line.strip().split()]
            if len(numbers) < 2:
                continue
            try:
                x = float(numbers[0])
                y = float(numbers[1])
            except ValueError:
                continue
            points.append([x, y])
    return points


def _parse_polygon_coords(path: Path) -> list[list[float]]:
    content = path.read_text(encoding="utf-8")
    numbers: list[float] = []
    for token in content.replace(";", " ").replace(",", " ").split():
        try:
            numbers.append(float(token))
        except ValueError:
            continue
    points = []
    for idx in range(0, len(numbers) - 1, 2):
        points.append([numbers[idx], numbers[idx + 1]])
    return points


def _load_polygon(case_dir: Path) -> tuple[list[list[float]], str]:
    gk_files = sorted(case_dir.glob("GK_*_poligon.txt"))
    if gk_files:
        return _parse_gk_poligon(gk_files[0]), os.fspath(gk_files[0])
    polygon_path = case_dir / "polygon_coords.txt"
    if polygon_path.exists():
        return _parse_polygon_coords(polygon_path), os.fspath(polygon_path)
    return [], ""


def _close_polygon(points: list[list[float]]) -> list[list[float]]:
    if not points:
        return []
    closed = [point[:] for point in points]
    if closed[0] != closed[-1]:
        closed.append(closed[0][:])
    return closed


def _polygon_hash(points: list[list[float]]) -> str:
    normalized = ";".join(f"{pt[0]:.4f},{pt[1]:.4f}" for pt in points)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _polygon_centroid(points: list[list[float]]) -> list[float]:
    if len(points) < 3:
        return points[0] if points else [0.0, 0.0]
    area = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if area == 0:
        return points[0]
    area *= 0.5
    cx /= 6 * area
    cy /= 6 * area
    return [cx, cy]


def _point_in_polygon(point: list[float], polygon: list[list[float]]) -> bool:
    x, y = point
    inside = False
    for i in range(len(polygon) - 1):
        x0, y0 = polygon[i]
        x1, y1 = polygon[i + 1]
        if (y0 > y) != (y1 > y):
            x_intersect = (x1 - x0) * (y - y0) / (y1 - y0 + 1e-9) + x0
            if x < x_intersect:
                inside = not inside
    return inside


def _grid_points(polygon: list[list[float]], limit: int) -> list[list[float]]:
    xs = [pt[0] for pt in polygon]
    ys = [pt[1] for pt in polygon]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = max_x - min_x
    height = max_y - min_y
    if width == 0 or height == 0:
        return []
    count = max(1, int(math.sqrt(limit)))
    step_x = width / count
    step_y = height / count
    points: list[list[float]] = []
    for i in range(1, count):
        for j in range(1, count):
            candidate = [min_x + i * step_x, min_y + j * step_y]
            if _point_in_polygon(candidate, polygon):
                points.append(candidate)
                if len(points) >= limit:
                    return points
    return points


def _sample_points(polygon: list[list[float]], limit: int) -> list[list[float]]:
    unique: list[list[float]] = []
    seen = set()

    def _add(point: list[float]) -> None:
        key = (round(point[0], 4), round(point[1], 4))
        if key not in seen:
            seen.add(key)
            unique.append(point)

    for point in polygon[:-1]:
        _add(point)
    centroid = _polygon_centroid(polygon)
    _add(centroid)
    remaining = max(0, limit - len(unique))
    if remaining:
        for point in _grid_points(polygon, remaining):
            _add(point)
            if len(unique) >= limit:
                break
    return unique[:limit]


def _parse_uldk_response(text: str) -> dict[str, str | None]:
    raw = (text or "").strip()
    if not raw:
        return {"raw": "", "status": None, "teryt": None, "name": None}
    for sep in (";", "|", ","):
        parts = raw.split(sep)
        if len(parts) >= 3:
            return {
                "raw": raw,
                "status": parts[0].strip(),
                "teryt": parts[1].strip(),
                "name": parts[2].strip(),
            }
    return {"raw": raw, "status": None, "teryt": None, "name": None}


def _query_uldk(request_name: str, point: list[float], srid: int) -> dict[str, str | None]:
    xy = f"{point[0]},{point[1]},{srid}"
    params = {"request": request_name, "xy": xy}
    response = requests.get(ULDK_BASE_URL, params=params, timeout=10)
    return _parse_uldk_response(response.text)


def _write_csv(path: Path, communes: dict[str, str], regions: dict[str, str]) -> None:
    lines = ["type,teryt,name"]
    for teryt, name in sorted(communes.items()):
        lines.append(f"commune,{teryt},{name}")
    for teryt, name in sorted(regions.items()):
        lines.append(f"region,{teryt},{name}")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_summary(path: Path, communes: dict[str, str], regions: dict[str, str]) -> None:
    path.write_text(
        "\n".join(
            [
                "# F002 summary",
                "",
                f"- Liczba gmin: {len(communes)}",
                f"- Liczba obrębów: {len(regions)}",
            ]
        ),
        encoding="utf-8",
    )


def _update_manifest(case_dir: Path, json_path: Path, csv_path: Path, summary_path: Path) -> None:
    manifest_path = case_dir / "manifest.json"
    payload = _load_json(manifest_path, {}) if manifest_path.exists() else {}
    payload["f002"] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "json": os.fspath(json_path),
        "csv": os.fspath(csv_path),
        "summary": os.fspath(summary_path),
    }
    _save_json(manifest_path, payload)


class F002Panel:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("F002")
        _ensure_runtime()
        self.cases: list[dict[str, Any]] = []
        self.case_dir_var = tk.StringVar(value="")
        self.case_label_var = tk.StringVar(value="")
        self.srid_var = tk.StringVar(value="2179")
        self.limit_var = tk.StringVar(value="200")
        self.last_step_var = tk.StringVar(value="-")
        self.message_var = tk.StringVar(value="-")
        self.result_var = tk.StringVar(value="-")
        self.paths_var = tk.StringVar(value="-")
        self.cache_var = tk.StringVar(value="-")
        self._load_state()
        self._build_ui()
        self._refresh_cases()

    def _load_state(self) -> None:
        state = _load_json(F002_STATE, {})
        if isinstance(state, dict):
            self.srid_var.set(str(state.get("srid", "2179")))
            self.limit_var.set(str(state.get("limit", "200")))

    def _save_state(self) -> None:
        _save_json(
            F002_STATE,
            {
                "srid": self.srid_var.get(),
                "limit": self.limit_var.get(),
                "last_case_dir": self.case_dir_var.get(),
            },
        )

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill="x")
        ttk.Button(header, text="F002", command=self._refresh_cases).pack(side="left")
        ttk.Label(
            header,
            text="Panel: wyznacza gminy i obręby na podstawie poligonu.",
        ).pack(side="left", padx=10)

        case_frame = ttk.Labelframe(self.root, text="Case", padding=10)
        case_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(case_frame, text="Aktywny case:").grid(row=0, column=0, sticky="w")
        self.case_combo = ttk.Combobox(case_frame, textvariable=self.case_label_var, width=60)
        self.case_combo.grid(row=0, column=1, sticky="w", padx=5)
        self.case_combo.bind("<<ComboboxSelected>>", self._on_case_selected)
        ttk.Button(case_frame, text="Odśwież listę", command=self._refresh_cases).grid(
            row=0, column=2, padx=5
        )
        ttk.Label(case_frame, text="Ścieżka:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(case_frame, textvariable=self.case_dir_var, width=70, state="readonly").grid(
            row=1, column=1, columnspan=2, sticky="w", padx=5
        )

        config_frame = ttk.Labelframe(self.root, text="Konfiguracja", padding=10)
        config_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(config_frame, text="SRID:").grid(row=0, column=0, sticky="w")
        ttk.Entry(config_frame, textvariable=self.srid_var, width=10).grid(
            row=0, column=1, sticky="w", padx=5
        )
        ttk.Label(config_frame, text="Limit punktów:").grid(row=0, column=2, sticky="w")
        ttk.Entry(config_frame, textvariable=self.limit_var, width=10).grid(
            row=0, column=3, sticky="w", padx=5
        )

        actions_frame = ttk.Frame(self.root, padding=10)
        actions_frame.pack(fill="x")
        ttk.Button(actions_frame, text="Uruchom F002", command=self._run_async).pack(
            side="left", padx=5
        )
        ttk.Button(actions_frame, text="Otwórz folder case", command=self._open_case).pack(
            side="left", padx=5
        )
        ttk.Button(
            actions_frame, text="Otwórz wynik JSON", command=self._open_json
        ).pack(side="left", padx=5)
        ttk.Button(
            actions_frame, text="Otwórz wynik CSV", command=self._open_csv
        ).pack(side="left", padx=5)

        status_frame = ttk.Labelframe(self.root, text="Status", padding=10)
        status_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(status_frame, text="Ostatni krok:").grid(row=0, column=0, sticky="w")
        ttk.Label(status_frame, textvariable=self.last_step_var).grid(row=0, column=1, sticky="w")
        ttk.Label(status_frame, text="Komunikat:").grid(row=1, column=0, sticky="w")
        ttk.Label(status_frame, textvariable=self.message_var).grid(row=1, column=1, sticky="w")
        ttk.Label(status_frame, text="Wynik:").grid(row=2, column=0, sticky="w")
        ttk.Label(status_frame, textvariable=self.result_var).grid(row=2, column=1, sticky="w")
        ttk.Label(status_frame, text="Ścieżki:").grid(row=3, column=0, sticky="w")
        ttk.Label(status_frame, textvariable=self.paths_var).grid(row=3, column=1, sticky="w")
        ttk.Label(status_frame, text="Cache:").grid(row=4, column=0, sticky="w")
        ttk.Label(status_frame, textvariable=self.cache_var).grid(row=4, column=1, sticky="w")

    def _refresh_cases(self) -> None:
        self.cases = _load_cases()
        labels = [_format_case_label(case) for case in self.cases]
        self.case_combo["values"] = labels
        active_dir = _find_active_case_dir(self.cases)
        self._select_case_by_dir(active_dir)

    def _select_case_by_dir(self, case_dir: str) -> None:
        if not case_dir:
            self.case_dir_var.set("")
            return
        for idx, case in enumerate(self.cases):
            if case.get("case_dir") == case_dir:
                self.case_combo.current(idx)
                self.case_label_var.set(_format_case_label(case))
                self.case_dir_var.set(case_dir)
                return
        self.case_dir_var.set(case_dir)

    def _on_case_selected(self, _event: Any) -> None:
        idx = self.case_combo.current()
        if idx < 0:
            return
        case_dir = self.cases[idx].get("case_dir", "")
        self.case_dir_var.set(case_dir)
        self._save_state()

    def _run_async(self) -> None:
        thread = threading.Thread(target=self._run, daemon=True)
        thread.start()

    def _set_status(self, step: str, message: str, result: str = "-") -> None:
        self.last_step_var.set(step)
        self.message_var.set(message)
        self.result_var.set(result)

    def _run(self) -> None:
        case_dir_value = self.case_dir_var.get()
        if not case_dir_value:
            self._set_status("INIT", "Brak aktywnego case.")
            return
        case_dir = Path(case_dir_value)
        if not case_dir.exists():
            self._set_status("INIT", "Case nie istnieje.")
            return
        try:
            srid = int(self.srid_var.get())
        except ValueError:
            srid = 2179
        try:
            limit = int(self.limit_var.get())
        except ValueError:
            limit = 200

        self._set_status("POLYGON", "Wczytywanie poligonu")
        points, polygon_path = _load_polygon(case_dir)
        if len(points) < 3:
            self._set_status("POLYGON", "Brak poprawnego poligonu", "error")
            return
        polygon = _close_polygon(points)
        polygon_hash = _polygon_hash(polygon)

        json_path = case_dir / "f002_admin_units.json"
        csv_path = case_dir / "f002_admin_units.csv"
        summary_path = case_dir / "f002_summary.md"

        if json_path.exists():
            payload = _load_json(json_path, {})
            if payload.get("polygon_hash") == polygon_hash:
                self.cache_var.set("cache hit")
                self.paths_var.set(f"{json_path}; {csv_path}")
                self._set_status("CACHE", "Wykryto cache", "ok")
                return

        self.cache_var.set("-")
        self._set_status("ULDK", "Pobieranie danych z ULDK")

        sample_points = _sample_points(polygon, limit)
        communes: dict[str, str] = {}
        regions: dict[str, str] = {}

        for point in sample_points:
            commune = _query_uldk("GetCommuneByXY", point, srid)
            if commune.get("teryt"):
                communes[str(commune["teryt"])] = str(commune.get("name") or "")
            region = _query_uldk("GetRegionByXY", point, srid)
            if region.get("teryt"):
                regions[str(region["teryt"])] = str(region.get("name") or "")

        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "case_dir": os.fspath(case_dir),
            "polygon_hash": polygon_hash,
            "srid": srid,
            "polygon_file": polygon_path,
            "sample_points": sample_points,
            "communes": [{"teryt": k, "name": v} for k, v in communes.items()],
            "regions": [{"teryt": k, "name": v} for k, v in regions.items()],
        }
        _save_json(json_path, payload)
        _write_csv(csv_path, communes, regions)
        _write_summary(summary_path, communes, regions)
        _update_manifest(case_dir, json_path, csv_path, summary_path)
        self.paths_var.set(f"{json_path}; {csv_path}")
        self._set_status("DONE", "Zapisano wyniki", "ok")
        self._save_state()
        _log(f"DONE case={case_dir} communes={len(communes)} regions={len(regions)}")

    def _open_case(self) -> None:
        _open_path(self.case_dir_var.get())

    def _open_json(self) -> None:
        case_dir_value = self.case_dir_var.get()
        if not case_dir_value:
            return
        _open_path(os.fspath(Path(case_dir_value) / "f002_admin_units.json"))

    def _open_csv(self) -> None:
        case_dir_value = self.case_dir_var.get()
        if not case_dir_value:
            return
        _open_path(os.fspath(Path(case_dir_value) / "f002_admin_units.csv"))


def launch_panel() -> None:
    root = tk.Tk()
    F002Panel(root)
    root.mainloop()


if __name__ == "__main__":
    launch_panel()
