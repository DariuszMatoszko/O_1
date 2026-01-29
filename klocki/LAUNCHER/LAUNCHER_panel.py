from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
import tkinter as tk


class LauncherPanel:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("OPERAT V2 — Launcher")
        self.root.geometry("900x650")
        self.root.resizable(False, False)

        self.repo_root = Path(__file__).resolve().parents[2]
        self.klocki_dir = self.repo_root / "klocki"
        self.logs_dir = Path(__file__).resolve().parent / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.logs_dir / "LAUNCHER.log"

        self.status_var = tk.StringVar(value="Gotowy")
        self._build_ui()
        self._load_klocki()

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill="x")
        ttk.Label(
            header,
            text="OPERAT V2 — Launcher",
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left")

        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(container, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            relief="sunken",
            anchor="w",
            padding=6,
        )
        status_bar.pack(side="bottom", fill="x")

    def _on_mousewheel(self, event: tk.Event) -> None:
        if event.delta:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _load_klocki(self) -> None:
        for child in self.scrollable_frame.winfo_children():
            child.destroy()

        pattern = re.compile(r"^F\d{3}$")
        if not self.klocki_dir.exists():
            messagebox.showwarning("Launcher", "Brak katalogu klocki")
            return

        klocki = sorted(
            [entry for entry in self.klocki_dir.iterdir() if entry.is_dir() and pattern.match(entry.name)],
            key=lambda entry: entry.name,
        )

        if not klocki:
            ttk.Label(self.scrollable_frame, text="Brak klocków do uruchomienia.").pack(
                anchor="w", pady=10, padx=10
            )
            return

        for entry in klocki:
            self._create_tile(entry)

    def _create_tile(self, klocek_dir: Path) -> None:
        frame = ttk.Labelframe(self.scrollable_frame, text=klocek_dir.name, padding=10)
        frame.pack(fill="x", padx=10, pady=6)

        button_row = ttk.Frame(frame)
        button_row.pack(fill="x")

        ttk.Button(
            button_row,
            text="URUCHOM",
            command=lambda d=klocek_dir: self._run_klocek(d),
            width=12,
        ).pack(side="left", padx=5)
        ttk.Button(
            button_row,
            text="FOLDER",
            command=lambda d=klocek_dir: self._open_folder(d, "folder"),
            width=10,
        ).pack(side="left", padx=5)
        ttk.Button(
            button_row,
            text="LOGI",
            command=lambda d=klocek_dir: self._open_logs(d),
            width=10,
        ).pack(side="left", padx=5)
        ttk.Button(
            button_row,
            text="EXPORT",
            command=lambda d=klocek_dir: self._open_export(d),
            width=10,
        ).pack(side="left", padx=5)

        status_text = self._read_state_status(klocek_dir)
        if status_text:
            ttk.Label(frame, text=status_text).pack(anchor="w", pady=(6, 0))

    def _read_state_status(self, klocek_dir: Path) -> str:
        state_path = klocek_dir / "state" / f"{klocek_dir.name}_state.json"
        if not state_path.exists():
            return ""
        try:
            with open(state_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            last_run = data.get("last_run", "-")
            status = data.get("last_status", data.get("status", "-"))
            return f"Status: {status} | Ostatni run: {last_run}"
        except (OSError, json.JSONDecodeError):
            return ""

    def _run_klocek(self, klocek_dir: Path) -> None:
        name = klocek_dir.name
        run_vbs = klocek_dir / f"RUN_{name}.vbs"
        run_bat = klocek_dir / f"RUN_{name}.bat"

        if run_vbs.exists():
            subprocess.Popen(["wscript.exe", str(run_vbs)], cwd=str(klocek_dir))
            self._set_status(f"Uruchomiono {name}")
            self._log_action(f"RUN VBS {name}")
            return

        if run_bat.exists():
            subprocess.Popen(["cmd.exe", "/c", str(run_bat)], cwd=str(klocek_dir))
            self._set_status(f"Uruchomiono {name}")
            self._log_action(f"RUN BAT {name}")
            return

        messagebox.showwarning("Launcher", f"Brak pliku RUN dla {name}")
        self._set_status(f"Brak pliku RUN dla {name}")
        self._log_action(f"BRAK RUN {name}")

    def _open_folder(self, path: Path, label: str) -> None:
        self._open_path(path)
        self._set_status(f"Otwarto {label} {path.name}")
        self._log_action(f"OPEN {label} {path}")

    def _open_logs(self, klocek_dir: Path) -> None:
        logs_dir = klocek_dir / "logs"
        target = logs_dir if logs_dir.exists() else klocek_dir
        self._open_folder(target, "logi")

    def _open_export(self, klocek_dir: Path) -> None:
        export_dir = klocek_dir / "export"
        exports_dir = klocek_dir / "exports"
        if export_dir.exists():
            self._open_folder(export_dir, "export")
            return
        if exports_dir.exists():
            self._open_folder(exports_dir, "export")
            return
        self._open_folder(klocek_dir, "folder")

    def _open_path(self, path: Path) -> None:
        if os.name == "nt":
            os.startfile(path)
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)

    def _log_action(self, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_path, "a", encoding="utf-8") as handle:
            handle.write(f"[{timestamp}] {message}\n")

