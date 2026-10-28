# Exam Integrity Browser Extension — ExamGuard AI

This is the official Manifest V3 extension for **ExamGuard AI (Exam Monitoring & Integrity Assurance Platform)**.

---

## 📌 How It Works & Detection Capabilities
1. **Multi-Vector Presence Detection:**
   - Injects secure DOM markers (`data-extension-id="examguard-extension-v1"`, `#examguard-extension-marker`).
   - Dispatches continuous bi-directional ping-pong handshakes (`EXAM_INTEGRITY_PING` / `EXAM_INTEGRITY_PONG`) across all frames (`all_frames: true`).
   - Dispatches HTTP beacon telemetry directly to the local ExamGuard backend at `http://127.0.0.1:8585/api/extension_event`.
2. **Instant Visual Feedback:**
   - **Pre-Exam Scanner:** Immediately recognizes the extension, updates the checklist badge to `FAIL (Active: Exam Integrity Extension)`, displays the high-visibility proctoring warning, and forwards the alert to the Faculty Dashboard.
   - **Active Exam HUD:** Connects and monitors DOM integrity in real time.

---

## 🚀 How to Load / Reload in Google Chrome

If you already loaded the extension earlier:
1. Open Chrome and go to `chrome://extensions/`
2. Find **Exam Integrity Extension**.
3. Click the **🔄 Reload (Refresh)** icon on the extension card so Chrome reloads the updated `manifest.json` and `content.js`.
4. Refresh your ExamGuard page (`http://localhost:8501`).

If loading for the first time:
1. Open Google Chrome.
2. Go to `chrome://extensions/`
3. Turn **ON** **Developer mode** (toggle in the top-right corner).
4. Click **Load unpacked** (top-left button).
5. Select this folder:
   `C:\Users\Mayur Tandel\OneDrive\Desktop\HTMLCSS\MINI_PROJECT_CLG\extension`
6. Open or refresh `http://localhost:8501`.
   ExamGuard will immediately recognize the extension!
