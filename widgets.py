"""Small reusable widgets shared by the screens."""

import tkinter as tk
from tkinter import ttk

import theme


class ScrollFrame(ttk.Frame):
    """A vertically scrollable container. Put content in `.body`."""

    def __init__(self, parent, bg=theme.BG, **kwargs):
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical",
                                       command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.body = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.body,
                                              anchor="nw")

        self.body.bind("<Configure>", self._on_body_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def _on_body_configure(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfigure(self._win, width=event.width)

    def _bind_wheel(self, _event):
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)
        self.canvas.bind_all("<Button-4>", self._on_wheel)
        self.canvas.bind_all("<Button-5>", self._on_wheel)

    def _unbind_wheel(self, _event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_wheel(self, event):
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1
        self.canvas.yview_scroll(delta, "units")


def header_bar(parent, title, subtitle="", right_widgets=None):
    """Dark bar across the top of a screen."""
    bar = ttk.Frame(parent, style="Header.TFrame")
    bar.pack(fill="x")

    inner = ttk.Frame(bar, style="Header.TFrame")
    inner.pack(fill="x", padx=22, pady=12)

    left = ttk.Frame(inner, style="Header.TFrame")
    left.pack(side="left")
    ttk.Label(left, text=title, style="HeaderTitle.TLabel").pack(anchor="w")
    if subtitle:
        ttk.Label(left, text=subtitle,
                  style="HeaderMuted.TLabel").pack(anchor="w", pady=(2, 0))

    right = ttk.Frame(inner, style="Header.TFrame")
    right.pack(side="right")
    if right_widgets:
        for builder in right_widgets:
            builder(right)
    return bar, right


def flat_button(parent, text, command, bg, fg="#FFFFFF", width=None,
                font=None, state="normal"):
    """A solid coloured tk.Button (ttk ignores background on Windows)."""
    btn = tk.Button(
        parent, text=text, command=command, bg=bg, fg=fg,
        activebackground=bg, activeforeground=fg, relief="flat", bd=0,
        font=font or (theme.FONT, 10, "bold"), cursor="hand2",
        padx=14, pady=7, state=state,
        disabledforeground="#FFFFFF",
    )
    if width:
        btn.configure(width=width)
    return btn
