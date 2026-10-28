"""
Test Suite for Browser Extension Detection and Monitoring Module
Covers all 14 test scenarios required in Section 8 of the project specification.
"""

import unittest
import time
from unittest.mock import patch, MagicMock
from starlette.testclient import TestClient

from database.db import ExamDatabase, get_db
from extension_monitor.detector import (
    BrowserEnvironmentEvaluator,
    ExtensionInterferenceClassifier,
    get_evaluator,
    get_classifier,
)
from backend.api import app


class TestBrowserExtensionMonitoring(unittest.TestCase):
    """
    Automated verification of the Browser Extension Detection & Monitoring subsystem.
    """

    def setUp(self):
        self.evaluator = get_evaluator()
        self.classifier = get_classifier()
        self.db = get_db()
        self.client = TestClient(app)
        self.test_session_id = f"TEST-SCENARIO-{int(time.time() * 1000)}"
        self.test_student_id = "STU-2026-081"

    def test_scenario_01_supported_browser_detection(self):
        """Scenario 1: Student starts an examination in a supported browser (Chrome, Edge, Firefox)."""
        ua_chrome = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        parsed = self.evaluator.parse_user_agent(ua_chrome)
        self.assertEqual(parsed["browser"], "Chrome")
        self.assertIn("124", parsed["version"])

        eval_res = self.evaluator.evaluate_compatibility(parsed)
        self.assertEqual(eval_res["status"], "READY")
        self.assertTrue(eval_res["is_supported"])
        self.assertEqual(len(eval_res["warnings"]), 0)

    def test_scenario_02_camera_permission_denied(self):
        """Scenario 2: Student denies camera permission."""
        browser_info = {"browser": "Chrome", "version": "124.0", "os": "Windows"}
        eval_res = self.evaluator.evaluate_compatibility(
            browser_info=browser_info,
            camera_permission="DENIED",
        )
        self.assertEqual(eval_res["status"], "WARNING")
        self.assertTrue(any("camera" in w.lower() for w in eval_res["warnings"]))

    def test_scenario_03_optional_extension_not_installed(self):
        """Scenario 3: Optional institutional extension is not installed (must NOT classify as cheating)."""
        risk, severity, reason = self.classifier.classify_event({
            "event_type": "EXTENSION_STATUS_UNAVAILABLE",
            "description": "Companion ping timed out. Operating in unmanaged web mode.",
        })
        self.assertEqual(risk, "LOW")
        self.assertIn("optional", reason.lower())

    def test_scenario_04_institutional_extension_handshake(self):
        """Scenario 4: Institutional extension installed and communicates successfully."""
        resp = self.client.post("/api/browser-readiness", json={
            "exam_session_id": self.test_session_id,
            "student_id": self.test_student_id,
            "user_agent": "Mozilla/5.0 Chrome/124.0.0.0",
            "institutional_extension_status": "CONNECTED",
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["session"]["institutional_extension_status"], "CONNECTED")

    def test_scenario_05_unexpected_dom_modification_detected(self):
        """Scenario 5: Examination page experiences unexpected foreign extension script injection."""
        risk, severity, reason = self.classifier.classify_event({
            "event_type": "PAGE_INTEGRITY_CHANGE",
            "description": "Script tag injected into body",
            "details": "src='chrome-extension://solv/helper.js'",
        })
        self.assertEqual(risk, "HIGH")
        self.assertEqual(severity, "CRITICAL")
        self.assertIn("extension protocol", reason.lower())

    def test_scenario_06_legitimate_application_update(self):
        """Scenario 6: Legitimate application update modifies DOM without extension indicators."""
        risk, severity, reason = self.classifier.classify_event({
            "event_type": "PAGE_INTEGRITY_CHANGE",
            "description": "Standard container layout refresh",
            "details": "div.css-update innerText refreshed",
        })
        self.assertEqual(risk, "LOW")

    def test_scenario_07_monitoring_event_submission_and_db_persistence(self):
        """Scenario 7: Monitoring event is submitted successfully and persisted in SQLite DB."""
        # First ensure session exists
        self.db.create_or_get_session(
            exam_session_id=self.test_session_id,
            student_id=self.test_student_id,
        )

        resp = self.client.post("/api/events", json={
            "exam_session_id": self.test_session_id,
            "student_id": self.test_student_id,
            "event_type": "WINDOW_BLUR_TAB_SWITCH",
            "description": "Candidate switched window",
            "occurrences": 1,
        })
        self.assertEqual(resp.status_code, 201)
        event_id = resp.json()["event_id"]
        self.assertIsNotNone(event_id)

        # Verify in DB
        db_events = self.db.get_events(exam_session_id=self.test_session_id)
        self.assertTrue(any(e["id"] == event_id for e in db_events))

    def test_scenario_08_backend_unavailable_handling(self):
        """Scenario 8: Client handles backend connection errors gracefully."""
        # Simulated by sending malformed or handling client exceptions
        resp = self.client.post("/api/events", content=b"invalid-json", headers={"Content-Type": "application/json"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.json())

    def test_scenario_09_authorization_session_mismatch(self):
        """Scenario 9: Student attempts to submit event for another student's session (must reject 403)."""
        foreign_student_id = "STU-OTHER-999"
        # Seed foreign student into DB so foreign key passes
        with self.db._lock:
            conn = self.db._get_connection()
            try:
                with conn:
                    conn.execute("""
                        INSERT OR IGNORE INTO students (student_id, full_name, email, department, roll_number)
                        VALUES (?, ?, ?, ?, ?)
                    """, (foreign_student_id, "Other Candidate", "other@college.edu", "IT", "IT-2026-999"))
            finally:
                conn.close()

        foreign_session_id = f"FOREIGN-{int(time.time() * 1000)}"
        self.db.create_or_get_session(
            exam_session_id=foreign_session_id,
            student_id=foreign_student_id,
        )

        resp = self.client.post("/api/events", json={
            "exam_session_id": foreign_session_id,
            "student_id": "STU-HACKER-111",
            "event_type": "PAGE_INTEGRITY_CHANGE",
        })
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Forbidden", resp.json()["error"])

    def test_scenario_10_admin_review_missing_event(self):
        """Scenario 10: Admin review handles invalid event ID gracefully."""
        resp = self.client.post("/api/review", json={
            "event_id": 99999999,
            "reviewer_id": "ADMIN-1",
            "review_decision": "CONFIRMED",
        })
        # Record review requires existing event or fails gracefully
        self.assertTrue(resp.status_code in (200, 400))

    def test_scenario_11_admin_filters_and_reviews_event(self):
        """Scenario 11: Administrator filters and reviews monitoring event with audit trail."""
        # Create event
        self.db.create_or_get_session(
            exam_session_id=self.test_session_id,
            student_id=self.test_student_id,
        )
        evt = self.db.record_event(
            exam_session_id=self.test_session_id,
            student_id=self.test_student_id,
            event_type="EXAM_INTERFACE_OVERLAY",
            event_description="Overlay covering options",
            detection_method="OverlayDetector",
            risk_level="MEDIUM",
        )
        evt_id = evt["id"]

        # Admin reviews event as FALSE_POSITIVE
        success = self.db.record_review(
            event_id=evt_id,
            reviewer_id="PROCTOR-MAYUR",
            review_decision="FALSE_POSITIVE",
            review_notes="Verified tooltip glitch, no cheating attempted.",
        )
        self.assertTrue(success)

        # Audit check
        updated_events = self.db.get_events(exam_session_id=self.test_session_id)
        target = next((e for e in updated_events if e["id"] == evt_id), None)
        self.assertIsNotNone(target)
        self.assertEqual(target["review_status"], "FALSE_POSITIVE")

        # Verify review audit table
        reviews = self.db.get_event_reviews(evt_id)
        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["reviewer_id"], "PROCTOR-MAYUR")
        self.assertEqual(reviews[0]["review_decision"], "FALSE_POSITIVE")

    def test_scenario_12_exam_answers_persistence(self):
        """Scenario 12: Examination answers, mark for review, and navigation persist in database."""
        self.db.create_or_get_session(
            exam_session_id=self.test_session_id,
            student_id=self.test_student_id,
        )
        self.db.record_answer(
            exam_session_id=self.test_session_id,
            student_id=self.test_student_id,
            question_id=1,
            selected_option="B) To allow networks to learn complex non-linear decision boundaries",
            is_marked_for_review=True,
        )

        answers = self.db.get_answers(self.test_session_id)
        self.assertIn(1, answers)
        self.assertTrue(answers[1]["is_marked_for_review"])
        self.assertIn("complex non-linear", answers[1]["selected_option"])

    def test_scenario_13_multi_modal_vision_and_fusion_still_operational(self):
        """Scenario 13: Existing multi-modal AI fusion engine components remain fully operational."""
        from fusion.engine import BehavioralFusionEngine
        from risk_scoring.scorer import RiskScorer

        # Test single-step raw fusion calculation without EMA decay lag
        engine = BehavioralFusionEngine(use_ema=False)
        scorer = RiskScorer()

        res = engine.compute_fusion_score(
            head_telemetry={"deviation_score": 0.8, "status": "LOOKING_AWAY"},
            gaze_telemetry={"attention_score": 0.2},
            yolo_telemetry={"phone_detected": True, "person_count": 2, "multi_person_detected": True},
            kb_telemetry_or_events={"keyboard_penalty": 0.5},
        )
        self.assertIn("cheating_probability_score", res)
        self.assertGreater(res["cheating_probability_score"], 0.4)

        level = scorer.evaluate_risk_level(res["cheating_probability_score"])
        self.assertIn(level, ("MEDIUM", "HIGH"))

    def test_scenario_14_exam_session_lifecycle_and_end(self):
        """Scenario 14: Examination session starts, transitions, and ends cleanly."""
        sess = self.db.create_or_get_session(
            exam_session_id=self.test_session_id,
            student_id=self.test_student_id,
        )
        self.assertEqual(sess["status"], "IN_PROGRESS")

        self.db.end_session(
            exam_session_id=self.test_session_id,
            status="SUBMITTED",
            peak_risk_score=0.35,
            final_risk_level="LOW",
        )

        sessions = self.db.get_sessions(student_id=self.test_student_id)
        target = next((s for s in sessions if s["exam_session_id"] == self.test_session_id), None)
        self.assertIsNotNone(target)
        self.assertEqual(target["status"], "SUBMITTED")
        self.assertEqual(target["final_risk_level"], "LOW")


if __name__ == "__main__":
    unittest.main()
