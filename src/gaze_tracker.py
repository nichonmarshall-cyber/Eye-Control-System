"""
This is where the actual gaze detection happens.

Basically: we feed it a webcam frame, it finds your face, finds your
eyes/irises, and figures out roughly whether you're looking left,
center, or right. That's it for now - no up/down, no blink stuff yet
(see the TODOs scattered through this file).

"""

import os
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from src import config, utils


class GazeTracker:
    def __init__(self):
        self._ensure_model_downloaded()

        # This sets up MediaPipe's face landmark detector. IMAGE mode
        # means we're just feeding it one frame at a time instead of a
        # continuous video stream, which keeps things simple for us.
        base_options = mp_python.BaseOptions(model_asset_path=self._model_path())
        options = mp_vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.IMAGE,
            num_faces=config.MAX_NUM_FACES,
            min_face_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
            min_face_presence_confidence=config.MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
        )
        self.landmarker = mp_vision.FaceLandmarker.create_from_options(options)

        # Whatever the calibration screen collects gets stored here.
        # TODO: Actually use this data to adjust thresholds per-user
        # instead of the fixed global ones in config.py. Right now we
        # just save it and don't do anything with it yet.
        self.calibration_data = {"LEFT": None, "CENTER": None, "RIGHT": None}

        # Keeps track of recent gaze readings so we can smooth them out
        # (see moving_average in utils.py).
        self._ratio_history = []

    @staticmethod
    def _model_path():
        # Figures out where models/face_landmarker.task should live,
        # relative to the project folder, no matter where you ran the
        # script from.
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(project_root, config.MODEL_DIR, config.MODEL_FILENAME)

    def _ensure_model_downloaded(self):
        """
        Downloads the face landmark model file if we don't already have
        it saved locally. Only needs to happen once - after that it's
        cached and works offline.

        TODO: Add proper error handling here (e.g. a friendly message
        instead of a crash if there's no internet on first run).
        """
        model_path = self._model_path()
        if os.path.exists(model_path):
            return

        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        urllib.request.urlretrieve(config.MODEL_URL, model_path)

    def process_frame(self, frame):
        """
        Takes one webcam frame, runs face detection on it, and returns
        the gaze direction.

        Returns a tuple:
            annotated_frame - the frame with little dots drawn on the eyes/iris
            gaze_direction - "LEFT", "CENTER", "RIGHT", or "NO FACE"
            raw_ratio - the unsmoothed number we used to decide direction (or None)
        """
        h, w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # MediaPipe wants RGB, OpenCV gives us BGR
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self.landmarker.detect(mp_image)

        gaze_direction = "NO FACE"
        raw_ratio = None

        if result.face_landmarks:
            # We only care about the first face found (num_faces=1 anyway)
            face_landmarks = result.face_landmarks[0]

            raw_ratio = self._compute_horizontal_ratio(face_landmarks, w, h)
            self._ratio_history.append(raw_ratio)
            smoothed_ratio = utils.moving_average(self._ratio_history, window=5)

            gaze_direction = self._ratio_to_direction(smoothed_ratio)

            frame = self._draw_debug_overlay(frame, face_landmarks, w, h)

        # TODO: Add blink detection here using eye-aspect-ratio (EAR)
        # and hook it up so the GUI can use it for "selecting" something.

        # TODO: Add vertical gaze detection (Up/Down) here, probably by
        # comparing iris position to the top/bottom eyelid landmarks
        # the same way we do left/right below.

        return frame, gaze_direction, raw_ratio

    def _compute_horizontal_ratio(self, landmarks, w, h):
        """
        Figures out roughly where the iris sits horizontally inside the
        eye (0 = all the way left, 1 = all the way right), then averages
        that across both eyes so one eye being weird doesn't throw
        everything off as much.
        """
        left_eye = utils.landmarks_to_np(landmarks, config.LEFT_EYE_LANDMARKS, w, h)
        left_iris = utils.landmarks_to_np(landmarks, config.LEFT_IRIS_LANDMARKS, w, h)

        right_eye = utils.landmarks_to_np(landmarks, config.RIGHT_EYE_LANDMARKS, w, h)
        right_iris = utils.landmarks_to_np(landmarks, config.RIGHT_IRIS_LANDMARKS, w, h)

        left_ratio = self._eye_ratio(left_eye, left_iris)
        right_ratio = self._eye_ratio(right_eye, right_iris)

        return (left_ratio + right_ratio) / 2.0

    @staticmethod
    def _eye_ratio(eye_points, iris_points):
        """
        The actual "where's the iris" math for one eye. Basically:
        find the eye's left/right corners, find the iris center, and
        see what percentage of the way across the iris center is.

        0 = iris is jammed against the left corner
        1 = iris is jammed against the right corner
        0.5ish = roughly centered
        """
        iris_center = utils.eye_center(iris_points)
        eye_left = eye_points[:, 0].min()
        eye_right = eye_points[:, 0].max()

        if eye_right - eye_left == 0:
            return 0.5  # avoid dividing by zero if something goes weird

        ratio = (iris_center[0] - eye_left) / (eye_right - eye_left)
        return utils.clamp(ratio, 0.0, 1.0)

    def _ratio_to_direction(self, ratio):
        """
        Turns the ratio number into an actual LEFT/CENTER/RIGHT label
        using the thresholds from config.py.

        TODO: Use per-user calibration_data instead of these fixed
        thresholds - right now everyone gets the same thresholds
        whether they have small eyes, big eyes, glasses, whatever.
        """
        if ratio < config.GAZE_LEFT_THRESHOLD:
            return "LEFT"
        elif ratio > config.GAZE_RIGHT_THRESHOLD:
            return "RIGHT"
        else:
            return "CENTER"

    def _draw_debug_overlay(self, frame, landmarks, w, h):
        """Draws little dots on the eye corners (green) and iris (red) so you can see what's being tracked."""
        for idx in config.LEFT_EYE_LANDMARKS + config.RIGHT_EYE_LANDMARKS:
            lm = landmarks[idx]
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (cx, cy), 1, (0, 255, 0), -1)

        for idx in config.LEFT_IRIS_LANDMARKS + config.RIGHT_IRIS_LANDMARKS:
            lm = landmarks[idx]
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (cx, cy), 1, (0, 0, 255), -1)

        return frame

    def apply_calibration(self, calibration_data):
        """
        Called by the calibration screen once it's done collecting
        samples. Just stores the data for now.

        TODO: Actually use calibration_data to adjust gaze thresholds
        per-user instead of letting it sit here unused.
        """
        self.calibration_data = calibration_data

    def close(self):
        self.landmarker.close()
