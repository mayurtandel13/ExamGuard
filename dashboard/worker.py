"""
ProctoringWorker Process-Wide Background Thread Engine
Decouples heavy Python ML inference, webcam frame acquisition, and signal fusion from Streamlit.
STRICT REQUIREMENT: ZERO streamlit (st.*) imports or calls inside this file or thread.
"""

import time
import threading
import cv2
import numpy as np
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

from config import CAMERA_CONFIG
from camera.capture import CameraCapture
from face.landmarks import FaceLandmarkExtractor
from head_pose.estimator import HeadPoseEstimator
from gaze.tracker import GazeTracker
from yolo.detector import YOLOObjectDetector
from keyboard.monitor import KeyboardMonitor
from fusion.engine import BehavioralFusionEngine
from timeline.timeline import BehavioralTimeline


@dataclass
class WorkerBufferData:
    timestamp: float = 0.0
    models_status: str = "loading"  # "loading", "ready", "error"
    models_error_msg: str = ""
    camera_status: str = "opening"  # "opening", "ready", "unavailable", "error"
    camera_error_msg: str = ""
    frame: Optional[np.ndarray] = None
    annotated_frame: Optional[np.ndarray] = None
    fps: float = 0.0
    landmark_tel: Dict[str, Any] = field(default_factory=lambda: {"face_detected": False, "primary_landmarks": None})
    head_tel: Dict[str, Any] = field(default_factory=lambda: {"status": "FORWARD", "pitch": 0.0, "yaw": 0.0, "roll": 0.0})
    gaze_tel: Dict[str, Any] = field(default_factory=lambda: {"gaze_state": "CENTER", "attention_score": 1.0, "avg_ear": 0.25})
    yolo_tel: Dict[str, Any] = field(default_factory=lambda: {"phone_detected": False, "person_count": 1, "multi_person_detected": False})
    kb_tel: Dict[str, Any] = field(default_factory=lambda: {"keyboard_penalty": 0.0, "recent_events": []})
    fusion_res: Dict[str, Any] = field(default_factory=lambda: {"risk_level": "LOW", "cheating_probability": 0.0})
    timing_ms: Dict[str, float] = field(default_factory=lambda: {"camera": 0.0, "face": 0.0, "yolo": 0.0, "total": 0.0})


# Module-level lazy ML models cache (thread-safe)
_MODELS_LOCK = threading.Lock()
_MODELS_CACHE = {}


def _get_lazy_models(enable_yolo=True):
    with _MODELS_LOCK:
        if "face" not in _MODELS_CACHE:
            print("[ProctoringWorker] Lazy loading backend ML models...", flush=True)
            _MODELS_CACHE["face"] = FaceLandmarkExtractor(max_num_faces=2, refine_landmarks=True)
            _MODELS_CACHE["head"] = HeadPoseEstimator()
            _MODELS_CACHE["gaze"] = GazeTracker()
            if enable_yolo:
                try:
                    _MODELS_CACHE["yolo"] = YOLOObjectDetector()
                except Exception as e:
                    print(f"[ProctoringWorker] YOLO load warning: {e}", flush=True)
                    _MODELS_CACHE["yolo"] = None
            else:
                _MODELS_CACHE["yolo"] = None
        return _MODELS_CACHE


# Process-wide worker singleton
_WORKER_SINGLETON = None
_WORKER_LOCK = threading.Lock()


class ProctoringWorker:
    """
    Decoupled background worker thread running ML inference & frame capture asynchronously.
    Updates a thread-safe dataclass buffer.
    ZERO st.* calls anywhere inside this class.
    """

    def __init__(self, device_idx=CAMERA_CONFIG["DEVICE_INDEX"], enable_yolo=True, kb_monitor=None):
        self.device_idx = int(device_idx)
        self.enable_yolo = enable_yolo
        if kb_monitor is not None:
            self.kb_monitor = kb_monitor
        else:
            try:
                from keyboard.monitor import get_global_keyboard_monitor
                self.kb_monitor = get_global_keyboard_monitor()
            except Exception:
                self.kb_monitor = None
        self.lock = threading.Lock()
        
        self.is_running = False
        self.thread = None
        self.cap = None
        
        self.fusion_engine = BehavioralFusionEngine()
        self.timeline = BehavioralTimeline()
        
        # Thread-safe Dataclass Buffer
        self.buffer = WorkerBufferData()

        # Tab switch detection state
        self._tab_switch_detected = False
        self._tab_switch_count = 0

        # Phone detection state
        self._phone_detected_sim = False
        self._phone_detected_count = 0
        self._last_phone_logged_time = 0.0
        self.active_session_id = "LIVE_SESSION"
        self.student_id = "STU-2026-081"

    def set_session_info(self, exam_session_id: str, student_id: str):
        """Sets active examination session and student metadata for event recording."""
        with self.lock:
            self.active_session_id = exam_session_id
            self.student_id = student_id

    def notify_tab_switch(self, count=1):
        """Notifies the proctoring worker that a tab switch occurred, elevating risk to HIGH."""
        with self.lock:
            self._tab_switch_detected = True
            self._tab_switch_count += int(count)

    def reset_tab_switch(self):
        """Resets the tab switch violation state."""
        with self.lock:
            self._tab_switch_detected = False
            self._tab_switch_count = 0

    def notify_phone_detected(self, confidence: float = 0.92):
        """Triggers simulated or verified phone detection and records event."""
        with self.lock:
            self._phone_detected_sim = True
            self._phone_detected_count += 1
            now = time.time()
            self._last_phone_logged_time = now

        self.timeline.add_event(
            module="YOLOObjectDetector",
            event_type="MOBILE_PHONE_DETECTED",
            severity="HIGH",
            value=float(confidence),
            description=f"Mobile phone detected in proctoring camera frame (Confidence: {confidence * 100:.1f}%). Prohibited device violation.",
            risk_contribution=0.85,
        )

        try:
            from database.db import get_db
            db = get_db()
            db.record_event(
                exam_session_id=self.active_session_id,
                student_id=self.student_id,
                event_type="MOBILE_PHONE_DETECTED",
                event_description=f"Mobile phone detected in camera feed (Confidence: {confidence * 100:.1f}%). Warning served to candidate.",
                detection_method="YOLOv8ObjectDetector",
                risk_level="HIGH",
                severity="HIGH",
                raw_data={"phone_detected": True, "phone_confidence": confidence, "simulated": True},
            )
        except Exception:
            pass

    def reset_phone_detection(self):
        """Resets phone detection state."""
        with self.lock:
            self._phone_detected_sim = False
            self._phone_detected_count = 0

    def _open_camera(self):
        """Attempts to open physical webcam with candidate check and non-empty frame validation."""
        candidates = [self.device_idx, 1, 0]
        unique_candidates = []
        for c in candidates:
            if c not in unique_candidates:
                unique_candidates.append(c)

        for c in unique_candidates:
            # Try DSHOW backend first on Windows for physical webcams
            try:
                cap = cv2.VideoCapture(int(c), cv2.CAP_DSHOW)
                if cap.isOpened():
                    ret, f = cap.read()
                    if ret and f is not None and f.size > 0 and f.mean() > 0.5:
                        self.device_idx = c
                        print(f"[ProctoringWorker] Successfully opened DSHOW webcam index {c}", flush=True)
                        return cap
                    cap.release()
            except Exception:
                pass

            # Fallback to default backend
            try:
                cap = cv2.VideoCapture(int(c))
                if cap.isOpened():
                    ret, f = cap.read()
                    if ret and f is not None and f.size > 0 and f.mean() > 0.5:
                        self.device_idx = c
                        print(f"[ProctoringWorker] Successfully opened webcam index {c}", flush=True)
                        return cap
                    cap.release()
            except Exception:
                pass

        return None

    def start(self):
        """Starts background worker thread safely without duplicating."""
        with self.lock:
            if self.is_running:
                return
            self.is_running = True
            self.thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.thread.start()
            print("[ProctoringWorker] Background thread started.", flush=True)

    def _worker_loop(self):
        """Continuous background loop running frame capture and ML inference at ~15 FPS."""
        # 1. Load ML Models
        try:
            models = _get_lazy_models(enable_yolo=self.enable_yolo)
            with self.lock:
                self.buffer.models_status = "ready"
                self.buffer.models_error_msg = ""
        except Exception as e:
            with self.lock:
                self.buffer.models_status = "error"
                self.buffer.models_error_msg = str(e)
            print(f"[ProctoringWorker] Model load error: {e}", flush=True)

        # 2. Open Camera
        self.cap = self._open_camera()
        if self.cap is not None and self.cap.isOpened():
            with self.lock:
                self.buffer.camera_status = "opening"
                self.buffer.camera_error_msg = ""
        else:
            with self.lock:
                self.buffer.camera_status = "unavailable"
                self.buffer.camera_error_msg = f"Camera device #{self.device_idx} unavailable (No active physical video stream detected)"
            print("[ProctoringWorker] Camera unavailable.", flush=True)

        frame_count = 0
        fps_start_time = time.perf_counter()
        current_fps = 0.0

        while self.is_running:
            t_loop_start = time.perf_counter()
            
            # Read Frame
            t0 = time.perf_counter()
            frame = None
            if self.cap is not None and self.cap.isOpened():
                try:
                    ret, f = self.cap.read()
                    if ret and f is not None and f.size > 0 and f.mean() > 0.5:
                        frame = f
                        with self.lock:
                            self.buffer.camera_status = "ready"
                            self.buffer.camera_error_msg = ""
                    else:
                        with self.lock:
                            if self.buffer.annotated_frame is None:
                                self.buffer.camera_status = "unavailable"
                                self.buffer.camera_error_msg = f"Camera device #{self.device_idx} is not transmitting video frames"
                except Exception as e:
                    with self.lock:
                        self.buffer.camera_status = "error"
                        self.buffer.camera_error_msg = str(e)
            t_cam = (time.perf_counter() - t0) * 1000.0

            # Debug mode test frame fallback if EXAM_DEBUG=1
            is_debug = os.environ.get("EXAM_DEBUG", "0") == "1"
            if frame is None and is_debug:
                frame = self._create_synthetic_debug_frame()

            # Face Mesh, Head Pose, Eye Gaze
            t1 = time.perf_counter()
            if frame is not None and self.buffer.models_status == "ready":
                landmark_extractor = models.get("face")
                head_estimator = models.get("head")
                gaze_tracker = models.get("gaze")

                landmark_tel = landmark_extractor.extract_landmarks(frame) if landmark_extractor else {"face_detected": False, "primary_landmarks": None}
                head_tel = head_estimator.process_frame(frame) if head_estimator else {"status": "FORWARD", "pitch": 0.0, "yaw": 0.0, "roll": 0.0}
                gaze_tel = gaze_tracker.process(landmark_tel.get("primary_landmarks"), frame.shape) if gaze_tracker else {"gaze_state": "CENTER", "attention_score": 1.0, "avg_ear": 0.25}
            else:
                landmark_tel = {"face_detected": False, "primary_landmarks": None}
                head_tel = {"status": "FORWARD", "pitch": 0.0, "yaw": 0.0, "roll": 0.0}
                gaze_tel = {"gaze_state": "CENTER", "attention_score": 1.0, "avg_ear": 0.25}
            t_face = (time.perf_counter() - t1) * 1000.0

            # YOLO Object Detection
            t2 = time.perf_counter()
            yolo_detector = models.get("yolo") if self.buffer.models_status == "ready" else None
            if frame is not None and self.enable_yolo and yolo_detector:
                yolo_tel = yolo_detector.process_frame(frame)
            else:
                yolo_tel = {
                    "phone_detected": False,
                    "person_count": 1 if landmark_tel.get("face_detected", False) else 0,
                    "multi_person_detected": False
                }

            # Check simulated phone detection override
            with self.lock:
                sim_phone = self._phone_detected_sim

            if sim_phone:
                yolo_tel["phone_detected"] = True
                if float(yolo_tel.get("phone_confidence", 0.0)) < 0.85:
                    yolo_tel["phone_confidence"] = 0.92

            # When phone is detected, throttle recording to database
            if yolo_tel.get("phone_detected"):
                now_t = time.time()
                with self.lock:
                    self._phone_detected_count += 1
                if now_t - self._last_phone_logged_time > 3.0:
                    self._last_phone_logged_time = now_t
                    try:
                        from database.db import get_db
                        db = get_db()
                        conf = float(yolo_tel.get("phone_confidence", 0.90))
                        db.record_event(
                            exam_session_id=self.active_session_id,
                            student_id=self.student_id,
                            event_type="MOBILE_PHONE_DETECTED",
                            event_description=f"Mobile phone detected in proctoring camera frame (Confidence: {conf*100:.1f}%). Prohibited device violation.",
                            detection_method="YOLOv8ObjectDetector",
                            risk_level="HIGH",
                            severity="HIGH",
                            raw_data=yolo_tel,
                        )
                    except Exception:
                        pass
            
            # Keyboard Telemetry (thread-safe fetch from passed kb_monitor if available)
            kb_tel = {"keyboard_penalty": 0.0, "recent_events": []}
            if self.kb_monitor and hasattr(self.kb_monitor, "get_telemetry"):
                try:
                    kb_tel = self.kb_monitor.get_telemetry()
                except Exception:
                    pass
            t_ml = (time.perf_counter() - t2) * 1000.0

            # Tab switch telemetry
            with self.lock:
                tab_tel = {
                    "tab_switch_detected": self._tab_switch_detected,
                    "count": self._tab_switch_count,
                }

            # Fusion & Timeline Logging (Always compute fusion score so keyboard & behavioral events update telemetry)
            fusion_res = self.fusion_engine.compute_fusion_score(head_tel, gaze_tel, yolo_tel, kb_tel, tab_telemetry=tab_tel)
            self.timeline.record_snapshot(head_tel, gaze_tel, yolo_tel, kb_tel, fusion_res)

            # Frame Annotation
            annotated = None
            if frame is not None:
                annotated = frame.copy()
                landmark_extractor = models.get("face")
                if landmark_tel.get("face_detected") and landmark_extractor:
                    annotated = landmark_extractor.draw_landmarks(annotated, landmark_tel)

                r_level = fusion_res["risk_level"]
                c_score = fusion_res["cheating_probability"]
                banner_color = (0, 230, 118) if r_level == "LOW" else ((0, 234, 255) if r_level == "MEDIUM" else (0, 23, 255))
                cv2.rectangle(annotated, (0, 0), (annotated.shape[1], 36), (20, 20, 20), -1)
                cv2.putText(annotated, f"RISK: {r_level} | PROB: {c_score:.2f}", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, banner_color, 2)

                # Flash red phone warning if phone is detected in frame
                if yolo_tel.get("phone_detected", False):
                    cv2.rectangle(annotated, (0, annotated.shape[0] - 38), (annotated.shape[1], annotated.shape[0]), (0, 0, 200), -1)
                    cv2.putText(annotated, "WARNING: MOBILE PHONE DETECTED!", (20, annotated.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

            t_total = (time.perf_counter() - t_loop_start) * 1000.0

            # FPS calculation
            frame_count += 1
            elapsed_fps = time.perf_counter() - fps_start_time
            if elapsed_fps >= 1.0:
                current_fps = round(frame_count / elapsed_fps, 1)
                frame_count = 0
                fps_start_time = time.perf_counter()

            # Update Dataclass Buffer Safely
            with self.lock:
                self.buffer.timestamp = time.time()
                self.buffer.frame = frame
                self.buffer.annotated_frame = annotated
                self.buffer.fps = current_fps
                self.buffer.landmark_tel = landmark_tel
                self.buffer.head_tel = head_tel
                self.buffer.gaze_tel = gaze_tel
                self.buffer.yolo_tel = yolo_tel
                self.buffer.kb_tel = kb_tel
                self.buffer.fusion_res = fusion_res
                self.buffer.timing_ms = {
                    "camera": round(t_cam, 1),
                    "face": round(t_face, 1),
                    "yolo": round(t_ml, 1),
                    "total": round(t_total, 1)
                }

            # Pace loop at ~15 FPS (~66ms target)
            elapsed_sec = time.perf_counter() - t_loop_start
            sleep_time = max(0.01, 0.066 - elapsed_sec)
            time.sleep(sleep_time)

        # Cleanup on loop exit
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        print("[ProctoringWorker] Stopped and camera released.", flush=True)

    def _create_synthetic_debug_frame(self):
        """Creates debug test card when EXAM_DEBUG=1 is active."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:, :] = (80, 50, 30)
        cv2.rectangle(frame, (20, 20), (620, 460), (0, 255, 255), 2)
        cv2.putText(frame, "📷 EXAM_DEBUG STREAM (Synthetic Pattern)", (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
        return frame

    def get_latest_data(self) -> WorkerBufferData:
        """Thread-safe read of latest buffer dataclass."""
        with self.lock:
            return self.buffer

    def get_timeline(self):
        """Returns reference to internal BehavioralTimeline."""
        return self.timeline

    def stop(self):
        """Stops background thread and releases resources."""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            try:
                self.thread.join(timeout=1.0)
            except Exception:
                pass
        self.thread = None


def get_process_worker_singleton(device_idx=CAMERA_CONFIG["DEVICE_INDEX"], enable_yolo=True, kb_monitor=None):
    """Process-wide singleton accessor for ProctoringWorker."""
    global _WORKER_SINGLETON
    with _WORKER_LOCK:
        if _WORKER_SINGLETON is None or not _WORKER_SINGLETON.is_running:
            _WORKER_SINGLETON = ProctoringWorker(device_idx=device_idx, enable_yolo=enable_yolo, kb_monitor=kb_monitor)
            _WORKER_SINGLETON.start()
        elif kb_monitor is not None and _WORKER_SINGLETON.kb_monitor is None:
            _WORKER_SINGLETON.kb_monitor = kb_monitor
        return _WORKER_SINGLETON


def stop_process_worker_singleton():
    """Stops and clears process-wide singleton."""
    global _WORKER_SINGLETON
    with _WORKER_LOCK:
        if _WORKER_SINGLETON is not None:
            _WORKER_SINGLETON.stop()
            _WORKER_SINGLETON = None
