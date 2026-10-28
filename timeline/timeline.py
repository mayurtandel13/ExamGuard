"""
Centralized Chronological Behavioral Timeline Engine (Phase 8)
Tracks frame risk snapshots, discrete behavioral events, risk-level history,
suspicious event counts, and exports post-exam summary metrics and CSV reports.
"""

import time
import datetime
import threading
import pandas as pd


class BehavioralTimeline:
    """
    Centralized Chronological Behavioral Event & Risk Timeline Manager.
    Records events with exact fields: timestamp, module, event_type, severity, value, description, risk_contribution.
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.session_start_time = None
        self.events = []
        self.risk_history = []
        self.event_counter = 0

    def start_session(self, start_time=None):
        """Initializes a new recording session."""
        with self.lock:
            self.session_start_time = start_time if start_time is not None else time.time()
            self.events = []
            self.risk_history = []
            self.event_counter = 0

    def _ensure_session(self):
        with self.lock:
            if self.session_start_time is None:
                self.session_start_time = time.time()

    def add_event(
        self,
        module,
        event_type,
        severity,
        value,
        description,
        risk_contribution,
        timestamp=None,
    ):
        """
        Adds a discrete behavioral event to the chronological timeline.

        Required fields:
        - timestamp: epoch timestamp (float) & formatted string
        - module: origin module string ('GazeTracker', 'HeadPoseEstimator', 'KeyboardMonitor', 'YOLOObjectDetector', 'FusionEngine')
        - event_type: category string ('GAZE_DISTRACTION', 'MOBILE_PHONE_DETECTED', etc.)
        - severity: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
        - value: numeric metric value
        - description: human-readable text explanation
        - risk_contribution: numeric risk score impact
        """
        self._ensure_session()

        now = timestamp if timestamp is not None else time.time()
        with self.lock:
            if self.session_start_time is None:
                self.session_start_time = now
            rel_time = round(now - self.session_start_time, 2)
            time_str = datetime.datetime.fromtimestamp(now).strftime("%H:%M:%S")

            self.event_counter += 1
            event_entry = {
                "event_id": self.event_counter,
                "timestamp": now,
                "rel_time_sec": rel_time,
                "timestamp_str": time_str,
                "module": str(module),
                "event_type": str(event_type),
                "severity": str(severity).upper(),
                "value": round(float(value), 3),
                "description": str(description),
                "risk_contribution": round(float(risk_contribution), 3),
            }

            self.events.append(event_entry)
            self.events.sort(key=lambda x: x["timestamp"])
            return event_entry

    def record_snapshot(
        self,
        head_telemetry=None,
        gaze_telemetry=None,
        yolo_telemetry=None,
        kb_telemetry_or_events=None,
        fusion_result=None,
        timestamp=None,
    ):
        """
        Records frame risk snapshot and automatically extracts contributing active events into the timeline.
        """
        now = timestamp if timestamp is not None else time.time()
        with self.lock:
            if self.session_start_time is None:
                self.session_start_time = now
            rel_time = round(now - self.session_start_time, 2)

        time_str = datetime.datetime.fromtimestamp(now).strftime("%H:%M:%S")

        head_tel = head_telemetry or {}
        gaze_tel = gaze_telemetry or {}
        yolo_tel = yolo_telemetry or {}
        fusion_res = fusion_result or {}

        # Keypress information
        if isinstance(kb_telemetry_or_events, dict):
            kb_events = kb_telemetry_or_events.get("recent_events", [])
            kb_penalty = kb_telemetry_or_events.get("keyboard_penalty", 0.0)
        elif isinstance(kb_telemetry_or_events, list):
            kb_events = kb_telemetry_or_events
            kb_penalty = 1.0 if len(kb_events) > 0 else 0.0
        else:
            kb_events = []
            kb_penalty = 0.0

        shortcut_str = ", ".join([e.get("shortcut", "Hotkey") for e in kb_events]) if kb_events else "None"

        cheat_prob = fusion_res.get("cheating_probability", fusion_res.get("cheating_probability_score", 0.0))
        inst_score = fusion_res.get("instantaneous_score", cheat_prob)
        risk_lvl = fusion_res.get("risk_level", "LOW")

        signals = fusion_res.get("signals", {})
        att_penalty = signals.get("attention_penalty", 1.0 - gaze_tel.get("attention_score", 1.0))
        head_penalty = signals.get("head_penalty", head_tel.get("deviation_score", 0.0))
        object_flag = signals.get("object_flag", 1.0 if yolo_tel.get("phone_detected") or yolo_tel.get("person_count", 0) > 1 else 0.0)

        weights = fusion_res.get("weights", {"w1_attention": 0.25, "w2_head": 0.25, "w3_keypress": 0.25, "w4_object": 0.40})

        snapshot = {
            "timestamp": now,
            "rel_time_sec": rel_time,
            "timestamp_str": time_str,
            "cheating_probability": round(float(cheat_prob), 3),
            "instantaneous_score": round(float(inst_score), 3),
            "risk_level": risk_lvl,
            "attention_penalty": round(float(att_penalty), 3),
            "head_penalty": round(float(head_penalty), 3),
            "keypress_penalty": round(float(kb_penalty), 3),
            "object_flag": round(float(object_flag), 3),
            "head_status": head_tel.get("status", "FORWARD"),
            "head_yaw": round(float(head_tel.get("yaw", 0.0)), 2),
            "head_pitch": round(float(head_tel.get("pitch", 0.0)), 2),
            "gaze_state": gaze_tel.get("gaze_state", "CENTER"),
            "phone_detected": bool(yolo_tel.get("phone_detected", False)),
            "person_count": int(yolo_tel.get("person_count", 0)),
            "active_shortcuts": shortcut_str,
        }

        with self.lock:
            self.risk_history.append(snapshot)
            self.risk_history.sort(key=lambda x: x["timestamp"])
            current_events_copy = list(self.events)

        # Extract and log active contributing events from fusion output
        for evt in fusion_res.get("contributing_events", fusion_res.get("active_events", [])):
            evt_type = evt.get("type", "SUSPICIOUS_BEHAVIOR")
            severity = evt.get("severity", "MEDIUM")
            desc = evt.get("message", "Suspicious behavior detected")

            # Determine origin module, trigger value, and risk contribution
            if evt_type == "MOBILE_PHONE_DETECTED":
                mod = "YOLOObjectDetector"
                val = yolo_tel.get("phone_confidence", 1.0)
                contrib = weights.get("w4_object", 0.40) * 1.0
            elif evt_type == "MULTIPLE_PERSONS_DETECTED":
                mod = "YOLOObjectDetector"
                val = yolo_tel.get("person_count", 2)
                contrib = weights.get("w4_object", 0.40) * 1.0
            elif evt_type in ["GAZE_DISTRACTION", "ATTENTION_DISTRACTION"]:
                mod = "GazeTracker"
                val = att_penalty
                contrib = weights.get("w1_attention", 0.25) * att_penalty
            elif evt_type in ["HEAD_POSE_DEVIATION", "REPEATED_HEAD_MOVEMENT"]:
                mod = "HeadPoseEstimator"
                val = head_penalty
                contrib = weights.get("w2_head", 0.25) * head_penalty
            elif evt_type == "SUSPICIOUS_SHORTCUT":
                mod = "KeyboardMonitor"
                val = kb_penalty
                contrib = weights.get("w3_keypress", 0.25) * kb_penalty
            elif evt_type == "WINDOW_BLUR_TAB_SWITCH":
                mod = "ScreenFocusMonitor"
                val = 1.0
                contrib = 0.85
            else:
                mod = "FusionEngine"
                val = cheat_prob
                contrib = cheat_prob

            # Avoid logging identical duplicate event within 1 second timestamp window
            is_dup = any(
                e["event_type"] == evt_type and abs(e["timestamp"] - now) < 1.0
                for e in current_events_copy
            )
            if not is_dup:
                self.add_event(
                    module=mod,
                    event_type=evt_type,
                    severity=severity,
                    value=val,
                    description=desc,
                    risk_contribution=contrib,
                    timestamp=now,
                )

        return snapshot

    def get_events(self, min_severity=None):
        """Returns events sorted chronologically, optionally filtered by minimum severity."""
        severity_order = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        with self.lock:
            evts = list(self.events)
        if min_severity is None:
            return evts

        min_rank = severity_order.get(str(min_severity).upper(), 1)
        return [
            e for e in evts
            if severity_order.get(e["severity"].upper(), 1) >= min_rank
        ]

    def get_events_df(self):
        """Returns DataFrame of all chronological events."""
        with self.lock:
            evts = list(self.events)
        if not evts:
            return pd.DataFrame(columns=[
                "event_id", "timestamp", "rel_time_sec", "timestamp_str",
                "module", "event_type", "severity", "value", "description", "risk_contribution"
            ])
        return pd.DataFrame(evts)

    def get_risk_history_df(self):
        """Returns DataFrame of frame-by-frame risk history snapshots."""
        with self.lock:
            rh = list(self.risk_history)
        if not rh:
            return pd.DataFrame(columns=[
                "timestamp", "rel_time_sec", "timestamp_str", "cheating_probability",
                "instantaneous_score", "risk_level", "attention_penalty",
                "head_penalty", "keypress_penalty", "object_flag",
                "head_status", "head_yaw", "head_pitch", "gaze_state",
                "phone_detected", "person_count", "active_shortcuts"
            ])
        return pd.DataFrame(rh)

    def get_suspicious_event_count(self, min_severity="MEDIUM"):
        """Returns total count of suspicious events at or above specified severity (default MEDIUM)."""
        return len(self.get_events(min_severity=min_severity))

    def get_final_cheating_probability(self):
        """Returns the final cheating probability score logged in the session."""
        with self.lock:
            if not self.risk_history:
                return 0.0
            return self.risk_history[-1]["cheating_probability"]

    def get_session_summary(self):
        """
        Computes centralized session summary metrics:
        - duration_sec
        - total_events
        - suspicious_event_count
        - avg_cheating_score
        - peak_cheating_score
        - final_cheating_probability
        - final_risk_level
        - risk_distribution
        - events_by_module
        - events_by_type
        """
        df_risk = self.get_risk_history_df()
        df_events = self.get_events_df()

        has_critical_violation = False
        with self.lock:
            has_critical_violation = any(
                e.get("event_type") in ["WINDOW_BLUR_TAB_SWITCH", "MOBILE_PHONE_DETECTED", "PHONE_DETECTED"]
                or ("tab" in str(e.get("event_type", "")).lower() and str(e.get("severity", "")).upper() in ["HIGH", "CRITICAL"])
                or ("phone" in str(e.get("event_type", "")).lower() and str(e.get("severity", "")).upper() in ["HIGH", "CRITICAL"])
                for e in self.events
            )

        if df_risk.empty:
            mod_counts = df_events["module"].value_counts().to_dict() if not df_events.empty else {}
            type_counts = df_events["event_type"].value_counts().to_dict() if not df_events.empty else {}
            return {
                "duration_sec": 0.0,
                "total_events": len(df_events),
                "suspicious_event_count": self.get_suspicious_event_count("MEDIUM"),
                "avg_cheating_score": 0.85 if has_critical_violation else 0.0,
                "peak_cheating_score": 0.85 if has_critical_violation else 0.0,
                "final_cheating_probability": 0.85 if has_critical_violation else 0.0,
                "final_risk_level": "HIGH" if has_critical_violation else "LOW",
                "risk_distribution": {"LOW": 0.0 if has_critical_violation else 100.0, "MEDIUM": 0.0, "HIGH": 100.0 if has_critical_violation else 0.0},
                "events_by_module": mod_counts,
                "events_by_type": type_counts,
            }

        duration = round(float(df_risk["rel_time_sec"].max() - df_risk["rel_time_sec"].min()), 1)
        avg_score = round(float(df_risk["cheating_probability"].mean()), 3)
        peak_score = round(float(df_risk["cheating_probability"].max()), 3)
        final_prob = round(float(df_risk["cheating_probability"].iloc[-1]), 3)

        # Risk distribution percentage breakdown
        risk_counts = df_risk["risk_level"].value_counts(normalize=True) * 100
        risk_dist = {
            "LOW": round(float(risk_counts.get("LOW", 0.0)), 1),
            "MEDIUM": round(float(risk_counts.get("MEDIUM", 0.0)), 1),
            "HIGH": round(float(risk_counts.get("HIGH", 0.0)), 1),
        }

        # Determine overall session final risk level based on peak, average, and final probability, plus critical violations (tab & phone)

        if has_critical_violation or peak_score >= 0.70 or avg_score >= 0.50 or final_prob >= 0.70:
            final_risk = "HIGH"
            if has_critical_violation:
                peak_score = max(peak_score, 0.85)
        elif peak_score >= 0.35 or avg_score >= 0.25 or final_prob >= 0.35:
            final_risk = "MEDIUM"
        else:
            final_risk = "LOW"

        mod_counts = df_events["module"].value_counts().to_dict() if not df_events.empty else {}
        type_counts = df_events["event_type"].value_counts().to_dict() if not df_events.empty else {}

        return {
            "duration_sec": duration,
            "total_events": len(df_events),
            "suspicious_event_count": self.get_suspicious_event_count("MEDIUM"),
            "avg_cheating_score": avg_score,
            "peak_cheating_score": peak_score,
            "final_cheating_probability": final_prob,
            "final_risk_level": final_risk,
            "risk_distribution": risk_dist,
            "events_by_module": mod_counts,
            "events_by_type": type_counts,
        }

    def export_to_csv(self, file_path_prefix=None):
        """
        Exports events and risk history to CSV string tuple (events_csv, risk_csv).
        Optionally saves to disk if file_path_prefix is provided.
        """
        df_events = self.get_events_df()
        df_risk = self.get_risk_history_df()

        events_csv = df_events.to_csv(index=False)
        risk_csv = df_risk.to_csv(index=False)

        if file_path_prefix:
            events_file = f"{file_path_prefix}_events.csv"
            risk_file = f"{file_path_prefix}_risk_history.csv"
            df_events.to_csv(events_file, index=False)
            df_risk.to_csv(risk_file, index=False)
            print(f"[BehavioralTimeline] Exported timeline data to '{events_file}' and '{risk_file}'")

        return events_csv, risk_csv
