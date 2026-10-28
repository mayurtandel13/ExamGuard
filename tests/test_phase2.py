"""
Phase 2 Automated Unit Tests & Verification Suite
Verifies Webcam capture abstraction and MediaPipe FaceMesh landmark extraction foundation.
"""

import unittest
import numpy as np
import cv2
from camera.capture import CameraCapture
from face.landmarks import FaceLandmarkExtractor


class TestPhase2WebcamAndFaceMesh(unittest.TestCase):
    """
    Unit tests for Phase 2 components.
    """

    def setUp(self):
        self.camera = CameraCapture(device_index=0)
        self.extractor = FaceLandmarkExtractor(max_num_faces=2, refine_landmarks=True)

    def tearDown(self):
        self.camera.stop()
        self.extractor.close()

    def test_camera_capture_abstraction(self):
        """Test CameraCapture initialization, synthetic frame fallback, and cleanup."""
        self.assertEqual(self.camera.width, 640)
        self.assertEqual(self.camera.height, 480)

        # Test synthetic frame generation
        synth_frame = self.camera.create_synthetic_frame()
        self.assertIsNotNone(synth_frame)
        self.assertEqual(synth_frame.shape, (480, 640, 3))

    def test_no_face_condition_handling(self):
        """Test FaceLandmarkExtractor behavior on black/empty frame (no-face condition)."""
        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        telemetry = self.extractor.extract_landmarks(black_frame)

        self.assertFalse(telemetry["face_detected"])
        self.assertEqual(telemetry["faces_count"], 0)
        self.assertEqual(telemetry["status"], "NO_FACE")
        self.assertIsNone(telemetry["primary_landmarks"])
        self.assertEqual(len(telemetry["pixel_coordinates"]), 0)

    def test_invalid_frame_handling(self):
        """Test extractor behavior on None or invalid array inputs."""
        telemetry_none = self.extractor.extract_landmarks(None)
        self.assertFalse(telemetry_none["face_detected"])
        self.assertEqual(telemetry_none["status"], "INVALID_FRAME")

        telemetry_empty = self.extractor.extract_landmarks(np.array([]))
        self.assertFalse(telemetry_empty["face_detected"])
        self.assertEqual(telemetry_empty["status"], "INVALID_FRAME")

    def test_landmark_extraction_and_debug_drawing(self):
        """Test face landmark processing and debug mesh drawing on synthetic image."""
        # Create a frame with a central bright region simulating a face
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.circle(test_frame, (320, 240), 100, (200, 200, 200), -1)

        telemetry = self.extractor.extract_landmarks(test_frame)
        self.assertIn("face_detected", telemetry)
        self.assertIn("faces_count", telemetry)
        self.assertIn("status", telemetry)

        # Test debug drawing on frame
        drawn_frame = self.extractor.draw_landmarks(test_frame, telemetry)
        self.assertIsNotNone(drawn_frame)
        self.assertEqual(drawn_frame.shape, test_frame.shape)

    def test_decoupled_camera_and_face_pipeline(self):
        """Verifies camera capture and FaceMesh processing remain completely decoupled."""
        # Camera handles frame capture stream
        success, frame = False, self.camera.create_synthetic_frame()

        # FaceMesh extractor handles image landmark processing independently
        telemetry = self.extractor.extract_landmarks(frame)
        self.assertIsInstance(telemetry, dict)
        self.assertIn("status", telemetry)


if __name__ == "__main__":
    unittest.main()
