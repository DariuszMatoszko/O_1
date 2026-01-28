from __future__ import annotations

import os
import threading
import tkinter as tk
from pathlib import Path
from typing import Optional
from tkinter import messagebox, ttk

from runtime_utils import (
    cleanup_sessions,
    clear_sessions,
    create_session,
    ensure_runtime_files,
    load_json,
    panel_state_path,
    portals_path,
    read_latest_session,
    save_json,
    selectors_path,
    session_paths,
    update_run_info,
)

PORTALS = {
    "sokolski": "Powiat sokólski",
    "augustowski": "Powiat augustowski",
}


def _open_path(path: str) -> None:
    if not path:
        return
    if os.name == "nt":
        os.startfile(path)
    else:
        os.system(f'xdg-open "{path}"')


class F001Panel:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("F001")
        self.portal_key: str | None = None
        self.edit_mode = False
        self.password_retry = False
        self.pending_retry_number: str | None = None
        self.session_root: Optional[str] = None
        self.session_info: dict[str, str] = {}

        ensure_runtime_files()
        cleanup_sessions()

        self.portals = load_json(portals_path(), {})
        self.selectors = load_json(selectors_path(), {})
        self.state_path = panel_state_path()
        self.panel_state = load_json(self.state_path, {})
        self.case_dir_var = tk.StringVar(value=self.panel_state.get("last_case_dir", ""))

        self._build_ui()

    def _build_ui(self) -> None:
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill="x")
        title_button = ttk.Button(header, text="F001", command=self._focus_number)
        title_button.pack(side="left")
        description = ttk.Label(
            header,
            text="Automatyczny panel: loguje się do portalu i szuka numeru GKN.",
        )
        description.pack(side="left", padx=10)

        portal_frame = ttk.Labelframe(self.root, text="Wybór powiatu", padding=10)
        portal_frame.pack(fill="x", padx=10, pady=5)
        for key, label in PORTALS.items():
            ttk.Button(
                portal_frame,
                text=label,
                command=lambda k=key: self._select_portal(k),
                width=24,
            ).pack(side="left", padx=5)

        data_frame = ttk.Labelframe(self.root, text="Dane portalu", padding=10)
        data_frame.pack(fill="x", padx=10, pady=5)
        self.data_frame = data_frame
        self.data_status = ttk.Label(data_frame, text="Wybierz powiat, aby sprawdzić dane.")
        self.data_status.pack(anchor="w")
        self.edit_button = ttk.Button(data_frame, text="Edytuj", command=self._enable_edit)
        self.edit_button.pack(anchor="e", pady=5)
        self.edit_button.pack_forget()

        self.data_entries = ttk.Frame(data_frame)
        self.url_var = tk.StringVar()
        self.login_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self._add_entry(self.data_entries, "URL", self.url_var)
        self._add_entry(self.data_entries, "Login", self.login_var)
        self._add_entry(self.data_entries, "Hasło", self.password_var, show="*")
        self.save_button = ttk.Button(data_frame, text="Zapisz", command=self._save_portal)
        self.retry_button = ttk.Button(data_frame, text="Zapisz i ponów", command=self._save_and_retry)

        number_frame = ttk.Labelframe(self.root, text="Numer GKN", padding=10)
        number_frame.pack(fill="x", padx=10, pady=5)
        self.number_var = tk.StringVar()
        self.number_entry = ttk.Entry(number_frame, textvariable=self.number_var, width=40)
        self.number_entry.pack(side="left", padx=5)
        self.start_button = ttk.Button(number_frame, text="START", command=self._start)
        self.start_button.pack(side="left", padx=5)
        self.debug_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            number_frame, text="DEBUG (screenshot po każdym kroku)", variable=self.debug_var
        ).pack(side="left", padx=10)

        status_frame = ttk.Labelframe(self.root, text="Status", padding=10)
        status_frame.pack(fill="x", padx=10, pady=5)
        self.last_step_var = tk.StringVar(value="-")
        self.message_var = tk.StringVar(value="-")
        self.found_var = tk.StringVar(value="-")
        self.screenshot_var = tk.StringVar(value="")

        ttk.Label(status_frame, text="Ostatni krok:").grid(row=0, column=0, sticky="w")
        ttk.Label(status_frame, textvariable=self.last_step_var).grid(row=0, column=1, sticky="w")
        ttk.Label(status_frame, text="Komunikat:").grid(row=1, column=0, sticky="w")
        ttk.Label(status_frame, textvariable=self.message_var).grid(row=1, column=1, sticky="w")
        ttk.Label(status_frame, text="Wynik:").grid(row=2, column=0, sticky="w")
        ttk.Label(status_frame, textvariable=self.found_var).grid(row=2, column=1, sticky="w")
        ttk.Label(status_frame, text="Screenshot:").grid(row=3, column=0, sticky="w")
        ttk.Label(status_frame, textvariable=self.screenshot_var).grid(row=3, column=1, sticky="w")

        self.open_screenshot_button = ttk.Button(
            status_frame, text="Otwórz screenshot", command=self._open_screenshot
        )
        self.open_screenshot_button.grid(row=4, column=1, sticky="w", pady=5)
        self.open_screenshot_button.state(["disabled"])

        actions_frame = ttk.Frame(self.root, padding=10)
        actions_frame.pack(fill="x")
        ttk.Button(
            actions_frame, text="Otwórz folder sesji", command=self._open_session_folder
        ).pack(side="left", padx=5)
        ttk.Button(
            actions_frame,
            text="Wyczyść tylko logi/screeny",
            command=self._clear_session_data,
        ).pack(side="left", padx=5)

        downloads_frame = ttk.Labelframe(self.root, text="Dane pobrane", padding=10)
        downloads_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(downloads_frame, text="Folder case (GKN):").grid(row=0, column=0, sticky="w")
        case_entry = ttk.Entry(
            downloads_frame, textvariable=self.case_dir_var, width=60, state="readonly"
        )
        case_entry.grid(row=0, column=1, sticky="w", padx=5)
        ttk.Button(
            downloads_frame,
            text="Otwórz folder danych (GKN)",
            command=self._open_case_folder,
        ).grid(row=1, column=0, sticky="w", pady=5)
        ttk.Button(
            downloads_frame, text="Otwórz meta.json", command=self._open_case_meta
        ).grid(row=1, column=1, sticky="w", pady=5)
        ttk.Button(
            downloads_frame,
            text="Otwórz polygon_coords.txt",
            command=self._open_case_polygon,
        ).grid(row=2, column=1, sticky="w", pady=5)
        ttk.Button(
            downloads_frame,
            text="Otwórz folder sesji",
            command=self._open_session_folder,
        ).grid(row=2, column=0, sticky="w", pady=5)

    def _add_entry(self, parent: ttk.Frame, label: str, variable: tk.StringVar, show: str | None = None) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=2)
        ttk.Label(row, text=label, width=10).pack(side="left")
        entry = ttk.Entry(row, textvariable=variable, show=show, width=50)
        entry.pack(side="left", fill="x", expand=True)

    def _focus_number(self) -> None:
        self.number_entry.focus_set()

    def _select_portal(self, key: str) -> None:
        self.portal_key = key
        if self.session_root:
            update_run_info(self.session_root, {"portal_key": key})
        self._refresh_portal_view()

    def _refresh_portal_view(self) -> None:
        if not self.portal_key:
            return
        portal_data = self.portals.get(self.portal_key)
        if portal_data and not self.edit_mode:
            self.data_status.configure(text="Dane zapisane.")
            self.data_entries.pack_forget()
            self.save_button.pack_forget()
            self.retry_button.pack_forget()
            self.edit_button.pack(anchor="e", pady=5)
        else:
            self.data_status.configure(text="Podaj URL, login i hasło.")
            self.url_var.set((portal_data or {}).get("url", ""))
            self.login_var.set((portal_data or {}).get("login", ""))
            self.password_var.set((portal_data or {}).get("password", ""))
            self.data_entries.pack(fill="x", pady=5)
            self.save_button.pack(anchor="e", pady=5)
            if self.pending_retry_number:
                self.retry_button.pack(anchor="e", pady=5)
            self.edit_button.pack_forget()

    def _enable_edit(self) -> None:
        self.edit_mode = True
        self._refresh_portal_view()

    def _save_portal(self) -> None:
        if not self.portal_key:
            return
        self.portals[self.portal_key] = {
            "url": self.url_var.get().strip(),
            "login": self.login_var.get().strip(),
            "password": self.password_var.get().strip(),
        }
        save_json(portals_path(), self.portals)
        self.edit_mode = False
        self._refresh_portal_view()

    def _save_and_retry(self) -> None:
        self._save_portal()
        if self.pending_retry_number:
            number = self.pending_retry_number
            self.pending_retry_number = None
            self._run_flow(number, retry=True)

    def _start(self) -> None:
        if not self.portal_key:
            messagebox.showwarning("F001", "Wybierz powiat.")
            return
        portal_data = self.portals.get(self.portal_key)
        if not portal_data or not portal_data.get("url"):
            self.edit_mode = True
            self._refresh_portal_view()
            messagebox.showwarning("F001", "Brak danych portalu. Uzupełnij pola.")
            return
        number = self.number_var.get().strip()
        if not number:
            messagebox.showwarning("F001", "Wpisz numer GKN.")
            return
        self._run_flow(number)

    def _run_flow(self, number: str, retry: bool = False) -> None:
        self.start_button.state(["disabled"])
        self.message_var.set("Uruchamianie...")
        self.last_step_var.set("-")
        self.found_var.set("-")
        self.screenshot_var.set("")
        self.open_screenshot_button.state(["disabled"])

        self.session_root = create_session(self.portal_key or "UNKNOWN", number)
        self.session_info = session_paths(self.session_root)
        run_data = load_json(self.session_info["run_path"], {})
        run_count = run_data.get("run_count", 0) + 1
        update_run_info(
            self.session_root,
            {
                "portal_key": self.portal_key,
                "last_number": number,
                "run_count": run_count,
            },
        )

        thread = threading.Thread(
            target=self._run_flow_thread,
            args=(number, retry),
            daemon=True,
        )
        thread.start()

    def _run_flow_thread(self, number: str, retry: bool) -> None:
        from automation.portal_runner import run_portal_flow

        portal_data = self.portals.get(self.portal_key, {}) if self.portal_key else {}
        result = run_portal_flow(
            number,
            portal_data,
            self.selectors,
            self.session_info,
            debug=self.debug_var.get(),
        )
        update_run_info(
            self.session_root,
            {
                "last_status": result.status,
                "last_step": result.last_step,
            },
        )
        self.root.after(0, lambda: self._handle_result(result, number, retry))

    def _handle_result(self, result, number: str, retry: bool) -> None:
        self.start_button.state(["!disabled"])
        self.last_step_var.set(result.last_step)
        self.message_var.set(result.message)
        self.found_var.set("ZNALEZIONO" if result.found else "NIE ZNALEZIONO")
        if result.screenshot_path:
            self.screenshot_var.set(result.screenshot_path)
            self.open_screenshot_button.state(["!disabled"])
        else:
            self.screenshot_var.set("")
            self.open_screenshot_button.state(["disabled"])

        if result.status == "password_error" and not retry:
            self.password_retry = True
            self.pending_retry_number = number
            self.edit_mode = True
            self.message_var.set("Błędne hasło. Wpisz nowe i kliknij 'Zapisz i ponów'.")
            self._refresh_portal_view()
            return

        self.password_retry = False
        self.pending_retry_number = None

        if result.case_dir:
            self._set_case_dir(result.case_dir, result.case_files or [])
            if result.case_files:
                key_files = ", ".join(Path(path).name for path in result.case_files)
                self.message_var.set(f"Zapisano dane do: {result.case_dir} ({key_files})")
            else:
                self.message_var.set(f"Zapisano dane do: {result.case_dir}")

    def _open_screenshot(self) -> None:
        path = self.screenshot_var.get().strip()
        if path:
            _open_path(path)

    def _open_session_folder(self) -> None:
        session = read_latest_session()
        if session:
            _open_path(session)

    def _open_case_folder(self) -> None:
        case_dir = self.case_dir_var.get().strip()
        if case_dir:
            _open_path(case_dir)

    def _open_case_meta(self) -> None:
        case_dir = self.case_dir_var.get().strip()
        if case_dir:
            _open_path(os.path.join(case_dir, "meta.json"))

    def _open_case_polygon(self) -> None:
        case_dir = self.case_dir_var.get().strip()
        if case_dir:
            _open_path(os.path.join(case_dir, "polygon_coords.txt"))

    def _set_case_dir(self, case_dir: str, files: list[str]) -> None:
        self.case_dir_var.set(case_dir)
        self.panel_state["last_case_dir"] = case_dir
        self.panel_state["last_case_files"] = files
        save_json(self.state_path, self.panel_state)

    def _clear_session_data(self) -> None:
        if not messagebox.askyesno("F001", "Usunąć tylko logi i screeny z sesji?"):
            return
        clear_sessions()
        messagebox.showinfo("F001", "Sesje wyczyszczone.")


def main() -> None:
    root = tk.Tk()
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")
    F001Panel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
