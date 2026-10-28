"""
Centralized UI Theming & Component System for AI-Based Exam Monitoring System
Provides:
- WCAG AA compliant Light and Dark mode styling with CSS variables
- Clean, academic typography (Inter font stack) and 8px grid spacing
- Reusable UI cards, badges, sticky top bars, metric chips, and checklist grids
- Consistent risk color scheme: Low = #22C55E, Medium = #F59E0B, High = #EF4444
"""

import streamlit as st
from typing import Dict, Any, List, Optional

THEME_COLORS = {
    "dark": {
        "bg": "#0B1220",
        "surface": "#111A2E",
        "surface_2": "#17223B",
        "border": "#24304A",
        "border_subtle": "#1B2742",
        "text": "#E6EAF2",
        "text_muted": "#9AA6BD",
        "primary": "#4F6BFF",
        "primary_hover": "#6B82FF",
        "primary_glow": "rgba(79, 107, 255, 0.25)",
        "success": "#22C55E",
        "success_bg": "rgba(34, 197, 94, 0.12)",
        "success_border": "rgba(34, 197, 94, 0.35)",
        "warning": "#F59E0B",
        "warning_bg": "rgba(245, 158, 11, 0.12)",
        "warning_border": "rgba(245, 158, 11, 0.35)",
        "danger": "#EF4444",
        "danger_bg": "rgba(239, 68, 68, 0.12)",
        "danger_border": "rgba(239, 68, 68, 0.35)",
        "card_shadow": "0 4px 20px -2px rgba(0, 0, 0, 0.5)",
        "header_bg": "rgba(17, 26, 46, 0.92)",
        "chart_bg": "#111A2E",
        "chart_text": "#E6EAF2",
        "chart_grid": "#24304A",
    },
    "light": {
        "bg": "#F4F6FB",
        "surface": "#FFFFFF",
        "surface_2": "#F0F3FA",
        "border": "#E1E6F0",
        "border_subtle": "#EBEFF7",
        "text": "#0F172A",
        "text_muted": "#5B6780",
        "primary": "#4F6BFF",
        "primary_hover": "#3B54E0",
        "primary_glow": "rgba(79, 107, 255, 0.18)",
        "success": "#16A34A",
        "success_bg": "rgba(22, 163, 74, 0.12)",
        "success_border": "rgba(22, 163, 74, 0.32)",
        "warning": "#D97706",
        "warning_bg": "rgba(217, 119, 6, 0.12)",
        "warning_border": "rgba(217, 119, 6, 0.32)",
        "danger": "#DC2626",
        "danger_bg": "rgba(220, 38, 38, 0.12)",
        "danger_border": "rgba(220, 38, 38, 0.32)",
        "card_shadow": "0 4px 16px -2px rgba(15, 23, 42, 0.06), 0 2px 6px -1px rgba(15, 23, 42, 0.04)",
        "header_bg": "rgba(255, 255, 255, 0.92)",
        "chart_bg": "#FFFFFF",
        "chart_text": "#0F172A",
        "chart_grid": "#E1E6F0",
    },
}


def get_css(theme: str = "dark") -> str:
    """Generates modern scoped CSS variables and rules based on current theme."""
    t = THEME_COLORS.get(theme, THEME_COLORS["dark"])

    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {{
    --bg: {t["bg"]};
    --surface: {t["surface"]};
    --surface-2: {t["surface_2"]};
    --border: {t["border"]};
    --border-subtle: {t["border_subtle"]};
    --text: {t["text"]};
    --text-muted: {t["text_muted"]};
    --primary: {t["primary"]};
    --primary-hover: {t["primary_hover"]};
    --primary-glow: {t["primary_glow"]};
    --success: {t["success"]};
    --success-bg: {t["success_bg"]};
    --success-border: {t["success_border"]};
    --warning: {t["warning"]};
    --warning-bg: {t["warning_bg"]};
    --warning-border: {t["warning_border"]};
    --danger: {t["danger"]};
    --danger-bg: {t["danger_bg"]};
    --danger-border: {t["danger_border"]};
    --card-shadow: {t["card_shadow"]};
    --header-bg: {t["header_bg"]};
}}

/* Universal font and base background */
html, body, [data-testid="stAppViewContainer"], .main {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-size: 15px;
    letter-spacing: -0.005em;
}}

/* Clean up Streamlit header & footer */
header[data-testid="stHeader"] {{
    background: transparent !important;
    height: 2.4rem !important;
    z-index: 99 !important;
}}
footer {{
    display: none !important;
}}

.main .block-container {{
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 100% !important;
}}

/* Sidebar Styling */
section[data-testid="stSidebar"] {{
    background-color: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] label {{
    color: var(--text) !important;
}}
.sidebar-logo-text {{
    color: var(--text) !important;
    font-weight: 800 !important;
}}
.sidebar-logo-sub {{
    color: var(--text-muted) !important;
}}

/* Headings */
h1, h2, h3, h4, h5, h6 {{
    color: var(--text) !important;
    font-weight: 700 !important;
    letter-spacing: -0.015em !important;
}}

/* Streamlit Containers with border */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    background-color: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    box-shadow: var(--card-shadow) !important;
    padding: 6px !important;
    transition: border-color 0.15s ease;
}}

/* Custom Card Classes */
.app-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 18px 22px;
    margin-bottom: 16px;
    box-shadow: var(--card-shadow);
}}

.app-card-title {{
    font-size: 1.15rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
}}

/* Hero Section */
.hero-header {{
    background: linear-gradient(135deg, rgba(79, 107, 255, 0.14) 0%, rgba(99, 102, 241, 0.04) 100%), var(--surface);
    border: 1px solid var(--border);
    border-left: 6px solid var(--primary);
    border-radius: 16px;
    padding: 22px 28px;
    margin-bottom: 22px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 16px;
    box-shadow: var(--card-shadow);
}}
.hero-title {{
    font-size: 1.7rem;
    font-weight: 800;
    color: var(--text);
    margin: 0;
    display: flex;
    align-items: center;
    gap: 12px;
    letter-spacing: -0.02em;
}}
.hero-title-highlight {{
    color: var(--primary);
    background: var(--primary-glow);
    padding: 2px 12px;
    border-radius: 8px;
    border: 1px solid rgba(79, 107, 255, 0.3);
}}
.hero-subtitle {{
    font-size: 0.92rem;
    color: var(--text-muted);
    margin-top: 6px;
    line-height: 1.4;
}}
.hero-badge-chip {{
    background: var(--surface-2);
    border: 1px solid var(--border);
    color: var(--text);
    font-size: 0.85rem;
    font-weight: 600;
    padding: 8px 16px;
    border-radius: 10px;
    display: inline-flex;
    align-items: center;
    gap: 8px;
}}

/* Sticky Top Bar for Exam */
.exam-sticky-topbar {{
    position: sticky;
    top: 0;
    z-index: 100;
    background: var(--header-bg);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 12px 20px;
    margin-bottom: 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
    box-shadow: var(--card-shadow);
}}

/* Question Display */
.question-heading {{
    font-size: 1.35rem;
    font-weight: 600;
    color: var(--text);
    line-height: 1.5;
    margin: 12px 0 16px 0;
}}

/* Full-width Selectable Radio Option Cards */
.stRadio > div {{
    gap: 10px !important;
}}
.stRadio label {{
    background: var(--surface) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 14px 18px !important;
    margin-bottom: 6px !important;
    display: flex !important;
    align-items: flex-start !important;
    cursor: pointer !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    width: 100% !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
}}
.stRadio label:hover {{
    background: var(--surface-2) !important;
    border-color: var(--primary) !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(79, 107, 255, 0.12) !important;
}}
.stRadio label > div:first-child {{
    margin-top: 3px !important;
}}
.stRadio label p {{
    font-size: 1.05rem !important;
    font-weight: 500 !important;
    color: var(--text) !important;
    line-height: 1.45 !important;
    margin: 0 !important;
}}

/* Buttons */
.stButton > button {{
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 8px 18px !important;
    font-size: 0.95rem !important;
    transition: all 0.18s ease-in-out !important;
}}
.stButton > button[kind="primary"] {{
    background: var(--primary) !important;
    border: 1px solid var(--primary) !important;
    color: #ffffff !important;
    box-shadow: 0 2px 8px var(--primary-glow) !important;
}}
.stButton > button[kind="primary"]:hover {{
    background: var(--primary-hover) !important;
    border-color: var(--primary-hover) !important;
    transform: translateY(-1px);
}}
.stButton > button[kind="secondary"] {{
    background: var(--surface-2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
}}
.stButton > button[kind="secondary"]:hover {{
    border-color: var(--primary) !important;
    background: var(--surface) !important;
    color: var(--primary) !important;
}}

/* Mini Metric Cards for Proctoring Grid */
.mini-metric-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 14px;
    margin-bottom: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    transition: transform 0.15s ease, border-color 0.15s ease;
}}
.mini-metric-card:hover {{
    border-color: var(--primary);
    transform: translateY(-1px);
}}
.mini-metric-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}}
.mini-metric-label {{
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--text-muted);
    letter-spacing: 0.05em;
    display: flex;
    align-items: center;
    gap: 5px;
}}
.mini-metric-value {{
    font-size: 1.4rem;
    font-weight: 800;
    color: var(--text);
    margin: 2px 0;
    line-height: 1.2;
}}
.mini-metric-sub {{
    font-size: 0.78rem;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

/* Soft Tinted Status Pills */
.pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 20px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    white-space: nowrap;
}}
.pill-pass {{
    background-color: var(--success-bg);
    color: var(--success);
    border: 1px solid var(--success-border);
}}
.pill-warn {{
    background-color: var(--warning-bg);
    color: var(--warning);
    border: 1px solid var(--warning-border);
}}
.pill-fail {{
    background-color: var(--danger-bg);
    color: var(--danger);
    border: 1px solid var(--danger-border);
}}
.pill-neutral {{
    background-color: var(--surface-2);
    color: var(--text-muted);
    border: 1px solid var(--border);
}}
.pill-primary {{
    background-color: var(--primary-glow);
    color: var(--primary);
    border: 1px solid rgba(79, 107, 255, 0.35);
}}

/* Status dot */
.status-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
}}
.dot-pass {{ background-color: var(--success); box-shadow: 0 0 6px var(--success); }}
.dot-warn {{ background-color: var(--warning); box-shadow: 0 0 6px var(--warning); }}
.dot-fail {{ background-color: var(--danger); box-shadow: 0 0 6px var(--danger); }}
.dot-neutral {{ background-color: var(--text-muted); }}

/* Risk Banner */
.risk-badge {{
    padding: 10px 16px;
    border-radius: 10px;
    font-weight: 700;
    font-size: 0.92rem;
    text-align: center;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    letter-spacing: 0.02em;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}}
.risk-low {{
    background-color: var(--success-bg);
    color: var(--success);
    border: 1.5px solid var(--success-border);
}}
.risk-medium {{
    background-color: var(--warning-bg);
    color: var(--warning);
    border: 1.5px solid var(--warning-border);
}}
.risk-high {{
    background-color: var(--danger-bg);
    color: var(--danger);
    border: 1.5px solid var(--danger-border);
}}

/* Pinned Non-Overlapping Violation Banner */
.violation-banner {{
    background: var(--danger-bg);
    border: 2px solid var(--danger-border);
    border-left: 6px solid var(--danger);
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 16px;
    box-shadow: 0 4px 16px rgba(239, 68, 68, 0.15);
    animation: fadeIn 0.25s ease-out;
}}

@keyframes pulseIcon {{
    0% {{ transform: scale(1); }}
    50% {{ transform: scale(1.15); }}
    100% {{ transform: scale(1); }}
}}
.pulse-icon {{
    display: inline-block;
    animation: pulseIcon 1.5s infinite ease-in-out;
    font-size: 1.4rem;
}}

/* Expanders */
div[data-testid="stExpander"] {{
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}}
div[data-testid="stExpander"] summary {{
    color: var(--text) !important;
    font-weight: 600 !important;
    padding: 10px 14px !important;
}}

/* Tabs */
button[data-baseweb="tab"] {{
    color: var(--text-muted) !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    border-radius: 8px 8px 0 0 !important;
    padding: 10px 16px !important;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    color: var(--primary) !important;
    border-bottom: 2px solid var(--primary) !important;
    background: transparent !important;
}}

/* Dataframe / Table styling */
div[data-testid="stDataFrame"] {{
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}}

/* Progress bar override */
div[data-testid="stProgress"] > div > div {{
    background-color: var(--surface-2) !important;
    border-radius: 10px !important;
}}
div[data-testid="stProgress"] > div > div > div {{
    background: linear-gradient(90deg, var(--primary), var(--primary-hover)) !important;
    border-radius: 10px !important;
}}

/* Legacy card classes compatibility */
.portal-header {{
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-left: 6px solid var(--primary) !important;
    border-radius: 14px !important;
    padding: 18px 24px !important;
    margin-bottom: 18px !important;
    color: var(--text) !important;
}}
.portal-title {{
    color: var(--text) !important;
    font-weight: 800 !important;
}}
.portal-title-highlight {{
    color: var(--primary) !important;
    background: var(--primary-glow) !important;
    border: 1px solid rgba(79, 107, 255, 0.3) !important;
}}
.portal-subtitle {{
    color: var(--text-muted) !important;
}}
.portal-student-chip {{
    background: var(--surface-2) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
}}
.metric-tile {{
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 14px 16px !important;
    color: var(--text) !important;
    box-shadow: var(--card-shadow) !important;
}}
.metric-tile-title {{
    color: var(--text-muted) !important;
}}
.metric-tile-val {{
    color: var(--text) !important;
}}
.metric-tile-sub {{
    color: var(--text-muted) !important;
}}
.clearance-fail-box {{
    background: var(--danger-bg) !important;
    border: 2px solid var(--danger-border) !important;
    border-left: 8px solid var(--danger) !important;
    border-radius: 12px !important;
    padding: 20px 24px !important;
    color: var(--text) !important;
}}
.clearance-pass-box {{
    background: var(--success-bg) !important;
    border: 2px solid var(--success-border) !important;
    border-left: 8px solid var(--success) !important;
    border-radius: 12px !important;
    padding: 20px 24px !important;
    color: var(--text) !important;
}}
.ext-warning-box {{
    background: var(--danger-bg) !important;
    border: 2px solid var(--danger-border) !important;
    border-left: 8px solid var(--danger) !important;
    border-radius: 12px !important;
    padding: 18px 22px !important;
    color: var(--text) !important;
}}
.ext-faculty-card {{
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-left: 6px solid var(--danger) !important;
    border-radius: 12px !important;
    padding: 14px 18px !important;
    color: var(--text) !important;
}}
</style>
"""


def apply_theme(theme: str = "dark"):
    """Injects CSS styling into the Streamlit session."""
    st.markdown(get_css(theme), unsafe_allow_html=True)


def render_html_block(html_content: str):
    """Safely renders HTML markup in Streamlit without accidental Markdown code-block interpretation.

    Uses st.html (Streamlit 1.33+) when available to insert HTML directly into the DOM
    without passing it through Markdown parsing. Falls back to st.markdown with unsafe_allow_html=True.
    """
    clean_html = html_content.strip()
    if hasattr(st, "html"):
        st.html(clean_html)
    else:
        unindented = "".join([line.lstrip() for line in clean_html.splitlines() if line.strip()])
        st.markdown(unindented, unsafe_allow_html=True)


def render_risk_badge(risk_level: str, score: float = 0.0):
    """Renders theme-consistent risk badge."""
    lvl = str(risk_level).upper()
    if lvl == "LOW":
        css_cls = "risk-low"
        icon = "🟢"
    elif lvl == "MEDIUM":
        css_cls = "risk-medium"
        icon = "⚠️"
    else:
        css_cls = "risk-high"
        icon = "🚨"

    html = (
        f'<div class="risk-badge {css_cls}">'
        f'<span>{icon}</span>'
        f'<span>INTEGRITY RISK: <strong>{lvl}</strong> &nbsp;|&nbsp; Score: <strong>{score:.2f}</strong></span>'
        f'</div>'
    )
    render_html_block(html)


def render_metric_card(label: str, value: Any, icon: str = "📊", status: str = "neutral", subtitle: str = ""):
    """Renders compact mini-metric card with status dot and icon for HUD grid."""
    dot_cls = f"dot-{status}"
    html = (
        f'<div class="mini-metric-card">'
        f'<div class="mini-metric-header">'
        f'<span class="mini-metric-label"><span>{icon}</span> <span>{label}</span></span>'
        f'<span class="status-dot {dot_cls}"></span>'
        f'</div>'
        f'<div class="mini-metric-value">{value}</div>'
        f'<div class="mini-metric-sub">{subtitle}</div>'
        f'</div>'
    )
    render_html_block(html)


def render_portal_hero(
    title: str = "Exam Monitoring and Integrity System",
    subtitle: str = "Intelligent Multi-Modal Proctoring & Browser Integrity Assurance Platform",
    student_name: str = "Mayur Tandel",
    student_id: str = "STU-2026-081",
    department: str = "Computer Science & Engineering",
    roll_number: str = "CS-2026-081",
):
    """Renders the top hero banner with gradient accent and student profile chip."""
    html = (
        f'<div class="hero-header">'
        f'<div style="flex: 1 1 400px;">'
        f'<h1 class="hero-title">'
        f'<span>🎓</span>'
        f'<span>Exam Monitoring and <span class="hero-title-highlight">Integrity System</span></span>'
        f'</h1>'
        f'<div class="hero-subtitle">{subtitle} &nbsp;•&nbsp; <strong>{department}</strong></div>'
        f'</div>'
        f'<div class="hero-badge-chip">'
        f'<span style="font-size: 1.2rem;">👤</span>'
        f'<div>'
        f'<div style="font-size: 0.92rem; font-weight: 700;">{student_name}</div>'
        f'<div style="font-size: 0.78rem; color: var(--text-muted);">{student_id} &nbsp;|&nbsp; {roll_number}</div>'
        f'</div>'
        f'<span class="pill pill-pass" style="margin-left: 8px;">VERIFIED CANDIDATE</span>'
        f'</div>'
        f'</div>'
    )
    render_html_block(html)


def render_exam_card(
    title: str = "AI & ML Certification Examination",
    course_code: str = "CS-DS-2026-X",
    duration_mins: int = 60,
    total_questions: int = 5,
    proctoring_features: Optional[List[str]] = None,
):
    """Renders a modern card summarizing the exam details."""
    features = proctoring_features or [
        "📹 3D Head Pose & Gaze HUD",
        "📱 YOLOv8 Mobile Phone Detection",
        "⌨️ Keystroke Hook Guard",
        "🛡️ Browser DOM Integrity Observer",
    ]
    feat_chips = "".join([f'<span class="pill pill-primary" style="margin: 3px 4px;">{f}</span>' for f in features])

    html = (
        f'<div class="app-card">'
        f'<div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px;">'
        f'<div>'
        f'<span class="pill pill-primary">ACTIVE ASSESSMENT</span>'
        f'<h2 style="font-size: 1.35rem; font-weight: 700; margin: 8px 0 4px 0; color: var(--text);">'
        f'{title}'
        f'</h2>'
        f'<div style="color: var(--text-muted); font-size: 0.88rem;">Course Code: <code>{course_code}</code> &nbsp;|&nbsp; Certified Academic Proctored Session</div>'
        f'</div>'
        f'<div style="display: flex; gap: 8px; flex-wrap: wrap;">'
        f'<span class="pill pill-neutral">⏱️ {duration_mins} Minutes</span>'
        f'<span class="pill pill-neutral">📝 {total_questions} Questions (MCQ)</span>'
        f'<span class="pill pill-pass">Passing: 60%</span>'
        f'</div>'
        f'</div>'
        f'<div style="margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border);">'
        f'<div style="font-size: 0.82rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 6px;">'
        f'Active Proctoring & Integrity Guards:'
        f'</div>'
        f'<div style="display: flex; flex-wrap: wrap; gap: 4px;">'
        f'{feat_chips}'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    render_html_block(html)


def render_readiness_checklist(checklist_items: List[Dict[str, Any]]):
    """Renders the browser readiness checklist as a clean grid of status chips with progress summary."""
    total = len(checklist_items)
    passed = sum(1 for item in checklist_items if item.get("status") in ["PASS", "READY", "OPTIMAL"])
    all_clean = (passed == total)

    summary_cls = "pill-pass" if all_clean else "pill-warn"
    summary_text = f"✅ {passed}/{total} Checks Passed — Environment Ready" if all_clean else f"⚠️ {passed}/{total} Passed — Action Required"

    chips_html = []
    for item in checklist_items:
        st_val = item.get("status", "PASS")
        is_pass = st_val in ["PASS", "READY", "OPTIMAL"]
        p_cls = "pill-pass" if is_pass else "pill-fail"
        icon = "✔" if is_pass else "✖"
        title = item.get("item", "Check")
        detail = item.get("detail", "")

        chips_html.append(
            f'<div style="background: var(--surface-2); border: 1px solid var(--border); border-radius: 10px; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center; gap: 8px;">'
            f'<div>'
            f'<div style="font-weight: 600; font-size: 0.9rem; color: var(--text);">{title}</div>'
            f'<div style="font-size: 0.78rem; color: var(--text-muted);">{detail}</div>'
            f'</div>'
            f'<span class="pill {p_cls}">{icon} {st_val}</span>'
            f'</div>'
        )

    grid_content = "".join(chips_html)

    html = (
        f'<div class="app-card">'
        f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; flex-wrap: wrap; gap: 8px;">'
        f'<div style="font-weight: 700; font-size: 1.05rem; color: var(--text); display: flex; align-items: center; gap: 8px;">'
        f'<span>🛡️</span> <span>Pre-Examination Hardware & Environment Verification</span>'
        f'</div>'
        f'<span class="pill {summary_cls}">{summary_text}</span>'
        f'</div>'
        f'<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 10px;">'
        f'{grid_content}'
        f'</div>'
        f'</div>'
    )
    render_html_block(html)


def render_phone_detection_live_warning(incident_count: int = 1, peak_confidence: float = 0.0):
    """Renders modern live on-screen alert banner when mobile phone is detected."""
    conf_str = f" (Confidence: {peak_confidence * 100:.1f}%)" if peak_confidence > 0 else ""
    html = (
        f'<div class="violation-banner">'
        f'<div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">'
        f'<span style="font-size: 1.12rem; font-weight: 800; color: var(--danger); display: flex; align-items: center; gap: 10px;">'
        f'<span class="pulse-icon">🚨</span> <span>HIGH-RISK PROCTORING ALERT: Mobile Phone Detected in Camera Feed!</span>'
        f'</span>'
        f'<span class="pill pill-fail">PHONE DETECTED (HIGH RISK)</span>'
        f'</div>'
        f'<div style="margin-top: 8px; font-size: 0.94rem; color: var(--text); line-height: 1.55;">'
        f'⚠️ <strong>Warning: Phone detection has happened!</strong> The proctoring computer vision engine detected an unauthorized mobile phone in your camera frame (Incident #{incident_count}{conf_str}). '
        f'Unauthorized electronic devices are strictly prohibited during proctored examinations. '
        f'<strong>Remove the phone immediately.</strong> This incident has been logged with video forensic evidence and submitted for proctor audit.'
        f'</div>'
        f'</div>'
    )
    render_html_block(html)


def render_phone_clearance_card(
    phone_detected: bool,
    incident_count: int = 0,
    peak_confidence: float = 0.0,
    events: Optional[List[Dict[str, Any]]] = None,
):
    """Renders theme-adaptive post-submission phone clearance card."""
    if phone_detected:
        cnt_label = incident_count if incident_count > 0 else (len(events) if events else 1)
        conf_label = f"{peak_confidence * 100:.1f}%" if peak_confidence > 0 else "High"
        html = (
            f'<div class="clearance-fail-box">'
            f'<div style="display: flex; align-items: flex-start; gap: 14px;">'
            f'<span style="font-size: 32px;">📱</span>'
            f'<div style="flex: 1;">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">'
            f'<span style="font-size: 1.2rem; font-weight: 800; color: var(--danger); letter-spacing: -0.01em;">'
            f'DEVICE INTEGRITY REPORT: MOBILE PHONE WAS DETECTED DURING EXAM'
            f'</span>'
            f'<span class="pill pill-fail" style="font-size: 12px; padding: 5px 12px;">CLEARANCE WITHHELD ❌</span>'
            f'</div>'
            f'<div style="margin-top: 6px; font-size: 0.94rem; color: var(--text); line-height: 1.5;">'
            f'<strong>Audit Notice:</strong> The proctoring computer vision engine recorded that an unauthorized mobile phone was detected in the camera stream <strong>{cnt_label} time{"s" if cnt_label > 1 else ""}</strong> (Peak Confidence: <strong>{conf_label}</strong>).'
            f'</div>'
            f'<div style="margin-top: 10px; background: var(--surface); border: 1px solid var(--danger-border); border-radius: 8px; padding: 12px 16px; font-size: 0.88rem; color: var(--text);">'
            f'<ul style="margin: 0; padding-left: 18px; line-height: 1.6;">'
            f'<li><strong>Live Device Alert:</strong> On-screen warning was displayed stating phone detection has happened.</li>'
            f'<li><strong>Camera Evidence Logged:</strong> Frame snapshots and timestamps were logged to the institutional archive.</li>'
            f'<li><strong>Prohibited Device Violation:</strong> Secondary communication devices are strictly banned in examination view.</li>'
            f'<li><strong>Final Status:</strong> Candidate examination clearance is withheld; session is referred to the Academic Disciplinary Board.</li>'
            f'</ul>'
            f'</div>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
    else:
        html = (
            f'<div class="clearance-pass-box">'
            f'<div style="display: flex; align-items: center; gap: 14px;">'
            f'<span style="font-size: 32px;">📱</span>'
            f'<div style="flex: 1;">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">'
            f'<span style="font-size: 1.2rem; font-weight: 800; color: var(--success); letter-spacing: -0.01em;">'
            f'DEVICE INTEGRITY REPORT: ZERO MOBILE PHONES DETECTED (CLEAN)'
            f'</span>'
            f'<span class="pill pill-pass" style="font-size: 12px; padding: 5px 12px;">DEVICE CLEARANCE APPROVED 🟢</span>'
            f'</div>'
            f'<div style="margin-top: 4px; font-size: 0.92rem; color: var(--text); line-height: 1.45;">'
            f'<strong>Device Verification:</strong> Continuous computer vision proctoring verified that zero (0) mobile phones, electronic devices, or secondary displays were present in the camera stream throughout the entire examination.'
            f'</div>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
    render_html_block(html)


def render_extension_clearance_card(
    extension_used: bool,
    detected_extension_name: str = "",
    events: Optional[List[Dict[str, Any]]] = None,
):
    """Renders theme-adaptive post-submission extension clearance card."""
    if extension_used:
        ext_label = detected_extension_name or "Third-Party Browser Extension"
        html = (
            f'<div class="clearance-fail-box">'
            f'<div style="display: flex; align-items: flex-start; gap: 14px;">'
            f'<span style="font-size: 32px;">🚨</span>'
            f'<div style="flex: 1;">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">'
            f'<span style="font-size: 1.2rem; font-weight: 800; color: var(--danger); letter-spacing: -0.01em;">'
            f'CLEARANCE REPORT: UNAUTHORIZED BROWSER EXTENSION USED'
            f'</span>'
            f'<span class="pill pill-fail" style="font-size: 12px; padding: 5px 12px;">CLEARANCE WITHHELD ❌</span>'
            f'</div>'
            f'<div style="margin-top: 6px; font-size: 0.94rem; color: var(--text); line-height: 1.5;">'
            f'<strong>Audit Notice:</strong> The proctoring integrity engine recorded that one or more browser extensions (<code style="background: var(--surface-2); padding: 2px 8px; border-radius: 4px; font-weight: 700;">{ext_label}</code>) were active / used during this examination session.'
            f'</div>'
            f'<div style="margin-top: 10px; background: var(--surface); border: 1px solid var(--danger-border); border-radius: 8px; padding: 12px 16px; font-size: 0.88rem; color: var(--text);">'
            f'<ul style="margin: 0; padding-left: 18px; line-height: 1.6;">'
            f'<li><strong>Pre-Exam Scan:</strong> Extension detected before exam start.</li>'
            f'<li><strong>Warning Issued to Candidate:</strong> Warning was served to candidate prior to start.</li>'
            f'<li><strong>Faculty Notification:</strong> Telemetry transmitted directly to the Faculty Review Dashboard.</li>'
            f'<li><strong>Final Status:</strong> Candidate proceeded despite warning; examination submission is flagged for review.</li>'
            f'</ul>'
            f'</div>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
    else:
        html = (
            f'<div class="clearance-pass-box">'
            f'<div style="display: flex; align-items: center; gap: 14px;">'
            f'<span style="font-size: 32px;">✅</span>'
            f'<div style="flex: 1;">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">'
            f'<span style="font-size: 1.2rem; font-weight: 800; color: var(--success); letter-spacing: -0.01em;">'
            f'CLEARANCE REPORT: ZERO EXTENSIONS DETECTED (CLEAN)'
            f'</span>'
            f'<span class="pill pill-pass" style="font-size: 12px; padding: 5px 12px;">CLEARANCE APPROVED 🟢</span>'
            f'</div>'
            f'<div style="margin-top: 4px; font-size: 0.92rem; color: var(--text); line-height: 1.45;">'
            f'<strong>Integrity Verification:</strong> Pre-exam diagnostic scan and real-time DOM monitoring confirmed that zero unauthorized browser extensions or scripts were used during this test session.'
            f'</div>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
    render_html_block(html)


def render_pre_exam_extension_warning(
    detected_extension_name: str,
    student_id: str = "STU-2026-081",
    session_id: str = "",
):
    """Renders prominent warning alert when an extension is detected before the exam starts."""
    html = (
        f'<div class="ext-warning-box">'
        f'<div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">'
        f'<span style="font-size: 26px;">🚨</span>'
        f'<div>'
        f'<div style="font-size: 1.15rem; font-weight: 800; color: var(--danger); letter-spacing: -0.01em;">'
        f'PROCTORING INTEGRITY WARNING: YOU ARE USING A BROWSER EXTENSION!'
        f'</div>'
        f'<div style="font-size: 0.88rem; color: var(--text-muted); font-weight: 600;">'
        f'Detected Signature: <code style="background: var(--surface); padding: 2px 8px; border-radius: 4px; font-weight: 700; color: var(--danger);">{detected_extension_name}</code>'
        f'</div>'
        f'</div>'
        f'</div>'
        f'<div style="font-size: 0.92rem; color: var(--text); line-height: 1.55; margin-top: 8px;">'
        f'<strong>⚠️ Institutional Examination Violation:</strong> '
        f'Candidates are strictly prohibited from having active browser extensions (such as AI assistants, solvers, auto-translators, devtools, or automation scripts) during examinations.'
        f'</div>'
        f'<div style="background: var(--surface); border: 1px solid var(--danger-border); border-radius: 8px; padding: 10px 14px; margin-top: 10px; font-size: 0.85rem; color: var(--text);">'
        f'<div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 6px;">'
        f'<span>📡 <strong>Faculty Telemetry Status:</strong> <span class="pill pill-fail">TRANSMITTED TO FACULTY DASHBOARD</span></span>'
        f'<span>Session ID: <code>{session_id}</code></span>'
        f'</div>'
        f'<div style="margin-top: 6px; color: var(--danger);">'
        f'<strong>Required Action:</strong> Please open your browser settings (<code>chrome://extensions</code> or <code>edge://extensions</code>), turn OFF all extensions, and reload this page before starting.'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    render_html_block(html)


def render_faculty_extension_alert_card(
    candidate_name: str,
    student_id: str,
    roll_no: str,
    session_id: str,
    ext_name: str,
    stage: str = "PRE_EXAM",
    timestamp_str: str = "Just Now",
):
    """Renders high-visibility alert tile for Faculty Dashboard when candidate triggers extension alert."""
    stage_label = "PRE-EXAM READINESS CHECK" if "PRE" in stage.upper() else "ACTIVE EXAM DOM INJECTION"
    html = (
        f'<div class="ext-faculty-card">'
        f'<div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px;">'
        f'<div>'
        f'<div style="display: flex; align-items: center; gap: 8px;">'
        f'<span class="pill pill-fail">🚨 EXTENSION VIOLATION</span>'
        f'<strong style="color: var(--text); font-size: 1.05rem;">{candidate_name}</strong>'
        f'<span style="color: var(--text-muted); font-size: 0.85rem;">({student_id} / {roll_no})</span>'
        f'</div>'
        f'<div style="margin-top: 6px; font-size: 0.88rem; color: var(--text);">'
        f'Flagged Extension: <strong style="color: var(--danger);">{ext_name}</strong> &nbsp;|&nbsp; '
        f'Detection Stage: <strong style="color: var(--primary);">{stage_label}</strong>'
        f'</div>'
        f'</div>'
        f'<div style="text-align: right;">'
        f'<span class="pill pill-warn">WARNING ISSUED</span>'
        f'<div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 4px;">🕒 {timestamp_str}</div>'
        f'</div>'
        f'</div>'
        f'<div style="margin-top: 8px; font-size: 0.82rem; color: var(--text-muted); background: var(--surface-2); padding: 6px 10px; border-radius: 6px;">'
        f'Session: <code>{session_id}</code> &nbsp;|&nbsp; '
        f'Status: <strong>Flagged for Faculty Audit — Clearance will show extension was used.</strong>'
        f'</div>'
        f'</div>'
    )
    render_html_block(html)


def render_metric_tile(title: str, value: Any, subtitle: str = "", status: str = "neutral"):
    """Renders a clean metric card (backwards compatibility)."""
    pill_html = ""
    if status == "pass":
        pill_html = '<span class="pill pill-pass">OPTIMAL</span>'
    elif status == "warn":
        pill_html = '<span class="pill pill-warn">ATTENTION</span>'
    elif status == "fail":
        pill_html = '<span class="pill pill-fail">ALERT</span>'

    card_html = (
        f'<div class="metric-tile">'
        f'<div style="display: flex; justify-content: space-between; align-items: center; gap: 4px;">'
        f'<span class="metric-tile-title">{title}</span>'
        f'{pill_html}'
        f'</div>'
        f'<div class="metric-tile-val">{value}</div>'
        f'<div class="metric-tile-sub">{subtitle}</div>'
        f'</div>'
    )
    render_html_block(card_html)


def render_academic_header(
    title: str = "Exam Monitoring and Integrity System",
    subtitle: str = "Intelligent Multi-Modal Proctoring & Browser Integrity Assurance Platform",
    student_name: str = "Mayur Tandel",
    student_id: str = "STU-2026-081",
    department: str = "Computer Science & Engineering",
):
    """Backwards-compatible academic header delegating to modern hero design."""
    render_portal_hero(
        title=title,
        subtitle=subtitle,
        student_name=student_name,
        student_id=student_id,
        department=department,
    )


def render_question_matrix_summary(total: int, answered: int, marked: int, unanswered: int):
    """Renders progress badge counters for examination palette."""
    summary_html = (
        f'<div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap;">'
        f'<span class="pill pill-neutral">Total: <strong>{total}</strong></span>'
        f'<span class="pill pill-pass">Answered: <strong>{answered}</strong></span>'
        f'<span class="pill pill-warn">Marked: <strong>{marked}</strong></span>'
        f'<span class="pill pill-neutral">Unanswered: <strong>{unanswered}</strong></span>'
        f'</div>'
    )
    render_html_block(summary_html)


def render_topbar(
    title: str = "AI & ML Certification Examination",
    student_name: str = "Mayur Tandel",
    student_id: str = "STU-2026-081",
    department: str = "CS",
    progress_str: str = "Q1 of 5",
    risk_level: str = "LOW",
    risk_score: float = 0.0,
):
    """Renders the top sticky proctoring bar for the exam view."""
    lvl = str(risk_level).upper()
    pill_cls = "pill-pass" if lvl == "LOW" else ("pill-warn" if lvl == "MEDIUM" else "pill-fail")

    html = (
        f'<div class="exam-sticky-topbar">'
        f'<div style="display: flex; align-items: center; gap: 10px;">'
        f'<span style="font-size: 1.3rem;">🎓</span>'
        f'<div>'
        f'<div style="font-weight: 700; font-size: 1.05rem; color: var(--text);">{title}</div>'
        f'<div style="font-size: 0.78rem; color: var(--text-muted);">Proctored Exam &nbsp;|&nbsp; <strong>{department}</strong></div>'
        f'</div>'
        f'</div>'
        f'<div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">'
        f'<span class="pill pill-neutral">👤 <strong>{student_name}</strong> ({student_id})</span>'
        f'<span class="pill pill-primary">📊 {progress_str}</span>'
        f'<span class="pill {pill_cls}">🛡️ RISK: {lvl} ({risk_score:.2f})</span>'
        f'</div>'
        f'</div>'
    )
    render_html_block(html)
