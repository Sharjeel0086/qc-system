"""Check sheet builder - add and edit check sheets from inside the program.

Everything the inspection flow uses is editable here: the sheet name and
code, the unit detail fields, the list of tests, and the scanner rules.
Saving writes data/checksheets.json and keeps a timestamped backup.
"""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import config_loader
import scanning
import theme
import widgets
from config_loader import Checksheet, ScanTarget, UnitField


class BuilderScreen(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.sheets = {k: Checksheet(k, s.to_dict())
                       for k, s in app.checksheets.items()}
        self.order = list(self.sheets)
        self.current_key = None
        self.dirty = False
        self._loading = False
        self._build()
        if self.order:
            self.sheet_list.selection_set(0)
            self._on_sheet_selected()

    # --- layout ----------------------------------------------------------
    def _build(self):
        def back_btn(parent):
            ttk.Button(parent, text="Close builder",
                       command=self.close).pack(side="left")

        widgets.header_bar(self, "Check sheet builder",
                           "Add check sheets, tests and scanner rules",
                           [back_btn])

        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True, padx=20, pady=(16, 10))

        left = ttk.Frame(outer)
        left.pack(side="left", fill="y", padx=(0, 18))
        ttk.Label(left, text="Check sheets", style="Head.TLabel").pack(
            anchor="w", pady=(0, 8))

        self.sheet_list = tk.Listbox(left, width=26, height=20,
                                     font=(theme.FONT, 10), bd=0,
                                     highlightthickness=1,
                                     highlightbackground=theme.BORDER,
                                     activestyle="none",
                                     selectbackground=theme.PRIMARY,
                                     selectforeground="#FFFFFF")
        self.sheet_list.pack(fill="y", expand=True)
        self.sheet_list.bind("<<ListboxSelect>>",
                             lambda _e: self._on_sheet_selected())

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(10, 0))
        for text, cmd in (("New", self.new_sheet),
                          ("Copy", self.duplicate_sheet),
                          ("Delete", self.delete_sheet)):
            ttk.Button(btns, text=text, command=cmd).pack(side="left",
                                                          padx=(0, 5))

        right = ttk.Frame(outer)
        right.pack(side="left", fill="both", expand=True)

        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        self.tab_general = ttk.Frame(self.notebook)
        self.tab_fields = ttk.Frame(self.notebook)
        self.tab_tests = ttk.Frame(self.notebook)
        self.tab_scan = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_general, text="  General  ")
        self.notebook.add(self.tab_fields, text="  Unit fields  ")
        self.notebook.add(self.tab_tests, text="  Tests  ")
        self.notebook.add(self.tab_scan, text="  Scanning  ")

        self._build_general()
        self._build_fields()
        self._build_tests()
        self._build_scan()

        footer = ttk.Frame(self)
        footer.pack(fill="x", padx=20, pady=(0, 14))
        self.status = ttk.Label(footer, text="", style="Muted.TLabel")
        self.status.pack(side="left")
        ttk.Button(footer, text="Save all check sheets",
                   style="Primary.TButton",
                   command=self.save_all).pack(side="right")
        ttk.Button(footer, text="Discard changes",
                   command=self.discard).pack(side="right", padx=(0, 8))

        self._refresh_sheet_list()

    def _build_general(self):
        pad = ttk.Frame(self.tab_general)
        pad.pack(fill="both", expand=True, padx=22, pady=20)
        pad.columnconfigure(1, weight=1)

        self.key_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.subtitle_var = tk.StringVar()

        # Short code needs an explicit Apply: renaming on every keystroke
        # would try to use invalid or half-typed codes and reshuffle the
        # sheet list while the person is still typing.
        ttk.Label(pad, text="Short code").grid(row=0, column=0, sticky="w")
        key_row = ttk.Frame(pad)
        key_row.grid(row=0, column=1, sticky="ew", padx=(14, 0))
        key_row.columnconfigure(0, weight=1)
        key_entry = ttk.Entry(key_row, textvariable=self.key_var,
                              font=(theme.FONT, 11))
        key_entry.grid(row=0, column=0, sticky="ew", ipady=3)
        ttk.Button(key_row, text="Apply code change",
                  command=self._apply_key_change).grid(row=0, column=1,
                                                        padx=(8, 0))
        ttk.Label(pad, text="Shown on the tile and used in photo folder "
                            "names, e.g. OQC. Click \"Apply code change\" "
                            "after editing this box.",
                  style="Muted.TLabel").grid(row=1, column=1, sticky="w",
                                             padx=(14, 0))
        self.key_status = tk.Label(pad, text="", bg=theme.BG,
                                   font=(theme.FONT, 8), anchor="w")
        self.key_status.grid(row=2, column=1, sticky="w", padx=(14, 0),
                             pady=(2, 0))

        # Name and subtitle apply as you type - no button needed.
        ttk.Label(pad, text="Check sheet name").grid(row=3, column=0,
                                                      sticky="w",
                                                      pady=(16, 4))
        name_entry = ttk.Entry(pad, textvariable=self.name_var,
                               font=(theme.FONT, 11))
        name_entry.grid(row=3, column=1, sticky="ew", pady=(16, 4),
                        padx=(14, 0), ipady=3)
        ttk.Label(pad, text="The full name the inspector sees, e.g. OQC "
                            "Check Sheet. Saved as you type.",
                  style="Muted.TLabel").grid(row=4, column=1, sticky="w",
                                             padx=(14, 0))

        ttk.Label(pad, text="Subtitle").grid(row=5, column=0, sticky="w",
                                             pady=(16, 4))
        subtitle_entry = ttk.Entry(pad, textvariable=self.subtitle_var,
                                   font=(theme.FONT, 11))
        subtitle_entry.grid(row=5, column=1, sticky="ew", pady=(16, 4),
                            padx=(14, 0), ipady=3)
        ttk.Label(pad, text="One short line of context. Optional. Saved as "
                            "you type.", style="Muted.TLabel").grid(
            row=6, column=1, sticky="w", padx=(14, 0))

        self.name_var.trace_add("write", self._apply_name_live)
        self.subtitle_var.trace_add("write", self._apply_subtitle_live)

        self.summary = ttk.Label(pad, text="", style="Muted.TLabel",
                                 justify="left")
        self.summary.grid(row=99, column=0, columnspan=2, sticky="w",
                          pady=(28, 0))

    def _apply_name_live(self, *_a):
        if self._loading or self.sheet is None:
            return
        self.sheet.name = self.name_var.get()
        self._mark_dirty()

    def _apply_subtitle_live(self, *_a):
        if self._loading or self.sheet is None:
            return
        self.sheet.subtitle = self.subtitle_var.get()
        self._mark_dirty()

    def _apply_key_change(self):
        if self.sheet is None:
            return
        old_key = self.current_key
        new_key = self.key_var.get().strip()
        if not new_key:
            self.key_status.configure(text="The code cannot be empty.",
                                      fg=theme.NG_COLOR)
            return
        if new_key == old_key:
            self.key_status.configure(text="", fg=theme.MUTED)
            return
        if not config_loader.SHEET_KEY_RE.match(new_key):
            self.key_status.configure(
                text="Use 1-16 letters, digits, '-' or '_', starting with a "
                     "letter or digit.", fg=theme.NG_COLOR)
            return
        if new_key in self.sheets:
            self.key_status.configure(
                text=f"'{new_key}' is already used by another check sheet.",
                fg=theme.NG_COLOR)
            return

        sheet = self.sheets.pop(old_key)
        sheet.key = new_key
        self.sheets[new_key] = sheet
        index = self.order.index(old_key)
        self.order[index] = new_key
        self.current_key = new_key
        self._mark_dirty()
        self.key_status.configure(text=f"Code updated to '{new_key}'.",
                                  fg=theme.OK_COLOR)
        self._refresh_sheet_list(new_key)

    def _build_fields(self):
        pad = ttk.Frame(self.tab_fields)
        pad.pack(fill="both", expand=True, padx=22, pady=18)

        ttk.Label(pad, text="Details the inspector fills in (or scans) before "
                            "the tests open. Serial number and main board "
                            "number are always present.",
                  style="Muted.TLabel", wraplength=720).pack(anchor="w",
                                                             pady=(0, 10))

        fields_wrap = ttk.Frame(pad)
        fields_wrap.pack(fill="both", expand=True)
        self.fields_tree = ttk.Treeview(
            fields_wrap, columns=("label", "id", "required", "scan"),
            show="headings", height=12, selectmode="browse")
        for col, text, width in (("label", "Label", 240),
                                 ("id", "Field id", 180),
                                 ("required", "Required", 90),
                                 ("scan", "Filled by scan", 140)):
            self.fields_tree.heading(col, text=text)
            self.fields_tree.column(
                col, width=width,
                anchor="center" if col in ("required", "scan") else "w")
        fields_scroll = ttk.Scrollbar(fields_wrap, orient="vertical",
                                      command=self.fields_tree.yview)
        self.fields_tree.configure(yscrollcommand=fields_scroll.set)
        fields_scroll.pack(side="right", fill="y")
        self.fields_tree.pack(side="left", fill="both", expand=True)
        self.fields_tree.bind("<Double-1>", lambda _e: self.edit_field())

        bar = ttk.Frame(pad)
        bar.pack(fill="x", pady=(10, 0))
        for text, cmd in (("Add field", self.add_field),
                          ("Edit", self.edit_field),
                          ("Remove", self.remove_field),
                          ("Move up", lambda: self.move_field(-1)),
                          ("Move down", lambda: self.move_field(1))):
            ttk.Button(bar, text=text, command=cmd).pack(side="left",
                                                         padx=(0, 6))

    def _build_tests(self):
        pad = ttk.Frame(self.tab_tests)
        pad.pack(fill="both", expand=True, padx=22, pady=18)

        head = ttk.Frame(pad)
        head.pack(fill="x", pady=(0, 10))
        ttk.Label(head, text="These appear as the rows of the check sheet, in "
                             "this order.", style="Muted.TLabel").pack(
            side="left")
        self.test_count_label = ttk.Label(head, text="", style="Muted.TLabel")
        self.test_count_label.pack(side="right")

        wrap = ttk.Frame(pad)
        wrap.pack(fill="both", expand=True)
        self.tests_list = tk.Listbox(wrap, font=(theme.FONT, 10), bd=0,
                                     highlightthickness=1,
                                     highlightbackground=theme.BORDER,
                                     activestyle="none",
                                     selectbackground=theme.PRIMARY,
                                     selectforeground="#FFFFFF")
        scroll = ttk.Scrollbar(wrap, orient="vertical",
                               command=self.tests_list.yview)
        self.tests_list.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tests_list.pack(side="left", fill="both", expand=True)
        self.tests_list.bind("<Double-1>", lambda _e: self.edit_test())

        bar = ttk.Frame(pad)
        bar.pack(fill="x", pady=(10, 0))
        for text, cmd in (("Add test", self.add_test),
                          ("Edit", self.edit_test),
                          ("Remove", self.remove_test),
                          ("Move up", lambda: self.move_test(-1)),
                          ("Move down", lambda: self.move_test(1))):
            ttk.Button(bar, text=text, command=cmd).pack(side="left",
                                                         padx=(0, 6))
        ttk.Button(bar, text="Paste a whole list...", style="Primary.TButton",
                   command=self.bulk_tests).pack(side="right")

    def _build_scan(self):
        pad = ttk.Frame(self.tab_scan)
        pad.pack(fill="both", expand=True, padx=22, pady=18)

        ttk.Label(pad, text="Each step is one code the inspector scans. A "
                            "single QR code can fill several fields at once.",
                  style="Muted.TLabel", wraplength=720).pack(anchor="w",
                                                             pady=(0, 10))

        scan_wrap = ttk.Frame(pad)
        scan_wrap.pack(fill="both", expand=True)
        self.scan_tree = ttk.Treeview(
            scan_wrap, columns=("label", "rule", "fills"), show="headings",
            height=8, selectmode="browse")
        for col, text, width in (("label", "Scan step", 220),
                                 ("rule", "How it is read", 250),
                                 ("fills", "Fills these fields", 280)):
            self.scan_tree.heading(col, text=text)
            self.scan_tree.column(col, width=width, anchor="w")
        scan_scroll = ttk.Scrollbar(scan_wrap, orient="vertical",
                                    command=self.scan_tree.yview)
        self.scan_tree.configure(yscrollcommand=scan_scroll.set)
        scan_scroll.pack(side="right", fill="y")
        self.scan_tree.pack(side="left", fill="both", expand=True)
        self.scan_tree.bind("<Double-1>", lambda _e: self.edit_scan())

        bar = ttk.Frame(pad)
        bar.pack(fill="x", pady=(10, 0))
        for text, cmd in (("Add scan step", self.add_scan),
                          ("Edit", self.edit_scan),
                          ("Remove", self.remove_scan),
                          ("Move up", lambda: self.move_scan(-1)),
                          ("Move down", lambda: self.move_scan(1))):
            ttk.Button(bar, text=text, command=cmd).pack(side="left",
                                                         padx=(0, 6))

    # --- sheet selection -------------------------------------------------
    @property
    def sheet(self):
        return self.sheets.get(self.current_key)

    def _refresh_sheet_list(self, select_key=None):
        self._loading = True
        self.sheet_list.delete(0, "end")
        for key in self.order:
            sheet = self.sheets[key]
            self.sheet_list.insert("end",
                                   f"{key}  -  {sheet.test_count} tests")
        if select_key and select_key in self.order:
            index = self.order.index(select_key)
            self.sheet_list.selection_clear(0, "end")
            self.sheet_list.selection_set(index)
            self.sheet_list.see(index)
        self._loading = False

    def _on_sheet_selected(self):
        if self._loading:
            return
        self._commit_general()
        selection = self.sheet_list.curselection()
        if not selection:
            return
        self.current_key = self.order[selection[0]]
        sheet = self.sheet
        self._loading = True
        self.key_var.set(sheet.key)
        self.name_var.set(sheet.name)
        self.subtitle_var.set(sheet.subtitle)
        self.key_status.configure(text="")
        self._loading = False
        self._refresh_all_tabs()

    def _commit_general(self):
        """Safety net: apply a short-code edit that was typed but never
        confirmed with "Apply code change", before switching sheets or
        saving. Name and subtitle already apply live as you type."""
        if self.current_key is None or self.current_key not in self.sheets:
            return
        new_key = self.key_var.get().strip()
        if new_key and new_key != self.current_key and new_key not in self.sheets:
            sheet = self.sheets.pop(self.current_key)
            sheet.key = new_key
            self.sheets[new_key] = sheet
            index = self.order.index(self.current_key)
            self.order[index] = new_key
            self.current_key = new_key
            self._refresh_sheet_list(new_key)

    def _refresh_all_tabs(self):
        self._refresh_fields()
        self._refresh_tests()
        self._refresh_scan()
        sheet = self.sheet
        if sheet:
            self.summary.configure(
                text=(f"{sheet.test_count} test(s)   |   "
                      f"{len(sheet.unit_fields)} detail field(s)   |   "
                      f"{len(sheet.scan_targets)} scan step(s)"))

    def _mark_dirty(self):
        if self._loading:
            return
        self.dirty = True
        self.status.configure(text="Unsaved changes")

    # --- sheet CRUD ------------------------------------------------------
    def new_sheet(self):
        self._commit_general()
        key = simpledialog.askstring(
            "New check sheet", "Short code (e.g. FQC):", parent=self)
        if not key:
            return
        key = key.strip()
        if key in self.sheets:
            messagebox.showerror("Code already used",
                                 f"'{key}' is already a check sheet code.",
                                 parent=self)
            return
        if not config_loader.SHEET_KEY_RE.match(key):
            messagebox.showerror(
                "Code not allowed",
                "Use 1-16 letters, digits, '-' or '_', starting with a letter "
                "or digit.", parent=self)
            return

        sheet = Checksheet(key, {
            "name": f"{key} Check Sheet",
            "subtitle": "",
            "unit_fields": [
                {"id": "serial_number", "label": "Serial number",
                 "required": True},
                {"id": "main_board_no", "label": "Main board number",
                 "required": True},
                {"id": "model", "label": "Model / size", "required": True},
            ],
            "scan_targets": [
                {"id": "unit_qr", "label": "Unit QR code",
                 "prompt": "Scan the QR code on the unit",
                 "rule": {"type": "raw", "target": "serial_number",
                          "trim": True, "upper": True}},
                {"id": "board_qr", "label": "Main board QR code",
                 "prompt": "Scan the QR code on the main board",
                 "rule": {"type": "raw", "target": "main_board_no",
                          "trim": True, "upper": True}},
            ],
            "tests": ["Appearance"],
        })
        self.sheets[key] = sheet
        self.order.append(key)
        self._mark_dirty()
        self._refresh_sheet_list(key)
        self._on_sheet_selected()
        self.notebook.select(self.tab_general)

    def duplicate_sheet(self):
        self._commit_general()
        if self.sheet is None:
            return
        key = simpledialog.askstring(
            "Copy check sheet", "Short code for the copy:", parent=self)
        if not key:
            return
        key = key.strip()
        if key in self.sheets:
            messagebox.showerror("Code already used",
                                 f"'{key}' is already in use.", parent=self)
            return
        self.sheets[key] = self.sheet.clone(key)
        self.order.append(key)
        self._mark_dirty()
        self._refresh_sheet_list(key)
        self._on_sheet_selected()

    def delete_sheet(self):
        if self.sheet is None:
            return
        if len(self.sheets) == 1:
            messagebox.showwarning(
                "Cannot delete", "At least one check sheet must remain.",
                parent=self)
            return
        if not messagebox.askyesno(
                "Delete check sheet",
                f"Delete '{self.sheet.name}'?\n\nInspections already saved "
                "under it stay in the database.", parent=self):
            return
        key = self.current_key
        self.sheets.pop(key)
        self.order.remove(key)
        self.current_key = None
        self._mark_dirty()
        self._refresh_sheet_list(self.order[0] if self.order else None)
        self._on_sheet_selected()

    # --- fields ----------------------------------------------------------
    def _refresh_fields(self):
        for item in self.fields_tree.get_children():
            self.fields_tree.delete(item)
        if self.sheet is None:
            return
        scannable = self.sheet.scannable_fields()
        for i, field in enumerate(self.sheet.unit_fields):
            self.fields_tree.insert(
                "", "end", iid=str(i),
                values=(field.label, field.id,
                        "yes" if field.required else "no",
                        "yes" if field.id in scannable else "no"))

    def _selected_field_index(self):
        sel = self.fields_tree.focus()
        return int(sel) if sel else None

    def add_field(self):
        if self.sheet is None:
            return
        result = FieldDialog(self, self.sheet).result
        if result:
            self.sheet.unit_fields.append(result)
            self._mark_dirty()
            self._refresh_all_tabs()

    def edit_field(self):
        index = self._selected_field_index()
        if index is None or self.sheet is None:
            return
        field = self.sheet.unit_fields[index]
        result = FieldDialog(self, self.sheet, field).result
        if result:
            self.sheet.unit_fields[index] = result
            self._mark_dirty()
            self._refresh_all_tabs()

    def remove_field(self):
        index = self._selected_field_index()
        if index is None or self.sheet is None:
            return
        field = self.sheet.unit_fields[index]
        if field.id in config_loader.MANDATORY_FIELDS:
            messagebox.showwarning(
                "Cannot remove",
                f"'{field.label}' is required on every check sheet.",
                parent=self)
            return
        self.sheet.unit_fields.pop(index)
        self._mark_dirty()
        self._refresh_all_tabs()

    def move_field(self, delta):
        index = self._selected_field_index()
        if index is None or self.sheet is None:
            return
        new = index + delta
        if not 0 <= new < len(self.sheet.unit_fields):
            return
        fields = self.sheet.unit_fields
        fields[index], fields[new] = fields[new], fields[index]
        self._mark_dirty()
        self._refresh_fields()
        self.fields_tree.selection_set(str(new))
        self.fields_tree.focus(str(new))

    # --- tests -----------------------------------------------------------
    def _refresh_tests(self):
        self.tests_list.delete(0, "end")
        if self.sheet is None:
            return
        for i, test in enumerate(self.sheet.tests, start=1):
            self.tests_list.insert("end", f"{i:>3}.  {test}")
        self.test_count_label.configure(
            text=f"{self.sheet.test_count} test(s)")

    def _selected_test_index(self):
        sel = self.tests_list.curselection()
        return sel[0] if sel else None

    def add_test(self):
        if self.sheet is None:
            return
        name = simpledialog.askstring("Add test", "Test name:", parent=self)
        if name and name.strip():
            self.sheet.tests.append(name.strip())
            self._mark_dirty()
            self._refresh_all_tabs()
            self.tests_list.see("end")

    def edit_test(self):
        index = self._selected_test_index()
        if index is None or self.sheet is None:
            return
        name = simpledialog.askstring(
            "Edit test", "Test name:", parent=self,
            initialvalue=self.sheet.tests[index])
        if name and name.strip():
            self.sheet.tests[index] = name.strip()
            self._mark_dirty()
            self._refresh_all_tabs()

    def remove_test(self):
        index = self._selected_test_index()
        if index is None or self.sheet is None:
            return
        self.sheet.tests.pop(index)
        self._mark_dirty()
        self._refresh_all_tabs()

    def move_test(self, delta):
        index = self._selected_test_index()
        if index is None or self.sheet is None:
            return
        new = index + delta
        if not 0 <= new < len(self.sheet.tests):
            return
        tests = self.sheet.tests
        tests[index], tests[new] = tests[new], tests[index]
        self._mark_dirty()
        self._refresh_tests()
        self.tests_list.selection_set(new)
        self.tests_list.see(new)

    def bulk_tests(self):
        if self.sheet is None:
            return
        result = BulkTestsDialog(self, self.sheet.tests).result
        if result is not None:
            self.sheet.tests = result
            self._mark_dirty()
            self._refresh_all_tabs()

    # --- scan steps ------------------------------------------------------
    def _refresh_scan(self):
        for item in self.scan_tree.get_children():
            self.scan_tree.delete(item)
        if self.sheet is None:
            return
        for i, target in enumerate(self.sheet.scan_targets):
            fills = [self.sheet.field_label(f) for f in target.target_fields]
            self.scan_tree.insert(
                "", "end", iid=str(i),
                values=(target.label, scanning.describe_rule(target.rule),
                        ", ".join(fills) or "nothing yet"))

    def _selected_scan_index(self):
        sel = self.scan_tree.focus()
        return int(sel) if sel else None

    def add_scan(self):
        if self.sheet is None:
            return
        result = ScanStepDialog(self, self.sheet).result
        if result:
            self.sheet.scan_targets.append(result)
            self._mark_dirty()
            self._refresh_all_tabs()

    def edit_scan(self):
        index = self._selected_scan_index()
        if index is None or self.sheet is None:
            return
        result = ScanStepDialog(self, self.sheet,
                                self.sheet.scan_targets[index]).result
        if result:
            self.sheet.scan_targets[index] = result
            self._mark_dirty()
            self._refresh_all_tabs()

    def remove_scan(self):
        index = self._selected_scan_index()
        if index is None or self.sheet is None:
            return
        self.sheet.scan_targets.pop(index)
        self._mark_dirty()
        self._refresh_all_tabs()

    def move_scan(self, delta):
        index = self._selected_scan_index()
        if index is None or self.sheet is None:
            return
        new = index + delta
        if not 0 <= new < len(self.sheet.scan_targets):
            return
        targets = self.sheet.scan_targets
        targets[index], targets[new] = targets[new], targets[index]
        self._mark_dirty()
        self._refresh_scan()
        self.scan_tree.selection_set(str(new))
        self.scan_tree.focus(str(new))

    # --- save ------------------------------------------------------------
    def save_all(self):
        self._commit_general()

        problems = []
        for key in self.order:
            found = config_loader.validate_sheet(key, self.sheets[key],
                                                 self.order)
            problems += [f"[{key}] {p}" for p in found]

        if problems:
            messagebox.showerror(
                "Fix these before saving",
                "\n".join(f"- {p}" for p in problems[:14])
                + (f"\n...and {len(problems) - 14} more"
                   if len(problems) > 14 else ""), parent=self)
            return

        ordered = {k: self.sheets[k] for k in self.order}
        try:
            config_loader.save_checksheets(ordered)
        except (config_loader.ConfigError, OSError) as exc:
            messagebox.showerror("Could not save", str(exc), parent=self)
            return

        self.app.checksheets = config_loader.load_checksheets()
        self.dirty = False
        self.status.configure(text="Saved")
        messagebox.showinfo(
            "Check sheets saved",
            f"{len(ordered)} check sheet(s) saved. The previous version was "
            "kept in data/backups.", parent=self)

    def discard(self):
        if self.dirty and not messagebox.askyesno(
                "Discard changes",
                "Throw away every change made since the last save?",
                parent=self):
            return
        self.app.show_builder()

    def close(self):
        if self.dirty and not messagebox.askyesno(
                "Unsaved changes",
                "There are unsaved changes. Close the builder anyway?",
                parent=self):
            return
        self.app.show_select()


# --- dialogs -------------------------------------------------------------

class _BaseDialog(tk.Toplevel):
    def __init__(self, parent, title, width=560, height=420):
        super().__init__(parent)
        self.result = None
        self.title(title)
        self.configure(bg=theme.BG)
        self.transient(parent.winfo_toplevel())
        self.resizable(True, True)
        self.geometry(f"{width}x{height}")
        self.body = ttk.Frame(self)
        self.body.pack(fill="both", expand=True, padx=22, pady=(20, 8))
        self.buttons = ttk.Frame(self)
        self.buttons.pack(fill="x", padx=22, pady=(0, 18))

    def add_buttons(self, ok_text="Save"):
        ttk.Button(self.buttons, text="Cancel",
                   command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(self.buttons, text=ok_text, style="Primary.TButton",
                   command=self.on_ok).pack(side="right")

    def finish(self):
        self.grab_set()
        self.wait_window(self)

    def on_ok(self):
        raise NotImplementedError


class FieldDialog(_BaseDialog):
    def __init__(self, parent, sheet, field=None):
        super().__init__(parent, "Unit detail field", 520, 330)
        self.sheet = sheet
        self.original = field
        locked = field is not None and field.id in config_loader.MANDATORY_FIELDS

        pad = self.body
        pad.columnconfigure(1, weight=1)

        self.label_var = tk.StringVar(value=field.label if field else "")
        self.id_var = tk.StringVar(value=field.id if field else "")
        self.req_var = tk.BooleanVar(value=field.required if field else False)

        ttk.Label(pad, text="Label shown to the inspector").grid(
            row=0, column=0, columnspan=2, sticky="w")
        entry = ttk.Entry(pad, textvariable=self.label_var,
                          font=(theme.FONT, 11))
        entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 14),
                   ipady=3)

        ttk.Label(pad, text="Field id (used by the scanner rules)").grid(
            row=2, column=0, columnspan=2, sticky="w")
        self.id_entry = ttk.Entry(pad, textvariable=self.id_var,
                                  font=("Consolas", 11))
        self.id_entry.grid(row=3, column=0, columnspan=2, sticky="ew",
                           pady=(4, 2), ipady=3)
        ttk.Label(pad, text="Lowercase letters, digits and underscores only.",
                  style="Muted.TLabel").grid(row=4, column=0, columnspan=2,
                                             sticky="w")

        chk = ttk.Checkbutton(pad, text="Required before the tests open",
                              variable=self.req_var)
        chk.grid(row=5, column=0, columnspan=2, sticky="w", pady=(16, 0))

        if locked:
            self.id_entry.state(["disabled"])
            chk.state(["disabled"])
            ttk.Label(pad, text="This field is built in and cannot be renamed "
                                "or made optional.",
                      style="Muted.TLabel").grid(row=6, column=0,
                                                 columnspan=2, sticky="w",
                                                 pady=(10, 0))

        if field is None:
            self.label_var.trace_add("write", self._suggest_id)

        self.error = tk.Label(pad, text="", bg=theme.BG, fg=theme.NG_COLOR,
                              font=(theme.FONT, 9), wraplength=440,
                              justify="left")
        self.error.grid(row=7, column=0, columnspan=2, sticky="w",
                        pady=(14, 0))

        self.add_buttons()
        entry.focus_set()
        self.finish()

    def _suggest_id(self, *_a):
        if self.id_entry.instate(["disabled"]):
            return
        self.id_var.set(config_loader.suggest_field_id(self.label_var.get()))

    def on_ok(self):
        label = self.label_var.get().strip()
        field_id = self.id_var.get().strip()
        if not label:
            self.error.configure(text="Give the field a label.")
            return
        if not config_loader.FIELD_ID_RE.match(field_id):
            self.error.configure(
                text="The field id must be lowercase letters, digits and "
                     "underscores, starting with a letter.")
            return
        taken = [f.id for f in self.sheet.unit_fields
                 if f is not self.original]
        if field_id in taken:
            self.error.configure(
                text=f"'{field_id}' is already used on this check sheet.")
            return
        self.result = UnitField({"id": field_id, "label": label,
                                 "required": self.req_var.get()})
        self.destroy()


class BulkTestsDialog(_BaseDialog):
    def __init__(self, parent, tests):
        super().__init__(parent, "Paste the test list", 620, 520)
        ttk.Label(self.body, text="One test per line. This replaces the whole "
                                  "list, so you can paste a column straight "
                                  "out of Excel.",
                  style="Muted.TLabel", wraplength=540).pack(anchor="w",
                                                             pady=(0, 10))
        self.text = tk.Text(self.body, font=(theme.FONT, 10), wrap="none",
                            bd=0, highlightthickness=1,
                            highlightbackground=theme.BORDER, bg=theme.SURFACE)
        self.text.pack(fill="both", expand=True)
        self.text.insert("1.0", "\n".join(tests))
        self.add_buttons(ok_text="Replace list")
        self.text.focus_set()
        self.finish()

    def on_ok(self):
        lines = [line.strip() for line in
                 self.text.get("1.0", "end").splitlines()]
        cleaned = []
        for line in lines:
            # tolerate pasted numbering like "1. Appearance" or "1) Appearance"
            stripped = line
            for sep in (". ", ") ", "\t"):
                head, found, tail = stripped.partition(sep)
                if found and head.strip().rstrip(".").isdigit():
                    stripped = tail
                    break
            stripped = stripped.strip()
            if stripped:
                cleaned.append(stripped)
        if not cleaned:
            messagebox.showwarning("Nothing to save",
                                   "The list is empty.", parent=self)
            return
        self.result = cleaned
        self.destroy()


class ScanStepDialog(_BaseDialog):
    """Configure one scan step, with a place to try a real code."""

    def __init__(self, parent, sheet, target=None):
        super().__init__(parent, "Scan step", 720, 660)
        self.sheet = sheet
        self.target = target
        rule = dict(target.rule) if target else {"type": "raw", "trim": True,
                                                 "upper": True}

        pad = self.body
        pad.columnconfigure(1, weight=1)

        self.label_var = tk.StringVar(value=target.label if target else "")
        self.prompt_var = tk.StringVar(value=target.prompt if target else "")
        self.type_var = tk.StringVar(value=rule.get("type", "raw"))
        self.upper_var = tk.BooleanVar(value=bool(rule.get("upper")))
        self.trim_var = tk.BooleanVar(value=bool(rule.get("trim", True)))

        ttk.Label(pad, text="Step name").grid(row=0, column=0, sticky="w")
        ttk.Entry(pad, textvariable=self.label_var, font=(theme.FONT, 11)
                  ).grid(row=0, column=1, sticky="ew", padx=(12, 0), ipady=3)

        ttk.Label(pad, text="On-screen instruction").grid(row=1, column=0,
                                                          sticky="w",
                                                          pady=(12, 0))
        ttk.Entry(pad, textvariable=self.prompt_var, font=(theme.FONT, 11)
                  ).grid(row=1, column=1, sticky="ew", padx=(12, 0),
                         pady=(12, 0), ipady=3)

        ttk.Label(pad, text="How the code is read").grid(row=2, column=0,
                                                         sticky="w",
                                                         pady=(12, 0))
        combo = ttk.Combobox(pad, textvariable=self.type_var,
                             values=list(scanning.PARSE_TYPES),
                             state="readonly")
        combo.grid(row=2, column=1, sticky="ew", padx=(12, 0), pady=(12, 0))
        combo.bind("<<ComboboxSelected>>", lambda _e: self._on_type_change())

        self.help_label = ttk.Label(pad, text="", style="Muted.TLabel",
                                    wraplength=640, justify="left")
        self.help_label.grid(row=3, column=0, columnspan=2, sticky="w",
                             pady=(8, 0))

        self.rule_frame = ttk.Frame(pad)
        self.rule_frame.grid(row=4, column=0, columnspan=2, sticky="nsew",
                             pady=(12, 0))
        pad.rowconfigure(4, weight=1)

        opts = ttk.Frame(pad)
        opts.grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Checkbutton(opts, text="Trim spaces",
                        variable=self.trim_var).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(opts, text="Force UPPERCASE",
                        variable=self.upper_var).pack(side="left")

        # try-it panel
        tryit = tk.Frame(pad, bg=theme.SURFACE,
                         highlightbackground=theme.BORDER, highlightthickness=1)
        tryit.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        inner = tk.Frame(tryit, bg=theme.SURFACE)
        inner.pack(fill="x", padx=14, pady=12)
        tk.Label(inner, text="Try a real code", bg=theme.SURFACE, fg=theme.INK,
                 font=(theme.FONT, 10, "bold")).pack(anchor="w")
        tk.Label(inner, text="Scan a code here (or paste one) to check the "
                             "rule before saving.", bg=theme.SURFACE,
                 fg=theme.MUTED, font=(theme.FONT, 9)).pack(anchor="w",
                                                            pady=(2, 8))
        row = tk.Frame(inner, bg=theme.SURFACE)
        row.pack(fill="x")
        self.try_var = tk.StringVar()
        try_entry = ttk.Entry(row, textvariable=self.try_var,
                              font=("Consolas", 11))
        try_entry.pack(side="left", fill="x", expand=True, ipady=4)
        try_entry.bind("<Return>", lambda _e: self._try_parse())
        widgets.flat_button(row, "Test", self._try_parse, theme.PRIMARY
                            ).pack(side="left", padx=(8, 0))
        self.try_result = tk.Label(inner, text="", bg=theme.SURFACE,
                                   fg=theme.MUTED, font=(theme.FONT, 9),
                                   justify="left", anchor="w", wraplength=620)
        self.try_result.pack(fill="x", pady=(8, 0))

        self.error = tk.Label(pad, text="", bg=theme.BG, fg=theme.NG_COLOR,
                              font=(theme.FONT, 9), wraplength=640,
                              justify="left")
        self.error.grid(row=7, column=0, columnspan=2, sticky="w",
                        pady=(10, 0))

        # One saved rule per parse type, so switching the dropdown back and
        # forth doesn't wipe out what was typed under a type visited earlier.
        self._rule_by_type = {rule.get("type", "raw"): rule}
        self._active_ptype = None
        self._rebuild_rule_form()
        self.add_buttons()
        self.finish()

    # -- dynamic rule form ------------------------------------------------
    def _on_type_change(self):
        self._capture_active_rule()
        self._rebuild_rule_form()

    def _capture_active_rule(self):
        """Save whatever is currently typed under the type being left."""
        if self._active_ptype is None:
            return
        try:
            self._rule_by_type[self._active_ptype] = self._collect_rule(
                ptype=self._active_ptype)
        except Exception:
            pass  # incomplete widgets (e.g. mid-edit) - just skip the save

    def _rebuild_rule_form(self):
        for child in self.rule_frame.winfo_children():
            child.destroy()
        ptype = self.type_var.get()
        self.help_label.configure(text=scanning.PARSE_TYPE_HELP.get(ptype, ""))
        rule = self._rule_by_type.get(ptype, {})
        self._active_ptype = ptype

        frame = self.rule_frame
        frame.columnconfigure(1, weight=1)
        field_ids = self.sheet.field_ids

        self.widgets = {}

        if ptype == "raw":
            ttk.Label(frame, text="Put the code into this field").grid(
                row=0, column=0, sticky="w")
            self.target_field_var = tk.StringVar(
                value=rule.get("target") or field_ids[0])
            ttk.Combobox(frame, textvariable=self.target_field_var,
                         values=field_ids, state="readonly").grid(
                row=0, column=1, sticky="ew", padx=(12, 0))

            ttk.Label(frame, text="Remove this prefix (optional)").grid(
                row=1, column=0, sticky="w", pady=(10, 0))
            self.prefix_var = tk.StringVar(value=rule.get("strip_prefix", ""))
            ttk.Entry(frame, textvariable=self.prefix_var,
                      font=("Consolas", 10)).grid(row=1, column=1, sticky="ew",
                                                  padx=(12, 0), pady=(10, 0))

            ttk.Label(frame, text="Extract with pattern (optional)").grid(
                row=2, column=0, sticky="w", pady=(10, 0))
            self.regex_var = tk.StringVar(value=rule.get("regex", ""))
            ttk.Entry(frame, textvariable=self.regex_var,
                      font=("Consolas", 10)).grid(row=2, column=1, sticky="ew",
                                                  padx=(12, 0), pady=(10, 0))

        elif ptype in ("delimited", "split", "json"):
            row = 0
            if ptype != "json":
                ttk.Label(frame, text="Separator between parts").grid(
                    row=0, column=0, sticky="w")
                default = ";" if ptype == "delimited" else ","
                self.sep_var = tk.StringVar(
                    value=rule.get("separator", default))
                ttk.Entry(frame, textvariable=self.sep_var, width=6,
                          font=("Consolas", 11)).grid(row=0, column=1,
                                                      sticky="w",
                                                      padx=(12, 0))
                row = 1
            if ptype == "delimited":
                ttk.Label(frame, text="Separator between key and value").grid(
                    row=1, column=0, sticky="w", pady=(10, 0))
                self.pair_var = tk.StringVar(
                    value=rule.get("pair_separator", ":"))
                ttk.Entry(frame, textvariable=self.pair_var, width=6,
                          font=("Consolas", 11)).grid(row=1, column=1,
                                                      sticky="w",
                                                      padx=(12, 0),
                                                      pady=(10, 0))
                row = 2

            example = {"delimited": "SN = serial_number\nMODEL = model",
                       "split": "0 = serial_number\n1 = model",
                       "json": "sn = serial_number\nmdl = model"}[ptype]
            hint = {"delimited": "Each line maps a key in the code to a field.",
                    "split": "Each line maps a position (0 is first) to a "
                             "field.",
                    "json": "Each line maps a JSON key to a field."}[ptype]
            ttk.Label(frame, text="Mapping").grid(row=row, column=0,
                                                  sticky="nw", pady=(12, 0))
            box = ttk.Frame(frame)
            box.grid(row=row, column=1, sticky="nsew", padx=(12, 0),
                     pady=(12, 0))
            frame.rowconfigure(row, weight=1)
            self.map_text = tk.Text(box, height=6, font=("Consolas", 10),
                                    bd=0, highlightthickness=1,
                                    highlightbackground=theme.BORDER,
                                    bg=theme.SURFACE)
            self.map_text.pack(fill="both", expand=True)
            existing = scanning.mapping_to_text(rule.get("map"))
            self.map_text.insert("1.0", existing or example)
            ttk.Label(box, text=f"{hint}  Field ids available: "
                                f"{', '.join(field_ids)}",
                      style="Muted.TLabel", wraplength=460,
                      justify="left").pack(anchor="w", pady=(4, 0))

        elif ptype == "regex":
            ttk.Label(frame, text="Pattern").grid(row=0, column=0, sticky="w")
            self.pattern_var = tk.StringVar(value=rule.get("pattern", ""))
            ttk.Entry(frame, textvariable=self.pattern_var,
                      font=("Consolas", 10)).grid(row=0, column=1, sticky="ew",
                                                  padx=(12, 0))
            ttk.Label(frame, text="Use named groups, e.g. "
                                  r"^(?P<serial_number>[A-Z]{3}\d+)"
                                  r"(?P<model>\d{2}[A-Z]+)$"
                                  f"   Field ids: {', '.join(field_ids)}",
                      style="Muted.TLabel", wraplength=620,
                      justify="left").grid(row=1, column=0, columnspan=2,
                                           sticky="w", pady=(8, 0))

        elif ptype == "fixed":
            ttk.Label(frame, text="Positions").grid(row=0, column=0,
                                                    sticky="nw")
            box = ttk.Frame(frame)
            box.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
            frame.rowconfigure(0, weight=1)
            self.slices_text = tk.Text(box, height=6, font=("Consolas", 10),
                                       bd=0, highlightthickness=1,
                                       highlightbackground=theme.BORDER,
                                       bg=theme.SURFACE)
            self.slices_text.pack(fill="both", expand=True)
            existing = scanning.slices_to_text(rule.get("slices"))
            self.slices_text.insert(
                "1.0", existing or "serial_number = 0, 10\nmodel = 10, 15")
            ttk.Label(box, text="field = start, end   (character positions, "
                                "counting from 0)", style="Muted.TLabel",
                      wraplength=460, justify="left").pack(anchor="w",
                                                           pady=(4, 0))

    # -- build / test rule ------------------------------------------------
    def _collect_rule(self, ptype=None):
        """Read the rule from whichever widgets are on screen. Pass ptype
        explicitly when the widgets don't match self.type_var anymore (e.g.
        capturing the outgoing type right after the dropdown has already
        changed)."""
        if ptype is None:
            ptype = self.type_var.get()
        rule = {"type": ptype, "trim": self.trim_var.get(),
                "upper": self.upper_var.get()}

        if ptype == "raw":
            rule["target"] = self.target_field_var.get()
            if self.prefix_var.get():
                rule["strip_prefix"] = self.prefix_var.get()
            if self.regex_var.get().strip():
                rule["regex"] = self.regex_var.get().strip()
        elif ptype == "delimited":
            rule["separator"] = self.sep_var.get() or ";"
            rule["pair_separator"] = self.pair_var.get() or ":"
            rule["map"] = scanning.text_to_mapping(
                self.map_text.get("1.0", "end"))
        elif ptype == "split":
            rule["separator"] = self.sep_var.get() or ","
            rule["map"] = scanning.text_to_mapping(
                self.map_text.get("1.0", "end"))
        elif ptype == "json":
            rule["map"] = scanning.text_to_mapping(
                self.map_text.get("1.0", "end"))
        elif ptype == "regex":
            rule["pattern"] = self.pattern_var.get().strip()
        elif ptype == "fixed":
            rule["slices"] = scanning.text_to_slices(
                self.slices_text.get("1.0", "end"))
        return rule

    def _try_parse(self):
        payload = self.try_var.get()
        try:
            values = scanning.parse_scan(payload, self._collect_rule())
        except scanning.ScanParseError as exc:
            self.try_result.configure(text=f"Not read: {exc}",
                                      fg=theme.NG_COLOR)
            return
        known = self.sheet.field_ids
        lines = []
        for field_id, value in values.items():
            mark = "" if field_id in known else "   <- not a field on this sheet"
            lines.append(f"{self.sheet.field_label(field_id)}: {value}{mark}")
        all_known = all(f in known for f in values)
        self.try_result.configure(
            text="Read successfully -\n" + "\n".join(lines),
            fg=theme.OK_COLOR if all_known else theme.RW_COLOR)

    def on_ok(self):
        label = self.label_var.get().strip()
        if not label:
            self.error.configure(text="Give the scan step a name.")
            return
        rule = self._collect_rule()
        probe = ScanTarget({"label": label, "rule": rule})
        fields = probe.target_fields
        if not fields:
            self.error.configure(
                text="This step does not fill any field yet. Set the mapping "
                     "or target field.")
            return
        unknown = [f for f in fields if f not in self.sheet.field_ids]
        if unknown:
            self.error.configure(
                text="These are not fields on this check sheet: "
                     + ", ".join(unknown)
                     + ". Add them on the Unit fields tab first.")
            return

        step_id = (self.target.id if self.target
                   else config_loader.suggest_field_id(label))
        prompt = self.prompt_var.get().strip() or f"Scan the {label.lower()}"
        self.result = ScanTarget({"id": step_id, "label": label,
                                  "prompt": prompt, "rule": rule})
        self.destroy()
