"""
Tests for Mobile Phone Detection in Camera Feed & Post-Exam Submission Audit
Verifies:
1. Classifier strictly assigns HIGH risk and HIGH severity to mobile phone detection.
2. BehavioralFusionEngine marks MOBILE_PHONE_DETECTED with high penalty on phone detection.
3. Database functions record, query, and summarize phone violations in get_phone_events & get_admin_summary.
4. UI components render live camera warning ('Warning: Phone detection has happened') and post-exam clearance card.
5. Worker handles notify_phone_detected, reset_phone_detection, and session info tracking.
6. BehavioralTimeline records mobile phone violation and elevates summary risk.
"""

import json
import time
import unittest
from unittest.mock import patch, MagicMock

from database.db import get_db
from extension_monitor.detector import get_classifier
from fusion.engine import BehavioralFusionEngine
from timeline.timeline import BehavioralTimeline
from dashboard.worker import ProctoringWorker
from dashboard.ui_components import (
    render_phone_detection_live_warning,
    render_phone_clearance_card,
)


class TestPhoneDetectionFlow(unittest.TestCase):
    def setUp(self):
        self.db = get_db()
        self.classifier = get_classifier()
        self.test_session_id = f"TEST-PHONE-{int(time.time() * 1000)}"
        self.test_student_id = "STU-PHONE-001"

        with self.db._lock:
            conn = self.db._get_connection()
            try:
                with conn:
                    conn.execute("""
                        INSERT OR IGNORE INTO students (student_id, full_name, email, department, roll_number)
                        VALUES (?, ?, ?, ?, ?)
                    """, (self.test_student_id, "Phone Test Candidate", "phone@test.edu", "CS", "PHONE-001"))
            finally:
                conn.close()

        self.db.create_or_get_session(
            exam_session_id=self.test_session_id,
            student_id=self.test_student_id,
        )

    def test_classifier_strictly_assigns_high_risk_to_phone_detection(self):
        """1. Classifier strictly returns HIGH risk and HIGH severity when phone is detected."""
        for event_type in ["MOBILE_PHONE_DETECTED", "PHONE_DETECTED"]:
            risk, sev, reason = self.classifier.classify_event({
                "event_type": event_type,
                "confidence": 0.94,
            })
            self.assertEqual(risk, "HIGH", f"Expected HIGH risk for {event_type}")
            self.assertEqual(sev, "HIGH", f"Expected HIGH severity for {event_type}")
            self.assertIn("phone", reason.lower())

    def test_fusion_engine_handles_phone_detection(self):
        """2. Fusion engine factors in phone detection signal and records contributing event."""
        engine = BehavioralFusionEngine(use_ema=False)
        head_tel = {"deviation_score": 0.0, "status": "FORWARD"}
        gaze_tel = {"attention_score": 1.0, "gaze_state": "CENTER"}
        kb_tel = {"keyboard_penalty": 0.0, "recent_events": []}

        # Case A: Clean camera feed without phone
        res_clean = engine.compute_fusion_score(
            head_tel, gaze_tel, {"phone_detected": False, "person_count": 1}, kb_tel
        )
        self.assertFalse(any(e["type"] == "MOBILE_PHONE_DETECTED" for e in res_clean["contributing_events"]))

        # Case B: Phone detected in camera feed
        res_phone = engine.compute_fusion_score(
            head_tel, gaze_tel, {"phone_detected": True, "phone_confidence": 0.95, "person_count": 1}, kb_tel
        )
        self.assertTrue(any(e["type"] == "MOBILE_PHONE_DETECTED" for e in res_phone["contributing_events"]))
        self.assertGreater(res_phone["cheating_probability"], res_clean["cheating_probability"])

    def test_database_records_and_retrieves_phone_violations(self):
        """3. Database stores MOBILE_PHONE_DETECTED events and includes them in get_phone_events and admin summary."""
        event_id = self.db.record_event(
            exam_session_id=self.test_session_id,
            student_id=self.test_student_id,
            event_type="MOBILE_PHONE_DETECTED",
            event_description="Mobile phone detected in proctoring camera frame (Confidence: 94%)",
            detection_method="YOLOv8ObjectDetector",
            risk_level="HIGH",
            severity="HIGH",
            raw_data={"confidence": 0.94, "class_name": "cell phone"},
        )
        self.assertIsNotNone(event_id)

        # Query session phone events
        phone_evts = self.db.get_phone_events(exam_session_id=self.test_session_id)
        self.assertGreaterEqual(len(phone_evts), 1)
        self.assertEqual(phone_evts[0]["event_type"], "MOBILE_PHONE_DETECTED")
        self.assertEqual(phone_evts[0]["risk_level"], "HIGH")

        # Verify admin summary metric counts phone violations
        admin_sum = self.db.get_admin_summary()
        self.assertIn("phone_violations", admin_sum)
        self.assertGreaterEqual(admin_sum["phone_violations"], 1)

    def test_live_warning_ui_component_renders_alert(self):
        """4. render_phone_detection_live_warning renders the explicit warning message."""
        rendered_html = []
        with patch("streamlit.markdown", side_effect=lambda html, **kwargs: rendered_html.append(html)):
            render_phone_detection_live_warning(incident_count=1, peak_confidence=0.92)

        self.assertEqual(len(rendered_html), 1)
        content = rendered_html[0]
        self.assertIn("Mobile Phone Detected in Camera Feed!", content)
        self.assertIn("Warning: Phone detection has happened!", content)
        self.assertIn("Remove the phone immediately.", content)
        self.assertIn("PHONE DETECTED (HIGH RISK)", content)

    def test_submission_clearance_card_when_phone_detected(self):
        """5. render_phone_clearance_card renders clearance withheld when phone was detected."""
        rendered_html = []
        with patch("streamlit.markdown", side_effect=lambda html, **kwargs: rendered_html.append(html)):
            render_phone_clearance_card(
                phone_detected=True,
                incident_count=2,
                peak_confidence=0.94,
            )

        self.assertEqual(len(rendered_html), 1)
        content = rendered_html[0]
        self.assertIn("DEVICE INTEGRITY REPORT: MOBILE PHONE WAS DETECTED DURING EXAM", content)
        self.assertIn("CLEARANCE WITHHELD ❌", content)
        self.assertIn("2 times", content)
        self.assertIn("Live Device Alert", content)

    def test_submission_clearance_card_when_clean(self):
        """6. render_phone_clearance_card renders clean device approval when no phone detected."""
        rendered_html = []
        with patch("streamlit.markdown", side_effect=lambda html, **kwargs: rendered_html.append(html)):
            render_phone_clearance_card(
                phone_detected=False,
            )

        self.assertEqual(len(rendered_html), 1)
        content = rendered_html[0]
        self.assertIn("DEVICE INTEGRITY REPORT: ZERO MOBILE PHONES DETECTED (CLEAN)", content)
        self.assertIn("DEVICE CLEARANCE APPROVED 🟢", content)
        self.assertIn("Continuous computer vision proctoring verified", content)

    def test_worker_notifies_and_resets_phone_detection(self):
        """7. ProctoringWorker correctly updates internal flags and resets on command."""
        worker = ProctoringWorker(device_idx=99, enable_yolo=False)
        self.assertFalse(worker._phone_detected_sim)
        self.assertEqual(worker._phone_detected_count, 0)

        worker.set_session_info(exam_session_id=self.test_session_id, student_id=self.test_student_id)
        self.assertEqual(worker.active_session_id, self.test_session_id)

        worker.notify_phone_detected(confidence=0.95)
        self.assertTrue(worker._phone_detected_sim)
        self.assertEqual(worker._phone_detected_count, 1)

        worker.reset_phone_detection()
        self.assertFalse(worker._phone_detected_sim)
        self.assertEqual(worker._phone_detected_count, 0)

    def test_timeline_records_phone_violation_and_escalates_summary(self):
        """8. BehavioralTimeline get_session_summary escalates risk level when phone violation occurs."""
        timeline = BehavioralTimeline()
        timeline.start_session()
        timeline.add_event(
            module="YOLOv8ObjectDetector",
            event_type="MOBILE_PHONE_DETECTED",
            severity="HIGH",
            value=1.0,
            description="Mobile phone detected in proctoring camera feed.",
            risk_contribution=0.90,
        )

        summary = timeline.get_session_summary()
        self.assertEqual(summary["final_risk_level"], "HIGH")
        self.assertGreaterEqual(summary["peak_cheating_score"], 0.85)


if __name__ == "__main__":
    unittest.main()
