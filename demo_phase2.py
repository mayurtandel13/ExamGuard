"""
Phase 2 Live Demonstration Script
Runs continuous webcam capture loop with MediaPipe FaceMesh debug overlays.
Press 'q' or ESC in opencv window to exit.
"""

import sys
import os
import cv2

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(__file__))

from config import CAMERA_CONFIG
from camera.capture import CameraCapture
from face.landmarks import FaceLandmarkExtractor


def main():
    print("=" * 60)
    print("  AI Exam Integrity System - Phase 2 Demonstration")
    print("  Webcam Capture & MediaPipe FaceMesh Foundation")
    print("=" * 60)

    # Initialize decoupled components using configured camera device index
    camera = CameraCapture(device_index=CAMERA_CONFIG["DEVICE_INDEX"])
    extractor = FaceLandmarkExtractor(max_num_faces=2, refine_landmarks=True)

    # Start webcam
    webcam_available = camera.start()
    if not webcam_available:
        print("[Demo] Hardware webcam not detected. Running synthetic frame test mode...")

    frame_count = 0

    try:
        while True:
            if webcam_available:
                success, frame = camera.read_frame()
                if not success:
                    print("[Demo] Camera read error encountered.")
                    break
            else:
                frame = camera.create_synthetic_frame()
                cv2.putText(
                    frame,
                    "SYNTHETIC TEST FRAME (No Camera)",
                    (50, 240),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                )

            frame_count += 1

            # Extract facial landmarks
            telemetry = extractor.extract_landmarks(frame)

            # Draw MediaPipe debug landmarks overlay
            annotated_frame = extractor.draw_landmarks(
                frame, telemetry, draw_tessellation=True, draw_contours=True, draw_irises=True
            )

            # Display Status Banner
            status = telemetry["status"]
            faces = telemetry["faces_count"]
            status_text = f"Status: {status} | Faces Detected: {faces}"
            color = (0, 255, 0) if telemetry["face_detected"] else (0, 0, 255)

            cv2.rectangle(annotated_frame, (0, 0), (640, 35), (20, 20, 20), -1)
            cv2.putText(
                annotated_frame,
                status_text,
                (15, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )

            if webcam_available:
                cv2.imshow("Phase 2 Demo - MediaPipe FaceMesh Debug", annotated_frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (27, ord("q")):  # ESC or 'q'
                    print("[Demo] User exited live view.")
                    break
            else:
                # In headless/synthetic test mode, run 10 loop iterations and finish
                if frame_count >= 10:
                    print(f"[Demo] Synthetic loop completed successfully ({frame_count} frames).")
                    break

    finally:
        camera.stop()
        extractor.close()
        cv2.destroyAllWindows()
        print("[Demo] Resources closed cleanly.")


if __name__ == "__main__":
    main()
