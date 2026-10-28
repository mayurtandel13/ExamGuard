"""
Keyboard Monitoring Module using pynput.
Monitors Alt+Tab, Ctrl+C, Ctrl+V, Windows key, and Print Screen shortcuts.
Calculates event frequency, inter-event timing, and continuous keyboard penalty without asserting automatic cheating.
Robustly handles Windows low-level key variations (left/right modifiers, control characters, stuck keys, and auto-repeats).
Provides lifetime session tracking, key-by-key occurrence breakdown, and proctoring database integration.
"""

import os
import time
import datetime
import threading
from collections import deque
from typing import Dict, List, Any, Optional
from pynput import keyboard
from config import KEYBOARD_CONFIG

# Structured Shortcut Violation Taxonomy & Academic Metadata
SHORTCUT_METADATA = {
    "ctrl+c": {
        "display_name": "Ctrl + C",
        "action": "Copy to Clipboard",
        "violation_type": "Clipboard Extraction / Content Copying",
        "severity": "MEDIUM",
        "risk_level": "MEDIUM",
        "description": "Attempted to copy exam question text to clipboard for unauthorized external search",
    },
    "ctrl+v": {
        "display_name": "Ctrl + V",
        "action": "Paste from Clipboard",
        "violation_type": "Clipboard Injection / Content Pasting",
        "severity": "MEDIUM",
        "risk_level": "MEDIUM",
        "description": "Attempted to paste unauthorized external content or answers into the examination",
    },
    "ctrl+x": {
        "display_name": "Ctrl + X",
        "action": "Cut to Clipboard",
        "violation_type": "Clipboard Cut Attempt",
        "severity": "LOW",
        "risk_level": "LOW",
        "description": "Attempted to cut or modify question content",
    },
    "ctrl+a": {
        "display_name": "Ctrl + A",
        "action": "Select All",
        "violation_type": "Mass Content Selection",
        "severity": "LOW",
        "risk_level": "LOW",
        "description": "Attempted to select all text on examination interface for batch extraction",
    },
    "ctrl+w": {
        "display_name": "Ctrl + W",
        "action": "Close Tab",
        "violation_type": "Tab Termination Attempt",
        "severity": "MEDIUM",
        "risk_level": "MEDIUM",
        "description": "Attempted to close browser tab or navigate away",
    },
    "ctrl+t": {
        "display_name": "Ctrl + T",
        "action": "Open New Tab",
        "violation_type": "Secondary Tab Opening Attempt",
        "severity": "MEDIUM",
        "risk_level": "MEDIUM",
        "description": "Attempted to open new browser tab during active proctored examination",
    },
    "alt+tab": {
        "display_name": "Alt + Tab",
        "action": "Task / Window Switching",
        "violation_type": "External Application Navigation",
        "severity": "HIGH",
        "risk_level": "HIGH",
        "description": "Attempted to switch away from examination window to an external application or browser",
    },
    "print_screen": {
        "display_name": "Print Screen (PrtScn)",
        "action": "Screen Capture",
        "violation_type": "Exam Screen Capture / Question Leakage",
        "severity": "HIGH",
        "risk_level": "HIGH",
        "description": "Attempted to capture full-screen screenshot of confidential exam questions",
    },
    "win": {
        "display_name": "Windows Key",
        "action": "Start Menu / OS Navigation",
        "violation_type": "OS System Menu Access",
        "severity": "MEDIUM",
        "risk_level": "MEDIUM",
        "description": "Attempted to open Windows Start menu or access secondary local applications",
    },
    "win+tab": {
        "display_name": "Win + Tab",
        "action": "Task View / Virtual Desktops",
        "violation_type": "Virtual Desktop Switching",
        "severity": "HIGH",
        "risk_level": "HIGH",
        "description": "Attempted to access virtual desktops or switch active task views",
    },
    "win+v": {
        "display_name": "Win + V",
        "action": "Clipboard History Access",
        "violation_type": "Advanced Clipboard History Inspection",
        "severity": "HIGH",
        "risk_level": "HIGH",
        "description": "Attempted to access OS-level clipboard history to retrieve copied solutions",
    },
    "win+d": {
        "display_name": "Win + D",
        "action": "Show Desktop / Minimize",
        "violation_type": "Window Minimization",
        "severity": "MEDIUM",
        "risk_level": "MEDIUM",
        "description": "Attempted to minimize exam window and view local files or desktop",
    },
    "alt+f4": {
        "display_name": "Alt + F4",
        "action": "Close Window",
        "violation_type": "Forced Window Termination",
        "severity": "HIGH",
        "risk_level": "HIGH",
        "description": "Attempted to force close the examination window",
    },
    "f12": {
        "display_name": "F12 (DevTools)",
        "action": "Developer Tools Access",
        "violation_type": "DOM Inspection / Tampering",
        "severity": "HIGH",
        "risk_level": "HIGH",
        "description": "Attempted to open browser developer tools to inspect DOM or examine underlying scripts",
    },
    "devtools": {
        "display_name": "Ctrl + Shift + I (DevTools)",
        "action": "Developer Tools Access",
        "violation_type": "DOM Inspection / Script Injection",
        "severity": "HIGH",
        "risk_level": "HIGH",
        "description": "Attempted to inspect page elements or execute unauthorized console scripts",
    },
}


class KeyboardMonitor:
    """
    Decoupled Keyboard Listener Engine with thread-safe start/stop controls.
    Normalizes OS-specific key codes (e.g., Windows Ctrl+C ASCII \\x03, left/right modifiers).
    Tracks instantaneous active events, continuous risk penalties, lifetime session key counts,
    and structured audit summaries.
    """

    def __init__(
        self,
        decay_seconds=KEYBOARD_CONFIG["EVENT_DECAY_SECONDS"],
        base_penalty=0.2,
        rapid_trigger_window=2.0,
    ):
        self.decay_seconds = decay_seconds
        self.base_penalty = base_penalty
        self.rapid_trigger_window = rapid_trigger_window

        self.lock = threading.Lock()
        self.listener = None
        self.current_keys = set()
        self.key_timestamps = {}
        self.triggered_combos = set()
        self.is_running = False

        self.event_history = deque()
        self.last_event_time = None
        self.total_event_count = 0
        self.last_event = None

        # Lifetime Session Tracking (Never purged until reset)
        self.session_events = []
        self.shortcut_counts = {}
        self.shortcut_first_seen = {}
        self.shortcut_last_seen = {}
        self.current_session_id = None
        self.current_student_id = None
        self.event_callbacks = []

        # Primary prioritized combo definitions (checked longest first)
        self.combo_definitions = [
            (frozenset(["ctrl", "shift", "i"]), "devtools"),
            (frozenset(["alt", "tab"]), "alt+tab"),
            (frozenset(["ctrl", "c"]), "ctrl+c"),
            (frozenset(["ctrl", "v"]), "ctrl+v"),
            (frozenset(["ctrl", "x"]), "ctrl+x"),
            (frozenset(["ctrl", "a"]), "ctrl+a"),
            (frozenset(["ctrl", "w"]), "ctrl+w"),
            (frozenset(["ctrl", "t"]), "ctrl+t"),
            (frozenset(["alt", "f4"]), "alt+f4"),
            (frozenset(["win", "tab"]), "win+tab"),
            (frozenset(["win", "v"]), "win+v"),
            (frozenset(["win", "d"]), "win+d"),
            (frozenset(["win"]), "win"),
            (frozenset(["print_screen"]), "print_screen"),
            (frozenset(["f12"]), "devtools"),
        ]

        # Backward compatibility target_combos dict
        self.target_combos = {combo: name for combo, name in self.combo_definitions}
        # Also add legacy Key objects for compatibility with external references
        self.target_combos.update({
            frozenset([keyboard.Key.alt, keyboard.Key.tab]): "alt+tab",
            frozenset([keyboard.Key.ctrl, keyboard.KeyCode.from_char("c")]): "ctrl+c",
            frozenset([keyboard.Key.ctrl, keyboard.KeyCode.from_char("v")]): "ctrl+v",
            frozenset([keyboard.Key.cmd, keyboard.KeyCode.from_char("c")]): "ctrl+c",
            frozenset([keyboard.Key.cmd, keyboard.KeyCode.from_char("v")]): "ctrl+v",
            frozenset([keyboard.Key.cmd]): "win",
            frozenset([keyboard.Key.cmd_r]): "win",
            frozenset([keyboard.Key.print_screen]): "print_screen",
            frozenset([keyboard.Key.alt, keyboard.Key.f4]): "alt+f4",
        })

    def set_session(self, session_id: str, student_id: str):
        """Attaches active examination session credentials for automatic database persistence."""
        with self.lock:
            self.current_session_id = session_id
            self.current_student_id = student_id

    def add_event_callback(self, callback):
        """Registers a callback function fn(event_dict) to be invoked upon each shortcut trigger."""
        with self.lock:
            if callback not in self.event_callbacks:
                self.event_callbacks.append(callback)

    def _normalize_key(self, key):
        """
        Translates raw pynput keys, virtual key codes, and Windows control characters
        into a consistent lowercase string representation.
        """
        if isinstance(key, str):
            return key.lower()

        # Modifier Keys
        if key in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            return "ctrl"
        if key in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
            return "alt"
        if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
            return "shift"
        if key in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r):
            return "win"

        # Special Action Keys
        if key == keyboard.Key.tab:
            return "tab"
        if key == keyboard.Key.print_screen:
            return "print_screen"
        if key == keyboard.Key.f4:
            return "f4"
        if key == keyboard.Key.f12:
            return "f12"
        if key == keyboard.Key.esc:
            return "esc"

        # Character keys & Windows ASCII Control Codes
        char = getattr(key, "char", None)
        if char:
            c = ord(char)
            # When Ctrl is held on Windows, 'c' becomes \x03, 'v' becomes \x16, 'a' becomes \x01, etc.
            if 1 <= c <= 26:
                return chr(ord("a") + c - 1)
            return char.lower()

        # Virtual Key Codes fallback
        vk = getattr(key, "vk", None)
        if vk is not None:
            if 65 <= vk <= 90:  # A-Z
                return chr(vk).lower()
            if 48 <= vk <= 57:  # 0-9
                return chr(vk)
            if vk == 9:  # VK_TAB
                return "tab"
            if vk == 44:  # VK_SNAPSHOT (PrintScreen)
                return "print_screen"
            if vk == 115:  # VK_F4
                return "f4"
            if vk == 123:  # VK_F12
                return "f12"
            if vk in (91, 92):  # VK_LWIN, VK_RWIN
                return "win"
            if vk in (162, 163, 17):  # VK_CONTROL
                return "ctrl"
            if vk in (164, 165, 18):  # VK_MENU (Alt)
                return "alt"
            if vk in (160, 161, 16):  # VK_SHIFT
                return "shift"

        # Key Name fallback
        name = getattr(key, "name", None)
        if name:
            if name.startswith("ctrl"):
                return "ctrl"
            if name.startswith("alt"):
                return "alt"
            if name.startswith("cmd"):
                return "win"
            if name.startswith("shift"):
                return "shift"
            return name.lower()

        return None

    def _clean_stale_keys(self, now):
        """
        Cleans keys that have been held longer than 5 seconds without release.
        Handles focus loss where OS did not send on_release (e.g. Alt+Tab window switch).
        """
        stale_threshold = 5.0
        stale_keys = [
            k for k, t in self.key_timestamps.items() if (now - t) > stale_threshold
        ]
        for k in stale_keys:
            self.current_keys.discard(k)
            self.key_timestamps.pop(k, None)
            to_clear = [
                name
                for combo, name in self.combo_definitions
                if k in combo and name in self.triggered_combos
            ]
            for name in to_clear:
                self.triggered_combos.discard(name)

    def _on_press(self, key):
        k = self._normalize_key(key)
        if not k:
            return

        now = time.time()
        with self.lock:
            self._clean_stale_keys(now)
            self.current_keys.add(k)
            self.key_timestamps[k] = now

            # Check if active key set matches any defined target shortcut
            for combo, name in self.combo_definitions:
                if combo.issubset(self.current_keys):
                    # Prevent auto-repeat spamming while shortcut is held down
                    if name not in self.triggered_combos:
                        self.triggered_combos.add(name)
                        self._record_event_unlocked(name, record_db=True)
                    break

    def _on_release(self, key):
        k = self._normalize_key(key)
        if not k:
            return

        with self.lock:
            if k in self.current_keys:
                self.current_keys.discard(k)
            self.key_timestamps.pop(k, None)

            # Untrigger any combos that require this released key
            to_clear = [
                name
                for combo, name in self.combo_definitions
                if k in combo and name in self.triggered_combos
            ]
            for name in to_clear:
                self.triggered_combos.discard(name)

    def _record_event_unlocked(self, shortcut_name, record_db=True):
        """Records an event assuming self.lock is already acquired."""
        now = time.time()
        if self.last_event_time is not None:
            inter_event_timing = round(now - self.last_event_time, 3)
        else:
            inter_event_timing = 0.0

        self.last_event_time = now
        self.total_event_count += 1

        # Track key frequency and occurrence timestamps
        self.shortcut_counts[shortcut_name] = self.shortcut_counts.get(shortcut_name, 0) + 1
        if shortcut_name not in self.shortcut_first_seen:
            self.shortcut_first_seen[shortcut_name] = now
        self.shortcut_last_seen[shortcut_name] = now

        meta = SHORTCUT_METADATA.get(shortcut_name, {
            "display_name": shortcut_name.upper(),
            "action": "Prohibited Hotkey",
            "violation_type": "Prohibited Shortcut",
            "severity": "MEDIUM",
            "risk_level": "MEDIUM",
            "description": f"Triggered prohibited hotkey: {shortcut_name}",
        })

        time_str = datetime.datetime.fromtimestamp(now).strftime("%H:%M:%S")

        event = {
            "timestamp": now,
            "timestamp_str": time_str,
            "shortcut": shortcut_name,
            "display_name": meta.get("display_name", shortcut_name.upper()),
            "event_type": "SUSPICIOUS_SHORTCUT",
            "inter_event_timing": inter_event_timing,
            "event_index": self.total_event_count,
            "count_for_shortcut": self.shortcut_counts[shortcut_name],
            "severity": meta.get("severity", "MEDIUM"),
            "risk_level": meta.get("risk_level", "MEDIUM"),
            "action": meta.get("action", "Prohibited Hotkey"),
            "violation_type": meta.get("violation_type", "Prohibited Shortcut"),
            "description": meta.get("description", f"Prohibited hotkey triggered: {shortcut_name.upper()}"),
        }
        self.event_history.append(event)
        self.session_events.append(event)
        self.last_event = event

        # Notify callbacks
        for cb in self.event_callbacks:
            try:
                cb(event)
            except Exception:
                pass

        # If active session credentials are set, record event in database
        if record_db and self.current_session_id and self.current_student_id:
            try:
                from database.db import get_db
                db = get_db()
                db.record_event(
                    exam_session_id=self.current_session_id,
                    student_id=self.current_student_id,
                    event_type="HOTKEY_SHORTCUT",
                    event_description=f"Forbidden shortcut detected: {meta.get('display_name', shortcut_name.upper())} ({self.shortcut_counts[shortcut_name]}x)",
                    detection_method="KeyboardHook (pynput)",
                    risk_level=meta.get("risk_level", "MEDIUM"),
                    severity=meta.get("severity", "MEDIUM"),
                    raw_data={
                        "shortcut": shortcut_name,
                        "display_name": meta.get("display_name", shortcut_name.upper()),
                        "count": self.shortcut_counts[shortcut_name],
                        "total_count": self.total_event_count,
                    },
                    occurred_at=now,
                )
            except Exception:
                pass

    def _record_event(self, shortcut_name, record_db=True):
        """Thread-safe public event recording."""
        with self.lock:
            self._record_event_unlocked(shortcut_name, record_db=record_db)

    def start(self):
        """Safely starts the non-blocking keyboard listener thread."""
        with self.lock:
            if not self.is_running:
                self.is_running = True
                try:
                    self.listener = keyboard.Listener(
                        on_press=self._on_press, on_release=self._on_release
                    )
                    self.listener.daemon = True
                    self.listener.start()
                    print("[KeyboardMonitor] Non-blocking pynput listener started safely.")
                except Exception as e:
                    print(f"[KeyboardMonitor] Listener start error ({e}). Running in simulation mode.")

    def stop(self):
        """Safely stops the keyboard listener thread."""
        with self.lock:
            if self.is_running and self.listener is not None:
                try:
                    self.listener.stop()
                except Exception:
                    pass
                self.listener = None
                self.is_running = False
                self.current_keys.clear()
                self.triggered_combos.clear()
                print("[KeyboardMonitor] Keyboard listener stopped safely.")

    def trigger_simulated_shortcut(self, shortcut_name, record_db=True):
        """Allows direct simulation of shortcut events for testing/demos."""
        self._record_event(shortcut_name, record_db=record_db)

    def get_telemetry(self, window_sec=None):
        """
        Calculates event frequency, inter-event timing, active recent events, and continuous keyboard penalty score.
        An isolated shortcut press generates a low penalty (0.2) rather than an automatic cheating flag.
        Also computes cumulative session penalty and occurrence counts per shortcut.
        """
        now = time.time()
        decay = window_sec if window_sec is not None else self.decay_seconds

        with self.lock:
            self._clean_stale_keys(now)

            # Evict expired events past decay window
            while self.event_history and (now - self.event_history[0]["timestamp"]) > decay:
                self.event_history.popleft()

            recent_events = list(self.event_history)
            freq = len(recent_events)

            latest_inter_event = 0.0
            if recent_events:
                latest_inter_event = recent_events[-1]["inter_event_timing"]

            # Calculate Instantaneous Keyboard Penalty [0.0 to 1.0]
            if freq == 0:
                keyboard_penalty = 0.0
            elif freq == 1:
                # Isolated shortcut press -> low penalty (0.2), not cheating
                keyboard_penalty = self.base_penalty
            else:
                # Multiple rapid shortcut presses -> higher penalty
                rapid_boost = (
                    0.2
                    if (latest_inter_event > 0 and latest_inter_event <= self.rapid_trigger_window)
                    else 0.05
                )
                keyboard_penalty = min(1.0, self.base_penalty + (freq - 1) * 0.25 + rapid_boost)

            # Cumulative session-wide penalty reflecting total violations committed
            if self.total_event_count == 0:
                cumulative_penalty = 0.0
            elif self.total_event_count == 1:
                cumulative_penalty = max(keyboard_penalty, 0.35)
            else:
                cumulative_penalty = min(1.0, 0.35 + (self.total_event_count - 1) * 0.15)

            return {
                "timestamp": now,
                "is_running": self.is_running,
                "event_frequency": freq,
                "total_event_count": self.total_event_count,
                "latest_inter_event_timing": latest_inter_event,
                "keyboard_penalty": round(keyboard_penalty, 3),
                "cumulative_penalty": round(cumulative_penalty, 3),
                "recent_events": recent_events,
                "last_event": self.last_event,
                "active_keys": list(self.current_keys),
                "shortcut_counts": dict(self.shortcut_counts),
                "session_events": list(self.session_events),
            }

    def get_recent_events(self, window_sec=None):
        """Returns list of active shortcut events."""
        telemetry = self.get_telemetry(window_sec=window_sec)
        return telemetry["recent_events"]

    def get_shortcut_summary(self) -> Dict[str, Any]:
        """
        Returns structured summary of all keyboard shortcuts detected during the session:
        counts per key, first and last occurrence timestamps, severity, and full breakdown.
        """
        with self.lock:
            breakdown = []
            for sc, count in self.shortcut_counts.items():
                meta = SHORTCUT_METADATA.get(sc, {
                    "display_name": sc.upper(),
                    "action": "Prohibited Hotkey",
                    "violation_type": "Prohibited Shortcut",
                    "severity": "MEDIUM",
                    "risk_level": "MEDIUM",
                    "description": f"Triggered prohibited hotkey: {sc}",
                })
                t_first = self.shortcut_first_seen.get(sc, 0.0)
                t_last = self.shortcut_last_seen.get(sc, 0.0)
                breakdown.append({
                    "shortcut": sc,
                    "display_name": meta.get("display_name", sc.upper()),
                    "count": count,
                    "action": meta.get("action", "Hotkey Action"),
                    "violation_type": meta.get("violation_type", "Prohibited Shortcut"),
                    "severity": meta.get("severity", "MEDIUM"),
                    "risk_level": meta.get("risk_level", "MEDIUM"),
                    "first_seen_str": datetime.datetime.fromtimestamp(t_first).strftime("%H:%M:%S") if t_first else "N/A",
                    "last_seen_str": datetime.datetime.fromtimestamp(t_last).strftime("%H:%M:%S") if t_last else "N/A",
                    "description": meta.get("description", ""),
                })

            # Sort by frequency descending
            breakdown.sort(key=lambda x: x["count"], reverse=True)

            return {
                "total_count": self.total_event_count,
                "unique_shortcuts_count": len(self.shortcut_counts),
                "shortcut_counts": dict(self.shortcut_counts),
                "session_events": list(self.session_events),
                "breakdown": breakdown,
                "has_violations": self.total_event_count > 0,
            }

    def reset(self):
        """Resets event history counters, active keys, and session accumulators."""
        with self.lock:
            self.event_history.clear()
            self.session_events.clear()
            self.shortcut_counts.clear()
            self.shortcut_first_seen.clear()
            self.shortcut_last_seen.clear()
            self.current_keys.clear()
            self.key_timestamps.clear()
            self.triggered_combos.clear()
            self.last_event_time = None
            self.total_event_count = 0
            self.last_event = None
            self.current_session_id = None
            self.current_student_id = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# -----------------------------------------------------------------------------
# Module-level Singleton Accessor
# -----------------------------------------------------------------------------
_GLOBAL_KEYBOARD_MONITOR: Optional[KeyboardMonitor] = None
_GLOBAL_KB_LOCK = threading.Lock()


def get_global_keyboard_monitor() -> KeyboardMonitor:
    """Thread-safe global singleton for KeyboardMonitor across all threads and modules."""
    global _GLOBAL_KEYBOARD_MONITOR
    with _GLOBAL_KB_LOCK:
        if _GLOBAL_KEYBOARD_MONITOR is None:
            _GLOBAL_KEYBOARD_MONITOR = KeyboardMonitor()
            try:
                _GLOBAL_KEYBOARD_MONITOR.start()
            except Exception as e:
                print(f"[KeyboardMonitor] Global listener start warning: {e}", flush=True)
        return _GLOBAL_KEYBOARD_MONITOR
