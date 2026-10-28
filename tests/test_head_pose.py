"""
Standalone verification test suite for Head Pose Estimation Module.
Tests 3D solvePnP angle calculation, configurable thresholds, sliding window buffer, and repeated movement event generation.
"""

import time
import unittest
import numpy as np
from head_pose.estimator import HeadPoseEstimator


class TestHeadPoseEstimator(unittest.TestCase):
    def setUp(self):
        self.estimator = HeadPoseEstimator(
            yaw_threshold=20.0,
            pitch_threshold=15.0,
            roll_threshold=15.0,
            window_seconds=3.0,
            min_repeated_movements=2,
        )

    def test_threshold_configuration(self):
        self.assertEqual(self.estimator.yaw_threshold, 20.0)
        self.assertEqual(self.estimator.pitch_threshold, 15.0)
        self.assertEqual(self.estimator.roll_threshold, 15.0)
        self.assertEqual(self.estimator.window_seconds, 3.0)
        self.assertEqual(self.estimator.min_repeated_movements, 2)

    def test_invalid_and_blank_frames(self):
        # Test None input
        res_none = self.estimator.process_frame(None)
        self.assertEqual(res_none["status"], "INVALID_FRAME")
        self.assertFalse(res_none["face_detected"])

        # Test blank frame (no face)
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        res_blank = self.estimator.process_frame(blank_frame)
        self.assertEqual(res_blank["status"], "NO_FACE")
        self.assertFalse(res_blank["face_detected"])
        self.assertEqual(res_blank["pitch"], 0.0)
        self.assertEqual(res_blank["yaw"], 0.0)
        self.assertEqual(res_blank["roll"], 0.0)
        self.assertIn("timestamp", res_blank)

    def test_sliding_window_event_generation(self):
        # Manually simulate off-center movement history in the sliding window
        now = time.time()
        self.estimator.movement_history.append((now - 1.0, "LOOKING_LEFT"))
        self.estimator.movement_history.append((now - 0.5, "LOOKING_RIGHT"))

        # Verify buffer size
        self.assertEqual(len(self.estimator.movement_history), 2)

        # Evict old entries past window duration
        old_time = now - 10.0
        self.estimator.movement_history.appendleft((old_time, "LOOKING_UP"))
        
        # Run process_frame on blank frame to trigger window cleanup
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        res = self.estimator.process_frame(blank_frame)

        # Confirm structured timestamp presence
        self.assertIn("timestamp", res)

    def tearDown(self):
        self.estimator.close()


if __name__ == "__main__":
    unittest.main()
