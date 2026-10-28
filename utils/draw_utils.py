"""
Visualization Utilities for Webcam Video Annotations & Overlays
"""

import cv2
import numpy as np


def draw_head_pose_arrow(frame, head_tel):
    """Draws 3D direction vector from nose tip."""
    if not head_tel.get("face_detected"):
        return frame

    nose_2d = head_tel.get("nose_2d")
    nose_proj_2d = head_tel.get("nose_proj_2d")

    if nose_2d and nose_proj_2d:
        cv2.arrowedLine(
            frame,
            nose_2d,
            nose_proj_2d,
            (0, 255, 255),
            2,
            tipLength=0.2,
        )

    # Text telemetry
    yaw = head_tel.get("yaw", 0.0)
    pitch = head_tel.get("pitch", 0.0)
    status = head_tel.get("status", "NORMAL")

    cv2.putText(
        frame,
        f"Head: {status} (Y:{yaw:.0f} P:{pitch:.0f})",
        (15, 65),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2,
    )
    return frame


def draw_yolo_detections(frame, yolo_tel):
    """Draws bounding boxes for detected persons and mobile phones."""
    detections = yolo_tel.get("detections", [])

    for det in detections:
        box = det["box"]
        cls_name = det["class_name"].upper()
        conf = det["confidence"]

        if cls_name == "CELL PHONE":
            color = (0, 0, 255)  # Red for phone violation
            label = f"ALERT: MOBILE PHONE ({conf*100:.0f}%)"
        else:
            color = (255, 191, 0)  # Cyan/Deep blue for person
            label = f"PERSON ({conf*100:.0f}%)"

        cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), color, 2)
        cv2.putText(
            frame,
            label,
            (box[0], max(20, box[1] - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
        )
    return frame


def draw_risk_banner(frame, fusion_res):
    """Draws top status bar with score, risk level badge, and active alerts."""
    h, w, _ = frame.shape
    score = fusion_res.get("cheating_probability_score", 0.0)
    risk_level = fusion_res.get("risk_level", "LOW")

    # Banner Background
    cv2.rectangle(frame, (0, 0), (w, 40), (20, 20, 20), -1)

    # Color mapping
    if risk_level == "LOW":
        badge_color = (0, 200, 80)    # Green
    elif risk_level == "MEDIUM":
        badge_color = (0, 215, 255)   # Yellow/Orange
    else:
        badge_color = (0, 0, 230)     # Bright Red

    # Risk Badge
    cv2.putText(
        frame,
        f"RISK: {risk_level}",
        (15, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        badge_color,
        2,
    )

    # Score Text
    score_text = f"Cheating Score: {score * 100:.1f}%"
    cv2.putText(
        frame,
        score_text,
        (w - 240, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        2,
    )

    # Score Bar
    bar_x_start = w - 240
    bar_width = 220
    bar_y = 32
    fill_width = int(bar_width * score)
    cv2.rectangle(frame, (bar_x_start, bar_y), (bar_x_start + bar_width, bar_y + 4), (80, 80, 80), -1)
    cv2.rectangle(frame, (bar_x_start, bar_y), (bar_x_start + fill_width, bar_y + 4), badge_color, -1)

    # Active Alerts Text Overlay at bottom of frame
    active_events = fusion_res.get("active_events", [])
    if active_events:
        alert_text = " | ".join([e["message"] for e in active_events[:2]])
        cv2.rectangle(frame, (0, h - 30), (w, h), (0, 0, 150), -1)
        cv2.putText(
            frame,
            f"⚠️ {alert_text}",
            (10, h - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1,
        )

    return frame
