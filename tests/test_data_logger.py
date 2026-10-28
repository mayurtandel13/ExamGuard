"""
Unit Test for Session Data Logger
"""

import unittest
from modules.data_logger import SessionDataLogger


class TestSessionDataLogger(unittest.TestCase):
    def setUp(self):
        self.logger = SessionDataLogger()
        self.logger.start_session()

    def test_log_frame_and_df_export(self):
        head_tel = {"status": "FORWARD", "yaw": 2.1, "pitch": -1.0}
        gaze_tel = {"gaze_state": "CENTER"}
        yolo_tel = {"phone_detected": False, "person_count": 1}
        shortcuts = []
        fusion_res = {
            "cheating_probability_score": 0.12,
            "instantaneous_score": 0.10,
            "risk_level": "LOW",
            "active_events": [],
        }

        self.logger.log_frame(head_tel, gaze_tel, yolo_tel, shortcuts, fusion_res)

        df_ts = self.logger.get_timeseries_df()
        self.assertEqual(len(df_ts), 1)
        self.assertEqual(df_ts.iloc[0]["risk_level"], "LOW")

        summary = self.logger.get_session_summary()
        self.assertEqual(summary["final_risk_level"], "LOW")
        self.assertEqual(summary["total_events"], 0)


if __name__ == "__main__":
    unittest.main()
