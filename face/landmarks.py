"""
Facial Landmark Extractor Module using MediaPipe Face Mesh
Extracts 468-478 3D facial landmarks and provides visual mesh debugging overlays.
"""

import cv2
import numpy as np
import mediapipe as mp


class FaceLandmarkExtractor:
    """
    Decoupled MediaPipe FaceMesh Landmark Extractor.
    """

    def __init__(
        self,
        max_num_faces=2,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ):
        self.max_num_faces = max_num_faces
        self.refine_landmarks = refine_landmarks
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence

        # MediaPipe Drawing and FaceMesh utilities
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.mp_face_mesh = mp.solutions.face_mesh

        # Initialize MediaPipe Face Mesh model
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=self.max_num_faces,
            refine_landmarks=self.refine_landmarks,
            min_detection_confidence=self.min_detection_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
        )

    def extract_landmarks(self, frame_bgr):
        """
        Processes BGR image frame and extracts face landmarks.
        Returns:
            telemetry (dict): Structured face landmark telemetry.
        """
        telemetry = {
            "face_detected": False,
            "faces_count": 0,
            "primary_landmarks": None,  # First face landmarks object
            "all_face_landmarks": [],   # List of all detected face landmarks
            "pixel_coordinates": [],    # [(x, y)] for primary face key points
            "status": "NO_FACE",
        }

        if frame_bgr is None or not isinstance(frame_bgr, np.ndarray) or frame_bgr.size == 0:
            telemetry["status"] = "INVALID_FRAME"
            return telemetry

        h, w, _ = frame_bgr.shape
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # Run MediaPipe Face Mesh inference
        results = self.face_mesh.process(frame_rgb)

        if not results or not results.multi_face_landmarks:
            return telemetry

        faces_count = len(results.multi_face_landmarks)
        telemetry["face_detected"] = True
        telemetry["faces_count"] = faces_count
        telemetry["all_face_landmarks"] = results.multi_face_landmarks
        telemetry["primary_landmarks"] = results.multi_face_landmarks[0]
        telemetry["status"] = "FACE_DETECTED"

        # Convert primary face landmarks to 2D pixel coordinates [(x, y)]
        primary = results.multi_face_landmarks[0]
        pixel_coords = []
        for lm in primary.landmark:
            px, py = int(lm.x * w), int(lm.y * h)
            pixel_coords.append((px, py))
        telemetry["pixel_coordinates"] = pixel_coords

        return telemetry

    def draw_landmarks(self, frame_bgr, telemetry, draw_tessellation=True, draw_contours=True, draw_irises=True):
        """
        Renders MediaPipe FaceMesh debug overlays (mesh tessellation, contours, irises) on frame.
        """
        if frame_bgr is None or not telemetry.get("face_detected"):
            return frame_bgr

        annotated_frame = frame_bgr.copy()
        all_faces = telemetry.get("all_face_landmarks", [])

        for face_landmarks in all_faces:
            # 1. Draw Mesh Tessellation
            if draw_tessellation:
                tess_conn = getattr(self.mp_face_mesh, "FACEMESH_TESSELATION", getattr(self.mp_face_mesh, "FACEMESH_TESSELLATION", None))
                tess_style = getattr(self.mp_drawing_styles, "get_default_face_mesh_tesselation_style", getattr(self.mp_drawing_styles, "get_default_face_mesh_tessellation_style", None))
                if tess_conn and tess_style:
                    self.mp_drawing.draw_landmarks(
                        image=annotated_frame,
                        landmark_list=face_landmarks,
                        connections=tess_conn,
                        landmark_drawing_spec=None,
                        connection_drawing_spec=tess_style(),
                    )

            # 2. Draw Facial Contours (Eyes, Lips, Eyebrows, Face Oval)
            if draw_contours:
                self.mp_drawing.draw_landmarks(
                    image=annotated_frame,
                    landmark_list=face_landmarks,
                    connections=self.mp_face_mesh.FACEMESH_CONTOURS,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_contours_style(),
                )

            # 3. Draw Iris Connections (Landmarks 468-477)
            if draw_irises and self.refine_landmarks:
                self.mp_drawing.draw_landmarks(
                    image=annotated_frame,
                    landmark_list=face_landmarks,
                    connections=self.mp_face_mesh.FACEMESH_IRISES,
                    landmark_drawing_spec=None,
                    connection_drawing_spec=self.mp_drawing_styles.get_default_face_mesh_iris_connections_style(),
                )

        return annotated_frame

    def close(self):
        """Releases MediaPipe resources."""
        if hasattr(self, "face_mesh") and self.face_mesh:
            self.face_mesh.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
