#Exam Integrity and Monitaring System

A complete modular software framework for multi-modal exam proctoring and behavioral integrity analysis.

---

## 🏛️ 1. Final Project Architecture

```
                                  +---------------------+
                                  |    Webcam Stream    |
                                  |   (Camera Capture)  |
                                  +----------+----------+
                                             |
                   +-------------------------+-------------------------+
                   |                         |                         |
        +----------v----------+   +----------v----------+   +----------v----------+
        | FaceMesh Landmarks  |   | 3D Head Pose        |   | YOLOv8 Object       |
        | (Iris & Contour)    |   | (Pitch/Yaw/Roll)    |   | (Phone/Multi-Person)|
        +----------+----------+   +----------+----------+   +----------+----------+
                   |                         |                         |
        +----------v----------+              |                         |
        | Eye Gaze &          |              |                         |
        | Attention Tracking  |              |                         |
        +----------+----------+              |                         |
                   |                         |                         |
                   +-------------------------+-------------------------+
                                             |
                                  +----------v----------+
                                  |  Keyboard Monitor   |  (System Hotkeys: Alt+Tab, Copy/Paste)
                                  +----------+----------+
                                             |
                                  +----------v----------+
                                  | Behavioral Fusion   |  Formula: w1*(1-Att) + w2*Head + w3*KB + w4*Obj
                                  | Engine & Scorer     |  Output: Cheating Probability & Risk Level
                                  +----------+----------+
                                             |
                                  +----------v----------+
                                  | Behavioral Timeline |  Chronological Event Logging & Snapshot
                                  | & Session Logger    |  Metrics (CSV Export & Summary)
                                  +----------+----------+
                                             |
                                  +----------v----------+
                                  | Streamlit Dashboard |  12 Live Monitoring & Analytics Sections
                                  | & Matplotlib HUD    |  (Risk Badges: LOW 🟢 / MEDIUM ⚠️ / HIGH 🚨)
                                  +---------------------+
```

---

## 📁 2. File Structure

```
MINI_PROJECT_CLG/
├── config.py                     # Global thresholds, model parameters, and fusion weights
├── requirements.txt              # System dependency specifications
├── README.md                     # Comprehensive documentation & file guide
├── app.py                        # Root entry point for Streamlit Application
├── camera/                       # Camera Stream Management Component
│   ├── __init__.py
│   └── capture.py                # CameraCapture stream abstraction & synthetic fallback
├── face/                         # Facial Mesh & Landmark Component
│   ├── __init__.py
│   └── landmarks.py              # FaceLandmarkExtractor MediaPipe interface
├── head_pose/                    # Head Orientation Component
│   ├── __init__.py
│   └── estimator.py              # HeadPoseEstimator (Pitch, Yaw, Roll, solvePnP)
├── gaze/                         # Eye Gaze & Attention Component
│   ├── __init__.py
│   └── tracker.py                # GazeTracker (Iris offset, EAR & Attention Score)
├── keyboard/                     # Input Telemetry Component
│   ├── __init__.py
│   └── monitor.py                # KeyboardMonitor (Shortcut listener & simulated trigger)
├── yolo/                         # Object & Person Detection Component
│   ├── __init__.py
│   └── detector.py               # YOLOObjectDetector (Phone & Multi-Person counter)
├── event_logging/                # Audit & Data Logging Component
│   ├── __init__.py
│   └── logger.py                 # SessionDataLogger (Telemetry & event recorder)
├── fusion/                       # Multi-Modal Behavioral Fusion Engine
│   ├── __init__.py
│   └── engine.py                 # BehavioralFusionEngine (Research formulation & EMA)
├── risk_scoring/                 # Risk Classification Component
│   ├── __init__.py
│   └── scorer.py                 # RiskScorer (Low / Medium / High risk evaluator)
├── timeline/                     # Behavioral Timeline Visualization Component
│   ├── __init__.py
│   ├── timeline.py               # BehavioralTimeline event recorder & summary engine
│   └── visualizer.py             # TimelineVisualizer (Matplotlib multi-panel dashboard)
├── dashboard/                    # User Interface Component
│   ├── __init__.py
│   ├── ui_components.py          # Custom CSS & risk badge renderers
│   └── app.py                    # Streamlit 12-section Proctoring Dashboard
├── utils/                        # Visual Utilities Component
│   ├── __init__.py
│   └── draw.py                   # HUDDrawer (Video frame bounding boxes & overlays)
└── tests/                        # Automated Verification Test Suite
    ├── __init__.py
    ├── test_structure.py         # Unit test suite verifying modular structure
    ├── test_camera.py            # Unit test suite for Camera Capture
    ├── test_face_landmarks.py    # Unit test suite for MediaPipe FaceMesh
    ├── test_head_pose.py         # Unit test suite for 3D Head Pose
    ├── test_gaze.py              # Unit test suite for Eye Gaze & Attention
    ├── test_yolo.py              # Unit test suite for YOLO Detector
    ├── test_keyboard.py          # Unit test suite for Keyboard Monitor
    ├── test_fusion_engine.py     # Unit test suite for Behavioral Fusion Engine
    ├── test_behavioral_fusion_scenarios.py # Scenarios A-G verification
    ├── test_behavioral_timeline.py # Timeline & Matplotlib visualization tests
    ├── test_dashboard.py        # Streamlit dashboard tests
    ├── verify_integrated_pipeline.py # 16-point integrated pipeline verification
    ├── test_end_to_end_integration.py # Full E2E multi-frame test runner
    └── run_controlled_test_protocol.py # 10-scenario protocol runner
```

---

## ⚙️ 3. How to Install

1. Clone or navigate to the repository directory:
   ```bash
   cd c:\Users\Mayur Tandel\OneDrive\Desktop\HTMLCSS\MINI_PROJECT_CLG
   ```

2. Create and activate a Python virtual environment (Python 3.10–3.12 recommended):
   ```bash
   python -m venv venv312
   .\venv312\Scripts\activate
   ```

3. Install required system dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🚀 4. How to Run

### Streamlit Web Proctoring Application
Run the Streamlit frontend dashboard:
```bash
.\venv312\Scripts\python.exe -m streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 5. How to Test

### Run All Unit & Integration Tests (54 Test Cases)
```bash
.\venv312\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

### Run 16-Point Integrated Pipeline Verification
```bash
.\venv312\Scripts\python.exe -m unittest tests/verify_integrated_pipeline.py
```

### Run Controlled Protocol Test (10 Behavioral Scenarios)
```bash
.\venv312\Scripts\python.exe tests/run_controlled_test_protocol.py
```

---

## ⚠️ 6. Known Limitations

1. **Heuristic Behavioral Risk Estimation**: The system estimates a continuous **Behavioral Risk Index** to assist human proctors. It is **NOT** a definitive cheating classifier.
2. **Partial Occlusion & Lighting Sensitivity**: Extremely low ambient lighting or severe head yaw exceeding $60^\circ$ may drop facial mesh landmark detection confidence.
3. **OS-Level Keyboard Hook Permissions**: Keyboard shortcut hook listeners (`pynput`) require standard desktop input listener permissions.

---

## 🔮 7. Future Improvements

1. **Temporal Recurrent Network Modeling**: Transition from heuristic EMA fusion to recurrent temporal models (e.g., LSTM / Transformer architectures) trained on annotated multi-modal proctoring benchmarks.
2. **Audio Monitoring & Voice Detection**: Integrate ambient acoustic monitoring and directional speaker classification (VAD / PyAnnote).
3. **WebRTC Remote Streaming**: Deploy WebRTC video pipelines for low-latency candidate-to-proctor remote browser streaming.
