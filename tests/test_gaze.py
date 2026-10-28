"""
Standalone verification test suite for Eye Gaze & Attention Tracking Module.
Tests gaze direction classification, normalized deviation, rolling window glance frequency/duration, and continuous Attention Score calculation.
"""

import time
import unittest
import numpy as np
from gaze.tracker import GazeTracker


class TestGazeTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = GazeTracker(
            off_center_threshold=0.30,
            ear_threshold=0.18,
            window_seconds=4.0,
            frequency_penalty_weight=0.15,
            duration_penalty_weight=0.25,
        )

    def test_configurable_parameters(self):
        self.assertEqual(self.tracker.off_center_threshold, 0.30)
        self.assertEqual(self.tracker.ear_threshold, 0.18)
        self.assertEqual(self.tracker.window_seconds, 4.0)
        self.assertEqual(self.tracker.frequency_penalty_weight, 0.15)
        self.assertEqual(self.tracker.duration_penalty_weight, 0.25)

    def test_null_face_landmarks_handling(self):
        # Process frame with None landmarks
        res = self.tracker.process(None, (480, 640, 3))
        self.assertEqual(res["gaze_state"], "NO_FACE")
        self.assertIn("attention_score", res)
        self.assertIn("off_screen_frequency", res)
        self.assertIn("off_screen_duration", res)
        self.assertIn("timestamp", res)

    def test_attention_score_decay_on_off_screen_glances(self):
        now = time.time()
        # Simulate rolling window entries for 3 distinct off-screen glances
        self.tracker._update_rolling_window(now - 3.0, "CENTER", is_off_screen=False, frame_dt=0.5)
        self.tracker._update_rolling_window(now - 2.5, "GAZE_LEFT", is_off_screen=True, frame_dt=0.5)
        self.tracker._update_rolling_window(now - 2.0, "CENTER", is_off_screen=False, frame_dt=0.5)
        self.tracker._update_rolling_window(now - 1.5, "GAZE_RIGHT", is_off_screen=True, frame_dt=0.5)
        self.tracker._update_rolling_window(now - 1.0, "CENTER", is_off_screen=False, frame_dt=0.5)
        self.tracker._update_rolling_window(now - 0.5, "GAZE_LEFT", is_off_screen=True, frame_dt=0.5)

        metrics = self.tracker._calculate_window_metrics_and_attention(current_deviation=0.8)

        # 3 off-screen glances in rolling window
        self.assertEqual(metrics["off_screen_frequency"], 3)
        self.assertGreater(metrics["off_screen_duration"], 0.0)
        # Attention score should decrease below 1.0 due to penalties
        self.assertLess(metrics["attention_score"], 1.0)
        self.assertGreaterEqual(metrics["attention_score"], 0.0)


if __name__ == "__main__":
    unittest.main()
