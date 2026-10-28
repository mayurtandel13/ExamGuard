"""
Eye Gaze & Attention Tracking Module using MediaPipe Iris Landmarks.
Tracks iris displacement, eye aspect ratio (EAR), gaze deviation, off-screen glance frequency/duration over a rolling time window, and generates a continuous Attention Score.
"""

import time
import math
from collections import deque
import numpy as np
from config import GAZE_CONFIG


class GazeTracker:
    """
    Decoupled Eye Gaze & Attention Tracker.
    Calculates normalized gaze deviation, maintains a rolling time window, tracks glance frequency & duration,
    and computes a continuous Attention Score.
    """

    def __init__(
        self,
        off_center_threshold=GAZE_CONFIG["OFF_CENTER_THRESHOLD"],
        ear_threshold=GAZE_CONFIG["EAR_BLINK_THRESHOLD"],
        window_seconds=5.0,
        frequency_penalty_weight=0.1,
        duration_penalty_weight=0.2,
        sustained_frames_thresh=GAZE_CONFIG["SUSTAINED_DISTRACTION_FRAMES"],
    ):
        self.off_center_threshold = off_center_threshold
        self.ear_threshold = ear_threshold
        self.window_seconds = window_seconds
        self.frequency_penalty_weight = frequency_penalty_weight
        self.duration_penalty_weight = duration_penalty_weight
        self.sustained_frames_thresh = sustained_frames_thresh

        # Landmark indices for Left Eye and Iris (MediaPipe FaceMesh topology)
        self.LEFT_EYE_CORNER_OUTER = 33
        self.LEFT_EYE_CORNER_INNER = 133
        self.LEFT_EYE_TOP = 159
        self.LEFT_EYE_BOTTOM = 145
        self.LEFT_IRIS = [468, 469, 470, 471, 472]

        # Landmark indices for Right Eye and Iris
        self.RIGHT_EYE_CORNER_OUTER = 263
        self.RIGHT_EYE_CORNER_INNER = 362
        self.RIGHT_EYE_TOP = 386
        self.RIGHT_EYE_BOTTOM = 374
        self.RIGHT_IRIS = [473, 474, 475, 476, 477]

        # Rolling time window history buffer storing tuples: (timestamp, gaze_state, is_off_screen, frame_duration)
        self.history_window = deque()
        self.last_frame_time = None
        self.distraction_frame_counter = 0

    @staticmethod
    def _euclidean_dist(pt1, pt2):
        return math.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])

    def _get_landmark_pt(self, landmarks, idx, w, h):
        lm = landmarks.landmark[idx]
        return np.array([lm.x * w, lm.y * h])

    def compute_ear(self, landmarks, w, h, is_left=True):
        """
        Computes Eye Aspect Ratio (EAR) for blink detection.
        """
        if is_left:
            top = self._get_landmark_pt(landmarks, self.LEFT_EYE_TOP, w, h)
            bottom = self._get_landmark_pt(landmarks, self.LEFT_EYE_BOTTOM, w, h)
            outer = self._get_landmark_pt(landmarks, self.LEFT_EYE_CORNER_OUTER, w, h)
            inner = self._get_landmark_pt(landmarks, self.LEFT_EYE_CORNER_INNER, w, h)
        else:
            top = self._get_landmark_pt(landmarks, self.RIGHT_EYE_TOP, w, h)
            bottom = self._get_landmark_pt(landmarks, self.RIGHT_EYE_BOTTOM, w, h)
            outer = self._get_landmark_pt(landmarks, self.RIGHT_EYE_CORNER_OUTER, w, h)
            inner = self._get_landmark_pt(landmarks, self.RIGHT_EYE_CORNER_INNER, w, h)

        vertical = self._euclidean_dist(top, bottom)
        horizontal = self._euclidean_dist(outer, inner)

        if horizontal == 0:
            return 0.0
        return vertical / horizontal

    def compute_gaze_ratio(self, landmarks, w, h, is_left=True):
        """
        Computes Iris Position Ratio relative to eye corners [0.0 (outer) to 1.0 (inner)].
        """
        if is_left:
            outer = self._get_landmark_pt(landmarks, self.LEFT_EYE_CORNER_OUTER, w, h)
            inner = self._get_landmark_pt(landmarks, self.LEFT_EYE_CORNER_INNER, w, h)
            iris_center = self._get_landmark_pt(landmarks, self.LEFT_IRIS[0], w, h)
        else:
            outer = self._get_landmark_pt(landmarks, self.RIGHT_EYE_CORNER_OUTER, w, h)
            inner = self._get_landmark_pt(landmarks, self.RIGHT_EYE_CORNER_INNER, w, h)
            iris_center = self._get_landmark_pt(landmarks, self.RIGHT_IRIS[0], w, h)

        total_eye_width = self._euclidean_dist(outer, inner)
        dist_from_outer = self._euclidean_dist(outer, iris_center)

        if total_eye_width == 0:
            return 0.5

        return dist_from_outer / total_eye_width

    def process(self, face_landmarks, frame_shape):
        """
        Processes face landmarks for Gaze telemetry, rolling glance statistics, and Attention Score.
        Returns structured telemetry dictionary.
        """
        now = time.time()
        dt = (now - self.last_frame_time) if self.last_frame_time else 0.033
        self.last_frame_time = now

        h, w = frame_shape[0], frame_shape[1]

        telemetry = {
            "timestamp": now,
            "ear_left": 0.0,
            "ear_right": 0.0,
            "avg_ear": 0.0,
            "eyes_closed": False,
            "gaze_left_ratio": 0.5,
            "gaze_right_ratio": 0.5,
            "avg_gaze_ratio": 0.5,
            "gaze_state": "NO_FACE" if face_landmarks is None else "CENTER",
            "gaze_deviation_score": 0.0,
            "attention_score": 1.0,
            "off_screen_frequency": 0,
            "off_screen_duration": 0.0,
            "sustained_distraction": False,
            "active_events": [],
        }

        if face_landmarks is None:
            self._update_rolling_window(now, "NO_FACE", is_off_screen=True, frame_dt=dt)
            telemetry.update(self._calculate_window_metrics_and_attention(0.0))
            return telemetry

        ear_l = self.compute_ear(face_landmarks, w, h, is_left=True)
        ear_r = self.compute_ear(face_landmarks, w, h, is_left=False)
        avg_ear = (ear_l + ear_r) / 2.0

        telemetry["ear_left"] = float(ear_l)
        telemetry["ear_right"] = float(ear_r)
        telemetry["avg_ear"] = float(avg_ear)

        if avg_ear < self.ear_threshold:
            telemetry["eyes_closed"] = True
            telemetry["gaze_state"] = "EYES_CLOSED"
            self._update_rolling_window(now, "EYES_CLOSED", is_off_screen=True, frame_dt=dt)
            telemetry.update(self._calculate_window_metrics_and_attention(0.5))
            return telemetry

        # Gaze Iris Ratio Calculation
        try:
            gaze_l = self.compute_gaze_ratio(face_landmarks, w, h, is_left=True)
            gaze_r = self.compute_gaze_ratio(face_landmarks, w, h, is_left=False)
            avg_gaze = (gaze_l + gaze_r) / 2.0
            telemetry["gaze_left_ratio"] = float(gaze_l)
            telemetry["gaze_right_ratio"] = float(gaze_r)
            telemetry["avg_gaze_ratio"] = float(avg_gaze)

            # Continuous deviation score between 0.0 (center) and 1.0 (max off-center)
            gaze_offset = abs(avg_gaze - 0.5)
            deviation_score = min(1.0, gaze_offset / self.off_center_threshold)
            telemetry["gaze_deviation_score"] = float(deviation_score)

            # Approximate Gaze Classification (GAZE_LEFT, GAZE_RIGHT, CENTER)
            if avg_gaze < (0.5 - self.off_center_threshold):
                gaze_state = "GAZE_LEFT"
                is_off_screen = True
                self.distraction_frame_counter += 1
            elif avg_gaze > (0.5 + self.off_center_threshold):
                gaze_state = "GAZE_RIGHT"
                is_off_screen = True
                self.distraction_frame_counter += 1
            else:
                gaze_state = "CENTER"
                is_off_screen = False
                self.distraction_frame_counter = max(0, self.distraction_frame_counter - 1)

            telemetry["gaze_state"] = gaze_state

            if self.distraction_frame_counter >= self.sustained_frames_thresh:
                telemetry["sustained_distraction"] = True
                event = {
                    "type": "GAZE_DISTRACTION",
                    "severity": "MEDIUM",
                    "message": f"Eye gaze directed away from screen ({gaze_state})",
                    "timestamp": now,
                    "details": {"gaze_state": gaze_state, "deviation_score": round(deviation_score, 2)},
                }
                telemetry["active_events"].append(event)

            # Update rolling window & compute dynamic Attention Score
            self._update_rolling_window(now, gaze_state, is_off_screen=is_off_screen, frame_dt=dt)
            telemetry.update(self._calculate_window_metrics_and_attention(deviation_score))

        except (IndexError, KeyError, AttributeError):
            telemetry["gaze_state"] = "CENTER"
            self._update_rolling_window(now, "CENTER", is_off_screen=False, frame_dt=dt)
            telemetry.update(self._calculate_window_metrics_and_attention(0.0))

        return telemetry

    def _update_rolling_window(self, now, gaze_state, is_off_screen, frame_dt):
        """
        Updates the rolling time window and evicts old entries past window_seconds.
        """
        self.history_window.append((now, gaze_state, is_off_screen, frame_dt))
        while self.history_window and (now - self.history_window[0][0]) > self.window_seconds:
            self.history_window.popleft()

    def _calculate_window_metrics_and_attention(self, current_deviation):
        """
        Computes glance frequency, glance duration, and continuous Attention Score.
        Attention score starts at 1.0 (100% focused) and decreases with off-screen frequency & duration.
        """
        if not self.history_window:
            return {"attention_score": 1.0, "off_screen_frequency": 0, "off_screen_duration": 0.0}

        # Calculate off-screen glance frequency (number of distinct off-screen transitions)
        off_screen_freq = 0
        prev_off = False
        total_off_duration = 0.0

        for t, state, is_off, dt in self.history_window:
            if is_off:
                total_off_duration += dt
                if not prev_off:
                    off_screen_freq += 1
            prev_off = is_off

        # Continuous Attention Score calculation [0.0 to 1.0]
        # Base penalty from current frame deviation
        dev_penalty = 0.3 * current_deviation

        # Frequency penalty (more off-screen glances = lower score)
        freq_penalty = self.frequency_penalty_weight * off_screen_freq

        # Duration penalty (longer cumulative time looking away = lower score)
        dur_ratio = min(1.0, total_off_duration / self.window_seconds)
        dur_penalty = self.duration_penalty_weight * dur_ratio

        # Compute final Attention Score
        attention_score = max(0.0, min(1.0, 1.0 - (dev_penalty + freq_penalty + dur_penalty)))

        return {
            "attention_score": round(float(attention_score), 3),
            "off_screen_frequency": off_screen_freq,
            "off_screen_duration": round(float(total_off_duration), 2),
        }

    def reset(self):
        """Resets gaze history window and frame counters."""
        self.history_window.clear()
        self.last_frame_time = None
        self.distraction_frame_counter = 0

    def close(self):
        """Releases gaze tracker resources."""
        self.reset()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


