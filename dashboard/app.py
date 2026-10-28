"""
Dashboard App Re-export Module (for backward compatibility with test suites)
"""

from app import (
    EXAM_QUESTIONS,
    DEBUG_EXAM,
    get_keyboard_monitor_singleton,
    get_cached_proctoring_worker as get_proctoring_worker_singleton,
)
