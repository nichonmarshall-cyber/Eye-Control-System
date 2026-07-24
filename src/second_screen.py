"""
The Home screen - four big tiles: Start Tracking, Calibration, Tutorial,
and Exit. Icons on top, labels on bottom, spread out in a 2x2 grid.

This is the screen users spend most of their time picking from with
their eyes, so the tiles are big on purpose - bigger targets are much
easier to hit reliably with gaze + blink, especially before calibration
is dialed in. If you shrink them, expect the blink-select accuracy to
suffer.
"""

import os
import tkinter as tk

from PIL import Image, ImageTk

from src import config


class SecondScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="white")

        self.controller = controller
        self._icon_cache = {}  # keep ImageTk refs alive so buttons don't blank out

        self._build_header()
        self._build_body()
        self._build_footer()

    def _build_header(self):
        header = tk.Frame(self, bg="white")
        header.pack(fill="x", pady=10)

        top_row = tk.Frame(header, bg="white")
        top_row.pack(fill="x", padx=10)

        # Logo
        logo = self._load_icon("logo.png", (60, 60))
        tk.Label(top_row, image=logo, bg="white").pack(side="left", padx=(0, 10))

        tk.Label(top_row, text="|", font=("Arial", 22),
                 fg="#cccccc", bg="white").pack(side="left", padx=10)

        tk.Label(
            top_row,
            text="EyeAble Control System",
            font=("Arial", 20, "bold"),
            fg="#0078D7",
            bg="white",
        ).pack(side="left", padx=10)

        tk.Label(top_row, text="|", font=("Arial", 22),
                 fg="#cccccc", bg="white").pack(side="left", padx=10)

        tk.Label(
            top_row,
            text="Welcome !\nUse your eyes to control the computer.",
            font=("Arial", 12),
            justify="left",
            bg="white",
        ).pack(side="left", padx=10)

        # Spacer pushes the status pills to the right edge
        tk.Label(top_row, bg="white").pack(side="left", expand=True)

        status_frame = tk.Frame(top_row, bg="white")
        status_frame.pack(side="right", padx=10)

        tk.Label(
            status_frame,
            text="● Tracking: OFF",
            font=("Arial", 10, "bold"),
            fg="#1a2b4a",
            bg="white",
            relief="solid",
            bd=1,
            padx=12,
            pady=6,
        ).pack(side="left", padx=5)

        tk.Button(
            status_frame,
            text="⚙  Settings",
            font=("Arial", 10),
            bg="white",
            relief="solid",
            bd=1,
            padx=12,
            pady=6,
            command=lambda: print("Settings clicked"),
        ).pack(side="left", padx=5)

        # Divider line under the header
        line = tk.Canvas(header, height=2, bg="white", highlightthickness=0)
        line.pack(fill="x", pady=5)
        line.create_line(0, 0, 2000, 0, fill="#cccccc", width=2)

    def _build_body(self):
        main = tk.Frame(self, bg="white")
        main.pack(expand=True)

        tk.Label(
            main,
            text="Home",
            font=("Arial", 28, "bold"),
            fg="#1a2b4a",
            bg="white",
        ).grid(row=0, column=0, columnspan=2, pady=(0, 6))

        tk.Label(
            main,
            text="Select an option by looking at it and blinking",
            font=("Arial", 12),
            fg="#333333",
            bg="white",
        ).grid(row=1, column=0, columnspan=2, pady=(0, 25))

        # The four tiles. Each is a big square button with the icon on
        # top and the label below - see _make_tile.
        self.btn_tracking = self._make_tile(
            main, "tracking.png", "Start Tracking",
            lambda: self.controller.show_frame("DashboardScreen"),
        )
        self.btn_tracking.grid(row=2, column=0, padx=25, pady=15)

        self.btn_calibration = self._make_tile(
            main, "calibration.png", "Calibration",
            lambda: self.controller.open_calibration(),
        )
        self.btn_calibration.grid(row=2, column=1, padx=25, pady=15)

        self.btn_tutorial = self._make_tile(
            main, "tutorial.png", "Tutorial",
            lambda: print("Tutorial clicked"),
        )
        self.btn_tutorial.grid(row=3, column=0, padx=25, pady=15)

        self.btn_exit = self._make_tile(
            main, "exit.png", "Exit",
            lambda: self.controller.exit_app(),
        )
        self.btn_exit.grid(row=3, column=1, padx=25, pady=15)

    def _build_footer(self):
        footer = tk.Frame(self, bg="white")
        footer.pack(fill="x", side="bottom", pady=5)

        tk.Label(
            footer, text="ⓘ  EyeAble v1.0",
            font=("Arial", 9), fg="#333333", bg="white",
        ).pack(side="left", padx=15)

        tk.Label(
            footer, text="Making technology accessible for everyone.",
            font=("Arial", 9), fg="#333333", bg="white",
        ).pack(side="left", expand=True)

        tk.Label(
            footer, text="?  Help",
            font=("Arial", 9), fg="#333333", bg="white",
        ).pack(side="right", padx=15)

    def _load_icon(self, filename, size):
        """
        Loads an icon PNG, resizes it, and caches the ImageTk reference
        so Tk doesn't garbage-collect it out from under the widget.
        Returns the cached image; call this with a fresh filename to get
        a new one.
        """
        path = os.path.join("src", "assets", filename)
        img = Image.open(path).resize(size, Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self._icon_cache[filename] = photo
        return photo

    def _make_tile(self, parent, icon_filename, label, command):
        """One of the four big Home tiles - icon on top, label below."""
        icon = self._load_icon(icon_filename, (72, 72))
        return tk.Button(
            parent,
            image=icon,
            text=label,
            compound="top",
            font=("Arial", 16, "bold"),
            fg="#1a2b4a",
            width=220,
            height=200,
            bg="#ffffff",
            relief="solid",
            bd=1,
            padx=20,
            pady=20,
            command=command,
        )