"""Saved records - search past inspections and open the detail of one."""

import os
import tkinter as tk
from tkinter import ttk

import database
import theme
import widgets
from screens.checksheet_screen import BASE_DIR, open_file


class RecordsScreen(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()
        self.reload()

    def _build(self):
        def back_btn(parent):
            ttk.Button(parent, text="Back to sheets",
                       command=self.app.show_select).pack(side="left")

        widgets.header_bar(self, "Saved records",
                           "Search and review completed inspections",
                           [back_btn])

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=24, pady=(18, 16))

        bar = ttk.Frame(body)
        bar.pack(fill="x", pady=(0, 12))

        ttk.Label(bar, text="Search").pack(side="left", padx=(0, 8))
        self.search_var = tk.StringVar()
        entry = ttk.Entry(bar, textvariable=self.search_var, width=28,
                          font=(theme.FONT, 10))
        entry.pack(side="left", ipady=2)
        entry.bind("<Return>", lambda _e: self.reload())

        ttk.Label(bar, text="Sheet").pack(side="left", padx=(16, 8))
        self.sheet_var = tk.StringVar(value="All sheets")
        options = ["All sheets"] + [s.name for s in
                                    self.app.checksheets.values()]
        combo = ttk.Combobox(bar, textvariable=self.sheet_var, values=options,
                             state="readonly", width=24)
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", lambda _e: self.reload())

        ttk.Button(bar, text="Apply", command=self.reload).pack(
            side="left", padx=(10, 0))
        ttk.Button(bar, text="Clear", command=self.clear).pack(
            side="left", padx=(6, 0))

        cols = ("id", "saved_at", "sheet", "serial", "board", "operator",
                "overall", "tally")
        self.tree = ttk.Treeview(body, columns=cols, show="headings",
                                 selectmode="browse")
        headings = {
            "id": ("#", 55), "saved_at": ("Saved", 145),
            "sheet": ("Check sheet", 180), "serial": ("Serial", 140),
            "board": ("Main board", 140), "operator": ("Inspector", 140),
            "overall": ("Overall", 80), "tally": ("OK / NG / RW", 110),
        }
        for col, (text, width) in headings.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width,
                             anchor="center" if col in ("id", "overall",
                                                        "tally") else "w")

        yscroll = ttk.Scrollbar(body, orient="vertical",
                                command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        yscroll.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        self.tree.tag_configure("OK", foreground=theme.OK_COLOR)
        self.tree.tag_configure("NG", foreground=theme.NG_COLOR)
        self.tree.tag_configure("RW", foreground=theme.RW_COLOR)
        self.tree.bind("<Double-1>", lambda _e: self.open_detail())

        footer = ttk.Frame(body)
        footer.pack(fill="x", pady=(12, 0))
        self.count_label = ttk.Label(footer, text="", style="Muted.TLabel")
        self.count_label.pack(side="left")
        ttk.Button(footer, text="Open record", style="Primary.TButton",
                   command=self.open_detail).pack(side="right")

    def clear(self):
        self.search_var.set("")
        self.sheet_var.set("All sheets")
        self.reload()

    def reload(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        key = ""
        chosen = self.sheet_var.get()
        for k, sheet in self.app.checksheets.items():
            if sheet.name == chosen:
                key = k
                break

        rows = database.list_inspections(self.search_var.get(), key)
        for r in rows:
            tally = f"{r['ok_count']} / {r['ng_count']} / {r['rw_count']}"
            self.tree.insert(
                "", "end", iid=str(r["id"]),
                values=(r["id"], r["saved_at"].replace("T", "  "),
                        r["checksheet_name"], r["serial_number"],
                        r["main_board_no"], r["operator_name"],
                        r["overall_result"], tally),
                tags=(r["overall_result"],))
        self.count_label.configure(text=f"{len(rows)} record(s) found")

    def open_detail(self):
        selected = self.tree.focus()
        if not selected:
            return
        RecordDetail(self, int(selected))


class RecordDetail(tk.Toplevel):
    def __init__(self, parent, insp_id):
        super().__init__(parent)
        head, rows = database.get_inspection(insp_id)
        if head is None:
            self.destroy()
            return

        self.title(f"Record #{insp_id} - {head['serial_number']}")
        self.geometry("880x600")
        self.configure(bg=theme.BG)
        self.transient(parent.winfo_toplevel())

        top = tk.Frame(self, bg=theme.HEADER)
        top.pack(fill="x")
        inner = tk.Frame(top, bg=theme.HEADER)
        inner.pack(fill="x", padx=20, pady=12)
        tk.Label(inner, text=head["checksheet_name"], bg=theme.HEADER,
                 fg="#FFFFFF", font=(theme.FONT, 14, "bold")).pack(anchor="w")
        tk.Label(inner,
                 text=(f"Serial {head['serial_number']}   |   Main board "
                       f"{head['main_board_no']}   |   {head['operator_name']}"
                       f"   |   {head['saved_at'].replace('T', '  ')}"),
                 bg=theme.HEADER, fg="#9DB0C0",
                 font=(theme.FONT, 9)).pack(anchor="w", pady=(3, 0))

        summary = tk.Frame(self, bg=theme.BG)
        summary.pack(fill="x", padx=20, pady=(14, 8))
        colour = theme.RESULT_COLORS.get(head["overall_result"], theme.MUTED)
        tk.Label(summary, text=f"Overall: {head['overall_result']}",
                 bg=theme.BG, fg=colour,
                 font=(theme.FONT, 12, "bold")).pack(side="left")
        tk.Label(summary,
                 text=(f"OK {head['ok_count']}    NG {head['ng_count']}"
                       f"    RW {head['rw_count']}    of {head['total_tests']}"
                       " tests"),
                 bg=theme.BG, fg=theme.MUTED,
                 font=(theme.FONT, 10)).pack(side="left", padx=(18, 0))

        scroll = widgets.ScrollFrame(self, bg=theme.BORDER)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 18))
        scroll.body.columnconfigure(0, weight=1)

        for i, r in enumerate(rows):
            bg = theme.SURFACE if i % 2 == 0 else theme.SURFACE_ALT
            line = tk.Frame(scroll.body, bg=bg)
            line.grid(row=i, column=0, sticky="ew", pady=(0, 1))
            line.columnconfigure(1, weight=3)
            line.columnconfigure(3, weight=2)

            res_colour = theme.RESULT_COLORS.get(r["result"], theme.MUTED)
            tk.Frame(line, bg=res_colour, width=4).grid(row=0, column=0,
                                                        sticky="ns")
            tk.Label(line, text=f"{r['test_order']}. {r['test_name']}", bg=bg,
                     fg=theme.INK, font=(theme.FONT, 10), anchor="w",
                     wraplength=300, justify="left").grid(
                row=0, column=1, sticky="w", padx=(12, 8), pady=9)
            tk.Label(line, text=r["result"], bg=bg, fg=res_colour,
                     font=(theme.FONT, 10, "bold"), width=5).grid(
                row=0, column=2, padx=6)
            tk.Label(line, text=r["reason"] or "-", bg=bg, fg=theme.MUTED,
                     font=(theme.FONT, 9), anchor="w", wraplength=260,
                     justify="left").grid(row=0, column=3, sticky="w", padx=6)

            abs_path = os.path.join(BASE_DIR, r["photo_path"])
            exists = bool(r["photo_path"]) and os.path.exists(abs_path)
            btn = tk.Button(
                line, text="Open photo" if exists else "photo missing",
                relief="flat", bd=0, bg=bg,
                fg=theme.PRIMARY if exists else theme.MUTED,
                font=(theme.FONT, 9, "underline" if exists else "normal"),
                cursor="hand2" if exists else "arrow",
                state="normal" if exists else "disabled",
                activebackground=bg,
                command=lambda p=abs_path: open_file(p))
            btn.grid(row=0, column=4, padx=(6, 12))
