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
from src.gaze_overlay import GazeOverlay


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
        self.gaze_overlay = None
        self.latest_tracking_data = {}

        # Gaze-selection state. _gaze_selectable_buttons is the list of
        # widgets a held blink can activate - the final dashboard can
        # register its own buttons here later without touching the
        # selection logic itself. _last_handled_blink_count starts as
        # None so a blink count left over from a previous run doesn't
        # fire a phantom selection the moment tracking starts.
        self._gaze_selectable_buttons = []
        self._gaze_highlighted_button = None
        self._last_handled_blink_count = None

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
        self.start_button = tk.Button(self.root, text="Start", width=12, height=2, font=("Arial", 11), command=self.start)
        self.start_button.grid(row=3, column=0, padx=8, pady=8)

        self.stop_button = tk.Button(self.root, text="Stop", width=12, height=2, font=("Arial", 11), command=self.stop)
        self.stop_button.grid(row=3, column=1, padx=8, pady=8)

        self.calibrate_button = tk.Button(
            self.root, text="Calibrate", width=12, height=2, font=("Arial, 11"), command=self.open_calibration
        )
        self.calibrate_button.grid(row=3, column=2, padx=8, pady=8)

        self.exit_button = tk.Button(self.root, text="Exit", width=12, height=2, font=("Arial", 11), command=self.exit_app)
        self.exit_button.grid(row=3, column=3, padx=8, pady=8)

        self.stats_button = tk.Button(
            self.root, text="Stats for Nerds", width=52, height=2, font=("Arial", 11), command=self.open_stats_window
        )
        self.stats_button.grid(row=4, column=0, columnspan=4, padx=5, pady=(0, 10))

        self.overlay_button = tk.Button(
            self.root, text="Show Gaze Overlay", width=52, height=2, font=("Arial", 11), command=self.toggle_gaze_overlay
        )
        self.overlay_button.grid(row=5, column=0, columnspan=4, padx=5, pady=(0, 10))

        self._register_gaze_selectable(
            self.start_button, self.stop_button, self.calibrate_button,
            self.exit_button, self.stats_button, self.overlay_button,
        )

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

    def toggle_gaze_overlay(self):
        """
        Unlike Stats for Nerds (which has its own close button and just
        gets refocused if you click the button again), the overlay has
        no title bar or close button at all - overrideredirect(True)
        stripped that away on purpose, since it's meant to be a passive
        visual layer, not a window you interact with directly. That
        means THIS button is the only way to turn it on or off, so it
        has to actually toggle instead of just "open or focus."
        """
        if self.gaze_overlay is not None:
            self.gaze_overlay.close()
            self.gaze_overlay = None
            self.overlay_button.config(text="Show Gaze Overlay")
        else:
            self.gaze_overlay = GazeOverlay(self.root, lambda: self.latest_tracking_data)
            self.overlay_button.config(text="Hide Gaze Overlay")

    def _register_gaze_selectable(self, *buttons):
        """
        Marks buttons as activatable by gaze + held blink. Remembers each
        button's normal background so the hover highlight can be undone.
        Reusable: the redesigned dashboard just calls this with its own
        buttons instead of these prototype ones.
        """
        for button in buttons:
            self._gaze_selectable_buttons.append(
                {"widget": button, "normal_bg": button.cget("bg")}
            )

    def _button_at_screen_point(self, pixel_x, pixel_y):
        """Returns the registered entry whose on-screen rectangle contains the point, or None."""
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
        """Moves the visual highlight to `entry`'s button (or clears it if None)."""
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
        """
        Runs once per frame: highlights whichever selectable button the
        gaze is currently on, and when a NEW deliberate blink has
        completed (blink_select_count increased), activates the button
        under the coordinates that were frozen when that blink started.
        """
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # Live hover highlight from the current (smoothed) gaze target.
        gaze_x = data.get("gaze_target_screen_x")
        gaze_y = data.get("gaze_target_screen_y")
        if gaze_x is not None and gaze_y is not None:
            hovered = self._button_at_screen_point(gaze_x * screen_w, gaze_y * screen_h)
        else:
            hovered = None
        self._set_gaze_highlight(hovered)

        # Blink activation - only when the count moves past what we've
        # already handled, so one blink can never fire twice.
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
            # invoke() runs the button's command exactly as a mouse
            # click would. Do this last: some commands (Stop, Exit)
            # tear down the very loop we're running inside of.
            entry["widget"].invoke()


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

            self.gaze_label.config(text=f"Gaze: {gaze_direction}")

            if raw_ratio is not None:
                h_ratio, v_ratio = raw_ratio
                self.ratio_label.config(text=f"h: {h_ratio:.2f} | v: {v_ratio:.2f}")
            else:
                self.ratio_label.config(text="h: --- | v: ---")

            # Stash the rich tracking data dict so the Stats for Nerds
            # window (if open) can read it without touching the camera
            # itself. process_frame() already rebuilt this dict above.

            self.latest_tracking_data = self.gaze_tracker.last_tracking_data

            self._update_gaze_selection(self.latest_tracking_data)

            # Converting the OpenCV frame into something Tkinter can actually display
            display_frame = cv2.resize(frame, (640, 360))
            display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)

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
        
    # TODO: Add audio feedback (like a beep or text-to-speech) when
    # gaze direction or selection changes.

