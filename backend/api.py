"""
Backend REST API for AI Exam Monitoring System
Built with Starlette & Uvicorn, integrating SQLite database and rule-based event classifier.
"""

import os
import json
import time
from typing import Dict, Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from database.db import get_db
from extension_monitor.detector import get_evaluator, get_classifier

db = get_db()
evaluator = get_evaluator()
classifier = get_classifier()


async def health(request: Request) -> JSONResponse:
    """Service health check."""
    return JSONResponse({
        "status": "healthy",
        "service": "AI Exam Integrity API",
        "timestamp": time.time(),
    })


async def report_browser_readiness(request: Request) -> JSONResponse:
    """
    POST /api/browser-readiness
    Accepts client browser environment telemetry, evaluates compatibility, and registers session.
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    exam_session_id = payload.get("exam_session_id")
    student_id = payload.get("student_id", "STU-2026-081")
    user_agent = payload.get("user_agent", "")
    camera_perm = payload.get("camera_permission", "GRANTED")
    mic_perm = payload.get("mic_permission", "GRANTED")
    ext_status = payload.get("institutional_extension_status", "NOT_INSTALLED")

    if not exam_session_id:
        return JSONResponse({"error": "exam_session_id is required"}, status_code=400)

    # Parse and evaluate environment
    browser_info = evaluator.parse_user_agent(user_agent)
    features = payload.get("features", {
        "webrtc": True,
        "mutation_observer": True,
        "fullscreen": True,
        "local_storage": True,
    })

    evaluation = evaluator.evaluate_compatibility(
        browser_info=browser_info,
        features=features,
        camera_permission=camera_perm,
        mic_permission=mic_perm,
    )

    # Persist or update session in DB
    session = db.create_or_get_session(
        exam_session_id=exam_session_id,
        exam_id=payload.get("exam_id", "EXAM-CS-2026-X"),
        student_id=student_id,
        browser_name=browser_info["browser"],
        browser_version=browser_info["version"],
        os_name=browser_info["os"],
        compatibility_status=evaluation["status"],
        institutional_extension_status=ext_status,
        camera_permission=camera_perm,
        mic_permission=mic_perm,
    )

    return JSONResponse({
        "success": True,
        "session": session,
        "evaluation": evaluation,
    })


async def submit_monitoring_event(request: Request) -> JSONResponse:
    """
    POST /api/events
    Submits a monitoring event. Server-side classifier validates and scores the event.
    Enforces authorization: student can only submit for their authorized session.
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    exam_session_id = payload.get("exam_session_id")
    student_id = payload.get("student_id")
    event_type = payload.get("event_type", "PAGE_INTEGRITY_CHANGE")
    description = payload.get("description", "Observable interface event")
    detection_method = payload.get("detection_method", "Telemetry")

    if not exam_session_id or not student_id:
        return JSONResponse({"error": "exam_session_id and student_id are required"}, status_code=400)

    # Validate authorization: Check if session exists and belongs to this student
    sessions = db.get_sessions(limit=500)
    matched_session = next((s for s in sessions if s["exam_session_id"] == exam_session_id), None)
    if matched_session and matched_session["student_id"] != student_id:
        return JSONResponse({"error": "Forbidden: Session belongs to another candidate"}, status_code=403)

    # Server-side rule-based risk classification (NEVER trust client's risk score)
    risk_level, severity, rule_reason = classifier.classify_event({
        "event_type": event_type,
        "description": description,
        "details": payload.get("details", description),
        "detection_method": detection_method,
        "occurrences": payload.get("occurrences", 1),
    })

    # Persist in DB
    recorded = db.record_event(
        exam_session_id=exam_session_id,
        student_id=student_id,
        event_type=event_type,
        event_description=f"{description} ({rule_reason})",
        detection_method=detection_method,
        risk_level=risk_level,
        severity=severity,
        raw_data=payload.get("raw_data", {}),
        occurred_at=payload.get("occurred_at", time.time()),
    )

    return JSONResponse({
        "success": True,
        "event_id": recorded.get("id"),
        "risk_level": risk_level,
        "severity": severity,
        "rule_reason": rule_reason,
        "review_status": recorded.get("review_status"),
    }, status_code=201)


async def get_monitoring_events(request: Request) -> JSONResponse:
    """
    GET /api/events
    Retrieves filtered events for administrative review.
    """
    qp = request.query_params
    session_id = qp.get("session_id")
    student_id = qp.get("student_id")
    event_type = qp.get("event_type")
    risk_level = qp.get("risk_level")
    review_status = qp.get("review_status")
    limit = int(qp.get("limit", 200))

    events = db.get_events(
        exam_session_id=session_id,
        student_id=student_id,
        event_type=event_type,
        risk_level=risk_level,
        review_status=review_status,
        limit=limit,
    )
    return JSONResponse({"count": len(events), "events": events})


async def get_session_summary(request: Request) -> JSONResponse:
    """
    GET /api/session-summary?session_id=...
    Returns consolidated examination session summary.
    """
    session_id = request.query_params.get("session_id")
    if not session_id:
        return JSONResponse({"error": "session_id is required"}, status_code=400)

    events = db.get_events(exam_session_id=session_id)
    high_count = sum(1 for e in events if e.get("risk_level") == "HIGH")
    med_count = sum(1 for e in events if e.get("risk_level") == "MEDIUM")
    low_count = sum(1 for e in events if e.get("risk_level") == "LOW")

    return JSONResponse({
        "session_id": session_id,
        "total_events": len(events),
        "high_risk_count": high_count,
        "medium_risk_count": med_count,
        "low_risk_count": low_count,
    })


async def submit_admin_review(request: Request) -> JSONResponse:
    """
    POST /api/review
    Applies administrator review decisions ('CONFIRMED', 'FALSE_POSITIVE', 'NEEDS_REVIEW').
    """
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    event_id = payload.get("event_id")
    reviewer_id = payload.get("reviewer_id", "ADMIN-PROCTOR")
    review_decision = payload.get("review_decision")
    review_notes = payload.get("review_notes", "")

    if not event_id or not review_decision:
        return JSONResponse({"error": "event_id and review_decision are required"}, status_code=400)

    success = db.record_review(
        event_id=int(event_id),
        reviewer_id=reviewer_id,
        review_decision=review_decision,
        review_notes=review_notes,
    )

    if not success:
        return JSONResponse({"error": "Invalid decision or event not found"}, status_code=400)

    return JSONResponse({
        "success": True,
        "event_id": event_id,
        "review_decision": review_decision.upper(),
        "reviewer_id": reviewer_id,
    })


routes = [
    Route("/health", health, methods=["GET"]),
    Route("/api/browser-readiness", report_browser_readiness, methods=["POST"]),
    Route("/api/events", submit_monitoring_event, methods=["POST"]),
    Route("/api/events", get_monitoring_events, methods=["GET"]),
    Route("/api/session-summary", get_session_summary, methods=["GET"]),
    Route("/api/review", submit_admin_review, methods=["POST"]),
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

app = Starlette(routes=routes, middleware=middleware)
