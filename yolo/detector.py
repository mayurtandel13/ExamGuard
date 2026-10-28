"""
YOLOv8 Object Detection Module using Ultralytics YOLO.
Detects cell phones and persons, extracts bounding boxes and confidence scores,
implements frame sampling optimization for real-time performance, and generates structured alert events.
"""

import time
import cv2
import numpy as np
from ultralytics import YOLO
from config import YOLO_CONFIG


class YOLOObjectDetector:
    """
    Decoupled YOLOv8 Object Detection Engine.
    Configurable for confidence threshold, sample interval, and target classes.
    """

    def __init__(
        self,
        model_name=YOLO_CONFIG["MODEL_NAME"],
        confidence_threshold=YOLO_CONFIG["CONFIDENCE_THRESHOLD"],
        phone_class_id=YOLO_CONFIG["PHONE_CLASS_ID"],
        person_class_id=YOLO_CONFIG["PERSON_CLASS_ID"],
        sample_interval=3,  # Run full inference every 3rd frame for real-time optimization
    ):
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.phone_class_id = phone_class_id
        self.person_class_id = person_class_id
        self.sample_interval = sample_interval

        self.frame_counter = 0
        self.cached_telemetry = None

        # Load YOLO model
        try:
            self.model = YOLO(self.model_name)
        except Exception as e:
            print(f"[YOLOObjectDetector] Warning: Error loading model '{self.model_name}': {e}")
            self.model = None

    def process_frame(self, frame_bgr):
        """
        Processes BGR image frame for Cell Phone and Person detection.
        Uses sample_interval caching to optimize real-time FPS.
        Returns structured telemetry dictionary.
        """
        now = time.time()
        self.frame_counter += 1

        # Return cached telemetry on skipped frames for real-time optimization
        if self.cached_telemetry is not None and (self.frame_counter % self.sample_interval != 0):
            telemetry = self.cached_telemetry.copy()
            telemetry["timestamp"] = now
            return telemetry

        telemetry = {
            "timestamp": now,
            "phone_detected": False,
            "phone_confidence": 0.0,
            "person_count": 0,
            "multi_person_detected": False,
            "detections": [],
            "active_events": [],
        }

        if frame_bgr is None or not isinstance(frame_bgr, np.ndarray) or frame_bgr.size == 0 or self.model is None:
            self.cached_telemetry = telemetry
            return telemetry

        # Run Ultralytics YOLOv8 inference
        results = self.model(frame_bgr, conf=self.confidence_threshold, verbose=False)

        if not results or len(results) == 0:
            self.cached_telemetry = telemetry
            return telemetry

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            self.cached_telemetry = telemetry
            return telemetry

        person_count = 0
        phone_detected = False
        max_phone_conf = 0.0
        phone_box = None

        for box in boxes:
            cls_id = int(box.cls[0].item())
            conf = float(box.conf[0].item())
            xyxy = box.xyxy[0].cpu().numpy().astype(int).tolist()

            class_name = self.model.names.get(cls_id, str(cls_id))

            detection_item = {
                "class_id": cls_id,
                "class_name": class_name,
                "confidence": round(conf, 3),
                "box": xyxy,  # [x1, y1, x2, y2]
            }

            if cls_id == self.person_class_id or class_name.lower() == "person":
                person_count += 1
                telemetry["detections"].append(detection_item)

            elif cls_id == self.phone_class_id or "phone" in class_name.lower() or "cell" in class_name.lower():
                phone_detected = True
                if conf > max_phone_conf:
                    max_phone_conf = conf
                    phone_box = xyxy
                telemetry["detections"].append(detection_item)

        telemetry["person_count"] = person_count
        telemetry["multi_person_detected"] = person_count > 1
        telemetry["phone_detected"] = phone_detected
        telemetry["phone_confidence"] = round(float(max_phone_conf), 3)

        # Generate Structured Alert Events (without asserting definite cheating)
        if phone_detected:
            event = {
                "type": "PHONE_DETECTED",
                "severity": "HIGH",
                "message": f"Mobile phone detected in frame (Confidence: {max_phone_conf * 100:.1f}%)",
                "timestamp": now,
                "details": {
                    "confidence": round(float(max_phone_conf), 3),
                    "box": phone_box,
                },
            }
            telemetry["active_events"].append(event)

        if person_count > 1:
            event = {
                "type": "MULTIPLE_PERSON_DETECTED",
                "severity": "HIGH",
                "message": f"Multiple persons detected in proctoring area (Count: {person_count})",
                "timestamp": now,
                "details": {
                    "person_count": person_count,
                },
            }
            telemetry["active_events"].append(event)

        self.cached_telemetry = telemetry
        return telemetry

    def reset(self):
        """Resets cached frame counter and telemetry state."""
        self.frame_counter = 0
        self.cached_telemetry = None

    def close(self):
        """Releases YOLO detector model resources."""
        self.reset()
        self.model = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


