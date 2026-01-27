from __future__ import annotations

import json
import os
import tkinter as tk

import dispatcher


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config_buttons.json")
COLUMNS = 6


def load_buttons() -> list[str]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as config_file:
        data = json.load(config_file)
    return list(data.get("buttons", []))


def build_panel(root: tk.Tk, buttons: list[str]) -> None:
    for index, button_id in enumerate(buttons):
        row = index // COLUMNS
        column = index % COLUMNS
        button = tk.Button(
            root,
            text=button_id,
            width=10,
            height=2,
            command=lambda value=button_id: dispatcher.handle(value),
        )
        button.grid(row=row, column=column, padx=5, pady=5, sticky="nsew")

    for column in range(COLUMNS):
        root.grid_columnconfigure(column, weight=1)


def main() -> None:
    root = tk.Tk()
    root.title("Panel F")
    buttons = load_buttons()
    build_panel(root, buttons)
    root.mainloop()


if __name__ == "__main__":
    main()
