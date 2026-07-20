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

import cv2
from PIL import Image, ImageTk

from src import config
from src.camera import Camera
from src.gaze_tracker import GazeTracker
from src.calibration import CalibrationWindow
from src.debug_window import StatsForNerdsWindow


class EyeAbleGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(config.WINDOW_TITLE)
        self.root.configure(bg=config.WINDOW_BG)
        self.root.resizable(False, False)

        self.camera = Camera()
        self.gaze_tracker = GazeTracker()

        self.running = False
        self.calibration_active = False  # True while CalibrationWindow owns the camera
        self._update_job = None
        self.stats_window = None
        self.latest_tracking_data = {}

        self._build_layout()

    def _build_layout(self):
        # Video preview shows up here
        self.video_label = tk.Label(self.root, bg="black")
        self.video_label.grid(row=0, column=0, columnspan=4, padx=10, pady=10)

        # Shows "Gaze: LEFT" / "Gaze: CENTER" / etc.
        self.gaze_label = tk.Label(
            self.root,
            text="Gaze: ---",
            font=("Arial", 20, "bold"),
            fg=config.ACCENT_COLOR,
            bg=config.WINDOW_BG,
        )
        self.gaze_label.grid(row=1, column=0, columnspan=4, pady=(0, 4))

        # Horizontal/vertical ratio numbers - these stay visible in the
        # main window on purpose (not just buried in Stats for Nerds),
        # since they're useful for quick day-to-day testing.
        self.ratio_label = tk.Label(
            self.root,
            text="Horizontal: --- | Vertical: ---",
            font=("Consolas", 11),
            fg="#aaaaaa",
            bg=config.WINDOW_BG,
        )
        self.ratio_label.grid(row=2, column=0, columnspan=4, pady=(0, 10))

        # The four buttons
        self.start_button = tk.Button(self.root, text="Start", width=12, command=self.start)
        self.start_button.grid(row=3, column=0, padx=5, pady=5)

        self.stop_button = tk.Button(self.root, text="Stop", width=12, command=self.stop)
        self.stop_button.grid(row=3, column=1, padx=5, pady=5)

        self.calibrate_button = tk.Button(
            self.root, text="Calibrate", width=12, command=self.open_calibration
        )
        self.calibrate_button.grid(row=3, column=2, padx=5, pady=5)

        self.exit_button = tk.Button(self.root, text="Exit", width=12, command=self.exit_app)
        self.exit_button.grid(row=3, column=3, padx=5, pady=5)

        self.stats_button = tk.Button(
            self.root, text="Stats for Nerds", width=52, command=self.open_stats_window
        )
        self.stats_button.grid(row=4, column=0, columnspan=4, padx=5, pady=(0, 10))

        # TODO: Add accessibility settings panel (font size, high
        # contrast mode, colorblind-friendly colors, etc.)
        # TODO: Add gaze-based menu navigation once we actually build
        # gaze-to-menu logic - right now this is just buttons you click.

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
        # Make sure the camera's actually running before we try to calibrate
        if not self.camera.is_running():
            success = self.camera.start()
            if not success:
                self.gaze_label.config(text="Gaze: Camera Error")
                return
            self.running = True
        """
        Pause our frame loop while the calibration runs, only
        one thing should be reading the camera frames at a time.
        see _resume_after_calibration for how this gets undone.
        """

        self._pause_main_loop()

        CalibrationWindow(
            self.root,
            self.camera,
            self.gaze_tracker,
            on_complete=self._resume_after_calibration,
            on_cancel=self._resume_after_calibration,
        )

    def _pause_main_loop(self):
        #Stops us from reading camera frames while calibration takes over - see open_calibration.
        self.calibration_active = True
        if self._update_job is not None:
            self.root.after_cancel(self._update_job)
            self._update_job = None
    
    def _resume_after_calibration(self, _calibration_data = None):
        """
        Called by CalibrationWindow (as either on_complete or on_cancel)
        once it's done with the camera - hands control back to our own
        frame loop. _calibration_data isn't used here (we read the real
        result straight off gaze_tracker.screen_calibration whenever we
        need it), it's just accepted so this one method can be passed as
        both callbacks even though on_complete calls it with data and
        on_cancel calls it with none.
        """
        self.calibration_active=False
        if self.running:
            self._update_frame()

    def open_stats_window(self):
        # Don't open a second window, just bring the existing one forward.
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
        # This is basically our main loop - grabs a frame, runs gaze
        # detection, updates the UI, then schedules itself to run again
        # in a few milliseconds. Keeps going as long as self.running is True.
        if not self.running or self.calibration_active:
            return

        success, frame = self.camera.read_frame()
        if success:
            frame, gaze_direction, raw_ratio = self.gaze_tracker.process_frame(frame)

            calibrated_gaze_direction = self.gaze_tracker.last_tracking_data.get("calibrated_gaze_direction", "...")
            self.gaze_label.config(text=f"Gaze: {calibrated_gaze_direction}")

            if raw_ratio is not None:
                h_ratio, v_ratio = raw_ratio
                self.ratio_label.config(text=f"h: {h_ratio:.2f} | v: {v_ratio:.2f}")
            else:
                self.ratio_label.config(text="h: --- | v: ---")

            # Stash the rich tracking data dict so the Stats for Nerds
            # window (if open) can read it without touching the camera
            # itself. process_frame() already rebuilt this dict above.

            self.latest_tracking_data = self.gaze_tracker.last_tracking_data

            # Converting the OpenCV frame into something Tkinter can actually display
            display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(display_frame)
            photo = ImageTk.PhotoImage(image=image)
            self.video_label.imgtk = photo  # need to keep this reference or Tkinter garbage-collects the image and the video goes blank
            self.video_label.config(image=photo)
        else:
            self.gaze_label.config(text="Gaze: No Frame")

        # TODO: Improve performance - e.g. skip some frames, resize
        # before processing, or move the face detection onto a
        # separate thread so the whole GUI doesn't lag on slower machines.

        self._update_job = self.root.after(config.GUI_UPDATE_DELAY_MS, self._update_frame)

    # TODO: Add blink-based confirmation so a blink can "select" something.
    # TODO: Actually connect gaze direction to menu navigation (e.g.
    # holding LEFT/RIGHT gaze for a bit selects a menu item).
    # TODO: Add audio feedback (like a beep or text-to-speech) when
    # gaze direction or selection changes.
    # TODO: gaze_tracker.predict_screen_region() is fully implemented
    # and tested but nothing in this file ever calls it - there's no
    # predicted screen position shown anywhere yet. Once calibration
    # is done, wire it up somewhere visible (Stats for Nerds is the
    # obvious first spot) to actually see whether it can tell the nine
    # regions apart.


