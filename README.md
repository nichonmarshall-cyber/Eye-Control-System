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
- Basic left/center/right/up/down gaze estimation
- Basic calibration screen (look left, center, right, up, down capture each one)
- Start / Stop / Calibrate / Exit buttons
- Live video preview with little dots showing what's being tracked
- Current gaze direction shown on screen in real time
- Code split up by responsibility (camera / tracking / calibration / GUI / config)
  so it's hopefully not too painful to work on different parts at once

## Current Limitations

- Vertical gaze estimation still needs improvement and struggles 
  to accurately distinguish upward and downward eye movement 
- Calibration collects data but doesn't actually change the gaze
  thresholds yet - it's stored but unused for now
- No blink detection, so there's no way to "select" anything yet
- No keyboard/mouse control or gaze-based menu navigation
- No audio feedback
- Only works for one person at a time, no saved profiles
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

- **Blink detection** - use eye-aspect-ratio (EAR) to detect blinks and use them as a "select" action
- **Better calibration** - actually use the calibration data to adjust thresholds per person, maybe sample over a few seconds instead of one snapshot per point
- **Full menu navigation** - let gaze (and eventually blinks) actually control the app instead of just being a label on screen
- **Improved gaze accuracy** - better smoothing, maybe a real model instead of hardcoded thresholds
- **Accessibility improvements** - high contrast mode, adjustable font sizes, audio feedback, sensitivity settings
- **Diagnostic panel** - Display raw and filtered tracking values to simplify debugging and threshold tuning

## Known Bugs

- Gaze label can flicker between CENTER and LEFT/RIGHT/UP/Doen near the threshold edges
- If no face is detected, the label says "NO FACE" but the video might briefly freeze
- Calibration lets you capture a point even if you weren't actually looking the right direction - no validation
- If you close the calibration window partway through, it doesn't reset progress if you reopen it
- Might run slow on weaker laptops since there's no frame skipping or threading yet

## Team Notes

Roughly who'd touch what:

- `gaze_tracker.py` - anyone doing blink detection, or accuracy improvements
- `calibration.py` - anyone improving the calibration algorithm or adding saved profiles
- `gui.py` - anyone doing menu navigation, accessibility settings, or audio feedback
- `config.py` - shared constants, add new settings here instead of hardcoding numbers elsewhere
