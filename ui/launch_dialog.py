import tkinter as tk
from tkinter import ttk

from ui.style import BACKGROUND_COLOR


class LaunchDialog(tk.Toplevel):
    """Pick how to start a game that has several runnable versions (WHDLoad, disks, SPS)."""

    def __init__(self, parent, game, options):
        super().__init__(parent)
        self.title("Launch")
        self.configure(background=BACKGROUND_COLOR)
        self.transient(parent)
        self.resizable(False, False)
        self.options = options
        self.choice = None

        body = ttk.Frame(self, padding=12)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=f"{game.title}\n{len(options)} ways to start it:",
                  justify="left").pack(anchor="w", pady=(0, 6))
        self.listbox = tk.Listbox(body, height=min(len(options), 12), width=70, activestyle="dotbox",
                                  exportselection=False)
        for option in options:
            self.listbox.insert("end", option.label)
        self.listbox.selection_set(0)
        self.listbox.pack(fill="both", expand=True)
        bar = ttk.Frame(body)
        bar.pack(fill="x", pady=(10, 0))
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(bar, text="Launch", command=self._launch).pack(side="right", padx=(0, 5))
        self.listbox.bind("<Double-1>", lambda _e: self._launch())
        self.bind("<Return>", lambda _e: self._launch())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.listbox.focus_set()
        self.grab_set()

    def _launch(self):
        sel = self.listbox.curselection()
        if sel:
            self.choice = self.options[sel[0]]
        self.destroy()

    def show(self):
        """Wait for the dialog to close; returns the chosen LaunchOption or None."""
        self.wait_window()
        return self.choice
