# EyeAble

EyeAble is a webcam-based gaze-tracking application developed as a group
Software Engineering project. It uses OpenCV and MediaPipe to estimate
where a user is looking, performs a sixteen-point calibration, and maps
the user's gaze to a continuous position on the screen.

The application runs as a multi-screen desktop dashboard: a start
screen, a home menu, and a live tracking dashboard styled after the
project's design mockups. Users navigate and select options hands-free
by looking at a control and performing a deliberate held blink. EyeAble
also includes a fullscreen gaze overlay, head-pose and tracking-quality
diagnostics, and a separate diagnostic window. It is designed and tested
primarily for Windows systems using a standard webcam and does not
require a dedicated GPU.

## Tech Stack

- Python
- OpenCV for webcam capture and image processing
- MediaPipe for face, eye, iris, and blink landmark detection
- NumPy for calibrated gaze-to-screen mapping
- Tkinter for the multi-screen desktop interface and fullscreen overlay
- Pillow for displaying OpenCV frames and interface icons in Tkinter
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
    ├── gui.py               # Controller: owns the tracking loop and hosts screens
    ├── start_screen.py      # Initial start / welcome screen
    ├── second_screen.py     # Home menu (Start Tracking, Calibration, Tutorial, Exit)
    ├── dashboard_screen.py  # Main tracking dashboard with gaze-selectable tiles
    ├── tracking_screen.py   # Diagnostic tracking view (camera preview + controls)
    ├── utils.py             # Shared helper functions
    ├── config.py            # Application constants and settings
    └── assets/              # Interface icons and logo
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

## Application Flow

EyeAble opens on a start screen and moves through a set of screens
managed by a central controller (`gui.py`). The controller owns the
camera, the gaze tracker, and the tracking loop, while each screen is a
self-contained view that the controller raises as needed:

- **Start screen** – entry point that leads into the home menu.
- **Home menu** – four large tiles: Start Tracking, Calibration,
  Tutorial, and Exit. Tiles are intentionally large so they are easy to
  select with gaze and blink.
- **Tracking dashboard** – the main experience. Shows selectable tiles
  (Computer, Files, Mail), a live "Looking At" gaze indicator, tracking
  settings, and Pause/Play, Stop, Re-calibrate, and Back-to-menu
  controls. Selecting a tile shows an on-screen confirmation.

Because the same controller owns tracking state across every screen, new
screens can be added by registering a view and, where relevant, calling
`_register_gaze_selectable` with that screen's buttons. No tracking or
selection logic needs to be rewritten.

## Completed Features

- Real-time webcam capture at a requested resolution of 1280×720
- Smaller camera preview while preserving full-resolution frames for
  tracking
- MediaPipe face, eye, iris, and blink landmark detection
- Basic left, center, right, up, and down gaze classification
- Fullscreen sixteen-point calibration on a four-by-four grid
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
- Fullscreen transparent gaze overlay that follows the calibrated gaze
- Overlay feedback that flashes when a held-blink selection is made
- Gaze-position freezing while the user's eyes are closed, so a blink
  selects whatever the user was looking at when their eyes closed
- Held-blink detection that separates deliberate selections from normal
  short blinks
- **Gaze-and-blink selection of interface controls:** buttons highlight
  while the user looks at them and activate on a deliberate held blink,
  reusable across screens
- **Multi-screen application flow** with a start screen, home menu, and
  a design-matched tracking dashboard
- Escape-to-cancel support during calibration
- Head-pose estimation for yaw, pitch, and roll
- Face-distance and tracking-quality guidance
- Separate Stats for Nerds diagnostic window
- Live display of horizontal and vertical gaze ratios
- Modular code separated by camera, tracking, calibration, overlay,
  diagnostics, controller, individual screens, configuration, and
  utility responsibilities

## Current Limitations

- The dashboard tiles (Computer, Files, Mail) are demonstration
  placeholders. Selecting one shows a confirmation but does not yet
  launch a real application or open real files.
- The tracking settings sliders (Sensitivity, Cursor Speed) are present
  in the interface but are not yet connected to tracking behavior.
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

- Tutorial screen and first-time-user instructions
- Connecting the dashboard tiles to real actions
- Wiring the tracking settings sliders to actual tracking behavior

## Future Work

The following tasks are available for future development. Team members
should communicate which task they are taking before beginning work to
avoid duplicate changes.

### User Interface

- Finish the tutorial screen and first-time-user instructions.
- Connect the dashboard tiles to real actions (open applications, files,
  or messages).
- Add a dedicated settings screen for accessibility and tracking
  options.
- Improve visual consistency across the start screen, home menu,
  dashboard, calibration screen, and diagnostic window.
- Add clear tracking, calibration, and camera-status indicators.

### Accessibility

- Add adjustable font sizes and larger interface controls.
- Add a high-contrast display mode.
- Connect configurable blink-hold timing and tracking sensitivity to the
  settings interface.
- Add optional audio feedback for calibration, tracking, highlighting,
  and selection.
- Add keyboard alternatives for all gaze-controlled actions.

### Calibration

- Save calibration profiles to disk.
- Allow users to load and manage saved calibration profiles.
- Allow individual calibration points to be repeated.
- Add a calibration accuracy or validation screen after the points are
  collected.
- Prompt first-time users to calibrate before enabling gaze controls.

### Tracking

- Improve vertical gaze accuracy across different users.
- Add stronger compensation for changes in head position, using the
  head-pose values already collected during calibration.
- Improve stability under different lighting conditions and webcam
  quality.
- Add adaptive smoothing that reduces jitter while remaining responsive.
- Add tracking-confidence feedback for the user.

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
- On first launch, tracking may need to be stopped and started once
  before the camera preview appears.
- The application may run more slowly on lower-powered computers.

## Team Notes

- Coordinate before editing shared tracking or configuration files.
- `gui.py` is the controller. It owns the camera, gaze tracker, and
  tracking loop, and hosts each screen. New screens are registered here.
- Screens (`start_screen.py`, `second_screen.py`, `dashboard_screen.py`,
  `tracking_screen.py`) are self-contained views. A screen exposes its
  buttons to gaze selection by calling `controller._register_gaze_selectable`.
- `gaze_tracker.py` contains the gaze mapping, smoothing, calibration,
  blink-state, and tracking-quality logic.
- `gaze_overlay.py` displays the calibrated gaze position and blink
  feedback but should not contain button-specific actions.
- `calibration.py` controls the sixteen-point calibration sequence.
- `config.py` should contain shared settings instead of hardcoded values.
- Future tasks should be selected from this README and announced to the
  team before implementation.