"""
Random helper functions that a few different files need.
Nothing fancy, just avoiding copy-pasting the same math everywhere.
"""

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
