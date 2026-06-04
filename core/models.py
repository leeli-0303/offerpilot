"""Core data models for OfferPilot — aligned with PRODUCT_SPEC.md."""


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ── Enums ───────────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    INTERESTED = "interested"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFERED = "offered"
    REJECTED = "rejected"


class InterviewRound(str, Enum):
    PHONE = "phone"
    TECH_1 = "tech_1"
    TECH_2 = "tech_2"
    ONSITE = "onsite"
    HR = "hr"
    FINAL = "final"


# ── Application status constants ────────────────────────────────────────

# Deprecated: APPLICATION_STATUSES — use APPLICATION_STATUSES_V2 instead.
# Kept for backward compatibility with existing code that still references it.
APPLICATION_STATUSES = [
    "待投递",
    "已投递",
    "笔试 / 测评",
    "一面",
    "二面",
    "HR 面",
    "Offer",
    "拒绝",
    "放弃",
]

APPLICATION_STATUSES_V2 = [
    "已投递",
    "简历评估",
    "笔试/测评",
    "一面",
    "二面",
    "HR面",
    "offer",
    "终止",
    "放弃",
]

# Deprecated: NEXT_ACTION_MAP — use NEXT_ACTION_MAP_V2 instead.
NEXT_ACTION_MAP: dict[str, str] = {
    "待投递": "准备投递材料，确认简历版本",
    "已投递": "等待反馈，5 个工作日后可跟进",
    "笔试 / 测评": "完成在线测评，注意截止时间",
    "一面": "准备技术基础、项目经验和算法题",
    "二面": "准备系统设计、项目深挖和行为面试",
    "HR 面": "准备薪资期望、入职时间和职业规划",
    "Offer": "评估 Offer 条件，决定是否接受",
    "拒绝": "总结经验，继续投递其他岗位",
    "放弃": "—",
}

NEXT_ACTION_MAP_V2: dict[str, str] = {
    "已投递": "等待反馈，5-7 个工作日后可跟进",
    "简历评估": "简历已进入评估阶段，关注邮件/短信通知",
    "笔试/测评": "完成在线测评，注意截止时间",
    "一面": "准备技术基础、项目经验和算法题",
    "二面": "准备系统设计、项目深挖和行为面试",
    "HR面": "准备薪资期望、入职时间和职业规划",
    "offer": "评估 Offer 条件，决定是否接受",
    "终止": "记录终止原因并复盘，为后续投递积累经验",
    "放弃": "归档该投递记录",
}


# ── Domain Models ───────────────────────────────────────────────────────

@dataclass
class Job:
    """A job position the user is tracking."""
    id: str
    company: str
    title: str
    user_id: str = ""
    status: JobStatus = JobStatus.INTERESTED
    jd_raw_text: str = ""
    jd_parsed_fields: dict = field(default_factory=dict)
    location: str = ""
    salary_range: str = ""
    tags: list[str] = field(default_factory=list)
    direction: str = ""          # e.g. 后端 / 前端 / 算法 / 数据 / 产品
    deadline: Optional[datetime] = None
    priority: str = "中"         # 高 / 中 / 低
    source_url: str = ""
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ResumeVersion:
    """A specific version of the user's resume (e.g. backend-CN, backend-EN, ML-CN)."""
    id: str
    version_name: str
    user_id: str = ""
    file_path: str = ""
    parsed_content: dict = field(default_factory=dict)
    summary_fields: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    target_direction: str = ""   # e.g. 后端 / 前端 / 算法
    keywords: list[str] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Application:
    """A job application record linking a Job to a ResumeVersion."""
    id: str
    job_id: str
    resume_id: str
    user_id: str = ""
    applied_date: Optional[datetime] = None
    channel: str = ""               # e.g. 内推 / 官网 / BOSS直聘
    current_stage: str = ""         # e.g. 简历筛选 / 技术二面 / 已发Offer
    status: str = ""                # uses APPLICATION_STATUSES_V2
    application_url: str = ""       # 投递链接（招聘官网/Boss/内推链接等）
    termination_reason: str = ""    # 终止原因，仅 status=="终止" 时有值
    interview_date: Optional[datetime] = None   # 面试时间（进入面试环节时自动更新）
    termination_date: Optional[datetime] = None # 终止时间（状态变为「终止」时自动记录）
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class InterviewRecord:
    """A record of a single interview round for an application."""
    id: str
    application_id: str
    user_id: str = ""
    round: InterviewRound = InterviewRound.PHONE
    interview_date: Optional[datetime] = None
    interviewer_feedback: str = ""
    self_rating: int = 0       # 1-5 self assessment
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class MatchResult:
    """AI-generated or rule-based job-to-resume match analysis result."""
    id: str
    job_id: str
    resume_id: str
    user_id: str = ""
    match_score: float = 0.0          # 0-100
    matched_points: list[str] = field(default_factory=list)       # what matched well
    missing_points: list[str] = field(default_factory=list)       # skills/keywords missing from resume
    risk_notes: list[str] = field(default_factory=list)           # risks from JD (996, 外包, etc.)
    optimization_suggestions: list[str] = field(default_factory=list)  # how to improve the resume
    recommended_action: str = ""       # e.g. 建议投递 / 可以尝试 / 建议观望
    # Legacy fields kept for backward compat with existing store.json
    gaps: list[str] = field(default_factory=list)       # deprecated alias for missing_points
    suggestions: list[str] = field(default_factory=list)  # deprecated alias for optimization_suggestions
    created_at: datetime = field(default_factory=datetime.now)
    # Internal flags set by LLM caller for UI feedback
    _fallback: bool = False          # True when LLM failed and rule-based fallback was used
    _fallback_reason: str = ""       # Human-readable fallback reason
    _raw_output: str = ""            # Raw LLM response for debugging


@dataclass
class WeeklyReview:
    """AI-generated weekly job-hunting summary report."""
    id: str
    user_id: str = ""
    week_label: str = ""       # e.g. "2026年第20周"
    date_range: str = ""       # e.g. "2026.05.11 - 2026.05.17"
    stats: dict = field(default_factory=dict)   # {new_jobs, applications_sent, interviews_completed, offers_received}
    highlights: list[str] = field(default_factory=list)
    next_week_focus: list[str] = field(default_factory=list)
    user_notes: str = ""       # user's own remarks / reflections on this weekly review
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    # Internal flags set by LLM caller for UI feedback
    _fallback: bool = False          # True when LLM failed and rule-based fallback was used
    _fallback_reason: str = ""       # Human-readable fallback reason
    _raw_output: str = ""            # Raw LLM response for debugging


@dataclass
class InterviewJournal:
    """A manual interview review entry for self-reflection after an interview.

    Unlike InterviewRecord (which is auto-linked to applications), this is a
    free-form journal that the user fills in manually to capture their
    experience, the questions they were asked, and lessons learned.
    """
    id: str
    user_id: str = ""
    job_position: str = ""         # 岗位（公司 + 岗位名称）
    round_progress: str = ""       # 进度（一面 / 二面 / HR面 / 终面 等）
    interview_date: Optional[datetime] = None
    experience: str = ""           # 面试体验
    questions_asked: str = ""      # 被问到的问题
    summary: str = ""              # 总结反思
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class UserProfile:
    """Local user profile — simple single-user identity & preferences.

    Since OfferPilot is a single-user desktop app, the "auth" is a
    lightweight gate: a password hash stored alongside preferences.
    """
    id: str = "user-001"
    username: str = ""
    display_name: str = ""         # 昵称 / 显示名
    school: str = ""               # 学校
    major: str = ""                # 专业
    degree: str = ""               # 学历（本科 / 硕士 / 博士）
    graduation_year: str = ""      # 毕业年份
    target_directions: list[str] = field(default_factory=list)  # 意向方向
    target_cities: list[str] = field(default_factory=list)      # 意向城市
    bio: str = ""                  # 个人简介
    password_hash: str = ""        # SHA-256 hashed password
    llm_settings: dict = field(default_factory=dict)  # user's own LLM API config
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
