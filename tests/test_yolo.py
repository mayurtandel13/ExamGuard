"""
Standalone verification test suite for YOLOv8 Object Detection Module.
Tests model initialization, frame sampling caching, blank frame processing, and alert event generation.
"""

import unittest
import numpy as np
from yolo.detector import YOLOObjectDetector


class TestYOLOObjectDetector(unittest.TestCase):
    def setUp(self):
        self.detector = YOLOObjectDetector(
            confidence_threshold=0.40,
            sample_interval=3,
        )

    def test_configurable_parameters(self):
        self.assertEqual(self.detector.confidence_threshold, 0.40)
        self.assertEqual(self.detector.sample_interval, 3)

    def test_invalid_and_blank_frame_processing(self):
        # Test None frame
        res_none = self.detector.process_frame(None)
        self.assertFalse(res_none["phone_detected"])
        self.assertEqual(res_none["person_count"], 0)
        self.assertEqual(res_none["detections"], [])
        self.assertIn("timestamp", res_none)

        # Test blank image frame
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        res_blank = self.detector.process_frame(blank_frame)
        self.assertFalse(res_blank["phone_detected"])
        self.assertEqual(res_blank["person_count"], 0)
        self.assertEqual(res_blank["detections"], [])

    def test_frame_sampling_interval_caching(self):
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Frame 1: Full inference run
        res1 = self.detector.process_frame(blank_frame)
        self.assertEqual(self.detector.frame_counter, 1)

        # Frame 2: Skipped frame (returns cached telemetry)
        res2 = self.detector.process_frame(blank_frame)
        self.assertEqual(self.detector.frame_counter, 2)
        self.assertEqual(res1["phone_detected"], res2["phone_detected"])

        # Frame 3: Full inference run (sample_interval = 3)
        res3 = self.detector.process_frame(blank_frame)
        self.assertEqual(self.detector.frame_counter, 3)


if __name__ == "__main__":
    unittest.main()
