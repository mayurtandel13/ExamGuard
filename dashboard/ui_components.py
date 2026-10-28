"""
UI Helper Components and Custom CSS for Streamlit Exam Monitoring Dashboard
Delegates to the modern ui.theme design system while preserving 100% backward compatibility.
"""

import streamlit as st
from typing import Dict, Any, List, Optional
from ui.theme import (
    get_css,
    apply_theme,
    render_html_block,
    render_risk_badge,
    render_academic_header,
    render_metric_tile,
    render_metric_card,
    render_question_matrix_summary,
    render_pre_exam_extension_warning,
    render_faculty_extension_alert_card,
    render_extension_clearance_card,
    render_phone_detection_live_warning,
    render_phone_clearance_card,
    render_portal_hero,
    render_readiness_checklist,
    render_exam_card,
    render_topbar,
    THEME_COLORS,
)


def inject_custom_css(theme: str = None):
    """Injects modern, responsive CSS with light/dark mode support based on session state."""
    active_theme = theme or st.session_state.get("theme", "dark")
    apply_theme(active_theme)
