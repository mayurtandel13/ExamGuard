import unittest
from dashboard.ui_components import render_risk_badge, inject_custom_css
from dashboard.app import (
    get_proctoring_worker_singleton,
    get_keyboard_monitor_singleton,
    EXAM_QUESTIONS,
)


class TestStreamlitDashboard(unittest.TestCase):
    def test_question_dataset_integrity(self):
        """Verify mock exam question dataset contains required fields."""
        self.assertGreaterEqual(len(EXAM_QUESTIONS), 5)
        for q in EXAM_QUESTIONS:
            self.assertIn("id", q)
            self.assertIn("question", q)
            self.assertIn("options", q)
            self.assertIn("correct_answer", q)
            self.assertEqual(len(q["options"]), 4)

    def test_worker_singleton_initialization(self):
        """Verify worker singleton resource initializer returns valid worker instance."""
        worker = get_proctoring_worker_singleton(enable_yolo=False)
        self.assertIsNotNone(worker)
        self.assertTrue(hasattr(worker, "get_latest_data"))
        self.assertTrue(hasattr(worker, "get_timeline"))

    def test_ui_components(self):
        """Verify UI component helpers execute cleanly without error."""
        try:
            inject_custom_css()
        except Exception as e:
            self.fail(f"inject_custom_css raised exception: {e}")

    def test_readiness_checklist_rendering(self):
        """Verify render_readiness_checklist executes cleanly with pass and fail items."""
        from dashboard.ui_components import render_readiness_checklist
        checklist = [
            {"item": "Camera Access", "detail": "Webcam stream verified", "status": "PASS"},
            {"item": "Microphone Access", "detail": "Audio input verified", "status": "PASS"},
            {"item": "Browser Extension Guard", "detail": "Action Required", "status": "FAIL"},
        ]
        try:
            render_readiness_checklist(checklist)
        except Exception as e:
            self.fail(f"render_readiness_checklist raised exception: {e}")


if __name__ == "__main__":
    unittest.main()
