"""
Phase 7: Behavioral Fusion Engine Unit Tests & Controlled Scenarios
Verifies research-paper formulation, input normalization, score clamping,
configurable weights/thresholds, timestamping, event logging, and logical score progression across controlled scenarios.
"""

import unittest
import time
from fusion.engine import BehavioralFusionEngine


class TestBehavioralFusionScenarios(unittest.TestCase):
    def setUp(self):
        # Create non-EMA engine for exact single-step formula validation
        self.engine_instant = BehavioralFusionEngine(
            w1_attention=0.25,
            w2_head=0.25,
            w3_keypress=0.25,
            w4_object=0.40,
            low_threshold=0.35,
            medium_threshold=0.70,
            use_ema=False,
        )
        # Create EMA engine for continuous risk progression testing
        self.engine_ema = BehavioralFusionEngine(
            w1_attention=0.25,
            w2_head=0.25,
            w3_keypress=0.25,
            w4_object=0.40,
            low_threshold=0.35,
            medium_threshold=0.70,
            use_ema=True,
        )

    def test_scenario_a_normal_behavior(self):
        """Scenario A: Normal behavior (high attention, centered head, no shortcuts, no phone, 1 person)."""
        head_tel = {"deviation_score": 0.0, "status": "FORWARD"}
        gaze_tel = {"attention_score": 1.0, "gaze_state": "CENTER"}
        yolo_tel = {"phone_detected": False, "person_count": 1, "multi_person_detected": False}
        kb_tel = {"keyboard_penalty": 0.0, "recent_events": []}

        res = self.engine_instant.compute_fusion_score(head_tel, gaze_tel, yolo_tel, kb_tel)

        self.assertEqual(res["risk_level"], "LOW")
        self.assertEqual(res["cheating_probability"], 0.0)
        self.assertEqual(res["signals"]["attention_penalty"], 0.0)
        self.assertEqual(res["signals"]["head_penalty"], 0.0)
        self.assertEqual(res["signals"]["keypress_penalty"], 0.0)
        self.assertEqual(res["signals"]["object_flag"], 0.0)
        self.assertEqual(len(res["contributing_events"]), 0)

    def test_scenario_b_frequent_gaze_away(self):
        """Scenario B: Frequent gaze away (Attention score drops to 0.2)."""
        head_tel = {"deviation_score": 0.0, "status": "FORWARD"}
        gaze_tel = {"attention_score": 0.2, "gaze_state": "GAZE_RIGHT"}
        yolo_tel = {"phone_detected": False, "person_count": 1}
        kb_tel = {"keyboard_penalty": 0.0, "recent_events": []}

        res = self.engine_instant.compute_fusion_score(head_tel, gaze_tel, yolo_tel, kb_tel)

        # Formula: 0.25 * (1 - 0.2) = 0.20
        self.assertAlmostEqual(res["cheating_probability"], 0.20, places=2)
        self.assertEqual(res["risk_level"], "LOW")
        self.assertEqual(res["signals"]["attention_penalty"], 0.8)
        self.assertTrue(any(e["type"] == "GAZE_DISTRACTION" for e in res["contributing_events"]))

    def test_scenario_c_repeated_head_movement(self):
        """Scenario C: Repeated head movement (Head pose deviation penalty 0.8)."""
        head_tel = {"deviation_score": 0.8, "status": "LOOKING_LEFT", "repeated_movement_detected": True}
        gaze_tel = {"attention_score": 1.0, "gaze_state": "CENTER"}
        yolo_tel = {"phone_detected": False, "person_count": 1}
        kb_tel = {"keyboard_penalty": 0.0, "recent_events": []}

        res = self.engine_instant.compute_fusion_score(head_tel, gaze_tel, yolo_tel, kb_tel)

        # Formula: 0.25 * 0.8 = 0.20
        self.assertAlmostEqual(res["cheating_probability"], 0.20, places=2)
        self.assertEqual(res["signals"]["head_penalty"], 0.8)
        self.assertTrue(any(e["type"] == "HEAD_POSE_DEVIATION" for e in res["contributing_events"]))

    def test_scenario_d_alt_tab(self):
        """Scenario D: Keypress penalty (Alt+Tab triggered, keypress penalty = 0.6)."""
        head_tel = {"deviation_score": 0.0, "status": "FORWARD"}
        gaze_tel = {"attention_score": 1.0, "gaze_state": "CENTER"}
        yolo_tel = {"phone_detected": False, "person_count": 1}
        kb_tel = {"keyboard_penalty": 0.6, "recent_events": [{"shortcut": "alt+tab", "timestamp": time.time()}]}

        res = self.engine_instant.compute_fusion_score(head_tel, gaze_tel, yolo_tel, kb_tel)

        # Formula: 0.25 * 0.6 = 0.15
        self.assertAlmostEqual(res["cheating_probability"], 0.15, places=2)
        self.assertEqual(res["signals"]["keypress_penalty"], 0.6)
        self.assertTrue(any(e["type"] == "SUSPICIOUS_SHORTCUT" for e in res["contributing_events"]))

    def test_scenario_e_phone_detected(self):
        """Scenario E: Mobile phone detected (Object flag = 1.0)."""
        head_tel = {"deviation_score": 0.0, "status": "FORWARD"}
        gaze_tel = {"attention_score": 1.0, "gaze_state": "CENTER"}
        yolo_tel = {"phone_detected": True, "phone_confidence": 0.92, "person_count": 1}
        kb_tel = {"keyboard_penalty": 0.0, "recent_events": []}

        res = self.engine_instant.compute_fusion_score(head_tel, gaze_tel, yolo_tel, kb_tel)

        # Formula: 0.40 * 1.0 = 0.40
        self.assertAlmostEqual(res["cheating_probability"], 0.40, places=2)
        self.assertEqual(res["risk_level"], "MEDIUM")
        self.assertEqual(res["signals"]["object_flag"], 1.0)
        self.assertTrue(any(e["type"] == "MOBILE_PHONE_DETECTED" for e in res["contributing_events"]))

    def test_scenario_f_multiple_people(self):
        """Scenario F: Multiple people detected (person_count = 2, Object flag = 1.0)."""
        head_tel = {"deviation_score": 0.0, "status": "FORWARD"}
        gaze_tel = {"attention_score": 1.0, "gaze_state": "CENTER"}
        yolo_tel = {"phone_detected": False, "person_count": 2, "multi_person_detected": True}
        kb_tel = {"keyboard_penalty": 0.0, "recent_events": []}

        res = self.engine_instant.compute_fusion_score(head_tel, gaze_tel, yolo_tel, kb_tel)

        # Formula: 0.40 * 1.0 = 0.40
        self.assertAlmostEqual(res["cheating_probability"], 0.40, places=2)
        self.assertEqual(res["risk_level"], "MEDIUM")
        self.assertEqual(res["signals"]["object_flag"], 1.0)
        self.assertTrue(any(e["type"] == "MULTIPLE_PERSONS_DETECTED" for e in res["contributing_events"]))

    def test_scenario_g_multiple_suspicious_signals(self):
        """Scenario G: Multiple suspicious signals simultaneously (Gaze away + Head pose + Alt+Tab + Phone)."""
        head_tel = {"deviation_score": 0.8, "status": "LOOKING_RIGHT", "repeated_movement_detected": True}
        gaze_tel = {"attention_score": 0.0, "gaze_state": "GAZE_RIGHT"}
        yolo_tel = {"phone_detected": True, "phone_confidence": 0.95, "person_count": 1}
        kb_tel = {"keyboard_penalty": 0.8, "recent_events": [{"shortcut": "alt+tab"}]}

        res = self.engine_instant.compute_fusion_score(head_tel, gaze_tel, yolo_tel, kb_tel)

        # Formula: 0.25*(1-0) + 0.25*0.8 + 0.25*0.8 + 0.40*1.0 = 0.25 + 0.20 + 0.20 + 0.40 = 1.05 -> clamped to 1.0
        self.assertEqual(res["cheating_probability"], 1.0)
        self.assertEqual(res["risk_level"], "HIGH")
        self.assertGreaterEqual(len(res["contributing_events"]), 4)

    def test_logical_score_progression_across_scenarios(self):
        """Verify that score changes logically between scenarios (e.g. Normal < Distraction < Multi-Signal)."""
        res_a = self._run_scenario("A")
        res_b = self._run_scenario("B")
        res_e = self._run_scenario("E")
        res_g = self._run_scenario("G")

        self.assertLess(res_a["cheating_probability"], res_b["cheating_probability"])
        self.assertLess(res_b["cheating_probability"], res_g["cheating_probability"])
        self.assertLess(res_e["cheating_probability"], res_g["cheating_probability"])

    def _run_scenario(self, scenario_letter):
        if scenario_letter == "A":
            head = {"deviation_score": 0.0}
            gaze = {"attention_score": 1.0}
            yolo = {"phone_detected": False, "person_count": 1}
            kb = {"keyboard_penalty": 0.0}
        elif scenario_letter == "B":
            head = {"deviation_score": 0.0}
            gaze = {"attention_score": 0.3}
            yolo = {"phone_detected": False, "person_count": 1}
            kb = {"keyboard_penalty": 0.0}
        elif scenario_letter == "E":
            head = {"deviation_score": 0.0}
            gaze = {"attention_score": 1.0}
            yolo = {"phone_detected": True, "person_count": 1}
            kb = {"keyboard_penalty": 0.0}
        elif scenario_letter == "G":
            head = {"deviation_score": 0.9}
            gaze = {"attention_score": 0.1}
            yolo = {"phone_detected": True, "person_count": 2}
            kb = {"keyboard_penalty": 0.9}
        else:
            raise ValueError("Unknown scenario")

        return self.engine_instant.compute_fusion_score(head, gaze, yolo, kb)

    def test_configurable_weights(self):
        """Verify configurable weights customize score calculation."""
        custom_engine = BehavioralFusionEngine(
            w1_attention=0.50,
            w2_head=0.10,
            w3_keypress=0.10,
            w4_object=0.30,
            use_ema=False,
        )

        gaze_tel = {"attention_score": 0.0}  # penalty = 1.0
        res = custom_engine.compute_fusion_score({}, gaze_tel, {}, {})

        # Formula: 0.50 * 1.0 = 0.50
        self.assertEqual(res["cheating_probability"], 0.50)

    def test_configurable_risk_thresholds(self):
        """Verify configurable risk thresholds trigger LOW, MEDIUM, and HIGH correctly."""
        strict_engine = BehavioralFusionEngine(
            w1_attention=0.25,
            w2_head=0.25,
            w3_keypress=0.25,
            w4_object=0.40,
            low_threshold=0.15,
            medium_threshold=0.40,
            use_ema=False,
        )

        # Attention score 0.2 -> (1 - 0.2) = 0.8 -> 0.25 * 0.8 = 0.20
        gaze_tel = {"attention_score": 0.2}
        res = strict_engine.compute_fusion_score({}, gaze_tel, {}, {})

        self.assertEqual(res["cheating_probability"], 0.20)
        self.assertEqual(res["risk_level"], "MEDIUM")

    def test_input_normalization_and_clamping(self):
        """Verify out-of-range signal values are normalized and clamped into [0.0, 1.0]."""
        gaze_tel = {"attention_score": -2.0}  # clamped att_score=0.0 -> penalty=1.0
        head_tel = {"deviation_score": 5.0}   # clamped to 1.0
        kb_tel = {"keyboard_penalty": 10.0}    # clamped to 1.0
        yolo_tel = {"phone_detected": True}    # flag = 1.0

        res = self.engine_instant.compute_fusion_score(head_tel, gaze_tel, yolo_tel, kb_tel)

        self.assertLessEqual(res["cheating_probability"], 1.0)
        self.assertGreaterEqual(res["cheating_probability"], 0.0)
        self.assertEqual(res["signals"]["attention_penalty"], 1.0)
        self.assertEqual(res["signals"]["head_penalty"], 1.0)
        self.assertEqual(res["signals"]["keypress_penalty"], 1.0)
        self.assertEqual(res["signals"]["object_flag"], 1.0)

    def test_timestamp_recording(self):
        """Verify every risk update contains an accurate timestamp."""
        t_before = time.time()
        res = self.engine_instant.compute_fusion_score({}, {}, {}, {})
        t_after = time.time()

        self.assertIn("timestamp", res)
        self.assertGreaterEqual(res["timestamp"], t_before)
        self.assertLessEqual(res["timestamp"], t_after)


if __name__ == "__main__":
    unittest.main()
