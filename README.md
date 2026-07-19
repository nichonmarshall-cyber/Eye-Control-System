# EyeAble (Prototype)

EyeAble is a gaze-tracking prototype we're building for our software
engineering class. It uses your webcam to figure out roughly whether
you're looking left, center, or right, and shows that in a simple
desktop window.

**Heads up: this is just a class milestone prototype, not a finished
product.** The point is to show the core idea working end to end
(webcam → face tracking → gaze direction → UI), not to have every
feature done. A bunch of stuff is intentionally left as TODOs for
whoever picks it up next.

## Tech Stack

- Python
- OpenCV (webcam capture)
- MediaPipe (face/eye landmark detection)
- Tkinter (the GUI)
- Built and tested on Windows, no GPU needed

## Project Structure

```
EyeAble/
│
├── main.py                # run this to start the app
├── requirements.txt
├── README.md
├── src/
│   ├── camera.py           # webcam on/off, grabbing frames
│   ├── gaze_tracker.py      # the actual face/eye/gaze detection logic
│   ├── calibration.py       # the look-left/center/right calibration popup
│   ├── debug_window.py      # "Stats for Nerds" debug panel
│   ├── gui.py               # the Tkinter window and buttons
│   ├── utils.py             # small helper functions
│   └── config.py            # all the constants/settings in one place
```

## Running It

```
pip install -r requirements.txt
python main.py
```

That should pop up a window with your webcam feed, a "Gaze: ..." label,
and Start / Stop / Calibrate / Exit buttons.

The required MediaPipe model file (`face_landmarker.task`) is included
in the `models/` folder. If it is missing, the application downloads it
automatically the first time `main.py` runs.so you'll need internet for 
that. After that it's cached in a `models/` folder and works offline.

## Completed Features

- Webcam opens and streams to the GUI
- Face detection + eye/iris landmark tracking (MediaPipe)
- Left/center/right/up/down gaze estimation (fixed-threshold, still the
  fallback/diagnostic system - see Current Limitations)
- **Nine-point screen calibration** - walks through 9 dots placed around
  the screen (corners, edge midpoints, center), automatically collects
  and median-samples valid gaze readings per point, with quality gating
  (rejects frames where eyes aren't visible, face is too close/far, or
  head is turned/tilted too much)
- **First-stage nearest-point screen-region prediction**
  (`GazeTracker.predict_screen_region()`) once calibration is done -
  implemented and tested, not wired into the UI yet (see Future Work)
- **Head pose estimation** (yaw/pitch/roll) via OpenCV's `solvePnP`,
  used to reject bad calibration samples and flag poor tracking
  conditions
- **Face-distance guidance** - rough "move closer/farther" status based
  on how wide your face appears in the frame, plus a check against your
  calibrated distance once you've calibrated
- **"Stats for Nerds" debug window** - a separate popup with a big set
  of live tracking numbers (per-eye ratios, face width, head pose,
  tracking quality and why, calibration progress, etc.), doesn't touch
  the camera itself
- Start / Stop / Calibrate / Exit / Stats for Nerds buttons
- Live video preview with little dots showing what's being tracked
- Current gaze direction, plus the raw horizontal/vertical ratio
  numbers, always visible in the main window
- Code split up by responsibility (camera / tracking / calibration /
  debug window / GUI / config) so it's hopefully not too painful to
  work on different parts at once

## Current Limitations

- The LEFT/CENTER/RIGHT/UP/DOWN direction system still runs on fixed
  global thresholds - the nine-point calibration collects real
  per-person data now, but nothing feeds it back into those thresholds
  yet, so everyone still gets the same `GAZE_LEFT_THRESHOLD` etc.
  regardless of their eyes/face
- `predict_screen_region()` (nearest-point screen prediction) is
  implemented and tested but not shown anywhere in the UI yet
- Vertical gaze estimation still needs improvement and struggles 
  to accurately distinguish upward and downward eye movement 
- Head pose (yaw/pitch/roll) is a rough approximation from a generic
  face model via `cv2.solvePnP`, not a precise measurement - good
  enough to reject "way too far turned" frames, but accuracy varies
  across different face shapes
- "Both eyes visible" comes from MediaPipe's blink blendshape scores -
  a real signal, not guessed, but it's a blink detector being reused
  for visibility, not a dedicated occlusion check. We also don't yet
  use that same blink data as an intentional "select" gesture
- Face-distance guidance (`face_width_ratio`) is just (face width in
  pixels) / (frame width) - a relative "close enough to track" signal,
  not an actual distance in inches or centimeters
- No keyboard/mouse control or gaze-based menu navigation
- No audio feedback
- Only works for one person at a time, and calibration isn't saved to
  disk - reopening the Calibrate window always wipes previous data and
  starts the nine points over from scratch, even within the same session
- Barely any error handling - if the camera's in use by another app or
  disconnects, expect a crash rather than a nice error message
- Everything runs on the main thread, so it might chug a bit on slower machines
- No accessibility options in the UI itself yet
- Uses MediaPipe's newer "Tasks" API instead of the older one, since
  the old one got removed in recent MediaPipe versions - just means it
  needs that model file download mentioned above

Most of this is marked with `# TODO:` comments right in the code so
it's easy to find where to pick things up.

## Future Work

- **Wire up screen-position prediction** - actually show/use the output
  of `predict_screen_region()` somewhere visible (Stats for Nerds is
  the obvious first spot) instead of it just being a tested-but-unused method
- **Real screen-coordinate interpolation** - replace the current
  nearest-of-nine-points matching with something that estimates a
  continuous X/Y position between the calibrated points
- **Blink-based selection** - we already get blink data every frame
  (via MediaPipe's blendshapes); turning a deliberate blink into a
  "select" action still needs its own logic and hooking up to the GUI
- **Feed calibration data into the direction thresholds** - actually
  use `screen_calibration` to adjust `GAZE_LEFT_THRESHOLD` etc. per
  person instead of the fixed global values everyone shares today
- **Full menu navigation** - let gaze (and eventually blinks) actually control the app instead of just being a label on screen
- **Improved gaze accuracy** - better smoothing, account for head tilt vs. actual eye movement, maybe a real model instead of hardcoded thresholds
- **Accessibility improvements** - high contrast mode, adjustable font sizes, audio feedback, sensitivity settings
- **Save calibration to disk** - so people don't have to redo all nine points every time they open the app
- **Per-point calibration redo** - let someone redo a single point instead of restarting the whole nine-point sequence

## Known Bugs

- If no face is detected, the label says "NO FACE" but the video might briefly freeze
- Calibration checks that *tracking conditions* look solid (face visible, good distance, head not turned too far) before counting a frame, but it can't actually confirm you were looking at the right dot - it trusts that you were
- Closing the calibration window partway through and reopening it always wipes previous progress and restarts the whole nine-point sequence - there's no way to resume or save a partial run
- Head pose estimation uses a generic face model, so yaw/pitch numbers will be a bit off for unusual face proportions - it's tuned to reject clearly-bad frames, not to be precise
- Might run slow on weaker laptops since there's no frame skipping or threading yet

## Team Notes

Roughly who'd touch what:

- `gaze_tracker.py` - anyone doing blink-based selection, accuracy improvements, feeding calibration data into the direction thresholds, or building out real screen-position interpolation
- `calibration.py` - anyone improving the calibration flow, adding per-point redo, or saving calibration to disk
- `debug_window.py` - anyone adding more Stats for Nerds fields (like predicted screen X/Y once that's wired up)
- `gui.py` - anyone doing menu navigation, accessibility settings, or audio feedback
- `config.py` - shared constants, add new settings here instead of hardcoding numbers elsewhere
