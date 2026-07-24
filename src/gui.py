"""
The main app - controller + screen host.

EyeAbleGUI is a controller: it owns the camera, the tracker, the
tracking loop, and long-lived state. It does NOT own visible widgets
directly. Each screen (StartScreen, SecondScreen, TrackingScreen) is
its own Frame that lives inside the same container. Only one is raised
at a time; show_frame(name) picks which.

When _update_frame runs, it reaches into the registered TrackingScreen
and updates ITS labels - screens can be redesigned or swapped without
touching this file.
"""

import tkinter as tk

import cv2
from PIL import Image, ImageTk

from src import config
from src.camera import Camera
from src.gaze_tracker import GazeTracker
from src.calibration import CalibrationWindow
from src.debug_window import StatsForNerdsWindow
from src.gaze_overlay import GazeOverlay

from src.start_screen import StartScreen
from src.second_screen import SecondScreen
from src.tracking_screen import TrackingScreen


class EyeAbleGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(config.WINDOW_TITLE)
        self.root.configure(bg=config.WINDOW_BG)
        self.root.geometry("1024x600")

        self.camera = Camera()
        self.gaze_tracker = GazeTracker()

        self.running = False
        self.calibration_active = False
        self._update_job = None
        self.stats_window = None
        self.gaze_overlay = None
        self.latest_tracking_data = {}

        self._gaze_selectable_buttons = []
        self._gaze_highlighted_button = None
        self._last_handled_blink_count = None

        self.video_label = None
        self.gaze_label = None
        self.ratio_label = None

        self._build_layout()

    def _build_layout(self):
        container = tk.Frame(self.root, bg=config.WINDOW_BG)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for ScreenClass in (StartScreen, SecondScreen, TrackingScreen):
            name = ScreenClass.__name__
            frame = ScreenClass(container, self)
            frame.grid(row=0, column=0, sticky="nsew")
            self.frames[name] = frame

        self.show_frame("StartScreen")

    def show_frame(self, name):
        frame = self.frames.get(name)
        if frame is not None:
            frame.tkraise()

    def start(self):
        if self.running:
            return
        success = self.camera.start()
        if not success:
            if self.gaze_label is not None:
                self.gaze_label.config(text="Gaze: Camera Error")
            return
        self.running = True
        self._update_frame()
        if self.gaze_overlay is None:
            self.toggle_gaze_overlay()

    def stop(self):
        self.running = False
        if self._update_job is not None:
            self.root.after_cancel(self._update_job)
            self._update_job = None
        self.camera.stop()
        if self.gaze_label is not None:
            self.gaze_label.config(text="Gaze: ---")
        if self.ratio_label is not None:
            self.ratio_label.config(text="h: --- | v: ---")
        if self.video_label is not None:
            self.video_label.config(image="")
        if self.gaze_overlay is not None:
            self.toggle_gaze_overlay()

    def open_calibration(self):
        if not self.camera.is_running():
            success = self.camera.start()
            if not success:
                if self.gaze_label is not None:
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

    def toggle_gaze_overlay(self):
        if self.gaze_overlay is not None:
            self.gaze_overlay.close()
            self.gaze_overlay = None
        else:
            self.gaze_overlay = GazeOverlay(self.root, lambda: self.latest_tracking_data)

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

            calibrated_direction = self.gaze_tracker.last_tracking_data.get(
                "calibrated_gaze_direction", "..."
            )
            if self.gaze_label is not None:
                self.gaze_label.config(text=f"Gaze: {calibrated_direction}")

            if self.ratio_label is not None:
                if raw_ratio is not None:
                    h_ratio, v_ratio = raw_ratio
                    self.ratio_label.config(text=f"h: {h_ratio:.2f} | v: {v_ratio:.2f}")
                else:
                    self.ratio_label.config(text="h: --- | v: ---")

            self.latest_tracking_data = self.gaze_tracker.last_tracking_data
            self._update_gaze_selection(self.latest_tracking_data)

            if self.video_label is not None:
                display_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                display_frame = cv2.resize(display_frame, (640, 360))
                image = Image.fromarray(display_frame)
                photo = ImageTk.PhotoImage(image=image)
                self.video_label.imgtk = photo
                self.video_label.config(image=photo) \
                
        else:
            if self.gaze_label is not None:
                self.gaze_label.config(text="Gaze: No Frame")

        self._update_job = self.root.after(config.GUI_UPDATE_DELAY_MS, self._update_frame)

    def _register_gaze_selectable(self, *buttons):
        for button in buttons:
            self._gaze_selectable_buttons.append(
                {"widget": button, "normal_bg": button.cget("bg")}
            )

    def _button_at_screen_point(self, pixel_x, pixel_y):
        for entry in self._gaze_selectable_buttons:
            widget = entry["widget"]
            if not widget.winfo_ismapped():
                continue
            x = widget.winfo_rootx()
            y = widget.winfo_rooty()
            if x <= pixel_x <= x + widget.winfo_width() and y <= pixel_y <= y + widget.winfo_height():
                return entry
        return None

    def _set_gaze_highlight(self, entry):
        if self._gaze_highlighted_button is entry:
            return
        if self._gaze_highlighted_button is not None:
            old_widget = self._gaze_highlighted_button["widget"]
            if old_widget.winfo_exists():
                old_widget.config(bg=self._gaze_highlighted_button["normal_bg"])
        if entry is not None:
            entry["widget"].config(bg=config.GAZE_HIGHLIGHT_COLOR)
        self._gaze_highlighted_button = entry

    def _update_gaze_selection(self, data):
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        gaze_x = data.get("gaze_target_screen_x")
        gaze_y = data.get("gaze_target_screen_y")
        if gaze_x is not None and gaze_y is not None:
            hovered = self._button_at_screen_point(gaze_x * screen_w, gaze_y * screen_h)
        else:
            hovered = None
        self._set_gaze_highlight(hovered)

        blink_count = data.get("blink_select_count", 0)
        if self._last_handled_blink_count is None:
            self._last_handled_blink_count = blink_count
            return
        if blink_count <= self._last_handled_blink_count:
            return
        self._last_handled_blink_count = blink_count

        select_x = data.get("blink_select_target_screen_x")
        select_y = data.get("blink_select_target_screen_y")
        if select_x is None or select_y is None:
            return

        entry = self._button_at_screen_point(select_x * screen_w, select_y * screen_h)
        if entry is not None:
            entry["widget"].invoke()