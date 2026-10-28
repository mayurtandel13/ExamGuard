"""
Phase 8: Behavioral Timeline Unit Tests & Simulated Event Verification
Verifies chronological event timeline, event attribute schema, CSV export,
session summary statistics, suspicious event counts, risk-level history, final cheating probability,
and Matplotlib visualization generation using simulated events.
"""

import unittest
import time
import os
import pandas as pd
from timeline.timeline import BehavioralTimeline
from timeline.visualizer import TimelineVisualizer
from fusion.engine import BehavioralFusionEngine


class TestBehavioralTimeline(unittest.TestCase):
    def setUp(self):
        self.timeline = BehavioralTimeline()
        self.engine = BehavioralFusionEngine(use_ema=False)
        self.timeline.start_session()

    def test_event_schema_attributes(self):
        """Verify every event contains timestamp, module, event type, severity, value, description, risk contribution."""
        evt = self.timeline.add_event(
            module="GazeTracker",
            event_type="GAZE_DISTRACTION",
            severity="MEDIUM",
            value=0.8,
            description="Eye gaze directed away from screen (GAZE_RIGHT)",
            risk_contribution=0.20,
        )

        self.assertIn("timestamp", evt)
        self.assertIn("timestamp_str", evt)
        self.assertEqual(evt["module"], "GazeTracker")
        self.assertEqual(evt["event_type"], "GAZE_DISTRACTION")
        self.assertEqual(evt["severity"], "MEDIUM")
        self.assertEqual(evt["value"], 0.8)
        self.assertEqual(evt["description"], "Eye gaze directed away from screen (GAZE_RIGHT)")
        self.assertEqual(evt["risk_contribution"], 0.20)

    def test_chronological_ordering(self):
        """Verify events are strictly stored and retrieved in chronological order."""
        t0 = time.time()
        self.timeline.add_event("KeyboardMonitor", "SUSPICIOUS_SHORTCUT", "MEDIUM", 0.5, "Alt+Tab", 0.15, timestamp=t0 + 5.0)
        self.timeline.add_event("GazeTracker", "GAZE_DISTRACTION", "LOW", 0.3, "Look away", 0.05, timestamp=t0 + 1.0)
        self.timeline.add_event("YOLOObjectDetector", "MOBILE_PHONE_DETECTED", "HIGH", 0.9, "Phone detected", 0.40, timestamp=t0 + 3.0)

        events = self.timeline.get_events()
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0]["module"], "GazeTracker")
        self.assertEqual(events[1]["module"], "YOLOObjectDetector")
        self.assertEqual(events[2]["module"], "KeyboardMonitor")

    def test_simulated_session_lifecycle(self):
        """Test full session with simulated multi-modal events across time."""
        t_base = time.time() - 60.0

        # Frame 1: Normal behavior
        res1 = self.engine.compute_fusion_score(
            {"deviation_score": 0.0},
            {"attention_score": 1.0},
            {"phone_detected": False, "person_count": 1},
            {"keyboard_penalty": 0.0},
        )
        self.timeline.record_snapshot({}, {"attention_score": 1.0}, {"phone_detected": False}, {}, res1, timestamp=t_base + 0.0)

        # Frame 2: Gaze distraction (t + 15s)
        res2 = self.engine.compute_fusion_score(
            {"deviation_score": 0.0},
            {"attention_score": 0.2, "gaze_state": "GAZE_RIGHT"},
            {"phone_detected": False, "person_count": 1},
            {"keyboard_penalty": 0.0},
        )
        self.timeline.record_snapshot({}, {"attention_score": 0.2, "gaze_state": "GAZE_RIGHT"}, {"phone_detected": False}, {}, res2, timestamp=t_base + 15.0)

        # Frame 3: Alt+Tab shortcut pressed (t + 30s)
        res3 = self.engine.compute_fusion_score(
            {"deviation_score": 0.0},
            {"attention_score": 1.0},
            {"phone_detected": False, "person_count": 1},
            {"keyboard_penalty": 0.6, "recent_events": [{"shortcut": "alt+tab"}]},
        )
        self.timeline.record_snapshot({}, {"attention_score": 1.0}, {"phone_detected": False}, {"keyboard_penalty": 0.6, "recent_events": [{"shortcut": "alt+tab"}]}, res3, timestamp=t_base + 30.0)

        # Frame 4: Mobile phone detected (t + 45s) -> HIGH risk spike
        res4 = self.engine.compute_fusion_score(
            {"deviation_score": 0.8, "status": "LOOKING_RIGHT"},
            {"attention_score": 0.1, "gaze_state": "GAZE_RIGHT"},
            {"phone_detected": True, "phone_confidence": 0.95, "person_count": 1},
            {"keyboard_penalty": 0.8, "recent_events": [{"shortcut": "alt+tab"}]},
        )
        self.timeline.record_snapshot(
            {"deviation_score": 0.8, "status": "LOOKING_RIGHT"},
            {"attention_score": 0.1, "gaze_state": "GAZE_RIGHT"},
            {"phone_detected": True, "phone_confidence": 0.95, "person_count": 1},
            {"keyboard_penalty": 0.8, "recent_events": [{"shortcut": "alt+tab"}]},
            res4,
            timestamp=t_base + 45.0,
        )

        # 1. Test Risk History
        df_risk = self.timeline.get_risk_history_df()
        self.assertEqual(len(df_risk), 4)

        # 2. Test Final Cheating Probability
        final_prob = self.timeline.get_final_cheating_probability()
        self.assertEqual(final_prob, 1.0)

        # 3. Test Suspicious Event Count
        susp_count = self.timeline.get_suspicious_event_count(min_severity="MEDIUM")
        self.assertGreaterEqual(susp_count, 3)

        # 4. Test Session Summary
        summary = self.timeline.get_session_summary()
        self.assertEqual(summary["duration_sec"], 45.0)
        self.assertEqual(summary["final_cheating_probability"], 1.0)
        self.assertEqual(summary["final_risk_level"], "HIGH")
        self.assertIn("LOW", summary["risk_distribution"])
        self.assertIn("HIGH", summary["risk_distribution"])

        # 5. Test CSV Export
        events_csv, risk_csv = self.timeline.export_to_csv()
        self.assertIn("event_type", events_csv)
        self.assertIn("cheating_probability", risk_csv)

    def test_matplotlib_visualization_generation(self):
        """Verify Matplotlib charts generate cleanly without errors."""
        t_base = time.time() - 30.0

        for i in range(5):
            t_curr = t_base + i * 5.0
            res = self.engine.compute_fusion_score(
                {"deviation_score": 0.1 * i},
                {"attention_score": 1.0 - 0.15 * i},
                {"phone_detected": (i >= 3), "person_count": 1},
                {"keyboard_penalty": 0.0},
            )
            self.timeline.record_snapshot(
                {"deviation_score": 0.1 * i},
                {"attention_score": 1.0 - 0.15 * i},
                {"phone_detected": (i >= 3)},
                {},
                res,
                timestamp=t_curr,
            )

        # Test single timeline chart
        fig_timeline = TimelineVisualizer.generate_timeline_chart(self.timeline)
        self.assertIsNotNone(fig_timeline)

        # Test signal breakdown chart
        fig_signals = TimelineVisualizer.generate_signal_breakdown_chart(self.timeline)
        self.assertIsNotNone(fig_signals)

        # Test pie chart
        summary = self.timeline.get_session_summary()
        fig_pie = TimelineVisualizer.generate_pie_chart(summary["risk_distribution"])
        self.assertIsNotNone(fig_pie)

        # Test full 3-panel dashboard figure
        fig_dash = TimelineVisualizer.generate_full_dashboard(self.timeline)
        self.assertIsNotNone(fig_dash)

        # Save dashboard to temp PNG file and check existence
        test_img_path = os.path.join("logs", "test_timeline_dashboard.png")
        TimelineVisualizer.save_visualization(fig_dash, test_img_path)
        self.assertTrue(os.path.exists(test_img_path))


if __name__ == "__main__":
    unittest.main()
