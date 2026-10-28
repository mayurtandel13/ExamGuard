"""
Tests for Tab Detection High-Risk Escalation
Verifies that whenever tab detection / window blur occurs:
1. Classifier strictly assigns HIGH risk and HIGH severity.
2. BehavioralFusionEngine elevates risk_level to HIGH and cheating_probability >= 0.85.
3. BehavioralTimeline.get_session_summary() marks final_risk_level as HIGH.
4. ProctoringWorker.notify_tab_switch() flags tab violation state.
5. Beacon server /api/tab_switch persists HIGH risk in database and returns HIGH status.
6. Client JS contains Tab Risk metric and HIGH risk warning handlers.
"""

import json
import time
import unittest
import urllib.request
from database.db import get_db
from extension_monitor.detector import get_classifier
from extension_monitor.client import get_integrity_client_js
from extension_monitor.server import start_tab_beacon_server
from fusion.engine import BehavioralFusionEngine
from timeline.timeline import BehavioralTimeline
from dashboard.worker import ProctoringWorker


class TestTabDetectionHighRisk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        start_tab_beacon_server(port=8585)
        time.sleep(0.1)

    def setUp(self):
        self.db = get_db()
        self.classifier = get_classifier()
        self.test_session_id = f"TEST-TAB-{int(time.time() * 1000)}"
        self.test_student_id = "STU-TAB-001"

        with self.db._lock:
            conn = self.db._get_connection()
            try:
                with conn:
                    conn.execute("""
                        INSERT OR IGNORE INTO students (student_id, full_name, email, department, roll_number)
                        VALUES (?, ?, ?, ?, ?)
                    """, (self.test_student_id, "Tab Candidate", "tab@test.edu", "CS", "TAB-001"))
            finally:
                conn.close()

        self.db.create_or_get_session(
            exam_session_id=self.test_session_id,
            student_id=self.test_student_id,
        )

    def test_classifier_strictly_assigns_high_risk_to_tab_detection(self):
        """1. Classifier strictly returns HIGH risk and HIGH severity on tab detection."""
        for event_type in ["WINDOW_BLUR_TAB_SWITCH", "TAB_SWITCH", "TAB_SWITCH_DETECTED", "WINDOW_BLUR"]:
            risk, sev, reason = self.classifier.classify_event({
                "event_type": event_type,
                "occurrences": 1,
            })
            self.assertEqual(risk, "HIGH", f"Failed for {event_type}")
            self.assertEqual(sev, "HIGH", f"Failed for {event_type}")
            self.assertIn("tab", reason.lower())

    def test_fusion_engine_elevates_to_high_risk_on_tab_detection(self):
        """2. Fusion engine escalates risk_level to HIGH and cheating score >= 0.85 on tab switch."""
        engine = BehavioralFusionEngine(use_ema=False)
        head_tel = {"deviation_score": 0.0, "status": "FORWARD"}
        gaze_tel = {"attention_score": 1.0, "gaze_state": "CENTER"}
        yolo_tel = {"phone_detected": False, "person_count": 1}
        kb_tel = {"keyboard_penalty": 0.0, "recent_events": []}

        # Baseline: normal behavior without tab switch -> LOW
        res_normal = engine.compute_fusion_score(head_tel, gaze_tel, yolo_tel, kb_tel)
        self.assertEqual(res_normal["risk_level"], "LOW")
        self.assertLess(res_normal["cheating_probability"], 0.35)

        # Tab switch occurrence -> escalates strictly to HIGH
        res_tab = engine.compute_fusion_score(
            head_tel, gaze_tel, yolo_tel, kb_tel,
            tab_telemetry={"tab_switch_detected": True, "count": 1}
        )
        self.assertEqual(res_tab["risk_level"], "HIGH")
        self.assertGreaterEqual(res_tab["cheating_probability"], 0.85)
        self.assertEqual(res_tab["signals"]["tab_switch_penalty"], 1.0)
        self.assertTrue(any(e["type"] == "WINDOW_BLUR_TAB_SWITCH" for e in res_tab["contributing_events"]))

    def test_timeline_session_summary_elevates_final_risk_to_high(self):
        """3. Timeline get_session_summary() computes final_risk_level as HIGH when tab switch occurred."""
        timeline = BehavioralTimeline()
        timeline.start_session()
        timeline.add_event(
            module="ScreenFocusMonitor",
            event_type="WINDOW_BLUR_TAB_SWITCH",
            severity="HIGH",
            value=1.0,
            description="Candidate switched browser window. Elevated to HIGH risk.",
            risk_contribution=0.85,
        )

        summary = timeline.get_session_summary()
        self.assertEqual(summary["final_risk_level"], "HIGH")
        self.assertGreaterEqual(summary["peak_cheating_score"], 0.85)

    def test_worker_notify_tab_switch_elevates_state(self):
        """4. ProctoringWorker notify_tab_switch() sets tab switch detection."""
        worker = ProctoringWorker(enable_yolo=False)
        self.assertFalse(worker._tab_switch_detected)
        self.assertEqual(worker._tab_switch_count, 0)

        worker.notify_tab_switch(count=2)
        self.assertTrue(worker._tab_switch_detected)
        self.assertEqual(worker._tab_switch_count, 2)

        worker.reset_tab_switch()
        self.assertFalse(worker._tab_switch_detected)
        self.assertEqual(worker._tab_switch_count, 0)

    def test_beacon_server_tab_switch_persists_high_risk(self):
        """5. Beacon server /api/tab_switch records HIGH risk in DB and returns HIGH status."""
        payload = json.dumps({
            "session_id": self.test_session_id,
            "student_id": self.test_student_id,
            "count": 1,
            "risk_level": "HIGH",
        }).encode("utf-8")

        req = urllib.request.Request(
            "http://127.0.0.1:8585/api/tab_switch",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data.get("risk_level"), "HIGH")

        events = self.db.get_events(exam_session_id=self.test_session_id, event_type="WINDOW_BLUR_TAB_SWITCH")
        self.assertTrue(len(events) > 0)
        self.assertEqual(events[0]["risk_level"], "HIGH")
        self.assertEqual(events[0]["severity"], "HIGH")

    def test_client_js_contains_tab_risk_metric(self):
        """6. Client-side JS component contains Tab Risk metric and HIGH risk handlers."""
        js_code = get_integrity_client_js(exam_session_id=self.test_session_id, student_id=self.test_student_id)
        self.assertIn("val-tab-risk", js_code)
        self.assertIn("Tab Risk:", js_code)
        self.assertIn("HIGH-RISK PROCTORING ALERT: Tab Switch Detected!", js_code)
        self.assertIn("Tab detection risk elevated to", js_code)


if __name__ == "__main__":
    unittest.main()
