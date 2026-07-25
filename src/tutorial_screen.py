"""
The tutorial screen - a short three-step walkthrough that shows the
user how to use EyeAble before they start tracking for real. Each step
has a live camera preview on the left (so the user can position
themselves) and instructions on the right, with Previous / Next
navigation and a progress indicator at the bottom.

Steps:
  1. Position Yourself - get in frame, good lighting
  2. Calibration      - follow the dots so the app learns your gaze
  3. Blink to Select  - hold your gaze on a button, then blink

The live preview reuses the controller's existing camera loop rather
than opening the webcam a second time. When this screen is shown it
points the controller's video output at its own preview label and
starts tracking; when the user leaves, it stops again. That keeps
camera access owned entirely by the controller, same as every other
screen.
"""

import os
import tkinter as tk

from PIL import Image, ImageTk

from src import config


BG_WHITE = "#ffffff"
BG_PANEL = "#f5f5f5"
TEXT_DARK = "#1a2b4a"
TEXT_LABEL = "#333333"
ACCENT_BLUE = "#0078D7"
DOT_ACTIVE = "#1a2b4a"
DOT_INACTIVE = "#cccccc"


# The three steps, in order. Each is a (title, body) pair. Keeping this
# as a list so adding or reordering steps is just editing this one spot.
STEPS = [
    (
        "Step 1: Position Yourself",
        "Position yourself in front of the camera.\n"
        "Make sure your face is clearly visible and well-lit.\n"
        "Sit about 20-28 in (50-70 cm) away and keep your head steady.",
    ),
    (
        "Step 2: Calibration",
        "Calibration teaches EyeAble where you are looking.\n"
        "A series of dots will appear around the screen - just follow\n"
        "each one with your eyes until calibration is complete.",
    ),
    (
        "Step 3: Blink to Select",
        "Once calibrated, look at any button to highlight it.\n"
        "To select it, hold your gaze on it and do a deliberate,\n"
        "held blink. Quick everyday blinks won't select anything.",
    ),
]


class TutorialScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_WHITE)

        self.controller = controller
        self._icon_cache = {}
        self._step = 0            # index into STEPS
        self._dots = []           # progress-dot labels, filled in _build_body

        self._build_header()
        self._build_body()
        self._build_footer()

        self._show_step(0)

    def _build_header(self):
        header = tk.Frame(self, bg=BG_WHITE, height=80)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        left = tk.Frame(header, bg=BG_WHITE)
        left.pack(side="left", padx=20, pady=10)

        logo = self._load_icon("logo.png", (50, 50))
        if logo is not None:
            tk.Label(left, image=logo, bg=BG_WHITE).pack(side="left", padx=(0, 12))

        tk.Label(left, text="|", font=("Arial", 20),
                 fg="#cccccc", bg=BG_WHITE).pack(side="left", padx=8)

        title_frame = tk.Frame(left, bg=BG_WHITE)
        title_frame.pack(side="left")
        tk.Label(title_frame, text="Tutorial", font=("Arial", 20, "bold"),
                 fg=TEXT_DARK, bg=BG_WHITE).pack(anchor="w")
        self.step_counter = tk.Label(title_frame, text="Step 1 of 3",
                                     font=("Arial", 11), fg=TEXT_LABEL, bg=BG_WHITE)
        self.step_counter.pack(anchor="w")

        # Divider under the header
        line = tk.Canvas(self, height=2, bg=BG_WHITE, highlightthickness=0)
        line.pack(fill="x")
        line.create_line(0, 0, 2000, 0, fill="#cccccc", width=2)

    def _build_body(self):
        body = tk.Frame(self, bg=BG_WHITE)
        body.pack(fill="both", expand=True, padx=40, pady=25)

        # Left: big live camera preview, label above it
        left = tk.Frame(body, bg=BG_WHITE)
        left.pack(side="left", fill="both", expand=True)

        tk.Label(left, text="Camera Preview", font=("Arial", 14, "bold"),
                 fg=TEXT_DARK, bg=BG_WHITE).pack(anchor="w", pady=(20, 12))

        # Fixed-size frame so the preview stays big even before the first
        # camera frame arrives. The controller's loop draws into cam_label
        # (see on_shown); the black box holds the space in the meantime.
        preview_box = tk.Frame(left, bg="black", width=560, height=420)
        preview_box.pack(anchor="w")
        preview_box.pack_propagate(False)

        self.cam_label = tk.Label(preview_box, bg="black")
        self.cam_label.pack(fill="both", expand=True)

        # Right: step title + instructions
        right = tk.Frame(body, bg=BG_WHITE)
        right.pack(side="right", fill="both", expand=True, padx=(40, 0))

        self.step_title = tk.Label(right, text="", font=("Arial", 20, "bold"),
                                   fg=ACCENT_BLUE, bg=BG_WHITE, justify="left")
        self.step_title.pack(anchor="w", pady=(40, 18))

        self.step_body = tk.Label(right, text="", font=("Arial", 14),
                                  fg=TEXT_LABEL, bg=BG_WHITE, justify="left")
        self.step_body.pack(anchor="w")

    def _build_footer(self):
        footer = tk.Frame(self, bg=BG_WHITE, height=110)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        # Progress dots (Step 1 / 2 / 3), centered
        dot_row = tk.Frame(footer, bg=BG_WHITE)
        dot_row.pack(pady=(15, 10))
        for i in range(len(STEPS)):
            dot = tk.Label(dot_row, text="●", font=("Arial", 16),
                           fg=DOT_INACTIVE, bg=BG_WHITE)
            dot.pack(side="left", padx=8)
            self._dots.append(dot)

        # Previous / Next on the sides, Back to Home in the middle
        nav = tk.Frame(footer, bg=BG_WHITE)
        nav.pack()

        self.prev_button = tk.Button(nav, text="←  Previous", font=("Arial", 12),
                                     bg=BG_WHITE, relief="solid", bd=1,
                                     padx=18, pady=8, command=self._on_previous)
        self.prev_button.pack(side="left", padx=8)

        self.home_button = tk.Button(nav, text="🏠  Back to Home", font=("Arial", 12),
                                     bg=BG_WHITE, relief="solid", bd=1,
                                     padx=18, pady=8, command=self._finish)
        self.home_button.pack(side="left", padx=8)

        self.next_button = tk.Button(nav, text="Next  →", font=("Arial", 12),
                                     bg=BG_WHITE, relief="solid", bd=1,
                                     padx=18, pady=8, command=self._on_next)
        self.next_button.pack(side="left", padx=8)

    # ---- Navigation ----

    def _show_step(self, index):
        self._step = index
        title, body = STEPS[index]
        self.step_title.config(text=title)
        self.step_body.config(text=body)
        self.step_counter.config(text=f"Step {index + 1} of {len(STEPS)}")

        # Update the progress dots
        for i, dot in enumerate(self._dots):
            dot.config(fg=DOT_ACTIVE if i <= index else DOT_INACTIVE)

        # Previous is disabled on the first step; the last step's Next
        # button becomes "Finish" so it's clear the walkthrough is done.
        self.prev_button.config(state="normal" if index > 0 else "disabled")
        if index == len(STEPS) - 1:
            self.next_button.config(text="Finish  ✓")
        else:
            self.next_button.config(text="Next  →")

    def _on_next(self):
        if self._step < len(STEPS) - 1:
            self._show_step(self._step + 1)
        else:
            self._finish()

    def _on_previous(self):
        if self._step > 0:
            self._show_step(self._step - 1)

    def _finish(self):
        """Leave the tutorial and go back to the Home menu."""
        self.on_hidden()
        self.controller.show_frame("SecondScreen")

    # ---- Camera lifecycle ----

    def on_shown(self):
        """
        Called by the controller when this screen becomes visible. Points
        the controller's video output at our preview label and starts the
        camera loop, then resets to step one.
        """
        self.controller.video_label = self.cam_label
        self.controller.start()
        self._show_step(0)

    def on_hidden(self):
        """
        Called when leaving the tutorial. Stops tracking so the webcam
        isn't left running, and clears the preview so a stale frame
        doesn't linger.
        """
        self.controller.stop()
        self.cam_label.config(image="")

    # ---- Helpers ----

    def _load_icon(self, filename, size):
        path = os.path.join("src", "assets", filename)
        try:
            img = Image.open(path).resize(size, Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self._icon_cache[filename] = photo
            return photo
        except Exception:
            return None