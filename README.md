# EyeAble

EyeAble is a webcam-based gaze-tracking application developed as a group
Software Engineering project. It uses OpenCV and MediaPipe to estimate
where a user is looking, performs a sixteen-point calibration, and maps
the user's gaze to a continuous position on the screen.

The current prototype includes a fullscreen gaze overlay, head-pose and
tracking-quality diagnostics, and held-blink detection wired to
hands-free button selection. EyeAble is designed and tested primarily
for Windows systems using a standard webcam and does not require a
dedicated GPU.

## Tech Stack

- Python
- OpenCV for webcam capture and image processing
- MediaPipe for face, eye, iris, and blink landmark detection
- NumPy for calibrated gaze-to-screen mapping
- Tkinter for the desktop interface and fullscreen overlay
- Pillow for displaying OpenCV frames in Tkinter
- Designed and tested on Windows without a dedicated GPU

## Project Structure

```text
EyeAble/
│
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
├── README.md
├── models/
│   └── face_landmarker.task # MediaPipe face-landmark model
└── src/
    ├── camera.py            # Webcam startup, capture, and shutdown
    ├── gaze_tracker.py      # Gaze, blink, calibration, and mapping logic
    ├── calibration.py       # Fullscreen sixteen-point calibration
    ├── gaze_overlay.py      # Fullscreen transparent gaze indicator
    ├── debug_window.py      # Live diagnostic information
    ├── gui.py               # Current tracking interface and controls
    ├── utils.py             # Shared helper functions
    └── config.py            # Application constants and settings
```

## Running the Application

Install the required packages:

```bash
pip install -r requirements.txt
```

Launch EyeAble:

```bash
python main.py
```

The MediaPipe model file is included in the `models` directory. If the
file is missing, EyeAble attempts to download it during startup, which
requires an internet connection. Once downloaded, the model can be used
offline.

## Completed Features

- Real-time webcam capture at a requested resolution of 1280×720
- Smaller 640×360 camera preview while preserving full-resolution
  frames for tracking
- MediaPipe face, eye, iris, and blink landmark detection
- Fullscreen sixteen-point calibration arranged as a 4×4 grid covering
  the corners, edges, and interior of the screen ~ 
- Collection of 45 valid gaze samples at each calibration point
- Calibration quality checks that reject samples when:
  - No face is detected
  - Both eyes are not visible
  - The user is too close to or too far from the camera
  - The user's head is turned or tilted too far
- Per-user polynomial gaze-to-screen mapping after calibration
- Inverse-distance weighted mapping as a fallback if the polynomial
  model cannot be fitted
- Smoothed continuous screen coordinates between calibration points
- Fullscreen transparent gaze overlay
- Overlay feedback when a held-blink gesture is detected
- Gaze-position freezing while the user's eyes are closed
- Held-blink detection that separates deliberate selections from normal
  short blinks
- Hands-free button selection: gaze-based hover highlighting on the
  prototype dashboard, with a held-blink activating whichever button
  the user is looking at
- Prototype dashboard buttons resized and spaced with slightly larger
  hit targets so they are easier to select by gaze. The live dashboard
  is expected to use its own sizing and does not depend on these
  values.
- Head-pose estimation for yaw, pitch, and roll
- Face-distance and tracking-quality guidance
- Separate Stats for Nerds diagnostic window
- Live display of horizontal and vertical gaze ratios
- Modular code separated by camera, tracking, calibration, overlay,
  diagnostics, interface, configuration, and utility responsibilities

## Current Limitations

- The redesigned dashboard has not yet been integrated with the
  tracking interface, resulting in an incomplete application flow.
- Selection accuracy is limited by webcam gaze precision, so smaller
  buttons on the prototype dashboard can still be difficult to target
  reliably.
- Vertical gaze tracking is less consistent than horizontal gaze
  tracking and can vary between users.
- Calibration data is stored only in memory and is lost when the
  application closes.
- Starting a new calibration clears the previous calibration.
- Individual calibration points cannot currently be repeated.
- The user must remain near the position and distance used during
  calibration for the best results.
- Head-pose values are approximations based on a generic face model.
- The application relies on Windows camera permissions and does not yet
  provide its own permission-request screen.
- Camera disconnections and cameras already in use by another
  application have limited error recovery.
- Tracking runs on the main application thread and may be slower on
  weaker computers.
- The interface does not yet include configurable accessibility
  settings or audio feedback.
- EyeAble currently supports one tracked user at a time.

## Work Currently in Progress

- Integrate the redesigned dashboard with the tracking workflow
- Remove the duplicate-dashboard application flow

## Future Work

The following tasks are available for future development. Team members
should communicate which task they are taking before beginning work to
avoid duplicate changes.

### User Interface

- Simplify the application so users interact with one primary dashboard.
- Finish the tutorial screen and first-time-user instructions.
- Improve visual consistency between the dashboard, calibration screen,
  tracking screen, and diagnostic window.
- Add clear tracking, calibration, and camera-status indicators.

### Accessibility

- Add adjustable font sizes and larger interface controls.
- Add a high-contrast display mode.
- Add configurable blink-hold timing and tracking sensitivity.
- Add optional audio feedback for calibration, tracking, highlighting,
  and selection.
- Add keyboard alternatives for all gaze-controlled actions.

### Calibration

- Save calibration profiles to disk.
- Allow users to load and manage saved calibration profiles.
- Allow individual calibration points to be repeated.
- Add a calibration accuracy or validation screen after the sixteen
  points are collected.
- Prompt first-time users to calibrate before enabling gaze controls.

### Tracking

- Improve vertical gaze accuracy across different users.
- Add stronger compensation for changes in head position.
- Improve stability under different lighting conditions and webcam
  quality.
- Consider a velocity-adaptive smoothing approach (for example, a 1€
  filter) as one possible way to reduce jitter while remaining
  responsive during quick eye movements.
- Add tracking-confidence feedback for the user.
- Consider adding a short dwell requirement before a blink can activate
  a button, to make hands-free selection feel steadier on small
  targets.

### Reliability and Performance

- Improve handling for unavailable, disconnected, or blocked cameras.
- Provide a clear message when the MediaPipe model cannot be downloaded.
- Move expensive tracking work away from the Tkinter interface thread.
- Measure and verify frame-processing latency.
- Improve support for different display resolutions and multiple
  monitors.

## Known Issues

- Calibration assumes the user is looking at the displayed target; it
  cannot independently verify attention to the correct dot.
- Tracking accuracy decreases when the user changes position after
  calibration.
- Closing calibration before completion discards the current progress.
- The gaze overlay can jitter when landmark measurements fluctuate.
- The application may run more slowly on lower-powered computers.

## Team Notes

- Coordinate before editing shared tracking or configuration files.
- `gaze_tracker.py` contains the gaze mapping, smoothing, calibration,
  blink-state, and tracking-quality logic.
- `gui.py` contains the current tracking interface and hosts the
  gaze-controlled button highlighting and selection logic.
- `gaze_overlay.py` displays the calibrated gaze position and blink
  feedback but should not contain button-specific actions.
- `calibration.py` controls the sixteen-point calibration sequence.
- `config.py` should contain shared settings instead of hardcoded values.
- Future tasks should be selected from this README and announced to the
  team before implementation.
