"""
Independent verification test for Facial Landmark Extractor Module.
"""

import unittest
import numpy as np
from face.landmarks import FaceLandmarkExtractor


class TestFaceLandmarkExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = FaceLandmarkExtractor(max_num_faces=2, refine_landmarks=True)

    def test_null_and_empty_frame_handling(self):
        # 1. Test None frame
        res_none = self.extractor.extract_landmarks(None)
        self.assertFalse(res_none["face_detected"])
        self.assertEqual(res_none["status"], "INVALID_FRAME")

        # 2. Test empty numpy array
        res_empty = self.extractor.extract_landmarks(np.array([]))
        self.assertFalse(res_empty["face_detected"])
        self.assertEqual(res_empty["status"], "INVALID_FRAME")

    def test_synthetic_blank_frame(self):
        # 3. Test blank black frame (no face present)
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        res = self.extractor.extract_landmarks(blank_frame)

        self.assertFalse(res["face_detected"])
        self.assertEqual(res["faces_count"], 0)
        self.assertIsNone(res["primary_landmarks"])
        self.assertEqual(res["pixel_coordinates"], [])
        self.assertEqual(res["status"], "NO_FACE")

        # Drawing on no-face frame should return identical frame without error
        annotated = self.extractor.draw_landmarks(blank_frame, res)
        self.assertTrue(np.array_equal(blank_frame, annotated))

    def tearDown(self):
        self.extractor.close()


if __name__ == "__main__":
    unittest.main()
