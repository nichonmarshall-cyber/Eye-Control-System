"""
This is where the actual gaze detection happens.

Basically: we feed it a webcam frame, it finds your face, finds your
eyes/irises, and figures out roughly whether you're looking left,
center, or right. That's it for now - no up/down, no blink stuff yet
(see the TODOs scattered through this file).

NEW: this file also now tracks a bunch of extra stuff beyond just
LEFT/CENTER/RIGHT/UP/DOWN - per-eye ratios, face distance, head pose,
and a "screen_calibration" system that's the first step toward
predicting where on the actual screen someone's looking, instead of
just a rough direction. The old direction system is untouched and
still runs every frame - the new stuff sits alongside it.

"""

import os
import statistics
import time
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
            output_face_blendshapes=True,
        )
        self.landmarker = mp_vision.FaceLandmarker.create_from_options(options)

        # Keeps track of recent gaze readings so we can smooth them out
        # (see moving_average in utils.py).
        self._h_ratio_history = []
        self._v_ratio_history = []

        self.screen_calibration = {name: None for name in config.CALIBRATION_TARGET_NAMES}
        self.calibration_complete = False
        self.calibrated_face_width_ratio = None
        self.current_calibration_point = None
        self.current_calibration_sample_count = 0
        self.last_tracking_data = {}

        """
        Blink-to-select tracking. _eyes_closed_since holds a
        timestamp (from time.monotonic()) for whenever both eyes are
        currently closed, or None when they're open - this is what
        lets us measure how long a blink has been held. The count
        just goes up every time a held-long-enough blink completes.
        """

        self._eyes_closed_since = None
        self._blink_select_count = 0

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

            h_ratio, left_h_ratio, right_h_ratio = self._compute_horizontal_ratio(face_landmarks, w, h)
            v_ratio, left_v_ratio, right_v_ratio = self._compute_vertical_ratio(face_landmarks, w, h)

            self._h_ratio_history.append(h_ratio)
            self._v_ratio_history.append(v_ratio)

            smoothed_h = utils.moving_average(self._h_ratio_history, window=5)
            smoothed_v = utils.moving_average(self._v_ratio_history, window=5)

            horizontal_label = self._horizontal_label(smoothed_h)
            vertical_label = self._vertical_label(smoothed_v)
            gaze_direction = self._combine_labels(horizontal_label, vertical_label)

            raw_ratio = (h_ratio, v_ratio)  # return the unsmoothed numbers too, for debugging

            #---- face size / distance estimation ----
            """
            234 and 454 are the leftmost/rightmost points of the face. oval in MediaPipe's landmark 
            layout. The distance between them is a rough proxy for how far away the face is from 
            the camera.
            """
            face_edge_points = utils.landmarks_to_np(face_landmarks, [234, 454], w, h)
            face_width_px = utils.distance(face_edge_points[0], face_edge_points[1])
            face_width_ratio = face_width_px / w  if w else None  # avoid division by zero if something goes weird

            eye_corner_points = utils.landmarks_to_np(face_landmarks, [133, 362], w, h)
            inter_eye_distance_px = utils.distance(eye_corner_points[0], eye_corner_points[1])

            # ---- eye visibility, from MediaPipe's blink blendshapes ----
            """
            This is a signal from the model (not a guess) - if its not available for some reason, we'll just 
            assume both eyes are visible rather than trying to guess.
            """
            left_blink = 0.0
            right_blink = 0.0
            both_eyes_visible = True
            if result.face_blendshapes:
                blink_scores = {c.category_name: c.score for c in result.face_blendshapes[0]}
                left_blink = blink_scores.get("eyeBlinkLeft",0.0)
                right_blink = blink_scores.get("eyeBlinkRight",0.0)
                both_eyes_visible = left_blink < 0.5 and right_blink < 0.5

            both_eyes_closed, eyes_closed_ms = self._update_blink_state(left_blink, right_blink)

            calibrated_gaze_direction = self._calibrated_direction(smoothed_h, smoothed_v)

            # ---- head pose (best effortm see utils.estimate_head_pose)----
            head_yaw, head_pitch, head_roll = utils.estimate_head_pose(face_landmarks, w, h)

            tracking_quality, tracking_quality_reason = self._assess_tracking_quality(
                both_eyes_visible=both_eyes_visible,
                face_width_ratio=face_width_ratio,
                head_yaw=head_yaw,
            )

            self.last_tracking_data = {
                "face_detected":True,
                "both_eyes_visible": both_eyes_visible,
                "gaze_direction":gaze_direction,
                "horizontal_ratio":smoothed_h,
                "vertical_ratio":smoothed_v,
                "raw_horizontal_ratio": h_ratio,
                "raw_vertical_ratio":v_ratio,
                "left_horizontal_ratio": left_h_ratio,
                "right_horizontal_ratio": right_h_ratio,
                "left_vertical_ratio": left_v_ratio,
                "right_vertical_ratio": right_v_ratio,
                "face_width_px": face_width_px,
                "face_width_ratio": face_width_ratio,
                "inter_eye_distance_px": inter_eye_distance_px,
                "head_yaw": head_yaw,
                "head_pitch": head_pitch,
                "head_roll": head_roll,
                "tracking_quality": tracking_quality,
                "tracking_quality_reason": tracking_quality_reason,
                "position_status": self._position_status(face_width_ratio),
                "both_eyes_closed": both_eyes_closed,
                "eyes_closed_ms": eyes_closed_ms,
                "blink_select_count": self._blink_select_count,
                "calibrated_gaze_direction": calibrated_gaze_direction,
            }

            frame = self._draw_debug_overlay(frame, face_landmarks, w, h)
        else:
            self.last_tracking_data = {
                "face_detected": False,
                "both_eyes_visible": False,
                "gaze_direction": "NO FACE",
                "horizontal_ratio": None,
                "vertical_ratio": None,
                "raw_horizontal_ratio": None,
                "raw_vertical_ratio": None,
                "left_horizontal_ratio": None,
                "right_horizontal_ratio": None,
                "left_vertical_ratio": None,
                "right_vertical_ratio": None,
                "face_width_px": None,
                "face_width_ratio": None,
                "inter_eye_distance_px": None,
                "head_yaw": None,
                "head_pitch": None,
                "head_roll": None,
                "tracking_quality": "NO FACE",
                "tracking_quality_reason": "No face detected in frame",
                "position_status": "N/A",
                 "both_eyes_closed": False,
                "eyes_closed_ms": 0,
                "blink_select_count": self._blink_select_count,
                "calibrated_gaze_direction": "NO FACE",
            }
        """ Calibration progress fields, added regardless of whether a
        face was found this frame - the Stats for Nerds window reads
        these every frame.
        """
        if self.current_calibration_point:
            self.last_tracking_data["current_calibration_point_text"] = (
                f"{self.current_calibration_point} "
                f"({self.screen_calibration_index() + 1} of {len(config.CALIBRATION_TARGET_NAMES)})"
            )
            self.last_tracking_data["calibration_samples_text"] = (
                f"{self.current_calibration_sample_count} of {config.CALIBRATION_SAMPLES_PER_POINT}"
            )
        else:
            self.last_tracking_data["current_calibration_point_text"] = "N/A"
            self.last_tracking_data["calibration_samples_text"] = "N/A"
        self.last_tracking_data["calibration_complete"] = self.calibration_complete

        return frame, gaze_direction, raw_ratio
    
    def screen_calibration_index(self):
        """
        Smaller helper so the progress text can show "point 3 of 9" instead of just raw name.
        """
        if self.current_calibration_point not in config.CALIBRATION_TARGET_NAMES:
            return 0
        return config.CALIBRATION_TARGET_NAMES.index(self.current_calibration_point)

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

        return (left_ratio + right_ratio) / 2.0, left_ratio, right_ratio
    
    def _compute_vertical_ratio(self, landmarks, w, h):
        """
        same idea as the horizontal ratio, but for vertical movement.
        (0 = iris is near the top of the eyelid, 1 _= iris is near the bottom)
        reuses the exact same eye/iris landmark points, just looks at the y-axis
        instead of x-axis.        
        """
        left_eye = utils.landmarks_to_np(landmarks, config.LEFT_EYE_LANDMARKS, w, h)
        left_iris = utils.landmarks_to_np(landmarks, config.LEFT_IRIS_LANDMARKS, w, h)

        right_eye = utils.landmarks_to_np(landmarks, config.RIGHT_EYE_LANDMARKS, w, h)
        right_iris = utils.landmarks_to_np(landmarks, config.RIGHT_IRIS_LANDMARKS, w, h)

        left_ratio = self._eye_ratio(left_eye, left_iris, axis=1)
        right_ratio = self._eye_ratio(right_eye, right_iris, axis=1)

        return (left_ratio + right_ratio) / 2.0, left_ratio, right_ratio

    @staticmethod
    def _eye_ratio(eye_points, iris_points, axis=0):
        """
        The actual "where's the iris" math for one eye. Basically:
        find the eye's left/right corners, find the iris center, and
        see what percentage of the way across the iris center is.

        axiis=0 (x-axis) -> horizontal: 0 = left corner, 1 = right corner
        axis=1 *(y-axis) -> vertical: 0 = top eyelid, 1 = bottom eyelid
        """
        iris_center = utils.eye_center(iris_points)
        eye_min = eye_points[:, axis].min()
        eye_max = eye_points[:, axis].max()

        if eye_max-eye_min == 0:
            return 0.5  # avoid dividing by zero if something goes weird

        ratio = (iris_center[axis] - eye_min) / (eye_max - eye_min)
        return utils.clamp(ratio, 0.0, 1.0)

    def _horizontal_label(self, ratio):
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
        
    def _vertical_label(self, ratio):
        """
        same as _horizontal_label but for up/down. the threshold are
        little more sensitive because the vertical movement of the 
        iris is smaller than the horizontal movement.

        TODO: Use per-user calibration_data instead of these fixed
        thresholds - right now everyone gets the same thresholds
        whether they have small eyes, big eyes, glasses, whatever.
        """

        if ratio < config.GAZE_UP_THRESHOLD:
            return "UP"
        elif ratio > config.GAZE_DOWN_THRESHOLD:
            return "DOWN"
        else:
            return "CENTER"
    
    @staticmethod     
    def _combine_labels(horizontal_label, vertical_label):
        """
        combines the horizontal and vertical labels into one direction
        string. if youre looking up and to the left at the same time
        you get "UP-LEFT" if youre just looking up you get "UP etc.\
        
        """
        if horizontal_label == "CENTER" and vertical_label == "CENTER":
            return "CENTER"
        elif horizontal_label == "CENTER":
            return vertical_label
        elif vertical_label == "CENTER":
            return horizontal_label
        else:
            return f"{vertical_label}-{horizontal_label}"

    def _assess_tracking_quality(self, both_eyes_visible, face_width_ratio, head_yaw):
        """
        Rolls face distance, eye visibility, and head yaw into one
        GOOD/POOR quality label plus a human-readable reason. Used both
        to show something useful in the debug window and (with
        stricter limits) to decide which frames are trustworthy enough
        to use during calibration.
        """
        if not both_eyes_visible:
            return "POOR", "One or both eyes not clearly visible"

        if face_width_ratio is not None and face_width_ratio < config.MIN_FACE_WIDTH_RATIO:
            return "POOR", "Face too far from camera"

        if face_width_ratio is not None and face_width_ratio > config.MAX_FACE_WIDTH_RATIO:
            return "POOR", "Face too close to camera"

        if head_yaw is not None and abs(head_yaw) > config.MAX_TRACKING_HEAD_YAW:
            return "POOR", "Head turned too far to the side"

        return "GOOD", "Face and eyes are stable"

    def _position_status(self, face_width_ratio):
        """
        Rough "are you at a usable distance from the camera" check
        based on how wide your face appears in the frame - not a real
        distance in inches/cm, just a ratio. If calibration's already
        been done, this also checks how far the current face size has
        drifted from the calibrated reference, since moving noticeably
        closer/farther after calibrating throws off the screen
        predictions.
        """
        if face_width_ratio is None:
            return "N/A"

        if self.calibration_complete and self.calibrated_face_width_ratio:
            relative_size = face_width_ratio / self.calibrated_face_width_ratio
            if relative_size < (1 - config.CALIBRATED_FACE_SIZE_TOLERANCE):
                return "MOVE CLOSER (drifted from calibrated position)"
            elif relative_size > (1 + config.CALIBRATED_FACE_SIZE_TOLERANCE):
                return "MOVE FARTHER (drifted from calibrated position)"
            # otherwise fall through to the general range check below

        if face_width_ratio < config.MIN_FACE_WIDTH_RATIO:
            return "MOVE CLOSER"
        elif face_width_ratio > config.MAX_FACE_WIDTH_RATIO:
            return "MOVE FARTHER"
        else:
            return "GOOD DISTANCE"

    def _draw_debug_overlay(self, frame, landmarks, w, h):
        """
        Draws little dots on the eye corners (green) and iris (red) so you can see what's being tracked.
        
        """
        for idx in config.LEFT_EYE_LANDMARKS + config.RIGHT_EYE_LANDMARKS:
            lm = landmarks[idx]
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (cx, cy), 1, (0, 255, 0), -1)

        for idx in config.LEFT_IRIS_LANDMARKS + config.RIGHT_IRIS_LANDMARKS:
            lm = landmarks[idx]
            cx, cy = int(lm.x * w), int(lm.y * h)
            cv2.circle(frame, (cx, cy), 1, (0, 0, 255), -1)

        return frame

    def _nearest_calibrated_region(self, horizontal_ratio, vertical_ratio):
        """
        Given a horizontal/vertical ratio, finds which of the nine
        calibrated points is closest (plain Euclidean distance).
        Returns the region name, or None if calibration isn't done or
        the ratios are missing. This is shared by predict_screen_region()
        (which adds pixel coordinates on top of this) and
        _calibrated_direction() (which just wants the region name to
        turn into a word) - so the "which point is closest" math only
        lives in one place.
        """
        if not self.calibration_complete or horizontal_ratio is None or vertical_ratio is None:
            return None

        best_name = None
        best_distance = None
        for name, point in self.screen_calibration.items():
            if point is None:
                continue
            dx = horizontal_ratio - point["horizontal_ratio"]
            dy = vertical_ratio - point["vertical_ratio"]
            dist_sq = dx * dx + dy * dy
            if best_distance is None or dist_sq < best_distance:
                best_distance = dist_sq
                best_name = name

        return best_name
    
    def _calibrated_direction(self, horizontal_ratio, vertical_ratio):
        """
        Translates the nearest calibrated point into the same
        LEFT/CENTER/RIGHT/UP/DOWN words the old fixed-threshold system
        already uses (see config.REGION_TO_DIRECTION). Shows
        "CALIBRATE FIRST" instead of a direction if calibration hasn't
        been done yet - no silent fallback to the old thresholds for
        the main label, on purpose.
        """
        region = self._nearest_calibrated_region(horizontal_ratio, vertical_ratio)
        if region is None:
            return "Calibrate First"
        return config.REGION_TO_DIRECTION.get(region, "Calibrate First")
    
    def _update_blink_state(self, left_blink_score, right_blink_score):
        """
        Tracks how long both eyes have been continuously closed
        together, and counts it as a deliberate "blink select" once
        they've been held shut for at least BLINK_SELECT_HOLD_MS
        before reopening. Short blinks (normal blinking) never cross
        that hold time, so they don't count - only a real, held-shut
        blink does.

        Returns (both_eyes_closed, eyes_closed_ms) for the current
        frame - eyes_closed_ms keeps climbing while eyes are held
        shut, and resets to 0 once they're open again.
        """
        both_eyes_closed = (
            left_blink_score > config.BLINK_CLOSED_SCORE_THRESHOLD
            and right_blink_score > config.BLINK_CLOSED_SCORE_THRESHOLD
        )

        now = time.monotonic()
        eyes_closed_ms = 0

        if both_eyes_closed:
            if self._eyes_closed_since is None:
                self._eyes_closed_since = now
            eyes_closed_ms = (now - self._eyes_closed_since) * 1000
        else:
            if self._eyes_closed_since is not None:
                held_ms = (now - self._eyes_closed_since) * 1000
                if held_ms >= config.BLINK_SELECT_HOLD_MS:
                    self._blink_select_count += 1
                self._eyes_closed_since = None
        
        return both_eyes_closed, eyes_closed_ms

    
    def reset_screen_calibration(self):
        """Wipes any existing calibration data - used when starting a fresh calibration run."""
        self.screen_calibration = {name: None for name in config.CALIBRATION_TARGET_NAMES}
        self.calibration_complete = False
        self.calibrated_face_width_ratio = None
        self.current_calibration_point = None
        self.current_calibration_sample_count = 0

    def start_screen_calibration_point(self, target_name):
        """Called by the calibration window when it moves on to a new dot - just resets the progress counters."""
        self.current_calibration_point = target_name
        self.current_calibration_sample_count = 0

    def record_calibration_progress(self, sample_count):
        """Lets the calibration window tell us how many valid samples it's collected so far, for the progress display."""
        self.current_calibration_sample_count = sample_count

    def apply_screen_calibration_point(self, target_name, samples):
        """
        Called once the calibration window has collected enough valid
        samples for one of the nine points. `samples` is a list of
        dicts (one per valid frame) with the same set of keys - this
        reduces them down to a single record using the MEDIAN of each
        field (not the average - median throws out one-off weird
        frames better than an average would).
        """
        if not samples:
            return

        def median_of(key):
            values = [s[key] for s in samples if s.get(key) is not None]
            return statistics.median(values) if values else None

        screen_x, screen_y = config.CALIBRATION_TARGET_POSITIONS[target_name]

        self.screen_calibration[target_name] = {
            "target_name": target_name,
            "screen_x": screen_x,
            "screen_y": screen_y,
            "horizontal_ratio": median_of("horizontal_ratio"),
            "vertical_ratio": median_of("vertical_ratio"),
            "left_horizontal_ratio": median_of("left_horizontal_ratio"),
            "right_horizontal_ratio": median_of("right_horizontal_ratio"),
            "left_vertical_ratio": median_of("left_vertical_ratio"),
            "right_vertical_ratio": median_of("right_vertical_ratio"),
            "face_width_ratio": median_of("face_width_ratio"),
            "head_yaw": median_of("head_yaw"),
            "head_pitch": median_of("head_pitch"),
        }

        if all(self.screen_calibration[name] is not None for name in config.CALIBRATION_TARGET_NAMES):
            self.calibration_complete = True
            face_widths = [
                self.screen_calibration[name]["face_width_ratio"]
                for name in config.CALIBRATION_TARGET_NAMES
                if self.screen_calibration[name]["face_width_ratio"] is not None
            ]
            if face_widths:
                self.calibrated_face_width_ratio = statistics.median(face_widths)

    def predict_screen_region(self, screen_width_px, screen_height_px):
        """
        FIRST STAGE ONLY - given the current gaze reading, finds which
        of the nine calibrated points is "closest" using plain
        Euclidean distance over (horizontal_ratio, vertical_ratio).
        This is nearest-neighbor matching, not real screen-coordinate
        interpolation - the point is just to test whether the system
        can tell the nine regions apart at all before building
        anything fancier on top.

        The actual "which point is closest" math now lives in
        _nearest_calibrated_region() - this method just adds pixel
        coordinates on top of whatever that returns.

        Not wired into the GUI or debug window yet - call this
        directly (e.g. from a quick test script or the Python
        console) once calibration_complete is True.
        """
        current_h = self.last_tracking_data.get("horizontal_ratio")
        current_v = self.last_tracking_data.get("vertical_ratio")

        best_name = self._nearest_calibrated_region(current_h, current_v)

        if best_name is None:
            return {
                "region": None, "screen_x": None, "screen_y": None,
                "pixel_x": None, "pixel_y": None, "valid": False,
                "tracking_quality": self.last_tracking_data.get("tracking_quality", "NO FACE"),
            }

        point = self.screen_calibration[best_name]
        pixel_x = int(point["screen_x"] * screen_width_px)
        pixel_y = int(point["screen_y"] * screen_height_px)

        return {
            "region": best_name,
            "screen_x": point["screen_x"],
            "screen_y": point["screen_y"],
            "pixel_x": pixel_x,
            "pixel_y": pixel_y,
            "valid": True,
            "tracking_quality": self.last_tracking_data.get("tracking_quality"),
        }
    def close(self):
        self.landmarker.close()
