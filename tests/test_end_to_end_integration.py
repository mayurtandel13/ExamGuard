"""
Final End-to-End System Integration Test Suite
Verifies the complete proctoring pipeline:
Camera -> FaceMesh -> Head Pose -> Eye Gaze -> YOLO Detection + Keyboard Monitoring
-> Event Logger -> Behavioral Fusion Engine -> Risk Classification -> Behavioral Timeline -> Dashboard Context
"""

import unittest
import time
import os

from camera.capture import CameraCapture
from face.landmarks import FaceLandmarkExtractor
from head_pose.estimator import HeadPoseEstimator
from gaze.tracker import GazeTracker
from yolo.detector import YOLOObjectDetector
from keyboard.monitor import KeyboardMonitor
from fusion.engine import BehavioralFusionEngine
from risk_scoring.scorer import RiskScorer
from timeline.timeline import BehavioralTimeline
from timeline.visualizer import TimelineVisualizer
from event_logging.logger import SessionDataLogger


class TestEndToEndSystemIntegration(unittest.TestCase):
    def setUp(self):
        self.camera = CameraCapture(device_index=1)
        self.landmark_extractor = FaceLandmarkExtractor(max_num_faces=2, refine_landmarks=True)
        self.head_estimator = HeadPoseEstimator()
        self.gaze_tracker = GazeTracker()
        self.yolo_detector = YOLOObjectDetector(confidence_threshold=0.30, sample_interval=1)
        self.kb_monitor = KeyboardMonitor()
        self.fusion_engine = BehavioralFusionEngine(use_ema=False)
        self.risk_scorer = RiskScorer()
        self.timeline = BehavioralTimeline()
        self.logger = SessionDataLogger()

    def tearDown(self):
        self.kb_monitor.stop()
        self.camera.stop()
        self.head_estimator.close()
        self.landmark_extractor.close()
        if self.yolo_detector:
            self.yolo_detector.close()
        self.gaze_tracker.close()

    def test_full_pipeline_stream_execution(self):
        """Executes full multi-frame end-to-end pipeline session with hardware/synthetic fallback stream."""
        # 1. Start Session
        self.timeline.start_session()
        self.logger.start_session()
        self.kb_monitor.start()
        cam_ok = self.camera.start(auto_fallback=True)

        t_start = time.time()

        # Simulate 10 live frames passing through the entire pipeline
        for frame_idx in range(10):
            frame_now = time.time()

            if cam_ok:
                ret, frame = self.camera.read_frame()
                if not ret or frame is None:
                    frame = self.camera.create_synthetic_frame()
            else:
                frame = self.camera.create_synthetic_frame()

            # Pipeline Step 1: Face Mesh Extraction
            landmark_tel = self.landmark_extractor.extract_landmarks(frame)

            # Pipeline Step 2: 3D Head Pose Estimation
            head_tel = self.head_estimator.process_frame(frame)

            # Pipeline Step 3: Eye Gaze & Continuous Attention Tracking
            gaze_tel = self.gaze_tracker.process(landmark_tel.get("primary_landmarks"), frame.shape)

            # Pipeline Step 4: YOLO Object Detection
            yolo_tel = self.yolo_detector.process_frame(frame) if self.yolo_detector else {
                "phone_detected": False,
                "person_count": 1 if landmark_tel.get("face_detected", False) else 0,
                "multi_person_detected": False,
            }

            # Pipeline Step 5: Keyboard Monitoring
            if frame_idx == 3:
                self.kb_monitor.trigger_simulated_shortcut("alt+tab")
            kb_tel = self.kb_monitor.get_telemetry()

            # Pipeline Step 6: Behavioral Fusion Engine Calculation
            fusion_res = self.fusion_engine.compute_fusion_score(head_tel, gaze_tel, yolo_tel, kb_tel)

            # Pipeline Step 7: Risk Classification Verification
            evaluated_risk = self.risk_scorer.evaluate_risk_level(fusion_res["cheating_probability"])
            self.assertEqual(evaluated_risk, fusion_res["risk_level"])

            # Pipeline Step 8: Behavioral Timeline & Event Logger Recording (Synchronized Timestamp)
            self.timeline.record_snapshot(head_tel, gaze_tel, yolo_tel, kb_tel, fusion_res, timestamp=frame_now)
            self.logger.log_frame(head_tel, gaze_tel, yolo_tel, kb_tel.get("recent_events", []), fusion_res)

        # 2. Stop Session
        self.kb_monitor.stop()
        self.camera.stop()

        # 3. Verify Session Integrity & Reports
        df_risk = self.timeline.get_risk_history_df()
        df_events = self.timeline.get_events_df()

        self.assertEqual(len(df_risk), 10)
        self.assertGreaterEqual(len(df_events), 1)

        # Verify duplicate event filtering (should not log duplicate events every single frame)
        unique_event_count = len(df_events)
        self.assertLessEqual(unique_event_count, 15)

        # Verify Session Summary & Export
        summary = self.timeline.get_session_summary()
        self.assertGreaterEqual(summary["total_events"], 1)
        self.assertIn("LOW", summary["risk_distribution"])

        events_csv, risk_csv = self.timeline.export_to_csv()
        self.assertTrue(len(events_csv) > 0)
        self.assertTrue(len(risk_csv) > 0)

        # 4. Verify Matplotlib Dashboard Generation
        fig_dashboard = TimelineVisualizer.generate_full_dashboard(self.timeline)
        self.assertIsNotNone(fig_dashboard)

        out_img = os.path.join("logs", "e2e_integration_dashboard.png")
        TimelineVisualizer.save_visualization(fig_dashboard, out_img)
        self.assertTrue(os.path.exists(out_img))


if __name__ == "__main__":
    unittest.main()
