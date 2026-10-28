"""
Phase 1 System Structure Verification Test
Verifies that all required component modules can be imported and initialized without errors.
"""

import unittest

# Import all required modular components
from camera import CameraCapture
from face import FaceLandmarkExtractor
from head_pose import HeadPoseEstimator
from gaze import GazeTracker
from keyboard import KeyboardMonitor
from yolo import YOLOObjectDetector
from event_logging import SessionDataLogger
from fusion import BehavioralFusionEngine
from risk_scoring import RiskScorer
from timeline import TimelineVisualizer
from utils import HUDDrawer
from config import FUSION_CONFIG, CAMERA_CONFIG


class TestSystemStructure(unittest.TestCase):
    """
    Verifies modular project scaffolding and interfaces.
    """

    def test_camera_module(self):
        cam = CameraCapture()
        self.assertEqual(cam.device_index, CAMERA_CONFIG["DEVICE_INDEX"])
        self.assertFalse(cam.is_opened())

    def test_face_landmarks_module(self):
        extractor = FaceLandmarkExtractor()
        data = extractor.extract_landmarks(None)
        self.assertIn("face_detected", data)

    def test_head_pose_module(self):
        estimator = HeadPoseEstimator()
        data = estimator.process_frame(None)
        self.assertIn("pitch", data)
        self.assertIn("yaw", data)

    def test_gaze_tracker_module(self):
        tracker = GazeTracker()
        data = tracker.process(None, (480, 640, 3))
        self.assertIn("gaze_state", data)

    def test_keyboard_monitor_module(self):
        kb = KeyboardMonitor()
        self.assertFalse(kb.is_running)

    def test_yolo_detector_module(self):
        yolo = YOLOObjectDetector()
        data = yolo.process_frame(None)
        self.assertIn("phone_detected", data)

    def test_event_logging_module(self):
        logger = SessionDataLogger()
        summary = logger.get_session_summary()
        self.assertIn("avg_cheating_score", summary)

    def test_fusion_engine_module(self):
        engine = BehavioralFusionEngine()
        res = engine.compute_fusion_score({}, {}, {}, [])
        self.assertIn("cheating_probability_score", res)

    def test_risk_scorer_module(self):
        scorer = RiskScorer()
        self.assertEqual(scorer.evaluate_risk_level(0.1), "LOW")
        self.assertEqual(scorer.evaluate_risk_level(0.5), "MEDIUM")
        self.assertEqual(scorer.evaluate_risk_level(0.8), "HIGH")

    def test_timeline_visualizer_module(self):
        fig = TimelineVisualizer.generate_timeline_chart(None, None)
        self.assertIsNotNone(fig)


if __name__ == "__main__":
    unittest.main()
