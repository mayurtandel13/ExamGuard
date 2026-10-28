"""
Browser Environment & Extension Interference Detection Engine
Implements realistic, rule-based detection adhering to standard web security boundaries.
"""

import re
import time
from typing import Dict, Any, Tuple, Optional, List


class BrowserEnvironmentEvaluator:
    """
    Evaluates client browser environment, parses user-agent headers,
    verifies feature support checklist, and returns standardized compatibility readiness.
    """

    SUPPORTED_BROWSERS = {
        "Chrome": 90,
        "Edge": 90,
        "Firefox": 90,
        "Brave": 90,
        "Opera": 76,
        "Safari": 15,
    }

    @staticmethod
    def parse_user_agent(ua_string: str) -> Dict[str, str]:
        """
        Parses browser name, major version, and operating system from User-Agent string.
        """
        if not ua_string:
            return {"browser": "Unknown", "version": "0.0", "os": "Unknown"}

        os_name = "Unknown"
        if "Windows NT 10.0" in ua_string or "Windows NT 11.0" in ua_string:
            os_name = "Windows 10/11"
        elif "Windows" in ua_string:
            os_name = "Windows"
        elif "Macintosh" in ua_string or "Mac OS X" in ua_string:
            os_name = "macOS"
        elif "Linux" in ua_string and "Android" not in ua_string:
            os_name = "Linux"
        elif "Android" in ua_string:
            os_name = "Android"
        elif "iPhone" in ua_string or "iPad" in ua_string:
            os_name = "iOS"

        browser_name = "Unknown"
        version = "0.0"

        # Check in order of specificity
        if "Edg/" in ua_string:
            browser_name = "Edge"
            m = re.search(r"Edg/([0-9]+(?:\.[0-9]+)*)", ua_string)
            if m:
                version = m.group(1)
        elif "OPR/" in ua_string:
            browser_name = "Opera"
            m = re.search(r"OPR/([0-9]+(?:\.[0-9]+)*)", ua_string)
            if m:
                version = m.group(1)
        elif "Brave" in ua_string:
            browser_name = "Brave"
            m = re.search(r"Chrome/([0-9]+(?:\.[0-9]+)*)", ua_string)
            if m:
                version = m.group(1)
        elif "Chrome/" in ua_string and "Chromium/" not in ua_string:
            browser_name = "Chrome"
            m = re.search(r"Chrome/([0-9]+(?:\.[0-9]+)*)", ua_string)
            if m:
                version = m.group(1)
        elif "Firefox/" in ua_string:
            browser_name = "Firefox"
            m = re.search(r"Firefox/([0-9]+(?:\.[0-9]+)*)", ua_string)
            if m:
                version = m.group(1)
        elif "Safari/" in ua_string and "Chrome/" not in ua_string:
            browser_name = "Safari"
            m = re.search(r"Version/([0-9]+(?:\.[0-9]+)*)", ua_string)
            if m:
                version = m.group(1)

        return {"browser": browser_name, "version": version, "os": os_name}

    @classmethod
    def evaluate_compatibility(
        cls,
        browser_info: Dict[str, str],
        features: Optional[Dict[str, bool]] = None,
        camera_permission: str = "GRANTED",
        mic_permission: str = "GRANTED",
        unauthorized_extension_active: bool = False,
        detected_extension_name: str = "Third-Party Browser Extension",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generates full readiness assessment checklist with warnings and status.
        """
        browser = browser_info.get("browser", "Unknown")
        version_str = browser_info.get("version", "0.0")
        try:
            major_version = int(version_str.split(".")[0])
        except (ValueError, IndexError):
            major_version = 0

        features = features or {
            "webrtc": True,
            "mutation_observer": True,
            "fullscreen": True,
            "local_storage": True,
        }

        min_version = cls.SUPPORTED_BROWSERS.get(browser)
        warnings: List[str] = []
        is_supported = False

        if min_version is None:
            status = "WARNING"
            warnings.append(f"Browser '{browser}' is not in the certified examination browser matrix.")
        elif major_version < min_version:
            status = "WARNING"
            warnings.append(f"{browser} version {version_str} is below recommended minimum version {min_version}.")
        else:
            status = "READY"
            is_supported = True

        # Check required features
        for feat, supported in features.items():
            if not supported:
                status = "WARNING"
                warnings.append(f"Required browser feature '{feat}' is not enabled.")

        # Camera Permission check
        if camera_permission.upper() == "DENIED":
            status = "WARNING"
            warnings.append("Camera / webcam hardware access was denied. Visual AI proctoring cannot operate.")
        elif camera_permission.upper() == "UNKNOWN":
            warnings.append("Camera hardware permissions have not been confirmed yet.")

        # Check for unauthorized third-party extensions
        if unauthorized_extension_active:
            status = "WARNING"
            warnings.append(
                f"Active third-party browser extension detected: '{detected_extension_name}'. "
                "All browser extensions must be disabled before starting the examination."
            )

        checklist = [
            {
                "item": "Browser Compatibility",
                "status": "PASS" if is_supported else "WARNING",
                "detail": f"{browser} {version_str} on {browser_info.get('os', 'Unknown')}",
            },
            {
                "item": "Third-Party Extension Guard",
                "status": "FAIL" if unauthorized_extension_active else "PASS",
                "detail": f"Active: {detected_extension_name} (Forbidden)" if unauthorized_extension_active else "Clean (No unauthorized extensions detected)",
            },
            {
                "item": "WebRTC Media Capture",
                "status": "PASS" if features.get("webrtc", True) else "FAIL",
                "detail": "Supported for continuous video frame streaming",
            },
            {
                "item": "DOM MutationObserver",
                "status": "PASS" if features.get("mutation_observer", True) else "FAIL",
                "detail": "Supported for interface integrity observation",
            },
            {
                "item": "Fullscreen API",
                "status": "PASS" if features.get("fullscreen", True) else "FAIL",
                "detail": "Supported for focused examination mode",
            },
            {
                "item": "Camera Permission",
                "status": "PASS" if camera_permission.upper() == "GRANTED" else ("FAIL" if camera_permission.upper() == "DENIED" else "PENDING"),
                "detail": "Physical video hardware permission",
            },
            {
                "item": "Microphone Permission",
                "status": "PASS" if mic_permission.upper() == "GRANTED" else "OPTIONAL",
                "detail": "Audio telemetry sensor",
            },
        ]

        return {
            "status": status,
            "browser": browser,
            "version": version_str,
            "os": browser_info.get("os", "Unknown"),
            "is_supported": is_supported,
            "warnings": warnings,
            "checklist": checklist,
            "unauthorized_extension_active": unauthorized_extension_active,
            "detected_extension_name": detected_extension_name,
        }


class ExtensionInterferenceClassifier:
    """
    Transparent, rule-based classification engine for observable extension interference
    and DOM integrity events.
    Enforces server-side validation so client-supplied risk scores cannot be forged.
    """

    EVENT_TYPES = {
        "PAGE_INTEGRITY_CHANGE",
        "EXAM_INTERFACE_OVERLAY",
        "ANSWER_INTERACTION_FAILURE",
        "EXAM_PAGE_NAVIGATION",
        "EXTENSION_STATUS_UNAVAILABLE",
        "BROWSER_COMPATIBILITY_WARNING",
        "DOM_MUTATION_SUSPICIOUS",
        "WINDOW_BLUR_TAB_SWITCH",
        "TAB_SWITCH",
        "TAB_SWITCH_DETECTED",
        "WINDOW_BLUR",
        "DEVTOOLS_SUSPECTED",
        "HOTKEY_SHORTCUT",
        "PRE_EXAM_EXTENSION_DETECTED",
        "EXTENSION_DETECTED",
        "EXTENSION_CLEARANCE_FLAG",
        "MOBILE_PHONE_DETECTED",
        "PHONE_DETECTED",
    }

    @classmethod
    def classify_event(cls, event_data: Dict[str, Any]) -> Tuple[str, str, str]:
        """
        Applies transparent rules to determine (risk_level, severity, rule_explanation).
        Returns risk_level in ('LOW', 'MEDIUM', 'HIGH').
        """
        event_type = event_data.get("event_type", "PAGE_INTEGRITY_CHANGE")
        details = str(event_data.get("details", "")).lower()
        desc = str(event_data.get("description", "")).lower()
        method = str(event_data.get("detection_method", "")).lower()
        occurrences = int(event_data.get("occurrences", 1))

        # Rule 0: Pre-Exam / Active Browser Extension Detected
        if event_type in ("PRE_EXAM_EXTENSION_DETECTED", "EXTENSION_DETECTED"):
            return (
                "HIGH",
                "HIGH",
                "Unauthorized third-party browser extension detected in candidate browser environment. "
                "Warning issued to candidate and alert forwarded to faculty examination board."
            )

        if event_type == "EXTENSION_CLEARANCE_FLAG":
            return (
                "HIGH",
                "CRITICAL",
                "Candidate attempted final submission with unverified or flagged browser extension history."
            )

        # Rule 1: High Risk - Verified Modification of Protected Exam Nodes or Extension Injections
        if "chrome-extension://" in details or "moz-extension://" in details:
            return (
                "HIGH",
                "CRITICAL",
                "Verified foreign script or asset injection from browser extension protocol detected."
            )

        if event_type == "PAGE_INTEGRITY_CHANGE" and ("question" in details or "radio" in details or "input" in details):
            if "removed" in details or "tampered" in details or "replaced" in details:
                return (
                    "HIGH",
                    "HIGH",
                    "Protected examination question or answer element was unexpectedly altered or removed."
                )

        if event_type == "EXAM_PAGE_NAVIGATION":
            return (
                "HIGH",
                "HIGH",
                "Unexpected page navigation or location replacement detected during active session."
            )

        if event_type == "ANSWER_INTERACTION_FAILURE" and occurrences >= 3:
            return (
                "HIGH",
                "HIGH",
                "Repeated failures or blocking while selecting answers, indicative of interaction tampering."
            )

        if event_type in ("WINDOW_BLUR_TAB_SWITCH", "TAB_SWITCH", "TAB_SWITCH_DETECTED", "WINDOW_BLUR") or "tab switch" in desc or "window blur" in desc:
            return (
                "HIGH",
                "HIGH",
                f"Candidate switched browser window, minimized tab, or backgrounded examination ({occurrences} incident{'s' if occurrences > 1 else ''}). Strict high-risk integrity violation."
            )

        if event_type in ("MOBILE_PHONE_DETECTED", "PHONE_DETECTED") or "phone" in desc or "cell" in desc:
            return (
                "HIGH",
                "HIGH",
                f"Mobile phone or unauthorized electronic device detected in proctoring camera frame ({occurrences} incident{'s' if occurrences > 1 else ''}). Strict high-risk device violation."
            )

        # Rule 2: Medium Risk - Overlays, Unverified Modifications
        if event_type == "EXAM_INTERFACE_OVERLAY":
            return (
                "MEDIUM",
                "MEDIUM",
                "An unexpected overlay element was detected covering questions or options."
            )

        if event_type == "DOM_MUTATION_SUSPICIOUS" and occurrences >= 2:
            return (
                "MEDIUM",
                "MEDIUM",
                "Repeated unexplained DOM modifications observed by MutationObserver."
            )

        if event_type == "DEVTOOLS_SUSPECTED":
            return (
                "MEDIUM",
                "MEDIUM",
                "Browser DevTools opening heuristic triggered (window dimension anomaly)."
            )

        # Rule 3: Low Risk - Potentially Legitimate UI Changes, Missing Extension
        if event_type == "EXTENSION_STATUS_UNAVAILABLE":
            return (
                "LOW",
                "LOW",
                "Optional institutional browser extension not responding or not installed (expected in unmanaged setups)."
            )

        if event_type == "BROWSER_COMPATIBILITY_WARNING":
            return (
                "LOW",
                "LOW",
                "Non-blocking browser compatibility or permission warning."
            )

        # Default fallback
        return (
            "LOW",
            "LOW",
            "Observable interface event logged. Potentially benign browser or styling change."
        )


_EVALUATOR = BrowserEnvironmentEvaluator()
_CLASSIFIER = ExtensionInterferenceClassifier()


def get_evaluator() -> BrowserEnvironmentEvaluator:
    return _EVALUATOR


def get_classifier() -> ExtensionInterferenceClassifier:
    return _CLASSIFIER
