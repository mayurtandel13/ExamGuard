"""
Browser Extension Detection & Integrity Monitoring Package
"""

from extension_monitor.detector import (
    BrowserEnvironmentEvaluator,
    ExtensionInterferenceClassifier,
    get_evaluator,
    get_classifier,
)

__all__ = [
    "BrowserEnvironmentEvaluator",
    "ExtensionInterferenceClassifier",
    "get_evaluator",
    "get_classifier",
]
