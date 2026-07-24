import tkinter as tk
import cv2
from PIL import Image, ImageTk
from src import config

class TrackingScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=config.WINDOW_BG)

        self.controller = controller

        # Video preview
        self.video_label = tk.Label(self, bg="black")
        self.video_label.grid(row=0, column=0, columnspan=4, padx=10, pady=10)

        # Gaze direction
        self.gaze_label = tk.Label(
            self,
            text="Gaze: ---",
            font=("Arial", 20, "bold"),
            fg=config.ACCENT_COLOR,
            bg=config.WINDOW_BG,
        )
        self.gaze_label.grid(row=1, column=0, columnspan=4, pady=(0, 4))

        # Ratio numbers
        self.ratio_label = tk.Label(
            self,
            text="Horizontal: --- | Vertical: ---",
            font=("Consolas", 11),
            fg="#aaaaaa",
            bg=config.WINDOW_BG,
        )
        self.ratio_label.grid(row=2, column=0, columnspan=4, pady=(0, 10))

        # Buttons
        tk.Button(self, text="Start", width=12, command=controller.start).grid(row=3, column=0, padx=5, pady=5)
        tk.Button(self, text="Stop", width=12, command=controller.stop).grid(row=3, column=1, padx=5, pady=5)
        tk.Button(self, text="Calibrate", width=12, command=controller.open_calibration).grid(row=3, column=2, padx=5, pady=5)
        tk.Button(self, text="Exit", width=12, command=controller.exit_app).grid(row=3, column=3, padx=5, pady=5)

        tk.Button(
            self,
            text="Stats for Nerds",
            width=52,
            command=controller.open_stats_window
        ).grid(row=4, column=0, columnspan=4, padx=5, pady=(0, 10))

        # Expose labels so controller can update them
        controller.video_label = self.video_label
        controller.gaze_label = self.gaze_label
        controller.ratio_label = self.ratio_label
