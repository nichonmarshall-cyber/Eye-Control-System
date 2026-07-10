"""
Just a wrapper around OpenCV's webcam stuff so the rest of the app
doesn't have to deal with cv2.VideoCapture directly. Keeps things
separated in case someone wants to swap the camera logic out later.
"""

import cv2

from src import config


class Camera:
    def __init__(self, camera_index=config.CAMERA_INDEX):
        self.camera_index = camera_index
        self.cap = None

    def start(self):
        """Turns the webcam on. Returns True/False depending on if it worked."""
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

        # TODO: Add proper error handling for cameras that fail to open,
        # are already in use by another app, or disconnect mid-session.
        # Right now we only check if it opened in the first place.
        if not self.cap.isOpened():
            return False
        return True

    def read_frame(self):
        """
        Grabs one frame from the webcam.
        Returns (success, frame) - frame is None if something went wrong.
        """
        if self.cap is None or not self.cap.isOpened():
            return False, None

        success, frame = self.cap.read()
        if not success:
            return False, None

        frame = cv2.flip(frame, 1)  # flip it so it acts like a mirror, feels more natural
        return True, frame

    def stop(self):
        """Turns the webcam off."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def is_running(self):
        return self.cap is not None and self.cap.isOpened()
