"""Step 1 - sign in."""

import tkinter as tk
from tkinter import ttk

import auth
import theme


class LoginScreen(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        wrap = ttk.Frame(self)
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        card = tk.Frame(wrap, bg=theme.SURFACE, highlightbackground=theme.BORDER,
                        highlightthickness=1)
        card.pack()

        pad = tk.Frame(card, bg=theme.SURFACE)
        pad.pack(padx=44, pady=40)

        tk.Label(pad, text="Quality Cross-Check System", bg=theme.SURFACE,
                 fg=theme.INK, font=(theme.FONT, 19, "bold")).pack(anchor="w")
        tk.Label(pad, text="LED unit inspection - sign in to continue",
                 bg=theme.SURFACE, fg=theme.MUTED,
                 font=(theme.FONT, 10)).pack(anchor="w", pady=(4, 26))

        tk.Label(pad, text="Username", bg=theme.SURFACE, fg=theme.INK,
                 font=(theme.FONT, 10)).pack(anchor="w")
        self.user_var = tk.StringVar()
        self.user_entry = ttk.Entry(pad, textvariable=self.user_var, width=34,
                                    font=(theme.FONT, 11))
        self.user_entry.pack(fill="x", pady=(4, 16), ipady=3)

        tk.Label(pad, text="Password", bg=theme.SURFACE, fg=theme.INK,
                 font=(theme.FONT, 10)).pack(anchor="w")
        self.pass_var = tk.StringVar()
        self.pass_entry = ttk.Entry(pad, textvariable=self.pass_var, show="*",
                                    width=34, font=(theme.FONT, 11))
        self.pass_entry.pack(fill="x", pady=(4, 6), ipady=3)

        self.show_var = tk.BooleanVar(value=False)
        tk.Checkbutton(pad, text="Show password", variable=self.show_var,
                       command=self._toggle_show, bg=theme.SURFACE,
                       fg=theme.MUTED, activebackground=theme.SURFACE,
                       selectcolor=theme.SURFACE, bd=0, highlightthickness=0,
                       font=(theme.FONT, 9)).pack(anchor="w", pady=(0, 14))

        self.error = tk.Label(pad, text="", bg=theme.SURFACE, fg=theme.NG_COLOR,
                              font=(theme.FONT, 9), wraplength=300,
                              justify="left")
        self.error.pack(anchor="w", pady=(0, 8))

        btn = tk.Button(pad, text="Sign in", command=self.attempt_login,
                        bg=theme.PRIMARY, fg="#FFFFFF", relief="flat", bd=0,
                        font=(theme.FONT, 11, "bold"), cursor="hand2", pady=9,
                        activebackground=theme.PRIMARY_DARK,
                        activeforeground="#FFFFFF")
        btn.pack(fill="x")

        tk.Label(pad, text="First run? Use admin / admin123 and change it "
                           "from the Users menu.", bg=theme.SURFACE,
                 fg=theme.MUTED, font=(theme.FONT, 8), wraplength=310,
                 justify="left").pack(anchor="w", pady=(18, 0))

        self.user_entry.focus_set()
        for widget in (self.user_entry, self.pass_entry):
            widget.bind("<Return>", lambda _e: self.attempt_login())

    def _toggle_show(self):
        self.pass_entry.configure(show="" if self.show_var.get() else "*")

    def attempt_login(self):
        self.error.configure(text="")
        user = auth.authenticate(self.user_var.get(), self.pass_var.get())
        if user is None:
            self.error.configure(
                text="That username and password combination was not "
                     "recognised. Check both and try again.")
            self.pass_var.set("")
            self.pass_entry.focus_set()
            return
        self.app.current_user = user
        self.app.show_select()
