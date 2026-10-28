"""
Camera Capture Module (Thread-Safe Background Video Stream Engine)
Handles webcam stream initialization, continuous background thread frame acquisition,
thread-safe RAM frame buffer access, auto-camera index detection, and resource cleanup.
"""

import time
import threading
import cv2
import numpy as np
from config import CAMERA_CONFIG


class CameraCapture:
    """
    Decoupled, thread-safe abstraction for webcam video stream capture with automatic fallback
    and continuous background thread frame reading.
    """

    def __init__(self, device_index=CAMERA_CONFIG["DEVICE_INDEX"]):
        self.device_index = int(device_index)
        self.cap = None
        self.width = int(CAMERA_CONFIG["FRAME_WIDTH"])
        self.height = int(CAMERA_CONFIG["FRAME_HEIGHT"])
        self.fps = int(CAMERA_CONFIG["TARGET_FPS"])

        self.lock = threading.Lock()
        self.is_running = False
        self.thread = None
        self.current_frame = None

    @staticmethod
    def is_droidcam_standby_frame(frame):
        """
        Validates if frame is a non-empty image matrix.
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return True
        return False

    def _try_open_cap(self, idx):
        """Helper to try opening VideoCapture with default backend first, then DSHOW."""
        try:
            cap = cv2.VideoCapture(int(idx))
            if cap.isOpened():
                ret, f = cap.read()
                if ret and f is not None and f.size > 0 and f.mean() > 1.0:
                    return cap
                cap.release()
        except Exception:
            pass

        try:
            cap = cv2.VideoCapture(int(idx), cv2.CAP_DSHOW)
            if cap.isOpened():
                ret, f = cap.read()
                if ret and f is not None and f.size > 0 and f.mean() > 1.0:
                    return cap
                cap.release()
        except Exception:
            pass

        return None

    def find_working_camera_index(self):
        """
        Quick single-pass check of primary candidates [0, 1] without repeated scanning.
        """
        for idx in [0, 1]:
            cap = self._try_open_cap(idx)
            if cap is not None:
                print(f"[CameraCapture] Physical webcam found at index {idx}.")
                return idx, cap
        return None, None

    def start(self, auto_fallback=True):
        """
        Initializes VideoCapture stream once and starts thread-safe background frame reader loop.
        """
        if self.is_running:
            return True

        try:
            # 1-shot attempt at requested device index
            self.cap = self._try_open_cap(self.device_index)

            # Optional 1-pass fallback if requested device index failed
            if self.cap is None and auto_fallback:
                working_idx, working_cap = self.find_working_camera_index()
                if working_cap is not None:
                    self.device_index = working_idx
                    self.cap = working_cap

            if self.cap is not None and self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, self.fps)

                self.is_running = True
                self.thread = threading.Thread(target=self._reader_loop, daemon=True)
                self.thread.start()
                print(f"[CameraCapture] Physical webcam index {self.device_index} opened successfully ({self.width}x{self.height}).")
                return True

            print(f"[CameraCapture] Camera not detected. Using synthetic test pattern fallback.")
            return False

        except Exception as e:
            print(f"[CameraCapture] ERROR: Exception while opening camera: {e}")
            self.cap = None
            return False

    def _reader_loop(self):
        """Dedicated background thread reading frames continuously into RAM buffer."""
        while self.is_running and self.cap is not None and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()
                if ret and frame is not None and frame.size > 0 and frame.mean() > 3.0:
                    with self.lock:
                        self.current_frame = frame
                time.sleep(0.01)
            except Exception as e:
                time.sleep(0.05)

    def is_opened(self):
        """Checks if camera stream is active and opened."""
        return self.is_running and self.cap is not None and self.cap.isOpened()

    def read_frame(self):
        """
        Instant thread-safe read of the latest frame from memory buffer.
        """
        with self.lock:
            if self.current_frame is not None:
                return True, self.current_frame.copy()

        return False, self.create_synthetic_frame()

    def create_synthetic_frame(self):
        """Generates a visible, brightly-colored test card frame for standby mode when hardware camera is unavailable."""
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        # Slate Blue background gradient
        frame[:, :] = (80, 50, 30)
        # Yellow and Cyan bounding boxes
        cv2.rectangle(frame, (20, 20), (self.width - 20, self.height - 20), (0, 255, 255), 2)
        cv2.circle(frame, (self.width // 2, self.height // 2), 70, (0, 200, 255), 2)
        cv2.putText(frame, "📷 PROCTORING VIDEO STREAM ACTIVE", (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
        cv2.putText(frame, "Synthetic Test Pattern (Hardware Cam Fallback)", (40, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 220, 255), 1)
        cv2.putText(frame, f"Active Camera Index: {self.device_index}", (40, self.height - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
        return frame

    def stop(self):
        """Releases background thread and camera hardware resources safely."""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            try:
                self.thread.join(timeout=1.0)
            except Exception:
                pass
        self.thread = None

        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
            print("[CameraCapture] Webcam stream stopped and resources released.")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
