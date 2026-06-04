"""SQLite-backed data store for OfferPilot multi-user support.

All data is persisted to ``data/offerpilot.db`` via the Database layer.
On first run, old ``data/store.json`` data is automatically migrated.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from core.database import (
    Database, DB_PATH, RESUMES_DIR,
    _row_to_job, _row_to_resume, _row_to_application, _row_to_interview,
    _row_to_journal, _row_to_match, _row_to_review,
    _job_to_row, _resume_to_row, _application_to_row, _interview_to_row,
    _journal_to_row, _match_to_row, _review_to_row,
    _json_dumps, _json_loads, _now, _parse_dt,
)
from core.models import (
    Job, JobStatus, ResumeVersion, Application,
    InterviewRecord, InterviewRound, MatchResult, WeeklyReview,
    InterviewJournal, UserProfile,
    APPLICATION_STATUSES_V2,
)


# ── User profile row converters ───────────────────────────────────────────

def _row_to_user(row: dict) -> UserProfile:
    return UserProfile(
        id=row.get("id", ""),
        username=row.get("username", ""),
        display_name=row.get("display_name", ""),
        school=row.get("school", ""),
        major=row.get("major", ""),
        degree=row.get("degree", ""),
        graduation_year=row.get("graduation_year", ""),
        target_directions=_json_loads(row.get("target_directions"), []),
        target_cities=_json_loads(row.get("target_cities"), []),
        bio=row.get("bio", ""),
        password_hash=row.get("password_hash", ""),
        llm_settings=_json_loads(row.get("llm_settings"), {}),
        created_at=_parse_dt(row.get("created_at")) or datetime.now(),
        updated_at=_parse_dt(row.get("updated_at")) or datetime.now(),
    )


# ── DataStore ──────────────────────────────────────────────────────────────

class DataStore:
    """SQLite-backed data store replacing the old JSON file store.

    Usage::

        store = DataStore()
        store.set_current_user(user_id)

        jobs = store.get_all_jobs()          # scoped to current user
        store.add_job(job)                   # auto-assigns user_id

    All ``get_all_*`` / ``add_*`` methods accept an optional ``user_id``
    keyword.  When omitted, ``user_id`` defaults to the value set via
    ``set_current_user()``.
    """

    def __init__(self):
        self._db = Database()
        self._current_user_id: Optional[str] = None

    def set_current_user(self, user_id: str):
        """Set the user context for subsequent data operations."""
        self._current_user_id = user_id

    @property
    def _uid(self) -> str:
        if not self._current_user_id:
            raise RuntimeError("DataStore: no current user set. Call set_current_user() first.")
        return self._current_user_id

    def _resolve_uid(self, user_id: Optional[str] = None) -> str:
        return user_id or self._uid

    # ── User ────────────────────────────────────────────────────────────

    def create_user(self, username: str, display_name: str, password_hash: str) -> tuple[bool, str]:
        """Create a new user. Returns (success, user_id_or_message)."""
        return self._db.create_user(username, display_name, password_hash)

    def get_user_by_username(self, username: str) -> Optional[dict]:
        return self._db.get_user_by_username(username)

    def get_user(self, user_id: str) -> Optional[dict]:
        return self._db.get_user(user_id)

    def update_user(self, user_id: str, fields: dict) -> bool:
        return self._db.update_user(user_id, fields)

    def get_user_profile(self, user_id: Optional[str] = None) -> Optional[UserProfile]:
        """Return the current user's profile as a UserProfile dataclass."""
        uid = self._resolve_uid(user_id)
        row = self._db.get_user(uid)
        return _row_to_user(row) if row else None

    def save_user_profile(self, profile: UserProfile):
        """Persist a UserProfile dataclass to the users table."""
        fields = {
            "display_name": profile.display_name,
            "school": profile.school,
            "major": profile.major,
            "degree": profile.degree,
            "graduation_year": profile.graduation_year,
            "target_directions": profile.target_directions,
            "target_cities": profile.target_cities,
            "bio": profile.bio,
            "password_hash": profile.password_hash,
            "llm_settings": profile.llm_settings,
        }
        self._db.update_user(profile.id, fields)

    def get_llm_settings(self, user_id: Optional[str] = None) -> dict:
        """Return the LLM settings dict for the given (or current) user."""
        uid = self._resolve_uid(user_id)
        row = self._db.get_user(uid)
        if row:
            return _json_loads(row.get("llm_settings"), {})
        return {}

    def save_llm_settings(self, settings: dict, user_id: Optional[str] = None):
        """Persist LLM settings dict for the given (or current) user."""
        uid = self._resolve_uid(user_id)
        # Ensure user row exists (edge case: test users or deleted users)
        existing = self._db.get_user(uid)
        if not existing:
            from datetime import datetime as _dt
            self._db._conn.execute(
                "INSERT OR IGNORE INTO users(id, username, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (uid, uid, _dt.now().isoformat(), _dt.now().isoformat()),
            )
            self._db._conn.commit()
        self._db.update_user(uid, {"llm_settings": settings})

    # ── Jobs ────────────────────────────────────────────────────────────

    def get_all_jobs(self, user_id: Optional[str] = None) -> list[Job]:
        uid = self._resolve_uid(user_id)
        return self._db._get_all("jobs", uid, Job, _row_to_job)

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._db._get_one("jobs", job_id, Job, _row_to_job)

    def add_job(self, job: Job, user_id: Optional[str] = None):
        job.user_id = self._resolve_uid(user_id)
        if not job.created_at:
            job.created_at = datetime.now()
        if not job.updated_at:
            job.updated_at = datetime.now()
        self._db._insert("jobs", job, _job_to_row)

    def update_job(self, job: Job):
        job.updated_at = datetime.now()
        row = _job_to_row(job)
        # Re-insert via replace (since we have the full object)
        self._db._update("jobs", job.id, {
            k: v for k, v in row.items() if k not in ("id", "user_id")
        })

    # ── Resumes ─────────────────────────────────────────────────────────

    def get_all_resumes(self, user_id: Optional[str] = None) -> list[ResumeVersion]:
        uid = self._resolve_uid(user_id)
        return self._db._get_all("resumes", uid, ResumeVersion, _row_to_resume)

    def get_resume(self, resume_id: str) -> Optional[ResumeVersion]:
        return self._db._get_one("resumes", resume_id, ResumeVersion, _row_to_resume)

    def add_resume(self, resume: ResumeVersion, user_id: Optional[str] = None):
        resume.user_id = self._resolve_uid(user_id)
        if not resume.created_at:
            resume.created_at = datetime.now()
        if not resume.updated_at:
            resume.updated_at = datetime.now()
        self._db._insert("resumes", resume, _resume_to_row)

    def update_resume(self, resume_id: str, updated_fields: dict) -> tuple[bool, str]:
        resume = self.get_resume(resume_id)
        if resume is None:
            return (False, f"简历版本 '{resume_id}' 不存在")
        for key, value in updated_fields.items():
            if hasattr(resume, key):
                setattr(resume, key, value)
        resume.updated_at = datetime.now()
        row = _resume_to_row(resume)
        self._db._update("resumes", resume_id, {
            k: v for k, v in row.items() if k not in ("id", "user_id")
        })
        return (True, "简历版本已更新")

    def delete_resume(self, resume_id: str) -> tuple[bool, str]:
        ref_count = self.get_resume_application_count(resume_id)
        if ref_count > 0:
            return (
                False,
                f"该简历版本被 {ref_count} 条投递记录引用，无法删除。"
                f"请先删除相关投递记录后再删除简历。",
            )
        resume = self.get_resume(resume_id)
        if resume is None:
            return (False, f"简历版本 '{resume_id}' 不存在")
        # Remove uploaded file
        if resume.file_path:
            try:
                file_p = Path(resume.file_path)
                if file_p.exists():
                    file_p.unlink()
            except OSError:
                pass
        self._db._delete("resumes", resume_id)
        return (True, f"简历版本 '{resume.version_name}' 已删除")

    def get_resume_application_count(self, resume_id: str) -> int:
        return self._db._count(
            "applications",
            where="resume_id = ? AND user_id = ?",
            params=(resume_id, self._uid),
        )

    def is_resume_used(self, resume_id: str) -> bool:
        return self.get_resume_application_count(resume_id) > 0

    # ── Applications ────────────────────────────────────────────────────

    def get_all_applications(self, user_id: Optional[str] = None) -> list[Application]:
        uid = self._resolve_uid(user_id)
        return self._db._get_all("applications", uid, Application, _row_to_application)

    def get_application(self, app_id: str) -> Optional[Application]:
        return self._db._get_one("applications", app_id, Application, _row_to_application)

    def add_application(self, app: Application, user_id: Optional[str] = None):
        app.user_id = self._resolve_uid(user_id)
        if not app.created_at:
            app.created_at = datetime.now()
        if not app.updated_at:
            app.updated_at = datetime.now()
        self._db._insert("applications", app, _application_to_row)

    def update_application(self, application_id: str, updated_fields: dict) -> tuple[bool, str]:
        app = self.get_application(application_id)
        if app is None:
            return (False, f"投递记录 '{application_id}' 不存在")
        for key, value in updated_fields.items():
            if hasattr(app, key):
                setattr(app, key, value)
        app.updated_at = datetime.now()
        row = _application_to_row(app)
        self._db._update("applications", application_id, {
            k: v for k, v in row.items() if k not in ("id", "user_id")
        })
        return (True, "投递记录已更新")

    def delete_application(self, application_id: str) -> tuple[bool, str]:
        app = self.get_application(application_id)
        if app is None:
            return (False, f"投递记录 '{application_id}' 不存在")

        job_id = app.job_id
        self._db._delete("applications", application_id)

        # Clean up orphaned job
        other_apps = self._db._count(
            "applications",
            where="job_id = ? AND user_id = ?",
            params=(job_id, self._uid),
        )
        if other_apps == 0:
            job = self.get_job(job_id)
            company = job.company if job else "未知公司"
            self._db._delete("jobs", job_id)
            return (True, f"已删除 {company} 的投递记录及关联岗位")

        job = self.get_job(job_id)
        company = job.company if job else "未知公司"
        return (True, f"已删除 {company} 的投递记录")

    def update_application_status(self, application_id: str, new_status: str):
        app = self.get_application(application_id)
        if app is None:
            raise KeyError(f"Application '{application_id}' not found")
        now = datetime.now()
        app.status = new_status
        app.updated_at = now

        interview_stages = {"笔试/测评", "一面", "二面", "HR面"}
        if new_status in interview_stages:
            app.interview_date = now
        if new_status == "终止":
            app.termination_date = now

        row = _application_to_row(app)
        self._db._update("applications", application_id, {
            k: v for k, v in row.items() if k not in ("id", "user_id")
        })

    # ── InterviewRecord ─────────────────────────────────────────────────

    def get_all_interviews(self, user_id: Optional[str] = None) -> list[InterviewRecord]:
        uid = self._resolve_uid(user_id)
        return self._db._get_all("interviews", uid, InterviewRecord, _row_to_interview)

    def get_interview(self, interview_id: str) -> Optional[InterviewRecord]:
        return self._db._get_one("interviews", interview_id, InterviewRecord, _row_to_interview)

    def add_interview(self, interview: InterviewRecord, user_id: Optional[str] = None):
        interview.user_id = self._resolve_uid(user_id)
        if not interview.created_at:
            interview.created_at = datetime.now()
        if not interview.updated_at:
            interview.updated_at = datetime.now()
        self._db._insert("interviews", interview, _interview_to_row)

    def update_interview(self, interview: InterviewRecord):
        interview.updated_at = datetime.now()
        row = _interview_to_row(interview)
        self._db._update("interviews", interview.id, {
            k: v for k, v in row.items() if k not in ("id", "user_id")
        })

    # ── InterviewJournal ────────────────────────────────────────────────

    def get_all_interview_journals(self, user_id: Optional[str] = None) -> list[InterviewJournal]:
        uid = self._resolve_uid(user_id)
        return self._db._get_all("interview_journals", uid, InterviewJournal, _row_to_journal)

    def get_interview_journal(self, journal_id: str) -> Optional[InterviewJournal]:
        return self._db._get_one("interview_journals", journal_id, InterviewJournal, _row_to_journal)

    def add_interview_journal(self, journal: InterviewJournal, user_id: Optional[str] = None):
        journal.user_id = self._resolve_uid(user_id)
        if not journal.created_at:
            journal.created_at = datetime.now()
        self._db._insert("interview_journals", journal, _journal_to_row)

    def update_interview_journal(self, journal: InterviewJournal):
        row = _journal_to_row(journal)
        self._db._update("interview_journals", journal.id, {
            k: v for k, v in row.items() if k not in ("id", "user_id")
        })

    def delete_interview_journal(self, journal_id: str) -> tuple[bool, str]:
        journal = self.get_interview_journal(journal_id)
        if journal is None:
            return (False, f"面试记录 '{journal_id}' 不存在")
        position = journal.job_position or "未知岗位"
        self._db._delete("interview_journals", journal_id)
        return (True, f"面试记录「{position}」已删除")

    # ── MatchResult ─────────────────────────────────────────────────────

    def get_all_match_results(self, user_id: Optional[str] = None) -> list[MatchResult]:
        uid = self._resolve_uid(user_id)
        return self._db._get_all("match_results", uid, MatchResult, _row_to_match)

    def get_match_result(self, match_id: str) -> Optional[MatchResult]:
        return self._db._get_one("match_results", match_id, MatchResult, _row_to_match)

    def get_match_result_by_job_resume(self, job_id: str, resume_id: str) -> Optional[MatchResult]:
        row = self._db._conn.execute(
            "SELECT * FROM match_results WHERE job_id = ? AND resume_id = ? AND user_id = ?",
            (job_id, resume_id, self._uid),
        ).fetchone()
        return _row_to_match(dict(row)) if row else None

    def add_match_result(self, match: MatchResult, user_id: Optional[str] = None):
        match.user_id = self._resolve_uid(user_id)
        if not match.created_at:
            match.created_at = datetime.now()
        self._db._insert("match_results", match, _match_to_row)

    # ── WeeklyReview ────────────────────────────────────────────────────

    def get_all_weekly_reviews(self, user_id: Optional[str] = None) -> list[WeeklyReview]:
        uid = self._resolve_uid(user_id)
        return self._db._get_all("weekly_reviews", uid, WeeklyReview, _row_to_review)

    def get_weekly_review(self, review_id: str) -> Optional[WeeklyReview]:
        return self._db._get_one("weekly_reviews", review_id, WeeklyReview, _row_to_review)

    def add_weekly_review(self, review: WeeklyReview, user_id: Optional[str] = None):
        review.user_id = self._resolve_uid(user_id)
        if not review.created_at:
            review.created_at = datetime.now()
        if not review.updated_at:
            review.updated_at = datetime.now()
        self._db._insert("weekly_reviews", review, _review_to_row)

    def update_weekly_review(self, review_id: str, updated_fields: dict) -> tuple[bool, str]:
        review = self.get_weekly_review(review_id)
        if review is None:
            return (False, f"周报 '{review_id}' 不存在")
        for key, value in updated_fields.items():
            if hasattr(review, key):
                setattr(review, key, value)
        review.updated_at = datetime.now()
        row = _review_to_row(review)
        self._db._update("weekly_reviews", review_id, {
            k: v for k, v in row.items() if k not in ("id", "user_id")
        })
        return (True, "周报已更新")

    def get_latest_weekly_review(self) -> Optional[WeeklyReview]:
        reviews = self.get_all_weekly_reviews()
        return reviews[0] if reviews else None

    # ── Legacy ──────────────────────────────────────────────────────────

    def get_all_reports(self) -> list:
        return []

    def reload(self):
        """No-op: SQLite reads are always fresh."""
        pass

    def close(self):
        self._db.close()


# ── Global singleton ──────────────────────────────────────────────────────

store = DataStore()
