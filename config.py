"""
System Configuration File
AI-Based Intelligent Exam Integrity and Behavioral Monitoring System
"""

import os

# --- Camera Settings ---
CAMERA_CONFIG = {
    "DEVICE_INDEX": 1,  # Index 1 is the active physical webcam (Index 0 returns dark standby frames)
    "FRAME_WIDTH": 640,
    "FRAME_HEIGHT": 480,
    "TARGET_FPS": 30,
}

# --- Head Pose Settings ---
HEAD_POSE_CONFIG = {
    "YAW_THRESHOLD_DEG": 25.0,
    "PITCH_THRESHOLD_DEG": 20.0,
    "ROLL_THRESHOLD_DEG": 20.0,
}

# --- Gaze Settings ---
GAZE_CONFIG = {
    "OFF_CENTER_THRESHOLD": 0.35,
    "EAR_BLINK_THRESHOLD": 0.18,
    "SUSTAINED_DISTRACTION_FRAMES": 15,
}

# --- YOLO Settings ---
YOLO_CONFIG = {
    "MODEL_NAME": "yolov8n.pt",
    "CONFIDENCE_THRESHOLD": 0.45,
    "PHONE_CLASS_ID": 67,
    "PERSON_CLASS_ID": 0,
}

# --- Keyboard Monitoring Settings ---
KEYBOARD_CONFIG = {
    "SUSPICIOUS_HOTKEYS": [
        "alt+tab",
        "ctrl+c",
        "ctrl+v",
        "win",
        "print_screen",
        "alt+f4",
    ],
    "EVENT_DECAY_SECONDS": 3.0,
}

# --- Behavioral Fusion & Risk Scoring ---
FUSION_CONFIG = {
    "WEIGHT_HEAD_POSE": 0.25,
    "WEIGHT_GAZE_DISTRACTION": 0.20,
    "WEIGHT_MOBILE_PHONE": 0.40,
    "WEIGHT_MULTI_PERSON": 0.35,
    "WEIGHT_KEYBOARD_SHORTCUT": 0.30,
    "EMA_ALPHA": 0.15,
    "RISK_THRESHOLD_LOW": 0.35,
    "RISK_THRESHOLD_MEDIUM": 0.70,
}

# --- Directory Paths ---
BASE_DIR = os.path.dirname(__file__)
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
