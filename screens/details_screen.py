"""Step 3 - unit details, filled by scanning.

A USB barcode / QR scanner behaves like a keyboard: it types the code into
the focused box and usually sends Enter. So the scan box below simply keeps
focus and reacts to Enter. Scanners that send Tab are handled too, and for
scanners configured with no terminator at all there is an idle timer that
submits the line once typing stops.
"""

import tkinter as tk
from tkinter import messagebox, ttk

import camera
import database
import scanning
import theme
import widgets

# A scanner types a whole code in a few milliseconds. If no key arrives for
# this long and the box is not empty, treat the line as finished.
IDLE_SUBMIT_MS = 350


class DetailsScreen(ttk.Frame):
    def __init__(self, parent, app, checksheet_key):
        super().__init__(parent)
        self.app = app
        self.sheet = app.checksheets[checksheet_key]
        self.vars = {}
        self.entries = {}
        self.tags = {}
        self.scanned_fields = set()
        self.done_steps = set()
        self.step_index = 0
        self._idle_job = None
        self._build()

    # --- layout ----------------------------------------------------------
    def _build(self):
        def back_btn(parent):
            ttk.Button(parent, text="Back to sheets",
                       command=self.app.show_select).pack(side="left")

        widgets.header_bar(self, self.sheet.name,
                           f"{self.sheet.key} - unit details", [back_btn])

        outer = ttk.Frame(self)
        outer.pack(fill="both", expand=True, padx=28, pady=(18, 14))

        # Footer is packed to the bottom FIRST, so it always stays on
        # screen and reachable, no matter how many fields a sheet has.
        footer = ttk.Frame(outer)
        footer.pack(side="bottom", fill="x", pady=(10, 0))

        scroll = widgets.ScrollFrame(outer)
        scroll.pack(side="top", fill="both", expand=True)
        body = scroll.body

        if self.sheet.scan_targets:
            self._build_scan_panel(body)

        ttk.Label(body, text="Unit details", style="Head.TLabel").pack(
            anchor="w", pady=(16, 2))
        ttk.Label(body, text="Scanned values appear below and can still be "
                             "corrected by hand. Fields marked * are required.",
                  style="Muted.TLabel").pack(anchor="w", pady=(0, 12))

        self._build_fields(body)

        self.error = tk.Label(footer, text="", bg=theme.BG, fg=theme.NG_COLOR,
                              font=(theme.FONT, 9), justify="left",
                              wraplength=640, anchor="w")
        self.error.pack(side="left", fill="x", expand=True)
        ttk.Button(footer, text="Cancel",
                   command=self.app.show_select).pack(side="right",
                                                      padx=(8, 0))
        ttk.Button(footer, text="Continue to tests", style="Primary.TButton",
                   command=self.proceed).pack(side="right")

        if self.sheet.scan_targets:
            self.after(120, self._focus_scan)
        elif self.sheet.unit_fields:
            self.entries[self.sheet.unit_fields[0].id].focus_set()

    def _build_scan_panel(self, parent):
        card = tk.Frame(parent, bg=theme.SURFACE,
                        highlightbackground=theme.PRIMARY, highlightthickness=2)
        card.pack(fill="x")

        inner = tk.Frame(card, bg=theme.SURFACE)
        inner.pack(fill="x", padx=22, pady=18)

        top = tk.Frame(inner, bg=theme.SURFACE)
        top.pack(fill="x")
        self.step_label = tk.Label(top, text="", bg=theme.SURFACE,
                                   fg=theme.PRIMARY,
                                   font=(theme.FONT, 9, "bold"))
        self.step_label.pack(side="left")
        self.steps_done_label = tk.Label(top, text="", bg=theme.SURFACE,
                                         fg=theme.MUTED,
                                         font=(theme.FONT, 9))
        self.steps_done_label.pack(side="right")

        self.prompt_label = tk.Label(inner, text="", bg=theme.SURFACE,
                                     fg=theme.INK,
                                     font=(theme.FONT, 15, "bold"),
                                     anchor="w", justify="left")
        self.prompt_label.pack(fill="x", pady=(5, 12))

        row = tk.Frame(inner, bg=theme.SURFACE)
        row.pack(fill="x")
        self.scan_var = tk.StringVar()
        self.scan_entry = ttk.Entry(row, textvariable=self.scan_var,
                                    font=("Consolas", 14))
        self.scan_entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.scan_entry.bind("<Return>", self._on_scan_submit)
        self.scan_entry.bind("<KP_Enter>", self._on_scan_submit)
        self.scan_entry.bind("<Tab>", self._on_scan_submit)
        self.scan_entry.bind("<Key>", self._on_scan_key)

        widgets.flat_button(row, "Read code", self._on_scan_submit,
                            theme.PRIMARY).pack(side="left", padx=(10, 0))
        widgets.flat_button(row, "Scan with camera", self._scan_with_camera,
                            theme.MUTED).pack(side="left", padx=(8, 0))

        tk.Label(inner, text="No handheld scanner at this station? Use "
                             "\"Scan with camera\" to read the code with a "
                             "webcam instead.", bg=theme.SURFACE,
                 fg=theme.MUTED, font=(theme.FONT, 8)).pack(anchor="w",
                                                            pady=(6, 0))

        links = tk.Frame(inner, bg=theme.SURFACE)
        links.pack(fill="x", pady=(10, 0))
        for text, cmd in (("Skip this step", self._skip_step),
                          ("Start scanning again", self.reset_scans)):
            tk.Button(links, text=text, command=cmd, relief="flat", bd=0,
                      bg=theme.SURFACE, fg=theme.PRIMARY,
                      font=(theme.FONT, 9, "underline"), cursor="hand2",
                      activebackground=theme.SURFACE).pack(side="left",
                                                           padx=(0, 16))

        self.scan_status = tk.Label(inner, text="", bg=theme.SURFACE,
                                    fg=theme.MUTED, font=(theme.FONT, 10),
                                    anchor="w", justify="left", wraplength=880)
        self.scan_status.pack(fill="x", pady=(10, 0))

        self._refresh_step()

    def _build_fields(self, parent):
        card = tk.Frame(parent, bg=theme.SURFACE,
                        highlightbackground=theme.BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)

        form = tk.Frame(card, bg=theme.SURFACE)
        form.pack(fill="both", expand=True, padx=24, pady=20)
        form.columnconfigure(0, weight=1, uniform="col")
        form.columnconfigure(1, weight=1, uniform="col")

        scannable = self.sheet.scannable_fields()

        for idx, field in enumerate(self.sheet.unit_fields):
            row, col = divmod(idx, 2)
            cell = tk.Frame(form, bg=theme.SURFACE)
            cell.grid(row=row, column=col, sticky="ew",
                      padx=(0, 18) if col == 0 else (18, 0), pady=(0, 14))
            cell.columnconfigure(0, weight=1)

            head = tk.Frame(cell, bg=theme.SURFACE)
            head.grid(row=0, column=0, sticky="ew")
            tk.Label(head, text=field.label + (" *" if field.required else ""),
                     bg=theme.SURFACE, fg=theme.INK,
                     font=(theme.FONT, 10)).pack(side="left")
            tag = tk.Label(head, text="scannable" if field.id in scannable
                           else "", bg=theme.SURFACE, fg=theme.MUTED,
                           font=(theme.FONT, 8))
            tag.pack(side="left", padx=(8, 0))
            self.tags[field.id] = tag

            var = tk.StringVar()
            entry = ttk.Entry(cell, textvariable=var, font=(theme.FONT, 11))
            entry.grid(row=1, column=0, sticky="ew", pady=(4, 0), ipady=3)
            var.trace_add("write",
                          lambda *_a, fid=field.id: self._on_manual_edit(fid))
            self.vars[field.id] = var
            self.entries[field.id] = entry

    # --- scanning --------------------------------------------------------
    @property
    def steps(self):
        return self.sheet.scan_targets

    def _focus_scan(self):
        if self.steps and self.step_index < len(self.steps):
            self.scan_entry.focus_set()

    def _refresh_step(self):
        total = len(self.steps)
        self.steps_done_label.configure(
            text=f"{len(self.done_steps)} of {total} code(s) read")

        if self.step_index >= total:
            self.step_label.configure(text="SCANNING COMPLETE")
            self.prompt_label.configure(text="All codes read")
            self.scan_entry.state(["disabled"])
            return

        self.scan_entry.state(["!disabled"])
        step = self.steps[self.step_index]
        self.step_label.configure(
            text=f"STEP {self.step_index + 1} OF {total} - "
                 f"{step.label.upper()}")
        self.prompt_label.configure(text=step.prompt)
        self._focus_scan()

    def _on_scan_key(self, _event):
        if self._idle_job is not None:
            self.after_cancel(self._idle_job)
        self._idle_job = self.after(IDLE_SUBMIT_MS, self._idle_submit)

    def _idle_submit(self):
        self._idle_job = None
        if self.scan_var.get().strip():
            self._on_scan_submit()

    def _on_scan_submit(self, _event=None):
        if self._idle_job is not None:
            self.after_cancel(self._idle_job)
            self._idle_job = None

        payload = self.scan_var.get()
        if not payload.strip():
            return "break"
        if self.step_index >= len(self.steps):
            return "break"

        step = self.steps[self.step_index]
        try:
            values = scanning.parse_scan(payload, step.rule)
        except scanning.ScanParseError as exc:
            self.scan_status.configure(
                text=f"Could not read that code: {exc}  "
                     "Scan again, or type the details in by hand below.",
                fg=theme.NG_COLOR)
            self.scan_var.set("")
            self._focus_scan()
            return "break"

        applied, ignored = [], []
        for field_id, value in values.items():
            if field_id in self.vars:
                self.vars[field_id].set(value)
                self.scanned_fields.add(field_id)
                self._mark_scanned(field_id)
                applied.append(self.sheet.field_label(field_id))
            else:
                ignored.append(field_id)

        if not applied:
            self.scan_status.configure(
                text="That code was read, but none of its values match a "
                     "field on this sheet. Check the scan step in the check "
                     "sheet builder.", fg=theme.RW_COLOR)
            self.scan_var.set("")
            self._focus_scan()
            return "break"

        note = f"{step.label} read - filled: {', '.join(applied)}."
        if ignored:
            note += f"  (ignored: {', '.join(ignored)})"
        self.scan_status.configure(text=note, fg=theme.OK_COLOR)

        self.done_steps.add(self.step_index)
        self.scan_var.set("")
        self.step_index += 1
        self._refresh_step()
        return "break"

    def _scan_with_camera(self):
        if self.step_index >= len(self.steps):
            return
        if not camera.require_camera(self):
            return
        step = self.steps[self.step_index]

        # Labels with a printed serial number above their barcode benefit
        # from dual OCR+barcode verification; a plain code with no printed
        # human-readable twin (e.g. a board QR) doesn't - OCR would just
        # never find anything to read there, so use the simpler
        # barcode-only dialog for those instead.
        use_verified = ("serial_number" in step.target_fields
                        and camera.CAN_READ_SERIAL_TEXT)

        if use_verified:
            dialog = camera.VerifiedScanDialog(self.winfo_toplevel(), step.prompt)
        else:
            dialog = camera.ScanCaptureDialog(self.winfo_toplevel(), step.prompt)
        self.wait_window(dialog)
        if dialog.payload:
            # Feed the decoded text through the exact same path a physical
            # scanner uses, so parsing and field-filling behave identically.
            self.scan_var.set(dialog.payload)
            self._on_scan_submit()
        self._focus_scan()

    def _skip_step(self):
        if self.step_index >= len(self.steps):
            return
        step = self.steps[self.step_index]
        self.scan_status.configure(
            text=f"{step.label} skipped - type those details in by hand.",
            fg=theme.RW_COLOR)
        self.scan_var.set("")
        self.step_index += 1
        self._refresh_step()
        if self.step_index >= len(self.steps):
            first = self.sheet.unit_fields[0].id
            self.entries[first].focus_set()

    def reset_scans(self):
        self.step_index = 0
        self.done_steps.clear()
        for field_id in list(self.scanned_fields):
            self.vars[field_id].set("")
            self._mark_scanned(field_id, on=False)
        self.scanned_fields.clear()
        self.scan_var.set("")
        self.scan_status.configure(text="Cleared. Scan the first code again.",
                                   fg=theme.MUTED)
        self._refresh_step()

    def _mark_scanned(self, field_id, on=True):
        tag = self.tags.get(field_id)
        if tag is None:
            return
        if on:
            tag.configure(text="scanned", fg=theme.OK_COLOR)
        else:
            scannable = self.sheet.scannable_fields()
            tag.configure(text="scannable" if field_id in scannable else "",
                          fg=theme.MUTED)

    def _on_manual_edit(self, field_id):
        """If a human types over a scanned value, stop calling it scanned."""
        if field_id in self.scanned_fields:
            tag = self.tags.get(field_id)
            if tag is not None and tag.cget("text") == "scanned":
                self.after_idle(lambda: self._check_override(field_id))

    def _check_override(self, field_id):
        if self.focus_get() is self.entries.get(field_id):
            self.scanned_fields.discard(field_id)
            self.tags[field_id].configure(text="edited by hand",
                                          fg=theme.RW_COLOR)

    # --- continue --------------------------------------------------------
    def collect(self):
        return {k: v.get().strip() for k, v in self.vars.items()}

    def proceed(self):
        self.error.configure(text="")
        values = self.collect()

        missing = [f.label for f in self.sheet.unit_fields
                   if f.required and not values.get(f.id)]
        if missing:
            self.error.configure(
                text="Scan or type these before continuing: "
                     + ", ".join(missing))
            for f in self.sheet.unit_fields:
                if f.required and not values.get(f.id):
                    self.entries[f.id].focus_set()
                    break
            return

        dup = database.find_duplicate(self.sheet.key, values["serial_number"])
        if dup is not None:
            go_on = messagebox.askyesno(
                "Unit already inspected",
                f"Serial {values['serial_number']} was already run on "
                f"{self.sheet.name}.\n\n"
                f"Saved: {dup['saved_at']}\n"
                f"Result: {dup['overall_result']}\n"
                f"By: {dup['operator_name']}\n\n"
                "Start a new inspection for the same unit?", parent=self)
            if not go_on:
                return

        self.app.show_checksheet(self.sheet.key, values)
