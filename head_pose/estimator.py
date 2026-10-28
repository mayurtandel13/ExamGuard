"""
Head Pose Estimation Module using MediaPipe FaceMesh and OpenCV solvePnP
Estimates 3D Head Orientation (Pitch, Yaw, Roll), detects off-center movements,
and uses a sliding time window to identify repeated suspicious head movements.
"""

import time
from collections import deque
import cv2
import numpy as np
import mediapipe as mp
from config import HEAD_POSE_CONFIG


class HeadPoseEstimator:
    """
    Decoupled Head Pose Estimator utilizing MediaPipe Face Mesh & OpenCV solvePnP.
    """

    def __init__(
        self,
        yaw_threshold=HEAD_POSE_CONFIG["YAW_THRESHOLD_DEG"],
        pitch_threshold=HEAD_POSE_CONFIG["PITCH_THRESHOLD_DEG"],
        roll_threshold=HEAD_POSE_CONFIG["ROLL_THRESHOLD_DEG"],
        window_seconds=5.0,
        min_repeated_movements=3,
    ):
        self.yaw_threshold = yaw_threshold
        self.pitch_threshold = pitch_threshold
        self.roll_threshold = roll_threshold
        self.window_seconds = window_seconds
        self.min_repeated_movements = min_repeated_movements

        # Sliding window buffer to track off-center movement timestamps
        self.movement_history = deque()

        # MediaPipe FaceMesh Engine
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=2,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        # 3D Generic Anthropometric Face Model Points (in millimeters)
        self.model_points = np.array(
            [
                (0.0, 0.0, 0.0),          # Nose tip (Landmark 1)
                (0.0, -330.0, -65.0),     # Chin (Landmark 152)
                (-225.0, 170.0, -135.0),  # Left eye outer corner (Landmark 33)
                (225.0, 170.0, -135.0),   # Right eye outer corner (Landmark 263)
                (-150.0, -150.0, -125.0), # Left mouth corner (Landmark 61)
                (150.0, -150.0, -125.0),  # Right mouth corner (Landmark 291)
            ],
            dtype=np.float64,
        )

        # Landmark indices corresponding to 3D model points
        self.landmark_indices = [1, 152, 33, 263, 61, 291]

    def process_frame(self, frame_bgr):
        """
        Analyzes BGR frame for 3D Head Pose (Pitch, Yaw, Roll).
        Returns structured telemetry dictionary with status, timestamp, and alerts.
        """
        now = time.time()
        telemetry = {
            "timestamp": now,
            "face_detected": False,
            "pitch": 0.0,
            "yaw": 0.0,
            "roll": 0.0,
            "status": "NO_FACE",
            "deviation_score": 0.0,
            "landmark_points": None,
            "nose_2d": None,
            "nose_proj_2d": None,
            "faces_count": 0,
            "active_events": [],
            "repeated_movement_detected": False,
        }

        if frame_bgr is None or not isinstance(frame_bgr, np.ndarray) or frame_bgr.size == 0:
            telemetry["status"] = "INVALID_FRAME"
            return telemetry

        h, w, _ = frame_bgr.shape
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(frame_rgb)

        if not results or not results.multi_face_landmarks:
            return telemetry

        telemetry["faces_count"] = len(results.multi_face_landmarks)
        telemetry["face_detected"] = True

        # Extract primary face landmarks
        face_landmarks = results.multi_face_landmarks[0]
        telemetry["landmark_points"] = face_landmarks

        # Extract 2D pixel coordinates for the 6 key facial landmarks
        image_points = []
        for idx in self.landmark_indices:
            lm = face_landmarks.landmark[idx]
            x, y = int(lm.x * w), int(lm.y * h)
            image_points.append((x, y))

        image_points = np.array(image_points, dtype=np.float64)

        # Camera Intrinsic Parameters (Focal length ~ width of image)
        focal_length = float(w)
        center = (w / 2.0, h / 2.0)
        camera_matrix = np.array(
            [[focal_length, 0, center[0]], [0, focal_length, center[1]], [0, 0, 1]],
            dtype=np.float64,
        )
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        # Solve Perspective-n-Point (solvePnP)
        success, rvec, tvec = cv2.solvePnP(
            self.model_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )

        if not success:
            telemetry["status"] = "CALCULATION_FAILED"
            return telemetry

        # Convert rotation vector to rotation matrix
        rmat, _ = cv2.Rodrigues(rvec)

        # Decompose rotation matrix to extract Euler angles (Pitch, Yaw, Roll)
        proj_matrix = np.hstack((rmat, tvec))
        _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(proj_matrix)

        pitch = float(euler_angles[0][0])
        yaw = float(euler_angles[1][0])
        roll = float(euler_angles[2][0])

        # Normalize angles to range [-180, 180]
        pitch = pitch if abs(pitch) <= 180 else pitch % 180
        yaw = yaw if abs(yaw) <= 180 else yaw % 180
        roll = roll if abs(roll) <= 180 else roll % 180

        telemetry["pitch"] = pitch
        telemetry["yaw"] = yaw
        telemetry["roll"] = roll

        # 3D Nose direction projection vector
        nose_end_point3D = np.array([(0.0, 0.0, 500.0)], dtype=np.float64)
        nose_end_point2D, _ = cv2.projectPoints(
            nose_end_point3D, rvec, tvec, camera_matrix, dist_coeffs
        )
        telemetry["nose_2d"] = (int(image_points[0][0]), int(image_points[0][1]))
        telemetry["nose_proj_2d"] = (
            int(nose_end_point2D[0][0][0]),
            int(nose_end_point2D[0][0][1]),
        )

        # Evaluate significant head direction movement
        yaw_ratio = abs(yaw) / self.yaw_threshold
        pitch_ratio = abs(pitch) / self.pitch_threshold
        deviation_score = min(1.0, max(yaw_ratio, pitch_ratio))
        telemetry["deviation_score"] = float(deviation_score)

        if yaw < -self.yaw_threshold:
            status = "LOOKING_RIGHT"
        elif yaw > self.yaw_threshold:
            status = "LOOKING_LEFT"
        elif pitch < -self.pitch_threshold:
            status = "LOOKING_DOWN"
        elif pitch > self.pitch_threshold:
            status = "LOOKING_UP"
        else:
            status = "FORWARD"

        telemetry["status"] = status

        # Sliding Time Window for Repeated Head Movement Detection
        if status != "FORWARD":
            self.movement_history.append((now, status))

        # Evict movements outside the time window
        while self.movement_history and (now - self.movement_history[0][0]) > self.window_seconds:
            self.movement_history.popleft()

        movement_count = len(self.movement_history)
        if movement_count >= self.min_repeated_movements:
            telemetry["repeated_movement_detected"] = True
            event = {
                "type": "REPEATED_HEAD_MOVEMENT",
                "severity": "MEDIUM",
                "message": f"Suspicious repeated head movement detected ({movement_count} occurrences in {self.window_seconds}s window)",
                "timestamp": now,
                "details": {
                    "movement_count": movement_count,
                    "window_seconds": self.window_seconds,
                    "latest_status": status,
                },
            }
            telemetry["active_events"].append(event)

        return telemetry

    def close(self):
        """Releases MediaPipe resources."""
        if hasattr(self, "face_mesh") and self.face_mesh:
            self.face_mesh.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

