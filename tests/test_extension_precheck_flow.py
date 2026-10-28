"""
Test Suite for Pre-Exam Browser Extension Checking, Warning, Faculty Alert, and Clearance Reporting.
Verifies the complete lifecycle:
1. Pre-exam environment evaluation flags active unauthorized browser extensions.
2. Rule-based classifier assigns HIGH risk to PRE_EXAM_EXTENSION_DETECTED and EXTENSION_DETECTED.
3. Beacon server endpoint /api/extension_event receives telemetry and logs event into SQLite DB.
4. Faculty dashboard summary and event logs record extension violations and metadata.
5. Post-submission clearance audit correctly flags that an extension was used during the session.
"""

import unittest
import time
import json
import urllib.request
from database.db import get_db
from extension_monitor.detector import get_evaluator, get_classifier
from extension_monitor.server import start_tab_beacon_server


class TestExtensionPrecheckFlow(unittest.TestCase):
    def setUp(self):
        self.db = get_db()
        self.evaluator = get_evaluator()
        self.classifier = get_classifier()
        self.test_session_id = f"TEST-EXT-{int(time.time() * 1000)}"
        self.test_student_id = "STU-2026-081"
        start_tab_beacon_server()

        # Seed test session
        self.db.create_or_get_session(
            exam_session_id=self.test_session_id,
            student_id=self.test_student_id,
        )

    def test_pre_exam_extension_evaluation_flag(self):
        """1. Evaluator flags active extension with FAIL in checklist and warning message."""
        browser_info = {"browser": "Chrome", "version": "124.0", "os": "Windows 11"}
        res = self.evaluator.evaluate_compatibility(
            browser_info=browser_info,
            unauthorized_extension_active=True,
            detected_extension_name="AI Exam Assistant & Solver",
        )
        self.assertEqual(res["status"], "WARNING")
        self.assertTrue(res["unauthorized_extension_active"])
        self.assertTrue(any("extension" in w.lower() for w in res["warnings"]))

        ext_item = next((item for item in res["checklist"] if "Extension" in item["item"]), None)
        self.assertIsNotNone(ext_item)
        self.assertEqual(ext_item["status"], "FAIL")
        self.assertIn("AI Exam Assistant", ext_item["detail"])

    def test_pre_exam_clean_evaluation(self):
        """2. Evaluator passes when no unauthorized extension is active."""
        browser_info = {"browser": "Chrome", "version": "124.0", "os": "Windows 11"}
        res = self.evaluator.evaluate_compatibility(
            browser_info=browser_info,
            unauthorized_extension_active=False,
        )
        ext_item = next((item for item in res["checklist"] if "Extension" in item["item"]), None)
        self.assertIsNotNone(ext_item)
        self.assertEqual(ext_item["status"], "PASS")

    def test_classifier_pre_exam_extension_detected(self):
        """3. Classifier classifies PRE_EXAM_EXTENSION_DETECTED as HIGH risk."""
        risk, severity, reason = self.classifier.classify_event({
            "event_type": "PRE_EXAM_EXTENSION_DETECTED",
            "extension_name": "Grammarly & Content Injector",
        })
        self.assertEqual(risk, "HIGH")
        self.assertIn("extension", reason.lower())

    def test_beacon_endpoint_logs_pre_exam_extension(self):
        """4. HTTP Beacon Server /api/extension_event persists event and forwards to faculty DB."""
        payload = json.dumps({
            "session_id": self.test_session_id,
            "student_id": self.test_student_id,
            "extension_name": "Tampermonkey Automation Script",
            "stage": "PRE_EXAM",
        }).encode("utf-8")

        req = urllib.request.Request(
            "http://127.0.0.1:8585/api/extension_event",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data.get("faculty_notified"))

        # Verify event was recorded in DB
        events = self.db.get_extension_events(exam_session_id=self.test_session_id)
        self.assertTrue(len(events) > 0)
        flagged = next((e for e in events if e["exam_session_id"] == self.test_session_id), None)
        self.assertIsNotNone(flagged)
        self.assertEqual(flagged["event_type"], "PRE_EXAM_EXTENSION_DETECTED")
        self.assertEqual(flagged["risk_level"], "HIGH")

    def test_faculty_summary_counts_extension_violations(self):
        """5. Faculty dashboard summary includes extension violations count."""
        summary = self.db.get_admin_summary()
        self.assertIn("extension_violations", summary)
        self.assertGreaterEqual(summary["extension_violations"], 1)

    def test_post_exam_clearance_determination(self):
        """6. Post-exam clearance correctly identifies extension was used vs clean clearance."""
        # Case A: When an extension was flagged
        self.db.record_event(
            exam_session_id=self.test_session_id,
            student_id=self.test_student_id,
            event_type="PRE_EXAM_EXTENSION_DETECTED",
            event_description="Pre-exam scan flagged active extension: AI Assistant. Warning served.",
            detection_method="PreExamExtensionScanner",
            risk_level="HIGH",
        )
        ext_events = self.db.get_extension_events(exam_session_id=self.test_session_id)
        extension_was_used = len(ext_events) > 0
        self.assertTrue(extension_was_used)

        # Case B: Clean session with zero extension events
        clean_session_id = f"CLEAN-{int(time.time() * 1000)}"
        self.db.create_or_get_session(exam_session_id=clean_session_id, student_id=self.test_student_id)
        clean_events = self.db.get_extension_events(exam_session_id=clean_session_id)
        self.assertEqual(len(clean_events), 0)

    def test_tab_switch_classification_high_risk(self):
        """7. Tab switch events are strictly classified with HIGH risk and HIGH severity."""
        risk, severity, reason = self.classifier.classify_event({
            "event_type": "WINDOW_BLUR_TAB_SWITCH",
            "occurrences": 1,
        })
        self.assertEqual(risk, "HIGH")
        self.assertEqual(severity, "HIGH")
        self.assertIn("tab", reason.lower())

    def test_tab_switch_beacon_records_high_risk(self):
        """8. Beacon server /api/tab_switch records tab switch event with HIGH risk in DB."""
        payload = json.dumps({
            "session_id": self.test_session_id,
            "student_id": self.test_student_id,
            "count": 1,
        }).encode("utf-8")

        req = urllib.request.Request(
            "http://127.0.0.1:8585/api/tab_switch",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)

        events = self.db.get_events(exam_session_id=self.test_session_id, event_type="WINDOW_BLUR_TAB_SWITCH")
        self.assertTrue(len(events) > 0)
        self.assertEqual(events[0]["risk_level"], "HIGH")
        self.assertEqual(events[0]["severity"], "HIGH")


if __name__ == "__main__":
    unittest.main()
