"""
The gaze overlay - a transparent, always-on-top, fullscreen window with
just one thing on it: a circle that follows wherever your calibrated
gaze is currently pointing. This is what makes "look at something,
then blink to select it" actually visible/usable - without this,
gaze_target_region/screen_x/screen_y in last_tracking_data are just
numbers nobody can see.

Like debug_window.py, this doesn't touch the camera itself - it just
reads whatever the main GUI's loop already computed, on its own timer.

The "transparent" trick: on Windows, a Tkinter window can declare one
specific color as "click-through and invisible" via -transparentcolor.
We fill the whole background with that color and only draw the circle
in a different color, so everything except the circle itself is
see-through, and mouse clicks pass right through to whatever's
actually underneath the overlay.
"""

import time
import tkinter as tk

from src import config


class GazeOverlay:
    def __init__(self, parent, get_tracking_data):
        """
        parent - the main Tk root, used as this Toplevel's parent
        get_tracking_data - zero-arg function returning the latest
            tracking data dict, same pattern as StatsForNerdsWindow.
        """
        self.get_tracking_data = get_tracking_data
        self._closed = False
        self._last_blink_select_count = 0
        self._flash_until = 0.0  # time.monotonic() timestamp; circle flashes while now < this

        self.window = tk.Toplevel(parent)
        self.window.overrideredirect(True)  # no title bar/border - just the circle
        self.window.attributes("-topmost", True)  # always stays above other windows

        screen_w = self.window.winfo_screenwidth()
        screen_h = self.window.winfo_screenheight()
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.window.geometry(f"{screen_w}x{screen_h}+0+0")

        # Anything drawn in "black" becomes see-through and click-through -
        # this only works reliably on Windows, which is what this project
        # targets. If it's ever run somewhere this isn't supported, the
        # window just falls back to showing as solid black instead of
        # crashing outright.
        try:
            self.window.attributes("-transparentcolor", "black")
        except tk.TclError:
            pass
        self.window.configure(bg="black")

        self.canvas = tk.Canvas(
            self.window, bg="black", highlightthickness=0,
            width=screen_w, height=screen_h,
        )
        self.canvas.pack(fill="both", expand=True)

        self.circle_id = None
        self._refresh()

    def _refresh(self):
        if self._closed:
            return

        data = self.get_tracking_data() or {}
        region = data.get("gaze_target_region")
        norm_x = data.get("gaze_target_screen_x")
        norm_y = data.get("gaze_target_screen_y")
        blink_count = data.get("blink_select_count", 0)

        # A selection just happened if the counter moved since our last
        # look at it - that's how we know to flash, even though we're
        # polling independently instead of being told directly.
        if blink_count > self._last_blink_select_count:
            self._flash_until = time.monotonic() + (config.GAZE_OVERLAY_FLASH_DURATION_MS / 1000)
        self._last_blink_select_count = blink_count

        if self.circle_id is not None:
            self.canvas.delete(self.circle_id)
            self.circle_id = None

        if region is not None and norm_x is not None and norm_y is not None:
            px = int(norm_x * self.screen_w)
            py = int(norm_y * self.screen_h)
            r = config.GAZE_OVERLAY_CIRCLE_RADIUS

            is_flashing = time.monotonic() < self._flash_until
            color = config.GAZE_OVERLAY_FLASH_COLOR if is_flashing else config.GAZE_OVERLAY_COLOR

            self.circle_id = self.canvas.create_oval(
                px - r, py - r, px + r, py + r,
                outline=color, width=4,
            )

        self.window.after(config.GAZE_OVERLAY_UPDATE_RATE_MS, self._refresh)

    def close(self):
        self._closed = True
        self.window.destroy()