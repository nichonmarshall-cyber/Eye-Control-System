"""
The "Stats for Nerds" debug window - a separate popup showing a bunch
of internal tracking numbers that aren't useful for a regular user but
are handy while tuning calibration and tracking.

Important: this window does NOT read the camera or run its own
detection loop. It just displays whatever the main GUI's loop already
computed (see EyeAbleGUI.latest_tracking_data), refreshed on its own
slower timer. That keeps us from ever reading the webcam twice per
frame - camera access stays owned entirely by the main loop.
"""

import tkinter as tk

from src import config


class StatsForNerdsWindow:
    # (data_key, label_text) pairs, in display order. Keeping this as
    # a list of tuples instead of a dict so the order stays stable.
    FIELDS = [
        ("gaze_direction", "Gaze direction (fixed thresholds)"),
        ("calibrated_gaze_direction", "Gaze direction (calibrated)"),
        ("raw_horizontal_ratio", "Horizontal ratio"),
        ("raw_vertical_ratio", "Vertical ratio"),
        ("left_horizontal_ratio", "Left eye horizontal"),
        ("right_horizontal_ratio", "Right eye horizontal"),
        ("left_vertical_ratio", "Left eye vertical"),
        ("right_vertical_ratio", "Right eye vertical"),
        ("horizontal_ratio", "Smoothed horizontal"),
        ("vertical_ratio", "Smoothed vertical"),
        ("face_detected", "Face detected"),
        ("both_eyes_visible", "Both eyes visible"),
        ("face_width_px", "Face width (px)"),
        ("face_width_ratio", "Face width ratio"),
        ("inter_eye_distance_px", "Inter-eye distance (px)"),
        ("head_yaw", "Head yaw"),
        ("head_pitch", "Head pitch"),
        ("head_roll", "Head roll"),
        ("position_status", "Position status"),
        ("tracking_quality", "Tracking quality"),
        ("tracking_quality_reason", "Tracking reason"),
        ("current_calibration_point_text", "Calibration point"),
        ("calibration_samples_text", "Calibration samples"),
        ("calibration_complete", "Calibration completed"),
        ("both_eyes_closed", "Eyes closed (blink)"),
        ("eyes_closed_ms", "Eyes closed duration"),
        ("blink_select_count", "Blink selects"),
    ]

    def __init__(self, parent, get_tracking_data, on_close_callback=None):
        """
        parent - the main Tk root, used as this Toplevel's parent
        get_tracking_data - zero-arg function returning the latest
            tracking data dict. We pull from this on our own timer
            instead of the main loop pushing to us, so the main loop
            doesn't need to know this window exists.
        on_close_callback - called when the window closes, so the GUI
            can clear its reference and allow a fresh window next time.
        """
        self.get_tracking_data = get_tracking_data
        self.on_close_callback = on_close_callback
        self._closed = False

        self.window = tk.Toplevel(parent)
        self.window.title("EyeAble - Stats for Nerds")
        self.window.geometry("440x560")
        self.window.configure(bg=config.WINDOW_BG)
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

        self._vars = {}
        self._build_layout()
        self._refresh()

    def _build_layout(self):
        container = tk.Frame(self.window, bg=config.WINDOW_BG)
        container.pack(fill="both", expand=True, padx=14, pady=14)

        for row, (key, label_text) in enumerate(self.FIELDS):
            name_label = tk.Label(
                container, text=f"{label_text}:", anchor="w",
                fg=config.TEXT_COLOR, bg=config.WINDOW_BG,
                font=("Consolas", 10),
            )
            name_label.grid(row=row, column=0, sticky="w", pady=2)

            value_var = tk.StringVar(value="N/A")
            value_label = tk.Label(
                container, textvariable=value_var, anchor="e",
                fg=config.ACCENT_COLOR, bg=config.WINDOW_BG,
                font=("Consolas", 10, "bold"),
            )
            value_label.grid(row=row, column=1, sticky="e", pady=2)

            self._vars[key] = value_var

        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)

    def _refresh(self):
        if self._closed:
            return

        data = self.get_tracking_data() or {}

        for key, _ in self.FIELDS:
            self._vars[key].set(self._format(key, data.get(key)))

        # Reschedule ourselves - this timer is independent of the main
        # camera loop, it just re-reads whatever's already there.
        self.window.after(config.DEBUG_UPDATE_RATE_MS, self._refresh)

    @staticmethod
    def _format(key, value):
        if value is None:
            return "N/A"

        if key in ("face_detected", "both_eyes_visible", "calibration_complete"):
            return "Yes" if value else "No"

        if key in ("head_yaw", "head_pitch", "head_roll"):
            return f"{value:.1f}\u00b0"
        
        if key in ("face_detected", "both_eyes_visible", "calibration_complete", "both_eyes_closed"):
            return "Yes" if value else "No"

        if key in ("face_width_px", "inter_eye_distance_px", "eyes_closed_ms"):
            return f"{value:.1f}"

        if isinstance(value, float):
            return f"{value:.3f}"

        return str(value)

    def focus(self):
        """Brings the window to the front instead of opening a duplicate."""
        self.window.lift()
        self.window.focus_force()

    def _on_close(self):
        self._closed = True
        self.window.destroy()
        if self.on_close_callback:
            self.on_close_callback()

    
    # TODO: gaze_tracker.predict_screen_region() (predicted region name,
    # normalized/pixel screen X and Y) isn't shown anywhere in this
    # window yet, on purpose - see the matching TODO in gui.py. Once
    # that's wired up, this is probably the natural place to add those
    # fields to FIELDS above.