"""
Database Access Layer for AI-Based Exam Monitoring System
Uses SQLite3 with WAL mode, parameterized queries, and thread safety.
"""

import os
import sqlite3
import threading
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs", "exam_integrity.db")


class ExamDatabase:
    """
    Centralized SQLite database manager for exam sessions, monitoring events,
    student telemetry, and administrative reviews.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._lock = threading.Lock()
        self.init_schema()
        self.seed_default_data()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_schema(self):
        """Initializes tables, constraints, and indexes."""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    # 1. Students
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS students (
                            student_id TEXT PRIMARY KEY,
                            full_name TEXT NOT NULL,
                            email TEXT NOT NULL,
                            department TEXT NOT NULL,
                            roll_number TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)

                    # 2. Exams
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS exams (
                            exam_id TEXT PRIMARY KEY,
                            title TEXT NOT NULL,
                            course_code TEXT NOT NULL,
                            total_questions INTEGER NOT NULL DEFAULT 5,
                            duration_minutes INTEGER NOT NULL DEFAULT 60,
                            instructions TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)

                    # 3. Monitoring Sessions
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS monitoring_sessions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            exam_session_id TEXT UNIQUE NOT NULL,
                            exam_id TEXT NOT NULL,
                            student_id TEXT NOT NULL,
                            browser_name TEXT DEFAULT 'Unknown',
                            browser_version TEXT DEFAULT 'Unknown',
                            os_name TEXT DEFAULT 'Unknown',
                            compatibility_status TEXT DEFAULT 'READY',
                            institutional_extension_status TEXT DEFAULT 'NOT_INSTALLED',
                            camera_permission TEXT DEFAULT 'UNKNOWN',
                            mic_permission TEXT DEFAULT 'UNKNOWN',
                            start_time REAL,
                            end_time REAL,
                            status TEXT DEFAULT 'IN_PROGRESS',
                            total_events INTEGER DEFAULT 0,
                            peak_risk_score REAL DEFAULT 0.0,
                            final_risk_level TEXT DEFAULT 'LOW',
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (student_id) REFERENCES students(student_id),
                            FOREIGN KEY (exam_id) REFERENCES exams(exam_id)
                        );
                    """)

                    # 4. Monitoring Events
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS monitoring_events (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            monitoring_session_id INTEGER,
                            exam_session_id TEXT NOT NULL,
                            student_id TEXT NOT NULL,
                            event_type TEXT NOT NULL,
                            event_description TEXT NOT NULL,
                            detection_method TEXT NOT NULL,
                            risk_level TEXT NOT NULL CHECK(risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
                            severity TEXT DEFAULT 'MEDIUM',
                            raw_data TEXT,
                            review_status TEXT DEFAULT 'NEEDS_REVIEW' CHECK(review_status IN ('NEEDS_REVIEW', 'CONFIRMED', 'FALSE_POSITIVE')),
                            occurred_at REAL NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (monitoring_session_id) REFERENCES monitoring_sessions(id)
                        );
                    """)

                    # 5. Monitoring Reviews
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS monitoring_reviews (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            monitoring_event_id INTEGER NOT NULL,
                            reviewer_id TEXT NOT NULL,
                            review_decision TEXT NOT NULL CHECK(review_decision IN ('CONFIRMED', 'FALSE_POSITIVE', 'NEEDS_REVIEW')),
                            review_notes TEXT,
                            reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (monitoring_event_id) REFERENCES monitoring_events(id) ON DELETE CASCADE
                        );
                    """)

                    # 6. Student Exam Answers
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS student_exam_answers (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            exam_session_id TEXT NOT NULL,
                            student_id TEXT NOT NULL,
                            question_id INTEGER NOT NULL,
                            selected_option TEXT,
                            is_marked_for_review INTEGER DEFAULT 0,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(exam_session_id, question_id)
                        );
                    """)

                    # Indexes for fast querying & filtering
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_exam ON monitoring_sessions(exam_id);")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_student ON monitoring_sessions(student_id);")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_session ON monitoring_events(exam_session_id);")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_risk ON monitoring_events(risk_level);")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_review ON monitoring_events(review_status);")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_reviews_event ON monitoring_reviews(monitoring_event_id);")
            finally:
                conn.close()

    def seed_default_data(self):
        """Seeds default student profile, exam, and initial historical records if missing."""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    # Seed Student
                    conn.execute("""
                        INSERT OR IGNORE INTO students (student_id, full_name, email, department, roll_number)
                        VALUES (?, ?, ?, ?, ?)
                    """, ("STU-2026-081", "Mayur Tandel", "mayur.tandel@college.edu", "Computer Science & Engineering", "CS-2026-081"))

                    # Seed Exams
                    conn.execute("""
                        INSERT OR IGNORE INTO exams (exam_id, title, course_code, total_questions, duration_minutes, instructions)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        "EXAM-CS-2026-X",
                        "AI & Machine Learning Certification Examination",
                        "CS-DS-2026-X",
                        5,
                        60,
                        "1. Ensure your webcam is enabled and face is well-lit.\n2. Do not switch tabs or use keyboard shortcuts (Alt+Tab, Ctrl+C/V).\n3. Keep your focus directed towards the exam screen at all times."
                    ))

                    conn.execute("""
                        INSERT OR IGNORE INTO exams (exam_id, title, course_code, total_questions, duration_minutes, instructions)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        "EXAM-DS-2026-Y",
                        "Advanced Data Structures & Algorithms Midterm",
                        "CS-ALGO-2026",
                        25,
                        90,
                        "1. Standard institutional examination regulations apply.\n2. Fullscreen mode required."
                    ))

                    # Seed sample completed session if no sessions exist
                    cur = conn.execute("SELECT COUNT(*) as c FROM monitoring_sessions")
                    if cur.fetchone()["c"] == 0:
                        hist_session_id = "SESSION-HIST-001"
                        start_t = time.time() - 86400 * 2
                        end_t = start_t + 1800
                        conn.execute("""
                            INSERT INTO monitoring_sessions (
                                exam_session_id, exam_id, student_id, browser_name, browser_version,
                                os_name, compatibility_status, institutional_extension_status,
                                camera_permission, mic_permission, start_time, end_time, status,
                                total_events, peak_risk_score, final_risk_level
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            hist_session_id, "EXAM-CS-2026-X", "STU-2026-081", "Chrome", "124.0.0.0",
                            "Windows 11", "READY", "CONNECTED",
                            "GRANTED", "GRANTED", start_t, end_t, "SUBMITTED",
                            2, 0.28, "LOW"
                        ))
                        sess_row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

                        # Sample historic event
                        conn.execute("""
                            INSERT INTO monitoring_events (
                                monitoring_session_id, exam_session_id, student_id, event_type,
                                event_description, detection_method, risk_level, severity,
                                review_status, occurred_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            sess_row_id, hist_session_id, "STU-2026-081", "WINDOW_BLUR_TAB_SWITCH",
                            "Brief browser focus loss detected (duration: 1.2s)", "ScreenFocusMonitor",
                            "LOW", "LOW", "CONFIRMED", start_t + 350
                        ))
                        evt_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

                        conn.execute("""
                            INSERT INTO monitoring_reviews (
                                monitoring_event_id, reviewer_id, review_decision, review_notes
                            ) VALUES (?, ?, ?, ?)
                        """, (evt_id, "ADMIN-PROCTOR-1", "CONFIRMED", "Brief momentary focus loss, verified benign."))
            finally:
                conn.close()

    # --- Student & Exam Management ---
    def get_student(self, student_id: str = "STU-2026-081") -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            row = conn.execute("SELECT * FROM students WHERE student_id = ?", (student_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_exams(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            rows = conn.execute("SELECT * FROM exams ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # --- Session Management ---
    def create_or_get_session(
        self,
        exam_session_id: str,
        exam_id: str = "EXAM-CS-2026-X",
        student_id: str = "STU-2026-081",
        browser_name: str = "Chrome",
        browser_version: str = "124.0.0.0",
        os_name: str = "Windows",
        compatibility_status: str = "READY",
        institutional_extension_status: str = "NOT_INSTALLED",
        camera_permission: str = "GRANTED",
        mic_permission: str = "GRANTED",
    ) -> Dict[str, Any]:
        """Creates or updates session metadata."""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    now = time.time()
                    conn.execute("""
                        INSERT INTO monitoring_sessions (
                            exam_session_id, exam_id, student_id, browser_name, browser_version,
                            os_name, compatibility_status, institutional_extension_status,
                            camera_permission, mic_permission, start_time, status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'IN_PROGRESS', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ON CONFLICT(exam_session_id) DO UPDATE SET
                            browser_name = excluded.browser_name,
                            browser_version = excluded.browser_version,
                            os_name = excluded.os_name,
                            compatibility_status = excluded.compatibility_status,
                            institutional_extension_status = excluded.institutional_extension_status,
                            camera_permission = excluded.camera_permission,
                            mic_permission = excluded.mic_permission,
                            updated_at = CURRENT_TIMESTAMP
                    """, (
                        exam_session_id, exam_id, student_id, browser_name, browser_version,
                        os_name, compatibility_status, institutional_extension_status,
                        camera_permission, mic_permission, now
                    ))
                row = conn.execute("SELECT * FROM monitoring_sessions WHERE exam_session_id = ?", (exam_session_id,)).fetchone()
                return dict(row) if row else {}
            finally:
                conn.close()

    def end_session(
        self,
        exam_session_id: str,
        status: str = "SUBMITTED",
        peak_risk_score: float = 0.0,
        final_risk_level: str = "LOW",
    ):
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    now = time.time()
                    conn.execute("""
                        UPDATE monitoring_sessions SET
                            end_time = ?,
                            status = ?,
                            peak_risk_score = ?,
                            final_risk_level = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE exam_session_id = ?
                    """, (now, status, peak_risk_score, final_risk_level, exam_session_id))
            finally:
                conn.close()

    def get_sessions(self, student_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            if student_id:
                query = """
                    SELECT ms.*, e.title as exam_title, e.course_code
                    FROM monitoring_sessions ms
                    LEFT JOIN exams e ON ms.exam_id = e.exam_id
                    WHERE ms.student_id = ?
                    ORDER BY ms.created_at DESC LIMIT ?
                """
                rows = conn.execute(query, (student_id, limit)).fetchall()
            else:
                query = """
                    SELECT ms.*, e.title as exam_title, e.course_code, s.full_name as student_name
                    FROM monitoring_sessions ms
                    LEFT JOIN exams e ON ms.exam_id = e.exam_id
                    LEFT JOIN students s ON ms.student_id = s.student_id
                    ORDER BY ms.created_at DESC LIMIT ?
                """
                rows = conn.execute(query, (limit,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # --- Monitoring Events ---
    def record_event(
        self,
        exam_session_id: str,
        student_id: str,
        event_type: str,
        event_description: str,
        detection_method: str,
        risk_level: str = "LOW",
        severity: str = "LOW",
        raw_data: Optional[Dict[str, Any]] = None,
        occurred_at: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Records an event with foreign session link and increments total session event counter."""
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    now = occurred_at if occurred_at is not None else time.time()
                    risk_level = risk_level.upper()
                    if risk_level not in ("LOW", "MEDIUM", "HIGH"):
                        risk_level = "LOW"

                    raw_json = json.dumps(raw_data) if raw_data else None

                    # Find monitoring_session_id
                    sess_row = conn.execute(
                        "SELECT id FROM monitoring_sessions WHERE exam_session_id = ?",
                        (exam_session_id,)
                    ).fetchone()
                    sess_id = sess_row["id"] if sess_row else None

                    cur = conn.execute("""
                        INSERT INTO monitoring_events (
                            monitoring_session_id, exam_session_id, student_id, event_type,
                            event_description, detection_method, risk_level, severity,
                            raw_data, review_status, occurred_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'NEEDS_REVIEW', ?)
                    """, (
                        sess_id, exam_session_id, student_id, event_type,
                        event_description, detection_method, risk_level, severity,
                        raw_json, now
                    ))
                    event_id = cur.lastrowid

                    # Increment event count on session
                    if sess_id:
                        conn.execute("""
                            UPDATE monitoring_sessions
                            SET total_events = total_events + 1, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (sess_id,))

                row = conn.execute("SELECT * FROM monitoring_events WHERE id = ?", (event_id,)).fetchone()
                return dict(row) if row else {}
            finally:
                conn.close()

    def get_events(
        self,
        exam_session_id: Optional[str] = None,
        student_id: Optional[str] = None,
        event_type: Optional[str] = None,
        risk_level: Optional[str] = None,
        review_status: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            query = "SELECT * FROM monitoring_events WHERE 1=1"
            params: List[Any] = []

            if exam_session_id:
                query += " AND exam_session_id = ?"
                params.append(exam_session_id)
            if student_id:
                query += " AND student_id = ?"
                params.append(student_id)
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            if risk_level and risk_level != "ALL":
                query += " AND risk_level = ?"
                params.append(risk_level.upper())
            if review_status and review_status != "ALL":
                query += " AND review_status = ?"
                params.append(review_status.upper())

            query += " ORDER BY occurred_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, tuple(params)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # --- Administrative Review ---
    def record_review(
        self,
        event_id: int,
        reviewer_id: str,
        review_decision: str,
        review_notes: str = "",
    ) -> bool:
        """Applies administrative review decision and saves audit record."""
        decision = review_decision.upper()
        if decision not in ("CONFIRMED", "FALSE_POSITIVE", "NEEDS_REVIEW"):
            return False

        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    # Update monitoring event review status
                    conn.execute("""
                        UPDATE monitoring_events
                        SET review_status = ?
                        WHERE id = ?
                    """, (decision, event_id))

                    # Insert review audit log
                    conn.execute("""
                        INSERT INTO monitoring_reviews (
                            monitoring_event_id, reviewer_id, review_decision, review_notes
                        ) VALUES (?, ?, ?, ?)
                    """, (event_id, reviewer_id, decision, review_notes))
                return True
            except Exception as e:
                print(f"[ExamDatabase] Review error: {e}", flush=True)
                return False
            finally:
                conn.close()

    def get_event_reviews(self, event_id: int) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM monitoring_reviews WHERE monitoring_event_id = ? ORDER BY reviewed_at DESC",
                (event_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # --- Student Exam Answers & State ---
    def record_answer(
        self,
        exam_session_id: str,
        student_id: str,
        question_id: int,
        selected_option: Optional[str],
        is_marked_for_review: bool = False,
    ):
        with self._lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                        INSERT INTO student_exam_answers (
                            exam_session_id, student_id, question_id, selected_option, is_marked_for_review, updated_at
                        ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        ON CONFLICT(exam_session_id, question_id) DO UPDATE SET
                            selected_option = excluded.selected_option,
                            is_marked_for_review = excluded.is_marked_for_review,
                            updated_at = CURRENT_TIMESTAMP
                    """, (exam_session_id, student_id, question_id, selected_option, 1 if is_marked_for_review else 0))
            finally:
                conn.close()

    def get_answers(self, exam_session_id: str) -> Dict[int, Dict[str, Any]]:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM student_exam_answers WHERE exam_session_id = ?",
                (exam_session_id,)
            ).fetchall()
            return {
                r["question_id"]: {
                    "selected_option": r["selected_option"],
                    "is_marked_for_review": bool(r["is_marked_for_review"]),
                }
                for r in rows
            }
        finally:
            conn.close()

    # --- Analytics & Summary Statistics ---
    def get_admin_summary(self) -> Dict[str, Any]:
        """Calculates live summary metrics for the administrator dashboard."""
        conn = self._get_connection()
        try:
            total_sessions = conn.execute("SELECT COUNT(*) as c FROM monitoring_sessions").fetchone()["c"]
            total_events = conn.execute("SELECT COUNT(*) as c FROM monitoring_events").fetchone()["c"]
            high_risk_events = conn.execute(
                "SELECT COUNT(*) as c FROM monitoring_events WHERE risk_level = 'HIGH'"
            ).fetchone()["c"]
            pending_reviews = conn.execute(
                "SELECT COUNT(*) as c FROM monitoring_events WHERE review_status = 'NEEDS_REVIEW'"
            ).fetchone()["c"]

            extension_violations = conn.execute(
                "SELECT COUNT(*) as c FROM monitoring_events WHERE event_type IN ('PRE_EXAM_EXTENSION_DETECTED', 'EXTENSION_DETECTED', 'PAGE_INTEGRITY_CHANGE')"
            ).fetchone()["c"]

            phone_violations = conn.execute(
                "SELECT COUNT(*) as c FROM monitoring_events WHERE event_type IN ('MOBILE_PHONE_DETECTED', 'PHONE_DETECTED')"
            ).fetchone()["c"]

            return {
                "total_sessions": total_sessions,
                "total_events": total_events,
                "high_risk_events": high_risk_events,
                "pending_reviews": pending_reviews,
                "extension_violations": extension_violations,
                "phone_violations": phone_violations,
            }
        finally:
            conn.close()

    def get_extension_events(
        self,
        exam_session_id: Optional[str] = None,
        student_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Returns all pre-exam and in-exam browser extension integrity events."""
        conn = self._get_connection()
        try:
            query = """
                SELECT me.*, s.full_name as student_name, s.roll_number, s.department
                FROM monitoring_events me
                LEFT JOIN students s ON me.student_id = s.student_id
                WHERE me.event_type IN ('PRE_EXAM_EXTENSION_DETECTED', 'EXTENSION_DETECTED', 'PAGE_INTEGRITY_CHANGE')
            """
            params: List[Any] = []
            if exam_session_id:
                query += " AND me.exam_session_id = ?"
                params.append(exam_session_id)
            if student_id:
                query += " AND me.student_id = ?"
                params.append(student_id)
            query += " ORDER BY me.occurred_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, tuple(params)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_phone_events(
        self,
        exam_session_id: Optional[str] = None,
        student_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Returns all mobile phone detection proctoring events."""
        conn = self._get_connection()
        try:
            query = """
                SELECT me.*, s.full_name as student_name, s.roll_number, s.department
                FROM monitoring_events me
                LEFT JOIN students s ON me.student_id = s.student_id
                WHERE me.event_type IN ('MOBILE_PHONE_DETECTED', 'PHONE_DETECTED')
            """
            params: List[Any] = []
            if exam_session_id:
                query += " AND me.exam_session_id = ?"
                params.append(exam_session_id)
            if student_id:
                query += " AND me.student_id = ?"
                params.append(student_id)
            query += " ORDER BY me.occurred_at DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, tuple(params)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_browser_compatibility_stats(self) -> Dict[str, Any]:
        """Computes browser distribution and compatibility breakdowns."""
        conn = self._get_connection()
        try:
            browser_rows = conn.execute(
                "SELECT browser_name, COUNT(*) as count FROM monitoring_sessions GROUP BY browser_name"
            ).fetchall()
            compat_rows = conn.execute(
                "SELECT compatibility_status, COUNT(*) as count FROM monitoring_sessions GROUP BY compatibility_status"
            ).fetchall()
            ext_rows = conn.execute(
                "SELECT institutional_extension_status, COUNT(*) as count FROM monitoring_sessions GROUP BY institutional_extension_status"
            ).fetchall()

            return {
                "browsers": {r["browser_name"]: r["count"] for r in browser_rows},
                "compatibility": {r["compatibility_status"]: r["count"] for r in compat_rows},
                "extension_status": {r["institutional_extension_status"]: r["count"] for r in ext_rows},
            }
        finally:
            conn.close()


# Singleton Instance
_DB_INSTANCE: Optional[ExamDatabase] = None
_DB_LOCK = threading.Lock()


def get_db(db_path: str = DEFAULT_DB_PATH) -> ExamDatabase:
    """Returns thread-safe singleton instance of ExamDatabase."""
    global _DB_INSTANCE
    with _DB_LOCK:
        if _DB_INSTANCE is None:
            _DB_INSTANCE = ExamDatabase(db_path=db_path)
        return _DB_INSTANCE
