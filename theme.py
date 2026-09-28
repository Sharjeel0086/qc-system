"""Visual constants and ttk style setup for the QC Cross-Check System."""

from tkinter import ttk

# --- Palette -------------------------------------------------------------
BG = "#EEF1F4"          # app background
SURFACE = "#FFFFFF"     # cards, rows, forms
SURFACE_ALT = "#F6F8FA"  # alternating row
INK = "#14202B"         # primary text
MUTED = "#6B7A88"       # secondary text
BORDER = "#CBD5DD"
PRIMARY = "#1D4E89"     # industrial blue
PRIMARY_DARK = "#163C6B"
HEADER = "#14202B"

# Result colours
OK_COLOR = "#1B8A4B"
NG_COLOR = "#C0392B"
RW_COLOR = "#D98200"
DISABLED = "#B7C1CA"

RESULT_COLORS = {"OK": OK_COLOR, "NG": NG_COLOR, "RW": RW_COLOR}

# --- Type ----------------------------------------------------------------
FONT = "Segoe UI"
F_TITLE = (FONT, 20, "bold")
F_HEAD = (FONT, 14, "bold")
F_SUB = (FONT, 11)
F_BODY = (FONT, 10)
F_SMALL = (FONT, 9)
F_MONO = ("Consolas", 10)


def apply_styles(root):
    """Configure ttk styles once, at start-up."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(".", background=BG, foreground=INK, font=F_BODY)
    style.configure("TFrame", background=BG)
    style.configure("Surface.TFrame", background=SURFACE)
    style.configure("Header.TFrame", background=HEADER)
    style.configure("Row.TFrame", background=SURFACE)
    style.configure("RowAlt.TFrame", background=SURFACE_ALT)

    style.configure("TLabel", background=BG, foreground=INK, font=F_BODY)
    style.configure("Surface.TLabel", background=SURFACE, foreground=INK)
    style.configure("Title.TLabel", font=F_TITLE, background=BG, foreground=INK)
    style.configure("Head.TLabel", font=F_HEAD, background=BG, foreground=INK)
    style.configure("Muted.TLabel", font=F_SMALL, background=BG, foreground=MUTED)
    style.configure("HeaderTitle.TLabel", font=F_HEAD, background=HEADER,
                    foreground="#FFFFFF")
    style.configure("HeaderMuted.TLabel", font=F_SMALL, background=HEADER,
                    foreground="#9DB0C0")
    style.configure("ColHead.TLabel", font=(FONT, 9, "bold"), background=BG,
                    foreground=MUTED)

    style.configure("TEntry", fieldbackground=SURFACE, bordercolor=BORDER,
                    padding=5)
    style.configure("TCombobox", fieldbackground=SURFACE, padding=4)

    style.configure("TButton", font=F_BODY, padding=(12, 7), borderwidth=0,
                    background="#DEE4EA", foreground=INK)
    style.map("TButton", background=[("active", "#CCD5DD")])

    style.configure("Primary.TButton", background=PRIMARY, foreground="#FFFFFF",
                    font=(FONT, 10, "bold"), padding=(16, 9))
    style.map("Primary.TButton",
              background=[("active", PRIMARY_DARK), ("disabled", DISABLED)])

    style.configure("Ghost.TButton", background=BG, foreground=PRIMARY,
                    padding=(8, 5))
    style.map("Ghost.TButton", background=[("active", "#E2E8EE")])

    style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE,
                    rowheight=26, font=F_BODY)
    style.configure("Treeview.Heading", font=(FONT, 9, "bold"),
                    background="#DEE4EA")

    return style
