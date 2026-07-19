"""
The calibration popup window - nine-point SCREEN calibration.

This replaces the old "look LEFT, click Capture" 5-direction popup.
Instead, it walks the user through looking at nine dots placed around
their actual screen (corners, edge midpoints, and dead center), and
for each one collects a batch of valid gaze samples while they hold
their gaze on the dot. Those samples get reduced down to one median
reading per point (see GazeTracker.apply_screen_calibration_point) -
that's the foundation for eventually predicting roughly WHERE on the
screen someone's looking, instead of just a rough LEFT/CENTER/RIGHT
direction.

Important: this window does NOT run alongside the main GUI's camera
loop. While it's open, the main GUI pauses its own frame reading (see
EyeAbleGUI.open_calibration) and this window becomes the only thing
reading camera frames until it's done or cancelled. Only one thing
should ever be reading the webcam at a time.
"""

import tkinter as tk
from tkinter import messagebox

from src import config


class CalibrationWindow:
    def __init__(self, parent, camera, gaze_tracker, on_complete=None, on_cancel=None):
        self.parent = parent
        self.camera = camera
        self.gaze_tracker = gaze_tracker
        self.on_complete = on_complete
        self.on_cancel = on_cancel

        self._cancelled = False
        self._finished = False

        self.target_names = config.CALIBRATION_TARGET_NAMES
        self.current_index = 0
        self.settling_frames_seen = 0
        self.current_samples = []

        self.gaze_tracker.reset_screen_calibration()

        self.window = tk.Toplevel(parent)
        self.window.title("EyeAble - Screen Calibration")
        self.window.configure(bg="black")

        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        self.screen_w = screen_w
        self.screen_h = screen_h

        """
        Try to go fullscreen so that the dots line up with the actual screen.
        if thats not supported fall back to a bug window instead of crashing
        """

        try:
            self.window.attributes("-fullscreen", True)
        except tk.TclError:
            self.window.geometry(f"{screen_w}x{screen_h}+0+0")

        self.window.bind("<Escape>", lambda event: self._cancel())
        self.window.protocol("WM_DELETE_WINDOW",self._cancel)

        self.canvas = tk.Canvas(
            self.window, bg="black", highlightthickness=0,
            width=screen_w, height=screen_h,
        )

        self.canvas.pack(fill="both", expand=True)

        self.instruction_text_id = self.canvas.create_text(
            screen_w // 2, 60,
            text="",fill="white", font=("Arial", 22, "bold"),
        )

        self.progress_text_id = self.canvas.create_text(
            screen_w // 2, 100,
            text="",fill="#aaaaaa", font=("Arial", 14),
        )

        self.canvas.create_text(
            screen_w // 2, screen_h - 40,
            text="Keep your head still and look directly at the dot - press ESC to cancel",
            fill="#666666", font=("Arial", 11),
        )

        self.dot_id = None
        self.warning_text_id = self.canvas.create_text(
            screen_w // 2, screen_h - 80,
            text = "", fill="#e07b38", font=("Arial", 12, "bold")
        )
        
        self._start_current_point()

    def _start_current_point(self):
        if self._cancelled or self._finished:
            return
        # Once we've gone through all of the 9 points, we're done.
        if self.current_index >= len(self.target_names):
            self._finish_calibration()
            return
        
        target_name = self.target_names[self.current_index]
        self.settling_frames_seen = 0
        self.current_samples = []
        self.gaze_tracker.start_screen_calibration_point(target_name)

        norm_x, norm_y = config.CALIBRATION_TARGET_POSITIONS[target_name]
        px = int(norm_x * self.screen_w)
        py = int(norm_y * self.screen_h)

        if self.dot_id is not None:
            self.canvas.delete(self.dot_id)

        r = config.CALIBRATION_DOT_RADIUS
        self.dot_id = self.canvas.create_oval(
            px - r, py - r, px + r, py + r,
            fill=config.ACCENT_COLOR, outline="white", width=2,
        )

        readable_name = target_name.replace("_"," ").title()
        self.canvas.itemconfig(self.instruction_text_id, text=f"Look at the dot - {readable_name}")
        self._update_progress_text()

        self.window.after(config.GUI_UPDATE_DELAY_MS, self._tick)

    def _update_progress_text(self, warning=""):
        """
        Refreshes the "Point X of 9 | Samples Y of 45" text and the
        small warning line underneath it. warning is whatever reason
        _frame_is_valid_for_calibration gave for skipping the current
        frame (or "" to clear it once frames start counting again).
        """
        self.canvas.itemconfig(
            self.progress_text_id,
            text=(
                f"Point {self.current_index + 1} of {len(self.target_names)}   |   "
                f"Samples {len(self.current_samples)} of {config.CALIBRATION_SAMPLES_PER_POINT}"
            ),
        )
        self.canvas.itemconfig(self.warning_text_id, text=warning)
        
    """
    # ---------------------------------------------------------------
    Main per-frame tick. Runs off window.after() so it never blocks
    the Tkinter event loop - this is what replaces the old
    click-a-button-to-grab-one-frame approach with something that
    automatically collects samples over time.
    ---------------------------------------------------------------
    """
    
    def _tick(self):
        if self._cancelled or self._finished:
            return

        success, frame = self.camera.read_frame()
        if not success:
            # Camera hiccup - just try again next tick instead of
            # crashing the whole calibration run.
            self.window.after(config.GUI_UPDATE_DELAY_MS, self._tick)
            return

        self.gaze_tracker.process_frame(frame)
        data = self.gaze_tracker.last_tracking_data

        if self.settling_frames_seen < config.CALIBRATION_SETTLING_FRAMES:
            # Still letting the user's eyes travel to the new dot -
            # these frames don't count toward anything either way.
            self.settling_frames_seen += 1
            self.window.after(config.GUI_UPDATE_DELAY_MS, self._tick)
            return

        is_valid, reason = self._frame_is_valid_for_calibration(data)
        if is_valid:
            self.current_samples.append({
                "horizontal_ratio": data["raw_horizontal_ratio"],
                "vertical_ratio": data["raw_vertical_ratio"],
                "left_horizontal_ratio": data["left_horizontal_ratio"],
                "right_horizontal_ratio": data["right_horizontal_ratio"],
                "left_vertical_ratio": data["left_vertical_ratio"],
                "right_vertical_ratio": data["right_vertical_ratio"],
                "face_width_ratio": data["face_width_ratio"],
                "head_yaw": data["head_yaw"],
                "head_pitch": data["head_pitch"],
            })
            self.gaze_tracker.record_calibration_progress(len(self.current_samples))
            self._update_progress_text()
        else:
            # Don't count this frame, but let the user know why so
            # they're not just staring at a stalled progress counter.
            self._update_progress_text(warning=reason)

        if len(self.current_samples) >= config.CALIBRATION_SAMPLES_PER_POINT:
            target_name = self.target_names[self.current_index]
            self.gaze_tracker.apply_screen_calibration_point(target_name, self.current_samples)
            self.current_index += 1
            self._start_current_point()
            return

        self.window.after(config.GUI_UPDATE_DELAY_MS, self._tick)

    @staticmethod
    def _frame_is_valid_for_calibration(data):
        """
        Only count a frame toward calibration if tracking looks solid -
        face found, both eyes visible, ratios actually came back, the
        user's at a reasonable distance from the camera, and their
        head isn't turned/tilted too far. Keeps one bad frame (blink,
        head turn, whatever) from skewing a calibration point.

        Returns (is_valid, reason) - reason is only used to show the
        user something useful when a frame gets skipped.
        """
        if not data.get("face_detected"):
            return False, "No face detected"

        if not data.get("both_eyes_visible"):
            return False, "Make sure both eyes are visible"

        if data.get("raw_horizontal_ratio") is None or data.get("raw_vertical_ratio") is None:
            return False, "Waiting for a clear gaze reading"

        face_width_ratio = data.get("face_width_ratio")
        if face_width_ratio is None:
            return False, "Can't measure face distance"
        if face_width_ratio < config.MIN_FACE_WIDTH_RATIO:
            return False, "Move closer to the camera"
        if face_width_ratio > config.MAX_FACE_WIDTH_RATIO:
            return False, "Move farther from the camera"

        head_yaw = data.get("head_yaw")
        if head_yaw is not None and abs(head_yaw) > config.MAX_CALIBRATION_HEAD_YAW:
            return False, "Face the camera more directly"

        head_pitch = data.get("head_pitch")
        if head_pitch is not None and abs(head_pitch) > config.MAX_CALIBRATION_HEAD_PITCH_DEVIATION:
            return False, "Keep your head level"

        return True, ""
    
    def _finish_calibration(self):
        """
        Called once all nine points have been captured. By this point
        gaze_tracker.screen_calibration is already fully populated (see
        apply_screen_calibration_point, called from _tick as each point
        finishes) - this method's job is just cleanup: mark ourselves
        finished, clear the "currently calibrating" marker, notify
        whoever's listening, and close the window.
        """
        self._finished = True
        self.gaze_tracker.current_calibration_point = None

        if self.on_complete:
            self.on_complete(self.gaze_tracker.screen_calibration)

        self.window.destroy()

    def _cancel(self):
        """
        Bails out of calibration early - wired up to both the ESC key
        and the window's close button. The `if self._finished: return`
        guard exists so this can't double-fire if ESC gets pressed in
        the split second after calibration already legitimately
        finished on its own.
        """
        if self._finished:
            return
        self._cancelled = True
        self.gaze_tracker.current_calibration_point = None

        if self.on_cancel:
            self.on_cancel()

        self.window.destroy()

        
    # TODO: Let the user redo a single point instead of restarting the
    # whole LEFT/CENTER/RIGHT sequence if they mess one up.
    # TODO: Save calibration data per user so people don't have to
    # recalibrate every single time they open the app. right now when 
    # they open the calibration window it starts over new.
