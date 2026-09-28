"""Step 2 - choose which checksheet to run."""

import tkinter as tk
from tkinter import ttk

import theme
import widgets


class SelectScreen(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        user = self.app.current_user
        name = user["full_name"] or user["username"]

        def builder_btn(parent):
            if user["role"] == "admin":
                ttk.Button(parent, text="Check sheet builder",
                           command=self.app.show_builder).pack(side="left",
                                                               padx=(0, 8))

        def records_btn(parent):
            ttk.Button(parent, text="Saved records",
                       command=self.app.show_records).pack(side="left",
                                                           padx=(0, 8))

        def logout_btn(parent):
            ttk.Button(parent, text="Sign out",
                       command=self.app.logout).pack(side="left")

        widgets.header_bar(
            self, "Quality Cross-Check System",
            f"Signed in as {name} ({user['role']})",
            [builder_btn, records_btn, logout_btn],
        )

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=28, pady=(24, 10))

        ttk.Label(body, text="Select a check sheet",
                  style="Title.TLabel").pack(anchor="w")
        ttk.Label(body, text="Click a sheet to start a new inspection.",
                  style="Muted.TLabel").pack(anchor="w", pady=(4, 20))

        scroll = widgets.ScrollFrame(body)
        scroll.pack(fill="both", expand=True)

        grid = scroll.body
        grid.columnconfigure((0, 1, 2), weight=1, uniform="tile")

        for idx, (key, sheet) in enumerate(self.app.checksheets.items()):
            self._tile(grid, key, sheet).grid(
                row=idx // 3, column=idx % 3, sticky="nsew", padx=8, pady=8)

    def _tile(self, parent, key, sheet):
        card = tk.Frame(parent, bg=theme.SURFACE, cursor="hand2",
                        highlightbackground=theme.BORDER, highlightthickness=1)

        inner = tk.Frame(card, bg=theme.SURFACE)
        inner.pack(fill="both", expand=True, padx=20, pady=18)

        tk.Label(inner, text=key, bg=theme.SURFACE, fg=theme.PRIMARY,
                 font=(theme.FONT, 9, "bold")).pack(anchor="w")
        tk.Label(inner, text=sheet.name, bg=theme.SURFACE, fg=theme.INK,
                 font=(theme.FONT, 14, "bold"), wraplength=240,
                 justify="left").pack(anchor="w", pady=(4, 2))
        if sheet.subtitle:
            tk.Label(inner, text=sheet.subtitle, bg=theme.SURFACE,
                     fg=theme.MUTED, font=(theme.FONT, 9), wraplength=240,
                     justify="left").pack(anchor="w")
        scan_note = (f"{len(sheet.scan_targets)} scan step(s)"
                     if sheet.scan_targets else "manual entry")
        tk.Label(inner, text=f"{sheet.test_count} tests   |   {scan_note}",
                 bg=theme.SURFACE, fg=theme.MUTED,
                 font=(theme.FONT, 9)).pack(anchor="w", pady=(12, 0))

        def open_sheet(_event=None):
            self.app.show_details(key)

        def enter(_event):
            card.configure(highlightbackground=theme.PRIMARY,
                           highlightthickness=2)

        def leave(_event):
            card.configure(highlightbackground=theme.BORDER,
                           highlightthickness=1)

        for w in (card, inner, *inner.winfo_children()):
            w.bind("<Button-1>", open_sheet)
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)
        return card
