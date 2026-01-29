from __future__ import annotations

import tkinter as tk

from LAUNCHER_panel import LauncherPanel


def main() -> None:
    root = tk.Tk()
    LauncherPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
