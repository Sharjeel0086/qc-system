"""Quality Cross-Check System - application entry point.

Run this file (F5 in Visual Studio Code) to start the program.

Flow:  sign in  ->  choose check sheet  ->  unit details  ->  tests  ->  save
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import auth            # noqa: E402
import config_loader   # noqa: E402
import database        # noqa: E402
import theme           # noqa: E402
from screens.builder_screen import BuilderScreen        # noqa: E402
from screens.checksheet_screen import ChecksheetScreen  # noqa: E402
from screens.details_screen import DetailsScreen        # noqa: E402
from screens.login_screen import LoginScreen            # noqa: E402
from screens.records_screen import RecordsScreen        # noqa: E402
from screens.select_screen import SelectScreen          # noqa: E402


class QCApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Quality Cross-Check System - LED Unit Inspection")
        self.geometry("1180x760")
        self.minsize(1040, 660)
        self.configure(bg=theme.BG)

        theme.apply_styles(self)

        self.current_user = None
        self.current_screen = None

        database.init_db()
        try:
            self.checksheets = config_loader.load_checksheets()
        except config_loader.ConfigError as exc:
            messagebox.showerror("Check sheet configuration problem", str(exc))
            self.destroy()
            raise SystemExit(1)

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self._build_menu()
        self.show_login()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # --- navigation ------------------------------------------------------
    def _swap(self, screen):
        if self.current_screen is not None:
            self.current_screen.destroy()
        self.current_screen = screen
        screen.pack(fill="both", expand=True)

    def show_login(self):
        self.current_user = None
        self._swap(LoginScreen(self.container, self))

    def show_select(self):
        self._require_login()
        self._swap(SelectScreen(self.container, self))

    def show_details(self, checksheet_key):
        self._require_login()
        self._swap(DetailsScreen(self.container, self, checksheet_key))

    def show_checksheet(self, checksheet_key, unit_fields):
        self._require_login()
        self._swap(ChecksheetScreen(self.container, self, checksheet_key,
                                    unit_fields))

    def show_records(self):
        self._require_login()
        self._swap(RecordsScreen(self.container, self))

    def show_builder(self):
        self._require_login()
        if self.current_user["role"] != "admin":
            messagebox.showwarning(
                "Not allowed",
                "Only an admin can change the check sheets.")
            return
        self._swap(BuilderScreen(self.container, self))

    def logout(self):
        if messagebox.askyesno("Sign out", "Sign out of the system?"):
            self.show_login()

    def _require_login(self):
        if self.current_user is None:
            self.show_login()
            raise RuntimeError("Not signed in")

    # --- menu ------------------------------------------------------------
    def _build_menu(self):
        menubar = tk.Menu(self)

        users = tk.Menu(menubar, tearoff=0)
        users.add_command(label="Add inspector...", command=self.add_user)
        users.add_command(label="Change my password...",
                          command=self.change_password)
        users.add_separator()
        users.add_command(label="Sign out", command=self.logout)
        menubar.add_cascade(label="Users", menu=users)

        tools = tk.Menu(menubar, tearoff=0)
        tools.add_command(label="Check sheet builder...",
                          command=self.open_builder)
        tools.add_command(label="Reload check sheets from file",
                          command=self.reload_config)
        tools.add_command(label="Open photo folder",
                          command=self.open_photo_folder)
        tools.add_command(label="Camera diagnostics...",
                          command=self.show_camera_diagnostics)
        menubar.add_cascade(label="Tools", menu=tools)

        helpm = tk.Menu(menubar, tearoff=0)
        helpm.add_command(label="About", command=self.about)
        menubar.add_cascade(label="Help", menu=helpm)

        self.configure(menu=menubar)

    def add_user(self):
        if self.current_user is None:
            messagebox.showinfo("Sign in first",
                                "Sign in before adding an inspector.")
            return
        if self.current_user["role"] != "admin":
            messagebox.showwarning("Not allowed",
                                   "Only an admin can add inspectors.")
            return
        username = simpledialog.askstring("Add inspector", "Username:",
                                          parent=self)
        if not username:
            return
        full_name = simpledialog.askstring("Add inspector", "Full name:",
                                           parent=self) or ""
        password = simpledialog.askstring("Add inspector", "Password:",
                                          show="*", parent=self)
        if not password:
            return
        try:
            database.create_user(username, password, full_name)
            messagebox.showinfo("Inspector added",
                                f"{username} can now sign in.")
        except Exception as exc:
            messagebox.showerror("Could not add inspector", str(exc))

    def change_password(self):
        if self.current_user is None:
            messagebox.showinfo("Sign in first",
                                "Sign in before changing a password.")
            return
        old = simpledialog.askstring("Change password", "Current password:",
                                     show="*", parent=self)
        if old is None:
            return
        if auth.authenticate(self.current_user["username"], old) is None:
            messagebox.showerror("Wrong password",
                                 "The current password does not match.")
            return
        new = simpledialog.askstring("Change password", "New password:",
                                     show="*", parent=self)
        if not new or len(new) < 4:
            messagebox.showerror("Password too short",
                                 "Use at least 4 characters.")
            return
        database.set_password(self.current_user["username"], new)
        messagebox.showinfo("Password changed",
                            "Use the new password next time you sign in.")

    def open_builder(self):
        if self.current_user is None:
            messagebox.showinfo("Sign in first",
                                "Sign in before editing the check sheets.")
            return
        self.show_builder()

    def reload_config(self):
        try:
            self.checksheets = config_loader.load_checksheets()
        except config_loader.ConfigError as exc:
            messagebox.showerror("Check sheet configuration problem", str(exc))
            return
        messagebox.showinfo(
            "Check sheets reloaded",
            f"{len(self.checksheets)} check sheet(s) loaded.")
        if self.current_user is not None:
            self.show_select()

    def open_photo_folder(self):
        from screens.checksheet_screen import PHOTO_ROOT, open_file
        os.makedirs(PHOTO_ROOT, exist_ok=True)
        open_file(PHOTO_ROOT)

    def show_camera_diagnostics(self):
        import camera
        messagebox.showinfo("Camera diagnostics", camera.diagnostics_text())

    def about(self):
        messagebox.showinfo(
            "About",
            "Quality Cross-Check System\n"
            "LED unit inspection check sheets\n\n"
            "Python + Tkinter + SQLite\n"
            "Check sheets are defined in data/checksheets.json")

    def on_close(self):
        if isinstance(self.current_screen, BuilderScreen) and \
                self.current_screen.dirty:
            if not messagebox.askyesno(
                    "Close the program?",
                    "The check sheet builder has unsaved changes. Close "
                    "anyway?"):
                return
        if isinstance(self.current_screen, ChecksheetScreen):
            if not messagebox.askyesno(
                    "Close the program?",
                    "The open inspection has not been saved. Close anyway?"):
                return
            self.current_screen._discard_all_temp_photos()
        self.destroy()


def main():
    app = QCApp()
    app.mainloop()


if __name__ == "__main__":
    main()
