"""
All the settings/constants for the project live here.

Basically if you want to tweak a number (camera resolution, gaze
thresholds, colors, etc.) you should be able to do it here instead of
digging through every file.
"""

# ---- Camera stuff ----
CAMERA_INDEX = 0       # change this if you have more than one webcam and it opens the wrong one
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# ---- MediaPipe face tracking settings ----
# Heads up: we are gonna use MediaPipe's new "Tasks" API. It needs a model file that gets
# downloaded automatically the first time you run the app - see the
# _ensure_model_downloaded function in gaze_tracker.py.
MAX_NUM_FACES = 1
MIN_DETECTION_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5

MODEL_DIR = "models"
MODEL_FILENAME = "face_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)

# ---- Eye landmark indices ----
# MediaPipe's face mesh has ~478 points total, and these are just the
# specific point numbers that correspond to eye corners and iris. We
# looked these up / grabbed them from MediaPipe's docs & examples -
# don't need to memorize them, just know they point at eyes and irises.
LEFT_EYE_LANDMARKS = [33, 133, 159, 145, 153, 154]
LEFT_IRIS_LANDMARKS = [468, 469, 470, 471, 472]

RIGHT_EYE_LANDMARKS = [362, 263, 386, 374, 380, 381]
RIGHT_IRIS_LANDMARKS = [473, 474, 475, 476, 477]

# ---- Gaze thresholds ----
# These decide how far the iris has to move before we call it
# "looking left" or "looking right" instead of "center". I just eyeballed
# these numbers by testing - they're not scientifically calibrated.
# TODO: Replace fixed thresholds with a properly calibrated, per-user model
GAZE_LEFT_THRESHOLD = 0.42
GAZE_RIGHT_THRESHOLD = 0.58

GAZE_UP_THRESHOLD = 0.46
GAZE_DOWN_THRESHOLD = 0.54


# TODO: We already get blink scores from MediaPipe's blendshapes
# (eyeBlinkLeft/eyeBlinkRight, see process_frame in gaze_tracker.py) -
# that's currently only used for "are both eyes visible right now."
# Turning a deliberate blink into a "select" gesture still needs its
# own threshold/timing here (e.g. how long a blink has to hold before
# it counts as intentional vs. just a normal blink).
# BLINK_SELECT_THRESHOLD = ...
# BLINK_SELECT_HOLD_MS = ...

# ---- Calibration settings ----
# Order matters here - it's the order the calibration window walks
# through the dots in (top row left-to-right, then middle, then
# bottom). CALIBRATION_TARGET_POSITIONS below gives each name a
# normalized (0-1) screen position instead of hardcoded pixels, so
# this works on whatever monitor resolution someone's running.
CALIBRATION_TARGET_NAMES = [
    "top_left", "top_center", "top_right",
    "middle_left", "center", "middle_right",
    "bottom_left", "bottom_center", "bottom_right"
]

CALIBRATION_TARGET_POSITIONS = {
    "top_left": (0.05, 0.05),
    "top_center": (0.50, 0.05),
    "top_right": (0.95, 0.05),
    "middle_left": (0.05, 0.50),
    "center": (0.50, 0.50),
    "middle_right": (0.95, 0.50),
    "bottom_left": (0.05, 0.95),
    "bottom_center": (0.50, 0.95),
    "bottom_right": (0.95, 0.95),
}

#----Gaze overlay----
"""
This overlay needs to run a little faster than the debug window, since we want
the circle to move smoothly to where we are looking.
"""
GAZE_OVERLAY_UPDATE_RATE_MS = 30
GAZE_OVERLAY_CIRCLE_RADIUS = 20
GAZE_OVERLAY_COLOR = "#4caf50" # circle color
GAZE_OVERLAY_FLASH_COLOR = "#ff5555" # the color it changes to when you select something
GAZE_OVERLAY_FLASH_DURATION_MS = 400 # how long it changes color for

CALIBRATION_SAMPLES_PER_POINT = 45  # how many frames to sample for each calibration point
CALIBRATION_SETTLING_FRAMES = 8  # how many frames to skip before starting to sample for each point
CALIBRATION_DOT_RADIUS = 10  # radius of the dot that appears on the screen during calibration

#---- Screen position mapping ----
"""
The polynomial that maps a gaze reading to a screen position has six
terms (see _polynomial_features in gaze_tracker.py), so we need at
least six calibration points before the fit means anything. Fewer than
that and it's underdetermined - it'd have more unknowns than equations
and just be inventing an answer. Nine points clears this easily; this
is really a safety net in case some points fail to collect.
"""
SCREEN_MAPPING_MIN_POINTS = 6

#---- Face distance / tracker quality settings ----
# These are just rough estimates of how far away the user is from the camera.
MIN_FACE_WIDTH_RATIO = 0.20 # if the face is smaller than this fraction of the frame width, we assume the user is too far away
MAX_FACE_WIDTH_RATIO = 0.50 # if the face is larger than this fraction of the frame width, we assume the user is too close
CALIBRATED_FACE_SIZE_TOLERANCE = 0.20 # if the face size changes by more than this fraction from the calibrated size, we assume the user moved

#---- Head pose limits (degrees) ----
# If the user's head is rotated beyond these angles, we assume they're looking away from the screen
MAX_CALIBRATION_HEAD_YAW = 22.0
MAX_CALIBRATION_HEAD_PITCH_DEVIATION = 12.0
MAX_TRACKING_HEAD_YAW = 18.0

#---- DEBUG / STATS FOR NERDS WINDOW ----
DEBUG_UPDATE_RATE_MS = 100  # how often (ms) the debug window refreshes, ~10fps


# ---- GUI settings ----
WINDOW_TITLE = "EyeAble - Gaze Tracking Prototype"
WINDOW_BG = "#1e1e1e"
TEXT_COLOR = "#f5f5f5"
ACCENT_COLOR = "#4caf50"
GUI_UPDATE_DELAY_MS = 15  # how often (ms) the video preview refreshes, ~60fps-ish

# TODO: Add accessibility settings (font size, high-contrast mode, colorblind palettes)
# TODO: Add user profile storage (per-user calibration + preferences)
