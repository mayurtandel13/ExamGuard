"""
Unit Test for Behavioral Fusion Engine
"""

import unittest
from modules.fusion_engine import BehavioralFusionEngine


class TestBehavioralFusionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = BehavioralFusionEngine()

    def test_normal_behavior_scoring(self):
        head_tel = {"deviation_score": 0.0, "status": "FORWARD"}
        gaze_tel = {"gaze_deviation_score": 0.0, "gaze_state": "CENTER"}
        yolo_tel = {"phone_detected": False, "person_count": 1}
        shortcuts = []

        res = self.engine.compute_fusion_score(head_tel, gaze_tel, yolo_tel, shortcuts)

        self.assertEqual(res["risk_level"], "LOW")
        self.assertLess(res["cheating_probability_score"], 0.35)
        self.assertEqual(len(res["active_events"]), 0)

    def test_mobile_phone_detection_risk(self):
        head_tel = {"deviation_score": 0.0, "status": "FORWARD"}
        gaze_tel = {"gaze_deviation_score": 0.0, "gaze_state": "CENTER"}
        yolo_tel = {"phone_detected": True, "phone_confidence": 0.88, "person_count": 1}
        shortcuts = []

        # Run several frames to allow EMA to ramp up
        for _ in range(25):
            res = self.engine.compute_fusion_score(head_tel, gaze_tel, yolo_tel, shortcuts)

        self.assertIn(res["risk_level"], ["MEDIUM", "HIGH"])
        self.assertGreater(res["cheating_probability_score"], 0.30)
        self.assertTrue(any(e["type"] == "MOBILE_PHONE_DETECTED" for e in res["active_events"]))

    def test_multi_person_and_shortcut_risk(self):
        head_tel = {"deviation_score": 0.5, "status": "LOOKING_RIGHT", "yaw": 30.0, "pitch": 0.0}
        gaze_tel = {"gaze_deviation_score": 0.8, "gaze_state": "GAZE_RIGHT"}
        yolo_tel = {"phone_detected": True, "phone_confidence": 0.9, "person_count": 2}
        shortcuts = [{"shortcut": "alt+tab"}]

        for _ in range(15):
            res = self.engine.compute_fusion_score(head_tel, gaze_tel, yolo_tel, shortcuts)

        self.assertEqual(res["risk_level"], "HIGH")
        self.assertGreaterEqual(res["cheating_probability_score"], 0.70)


if __name__ == "__main__":
    unittest.main()
