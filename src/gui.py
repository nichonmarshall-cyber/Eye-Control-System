"""
The main app window - this is what actually shows up on screen.

Has a live video preview, a label showing the current gaze direction,
and four buttons: Start, Stop, Calibrate, Exit. That's the whole UI
for now. Not pretty, just functional for the demo.

This file is the only one that reads the camera during noraml
 tracking(see_update_frame). The stats for nerds window just 
 reads off this one. During calibration this loop pauses entirely
 and CalibrationWindow becomes the only thing reading the frames,
 so we never have two things fighting over the camera.
"""

import tkinter as tk

from src import config
from src.camera import Camera
from src.gaze_tracker import GazeTracker
from src.calibration import CalibrationWindow
from src.debug_window import StatsForNerdsWindow

from src.start_screen import StartScreen
from src.second_screen import SecondScreen
from src.tracking_screen import TrackingScreen


class EyeAbleGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(config.WINDOW_TITLE)
        self.root.configure(bg=config.WINDOW_BG)
        self.root.resizable(False, False)

        # --- Screen container ---
        container = tk.Frame(self.root)
        container.pack(fill="both", expand=True)

        self.frames = {}

        # Create screens
        for ScreenClass, name in [
            (StartScreen, "StartScreen"),
            (SecondScreen, "SecondScreen"),
            (TrackingScreen, "TrackingScreen"),
        ]:
            frame = ScreenClass(container, self)
            self.frames[name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
            container.grid_rowconfigure(0, weight=1)
            container.grid_columnconfigure(0, weight=1)


        # Show StartScreen first
        self.show_frame("StartScreen")

        # --- Tracking system ---
        self.camera = Camera()
        self.gaze_tracker = GazeTracker()

        self.running = False
        self.calibration_active = False
        self._update_job = None
        self.stats_window = None
        self.latest_tracking_data = {}

    # --- Screen switching ---
    def show_frame(self, name):
        frame = self.frames[name]
        frame.tkraise()

    # --- Tracking logic (unchanged) ---
    def start(self):
        if self.running:
            return

        success = self.camera.start()
        if not success:
            self.gaze_label.config(text="Gaze: Camera Error")
            return

        self.running = True
        self._update_frame()

    def stop(self):
        self.running = False
        if self._update_job is not None:
            self.root.after_cancel(self._update_job)
            self._update_job = None
        self.camera.stop()
        self.gaze_label.config(text="Gaze: ---")
        self.ratio_label.config(text="h: --- | v: ---")
        self.video_label.config(image="")

    def open_calibration(self):
        if not self.camera.is_running():
            success = self.camera.start()
            if not success:
                self.gaze_label.config(text="Gaze: Camera Error")
                return
            self.running = True

        self._pause_main_loop()

        CalibrationWindow(
            self.root,
            self.camera,
            self.gaze_tracker,
            on_complete=self._resume_after_calibration,
            on_cancel=self._resume_after_calibration,
        )

    def _pause_main_loop(self):
        self.calibration_active = True
        if self._update_job is not None:
            self.root.after_cancel(self._update_job)
            self._update_job = None

    def _resume_after_calibration(self, _calibration_data=None):
        self.calibration_active = False
        if self.running:
            self._update_frame()

    def open_stats_window(self):
        if self.stats_window is not None:
            self.stats_window.focus()
            return

        self.stats_window = StatsForNerdsWindow(
            self.root,
            lambda: self.latest_tracking_data,
            on_close_callback=self._on_stats_window_closed,
        )

    def _on_stats_window_closed(self):
        self.stats_window = None

    def exit_app(self):
        self.stop()
        self.gaze_tracker.close()
        self.root.destroy()

    def _update_frame(self):
        if not self.running or self.calibration_active:
            return

        success, frame = self.camera.read_frame()
        if success:
            frame, gaze_direction, raw_ratio = self.gaze_tracker.process_frame(frame)

            self.gaze_label.config(text=f"Gaze: {gaze_direction}")

            if raw_ratio is not None:
                h_ratio, v_ratio = raw_ratio
                self.ratio_label.config(text=f"h: {h_ratio:.2f} | v: {v_ratio:.2f}")
            else:
                self.ratio_label.config(text="h: --- | v: ---")

            self.latest_tracking_data = self.gaze_tracker.last_tracking_data

            display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(display_frame)
            photo = ImageTk.PhotoImage(image=image)
            self.video_label.imgtk = photo
            self.video_label.config(image=photo)
        else:
            self.gaze_label.config(text="Gaze: No Frame")

        self._update_job = self.root.after(config.GUI_UPDATE_DELAY_MS, self._update_frame)
