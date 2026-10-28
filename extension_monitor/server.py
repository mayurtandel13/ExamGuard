"""
HTTP Beacon Server for Client-Side Tab Switching & Integrity Monitoring
Receives beacon pings from client-side JS when browser window loses focus, tabs switch,
or extensions are detected in the candidate's browser environment.
"""

import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional
from database.db import get_db

_server_instance = None
_server_lock = threading.Lock()

# Thread-safe in-memory cache for live extension events
_ACTIVE_DETECTED_EXTENSIONS: Dict[str, Dict[str, Any]] = {}
_LATEST_DETECTED_EXTENSION: Optional[Dict[str, Any]] = None
_INSTITUTIONAL_EXT_CONNECTED: bool = False
_EXTENSION_STATE_LOCK = threading.Lock()


def record_active_extension(
    ext_name: str,
    session_id: str = "UNKNOWN",
    student_id: str = "STU-2026-081",
    stage: str = "PRE_EXAM",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Records an active extension detection event in memory for fast UI queries."""
    global _LATEST_DETECTED_EXTENSION, _INSTITUTIONAL_EXT_CONNECTED
    with _EXTENSION_STATE_LOCK:
        entry = {
            "name": ext_name,
            "session_id": session_id,
            "student_id": student_id,
            "stage": stage,
            "timestamp": time.time(),
            "extra": extra or {},
        }
        _ACTIVE_DETECTED_EXTENSIONS[student_id] = entry
        _LATEST_DETECTED_EXTENSION = entry
        lower_name = ext_name.lower()
        if "companion" in lower_name or "institutional" in lower_name:
            _INSTITUTIONAL_EXT_CONNECTED = True


def get_active_detected_extension(student_id: str = "STU-2026-081") -> Optional[Dict[str, Any]]:
    """
    Returns the active detected extension for a student if detected recently (within 15 minutes).
    Falls back to the most recent global detection if reported in the last 10 minutes.
    """
    with _EXTENSION_STATE_LOCK:
        now = time.time()
        entry = _ACTIVE_DETECTED_EXTENSIONS.get(student_id)
        if entry and (now - entry.get("timestamp", 0) < 900):
            return entry
        if _LATEST_DETECTED_EXTENSION and (now - _LATEST_DETECTED_EXTENSION.get("timestamp", 0) < 600):
            return _LATEST_DETECTED_EXTENSION
        return None


def is_institutional_extension_connected() -> bool:
    """Returns True if the institutional companion extension completed a handshake."""
    with _EXTENSION_STATE_LOCK:
        return _INSTITUTIONAL_EXT_CONNECTED


def clear_active_detected_extension(student_id: Optional[str] = None) -> None:
    """Clears the active detected extension state for rescanning."""
    global _LATEST_DETECTED_EXTENSION, _INSTITUTIONAL_EXT_CONNECTED
    with _EXTENSION_STATE_LOCK:
        if student_id and student_id in _ACTIVE_DETECTED_EXTENSIONS:
            del _ACTIVE_DETECTED_EXTENSIONS[student_id]
        else:
            _ACTIVE_DETECTED_EXTENSIONS.clear()
        _LATEST_DETECTED_EXTENSION = None
        _INSTITUTIONAL_EXT_CONNECTED = False


class TabSwitchBeaconHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path in ("/api/extension_status", "/api/extension_status/"):
            active = get_active_detected_extension()
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            resp = {
                "active_extension_detected": active is not None,
                "detected_extension": active,
                "institutional_connected": is_institutional_extension_connected(),
            }
            self.wfile.write(json.dumps(resp).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/tab_switch":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                data = json.loads(body)
                count = int(data.get("count", 1))
                db = get_db()
                db.record_event(
                    exam_session_id=data.get("session_id", "UNKNOWN"),
                    student_id=data.get("student_id", "STU-2026-081"),
                    event_type="WINDOW_BLUR_TAB_SWITCH",
                    event_description=f"Candidate switched browser window or minimized examination tab (Incident #{count}). Tab detection risk elevated to HIGH.",
                    detection_method="ScreenFocusMonitor",
                    risk_level="HIGH",
                    severity="HIGH",
                    raw_data=data,
                )

                # Synchronize with ProctoringWorker singleton if already running
                try:
                    import dashboard.worker as worker_mod
                    worker = getattr(worker_mod, "_WORKER_SINGLETON", None)
                    if worker is not None and getattr(worker, "is_running", False):
                        if hasattr(worker, "notify_tab_switch"):
                            worker.notify_tab_switch(count=count)
                        worker.get_timeline().add_event(
                            module="ScreenFocusMonitor",
                            event_type="WINDOW_BLUR_TAB_SWITCH",
                            severity="HIGH",
                            value=float(count),
                            description=f"Candidate switched browser window or minimized tab (#{count}). Elevated to HIGH risk.",
                            risk_contribution=0.85,
                        )
                except Exception:
                    pass
            except Exception:
                pass

            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "recorded", "risk_level": "HIGH"}')
        elif self.path == "/api/keyboard_event":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                data = json.loads(body)
                shortcut = str(data.get("shortcut", "unknown")).lower()
                session_id = data.get("session_id", "UNKNOWN")
                student_id = data.get("student_id", "STU-2026-081")
                count = int(data.get("count", 1))

                is_high_risk = shortcut in ("print_screen", "alt+tab", "win+tab", "devtools", "f12", "alt+f4")
                risk_lvl = "HIGH" if is_high_risk else "MEDIUM"
                desc = f"Forbidden shortcut detected in browser: {shortcut.upper()} (Incident #{count})"

                db = get_db()
                db.record_event(
                    exam_session_id=session_id,
                    student_id=student_id,
                    event_type="HOTKEY_SHORTCUT",
                    event_description=desc,
                    detection_method="BrowserDOMHook",
                    risk_level=risk_lvl,
                    severity=risk_lvl,
                    raw_data=data,
                )

                # Synchronize with Python KeyboardMonitor singleton
                try:
                    from keyboard.monitor import get_global_keyboard_monitor
                    kb = get_global_keyboard_monitor()
                    kb.trigger_simulated_shortcut(shortcut, record_db=False)
                except Exception:
                    pass
            except Exception:
                pass

            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "recorded", "shortcut_captured": true}')
        elif self.path in ("/api/extension_event", "/api/extension_precheck", "/api/extension_handshake"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                data = json.loads(body)
                session_id = data.get("session_id", "PORTAL_ACTIVE_SESSION")
                student_id = data.get("student_id", "STU-2026-081")
                ext_name = data.get("extension_name", "Exam Integrity Extension")
                stage = data.get("stage", "PRE_EXAM")
                event_type = "PRE_EXAM_EXTENSION_DETECTED" if "PRE" in stage.upper() else "EXTENSION_DETECTED"
                desc = f"Active browser extension detected ({ext_name}) during {stage.replace('_', ' ').lower()}. Warning displayed to candidate; forwarded to faculty dashboard."

                # Update in-memory tracker
                record_active_extension(
                    ext_name=ext_name,
                    session_id=session_id,
                    student_id=student_id,
                    stage=stage,
                    extra=data,
                )

                db = get_db()
                db.record_event(
                    exam_session_id=session_id,
                    student_id=student_id,
                    event_type=event_type,
                    event_description=desc,
                    detection_method="PreExamExtensionScanner" if "PRE" in stage.upper() else "BrowserIntegrityGuard",
                    risk_level="HIGH",
                    severity="HIGH",
                    raw_data=data,
                )
            except Exception:
                pass

            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "recorded", "faculty_notified": true, "extension_recognized": true}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress console clutter


def start_tab_beacon_server(port: int = 8585) -> bool:
    """Starts the lightweight tab beacon server in a daemon background thread."""
    global _server_instance
    with _server_lock:
        if _server_instance is not None:
            return True
        try:
            server = HTTPServer(("127.0.0.1", port), TabSwitchBeaconHandler)
            _server_instance = server
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            return True
        except Exception:
            # Port may already be bound or in use
            return False
