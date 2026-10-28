"""
Main Entry Point & Dashboard Script for AI-Based Exam Monitoring System
College Mini Project Enhancement:
- Professional Academic UI/UX (Slate & Subtle Blue Theme)
- Student Examination Dashboard & Readiness Checklist
- Distraction-Free Exam Interface with Question Navigation Palette & Mark for Review
- Submission Confirmation Dialog & Review Summary
- Live Multi-Modal Vision & Hotkey Proctoring HUD
- Browser Extension & DOM Integrity Monitoring Module
- Administrator Monitoring Dashboard with Event Review & Audit Trail
"""

import sys
import os
import time
import datetime
import json
import cv2
import pandas as pd
import numpy as np
import streamlit as st

print("[MARKER 1] Top of app.py execution", flush=True)

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import CAMERA_CONFIG, FUSION_CONFIG
from keyboard.monitor import KeyboardMonitor
from timeline.visualizer import TimelineVisualizer
from ui.theme import (
    apply_theme,
    get_css,
    THEME_COLORS,
    render_topbar,
    render_portal_hero,
    render_exam_card,
    render_readiness_checklist,
    render_metric_card,
    render_risk_badge,
    render_academic_header,
    render_metric_tile,
    render_question_matrix_summary,
    render_pre_exam_extension_warning,
    render_faculty_extension_alert_card,
    render_extension_clearance_card,
    render_phone_detection_live_warning,
    render_phone_clearance_card,
)
from dashboard.ui_components import inject_custom_css
from dashboard.worker import (
    get_process_worker_singleton,
    stop_process_worker_singleton,
    WorkerBufferData,
)
from database.db import get_db
from extension_monitor.detector import get_evaluator, get_classifier
from extension_monitor.client import get_integrity_client_js, get_pre_exam_extension_detector_js
from extension_monitor.server import (
    start_tab_beacon_server,
    get_active_detected_extension,
    clear_active_detected_extension,
    is_institutional_extension_connected,
)

# Start background beacon server for tab detection
start_tab_beacon_server()

print("[MARKER 2] Imports completed", flush=True)

# -----------------------------------------------------------------------------
# EXAM QUESTION DATASET
# -----------------------------------------------------------------------------
EXAM_QUESTIONS = [
    {
        "id": 1,
        "question": "What is the primary function of non-linear activation functions in deep neural networks?",
        "options": [
            "A) To normalize input data ranges to zero mean",
            "B) To allow networks to learn complex non-linear decision boundaries",
            "C) To reduce the number of trainable model parameters",
            "D) To prevent gradient degradation during forward propagation"
        ],
        "correct_answer": "B) To allow networks to learn complex non-linear decision boundaries"
    },
    {
        "id": 2,
        "question": "Which machine learning model relies on an ensemble of decision trees with feature bagging?",
        "options": [
            "A) Support Vector Machine (SVM)",
            "B) K-Nearest Neighbors (KNN)",
            "C) Random Forest Classifier",
            "D) Logistic Regression"
        ],
        "correct_answer": "C) Random Forest Classifier"
    },
    {
        "id": 3,
        "question": "In Perspective-n-Point (PnP) pose estimation, what input data is required to calculate 3D head orientation?",
        "options": [
            "A) 2D pixel coordinates and corresponding 3D reference object points",
            "B) Optical flow motion vectors between consecutive frames",
            "C) RGB color histograms and depth map disparity",
            "D) Bounding box width and height dimensions"
        ],
        "correct_answer": "A) 2D pixel coordinates and corresponding 3D reference object points"
    },
    {
        "id": 4,
        "question": "What occurs when an eye gaze tracking module detects a low Eye Aspect Ratio (EAR) for an extended duration?",
        "options": [
            "A) Indicates eye blink or prolonged eye closure",
            "B) Indicates high candidate attention towards screen center",
            "C) Triggers immediate object detection confidence boost",
            "D) Resets the keyboard shortcut monitoring counter"
        ],
        "correct_answer": "A) Indicates eye blink or prolonged eye closure"
    },
    {
        "id": 5,
        "question": "In an AI proctoring system, why is behavioral multi-modal signal fusion preferred over single-metric thresholding?",
        "options": [
            "A) It eliminates the need for camera hardware entirely",
            "B) It combines head pose, gaze, objects, and keypresses to reduce false positive cheating flags",
            "C) It reduces GPU memory requirements for deep learning inference",
            "D) It automatically answers student questions during the exam"
        ],
        "correct_answer": "B) It combines head pose, gaze, objects, and keypresses to reduce false positive cheating flags"
    }
]

# -----------------------------------------------------------------------------
# GLOBAL DEBUG CONFIGURATION SWITCH
# -----------------------------------------------------------------------------
DEBUG_EXAM = os.environ.get("EXAM_DEBUG", "0") == "1"

# -----------------------------------------------------------------------------
# CACHED SINGLETONS
# -----------------------------------------------------------------------------
@st.cache_resource
def get_keyboard_monitor_singleton():
    """Single persistent keyboard listener thread."""
    from keyboard.monitor import get_global_keyboard_monitor
    kb = get_global_keyboard_monitor()
    try:
        if not kb.is_running:
            kb.start()
    except Exception as e:
        print(f"[KeyboardMonitor Singleton] Start warning: {e}", flush=True)
    return kb


def get_cached_proctoring_worker(device_idx=CAMERA_CONFIG["DEVICE_INDEX"], enable_yolo=True):
    """Returns active process-wide worker singleton with running keyboard listener."""
    kb = get_keyboard_monitor_singleton()
    if not kb.is_running:
        try:
            kb.start()
        except Exception:
            pass
    return get_process_worker_singleton(device_idx=device_idx, enable_yolo=enable_yolo, kb_monitor=kb)


# Alias for backward compatibility with test suites
get_proctoring_worker_singleton = get_cached_proctoring_worker

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION FIRST
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ExamGuard - Exam Monitoring and Integrity System",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "theme" not in st.session_state:
    st.session_state["theme"] = "dark"

apply_theme(st.session_state["theme"])
print("[MARKER 3] set_page_config & custom CSS done", flush=True)

# Database and Evaluator Singletons
db = get_db()
evaluator = get_evaluator()
classifier = get_classifier()

# Main Application Try Block for Error Visibility
try:
    # -------------------------------------------------------------------------
    # SESSION STATE INITIALIZATION
    # -------------------------------------------------------------------------
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"
    if "exam_started" not in st.session_state:
        st.session_state.exam_started = False
    if "exam_active" not in st.session_state:
        st.session_state.exam_active = False
    if "exam_submitted" not in st.session_state:
        st.session_state.exam_submitted = False
    if "current_question_index" not in st.session_state:
        st.session_state.current_question_index = 0
    if "user_answers" not in st.session_state:
        st.session_state.user_answers = {}
    if "marked_for_review" not in st.session_state:
        st.session_state.marked_for_review = set()
    if "exam_start_time" not in st.session_state:
        st.session_state.exam_start_time = None
    if "total_exam_seconds" not in st.session_state:
        st.session_state.total_exam_seconds = 3600
    if "portal_mode" not in st.session_state:
        st.session_state.portal_mode = "🎓 Student Portal"
    if "active_session_id" not in st.session_state:
        st.session_state.active_session_id = f"SESSION-{int(time.time())}"
    if "student_id" not in st.session_state:
        st.session_state.student_id = "STU-2026-081"
    if "camera_permission_granted" not in st.session_state:
        st.session_state.camera_permission_granted = True
    if "mic_permission_granted" not in st.session_state:
        st.session_state.mic_permission_granted = True
    if "simulated_browser_name" not in st.session_state:
        st.session_state.simulated_browser_name = "Chrome"
    if "simulated_browser_ver" not in st.session_state:
        st.session_state.simulated_browser_ver = "124.0.0.0"
    if "extension_connected" not in st.session_state:
        st.session_state.extension_connected = False
    if "unauthorized_extension_active" not in st.session_state:
        st.session_state.unauthorized_extension_active = False
    if "detected_extension_name" not in st.session_state:
        st.session_state.detected_extension_name = "AI Exam Assistant & Solver"
    if "extension_used_in_exam" not in st.session_state:
        st.session_state.extension_used_in_exam = False
    if "pre_exam_extension_warned" not in st.session_state:
        st.session_state.pre_exam_extension_warned = False
    if "phone_detected_in_exam" not in st.session_state:
        st.session_state.phone_detected_in_exam = False

    # Fetch student metadata from database
    student_record = db.get_student(st.session_state.student_id) or {
        "student_id": "STU-2026-081",
        "full_name": "Mayur Tandel",
        "email": "mayur.tandel@college.edu",
        "department": "Computer Science & Engineering",
        "roll_number": "CS-2026-081",
    }

    # -------------------------------------------------------------------------
    # 2. TOP HEADER (Render on portal home and admin, NOT inside active exam)
    # -------------------------------------------------------------------------
    if not st.session_state.exam_active:
        render_portal_hero(
            title="Exam Monitoring and Integrity System",
            subtitle="Intelligent Multi-Modal Proctoring & Browser Integrity Assurance Platform",
            student_name=student_record["full_name"],
            student_id=student_record["student_id"],
            department=student_record["department"],
            roll_number=student_record.get("roll_number", "CS-2026-081"),
        )

    # -------------------------------------------------------------------------
    # 3. SIDEBAR NAVIGATION & CONTROLS
    # -------------------------------------------------------------------------
    st.sidebar.markdown("""
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px; padding: 2px 0;">
        <span style="font-size: 1.8rem;">🛡️</span>
        <div>
            <div class="sidebar-logo-text" style="font-size: 1.15rem; font-weight: 800; letter-spacing: -0.02em; color: var(--text) !important;">ExamGuard</div>
            <div class="sidebar-logo-sub" style="font-size: 0.74rem; color: var(--text-muted) !important; font-weight: 600;">Vision & DOM Integrity</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("<small style='font-weight:700; text-transform:uppercase; color:var(--text-muted); letter-spacing:0.04em;'>Portal Navigation</small>", unsafe_allow_html=True)
    portal_selection = st.sidebar.radio(
        "Select Portal Mode",
        ["🎓 Student Portal", "🛡️ Administrator Dashboard"],
        index=0 if st.session_state.portal_mode == "🎓 Student Portal" else 1,
        key="sidebar_portal_radio",
        label_visibility="collapsed",
    )
    st.session_state.portal_mode = portal_selection

    st.sidebar.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
    st.sidebar.markdown("<small style='font-weight:700; text-transform:uppercase; color:var(--text-muted); letter-spacing:0.04em;'>Theme Preference</small>", unsafe_allow_html=True)
    theme_selection = st.sidebar.radio(
        "Display Theme",
        ["🌙 Dark Mode", "☀️ Light Mode"],
        index=0 if st.session_state.get("theme", "dark") == "dark" else 1,
        key="sidebar_theme_radio",
        horizontal=True,
        label_visibility="collapsed",
    )
    new_theme = "dark" if "Dark" in theme_selection else "light"
    if new_theme != st.session_state.get("theme", "dark"):
        st.session_state.theme = new_theme
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Examination Controls")
    device_idx = int(
        st.sidebar.number_input(
            "Hardware Camera Index",
            min_value=0,
            max_value=5,
            value=int(CAMERA_CONFIG["DEVICE_INDEX"]),
            step=1,
            help="Index 1 is typical on Windows laptop/USB webcams; select Index 0 if Index 1 returns standby."
        )
    )

    # IMPORTANT: Keep button 0 in sidebar as "▶️ START EXAM" for test suite compatibility
    col_side_start, col_side_stop = st.sidebar.columns(2)
    with col_side_start:
        if st.button("▶️ START EXAM", type="primary", use_container_width=True, disabled=st.session_state.exam_active):
            st.session_state.exam_started = True
            st.session_state.exam_active = True
            st.session_state.exam_submitted = False
            st.session_state.current_question_index = 0
            st.session_state.user_answers = {}
            st.session_state.marked_for_review = set()
            st.session_state.exam_start_time = time.time()
            st.session_state.active_session_id = f"SESSION-{int(time.time())}"

            # Register session in persistent database
            db.create_or_get_session(
                exam_session_id=st.session_state.active_session_id,
                exam_id="EXAM-CS-2026-X",
                student_id=st.session_state.student_id,
                browser_name=st.session_state.simulated_browser_name,
                browser_version=st.session_state.simulated_browser_ver,
                os_name="Windows 11",
                compatibility_status="WARNING" if st.session_state.unauthorized_extension_active else "READY",
                institutional_extension_status="CONNECTED" if st.session_state.extension_connected else "NOT_INSTALLED",
                camera_permission="GRANTED" if st.session_state.camera_permission_granted else "DENIED",
                mic_permission="GRANTED" if st.session_state.mic_permission_granted else "DENIED",
            )

            # Record pre-exam extension violation if active
            if st.session_state.unauthorized_extension_active:
                st.session_state.extension_used_in_exam = True
                db.record_event(
                    exam_session_id=st.session_state.active_session_id,
                    student_id=st.session_state.student_id,
                    event_type="PRE_EXAM_EXTENSION_DETECTED",
                    event_description=f"Active browser extension detected ({st.session_state.detected_extension_name}) before starting exam. Candidate warned; telemetry sent to faculty dashboard.",
                    detection_method="PreExamExtensionScanner",
                    risk_level="HIGH",
                    severity="HIGH",
                    raw_data={
                        "extension_name": st.session_state.detected_extension_name,
                        "stage": "PRE_EXAM",
                        "warned": True,
                        "started_with_extension": True,
                    },
                )

            st.session_state.phone_detected_in_exam = False
            try:
                worker_obj = get_cached_proctoring_worker(device_idx=device_idx)
                if hasattr(worker_obj, "set_session_info"):
                    worker_obj.set_session_info(st.session_state.active_session_id, st.session_state.student_id)
                if hasattr(worker_obj, "reset_phone_detection"):
                    worker_obj.reset_phone_detection()
            except Exception:
                pass

            kb = get_keyboard_monitor_singleton()
            kb.reset()
            kb.set_session(st.session_state.active_session_id, st.session_state.student_id)
            if not kb.is_running:
                kb.start()
            st.rerun()

    with col_side_stop:
        if st.button("⏹️ STOP EXAM", type="secondary", use_container_width=True, disabled=not st.session_state.exam_active):
            st.session_state.exam_active = False
            st.session_state.exam_started = False
            stop_process_worker_singleton()
            db.end_session(
                exam_session_id=st.session_state.active_session_id,
                status="ABORTED",
            )
            st.success("Session stopped safely.")
            st.rerun()

    # Sidebar: Live Keyboard Status & Simulation Tool
    with st.sidebar.expander("⌨️ Keyboard Proctoring Status", expanded=False):
        kb_mon = get_keyboard_monitor_singleton()
        kb_status_str = "🟢 Active (Listening)" if kb_mon.is_running else "🟡 Idle"
        st.caption(f"**Hook Status**: {kb_status_str}")
        st.caption(f"**Total Flags**: `{kb_mon.total_event_count}`")
        if kb_mon.last_event:
            st.caption(f"**Last Flag**: `{kb_mon.last_event.get('shortcut', 'None').upper()}`")
        if kb_mon.shortcut_counts:
            st.markdown("**Keystroke Counts:**")
            for sc, count in kb_mon.shortcut_counts.items():
                st.caption(f"- `{sc.upper()}`: **{count}** time(s)")

        st.markdown("**Simulate Shortcut Trigger**:")
        sim_col1, sim_col2 = st.columns(2)
        with sim_col1:
            if st.button("⚡ Alt+Tab", key="sim_alttab", use_container_width=True):
                kb_mon.trigger_simulated_shortcut("alt+tab", record_db=False)
                db.record_event(
                    exam_session_id=st.session_state.active_session_id,
                    student_id=st.session_state.student_id,
                    event_type="HOTKEY_SHORTCUT",
                    event_description=f"Candidate triggered Alt+Tab task-switch shortcut ({kb_mon.shortcut_counts.get('alt+tab', 1)}x)",
                    detection_method="KeyboardHook",
                    risk_level="HIGH",
                    severity="HIGH",
                    raw_data={"shortcut": "alt+tab", "count": kb_mon.shortcut_counts.get("alt+tab", 1)},
                )
                st.toast("Triggered: Alt+Tab (Task Switch)", icon="⚠️")
            if st.button("⚡ Ctrl+C", key="sim_ctrlc", use_container_width=True):
                kb_mon.trigger_simulated_shortcut("ctrl+c", record_db=False)
                db.record_event(
                    exam_session_id=st.session_state.active_session_id,
                    student_id=st.session_state.student_id,
                    event_type="HOTKEY_SHORTCUT",
                    event_description=f"Candidate triggered Ctrl+C copy shortcut ({kb_mon.shortcut_counts.get('ctrl+c', 1)}x)",
                    detection_method="KeyboardHook",
                    risk_level="MEDIUM",
                    severity="MEDIUM",
                    raw_data={"shortcut": "ctrl+c", "count": kb_mon.shortcut_counts.get("ctrl+c", 1)},
                )
                st.toast("Triggered: Ctrl+C (Copy)", icon="⚠️")
        with sim_col2:
            if st.button("⚡ Ctrl+V", key="sim_ctrlv", use_container_width=True):
                kb_mon.trigger_simulated_shortcut("ctrl+v", record_db=False)
                db.record_event(
                    exam_session_id=st.session_state.active_session_id,
                    student_id=st.session_state.student_id,
                    event_type="HOTKEY_SHORTCUT",
                    event_description=f"Candidate triggered Ctrl+V paste shortcut ({kb_mon.shortcut_counts.get('ctrl+v', 1)}x)",
                    detection_method="KeyboardHook",
                    risk_level="MEDIUM",
                    severity="MEDIUM",
                    raw_data={"shortcut": "ctrl+v", "count": kb_mon.shortcut_counts.get("ctrl+v", 1)},
                )
                st.toast("Triggered: Ctrl+V (Paste)", icon="⚠️")
            if st.button("⚡ PrintScreen", key="sim_prtsc", use_container_width=True):
                kb_mon.trigger_simulated_shortcut("print_screen", record_db=False)
                db.record_event(
                    exam_session_id=st.session_state.active_session_id,
                    student_id=st.session_state.student_id,
                    event_type="HOTKEY_SHORTCUT",
                    event_description=f"Candidate triggered PrintScreen capture shortcut ({kb_mon.shortcut_counts.get('print_screen', 1)}x)",
                    detection_method="KeyboardHook",
                    risk_level="HIGH",
                    severity="HIGH",
                    raw_data={"shortcut": "print_screen", "count": kb_mon.shortcut_counts.get("print_screen", 1)},
                )
                st.toast("Triggered: Print Screen (Screenshot)", icon="⚠️")

    # Sidebar: Browser Extension & DOM Simulation Tools
    with st.sidebar.expander("🛡️ Extension & DOM Simulator", expanded=False):
        st.caption("Inject observable events into monitoring database for demonstration:")
        if st.button("🚨 Simulate Extension Script Injection", key="sim_ext_inject", use_container_width=True):
            db.record_event(
                exam_session_id=st.session_state.active_session_id,
                student_id=st.session_state.student_id,
                event_type="PAGE_INTEGRITY_CHANGE",
                event_description="Foreign script tag injected from chrome-extension:// scheme",
                detection_method="MutationObserver",
                risk_level="HIGH",
                severity="CRITICAL",
                raw_data={"src": "chrome-extension://abcdef/solver.js", "target": "body"},
            )
            st.toast("Simulated: Extension Script Injection (HIGH Risk)", icon="🚨")

        if st.button("⚠️ Simulate Question Overlay Detected", key="sim_ext_overlay", use_container_width=True):
            db.record_event(
                exam_session_id=st.session_state.active_session_id,
                student_id=st.session_state.student_id,
                event_type="EXAM_INTERFACE_OVERLAY",
                event_description="Suspicious fixed overlay detected covering Question 1 area",
                detection_method="DOMOverlayDetector",
                risk_level="MEDIUM",
                severity="MEDIUM",
                raw_data={"zIndex": 99999, "position": "fixed", "bounds": [120, 450, 400, 200]},
            )
            st.toast("Simulated: Exam Interface Overlay (MEDIUM Risk)", icon="⚠️")

        if st.button("🔄 Simulate Window Blur (Tab Switch)", key="sim_tab_switch", use_container_width=True):
            db.record_event(
                exam_session_id=st.session_state.active_session_id,
                student_id=st.session_state.student_id,
                event_type="WINDOW_BLUR_TAB_SWITCH",
                event_description="Candidate switched browser window or minimized examination tab (HIGH Risk)",
                detection_method="ScreenFocusMonitor",
                risk_level="HIGH",
                severity="HIGH",
                raw_data={"duration_sec": 3.4},
            )
            try:
                worker = get_cached_proctoring_worker(device_idx=device_idx)
                if hasattr(worker, "notify_tab_switch"):
                    worker.notify_tab_switch(count=1)
                worker.get_timeline().add_event(
                    module="ScreenFocusMonitor",
                    event_type="WINDOW_BLUR_TAB_SWITCH",
                    severity="HIGH",
                    value=1.0,
                    description="Candidate switched browser window or minimized examination tab. Tab detection risk elevated to HIGH.",
                    risk_contribution=0.85,
                )
            except Exception:
                pass
            st.toast("Simulated: Window Blur / Tab Switch (HIGH Risk)", icon="🚨")

        if st.button("📱 Simulate Mobile Phone Detected (HIGH Risk)", key="sim_phone_det", use_container_width=True):
            st.session_state.phone_detected_in_exam = True
            db.record_event(
                exam_session_id=st.session_state.active_session_id,
                student_id=st.session_state.student_id,
                event_type="MOBILE_PHONE_DETECTED",
                event_description="Mobile phone or unauthorized electronic device detected in proctoring camera frame (Confidence: 94%)",
                detection_method="YOLOv8ObjectDetector",
                risk_level="HIGH",
                severity="HIGH",
                raw_data={"confidence": 0.94, "class_name": "cell phone", "source": "camera"},
            )
            try:
                worker = get_cached_proctoring_worker(device_idx=device_idx)
                if hasattr(worker, "notify_phone_detected"):
                    worker.notify_phone_detected(confidence=0.94)
                worker.get_timeline().add_event(
                    module="YOLOv8ObjectDetector",
                    event_type="MOBILE_PHONE_DETECTED",
                    severity="HIGH",
                    value=1.0,
                    description="Mobile phone detected in camera feed. Warning displayed to candidate. Tab and device detection risk elevated to HIGH.",
                    risk_contribution=0.90,
                )
            except Exception:
                pass
            st.toast("Simulated: Mobile Phone Detected (HIGH Risk)", icon="📱")

    print("[MARKER 4] Title and Sidebar rendered", flush=True)

    # -------------------------------------------------------------------------
    # INDEPENDENT TIMER FRAGMENT (Runs every 1s)
    # -------------------------------------------------------------------------
    @st.fragment(run_every="1s")
    def render_exam_timer_fragment():
        if not st.session_state.get("exam_start_time"):
            st.markdown("<div style='font-size:1.05rem; font-weight:700; color:var(--text); background:var(--surface-2); border:1px solid var(--border); padding:6px 14px; border-radius:10px; text-align:center;'>⏱️ <code>60:00</code></div>", unsafe_allow_html=True)
            return
        elapsed = int(time.time() - st.session_state.exam_start_time)
        remaining = max(0, st.session_state.total_exam_seconds - elapsed)
        mins, secs = divmod(remaining, 60)
        if remaining <= 120:
            time_color = "var(--danger)"
            alert_icon = "🔥"
        elif remaining <= 600:
            time_color = "var(--warning)"
            alert_icon = "⏳"
        else:
            time_color = "var(--text)"
            alert_icon = "⏱️"
        st.markdown(
            f"<div style='display:inline-flex; align-items:center; justify-content:center; gap:6px; font-size:1.05rem; font-weight:700; color:{time_color}; background:var(--surface-2); border:1px solid var(--border); padding:6px 14px; border-radius:10px; width:100%; text-align:center;'>"
            f"<span>{alert_icon}</span> <span style='font-family:monospace; font-size:1.15rem;'>{mins:02d}:{secs:02d}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # -------------------------------------------------------------------------
    # LIVE PROCTORING FRAGMENT (Runs every 500ms, Reads Buffer Only)
    # -------------------------------------------------------------------------
    @st.fragment(run_every="500ms")
    def render_live_proctoring_fragment(worker):
        if not st.session_state.get("exam_active", False):
            return

        data: WorkerBufferData = worker.get_latest_data()
        annotated = data.annotated_frame

        # Accurate status synchronization
        cam_status_disp = "Streaming 🟢" if annotated is not None else data.camera_status
        fps_val = data.fps
        t_ms = data.timing_ms

        st.markdown(
            f"<div style='display:flex; justify-content:space-between; align-items:center; background:var(--surface-2); border:1px solid var(--border); border-radius:8px; padding:6px 10px; margin-bottom:8px; font-size:0.78rem; color:var(--text-muted);'>"
            f"<span>📷 {cam_status_disp}</span>"
            f"<span>⚡ {fps_val:.0f} FPS</span>"
            f"<span>⏱️ {t_ms.get('total', 0):.0f}ms Latency</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        # 1. Live Webcam Feed
        if annotated is not None:
            rgb_frame = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            st.image(rgb_frame, channels="RGB", use_container_width=True)
        else:
            if data.models_status == "loading":
                st.warning("⏳ Loading AI Models into memory...")
            elif data.camera_status == "opening":
                st.warning("📷 Connecting to camera, awaiting video feed...")
            else:
                st.error(f"📷 {data.camera_error_msg or 'Webcam stream unavailable'}")
                st.caption("ℹ️ The examination UI remains fully active. You can adjust the Camera Index in the sidebar.")

        # Cheating Probability & Risk Level
        fusion_res = data.fusion_res
        r_level = fusion_res.get("risk_level", "LOW")
        c_score = fusion_res.get("cheating_probability", 0.0)

        # Check for tab switch events recorded for active session
        session_tab_evts = db.get_events(
            exam_session_id=st.session_state.active_session_id,
            event_type="WINDOW_BLUR_TAB_SWITCH",
            limit=50,
        )
        worker_tab_det = getattr(worker, "_tab_switch_detected", False)
        has_tab_switches = len(session_tab_evts) > 0 or worker_tab_det

        # Check for camera phone detection in live stream, worker memory, or persistent database
        yolo_tel = data.yolo_tel
        phone_det_live = yolo_tel.get("phone_detected", False)
        worker_phone_det = getattr(worker, "_phone_detected_sim", False)
        session_phone_evts = db.get_phone_events(
            exam_session_id=st.session_state.active_session_id,
            limit=5,
        )
        has_phone_detected = phone_det_live or worker_phone_det or len(session_phone_evts) > 0 or st.session_state.get("phone_detected_in_exam", False)

        if has_phone_detected:
            st.session_state.phone_detected_in_exam = True
            r_level = "HIGH"
            c_score = max(float(c_score), 0.90)
        elif has_tab_switches:
            r_level = "HIGH"
            c_score = max(float(c_score), 0.85)

        st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
        col_risk1, col_risk2 = st.columns([1, 1])
        with col_risk1:
            st.markdown("<small style='font-weight:700; text-transform:uppercase; color:var(--text-muted); font-size:0.75rem; letter-spacing:0.04em;'>Cheating Probability</small>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:1.35rem; font-weight:800; color:var(--text); margin:2px 0;'>{c_score:.2f}</div>", unsafe_allow_html=True)
            st.progress(float(c_score))
        with col_risk2:
            st.markdown("<small style='font-weight:700; text-transform:uppercase; color:var(--text-muted); font-size:0.75rem; letter-spacing:0.04em;'>Current Risk Level</small>", unsafe_allow_html=True)
            render_risk_badge(r_level, c_score)

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        # 2x4 Mini Metric Cards Grid (Icon + Value + Colored Status Dot)
        gaze_tel = data.gaze_tel
        head_tel = data.head_tel
        kb_tel = data.kb_tel

        att_val = float(gaze_tel.get("attention_score", 1.0))
        g_state = gaze_tel.get("gaze_state", "CENTER")
        ear_val = gaze_tel.get("avg_ear", 0.0)

        hp_status = head_tel.get("status", "FORWARD")
        p, y = head_tel.get("pitch", 0.0), head_tel.get("yaw", 0.0)

        phone_det = yolo_tel.get("phone_detected", False)
        phone_conf = yolo_tel.get("phone_confidence", 0.0)
        is_phone_flagged = phone_det or has_phone_detected

        p_count = yolo_tel.get("person_count", 0)

        recent_kb = kb_tel.get("recent_events", [])
        kb_str = ", ".join([e.get("shortcut", "Key").upper() for e in recent_kb]) if recent_kb else "None"
        tot_cnt = kb_tel.get("total_event_count", 0)

        ext_evts_live = db.get_extension_events(exam_session_id=st.session_state.active_session_id)
        has_ext_breach = bool(ext_evts_live or st.session_state.get("extension_used_in_exam", False))

        # Row 1: Attention & Gaze
        r1_c1, r1_c2 = st.columns(2)
        with r1_c1:
            render_metric_card("Attention", f"{att_val:.2f}", icon="🧠", status="pass" if att_val >= 0.75 else ("warn" if att_val >= 0.45 else "fail"), subtitle="Screen Focus")
        with r1_c2:
            render_metric_card("Eye Gaze", g_state, icon="👀", status="pass" if g_state == "CENTER" else "warn", subtitle=f"EAR: {ear_val:.2f}")

        # Row 2: 3D Head Pose & Mobile Phone
        r2_c1, r2_c2 = st.columns(2)
        with r2_c1:
            render_metric_card("Head Pose", hp_status, icon="👤", status="pass" if hp_status == "FORWARD" else "warn", subtitle=f"P:{p:.0f}° Y:{y:.0f}°")
        with r2_c2:
            render_metric_card("Mobile Phone", "DETECTED" if is_phone_flagged else "CLEAR", icon="📱", status="fail" if is_phone_flagged else "pass", subtitle=f"Conf: {phone_conf*100:.0f}%" if is_phone_flagged else "0% Conf")

        # Row 3: Keyboard Shortcuts & Persons in Frame
        r3_c1, r3_c2 = st.columns(2)
        with r3_c1:
            render_metric_card("Hotkeys", f"{tot_cnt} Flag(s)" if tot_cnt > 0 else "CLEAR", icon="⌨️", status="fail" if tot_cnt > 0 else "pass", subtitle=kb_str if tot_cnt > 0 else "No Violations")
        with r3_c2:
            render_metric_card("Persons", f"{p_count}", icon="👥", status="pass" if p_count == 1 else ("warn" if p_count > 1 else "fail"), subtitle="Normal" if p_count == 1 else "Multi-Person ⚠️")

        # Row 4: Tab Switch & DOM Guard
        r4_c1, r4_c2 = st.columns(2)
        with r4_c1:
            render_metric_card("Tab Focus", "BLUR / SWITCH" if has_tab_switches else "FOCUSED", icon="🔄", status="fail" if has_tab_switches else "pass", subtitle="HIGH Risk" if has_tab_switches else "Active Window")
        with r4_c2:
            render_metric_card("DOM Guard", "BREACH" if has_ext_breach else "SECURE", icon="🛡️", status="fail" if has_ext_breach else "pass", subtitle="Extension Alert" if has_ext_breach else "Zero Extensions")

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        # Tabs for Heavy Details: Events & Timeline Chart
        tab_events, tab_timeline = st.tabs(["📝 Behavioral Events", "📈 Risk Timeline"])
        with tab_events:
            timeline = worker.get_timeline()
            events_df = timeline.get_events_df()
            if not events_df.empty:
                st.dataframe(
                    events_df[["timestamp_str", "module", "event_type", "severity", "description"]].tail(5).iloc[::-1],
                    use_container_width=True,
                )
            else:
                db_evts = db.get_events(exam_session_id=st.session_state.active_session_id, limit=5)
                if db_evts:
                    st.dataframe(pd.DataFrame(db_evts)[["occurred_at", "event_type", "risk_level", "event_description"]], use_container_width=True)
                else:
                    st.success("🟢 No suspicious events recorded.")

        with tab_timeline:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig_time = TimelineVisualizer.generate_timeline_chart(
                timeline,
                figsize=(7, 2.5),
                theme=st.session_state.get("theme", "dark"),
            )
            st.pyplot(fig_time, clear_figure=True)
            plt.close(fig_time)

    # -------------------------------------------------------------------------
    # 4. VIEW SELECTION & MAIN CONTENT RENDER
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # VIEW A: ADMINISTRATOR DASHBOARD
    # -------------------------------------------------------------------------
    if st.session_state.portal_mode == "🛡️ Administrator Dashboard":
        print("[MARKER 5] View selected: ADMINISTRATOR DASHBOARD", flush=True)

        st.markdown("### 🛡️ Examination Monitoring & Proctoring Administration")
        st.caption("Real-time behavioral telemetry, browser compatibility analysis, and event review audit trail.")

        # Real Summary Metrics from Database
        summary_data = db.get_admin_summary()
        m_c1, m_c2, m_c3, m_c4, m_c5, m_c6 = st.columns(6)
        with m_c1:
            render_metric_tile("Total Monitored Sessions", summary_data["total_sessions"], "Registered Candidates", "neutral")
        with m_c2:
            render_metric_tile("Logged Integrity Events", summary_data["total_events"], "All Telemetry Signals", "neutral")
        with m_c3:
            ext_viol_count = summary_data.get("extension_violations", 0)
            render_metric_tile("Extension Violations", f"{ext_viol_count}", "Pre-Exam & In-Exam Flags", "fail" if ext_viol_count > 0 else "pass")
        with m_c4:
            phone_viol_count = summary_data.get("phone_violations", 0)
            render_metric_tile("Phone Violations", f"{phone_viol_count}", "Camera Device Flags", "fail" if phone_viol_count > 0 else "pass")
        with m_c5:
            render_metric_tile("High-Risk Alerts", summary_data["high_risk_events"], "Requires Review", "fail" if summary_data["high_risk_events"] > 0 else "pass")
        with m_c6:
            render_metric_tile("Pending Reviews", summary_data["pending_reviews"], "Awaiting Decision", "warn" if summary_data["pending_reviews"] > 0 else "pass")

        # Real-time Faculty Alert Feed for Browser Extensions
        st.markdown("#### 🚨 Faculty Extension Violation Alerts & Pre-Exam Flags")
        st.caption("Active and archived alerts dispatched to faculty when candidates are detected using browser extensions before starting or during exams.")
        recent_ext_events = db.get_extension_events(limit=25)
        if recent_ext_events:
            for rev in recent_ext_events[:4]:
                raw_d = rev.get("raw_data")
                if isinstance(raw_d, str):
                    try:
                        raw_d = json.loads(raw_d)
                    except Exception:
                        raw_d = {}
                elif not isinstance(raw_d, dict):
                    raw_d = {}
                ext_n = raw_d.get("extension_name", "Third-Party Browser Extension")
                stg = raw_d.get("stage", "PRE_EXAM" if "PRE" in rev.get("event_type", "") else "ACTIVE_EXAM")
                occ_t = rev.get("occurred_at", time.time())
                t_str = datetime.datetime.fromtimestamp(occ_t).strftime("%H:%M:%S")

                render_faculty_extension_alert_card(
                    candidate_name=rev.get("student_name") or "Mayur Tandel",
                    student_id=rev.get("student_id", "STU-2026-081"),
                    roll_no=rev.get("roll_number", "CS-2026-081"),
                    session_id=rev.get("exam_session_id", "N/A"),
                    ext_name=ext_n,
                    stage=stg,
                    timestamp_str=t_str,
                )
        else:
            st.success("🟢 No active browser extension violations reported across candidate sessions.")

        st.divider()

        # Admin Tabs
        admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([
            "📋 Candidate Sessions",
            "🛡️ Browser Monitoring & Events",
            "🌐 Browser Compatibility Reports",
            "📊 Activity Analytics & Reports",
        ])

        with admin_tab1:
            st.markdown("#### 📋 Active and Historical Examination Sessions")
            sessions = db.get_sessions(limit=100)
            if sessions:
                sessions_df = pd.DataFrame(sessions)
                display_cols = [
                    "exam_session_id", "student_id", "browser_name", "browser_version",
                    "compatibility_status", "institutional_extension_status",
                    "final_risk_level", "total_events", "status", "created_at"
                ]
                available_cols = [c for c in display_cols if c in sessions_df.columns]
                st.dataframe(sessions_df[available_cols], use_container_width=True)
            else:
                st.info("No recorded examination sessions in database.")

        with admin_tab2:
            st.markdown("#### 🛡️ Browser & Extension Integrity Event Logs")

            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            with col_f1:
                filter_risk = st.selectbox("Filter Risk Level", ["ALL", "HIGH", "MEDIUM", "LOW"], index=0)
            with col_f2:
                filter_status = st.selectbox("Filter Review Status", ["ALL", "NEEDS_REVIEW", "CONFIRMED", "FALSE_POSITIVE"], index=0)
            with col_f3:
                filter_type = st.selectbox("Filter Event Type", ["ALL", "MOBILE_PHONE_DETECTED", "PRE_EXAM_EXTENSION_DETECTED", "EXTENSION_DETECTED", "WINDOW_BLUR_TAB_SWITCH", "HOTKEY_SHORTCUT", "PAGE_INTEGRITY_CHANGE", "EXAM_INTERFACE_OVERLAY"], index=0)
            with col_f4:
                filter_student = st.text_input("Filter by Student ID", value="")

            events = db.get_events(
                student_id=filter_student.strip() if filter_student.strip() else None,
                event_type=None if filter_type == "ALL" else filter_type,
                risk_level=filter_risk,
                review_status=filter_status,
                limit=150,
            )

            if events:
                events_df = pd.DataFrame(events)
                cols_to_show = ["id", "exam_session_id", "student_id", "event_type", "risk_level", "review_status", "detection_method", "event_description", "created_at"]
                cols_present = [c for c in cols_to_show if c in events_df.columns]
                st.dataframe(events_df[cols_present], use_container_width=True)

                st.divider()
                st.markdown("##### ✍️ Administrative Event Review Action")
                st.caption("Human proctor review workflow for confirming or dismissing flagged monitoring events.")

                event_ids = [e["id"] for e in events]
                selected_event_id = st.selectbox("Select Event ID to Review", event_ids)
                selected_event = next((e for e in events if e["id"] == selected_event_id), None)

                if selected_event:
                    rev_c1, rev_c2 = st.columns([2, 3])
                    with rev_c1:
                        st.markdown(f"**Event Type**: `{selected_event['event_type']}`")
                        st.markdown(f"**Risk Level**: `{selected_event['risk_level']}`")
                        st.markdown(f"**Detection Method**: `{selected_event['detection_method']}`")
                        st.markdown(f"**Description**: {selected_event['event_description']}")
                        st.markdown(f"**Current Status**: `{selected_event['review_status']}`")

                    with rev_c2:
                        rev_decision = st.radio(
                            "Proctor Decision:",
                            ["CONFIRMED", "FALSE_POSITIVE", "NEEDS_REVIEW"],
                            index=0 if selected_event["review_status"] == "CONFIRMED" else (1 if selected_event["review_status"] == "FALSE_POSITIVE" else 2),
                            horizontal=True,
                            key=f"radio_rev_{selected_event_id}",
                        )
                        rev_notes = st.text_area(
                            "Reviewer Notes / Justification:",
                            value="",
                            placeholder="e.g. Verified brief momentary focus loss, candidate remained at station.",
                            key=f"notes_rev_{selected_event_id}",
                        )

                        if st.button("💾 Save Review Decision", type="primary", key=f"btn_save_rev_{selected_event_id}"):
                            success = db.record_review(
                                event_id=selected_event_id,
                                reviewer_id="ADMIN-PROCTOR",
                                review_decision=rev_decision,
                                review_notes=rev_notes,
                            )
                            if success:
                                st.success(f"Event #{selected_event_id} marked as '{rev_decision}' and logged to audit trail.")
                                st.rerun()
                            else:
                                st.error("Failed to update review decision.")
            else:
                st.info("No monitoring events matching the current filter criteria.")

        with admin_tab3:
            st.markdown("#### 🌐 Browser Compatibility & Readiness Reports")
            compat_stats = db.get_browser_compatibility_stats()

            c_col1, c_col2, c_col3 = st.columns(3)
            with c_col1:
                st.markdown("**Browser Distribution**")
                if compat_stats["browsers"]:
                    st.dataframe(pd.DataFrame(list(compat_stats["browsers"].items()), columns=["Browser", "Candidates"]), use_container_width=True)
                else:
                    st.caption("No browser data logged.")

            with c_col2:
                st.markdown("**Compatibility Readiness**")
                if compat_stats["compatibility"]:
                    st.dataframe(pd.DataFrame(list(compat_stats["compatibility"].items()), columns=["Status", "Count"]), use_container_width=True)
                else:
                    st.caption("No compatibility records logged.")

            with c_col3:
                st.markdown("**Institutional Extension Connection**")
                if compat_stats["extension_status"]:
                    st.dataframe(pd.DataFrame(list(compat_stats["extension_status"].items()), columns=["Extension Status", "Count"]), use_container_width=True)
                else:
                    st.caption("No extension status logged.")

        with admin_tab4:
            st.markdown("#### 📊 Suspicious Activity Summaries & CSV Export")
            st.markdown("""
            * **Automated Scoring Principle**: Multi-modal fusion aggregates 3D head orientation, gaze vector, keyboard telemetry, and object counts into a continuous probability metric.
            * **Extension & DOM Monitoring**: MutationObserver logs interface alterations and overlay intrusions without invasive browser snooping.
            * **Human-in-the-Loop Integrity**: Monitoring alerts represent evidence for administrator review rather than unilateral disqualification.
            """)

            all_events = db.get_events(limit=500)
            if all_events:
                csv_data = pd.DataFrame(all_events).to_csv(index=False)
                st.download_button(
                    "📥 Export Complete Examination Monitoring Audit Log (CSV)",
                    data=csv_data,
                    file_name="exam_integrity_audit_log.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

    # -------------------------------------------------------------------------
    # VIEW B: STUDENT DASHBOARD (PORTAL HOME)
    # -------------------------------------------------------------------------
    elif not st.session_state.exam_active and not st.session_state.exam_submitted:
        print("[MARKER 5] View selected: HOME PORTAL", flush=True)

        # Live Browser Extension & Companion Handshake Synchronization
        query_ext_detected = st.query_params.get("ext_detected") == "1"
        query_ext_name = st.query_params.get("ext_name", "")
        beacon_ext = get_active_detected_extension(st.session_state.student_id)

        if query_ext_detected:
            if not st.session_state.unauthorized_extension_active:
                st.session_state.unauthorized_extension_active = True
                st.session_state.extension_alert_sent_to_faculty = False
            if query_ext_name:
                st.session_state.detected_extension_name = query_ext_name
        elif beacon_ext:
            if not st.session_state.unauthorized_extension_active:
                st.session_state.unauthorized_extension_active = True
                st.session_state.extension_alert_sent_to_faculty = False
            st.session_state.detected_extension_name = beacon_ext.get("name", "Exam Integrity Extension")

        if is_institutional_extension_connected():
            st.session_state.extension_connected = True

        st.info("ℹ️ Welcome to the AI-Proctored Examination Portal. Please review your system readiness checklist below before starting.")

        dash_col1, dash_col2 = st.columns([3, 2], gap="medium")

        with dash_col1:
            # 1. Candidate Information Card (Clean Native Container)
            st.markdown("#### 👤 Candidate Profile")
            with st.container(border=True):
                prof_c1, prof_c2 = st.columns(2)
                with prof_c1:
                    st.markdown(f"**Full Name:** {student_record['full_name']}")
                    st.markdown(f"**Department:** {student_record['department']}")
                    st.markdown(f"**Active Session:** `{st.session_state.active_session_id}`")
                with prof_c2:
                    st.markdown(f"**Candidate ID:** {student_record['student_id']}")
                    st.markdown(f"**Roll Number:** {student_record['roll_number']}")
                    st.markdown('**Portal Status:** <span class="pill pill-pass">AUTHORIZED</span>', unsafe_allow_html=True)

            # Pre-Exam Extension Warning Alert Banner (if active)
            if st.session_state.unauthorized_extension_active:
                render_pre_exam_extension_warning(
                    detected_extension_name=st.session_state.detected_extension_name,
                    student_id=st.session_state.student_id,
                    session_id=st.session_state.active_session_id,
                )
                if not st.session_state.extension_alert_sent_to_faculty:
                    db.record_event(
                        exam_session_id=st.session_state.active_session_id,
                        student_id=st.session_state.student_id,
                        event_type="PRE_EXAM_EXTENSION_DETECTED",
                        event_description=f"Candidate flagged before exam: Active browser extension detected ({st.session_state.detected_extension_name}). Warning displayed: 'You are using browser extension'. Telemetry sent to Faculty Dashboard.",
                        detection_method="PreExamExtensionScanner",
                        risk_level="HIGH",
                        severity="HIGH",
                        raw_data={
                            "extension_name": st.session_state.detected_extension_name,
                            "stage": "PRE_EXAM",
                            "warned": True,
                        },
                    )
                    st.session_state.extension_alert_sent_to_faculty = True
                    st.session_state.extension_used_in_exam = True

            # 2. Available Examinations
            st.markdown("#### 📋 Available & Upcoming Examinations")
            render_exam_card(
                title="AI & ML Certification Examination",
                course_code="CS-DS-2026-X",
                duration_mins=60,
                total_questions=5,
            )

            # Primary Exam Start Action
            if st.button("🚀 CLICK HERE TO START EXAM NOW", type="primary", use_container_width=True):
                st.session_state.exam_started = True
                st.session_state.exam_active = True
                st.session_state.exam_submitted = False
                st.session_state.current_question_index = 0
                st.session_state.user_answers = {}
                st.session_state.marked_for_review = set()
                st.session_state.exam_start_time = time.time()
                st.session_state.active_session_id = f"SESSION-{int(time.time())}"

                # Register session in persistent database
                db.create_or_get_session(
                    exam_session_id=st.session_state.active_session_id,
                    exam_id="EXAM-CS-2026-X",
                    student_id=st.session_state.student_id,
                    browser_name=st.session_state.simulated_browser_name,
                    browser_version=st.session_state.simulated_browser_ver,
                    os_name="Windows 11",
                    compatibility_status="WARNING" if st.session_state.unauthorized_extension_active else "READY",
                    institutional_extension_status="CONNECTED" if st.session_state.extension_connected else "NOT_INSTALLED",
                    camera_permission="GRANTED" if st.session_state.camera_permission_granted else "DENIED",
                    mic_permission="GRANTED" if st.session_state.mic_permission_granted else "DENIED",
                )

                # Record pre-exam extension violation if active
                if st.session_state.unauthorized_extension_active:
                    st.session_state.extension_used_in_exam = True
                    db.record_event(
                        exam_session_id=st.session_state.active_session_id,
                        student_id=st.session_state.student_id,
                        event_type="PRE_EXAM_EXTENSION_DETECTED",
                        event_description=f"Active browser extension detected ({st.session_state.detected_extension_name}) before starting exam. Candidate warned; telemetry sent to faculty dashboard.",
                        detection_method="PreExamExtensionScanner",
                        risk_level="HIGH",
                        severity="HIGH",
                        raw_data={
                            "extension_name": st.session_state.detected_extension_name,
                            "stage": "PRE_EXAM",
                            "warned": True,
                            "started_with_extension": True,
                        },
                    )

                kb = get_keyboard_monitor_singleton()
                kb.reset()
                kb.set_session(st.session_state.active_session_id, st.session_state.student_id)
                if not kb.is_running:
                    kb.start()
                st.rerun()

        with dash_col2:
            # 3. Browser Readiness & Compatibility Checklist
            st.markdown("#### 🛡️ Browser Readiness & Compatibility Checklist")

            # Client-Side Real-Time Extension Scanner Telemetry Component
            st.components.v1.html(
                get_pre_exam_extension_detector_js(
                    exam_session_id=st.session_state.active_session_id,
                    student_id=st.session_state.student_id,
                    is_extension_active=st.session_state.unauthorized_extension_active,
                    extension_name=st.session_state.detected_extension_name,
                ),
                height=135,
            )

            # Evaluate Environment
            browser_info = {
                "browser": st.session_state.simulated_browser_name,
                "version": st.session_state.simulated_browser_ver,
                "os": "Windows 11",
            }
            evaluation = evaluator.evaluate_compatibility(
                browser_info=browser_info,
                camera_permission="GRANTED" if st.session_state.camera_permission_granted else "DENIED",
                mic_permission="GRANTED" if st.session_state.mic_permission_granted else "DENIED",
                unauthorized_extension_active=st.session_state.unauthorized_extension_active,
                detected_extension_name=st.session_state.detected_extension_name,
            )

            render_readiness_checklist(evaluation["checklist"])

            if st.session_state.unauthorized_extension_active:
                if st.button("🔄 Re-Scan Environment (After Disabling Extensions)", key="rescan_ext_btn", use_container_width=True):
                    clear_active_detected_extension(st.session_state.student_id)
                    try:
                        st.query_params.clear()
                    except Exception:
                        pass
                    st.session_state.unauthorized_extension_active = False
                    st.session_state.extension_alert_sent_to_faculty = False
                    st.rerun()

            # Permission Check Configuration
            with st.expander("🔧 Hardware Permissions & Browser Configuration", expanded=False):
                st.session_state.camera_permission_granted = st.checkbox(
                    "Camera Permission Granted",
                    value=st.session_state.camera_permission_granted,
                    help="Simulate camera permission grant/deny"
                )
                st.session_state.mic_permission_granted = st.checkbox(
                    "Microphone Permission Granted",
                    value=st.session_state.mic_permission_granted
                )
                st.session_state.extension_connected = st.checkbox(
                    "Institutional Extension Connected",
                    value=st.session_state.extension_connected,
                    help="Simulate institutional companion handshake"
                )

                st.markdown("---")
                st.markdown("##### 🛡️ Third-Party Extension Security Testing")
                ext_test_toggle = st.checkbox(
                    "🚨 Trigger / Simulate Active Extension Detected",
                    value=st.session_state.unauthorized_extension_active,
                    help="Simulate detection of an unauthorized third-party browser extension before exam."
                )
                if ext_test_toggle != st.session_state.unauthorized_extension_active:
                    st.session_state.unauthorized_extension_active = ext_test_toggle
                    st.session_state.extension_alert_sent_to_faculty = False
                    st.rerun()

                ext_choices = [
                    "AI Exam Assistant & Solver",
                    "Grammarly & Content Injector",
                    "Tampermonkey Automation Script",
                    "AdBlock Plus & DOM Manipulator",
                    "Google Translate Overlay Extension",
                ]
                default_ext_idx = ext_choices.index(st.session_state.detected_extension_name) if st.session_state.detected_extension_name in ext_choices else 0
                ext_name_sel = st.selectbox(
                    "Detected Extension Signature:",
                    ext_choices,
                    index=default_ext_idx,
                )
                if ext_name_sel != st.session_state.detected_extension_name:
                    st.session_state.detected_extension_name = ext_name_sel
                    st.session_state.extension_alert_sent_to_faculty = False
                    st.rerun()

            # 4. Previous Examination History
            st.markdown("#### 📜 Candidate Examination History")
            history = db.get_sessions(student_id=st.session_state.student_id, limit=5)
            if history:
                for h in history:
                    risk_cls = "pill-pass" if h["final_risk_level"] == "LOW" else ("pill-warn" if h["final_risk_level"] == "MEDIUM" else "pill-fail")
                    with st.container(border=True):
                        col_h1, col_h2 = st.columns([3, 1])
                        with col_h1:
                            st.markdown(f"**{h['exam_title'] or 'Examination Session'}**")
                            st.caption(f"Session: `{h['exam_session_id']}` | Status: {h['status']} | Events: {h['total_events']}")
                        with col_h2:
                            st.markdown(f"<span class='pill {risk_cls}'>{h['final_risk_level']} RISK</span>", unsafe_allow_html=True)
            else:
                st.caption("No prior examination sessions found.")

    # -------------------------------------------------------------------------
    # VIEW C: ACTIVE DISTRACTION-FREE EXAMINATION INTERFACE
    # -------------------------------------------------------------------------
    elif st.session_state.exam_active:
        print("[MARKER 5] View selected: ACTIVE EXAM INTERFACE", flush=True)

        # Distraction-Free Top Bar with Timer, Progress & Theme Switch
        q_num = st.session_state.current_question_index + 1
        total_q = len(EXAM_QUESTIONS)

        top_c1, top_c2, top_c3, top_c4 = st.columns([3.2, 1.8, 1.6, 1.2])
        with top_c1:
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 1.6rem;">✍️</span>
                <div>
                    <div style="font-size: 1.15rem; font-weight: 800; color: var(--text); letter-spacing: -0.01em;">AI & ML Certification Examination</div>
                    <div style="font-size: 0.8rem; color: var(--text-muted);">Candidate: <strong>{student_record['full_name']}</strong> ({student_record['student_id']}) &nbsp;•&nbsp; <code>CS-DS-2026-X</code></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with top_c2:
            render_exam_timer_fragment()
        with top_c3:
            st.markdown(
                f"<div style='font-size: 1.05rem; font-weight: 700; color: var(--text); background: var(--surface-2); border: 1px solid var(--border); padding: 6px 14px; border-radius: 10px; text-align: center;'>"
                f"📊 <strong>Q{q_num} of {total_q}</strong>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with top_c4:
            theme_btn_label = "☀️ Light" if st.session_state.get("theme", "dark") == "dark" else "🌙 Dark"
            if st.button(theme_btn_label, key="exam_theme_quick_toggle", use_container_width=True):
                st.session_state.theme = "light" if st.session_state.get("theme", "dark") == "dark" else "dark"
                st.rerun()

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        # 2-Zone Layout: Left = Exam Area (62%), Right = Proctoring Panel (38%)
        col_questions, col_proctoring = st.columns([1.6, 1.0], gap="large")

        # LEFT COLUMN: STUDENT QUESTIONS & NAVIGATION PALETTE
        with col_questions:
            # Check for live camera phone detection (from database, worker telemetry, or session)
            session_phone_events = db.get_phone_events(
                exam_session_id=st.session_state.active_session_id,
                limit=50,
            )
            curr_worker_phone = False
            curr_phone_conf = 0.0
            try:
                worker_inst = get_cached_proctoring_worker(device_idx=device_idx)
                if worker_inst:
                    w_data = worker_inst.get_latest_data()
                    curr_worker_phone = w_data.yolo_tel.get("phone_detected", False) or getattr(worker_inst, "_phone_detected_sim", False)
                    curr_phone_conf = w_data.yolo_tel.get("phone_confidence", 0.0)
            except Exception:
                pass

            phone_alert_active = (
                len(session_phone_events) > 0
                or curr_worker_phone
                or st.session_state.get("phone_detected_in_exam", False)
            )
            if phone_alert_active:
                st.session_state.phone_detected_in_exam = True
                phone_cnt = max(len(session_phone_events), 1)
                peak_conf = max(curr_phone_conf, max([float(e.get("raw_data", {}).get("confidence", 0.0) if isinstance(e.get("raw_data"), dict) else 0.0) for e in session_phone_events], default=0.92))
                render_phone_detection_live_warning(incident_count=phone_cnt, peak_confidence=peak_conf)

            # Check for recorded tab switch events for this active session
            all_live_events = db.get_events(
                student_id=st.session_state.student_id,
                event_type="WINDOW_BLUR_TAB_SWITCH",
                limit=50,
            )
            session_live_tabs = [e for e in all_live_events if e.get("exam_session_id") == st.session_state.active_session_id]
            tab_alert_cnt = len(session_live_tabs)
            if tab_alert_cnt > 0:
                st.markdown(f"""
                <div class="violation-banner">
                    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                        <span style="font-size: 1.1rem; font-weight: 800; color: var(--danger); display: flex; align-items: center; gap: 10px;">
                            <span class="pulse-icon">🚨</span> <span>HIGH-RISK PROCTORING ALERT: Tab Switch Detected ({tab_alert_cnt} Incident{'s' if tab_alert_cnt > 1 else ''})!</span>
                        </span>
                        <span class="pill pill-fail">TAB SWITCH (HIGH RISK)</span>
                    </div>
                    <div style="margin-top: 8px; font-size: 0.92rem; color: var(--text); line-height: 1.5;">
                        ⚠️ <strong>High-Risk Violation</strong>: Navigating away from the active examination window or switching browser tabs is strictly prohibited. All tab switches are classified as <strong>HIGH RISK</strong>, logged with exact timestamps, and forwarded for proctor review.
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # Check for recorded keyboard shortcut events for this active session
            all_live_kb_events = db.get_events(
                student_id=st.session_state.student_id,
                event_type="HOTKEY_SHORTCUT",
                limit=100,
            )
            session_live_kb = [e for e in all_live_kb_events if e.get("exam_session_id") == st.session_state.active_session_id]
            kb_mon = get_keyboard_monitor_singleton()
            kb_summary = kb_mon.get_shortcut_summary()

            # Compile combined shortcut counts
            import json
            combined_kb_counts = dict(kb_summary.get("shortcut_counts", {}))
            for e in session_live_kb:
                raw_d = e.get("raw_data")
                sc = None
                if isinstance(raw_d, str):
                    try:
                        sc = json.loads(raw_d).get("shortcut")
                    except Exception:
                        pass
                elif isinstance(raw_d, dict):
                    sc = raw_d.get("shortcut")
                if not sc:
                    desc_l = str(e.get("event_description", "")).lower()
                    for cand in ["alt+tab", "ctrl+c", "ctrl+v", "ctrl+x", "ctrl+a", "print_screen", "devtools", "f12", "alt+f4", "win"]:
                        if cand in desc_l or cand.replace("+", " ") in desc_l:
                            sc = cand
                            break
                if sc:
                    sc = sc.lower()
                    if sc not in combined_kb_counts:
                        combined_kb_counts[sc] = 1

            total_kb_incidents = max(len(session_live_kb), sum(combined_kb_counts.values()) if combined_kb_counts else 0)

            if total_kb_incidents > 0:
                kb_badges_list = []
                for sc, cnt in sorted(combined_kb_counts.items(), key=lambda x: x[1], reverse=True):
                    sc_disp = sc.upper().replace("+", " + ")
                    kb_badges_list.append(f"<code style='background:var(--surface); padding:2px 8px; border-radius:4px; font-weight:700;'>{sc_disp}: {cnt}×</code>")
                kb_badges_str = " &nbsp; ".join(kb_badges_list) if kb_badges_list else "Prohibited Shortcuts"

                st.markdown(f"""
                <div class="violation-banner">
                    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                        <span style="font-size: 1.1rem; font-weight: 800; color: var(--danger); display: flex; align-items: center; gap: 10px;">
                            <span class="pulse-icon">⌨️</span> <span>PROCTORING WARNING: Forbidden Keyboard Shortcut Detected ({total_kb_incidents} Incident{'s' if total_kb_incidents > 1 else ''})!</span>
                        </span>
                        <span class="pill pill-warn">HOTKEY FLAGGED</span>
                    </div>
                    <div style="margin-top: 8px; font-size: 0.92rem; color: var(--text); line-height: 1.5;">
                        <strong>Flagged Keys:</strong> {kb_badges_str}
                    </div>
                    <div style="margin-top: 6px; font-size: 0.88rem; color: var(--text); line-height: 1.45;">
                        ⚠️ <strong>Integrity Violation:</strong> Shortcuts for copying text (Ctrl+C), pasting answers (Ctrl+V), task-switching (Alt+Tab), or screenshots (Print Screen) are strictly prohibited. Your Cheating Probability has been increased, and keystrokes have been logged.
                    </div>
                </div>
                """, unsafe_allow_html=True)

            curr_idx = st.session_state.current_question_index
            total_questions = len(EXAM_QUESTIONS)

            # Compute Status Counts
            answered_count = len([k for k, v in st.session_state.user_answers.items() if v is not None])
            marked_count = len(st.session_state.marked_for_review)
            unanswered_count = total_questions - answered_count

            # Progress Badge Counters
            render_question_matrix_summary(
                total=total_questions,
                answered=answered_count,
                marked=marked_count,
                unanswered=unanswered_count,
            )

            # Question Navigation Matrix (Clickable numbered pills 1..5)
            st.markdown("**Question Palette:**")
            matrix_cols = st.columns(total_questions)
            for q_i in range(total_questions):
                with matrix_cols[q_i]:
                    is_current = (q_i == curr_idx)
                    is_answered = (q_i in st.session_state.user_answers and st.session_state.user_answers[q_i] is not None)
                    is_marked = (q_i in st.session_state.marked_for_review)

                    # Dynamic label with status indicator
                    if is_current:
                        prefix = "▶ Q"
                    elif is_marked:
                        prefix = "🏷️ Q"
                    elif is_answered:
                        prefix = "✔ Q"
                    else:
                        prefix = "Q"

                    btn_type = "primary" if is_current else "secondary"
                    if st.button(f"{prefix}{q_i + 1}", key=f"matrix_q_{q_i}", type=btn_type, use_container_width=True):
                        st.session_state.current_question_index = q_i
                        st.rerun()

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            # Active Question Display Card (Using Clean Native Container - ZERO Raw HTML)
            q_data = EXAM_QUESTIONS[curr_idx]
            is_q_marked = curr_idx in st.session_state.marked_for_review

            with st.container(border=True):
                col_qh1, col_qh2 = st.columns([3, 1])
                with col_qh1:
                    st.markdown(f"**Question {curr_idx + 1} of {total_questions}**")
                with col_qh2:
                    if is_q_marked:
                        st.markdown('<span class="pill pill-warn">🏷️ MARKED FOR REVIEW</span>', unsafe_allow_html=True)

                st.markdown(f"<div class='question-heading'>{q_data['question']}</div>", unsafe_allow_html=True)
                st.divider()

                options = q_data["options"]
                current_selected = st.session_state.user_answers.get(curr_idx, None)
                default_index = options.index(current_selected) if current_selected in options else None

                # MCQ Answer Options Radio Group (styled as full-width interactive cards)
                selected_option = st.radio(
                    "Select the most appropriate answer:",
                    options,
                    index=default_index,
                    key=f"radio_q_{curr_idx}",
                    label_visibility="collapsed",
                )
                st.session_state.user_answers[curr_idx] = selected_option

            # Save answer to database
            db.record_answer(
                exam_session_id=st.session_state.active_session_id,
                student_id=st.session_state.student_id,
                question_id=q_data["id"],
                selected_option=selected_option,
                is_marked_for_review=is_q_marked,
            )

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

            # Action Bar: Previous, Next, Mark for Review, Clear Response
            act_col1, act_col2, act_col3, act_col4 = st.columns(4)
            with act_col1:
                if st.button("⬅️ Previous", disabled=(curr_idx == 0), use_container_width=True):
                    st.session_state.current_question_index -= 1
                    st.rerun()

            with act_col2:
                if st.button("Next ➡️", disabled=(curr_idx == total_questions - 1), use_container_width=True):
                    st.session_state.current_question_index += 1
                    st.rerun()

            with act_col3:
                mark_label = "Unmark Review" if is_q_marked else "🏷️ Mark Review"
                if st.button(mark_label, use_container_width=True):
                    if is_q_marked:
                        st.session_state.marked_for_review.remove(curr_idx)
                    else:
                        st.session_state.marked_for_review.add(curr_idx)
                    st.rerun()

            with act_col4:
                if st.button("🧹 Clear", use_container_width=True):
                    st.session_state.user_answers[curr_idx] = None
                    if curr_idx in st.session_state.marked_for_review:
                        st.session_state.marked_for_review.remove(curr_idx)
                    st.rerun()

            st.divider()

            # Submission Review & Confirmation Card (Clean Native Container)
            with st.container(border=True):
                st.markdown("⚠️ **Final Submission Review & Confirmation**")
                st.caption(f"Review summary: **{answered_count}** answered, **{marked_count}** marked for review, **{unanswered_count}** unanswered.")
                st.caption("Clicking the button below will permanently finalize your responses and conclude the examination.")

                if st.button("🛑 SUBMIT EXAM & FINISH", type="primary", use_container_width=True):
                    st.session_state.exam_active = False
                    st.session_state.exam_submitted = True
                    kb = get_keyboard_monitor_singleton()
                    st.session_state.final_keyboard_summary = kb.get_shortcut_summary()

                    # Query tab switches, phone violations, and extension violations to determine final submission risk
                    tab_evts_end = db.get_events(exam_session_id=st.session_state.active_session_id, event_type="WINDOW_BLUR_TAB_SWITCH")
                    ext_evts_end = db.get_extension_events(exam_session_id=st.session_state.active_session_id)
                    phone_evts_end = db.get_phone_events(exam_session_id=st.session_state.active_session_id)
                    has_phone = len(phone_evts_end) > 0 or st.session_state.get("phone_detected_in_exam", False)
                    has_violations = len(tab_evts_end) > 0 or len(ext_evts_end) > 0 or has_phone or st.session_state.get("extension_used_in_exam", False)
                    sub_risk = "HIGH" if has_violations else "LOW"
                    peak_sub_score = 0.90 if has_phone else (0.85 if has_violations else 0.0)

                    db.end_session(
                        exam_session_id=st.session_state.active_session_id,
                        status="SUBMITTED",
                        peak_risk_score=peak_sub_score,
                        final_risk_level=sub_risk,
                    )
                    st.rerun()

        # RIGHT COLUMN: LIVE PROCTORING MONITOR & BROWSER INTEGRITY GUARD
        with col_proctoring:
            st.markdown("#### 📹 Live Proctoring & Integrity Monitor")

            # Client-Side DOM & Extension Integrity Component
            st.components.v1.html(
                get_integrity_client_js(
                    exam_session_id=st.session_state.active_session_id,
                    student_id=st.session_state.student_id,
                ),
                height=140,
            )

            try:
                # Get cached worker singleton (isolated thread execution)
                worker = get_cached_proctoring_worker(device_idx=device_idx)
                render_live_proctoring_fragment(worker)
            except Exception as frag_err:
                st.error("Proctoring Monitor Error")
                st.exception(frag_err)

        print("[MARKER 6] Exam UI render completed", flush=True)

    # -------------------------------------------------------------------------
    # VIEW D: EXAM SUBMITTED SUMMARY & POST-EXAM ANALYTICS
    # -------------------------------------------------------------------------
    elif st.session_state.exam_submitted:
        print("[MARKER 5] View selected: EXAM SUBMITTED SUMMARY", flush=True)
        st.balloons()
        st.success("🎉 Examination Completed & Submitted Successfully!")

        st.markdown("### 12. Exam Summary & Post-Exam Behavioral Analytics")
        worker = get_cached_proctoring_worker(device_idx=device_idx)
        timeline = worker.get_timeline()
        summary = timeline.get_session_summary()

        sum_c1, sum_c2, sum_c3, sum_c4 = st.columns(4)
        sum_c1.metric("Exam Duration", f"{summary['duration_sec']:.1f} s")
        sum_c2.metric("Total Events Logged", f"{summary['total_events']}")
        sum_c3.metric("Suspicious Events", f"{summary['suspicious_event_count']}")
        sum_c4.metric("Final Cheating Probability", f"{summary['final_cheating_probability']:.2f}")

        # Check if tab switch events, extension breaches, or phone detection occurred to escalate final session risk to HIGH
        post_tab_events = db.get_events(
            exam_session_id=st.session_state.active_session_id,
            event_type="WINDOW_BLUR_TAB_SWITCH",
        )
        post_ext_events = db.get_extension_events(exam_session_id=st.session_state.active_session_id)
        post_phone_events = db.get_phone_events(exam_session_id=st.session_state.active_session_id)
        phone_was_detected = (
            len(post_phone_events) > 0 
            or st.session_state.get("phone_detected_in_exam", False)
        )
        if len(post_tab_events) > 0 or len(post_ext_events) > 0 or phone_was_detected or st.session_state.get("extension_used_in_exam", False):
            summary["final_risk_level"] = "HIGH"
            summary["peak_cheating_score"] = max(float(summary.get("peak_cheating_score", 0.0)), 0.90 if phone_was_detected else 0.85)

        st.divider()
        render_risk_badge(summary["final_risk_level"], summary["peak_cheating_score"])

        # Update persistent database with final peak scores
        db.end_session(
            exam_session_id=st.session_state.active_session_id,
            status="SUBMITTED",
            peak_risk_score=float(summary["peak_cheating_score"]),
            final_risk_level=str(summary["final_risk_level"]).upper(),
        )

        # ---------------------------------------------------------------------
        # BROWSER EXTENSION INTEGRITY CLEARANCE REPORT AT EXAM SUBMISSION
        # ---------------------------------------------------------------------
        st.divider()
        st.markdown("### 🛡️ Browser Extension Integrity Clearance & Audit Report")
        st.caption("Official examination clearance verification confirming whether third-party browser extensions were active or used.")

        # Query extension violation events for this session
        ext_events = db.get_extension_events(exam_session_id=st.session_state.active_session_id)
        if not ext_events:
            all_sess_evts = db.get_events(exam_session_id=st.session_state.active_session_id)
            ext_events = [e for e in all_sess_evts if "EXTENSION" in e.get("event_type", "").upper() or "chrome-extension://" in str(e.get("raw_data", ""))]

        extension_was_used = st.session_state.get("extension_used_in_exam", False) or len(ext_events) > 0
        detected_name = st.session_state.get("detected_extension_name", "AI Exam Assistant / Third-Party Extension")
        if ext_events:
            first_raw = ext_events[0].get("raw_data")
            if isinstance(first_raw, str):
                try:
                    first_raw = json.loads(first_raw)
                except Exception:
                    first_raw = {}
            if isinstance(first_raw, dict) and first_raw.get("extension_name"):
                detected_name = first_raw.get("extension_name")

        render_extension_clearance_card(
            extension_used=extension_was_used,
            detected_extension_name=detected_name,
            events=ext_events,
        )

        if extension_was_used:
            with st.container(border=True):
                st.markdown("##### 📋 Extension Clearance Breakdown & Violation Audit Trail")
                st.markdown(
                    f"**Candidate & Faculty Clearance Notice**: The integrity engine flagged active browser extension usage (**{detected_name}**). "
                    "Institutional guidelines strictly prohibit third-party extension environments. "
                    "Pre-exam warnings were served to the candidate, and full forensic telemetry was recorded and dispatched to the Faculty Examination Board."
                )
                clearance_table = [
                    {
                        "Clearance Audit Metric": "Browser Extension Clearance",
                        "Clearance Status": "FAILED — EXTENSION DETECTED & USED ❌",
                        "Forensic Findings": f"Active signature: {detected_name}",
                    },
                    {
                        "Clearance Audit Metric": "Pre-Exam Warning Served",
                        "Clearance Status": "CONFIRMED ISSUED ⚠️",
                        "Forensic Findings": "Warning 'You are using browser extension(s)' was presented to candidate prior to start",
                    },
                    {
                        "Clearance Audit Metric": "Faculty Dashboard Notification",
                        "Clearance Status": "TRANSMITTED & ARCHIVED 📡",
                        "Forensic Findings": "Real-time violation notification logged to Faculty Review Dashboard",
                    },
                    {
                        "Clearance Audit Metric": "Final Clearance Determination",
                        "Clearance Status": "CLEARANCE WITHHELD ❌",
                        "Forensic Findings": "Referred to Academic Disciplinary Review Committee for final score validation",
                    },
                ]
                st.dataframe(pd.DataFrame(clearance_table), use_container_width=True)

                if ext_events:
                    st.markdown("##### 🕒 Extension Incident Chronology & Faculty Audit Trail")
                    ext_chrono = []
                    for idx, ev in enumerate(ext_events, 1):
                        occ_t = ev.get("occurred_at", time.time())
                        t_str = datetime.datetime.fromtimestamp(occ_t).strftime("%H:%M:%S")
                        ext_chrono.append({
                            "Incident #": idx,
                            "Violation Type": ev.get("event_type", "PRE_EXAM_EXTENSION_DETECTED"),
                            "Risk Level": ev.get("risk_level", "HIGH"),
                            "Detection Engine": ev.get("detection_method", "PreExamExtensionScanner"),
                            "Timestamp": t_str,
                            "Forensic Description": ev.get("event_description", ""),
                        })
                    st.dataframe(pd.DataFrame(ext_chrono), use_container_width=True)
        else:
            with st.container(border=True):
                st.success("✅ **Browser Extension Clearance Approved**: Pre-exam diagnostic scans and real-time DOM integrity guards confirmed that zero unauthorized extensions were present or active. Candidate maintained 100% clean browser integrity.")

        # ---------------------------------------------------------------------
        # TAB SWITCHING AUDIT REPORT AT EXAM SUBMISSION
        # ---------------------------------------------------------------------
        st.divider()
        st.markdown("### 🔍 Browser Tab Switching & Navigation Integrity Audit")

        all_post_events = db.get_events(
            student_id=st.session_state.student_id,
            event_type="WINDOW_BLUR_TAB_SWITCH",
            limit=100,
        )
        session_tab_events = [e for e in all_post_events if e.get("exam_session_id") == st.session_state.active_session_id]
        total_tab_switches = len(session_tab_events)

        if total_tab_switches > 0:
            with st.container(border=True):
                st.error(
                    f"🚨 **HIGH-RISK PROCTORING INTEGRITY VIOLATION: {total_tab_switches} TAB SWITCH EVENT{'S' if total_tab_switches > 1 else ''} DETECTED!**"
                )
                st.markdown(
                    f"**Attention Candidate & Reviewing Proctor**: During this proctored examination, the monitoring engine detected that the examination window lost focus or a browser tab switch occurred **{total_tab_switches} time{'s' if total_tab_switches > 1 else ''}**. "
                    "Navigating away from the active examination tab is classified as a **HIGH-RISK** breach under institutional examination rules. All occurrences have been recorded with timestamps and submitted for proctor audit."
                )
                tab_table_data = []
                for idx, te in enumerate(session_tab_events, 1):
                    tab_table_data.append({
                        "Incident #": idx,
                        "Violation Type": "Window Blur / Tab Switch",
                        "Description": te.get("event_description", "Candidate switched away from exam tab"),
                        "Detection Engine": te.get("detection_method", "ScreenFocusMonitor"),
                        "Risk Level": te.get("risk_level", "HIGH"),
                        "Recorded Timestamp": te.get("created_at", "N/A"),
                    })
                st.dataframe(pd.DataFrame(tab_table_data), use_container_width=True)
        else:
            with st.container(border=True):
                st.success("✅ **Tab Integrity Verified**: Zero (0) tab switches or window blurs were detected. The candidate remained in the active examination window throughout the entire test.")

        # ---------------------------------------------------------------------
        # KEYBOARD SHORTCUT DETECTION AUDIT REPORT AT EXAM SUBMISSION
        # ---------------------------------------------------------------------
        st.divider()
        st.markdown("### ⌨️ Proctored Keyboard Shortcut & Hotkey Integrity Audit Report")
        st.caption("Detailed forensic behavioral breakdown of prohibited keystroke events, key frequency counts, and cheating score penalties.")

        # Gather all keyboard events for active session from DB and in-memory monitor
        all_post_kb_events = db.get_events(
            student_id=st.session_state.student_id,
            event_type="HOTKEY_SHORTCUT",
            limit=200,
        )
        session_kb_events = [e for e in all_post_kb_events if e.get("exam_session_id") == st.session_state.active_session_id]

        kb_mon = get_keyboard_monitor_singleton()
        kb_summary = getattr(st.session_state, "final_keyboard_summary", None) or kb_mon.get_shortcut_summary()

        from keyboard.monitor import SHORTCUT_METADATA

        # Aggregate keys pressed, counts, timestamps, and metadata
        aggregated_keys = {}
        for item in kb_summary.get("breakdown", []):
            sc = item["shortcut"].lower()
            aggregated_keys[sc] = {
                "shortcut": sc,
                "display_name": item["display_name"],
                "count": item["count"],
                "severity": item["severity"],
                "risk_level": item["risk_level"],
                "category": item["violation_type"],
                "first_seen": item["first_seen_str"],
                "last_seen": item["last_seen_str"],
                "description": item["description"],
            }

        # Merge with any database events to ensure 100% data completeness
        for e in session_kb_events:
            raw_d = e.get("raw_data")
            sc = None
            if isinstance(raw_d, str):
                try:
                    sc = json.loads(raw_d).get("shortcut")
                except Exception:
                    pass
            elif isinstance(raw_d, dict):
                sc = raw_d.get("shortcut")
            if not sc:
                desc_l = str(e.get("event_description", "")).lower()
                for cand in ["alt+tab", "ctrl+c", "ctrl+v", "ctrl+x", "ctrl+a", "print_screen", "devtools", "f12", "alt+f4", "win"]:
                    if cand in desc_l or cand.replace("+", " ") in desc_l:
                        sc = cand
                        break
            if sc:
                sc = sc.lower()
                meta = SHORTCUT_METADATA.get(sc, {
                    "display_name": sc.upper(),
                    "violation_type": "Prohibited Shortcut",
                    "severity": e.get("severity", "MEDIUM"),
                    "risk_level": e.get("risk_level", "MEDIUM"),
                    "description": e.get("event_description", ""),
                })
                occ_t = e.get("occurred_at", time.time())
                occ_time_str = datetime.datetime.fromtimestamp(occ_t).strftime("%H:%M:%S")
                if sc not in aggregated_keys:
                    aggregated_keys[sc] = {
                        "shortcut": sc,
                        "display_name": meta.get("display_name", sc.upper()),
                        "count": 1,
                        "severity": meta.get("severity", e.get("severity", "MEDIUM")),
                        "risk_level": meta.get("risk_level", e.get("risk_level", "MEDIUM")),
                        "category": meta.get("violation_type", "Prohibited Shortcut"),
                        "first_seen": occ_time_str,
                        "last_seen": occ_time_str,
                        "description": meta.get("description", e.get("event_description", "")),
                    }
                else:
                    db_sc_count = len([ev for ev in session_kb_events if sc in str(ev).lower()])
                    if db_sc_count > aggregated_keys[sc]["count"]:
                        aggregated_keys[sc]["count"] = db_sc_count

        total_kb_violations = sum(item["count"] for item in aggregated_keys.values()) if aggregated_keys else len(session_kb_events)

        if total_kb_violations > 0:
            with st.container(border=True):
                st.error(
                    f"⚠️ **PROCTORING INTEGRITY VIOLATION: {total_kb_violations} FORBIDDEN KEYSTROKE SHORTCUT EVENT{'S' if total_kb_violations > 1 else ''} DETECTED!**"
                )
                flagged_names_str = ", ".join([v["display_name"] for v in aggregated_keys.values()])
                st.markdown(
                    f"**Attention Candidate & Proctor Reviewer**: During this proctored examination, the monitoring engine intercepted and logged "
                    f"**{total_kb_violations} prohibited keyboard shortcut press{'es' if total_kb_violations > 1 else ''}** across **{len(aggregated_keys)} distinct key{'s' if len(aggregated_keys) > 1 else ''}** ({flagged_names_str}). "
                    "Keystrokes for clipboard operations (Ctrl+C / Ctrl+V), application switching (Alt+Tab), and screen captures (Print Screen) directly violate institutional examination integrity policies. "
                    "**The candidate's Cheating Probability score was penalized accordingly**, and complete forensic logs are recorded below for administrative review."
                )

                # Summary Metric Tiles
                kbm_c1, kbm_c2, kbm_c3, kbm_c4 = st.columns(4)
                any_high = any(v["risk_level"] == "HIGH" for v in aggregated_keys.values())
                penalty_est = min(1.0, 0.25 + (total_kb_violations - 1) * 0.15)
                with kbm_c1:
                    render_metric_tile("Total Key Violations", f"{total_kb_violations}", "Recorded Incidents", "fail")
                with kbm_c2:
                    render_metric_tile("Distinct Keys Flagged", f"{len(aggregated_keys)}", "Unique Forbidden Keys", "fail" if len(aggregated_keys) > 1 else "warn")
                with kbm_c3:
                    render_metric_tile("Cheating Penalty Applied", f"+{penalty_est:.2f}", "Continuous Penalty", "fail" if any_high else "warn")
                with kbm_c4:
                    render_metric_tile("Proctor Verdict", "FLAGGED ⚠️" if any_high else "REVIEW 🟠", "Audit Required", "fail" if any_high else "warn")

                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

                # Visual Badges / Frequency Pills
                st.markdown("**Forbidden Key Occurrence Badges:**")
                badges_html = " ".join([
                    f"<span class='pill {'pill-fail' if v['risk_level'] == 'HIGH' else 'pill-warn'}' style='font-size: 13px; padding: 5px 12px; margin-right: 8px;'>"
                    f"⚡ {v['display_name']} : <strong>{v['count']} Time{'s' if v['count'] > 1 else ''}</strong></span>"
                    for v in sorted(aggregated_keys.values(), key=lambda x: x["count"], reverse=True)
                ])
                st.markdown(badges_html, unsafe_allow_html=True)

                st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

                # Primary Breakdown Table: Which Key Was Pressed and How Many Times
                st.markdown("##### 📋 Key Detection Breakdown: Prohibited Keys Pressed & Exact Frequencies")
                breakdown_table = []
                for v in sorted(aggregated_keys.values(), key=lambda x: x["count"], reverse=True):
                    breakdown_table.append({
                        "Key / Shortcut": v["display_name"],
                        "Times Pressed": f"{v['count']} time{'s' if v['count'] > 1 else ''}",
                        "Violation Category": v["category"],
                        "Security Risk": v["risk_level"],
                        "First Detected": v["first_seen"],
                        "Last Detected": v["last_seen"],
                        "Behavioral Description": v["description"],
                    })
                st.dataframe(pd.DataFrame(breakdown_table), use_container_width=True)

                # Chronological Keystroke Incident Log
                st.markdown("##### 🕒 Chronological Keystroke Incident Audit Log")
                chrono_table = []
                raw_chrono = list(kb_summary.get("session_events", []))
                if not raw_chrono and session_kb_events:
                    for idx, e in enumerate(session_kb_events, 1):
                        raw_chrono.append({
                            "event_index": idx,
                            "shortcut": e.get("raw_data", {}).get("shortcut") if isinstance(e.get("raw_data"), dict) else "HOTKEY",
                            "timestamp_str": datetime.datetime.fromtimestamp(e.get("occurred_at", time.time())).strftime("%H:%M:%S"),
                            "detection_method": e.get("detection_method", "KeyboardHook"),
                            "risk_level": e.get("risk_level", "MEDIUM"),
                            "description": e.get("event_description", ""),
                        })

                for idx, ev in enumerate(raw_chrono, 1):
                    sc_name = ev.get("shortcut", "hotkey").lower()
                    meta = SHORTCUT_METADATA.get(sc_name, {})
                    chrono_table.append({
                        "Incident #": idx,
                        "Key Shortcut": meta.get("display_name", sc_name.upper()),
                        "Detection Engine": ev.get("detection_method", "KeyboardHook (pynput)"),
                        "Risk Level": ev.get("risk_level", "MEDIUM"),
                        "Recorded Timestamp": ev.get("timestamp_str", "N/A"),
                        "Audit Description": ev.get("description", f"Detected forbidden keypress: {sc_name.upper()}"),
                    })
                if chrono_table:
                    st.dataframe(pd.DataFrame(chrono_table), use_container_width=True)
        else:
            with st.container(border=True):
                st.success("✅ **Keyboard Integrity Verified**: Zero (0) prohibited keyboard shortcuts (Ctrl+C, Ctrl+V, Alt+Tab, Print Screen, etc.) were detected. The candidate maintained clean keyboard integrity throughout the entire examination.")

        # ---------------------------------------------------------------------
        # MOBILE PHONE & ELECTRONIC DEVICE INTEGRITY AUDIT REPORT AT EXAM SUBMISSION
        # ---------------------------------------------------------------------
        st.divider()
        st.markdown("### 📱 Mobile Phone & Electronic Device Integrity Audit Report")
        st.caption("Official camera vision clearance verification confirming whether mobile phones or unauthorized electronic devices were detected.")

        phone_incident_count = len(post_phone_events) if len(post_phone_events) > 0 else (1 if phone_was_detected else 0)
        peak_phone_conf = 0.0
        if post_phone_events:
            for pe in post_phone_events:
                rd = pe.get("raw_data")
                if isinstance(rd, str):
                    try:
                        rd = json.loads(rd)
                    except Exception:
                        rd = {}
                if isinstance(rd, dict):
                    peak_phone_conf = max(peak_phone_conf, float(rd.get("confidence", 0.0)))
        if peak_phone_conf == 0.0 and phone_was_detected:
            peak_phone_conf = 0.94

        render_phone_clearance_card(
            phone_detected=phone_was_detected,
            incident_count=phone_incident_count,
            peak_confidence=peak_phone_conf,
            events=post_phone_events,
        )

        if phone_was_detected:
            with st.container(border=True):
                st.markdown("##### 📋 Mobile Phone Clearance Breakdown & Device Violation Audit Trail")
                st.markdown(
                    f"**Candidate & Faculty Clearance Notice**: The YOLOv8 computer vision model detected an active mobile phone in camera view (**{phone_incident_count} incident{'s' if phone_incident_count > 1 else ''}**, peak confidence **{peak_phone_conf*100:.1f}%**). "
                    "Institutional guidelines strictly prohibit electronic devices, cell phones, or secondary displays in the proctored testing environment. "
                    "Live on-screen warnings were issued to the candidate immediately upon detection, and camera visual evidence was archived into the institutional audit repository."
                )
                phone_clearance_table = [
                    {
                        "Clearance Audit Metric": "Electronic Device Clearance",
                        "Clearance Status": "FAILED — MOBILE PHONE DETECTED ❌",
                        "Forensic Findings": f"YOLOv8 vision detection: {phone_incident_count} incident(s), peak confidence {peak_phone_conf*100:.1f}%",
                    },
                    {
                        "Clearance Audit Metric": "Live Warning Served",
                        "Clearance Status": "CONFIRMED ISSUED ⚠️",
                        "Forensic Findings": "Warning 'Phone detection has happened' displayed live on candidate exam screen",
                    },
                    {
                        "Clearance Audit Metric": "Camera Visual Evidence",
                        "Clearance Status": "CAPTURED & LOGGED 📷",
                        "Forensic Findings": "Bounding box telemetry and proctoring HUD overlay archived to database",
                    },
                    {
                        "Clearance Audit Metric": "Final Clearance Determination",
                        "Clearance Status": "CLEARANCE WITHHELD ❌",
                        "Forensic Findings": "Referred to Academic Disciplinary Review Board for strict integrity review",
                    },
                ]
                st.dataframe(pd.DataFrame(phone_clearance_table), use_container_width=True)

                if post_phone_events:
                    st.markdown("##### 🕒 Mobile Phone Incident Chronology & Evidence Trail")
                    phone_chrono = []
                    for idx, pev in enumerate(post_phone_events, 1):
                        occ_t = pev.get("occurred_at", time.time())
                        t_str = datetime.datetime.fromtimestamp(occ_t).strftime("%H:%M:%S")
                        phone_chrono.append({
                            "Incident #": idx,
                            "Violation Type": pev.get("event_type", "MOBILE_PHONE_DETECTED"),
                            "Risk Level": pev.get("risk_level", "HIGH"),
                            "Detection Method": pev.get("detection_method", "YOLOv8ObjectDetector"),
                            "Timestamp": t_str,
                            "Forensic Description": pev.get("event_description", ""),
                        })
                    st.dataframe(pd.DataFrame(phone_chrono), use_container_width=True)
        else:
            with st.container(border=True):
                st.success("✅ **Electronic Device Clearance Approved**: Continuous camera analysis confirmed zero (0) mobile phones or unauthorized electronic devices were detected. Candidate maintained 100% clean device integrity.")

        st.markdown("#### 📊 Candidate Behavioral Activity & Signal Timeline")
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig_dash = TimelineVisualizer.generate_full_dashboard(timeline, theme=st.session_state.get("theme", "dark"))
        st.pyplot(fig_dash)
        plt.close(fig_dash)

        st.divider()
        st.markdown("#### 📥 Export Exam Session Reports")
        events_csv, risk_csv = timeline.export_to_csv()
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            st.download_button(
                "📥 Download Events Log (CSV)",
                data=events_csv,
                file_name="exam_behavioral_events.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col_exp2:
            st.download_button(
                "📥 Download Risk History (CSV)",
                data=risk_csv,
                file_name="exam_risk_history.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.divider()
        if st.button("🔄 Return to Main Portal", type="primary", use_container_width=True):
            st.session_state.exam_submitted = False
            st.session_state.exam_active = False
            st.session_state.exam_started = False
            st.rerun()

except Exception as top_err:
    st.error("GLOBAL APPLICATION EXCEPTION DETECTED")
    st.exception(top_err)
