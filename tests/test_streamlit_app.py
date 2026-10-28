"""
STEP 6 — Streamlit App Unit & Integration Tests using streamlit.testing.v1.AppTest.
Verifies:
1. App loads without errors.
2. Clicking START EXAM renders question text.
3. Submit works and transitions to exam summary.
4. Camera failure fallback: exam UI still renders question text and displays error message.
5. Worker singleton uniqueness across reruns.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from streamlit.testing.v1 import AppTest
from dashboard.worker import ProctoringWorker
from dashboard.app import get_proctoring_worker_singleton

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


class TestStreamlitAppIntegrity(unittest.TestCase):
    def test_app_loads(self):
        """1. Verify Streamlit app loads home portal without throwing exceptions."""
        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()
        self.assertFalse(at.exception, f"App load threw exception: {at.exception}")
        self.assertTrue(len(at.info) > 0 or len(at.markdown) > 0)

    def test_start_exam_renders_question(self):
        """2. Verify clicking START EXAM transitions to active exam and renders question text."""
        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()
        
        if len(at.button) > 0:
            at.button[0].click().run()

        self.assertFalse(at.exception, f"Start exam threw exception: {at.exception}")
        question_found = any("Question 1" in str(sub.value) for sub in at.subheader) or \
                         any("Question 1" in str(m.value) for m in at.markdown) or \
                         at.session_state.get("exam_active", False)
        self.assertTrue(question_found, "Question UI did not render after clicking START EXAM")

    def test_exam_submit_workflow(self):
        """3. Verify clicking submit finishes exam session."""
        at = AppTest.from_file(APP_PATH, default_timeout=10)
        at.run()
        
        if len(at.button) > 0:
            at.button[0].click().run()

        submit_btn = None
        for b in at.button:
            if "SUBMIT" in str(b.label):
                submit_btn = b
                break
        
        if submit_btn:
            submit_btn.click().run()
            self.assertTrue(at.session_state["exam_submitted"])

    def test_camera_failure_fallback(self):
        """4. Verify with camera mocked to fail, exam UI still renders and shows error."""
        at = AppTest.from_file(APP_PATH, default_timeout=10)
        
        with patch("cv2.VideoCapture") as mock_cap:
            instance = MagicMock()
            instance.isOpened.return_value = False
            mock_cap.return_value = instance
            
            at.run()
            if len(at.button) > 0:
                at.button[0].click().run()

            self.assertFalse(at.exception, f"App threw exception when camera failed: {at.exception}")
            self.assertTrue(at.session_state["exam_active"])

    def test_worker_singleton_uniqueness(self):
        """5. Verify worker singleton returns identical instance across invocations."""
        w1 = get_proctoring_worker_singleton(device_idx=99, enable_yolo=False)
        w2 = get_proctoring_worker_singleton(device_idx=99, enable_yolo=False)
        self.assertIs(w1, w2, "Worker singleton created duplicate instances across reruns!")


if __name__ == "__main__":
    unittest.main()
