"""Steps 4 and 5 - the test grid, photo capture, result and save.

Rules enforced here:
  * every test is listed in a column
  * a photo must be attached before the result buttons unlock
  * NG or RW unlocks a reason / defect box, which must be filled
  * nothing saves until every row is complete
"""

import os
import shutil
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import camera
import database
import theme
import widgets

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHOTO_ROOT = os.path.join(BASE_DIR, "photos")

IMAGE_TYPES = [
    ("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.webp"),
    ("All files", "*.*"),
]

RESULTS = ("OK", "NG", "RW")
RESULT_HINT = {
    "OK": "Pass",
    "NG": "Not good",
    "RW": "Rework",
}


def open_file(path):
    """Open an image in the system viewer."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception as exc:
        messagebox.showerror("Cannot open photo", str(exc))


class TestRow:
    """One line of the checksheet."""

    def __init__(self, screen, parent, index, test_name):
        self.screen = screen
        self.index = index
        self.test_name = test_name
        self.photo_path = ""
        self.is_temp_photo = False
        self.result = ""

        bg = theme.SURFACE if index % 2 == 0 else theme.SURFACE_ALT
        self.bg = bg
        self.frame = tk.Frame(parent, bg=bg)
        self.frame.grid(row=index, column=0, sticky="ew", pady=(0, 1))
        self.frame.columnconfigure(1, weight=3, minsize=230)
        self.frame.columnconfigure(2, minsize=250)
        self.frame.columnconfigure(3, minsize=210)
        self.frame.columnconfigure(4, weight=2, minsize=230)

        # status stripe on the left edge
        self.stripe = tk.Frame(self.frame, bg=theme.BORDER, width=4)
        self.stripe.grid(row=0, column=0, sticky="ns", rowspan=2)

        # column 1 - test name
        name_box = tk.Frame(self.frame, bg=bg)
        name_box.grid(row=0, column=1, sticky="w", padx=(14, 10), pady=11)
        tk.Label(name_box, text=f"{index + 1}.", bg=bg, fg=theme.MUTED,
                 font=(theme.FONT, 9)).pack(side="left", padx=(0, 8))
        tk.Label(name_box, text=test_name, bg=bg, fg=theme.INK,
                 font=(theme.FONT, 10), wraplength=280, justify="left"
                 ).pack(side="left")

        # column 2 - photo
        photo_box = tk.Frame(self.frame, bg=bg)
        photo_box.grid(row=0, column=2, sticky="w", padx=6, pady=8)
        photo_row1 = tk.Frame(photo_box, bg=bg)
        photo_row1.pack(anchor="w")
        self.photo_btn = widgets.flat_button(
            photo_row1, "Browse", self.pick_photo, theme.PRIMARY,
            font=(theme.FONT, 9, "bold"))
        self.photo_btn.pack(side="left")
        self.camera_btn = widgets.flat_button(
            photo_row1, "Camera", self.capture_photo, theme.MUTED,
            font=(theme.FONT, 9, "bold"))
        self.camera_btn.pack(side="left", padx=(6, 0))
        self.view_btn = tk.Button(
            photo_row1, text="View", command=self.view_photo, relief="flat",
            bd=0, bg=bg, fg=theme.PRIMARY, font=(theme.FONT, 9, "underline"),
            cursor="hand2", activebackground=bg)
        self.photo_label = tk.Label(photo_box, text="required", bg=bg,
                                    fg=theme.MUTED, font=(theme.FONT, 8),
                                    anchor="w")
        self.photo_label.pack(anchor="w", pady=(3, 0))

        # column 3 - result buttons
        res_box = tk.Frame(self.frame, bg=bg)
        res_box.grid(row=0, column=3, sticky="w", padx=6, pady=8)
        self.result_buttons = {}
        for code in RESULTS:
            btn = tk.Button(
                res_box, text=code, relief="flat", bd=0, width=4,
                font=(theme.FONT, 9, "bold"), cursor="arrow",
                command=lambda c=code: self.set_result(c))
            btn.pack(side="left", padx=(0, 5))
            self.result_buttons[code] = btn

        # column 4 - reason / defect
        reason_box = tk.Frame(self.frame, bg=bg)
        reason_box.grid(row=0, column=4, sticky="ew", padx=(6, 14), pady=8)
        reason_box.columnconfigure(0, weight=1)
        self.reason_var = tk.StringVar()
        self.reason_entry = ttk.Entry(reason_box, textvariable=self.reason_var,
                                      font=(theme.FONT, 10))
        self.reason_entry.grid(row=0, column=0, sticky="ew", ipady=2)
        self.reason_hint = tk.Label(reason_box, text="not needed for OK",
                                    bg=bg, fg=theme.MUTED,
                                    font=(theme.FONT, 8), anchor="w")
        self.reason_hint.grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.reason_var.trace_add("write", lambda *_: screen.refresh_progress())

        self._lock_results()
        self._lock_reason()

    # --- photo -----------------------------------------------------------
    def pick_photo(self):
        path = filedialog.askopenfilename(
            title=f"Photo for: {self.test_name}", filetypes=IMAGE_TYPES,
            parent=self.frame,
        )
        if not path:
            return
        self._apply_photo(path, is_temp=False)

    def capture_photo(self):
        if not camera.require_camera(self.frame):
            return
        dialog = camera.PhotoCaptureDialog(self.frame.winfo_toplevel(),
                                           self.test_name)
        self.frame.wait_window(dialog)
        if dialog.saved_path:
            self._apply_photo(dialog.saved_path, is_temp=True)

    def _apply_photo(self, path, is_temp):
        self._discard_old_temp_photo()
        self.photo_path = path
        self.is_temp_photo = is_temp
        self.photo_btn.configure(text="Change photo")
        label = "Captured just now" if is_temp else self._short_name(path)
        self.photo_label.configure(text=label, fg=theme.OK_COLOR)
        self.view_btn.pack(side="left", padx=(6, 0))
        self._unlock_results()
        self.screen.refresh_progress()

    def _discard_old_temp_photo(self):
        """Delete the previous captured-photo temp file, if any, once it's
        replaced by a new choice - otherwise retakes pile up on disk."""
        if self.is_temp_photo and self.photo_path and \
                os.path.exists(self.photo_path):
            try:
                os.remove(self.photo_path)
            except OSError:
                pass

    def view_photo(self):
        if self.photo_path and os.path.exists(self.photo_path):
            open_file(self.photo_path)
        else:
            messagebox.showwarning("Photo missing",
                                   "That photo file is no longer on disk. "
                                   "Attach it again.")

    @staticmethod
    def _short_name(path, limit=18):
        name = os.path.basename(path)
        return name if len(name) <= limit else name[:limit - 3] + "..."

    # --- result ----------------------------------------------------------
    def _lock_results(self):
        for btn in self.result_buttons.values():
            btn.configure(bg="#E3E8ED", fg=theme.DISABLED, state="disabled",
                          activebackground="#E3E8ED", cursor="arrow",
                          disabledforeground=theme.DISABLED)

    def _unlock_results(self):
        for code, btn in self.result_buttons.items():
            colour = theme.RESULT_COLORS[code]
            btn.configure(state="normal", cursor="hand2",
                          bg=self.bg, fg=colour,
                          activebackground=colour, activeforeground="#FFFFFF",
                          highlightbackground=colour, highlightthickness=1,
                          bd=0)
        self._paint_results()

    def _paint_results(self):
        for code, btn in self.result_buttons.items():
            colour = theme.RESULT_COLORS[code]
            if code == self.result:
                btn.configure(bg=colour, fg="#FFFFFF", activebackground=colour)
            else:
                btn.configure(bg=self.bg, fg=colour, activebackground=colour)

    def set_result(self, code):
        if not self.photo_path:
            messagebox.showinfo(
                "Photo first",
                "Attach the photo for this test before setting a result.")
            return
        self.result = code
        self._paint_results()
        self.stripe.configure(bg=theme.RESULT_COLORS[code])
        if code == "OK":
            self._lock_reason()
        else:
            self._unlock_reason(code)
        self.screen.refresh_progress()

    # --- reason ----------------------------------------------------------
    def _lock_reason(self):
        self.reason_var.set("")
        self.reason_entry.state(["disabled"])
        self.reason_hint.configure(text="not needed for OK", fg=theme.MUTED)

    def _unlock_reason(self, code):
        self.reason_entry.state(["!disabled"])
        label = ("NG reason - required" if code == "NG"
                 else "Rework defect - required")
        self.reason_hint.configure(text=label, fg=theme.RESULT_COLORS[code])
        self.reason_entry.focus_set()

    # --- state -----------------------------------------------------------
    @property
    def reason(self):
        return self.reason_var.get().strip()

    def is_complete(self):
        if not self.photo_path or not self.result:
            return False
        if self.result in ("NG", "RW") and not self.reason:
            return False
        return True

    def problem(self):
        if not self.photo_path:
            return "photo missing"
        if not self.result:
            return "result not selected"
        if self.result in ("NG", "RW") and not self.reason:
            return ("NG reason not filled" if self.result == "NG"
                    else "rework defect not filled")
        return ""

    def to_record(self):
        return {
            "test_order": self.index + 1,
            "test_name": self.test_name,
            "result": self.result,
            "reason": self.reason,
            "photo_path": self.photo_path,
        }


class ChecksheetScreen(ttk.Frame):
    def __init__(self, parent, app, checksheet_key, unit_fields):
        super().__init__(parent)
        self.app = app
        self.sheet = app.checksheets[checksheet_key]
        self.unit_fields = unit_fields
        self.rows = []
        self._build()

    def _build(self):
        serial = self.unit_fields.get("serial_number", "")
        board = self.unit_fields.get("main_board_no", "")

        def back_btn(parent):
            ttk.Button(parent, text="Discard and exit",
                       command=self.confirm_exit).pack(side="left")

        widgets.header_bar(
            self, self.sheet.name,
            f"Serial {serial}   |   Main board {board}", [back_btn])

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=24, pady=(16, 0))

        top = ttk.Frame(body)
        top.pack(fill="x")
        ttk.Label(top, text="Test results", style="Head.TLabel").pack(
            side="left")
        self.progress = ttk.Label(top, text="", style="Muted.TLabel")
        self.progress.pack(side="right")

        ttk.Label(body, text="Attach the photo taken after each test, then set "
                             "the result. NG and RW need a written reason.",
                  style="Muted.TLabel").pack(anchor="w", pady=(4, 12))

        # column headings
        head = tk.Frame(body, bg=theme.BG)
        head.pack(fill="x")
        head.columnconfigure(1, weight=3, minsize=230)
        head.columnconfigure(2, minsize=250)
        head.columnconfigure(3, minsize=210)
        head.columnconfigure(4, weight=2, minsize=230)
        tk.Frame(head, bg=theme.BG, width=4).grid(row=0, column=0)
        for col, text in ((1, "Test"), (2, "Photo"), (3, "Result"),
                          (4, "NG reason / RW defect")):
            tk.Label(head, text=text, bg=theme.BG, fg=theme.MUTED,
                     font=(theme.FONT, 9, "bold")).grid(
                row=0, column=col, sticky="w",
                padx=(14 if col == 1 else 6, 6), pady=(0, 6))

        scroll = widgets.ScrollFrame(body, bg=theme.BORDER)
        scroll.pack(fill="both", expand=True)
        scroll.body.columnconfigure(0, weight=1)

        for idx, test_name in enumerate(self.sheet.tests):
            self.rows.append(TestRow(self, scroll.body, idx, test_name))

        footer = ttk.Frame(self)
        footer.pack(fill="x", padx=24, pady=14)
        self.footer_note = ttk.Label(footer, text="", style="Muted.TLabel")
        self.footer_note.pack(side="left")
        self.save_btn = ttk.Button(footer, text="Save inspection",
                                   style="Primary.TButton",
                                   command=self.save)
        self.save_btn.pack(side="right")

        self.refresh_progress()

    # --- progress --------------------------------------------------------
    def refresh_progress(self):
        done = sum(1 for r in self.rows if r.is_complete())
        total = len(self.rows)
        self.progress.configure(text=f"{done} of {total} tests complete")
        if done == total:
            self.footer_note.configure(
                text="All tests complete - ready to save.")
        else:
            self.footer_note.configure(
                text=f"{total - done} test(s) still incomplete.")

    # --- save ------------------------------------------------------------
    def save(self):
        incomplete = [(r.index + 1, r.test_name, r.problem())
                      for r in self.rows if not r.is_complete()]
        if incomplete:
            preview = "\n".join(f"  {n}. {name} - {why}"
                                for n, name, why in incomplete[:10])
            more = ("\n  ...and %d more" % (len(incomplete) - 10)
                    if len(incomplete) > 10 else "")
            messagebox.showwarning(
                "Inspection not complete",
                f"{len(incomplete)} test(s) still need attention:\n\n"
                f"{preview}{more}", parent=self)
            return

        missing_files = [r.test_name for r in self.rows
                         if not os.path.exists(r.photo_path)]
        if missing_files:
            messagebox.showerror(
                "Photo files missing",
                "These photos are no longer on disk. Attach them again:\n\n"
                + "\n".join(missing_files[:8]), parent=self)
            return

        try:
            records = self._copy_photos()
        except OSError as exc:
            messagebox.showerror("Could not store photos", str(exc),
                                 parent=self)
            return

        user = self.app.current_user
        insp_id, overall = database.save_inspection(
            self.sheet.key, self.sheet.name, self.unit_fields, records,
            user["id"], user["full_name"] or user["username"],
        )

        counts = {c: sum(1 for r in self.rows if r.result == c)
                  for c in RESULTS}
        messagebox.showinfo(
            "Inspection saved",
            f"Record #{insp_id} saved.\n\n"
            f"Sheet: {self.sheet.name}\n"
            f"Serial: {self.unit_fields.get('serial_number')}\n"
            f"Overall: {overall}\n"
            f"OK {counts['OK']}   NG {counts['NG']}   RW {counts['RW']}",
            parent=self)
        self.app.show_select()

    def _copy_photos(self):
        """Copy every attached photo into photos/<sheet>/<serial>_<stamp>/."""
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        serial = self.unit_fields.get("serial_number", "unit")
        safe_serial = "".join(ch for ch in serial
                              if ch.isalnum() or ch in "-_") or "unit"
        folder = os.path.join(PHOTO_ROOT, self.sheet.key,
                              f"{safe_serial}_{stamp}")
        os.makedirs(folder, exist_ok=True)

        records = []
        for row in self.rows:
            rec = row.to_record()
            ext = os.path.splitext(row.photo_path)[1] or ".jpg"
            safe_test = "".join(ch if ch.isalnum() else "_"
                                for ch in row.test_name)[:40].strip("_")
            dest = os.path.join(folder,
                                f"{row.index + 1:02d}_{safe_test}{ext}")
            shutil.copy2(row.photo_path, dest)
            rec["photo_path"] = os.path.relpath(dest, BASE_DIR)
            records.append(rec)
            if row.is_temp_photo:
                try:
                    os.remove(row.photo_path)
                except OSError:
                    pass
        return records

    def confirm_exit(self):
        touched = any(r.photo_path or r.result for r in self.rows)
        if touched and not messagebox.askyesno(
                "Discard this inspection?",
                "Nothing has been saved yet. Leaving now loses the entries "
                "made on this sheet.\n\nDiscard and go back?", parent=self):
            return
        self._discard_all_temp_photos()
        self.app.show_select()

    def _discard_all_temp_photos(self):
        for row in self.rows:
            if row.is_temp_photo and row.photo_path and \
                    os.path.exists(row.photo_path):
                try:
                    os.remove(row.photo_path)
                except OSError:
                    pass
