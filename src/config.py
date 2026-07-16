"""
All the settings/constants for the project live here.

Basically if you want to tweak a number (camera resolution, gaze
thresholds, colors, etc.) you should be able to do it here instead of
digging through every file.
"""

# ---- Camera stuff ----
CAMERA_INDEX = 0       # change this if you have more than one webcam and it opens the wrong one
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

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


# TODO: Add eye-aspect-ratio (EAR) threshold for blink detection
# BLINK_EAR_THRESHOLD = ...

# ---- Calibration settings ----
CALIBRATION_POINTS = ["LEFT", "CENTER", "RIGHT","UP", "DOWN"] 
CALIBRATION_HOLD_FRAMES = 30  # not actually used yet, placeholder for later

# ---- GUI settings ----
WINDOW_TITLE = "EyeAble - Gaze Tracking Prototype"
WINDOW_BG = "#1e1e1e"
TEXT_COLOR = "#f5f5f5"
ACCENT_COLOR = "#4caf50"
GUI_UPDATE_DELAY_MS = 15  # how often (ms) the video preview refreshes, ~60fps-ish

# TODO: Add accessibility settings (font size, high-contrast mode, colorblind palettes)
# TODO: Add user profile storage (per-user calibration + preferences)
