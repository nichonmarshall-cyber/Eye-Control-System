"""
The main app window - this is what actually shows up on screen.

Has a live video preview, a label showing the current gaze direction,
and four buttons: Start, Stop, Calibrate, Exit. That's the whole UI
for now. Not pretty, just functional for the demo.
"""

import tkinter as tk

import cv2
from PIL import Image, ImageTk

from src import config
from src.camera import Camera
from src.gaze_tracker import GazeTracker
from src.calibration import CalibrationWindow


class EyeAbleGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(config.WINDOW_TITLE)
        self.root.configure(bg=config.WINDOW_BG)
        self.root.resizable(False, False)

        self.camera = Camera()
        self.gaze_tracker = GazeTracker()

        self.running = False
        self._update_job = None

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
        self.gaze_label.grid(row=1, column=0, columnspan=4, pady=(0, 10))

        # The four buttons
        self.start_button = tk.Button(self.root, text="Start", width=12, command=self.start)
        self.start_button.grid(row=2, column=0, padx=5, pady=10)

        self.stop_button = tk.Button(self.root, text="Stop", width=12, command=self.stop)
        self.stop_button.grid(row=2, column=1, padx=5, pady=10)

        self.calibrate_button = tk.Button(
            self.root, text="Calibrate", width=12, command=self.open_calibration
        )
        self.calibrate_button.grid(row=2, column=2, padx=5, pady=10)

        self.exit_button = tk.Button(self.root, text="Exit", width=12, command=self.exit_app)
        self.exit_button.grid(row=2, column=3, padx=5, pady=10)

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
        self.video_label.config(image="")

    def open_calibration(self):
        # Make sure the camera's actually running before we try to calibrate
        if not self.camera.is_running():
            success = self.camera.start()
            if not success:
                self.gaze_label.config(text="Gaze: Camera Error")
                return
            self.running = True
            self._update_frame()

        CalibrationWindow(self.root, self.camera, self.gaze_tracker)

    def exit_app(self):
        self.stop()
        self.gaze_tracker.close()
        self.root.destroy()

    def _update_frame(self):
        # This is basically our main loop - grabs a frame, runs gaze
        # detection, updates the UI, then schedules itself to run again
        # in a few milliseconds. Keeps going as long as self.running is True.
        if not self.running:
            return

        success, frame = self.camera.read_frame()
        if success:
            frame, gaze_direction, _ = self.gaze_tracker.process_frame(frame)

            self.gaze_label.config(text=f"Gaze: {gaze_direction}")

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
