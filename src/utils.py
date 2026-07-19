"""
Random helper functions that a few different files need.
Nothing fancy, just avoiding copy-pasting the same math everywhere.
"""

import cv2
import numpy as np


def landmarks_to_np(landmarks, indices, frame_w, frame_h):
    """
    MediaPipe gives us landmark coordinates as decimals between 0 and 1
    (like, 0.5 = middle of the frame). This grabs the landmarks we
    actually care about (by index) and converts them into real pixel
    coordinates so we can use them with OpenCV.
    """
    points = []
    for idx in indices:
        lm = landmarks[idx]
        points.append([lm.x * frame_w, lm.y * frame_h])
    return np.array(points, dtype=np.float64)


def eye_center(eye_points):
    """Averages a bunch of points to get the center point. Used to find where the iris is."""
    return eye_points.mean(axis=0)

def distance(point_a, point_b):
    """plain straight-line pixel distance between two (x, y) points."""
    return float(np.hypot(point_b[0] - point_a[0], point_b[1] - point_a[1]))

def clamp(value, min_value, max_value):
    """Keeps a number from going above or below a min/max range."""
    return max(min_value, min(value, max_value))


def moving_average(values, window=5):
    """
    Averages the last few gaze readings together so the direction label
    doesn't flicker like crazy every single frame. Pretty basic smoothing,
    could definitely be better.

    TODO: Improve gaze smoothing (e.g. exponential smoothing, Kalman
    filter, or outlier rejection) for more stable direction output.
    """
    if len(values) == 0:
        return 0
    window_slice = values[-window:]
    return sum(window_slice) / len(window_slice)

def estimate_head_pose(landmarks, w, h):
    """
    Rough head yaw/pitch/roll estimate using OpenCV's solvePnP, matched
    against a generic average face shape (this is the standard 6-point
    approach - nose tip, chin, eye corners, mouth corners - that most
    OpenCV head-pose tutorials use). It's an approximation, not a
    precise measurement - it'll be off for unusual face proportions -
    but it's good enough to catch "this person turned way too far to
    the side, don't trust this frame."

    Returns (yaw, pitch, roll) in degrees, or (None, None, None) if
    anything goes wrong. Wrapped in a try/except on purpose - a failed
    head pose estimate should never crash the app, it should just mean
    we don't have a head pose for this particular frame.
    """
    try:
        # nose tip, chin, left eye outer corner, right eye outer
        # corner, left mouth corner, right mouth corner
    
        pose_landmark_indices = [1, 152, 263, 33, 291, 61]
        image_points = landmarks_to_np(landmarks, pose_landmark_indices, w, h)

        # Generic 3D reference face (rough millimeters, not tied to any
        # real person) - this is a commonly used approximate shape for
        # this kind of 6-point head pose estimate.
        model_points = np.array([
            (0.0, 0.0, 0.0),           # Nose tip
            (0.0, -330.0, -65.0),      # Chin
            (-225.0, 170.0, -135.0),   # Left eye outer corner
            (225.0, 170.0, -135.0),    # Right eye outer corner
            (-150.0, -150.0, -125.0),  # Left mouth corner
            (150.0, -150.0, -125.0),   # Right mouth corner
        ])

        # Rough camera matrix - we don't have real lens calibration for
        # whatever webcam someone's using, so this just assumes a
        # "reasonable" focal length based on frame width. Good enough
        # for a rough yaw/pitch estimate, not for anything precise.
        focal_length = w
        center = (w / 2, h / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1],
        ], dtype=np.float64)
        dist_coeffs = np.zeros((4, 1))  # assuming no lens distortion

        success, rotation_vector, _ = cv2.solvePnP(
            model_points, image_points, camera_matrix, dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )

        if not success:
            return None, None, None

        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)

        # Standard rotation-matrix-to-Euler-angles decomposition.
        sy = np.sqrt(rotation_matrix[0, 0] ** 2 + rotation_matrix[1, 0] ** 2)
        singular = sy < 1e-6

        if not singular:
            pitch = np.arctan2(rotation_matrix[2, 1], rotation_matrix[2, 2])
            yaw = np.arctan2(-rotation_matrix[2, 0], sy)
            roll = np.arctan2(rotation_matrix[1, 0], rotation_matrix[0, 0])
        else:
            pitch = np.arctan2(-rotation_matrix[1, 2], rotation_matrix[1, 1])
            yaw = np.arctan2(-rotation_matrix[2, 0], sy)
            roll = 0.0

        return float(np.degrees(yaw)), float(np.degrees(pitch)), float(np.degrees(roll))

    except Exception:
        # Deliberately broad - lots of things could go wrong here
        # (missing landmarks, weird geometry, solvePnP just failing)
        # and none of them should take the app down with them.
        return None, None, None
