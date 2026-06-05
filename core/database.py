"""SQLite database layer for OfferPilot multi-user support.

Replaces the JSON-file store with a SQLite database at ``data/offerpilot.db``.
On first run, data from ``data/store.json`` is automatically migrated.
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.models import (
    Job, JobStatus, ResumeVersion, Application,
    InterviewRecord, InterviewRound, MatchResult, WeeklyReview,
    InterviewJournal, UserProfile, PrepNote,
)

# ── Paths ─────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "offerpilot.db"
OLD_STORE = PROJECT_ROOT / "data" / "store.json"
RESUMES_DIR = PROJECT_ROOT / "data" / "resumes"

# ── Helpers ───────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().isoformat()


def _json_dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _json_loads(s: str, default=None):
    if not s:
        return default if default is not None else []
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else []


# ── Schema ────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT DEFAULT '',
    school TEXT DEFAULT '',
    major TEXT DEFAULT '',
    degree TEXT DEFAULT '',
    graduation_year TEXT DEFAULT '',
    target_directions TEXT DEFAULT '[]',
    target_cities TEXT DEFAULT '[]',
    bio TEXT DEFAULT '',
    password_hash TEXT DEFAULT '',
    llm_settings TEXT DEFAULT '{}',
    created_at TEXT DEFAULT '',
    updated_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    company TEXT DEFAULT '',
    title TEXT DEFAULT '',
    status TEXT DEFAULT 'interested',
    jd_raw_text TEXT DEFAULT '',
    jd_parsed_fields TEXT DEFAULT '{}',
    location TEXT DEFAULT '',
    salary_range TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    direction TEXT DEFAULT '',
    deadline TEXT DEFAULT NULL,
    priority TEXT DEFAULT '中',
    source_url TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT '',
    updated_at TEXT DEFAULT '',
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS resumes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    version_name TEXT DEFAULT '',
    file_path TEXT DEFAULT '',
    parsed_content TEXT DEFAULT '{}',
    summary_fields TEXT DEFAULT '{}',
    tags TEXT DEFAULT '[]',
    target_direction TEXT DEFAULT '',
    keywords TEXT DEFAULT '[]',
    highlights TEXT DEFAULT '[]',
    created_at TEXT DEFAULT '',
    updated_at TEXT DEFAULT '',
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS applications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    job_id TEXT DEFAULT '',
    resume_id TEXT DEFAULT '',
    applied_date TEXT DEFAULT NULL,
    channel TEXT DEFAULT '',
    current_stage TEXT DEFAULT '',
    status TEXT DEFAULT '',
    application_url TEXT DEFAULT '',
    termination_reason TEXT DEFAULT '',
    interview_date TEXT DEFAULT NULL,
    termination_date TEXT DEFAULT NULL,
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT '',
    updated_at TEXT DEFAULT '',
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS interviews (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    application_id TEXT DEFAULT '',
    round TEXT DEFAULT 'phone',
    interview_date TEXT DEFAULT NULL,
    interviewer_feedback TEXT DEFAULT '',
    self_rating INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT '',
    updated_at TEXT DEFAULT '',
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS interview_journals (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    job_position TEXT DEFAULT '',
    round_progress TEXT DEFAULT '',
    interview_date TEXT DEFAULT NULL,
    experience TEXT DEFAULT '',
    questions_asked TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    created_at TEXT DEFAULT '',
    updated_at TEXT DEFAULT '',
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS match_results (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    job_id TEXT DEFAULT '',
    resume_id TEXT DEFAULT '',
    match_score REAL DEFAULT 0.0,
    matched_points TEXT DEFAULT '[]',
    missing_points TEXT DEFAULT '[]',
    risk_notes TEXT DEFAULT '[]',
    optimization_suggestions TEXT DEFAULT '[]',
    recommended_action TEXT DEFAULT '',
    gaps TEXT DEFAULT '[]',
    suggestions TEXT DEFAULT '[]',
    created_at TEXT DEFAULT '',
    updated_at TEXT DEFAULT '',
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS weekly_reviews (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    week_label TEXT DEFAULT '',
    date_range TEXT DEFAULT '',
    stats TEXT DEFAULT '{}',
    highlights TEXT DEFAULT '[]',
    next_week_focus TEXT DEFAULT '[]',
    user_notes TEXT DEFAULT '',
    created_at TEXT DEFAULT '',
    updated_at TEXT DEFAULT '',
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS prep_notes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    date TEXT DEFAULT NULL,
    topic TEXT DEFAULT '',
    content TEXT DEFAULT '',
    created_at TEXT DEFAULT '',
    updated_at TEXT DEFAULT '',
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""


# ── Database class ────────────────────────────────────────────────────────

class Database:
    """SQLite database for OfferPilot."""

    def __init__(self):
        db_dir = DB_PATH.parent
        db_dir.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(SCHEMA_SQL)
        self._conn.commit()
        self._migrate_schema()
        self._migrate_from_json()

    # ── Schema migration ───────────────────────────────────────────────

    def _migrate_schema(self):
        """Add any missing columns to existing tables (forward-compat)."""
        # Add llm_settings column if it doesn't exist (v0.2 → v0.3)
        for col_sql, table in [
            ("ALTER TABLE users ADD COLUMN llm_settings TEXT DEFAULT '{}'", "users"),
            ("ALTER TABLE prep_notes ADD COLUMN updated_at TEXT DEFAULT ''", "prep_notes"),
        ]:
            try:
                self._conn.execute(col_sql)
            except sqlite3.OperationalError:
                pass  # column already exists or table doesn't exist yet

    # ── Migration ──────────────────────────────────────────────────────

    def _migrate_from_json(self):
        """One-time migration from old store.json to SQLite."""
        if not OLD_STORE.exists():
            return
        # Check if migration already happened
        row = self._conn.execute("SELECT COUNT(*) as cnt FROM jobs").fetchone()
        if row and row["cnt"] > 0:
            return  # already has data

        try:
            with open(OLD_STORE, "r", encoding="utf-8") as fh:
                old = json.load(fh)
        except Exception:
            return

        def _safe_str(val, default=""):
            """Extract string value, handling __dt__ markers from old store."""
            if val is None:
                return default
            if isinstance(val, dict) and "__dt__" in val:
                return val["__dt__"]
            if isinstance(val, str):
                return val
            return str(val) if val else default

        legacy_user_id = "user-legacy-migrated"

        # Build legacy user from old user_profile, or create a basic one
        up = old.get("user_profile")
        if up and isinstance(up, dict) and up.get("username"):
            legacy_username = _safe_str(up.get("username"), "legacy")
            legacy_display = _safe_str(up.get("display_name"), "历史数据用户")
            legacy_password = _safe_str(up.get("password_hash"))
            self._conn.execute(
                "INSERT OR REPLACE INTO users(id, username, display_name, password_hash, "
                "school, major, degree, graduation_year, target_directions, target_cities, bio, "
                "created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    legacy_user_id,
                    legacy_username,
                    legacy_display,
                    legacy_password,
                    _safe_str(up.get("school")),
                    _safe_str(up.get("major")),
                    _safe_str(up.get("degree")),
                    _safe_str(up.get("graduation_year")),
                    _json_dumps(up.get("target_directions", [])),
                    _json_dumps(up.get("target_cities", [])),
                    _safe_str(up.get("bio")),
                    _safe_str(up.get("created_at"), _now()),
                    _safe_str(up.get("updated_at"), _now()),
                ),
            )
        else:
            self._conn.execute(
                "INSERT OR IGNORE INTO users(id, username, display_name, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (legacy_user_id, "legacy", "历史数据用户", _now(), _now()),
            )

        # Migrate each collection
        for collection, table, row_converter in (
            ("jobs", "jobs", _row_from_old_job),
            ("resumes", "resumes", _row_from_old_resume),
            ("applications", "applications", _row_from_old_application),
            ("interviews", "interviews", _row_from_old_interview),
            ("interview_journals", "interview_journals", _row_from_old_journal),
            ("match_results", "match_results", _row_from_old_match),
            ("weekly_reviews", "weekly_reviews", _row_from_old_review),
        ):
            for obj_id, obj_dict in old.get(collection, {}).items():
                row_data = row_converter(obj_id, legacy_user_id, obj_dict)
                columns = ", ".join(row_data.keys())
                placeholders = ", ".join("?" for _ in row_data)
                self._conn.execute(
                    f"INSERT OR IGNORE INTO {table} ({columns}) VALUES ({placeholders})",
                    list(row_data.values()),
                )

        self._conn.commit()
        # Rename old store so we don't re-migrate
        try:
            OLD_STORE.rename(OLD_STORE.with_suffix(".json.migrated"))
        except OSError:
            pass

    # ── Users ──────────────────────────────────────────────────────────

    def create_user(self, username: str, display_name: str, password_hash: str) -> tuple[bool, str]:
        """Create a new user. Returns (success, message)."""
        user_id = f"user-{username}"
        try:
            self._conn.execute(
                "INSERT INTO users(id, username, display_name, password_hash, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, username, display_name, password_hash, _now(), _now()),
            )
            self._conn.commit()
            return True, user_id
        except sqlite3.IntegrityError:
            return False, "用户名已被占用，请换一个"

    def get_user_by_username(self, username: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        return dict(row) if row else None

    def get_user(self, user_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None

    def update_user(self, user_id: str, fields: dict) -> bool:
        """Update user profile fields."""
        if not fields:
            return False
        # Serialize list/dict fields
        for key in ("target_directions", "target_cities"):
            if key in fields and isinstance(fields[key], list):
                fields[key] = _json_dumps(fields[key])
        if "llm_settings" in fields and isinstance(fields["llm_settings"], dict):
            fields["llm_settings"] = _json_dumps(fields["llm_settings"])
        fields["updated_at"] = _now()
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [user_id]
        self._conn.execute(
            f"UPDATE users SET {set_clause} WHERE id = ?", values
        )
        self._conn.commit()
        return True

    # ── Generic CRUD helpers ───────────────────────────────────────────

    def _get_all(self, table: str, user_id: str, model_cls, row_converter) -> list:
        rows = self._conn.execute(
            f"SELECT * FROM {table} WHERE user_id = ? ORDER BY updated_at DESC, created_at DESC",
            (user_id,),
        ).fetchall()
        return [row_converter(dict(r)) for r in rows]

    def _get_one(self, table: str, obj_id: str, model_cls, row_converter):
        row = self._conn.execute(
            f"SELECT * FROM {table} WHERE id = ?", (obj_id,)
        ).fetchone()
        return row_converter(dict(row)) if row else None

    def _insert(self, table: str, obj, row_converter) -> bool:
        row_data = row_converter(obj)
        columns = ", ".join(row_data.keys())
        placeholders = ", ".join("?" for _ in row_data)
        try:
            self._conn.execute(
                f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
                list(row_data.values()),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def _update(self, table: str, obj_id: str, fields: dict) -> bool:
        if not fields:
            return False
        # Serialize any list/dict values
        serialized = {}
        for k, v in fields.items():
            if isinstance(v, (list, dict)):
                serialized[k] = _json_dumps(v)
            elif isinstance(v, datetime):
                serialized[k] = v.isoformat()
            else:
                serialized[k] = v
        set_clause = ", ".join(f"{k} = ?" for k in serialized)
        values = list(serialized.values()) + [obj_id]
        self._conn.execute(
            f"UPDATE {table} SET {set_clause} WHERE id = ?", values
        )
        self._conn.commit()
        return True

    def _delete(self, table: str, obj_id: str) -> bool:
        self._conn.execute(f"DELETE FROM {table} WHERE id = ?", (obj_id,))
        self._conn.commit()
        return True

    def _count(self, table: str, user_id: str = None, where: str = None, params: tuple = ()) -> int:
        if where:
            sql = f"SELECT COUNT(*) as cnt FROM {table} WHERE {where}"
            row = self._conn.execute(sql, params).fetchone()
        elif user_id:
            row = self._conn.execute(
                f"SELECT COUNT(*) as cnt FROM {table} WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        else:
            row = self._conn.execute(f"SELECT COUNT(*) as cnt FROM {table}").fetchone()
        return row["cnt"] if row else 0

    # ── Close ──────────────────────────────────────────────────────────

    def close(self):
        self._conn.close()


# ── Row converters: DB row dict → model ──────────────────────────────────

def _parse_dt(val) -> Optional[datetime]:
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None


def _row_to_job(row: dict) -> Job:
    return Job(
        id=row["id"],
        user_id=row.get("user_id", ""),
        company=row.get("company", ""),
        title=row.get("title", ""),
        status=JobStatus(row["status"]) if row.get("status") in ("interested", "applied", "interviewing", "offered", "rejected") else JobStatus.INTERESTED,
        jd_raw_text=row.get("jd_raw_text", ""),
        jd_parsed_fields=_json_loads(row.get("jd_parsed_fields"), {}),
        location=row.get("location", ""),
        salary_range=row.get("salary_range", ""),
        tags=_json_loads(row.get("tags"), []),
        direction=row.get("direction", ""),
        deadline=_parse_dt(row.get("deadline")),
        priority=row.get("priority", "中"),
        source_url=row.get("source_url", ""),
        notes=row.get("notes", ""),
        created_at=_parse_dt(row.get("created_at")) or datetime.now(),
        updated_at=_parse_dt(row.get("updated_at")) or datetime.now(),
    )


def _row_to_resume(row: dict) -> ResumeVersion:
    return ResumeVersion(
        id=row["id"],
        user_id=row.get("user_id", ""),
        version_name=row.get("version_name", ""),
        file_path=row.get("file_path", ""),
        parsed_content=_json_loads(row.get("parsed_content"), {}),
        summary_fields=_json_loads(row.get("summary_fields"), {}),
        tags=_json_loads(row.get("tags"), []),
        target_direction=row.get("target_direction", ""),
        keywords=_json_loads(row.get("keywords"), []),
        highlights=_json_loads(row.get("highlights"), []),
        created_at=_parse_dt(row.get("created_at")) or datetime.now(),
        updated_at=_parse_dt(row.get("updated_at")) or datetime.now(),
    )


def _row_to_application(row: dict) -> Application:
    return Application(
        id=row["id"],
        user_id=row.get("user_id", ""),
        job_id=row.get("job_id", ""),
        resume_id=row.get("resume_id", ""),
        applied_date=_parse_dt(row.get("applied_date")),
        channel=row.get("channel", ""),
        current_stage=row.get("current_stage", ""),
        status=row.get("status", ""),
        application_url=row.get("application_url", ""),
        termination_reason=row.get("termination_reason", ""),
        interview_date=_parse_dt(row.get("interview_date")),
        termination_date=_parse_dt(row.get("termination_date")),
        notes=row.get("notes", ""),
        created_at=_parse_dt(row.get("created_at")) or datetime.now(),
        updated_at=_parse_dt(row.get("updated_at")) or datetime.now(),
    )


def _row_to_interview(row: dict) -> InterviewRecord:
    return InterviewRecord(
        id=row["id"],
        user_id=row.get("user_id", ""),
        application_id=row.get("application_id", ""),
        round=InterviewRound(row["round"]) if row.get("round") in ("phone", "tech_1", "tech_2", "onsite", "hr", "final") else InterviewRound.PHONE,
        interview_date=_parse_dt(row.get("interview_date")),
        interviewer_feedback=row.get("interviewer_feedback", ""),
        self_rating=row.get("self_rating", 0),
        notes=row.get("notes", ""),
        created_at=_parse_dt(row.get("created_at")) or datetime.now(),
        updated_at=_parse_dt(row.get("updated_at")) or datetime.now(),
    )


def _row_to_journal(row: dict) -> InterviewJournal:
    return InterviewJournal(
        id=row["id"],
        user_id=row.get("user_id", ""),
        job_position=row.get("job_position", ""),
        round_progress=row.get("round_progress", ""),
        interview_date=_parse_dt(row.get("interview_date")),
        experience=row.get("experience", ""),
        questions_asked=row.get("questions_asked", ""),
        summary=row.get("summary", ""),
        created_at=_parse_dt(row.get("created_at")) or datetime.now(),
    )


def _row_to_match(row: dict) -> MatchResult:
    return MatchResult(
        id=row["id"],
        user_id=row.get("user_id", ""),
        job_id=row.get("job_id", ""),
        resume_id=row.get("resume_id", ""),
        match_score=row.get("match_score", 0.0),
        matched_points=_json_loads(row.get("matched_points"), []),
        missing_points=_json_loads(row.get("missing_points"), []),
        risk_notes=_json_loads(row.get("risk_notes"), []),
        optimization_suggestions=_json_loads(row.get("optimization_suggestions"), []),
        recommended_action=row.get("recommended_action", ""),
        gaps=_json_loads(row.get("gaps"), []),
        suggestions=_json_loads(row.get("suggestions"), []),
        created_at=_parse_dt(row.get("created_at")) or datetime.now(),
    )


def _row_to_prep_note(row: dict) -> PrepNote:
    return PrepNote(
        id=row["id"],
        user_id=row.get("user_id", ""),
        date=_parse_dt(row.get("date")),
        topic=row.get("topic", ""),
        content=row.get("content", ""),
        created_at=_parse_dt(row.get("created_at")) or datetime.now(),
    )


def _row_to_review(row: dict) -> WeeklyReview:
    return WeeklyReview(
        id=row["id"],
        user_id=row.get("user_id", ""),
        week_label=row.get("week_label", ""),
        date_range=row.get("date_range", ""),
        stats=_json_loads(row.get("stats"), {}),
        highlights=_json_loads(row.get("highlights"), []),
        next_week_focus=_json_loads(row.get("next_week_focus"), []),
        user_notes=row.get("user_notes", ""),
        created_at=_parse_dt(row.get("created_at")) or datetime.now(),
        updated_at=_parse_dt(row.get("updated_at")) or datetime.now(),
    )


# ── Row converters: model → DB dict ──────────────────────────────────────

def _job_to_row(job: Job) -> dict:
    return {
        "id": job.id,
        "user_id": job.user_id,
        "company": job.company,
        "title": job.title,
        "status": job.status.value if isinstance(job.status, JobStatus) else job.status,
        "jd_raw_text": job.jd_raw_text,
        "jd_parsed_fields": _json_dumps(job.jd_parsed_fields),
        "location": job.location,
        "salary_range": job.salary_range,
        "tags": _json_dumps(job.tags),
        "direction": job.direction,
        "deadline": job.deadline.isoformat() if job.deadline else None,
        "priority": job.priority,
        "source_url": job.source_url,
        "notes": job.notes,
        "created_at": job.created_at.isoformat() if job.created_at else _now(),
        "updated_at": job.updated_at.isoformat() if job.updated_at else _now(),
    }


def _resume_to_row(resume: ResumeVersion) -> dict:
    return {
        "id": resume.id,
        "user_id": resume.user_id,
        "version_name": resume.version_name,
        "file_path": resume.file_path,
        "parsed_content": _json_dumps(resume.parsed_content),
        "summary_fields": _json_dumps(resume.summary_fields),
        "tags": _json_dumps(resume.tags),
        "target_direction": resume.target_direction,
        "keywords": _json_dumps(resume.keywords),
        "highlights": _json_dumps(resume.highlights),
        "created_at": resume.created_at.isoformat() if resume.created_at else _now(),
        "updated_at": resume.updated_at.isoformat() if resume.updated_at else _now(),
    }


def _application_to_row(app: Application) -> dict:
    return {
        "id": app.id,
        "user_id": app.user_id,
        "job_id": app.job_id,
        "resume_id": app.resume_id,
        "applied_date": app.applied_date.isoformat() if app.applied_date else None,
        "channel": app.channel,
        "current_stage": app.current_stage,
        "status": app.status,
        "application_url": app.application_url,
        "termination_reason": app.termination_reason,
        "interview_date": app.interview_date.isoformat() if app.interview_date else None,
        "termination_date": app.termination_date.isoformat() if app.termination_date else None,
        "notes": app.notes,
        "created_at": app.created_at.isoformat() if app.created_at else _now(),
        "updated_at": app.updated_at.isoformat() if app.updated_at else _now(),
    }


def _interview_to_row(iv: InterviewRecord) -> dict:
    return {
        "id": iv.id,
        "user_id": iv.user_id,
        "application_id": iv.application_id,
        "round": iv.round.value if isinstance(iv.round, InterviewRound) else iv.round,
        "interview_date": iv.interview_date.isoformat() if iv.interview_date else None,
        "interviewer_feedback": iv.interviewer_feedback,
        "self_rating": iv.self_rating,
        "notes": iv.notes,
        "created_at": iv.created_at.isoformat() if iv.created_at else _now(),
        "updated_at": iv.updated_at.isoformat() if iv.updated_at else _now(),
    }


def _journal_to_row(j: InterviewJournal) -> dict:
    return {
        "id": j.id,
        "user_id": j.user_id,
        "job_position": j.job_position,
        "round_progress": j.round_progress,
        "interview_date": j.interview_date.isoformat() if j.interview_date else None,
        "experience": j.experience,
        "questions_asked": j.questions_asked,
        "summary": j.summary,
        "created_at": j.created_at.isoformat() if j.created_at else _now(),
        "updated_at": _now(),
    }


def _match_to_row(m: MatchResult) -> dict:
    return {
        "id": m.id,
        "user_id": m.user_id,
        "job_id": m.job_id,
        "resume_id": m.resume_id,
        "match_score": m.match_score,
        "matched_points": _json_dumps(m.matched_points),
        "missing_points": _json_dumps(m.missing_points),
        "risk_notes": _json_dumps(m.risk_notes),
        "optimization_suggestions": _json_dumps(m.optimization_suggestions),
        "recommended_action": m.recommended_action,
        "gaps": _json_dumps(m.gaps),
        "suggestions": _json_dumps(m.suggestions),
        "created_at": m.created_at.isoformat() if m.created_at else _now(),
        "updated_at": _now(),
    }


def _prep_note_to_row(n: PrepNote) -> dict:
    return {
        "id": n.id,
        "user_id": n.user_id,
        "date": n.date.isoformat() if n.date else None,
        "topic": n.topic,
        "content": n.content,
        "created_at": n.created_at.isoformat() if n.created_at else _now(),
        "updated_at": _now(),
    }


def _review_to_row(r: WeeklyReview) -> dict:
    return {
        "id": r.id,
        "user_id": r.user_id,
        "week_label": r.week_label,
        "date_range": r.date_range,
        "stats": _json_dumps(r.stats),
        "highlights": _json_dumps(r.highlights),
        "next_week_focus": _json_dumps(r.next_week_focus),
        "user_notes": r.user_notes,
        "created_at": r.created_at.isoformat() if r.created_at else _now(),
        "updated_at": r.updated_at.isoformat() if r.updated_at else _now(),
    }


# ── Old-store migration converters ───────────────────────────────────────

def _row_from_old_job(obj_id: str, user_id: str, d: dict) -> dict:
    return _job_to_row(Job(
        id=obj_id, user_id=user_id,
        company=d.get("company", ""), title=d.get("title", ""),
        status=_enum_val(JobStatus, d.get("status", "interested")),
        jd_raw_text=d.get("jd_raw_text", ""),
        jd_parsed_fields=_deser(d.get("jd_parsed_fields"), {}),
        location=d.get("location", ""), salary_range=d.get("salary_range", ""),
        tags=_deser(d.get("tags"), []), direction=d.get("direction", ""),
        deadline=_parse_dt_field(d.get("deadline")),
        priority=d.get("priority", "中"), source_url=d.get("source_url", ""),
        notes=d.get("notes", ""),
        created_at=_parse_dt_field(d.get("created_at")) or datetime.now(),
        updated_at=_parse_dt_field(d.get("updated_at")) or datetime.now(),
    ))


def _row_from_old_resume(obj_id: str, user_id: str, d: dict) -> dict:
    return _resume_to_row(ResumeVersion(
        id=obj_id, user_id=user_id,
        version_name=d.get("version_name", ""), file_path=d.get("file_path", ""),
        parsed_content=_deser(d.get("parsed_content"), {}),
        summary_fields=_deser(d.get("summary_fields"), {}),
        tags=_deser(d.get("tags"), []),
        target_direction=d.get("target_direction", ""),
        keywords=_deser(d.get("keywords"), []),
        highlights=_deser(d.get("highlights"), []),
        created_at=_parse_dt_field(d.get("created_at")) or datetime.now(),
        updated_at=_parse_dt_field(d.get("updated_at")) or datetime.now(),
    ))


def _row_from_old_application(obj_id: str, user_id: str, d: dict) -> dict:
    return _application_to_row(Application(
        id=obj_id, user_id=user_id,
        job_id=d.get("job_id", ""), resume_id=d.get("resume_id", ""),
        applied_date=_parse_dt_field(d.get("applied_date")),
        channel=d.get("channel", ""), current_stage=d.get("current_stage", ""),
        status=d.get("status", ""),
        application_url=d.get("application_url", ""),
        termination_reason=d.get("termination_reason", ""),
        interview_date=_parse_dt_field(d.get("interview_date")),
        termination_date=_parse_dt_field(d.get("termination_date")),
        notes=d.get("notes", ""),
        created_at=_parse_dt_field(d.get("created_at")) or datetime.now(),
        updated_at=_parse_dt_field(d.get("updated_at")) or datetime.now(),
    ))


def _row_from_old_interview(obj_id: str, user_id: str, d: dict) -> dict:
    return _interview_to_row(InterviewRecord(
        id=obj_id, user_id=user_id,
        application_id=d.get("application_id", ""),
        round=_enum_val(InterviewRound, d.get("round", "phone")),
        interview_date=_parse_dt_field(d.get("interview_date")),
        interviewer_feedback=d.get("interviewer_feedback", ""),
        self_rating=d.get("self_rating", 0),
        notes=d.get("notes", ""),
        created_at=_parse_dt_field(d.get("created_at")) or datetime.now(),
        updated_at=_parse_dt_field(d.get("updated_at")) or datetime.now(),
    ))


def _row_from_old_journal(obj_id: str, user_id: str, d: dict) -> dict:
    return _journal_to_row(InterviewJournal(
        id=obj_id, user_id=user_id,
        job_position=d.get("job_position", ""),
        round_progress=d.get("round_progress", ""),
        interview_date=_parse_dt_field(d.get("interview_date")),
        experience=d.get("experience", ""),
        questions_asked=d.get("questions_asked", ""),
        summary=d.get("summary", ""),
        created_at=_parse_dt_field(d.get("created_at")) or datetime.now(),
    ))


def _row_from_old_match(obj_id: str, user_id: str, d: dict) -> dict:
    return _match_to_row(MatchResult(
        id=obj_id, user_id=user_id,
        job_id=d.get("job_id", ""), resume_id=d.get("resume_id", ""),
        match_score=d.get("match_score", 0.0),
        matched_points=_deser(d.get("matched_points"), []),
        missing_points=_deser(d.get("missing_points"), []) or _deser(d.get("gaps"), []),
        risk_notes=_deser(d.get("risk_notes"), []),
        optimization_suggestions=_deser(d.get("optimization_suggestions"), []) or _deser(d.get("suggestions"), []),
        recommended_action=d.get("recommended_action", ""),
        gaps=_deser(d.get("gaps"), []),
        suggestions=_deser(d.get("suggestions"), []),
        created_at=_parse_dt_field(d.get("created_at")) or datetime.now(),
    ))


def _row_from_old_review(obj_id: str, user_id: str, d: dict) -> dict:
    return _review_to_row(WeeklyReview(
        id=obj_id, user_id=user_id,
        week_label=d.get("week_label", ""), date_range=d.get("date_range", ""),
        stats=_deser(d.get("stats"), {}),
        highlights=_deser(d.get("highlights"), []),
        next_week_focus=_deser(d.get("next_week_focus"), []),
        user_notes=d.get("user_notes", ""),
        created_at=_parse_dt_field(d.get("created_at")) or datetime.now(),
        updated_at=_parse_dt_field(d.get("updated_at")) or datetime.now(),
    ))


def _enum_val(enum_cls, val):
    """Safely convert a string to an enum value."""
    if isinstance(val, enum_cls):
        return val
    try:
        return enum_cls(val)
    except (ValueError, KeyError):
        # Return first enum member as default
        return list(enum_cls)[0]


def _parse_dt_field(val):
    """Parse datetime from various representations."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, dict) and "__dt__" in val:
        try:
            return datetime.fromisoformat(val["__dt__"])
        except Exception:
            return None
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val)
        except Exception:
            return None
    return None


def _deser(val, default=None):
    """Deserialize values that may be dicts, lists, or already deserialized."""
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        return _json_loads(val, default)
    return default if default is not None else val
