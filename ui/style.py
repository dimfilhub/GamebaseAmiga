from tkinter import ttk

BACKGROUND_COLOR = "#0055aa"  # Workbench 1.x blue, as in AmigaExec
TEXT_COLOR = "#ffffff"
LINK_COLOR = "#ff8800"  # Workbench orange
DARK_BLUE = "#003377"
LIGHT_BLUE = "#3377cc"
DISABLED_TEXT = "#7fa6d4"
QUIT_COLOR = "#c62828"


class AppStyle:
    """clam has fixed light colours; the native macOS theme follows system dark mode."""

    def __init__(self, root):
        self.root = root

    def apply(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        bg = BACKGROUND_COLOR
        self.root.configure(background=bg)
        for name in ("TFrame", "TLabel", "TPanedwindow", "TNotebook", "TLabelframe",
                     "TLabelframe.Label", "TRadiobutton", "TCheckbutton"):
            style.configure(name, background=bg, foreground=TEXT_COLOR)
        style.map("TCheckbutton", background=[("active", bg)], foreground=[("active", TEXT_COLOR)])
        style.map("TRadiobutton", background=[("active", bg)], foreground=[("active", TEXT_COLOR)])
        style.configure("TNotebook", background=bg, bordercolor="white")
        style.configure("TNotebook.Tab", background=DARK_BLUE, foreground="white", padding=(14, 4))
        style.map("TNotebook.Tab", background=[("selected", LIGHT_BLUE)],
                  foreground=[("selected", "white")])
        style.configure("TButton", background=bg, foreground="white", bordercolor="white",
                        lightcolor=bg, darkcolor=bg, focuscolor=bg)
        style.map("TButton", background=[("active", LIGHT_BLUE), ("disabled", bg)],
                  foreground=[("disabled", DISABLED_TEXT)])
        style.configure("TEntry", fieldbackground="white", foreground="blue")
        style.configure("TCombobox", fieldbackground="white", foreground="black")
        style.configure("Treeview", background="white", fieldbackground="white", foreground="black")
        style.map("Treeview", background=[("selected", "#0078d7")],
                  foreground=[("selected", "white")])
        style.configure("Treeview.Heading", foreground="blue")
        style.configure("quit.TButton", background=QUIT_COLOR, lightcolor=QUIT_COLOR,
                        darkcolor=QUIT_COLOR, focuscolor=QUIT_COLOR)
        style.map("quit.TButton", background=[("active", "#e53935"), ("disabled", QUIT_COLOR)])
