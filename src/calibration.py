"""
The calibration popup window.

Walks you through looking LEFT, then CENTER, then RIGHT, and grabs a
gaze sample each time you click Capture. Right now that's really all
it does - the collected data gets stored but nothing actually adjusts
based on it yet (see the TODO down in _finish_calibration).
"""

import tkinter as tk
from tkinter import messagebox

from src import config


class CalibrationWindow:
    def __init__(self, parent, camera, gaze_tracker, on_complete=None):
        self.parent = parent
        self.camera = camera
        self.gaze_tracker = gaze_tracker
        self.on_complete = on_complete

        self.window = tk.Toplevel(parent)
        self.window.title("EyeAble - Calibration")
        self.window.configure(bg=config.WINDOW_BG)
        self.window.geometry("500x300")
        self.window.grab_set()  # makes this popup "modal" so you can't click the main window while it's open

        self.current_point_index = 0
        self.collected_data = {}

        self.instruction_label = tk.Label(
            self.window,
            text="",
            font=("Arial", 18),
            fg=config.TEXT_COLOR,
            bg=config.WINDOW_BG,
        )
        self.instruction_label.pack(pady=40)

        self.status_label = tk.Label(
            self.window,
            text="Press 'Capture' while looking in the indicated direction.",
            font=("Arial", 11),
            fg=config.TEXT_COLOR,
            bg=config.WINDOW_BG,
        )
        self.status_label.pack(pady=10)

        self.capture_button = tk.Button(
            self.window, text="Capture", command=self._capture_point, width=15
        )
        self.capture_button.pack(pady=20)

        self._show_current_point()

    def _show_current_point(self):
        # Once we've gone through all the points (LEFT/CENTER/RIGHT), we're done.
        if self.current_point_index >= len(config.CALIBRATION_POINTS):
            self._finish_calibration()
            return

        point_name = config.CALIBRATION_POINTS[self.current_point_index]
        self.instruction_label.config(text=f"Look {point_name} and click Capture")

    def _capture_point(self):
        """
        Grabs one gaze reading for whatever direction we're currently
        asking about, and moves on to the next one.

        NOTE: this is a single snapshot, not an average over time -
        keeping it simple for now.
        TODO: Implement a better calibration algorithm - e.g. sample
        over a few seconds instead of a single frame, throw out weird
        outlier readings, and calibrate each eye separately instead of
        one averaged number.
        """
        success, frame = self.camera.read_frame()
        if not success:
            messagebox.showwarning("Camera Error", "Could not read from webcam.")
            return

        _, _, raw_ratio = self.gaze_tracker.process_frame(frame)

        if raw_ratio is None:
            messagebox.showwarning(
                "No Face Detected", "Please make sure your face is visible."
            )
            return

        point_name = config.CALIBRATION_POINTS[self.current_point_index]
        self.collected_data[point_name] = raw_ratio

        self.current_point_index += 1
        self._show_current_point()

    def _finish_calibration(self):
        # Hand the collected samples off to the gaze tracker. Right now
        # it just stores them and doesn't actually use them - see the
        # TODO in gaze_tracker.py's apply_calibration().
        self.gaze_tracker.apply_calibration(self.collected_data)
        messagebox.showinfo("Calibration Complete", "Calibration data captured.")

        if self.on_complete:
            self.on_complete(self.collected_data)

        self.window.destroy()

    # TODO: Let the user redo a single point instead of restarting the
    # whole LEFT/CENTER/RIGHT sequence if they mess one up.
    # TODO: Save calibration data per user so people don't have to
    # recalibrate every single time they open the app.
