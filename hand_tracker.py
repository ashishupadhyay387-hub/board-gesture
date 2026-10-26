"""Thin wrapper around MediaPipe Hands + finger-state helpers."""
import math

import cv2
import mediapipe as mp


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


class HandTracker:
    TIPS = (8, 12, 16, 20)   # index, middle, ring, pinky fingertips
    PIPS = (6, 10, 14, 18)   # matching middle joints

    def __init__(self, detection_conf=0.7, tracking_conf=0.6):
        self._mp_hands = mp.solutions.hands
        self._drawer = mp.solutions.drawing_utils
        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=1,
            min_detection_confidence=detection_conf,
            min_tracking_confidence=tracking_conf,
        )

    def process(self, frame_bgr):
        """Return landmarks of the first detected hand, or None."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        result = self._hands.process(rgb)
        if not result.multi_hand_landmarks:
            return None
        return result.multi_hand_landmarks[0]

    @staticmethod
    def to_pixels(landmarks, width, height):
        return [(int(p.x * width), int(p.y * height)) for p in landmarks.landmark]

    def fingers_up(self, pts):
        """[index, middle, ring, pinky] -> True if extended.
        Distance-from-wrist test, so it works even if the hand is tilted."""
        wrist = pts[0]
        return [
            _dist(pts[t], wrist) > _dist(pts[p], wrist) * 1.08
            for t, p in zip(self.TIPS, self.PIPS)
        ]

    def draw_skeleton(self, frame, landmarks):
        self._drawer.draw_landmarks(frame, landmarks, self._mp_hands.HAND_CONNECTIONS)

    def close(self):
        self._hands.close()
