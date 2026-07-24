"""
The main tracking dashboard - what the user sees while tracking is
running. Three big tiles on the left (Computer, Files, Mail) that can
be gaze-selected, a sidebar on the right showing what the user is
currently looking at plus tracking settings, and Pause / Stop /
Re-calibrate controls scattered where they belong.

The three tiles don't actually launch anything - they're placeholders
that show a "Selection Confirmed" popup when activated. That's enough
to demo the gaze + blink flow end-to-end without needing real OS
integration; wiring them to real actions is separate work.
"""

import os
import tkinter as tk

from PIL import Image, ImageTk

from src import config


# Colors used only inside this screen - kept local since nothing else
# in the app cares about the dashboard's specific palette. If we ever
# theme the whole app, these get promoted to config.
BG_WHITE = "#ffffff"
BG_PANEL = "#f5f5f5"
TEXT_DARK = "#1a2b4a"
TEXT_LABEL = "#333333"
HIGHLIGHT_BLUE = "#3a6ea5"     # matches config.GAZE_HIGHLIGHT_COLOR
SELECTION_GREEN = "#4caf50"


class DashboardScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_WHITE)

        self.controller = controller
        self._icon_cache = {}                     # keep ImageTk refs alive
        self._selection_confirmation_after = None # after() job for auto-hide

        self._build_header()
        self._build_body()
        self._build_footer()

    def _build_header(self):
        header = tk.Frame(self, bg=BG_WHITE, height=90)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        left = tk.Frame(header, bg=BG_WHITE)
        left.pack(side="left", padx=20, pady=10)

        logo = self._load_icon("logo.png", (60, 60))
        tk.Label(left, image=logo, bg=BG_WHITE).pack(side="left", padx=(0, 12))

        title_frame = tk.Frame(left, bg=BG_WHITE)
        title_frame.pack(side="left")
        tk.Label(title_frame, text="EyeAble", font=("Arial", 22, "bold"),
                 fg=TEXT_DARK, bg=BG_WHITE).pack(anchor="w")
        tk.Label(title_frame, text="Eye Control System", font=("Arial", 11),
                 fg=TEXT_DARK, bg=BG_WHITE).pack(anchor="w")

        right = tk.Frame(header, bg=BG_WHITE)
        right.pack(side="right", padx=20)

        self.pause_button = tk.Button(
            right, text="⏸  Pause", font=("Arial", 11),
            bg=BG_WHITE, relief="solid", bd=1,
            padx=18, pady=10, command=self._on_pause,
        )
        self.pause_button.pack(side="left", padx=5)

        self.stop_button = tk.Button(
            right, text="■  Stop", font=("Arial", 11),
            bg=BG_WHITE, relief="solid", bd=1,
            padx=18, pady=10, command=self._on_stop,
        )
        self.stop_button.pack(side="left", padx=5)

        # Not a button - just a status pill. Gets flipped between
        # "Tracking: ON" and "Tracking: PAUSED" by _on_pause / on_shown.
        self.tracking_indicator = tk.Label(
            right, text="● Tracking: ON",
            font=("Arial", 11, "bold"),
            bg=BG_WHITE, fg=TEXT_DARK,
            padx=18, pady=10, relief="solid", bd=1,
        )
        self.tracking_indicator.pack(side="left", padx=5)

    def _build_body(self):
        body = tk.Frame(self, bg=BG_WHITE)
        body.pack(fill="both", expand=True)

        # Left: gray canvas area holding the three vertical tiles.
        canvas_area = tk.Frame(body, bg=BG_PANEL)
        canvas_area.pack(side="left", fill="both", expand=True)

        tile_column = tk.Frame(canvas_area, bg=BG_PANEL)
        tile_column.pack(side="left", padx=40, pady=30, fill="y")

        self.tile_computer = self._make_tile(tile_column, "computer.png", "Computer")
        self.tile_computer.pack(pady=20, expand=True)

        self.tile_files = self._make_tile(tile_column, "file.png", "Files")
        self.tile_files.pack(pady=20, expand=True)

        self.tile_mail = self._make_tile(tile_column, "mail.png", "Mail")
        self.tile_mail.pack(pady=20, expand=True)

        # Center of the canvas - stays empty until a selection is made,
        # then hosts the confirmation card via place().
        self.center_canvas = tk.Frame(canvas_area, bg=BG_PANEL)
        self.center_canvas.pack(side="left", fill="both", expand=True)

        self.confirmation_frame = tk.Frame(
            self.center_canvas, bg=BG_WHITE, relief="solid", bd=1,
        )
        self.confirmation_title = tk.Label(
            self.confirmation_frame,
            text="Selection Confirmed",
            font=("Arial", 14, "bold"),
            bg=BG_WHITE, fg=TEXT_DARK,
        )
        self.confirmation_body = tk.Label(
            self.confirmation_frame, text="",
            font=("Arial", 11), bg=BG_WHITE, fg=TEXT_LABEL,
        )

        # Right sidebar
        sidebar = tk.Frame(body, bg=BG_WHITE, width=340)
        sidebar.pack(side="right", fill="y", padx=25, pady=25)
        sidebar.pack_propagate(False)

        # --- Gaze Cursor section ---
        tk.Label(sidebar, text="Gaze Cursor", font=("Arial", 15, "bold"),
                 fg=TEXT_DARK, bg=BG_WHITE, anchor="w").pack(fill="x", pady=(0, 10))

        gaze_status_box = tk.Frame(sidebar, bg=BG_PANEL, relief="solid", bd=1)
        gaze_status_box.pack(fill="x", pady=(0, 30))

        inner = tk.Frame(gaze_status_box, bg=BG_PANEL)
        inner.pack(padx=15, pady=18)
        tk.Label(inner, text="●", font=("Arial", 28),
                 bg=BG_PANEL, fg=TEXT_DARK).pack(side="left", padx=(0, 15))

        gaze_text = tk.Frame(inner, bg=BG_PANEL)
        gaze_text.pack(side="left")
        tk.Label(gaze_text, text="Looking At:", font=("Arial", 10),
                 bg=BG_PANEL, fg=TEXT_LABEL, anchor="w").pack(fill="x")
        self.looking_at_label = tk.Label(
            gaze_text, text="Nothing",
            font=("Arial", 14, "bold"),
            bg=BG_PANEL, fg=TEXT_DARK, anchor="w",
        )
        self.looking_at_label.pack(fill="x")

        # --- Tracking Settings section ---
        tk.Label(sidebar, text="Tracking Settings", font=("Arial", 15, "bold"),
                 fg=TEXT_DARK, bg=BG_WHITE, anchor="w").pack(fill="x", pady=(0, 15))

        # Sensitivity and Cursor Speed sliders don't actually change
        # anything yet - they're placeholders for a future settings
        # system so the layout looks right in demos. Wire them into the
        # real config when there's a real config knob for them.
        tk.Label(sidebar, text="Sensitivity", font=("Arial", 11),
                 fg=TEXT_LABEL, bg=BG_WHITE, anchor="w").pack(fill="x", pady=(0, 3))
        tk.Scale(sidebar, from_=1, to=10, orient="horizontal",
                 bg=BG_WHITE, highlightthickness=0, showvalue=False,
                 troughcolor=BG_PANEL).pack(fill="x", pady=(0, 18))

        tk.Label(sidebar, text="Cursor Speed", font=("Arial", 11),
                 fg=TEXT_LABEL, bg=BG_WHITE, anchor="w").pack(fill="x", pady=(0, 3))
        tk.Scale(sidebar, from_=1, to=10, orient="horizontal",
                 bg=BG_WHITE, highlightthickness=0, showvalue=False,
                 troughcolor=BG_PANEL).pack(fill="x", pady=(0, 18))

        blink_row = tk.Frame(sidebar, bg=BG_WHITE)
        blink_row.pack(fill="x", pady=(5, 25))
        tk.Label(blink_row, text="Blink to Select", font=("Arial", 11),
                 fg=TEXT_LABEL, bg=BG_WHITE).pack(side="left")
        tk.Label(blink_row, text="✓ ON", font=("Arial", 11, "bold"),
                 fg=SELECTION_GREEN, bg=BG_WHITE).pack(side="right")

        self.recalibrate_button = tk.Button(
            sidebar, text="⊕  Re-calibrate",
            font=("Arial", 12), bg=BG_WHITE,
            relief="solid", bd=1, pady=12,
            command=self.controller.open_calibration,
        )
        self.recalibrate_button.pack(fill="x", pady=(15, 0))

    def _build_footer(self):
        # The footer is two rows: the Back-to-menu button on top and
        # the tiny "EyeAble v1.0 / tagline / Help" strip below it.
        # They're packed to side="bottom" in reverse order because that's
        # how pack works - last packed is closest to the edge.
        strip = tk.Frame(self, bg=BG_WHITE, height=32)
        strip.pack(fill="x", side="bottom")
        strip.pack_propagate(False)

        tk.Label(strip, text="ⓘ  EyeAble v1.0",
                 font=("Arial", 9), bg=BG_WHITE,
                 fg=TEXT_LABEL).pack(side="left", padx=20)
        tk.Label(strip, text="Making technology accessible for everyone.",
                 font=("Arial", 9), bg=BG_WHITE,
                 fg=TEXT_LABEL).pack(side="left", expand=True)
        tk.Label(strip, text="?  Help",
                 font=("Arial", 9), bg=BG_WHITE,
                 fg=TEXT_LABEL).pack(side="right", padx=20)

        back_row = tk.Frame(self, bg=BG_WHITE, height=70)
        back_row.pack(fill="x", side="bottom")
        back_row.pack_propagate(False)

        self.back_button = tk.Button(
            back_row, text="🏠  Back to menu",
            font=("Arial", 12), bg=BG_WHITE,
            relief="solid", bd=1, padx=30, pady=12,
            command=lambda: self.controller.show_frame("SecondScreen"),
        )
        self.back_button.pack(pady=15)

    def _load_icon(self, filename, size):
        """
        Same helper pattern as SecondScreen: loads a PNG, resizes it,
        and stashes the ImageTk reference in a cache dict so Tk doesn't
        garbage-collect it and blank out the widget it lives on.
        """
        path = os.path.join("src", "assets", filename)
        img = Image.open(path).resize(size, Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self._icon_cache[filename] = photo
        return photo

    def _make_tile(self, parent, icon_filename, label):
        """One of the three big tiles - big square button, icon on top."""
        tile = tk.Button(
            parent, bg=BG_WHITE, relief="solid", bd=1,
            width=140, height=140,
            compound="top",
            font=("Arial", 13, "bold"),
            fg=TEXT_DARK,
            command=lambda: self._on_tile_click(label),
        )
        try:
            icon = self._load_icon(icon_filename, (72, 72))
            tile.config(image=icon, text=label)
        except Exception as err:
            # Better to fall back to a text label than crash the whole
            # screen if an icon file went missing during a rename.
            print(f"[dashboard] icon failed for {icon_filename}: {err}")
            tile.config(text=f"[{label}]")
        return tile

    def _on_tile_click(self, label):
        """Fired when a tile is activated (mouse click OR blink-select)."""
        self.looking_at_label.config(text=label)
        self._show_selection_confirmation(label)

    def _show_selection_confirmation(self, label):
        """
        Pop up the "Selection Confirmed" card near the center of the
        canvas for 3 seconds. If another selection fires before the
        timer elapses, the card just updates in place and resets its
        auto-hide clock.
        """
        self.confirmation_body.config(text=f"{label} app will open.")

        self.confirmation_title.pack_forget()
        self.confirmation_body.pack_forget()

        self.confirmation_title.pack(pady=(20, 5), padx=30)
        self.confirmation_body.pack(pady=(0, 20), padx=30)
        self.confirmation_frame.place(relx=0.55, rely=0.55, anchor="center")

        if self._selection_confirmation_after is not None:
            self.after_cancel(self._selection_confirmation_after)
        self._selection_confirmation_after = self.after(
            3000, self._hide_selection_confirmation
        )

    def _hide_selection_confirmation(self):
        self.confirmation_frame.place_forget()
        self._selection_confirmation_after = None

    def _on_pause(self):
        """
        Toggle between paused and running. When paused, tracking stops
        and the button flips to "Play" so the user can resume without
        leaving the screen.
        """
        if self.controller.running:
            self.controller.stop()
            self.tracking_indicator.config(text="○ Tracking: PAUSED")
            self.pause_button.config(text="▶  Play")
        else:
            self.controller.start()
            self.tracking_indicator.config(text="● Tracking: ON")
            self.pause_button.config(text="⏸  Pause")

    def _on_stop(self):
        """Stop tracking and drop back to the Home screen."""
        self.controller.stop()
        self.controller.show_frame("SecondScreen")

    def on_shown(self):
        """
        Called by the controller every time this screen becomes visible.
        Registers our buttons with the gaze-selection layer so blink-
        select can activate them, and kicks tracking back on.
        """
        self.controller._register_gaze_selectable(
            self.tile_computer, self.tile_files, self.tile_mail,
            self.pause_button, self.stop_button, self.recalibrate_button,
            self.back_button,
        )
        self.controller.start()
        self.tracking_indicator.config(text="● Tracking: ON")