"""
Behavioral Fusion Engine Module (Phase 7)
Fuses multi-modal behavioral signals into a composite Cheating Probability Score and Risk Level.

Research-Paper Formulation:
Cheating Probability = w1 * (1 - Attention Score) + w2 * Head-Pose Penalty + w3 * Keypress Penalty + w4 * Object-Detection Flag

Disclaimer:
This engine performs heuristic behavioral risk estimation for proctoring assistance.
It is NOT a definitive cheating classifier.
No machine-learning model is trained or assumed for classification.
No empirical accuracy numbers are invented.
"""

import time
from config import FUSION_CONFIG


class BehavioralFusionEngine:
    """
    Modular Behavioral Fusion Engine implementing research paper weighting formulation
    with input normalization, score clamping, configurable weights/thresholds, and event tracking.
    """

    def __init__(
        self,
        w1_attention=None,
        w2_head=None,
        w3_keypress=None,
        w4_object=None,
        low_threshold=None,
        medium_threshold=None,
        ema_alpha=None,
        use_ema=True,
    ):
        """
        Initialize the Behavioral Fusion Engine with configurable weights and risk thresholds.
        """
        self.w1_attention = (
            w1_attention
            if w1_attention is not None
            else FUSION_CONFIG.get("WEIGHT_GAZE_DISTRACTION", 0.25)
        )
        self.w2_head = (
            w2_head
            if w2_head is not None
            else FUSION_CONFIG.get("WEIGHT_HEAD_POSE", 0.25)
        )
        self.w3_keypress = (
            w3_keypress
            if w3_keypress is not None
            else FUSION_CONFIG.get("WEIGHT_KEYBOARD_SHORTCUT", 0.25)
        )
        self.w4_object = (
            w4_object
            if w4_object is not None
            else FUSION_CONFIG.get("WEIGHT_MOBILE_PHONE", 0.40)
        )

        self.low_threshold = (
            low_threshold
            if low_threshold is not None
            else FUSION_CONFIG.get("RISK_THRESHOLD_LOW", 0.35)
        )
        self.medium_threshold = (
            medium_threshold
            if medium_threshold is not None
            else FUSION_CONFIG.get("RISK_THRESHOLD_MEDIUM", 0.70)
        )

        self.ema_alpha = (
            ema_alpha
            if ema_alpha is not None
            else FUSION_CONFIG.get("EMA_ALPHA", 0.30)
        )
        self.use_ema = use_ema

        # EMA State
        self.previous_cheating_score = 0.0

    def normalize_signal(self, value):
        """
        Normalizes and clamps an input signal value strictly into range [0.0, 1.0].
        """
        try:
            val = float(value)
            return max(0.0, min(1.0, val))
        except (TypeError, ValueError):
            return 0.0

    def compute_fusion_score(self, head_telemetry, gaze_telemetry, yolo_telemetry, kb_telemetry_or_events, tab_telemetry=None):
        """
        Calculates Cheating Probability Score and Risk Level from multi-modal inputs.
        
        Formula:
        Cheating Probability = w1 * (1 - Attention Score) + w2 * Head-Pose Penalty + w3 * Keypress Penalty + w4 * Object-Detection Flag
        Whenever tab switch / window blur occurs, the integrity risk escalates strictly to HIGH.

        Returns:
            dict containing timestamp, raw & smoothed scores, risk level, signal breakdown, and contributing events.
        """
        now = time.time()

        # Handle None inputs safely
        head_telemetry = head_telemetry or {}
        gaze_telemetry = gaze_telemetry or {}
        yolo_telemetry = yolo_telemetry or {}
        kb_telemetry_or_events = kb_telemetry_or_events or {}

        # 1. Attention Penalty: (1 - Attention Score)
        if "attention_score" in gaze_telemetry:
            att_score = self.normalize_signal(gaze_telemetry["attention_score"])
            p_attention = 1.0 - att_score
        elif "gaze_deviation_score" in gaze_telemetry:
            p_attention = self.normalize_signal(gaze_telemetry["gaze_deviation_score"])
        else:
            p_attention = 0.0
        p_attention = self.normalize_signal(p_attention)

        # 2. Head-Pose Penalty
        p_head = self.normalize_signal(head_telemetry.get("deviation_score", 0.0))

        # 3. Keypress Penalty
        if isinstance(kb_telemetry_or_events, dict):
            p_keypress = self.normalize_signal(kb_telemetry_or_events.get("keyboard_penalty", 0.0))
            kb_events = kb_telemetry_or_events.get("recent_events", [])
        elif isinstance(kb_telemetry_or_events, list):
            kb_events = kb_telemetry_or_events
            p_keypress = 1.0 if len(kb_events) > 0 else 0.0
        else:
            kb_events = []
            p_keypress = 0.0
        p_keypress = self.normalize_signal(p_keypress)

        # 4. Object-Detection Flag (Phone or Multi-Person)
        phone_det = bool(yolo_telemetry.get("phone_detected", False))
        person_count = int(yolo_telemetry.get("person_count", 0))
        multi_person_det = bool(yolo_telemetry.get("multi_person_detected", False)) or (person_count > 1)

        p_phone = 1.0 if phone_det else 0.0
        p_multi = 1.0 if multi_person_det else 0.0
        p_object = self.normalize_signal(max(p_phone, p_multi))

        # 5. Tab Switch Detection (Elevates risk strictly to HIGH)
        tab_detected = False
        tab_count = 0
        if isinstance(tab_telemetry, dict):
            tab_detected = bool(tab_telemetry.get("tab_switch_detected", False) or tab_telemetry.get("blur_detected", False) or tab_telemetry.get("count", 0) > 0)
            tab_count = int(tab_telemetry.get("count", 1 if tab_detected else 0))
        elif isinstance(tab_telemetry, (bool, int)):
            tab_detected = bool(tab_telemetry)
            tab_count = int(tab_telemetry) if isinstance(tab_telemetry, int) else 1
        elif isinstance(tab_telemetry, (list, tuple)):
            tab_detected = len(tab_telemetry) > 0
            tab_count = len(tab_telemetry)

        # Research Paper Formulation (Instantaneous Score)
        s_inst = (
            self.w1_attention * p_attention
            + self.w2_head * p_head
            + self.w3_keypress * p_keypress
            + self.w4_object * p_object
        )

        # Clamp instantaneous probability strictly to valid range [0.0, 1.0]
        s_inst = self.normalize_signal(s_inst)

        # If tab switch is detected, elevate instantaneous score to HIGH range
        if tab_detected:
            s_inst = max(s_inst, 0.85)

        # Apply continuous EMA smoothing if enabled
        if self.use_ema:
            # When active violation occurs (shortcut, object, or tab switch), use responsive alpha for immediate visual feedback
            effective_alpha = max(self.ema_alpha, 0.40) if (p_keypress > 0 or p_object > 0 or tab_detected) else self.ema_alpha
            s_cheat = (effective_alpha * s_inst) + ((1.0 - effective_alpha) * self.previous_cheating_score)
            s_cheat = self.normalize_signal(s_cheat)
            if tab_detected:
                s_cheat = max(s_cheat, 0.85)
            self.previous_cheating_score = s_cheat
        else:
            s_cheat = s_inst

        # Generate LOW/MEDIUM/HIGH Risk Level (Tab switch strictly elevates to HIGH)
        if tab_detected:
            risk_level = "HIGH"
        elif s_cheat < self.low_threshold:
            risk_level = "LOW"
        elif s_cheat < self.medium_threshold:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        # Record Contributing Events
        contributing_events = []

        if tab_detected:
            contributing_events.append({
                "type": "WINDOW_BLUR_TAB_SWITCH",
                "severity": "HIGH",
                "message": f"Candidate switched browser window or minimized examination tab ({tab_count} incident{'s' if tab_count > 1 else ''}). Tab detection risk elevated to HIGH.",
                "timestamp": now,
                "details": {"count": tab_count, "risk_level": "HIGH"},
            })

        if phone_det:
            conf = float(yolo_telemetry.get("phone_confidence", 0.0))
            contributing_events.append({
                "type": "MOBILE_PHONE_DETECTED",
                "severity": "HIGH",
                "message": f"Mobile phone detected in frame (Conf: {conf * 100:.1f}%)",
                "timestamp": now,
                "details": {"phone_confidence": conf},
            })

        if multi_person_det:
            contributing_events.append({
                "type": "MULTIPLE_PERSONS_DETECTED",
                "severity": "HIGH",
                "message": f"Multiple persons detected ({person_count} persons)",
                "timestamp": now,
                "details": {"person_count": person_count},
            })

        head_status = head_telemetry.get("status", "FORWARD")
        if head_status in ["LOOKING_LEFT", "LOOKING_RIGHT", "LOOKING_UP", "LOOKING_DOWN"] or head_telemetry.get("repeated_movement_detected", False):
            contributing_events.append({
                "type": "HEAD_POSE_DEVIATION",
                "severity": "MEDIUM",
                "message": f"Head turned off-center or repeated movement: {head_status}",
                "timestamp": now,
                "details": {"status": head_status, "pitch": head_telemetry.get("pitch", 0.0), "yaw": head_telemetry.get("yaw", 0.0)},
            })

        gaze_state = gaze_telemetry.get("gaze_state", "CENTER")
        if gaze_state in ["GAZE_LEFT", "GAZE_RIGHT"] or gaze_telemetry.get("sustained_distraction", False) or p_attention > 0.4:
            contributing_events.append({
                "type": "GAZE_DISTRACTION",
                "severity": "MEDIUM",
                "message": f"Eye gaze directed away from screen ({gaze_state})",
                "timestamp": now,
                "details": {"gaze_state": gaze_state, "attention_penalty": round(p_attention, 3)},
            })

        if kb_events:
            if isinstance(kb_events[0], dict):
                shortcut_names = ", ".join([e.get("shortcut", "Hotkey") for e in kb_events])
            else:
                shortcut_names = "Shortcut"
            contributing_events.append({
                "type": "SUSPICIOUS_SHORTCUT",
                "severity": "MEDIUM",
                "message": f"Forbidden key shortcut pressed: {shortcut_names}",
                "timestamp": now,
                "details": {"shortcuts": shortcut_names},
            })

        return {
            "timestamp": now,
            "instantaneous_score": round(float(s_inst), 3),
            "cheating_probability": round(float(s_cheat), 3),
            "cheating_probability_score": round(float(s_cheat), 3),
            "risk_level": risk_level,
            "weights": {
                "w1_attention": self.w1_attention,
                "w2_head": self.w2_head,
                "w3_keypress": self.w3_keypress,
                "w4_object": self.w4_object,
            },
            "risk_thresholds": {
                "low_threshold": self.low_threshold,
                "medium_threshold": self.medium_threshold,
            },
            "signals": {
                "attention_penalty": round(float(p_attention), 3),
                "head_penalty": round(float(p_head), 3),
                "keypress_penalty": round(float(p_keypress), 3),
                "object_flag": round(float(p_object), 3),
                "tab_switch_penalty": 1.0 if tab_detected else 0.0,
            },
            "contributing_events": contributing_events,
            "active_events": contributing_events,
        }

    def reset(self):
        """Resets fusion state engine."""
        self.previous_cheating_score = 0.0



