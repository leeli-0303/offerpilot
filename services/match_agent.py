"""Rule-based job-to-resume matching service.

Computes a match analysis by comparing a Job's parsed fields (skills,
keywords, direction) against a ResumeVersion's keywords, highlights,
and target direction.  No LLM calls.
"""

import re
import math

from core.models import Job, ResumeVersion, MatchResult
from core.utils import generate_id


# ── Fuzzy skill matching ─────────────────────────────────────────────────

# Common skill aliases (lowercase normalized form → canonical)
_SKILL_ALIASES: dict[str, str] = {
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "js": "javascript",
    "javascript": "javascript",
    "ts": "typescript",
    "typescript": "typescript",
    "golang": "go",
    "go": "go",
    "cpp": "c++",
    "cplusplus": "c++",
    "reactjs": "react",
    "vuejs": "vue",
    "nodejs": "node",
    "node": "node.js",
    "postgres": "postgresql",
    "psql": "postgresql",
    "es": "elasticsearch",
    "elastic": "elasticsearch",
    "tf": "tensorflow",
    "pytorch": "pytorch",
    "torch": "pytorch",
    "sklearn": "scikit-learn",
    "scikit-learn": "scikit-learn",
    "ml": "机器学习",
    "dl": "深度学习",
    "nlp": "自然语言处理",
    "cv": "计算机视觉",
    "aws": "aws",
    "gcp": "gcp",
    "azure": "azure",
}


def _normalize_skill_name(name: str) -> str:
    """Normalize a skill/keyword string for comparison.

    - lowercase
    - strip whitespace
    - remove punctuation (dots, hyphens, hashes)
    - resolve common aliases
    """
    s = name.lower().strip()
    # Remove common punctuation but keep word structure
    s = re.sub(r"[.\-#]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Resolve alias
    return _SKILL_ALIASES.get(s, s)


def _skills_overlap(a: str, b: str) -> bool:
    """Return True if two skill strings refer to the same thing.

    Checks: exact match after normalization, then substring containment.
    """
    na = _normalize_skill_name(a)
    nb = _normalize_skill_name(b)
    if na == nb:
        return True
    # Substring: "Spring Boot" contains "Spring"
    if na in nb or nb in na:
        return True
    # Word-level: check if any word from one appears in the other
    words_a = set(na.split())
    words_b = set(nb.split())
    if words_a & words_b:
        return True
    return False


# ── Scoring constants ────────────────────────────────────────────────────

# Weights for each scoring dimension (must sum to 1.0)
_W_SKILLS = 0.45       # technical skill overlap
_W_KEYWORDS = 0.20     # non-skill keyword overlap (校招, 应届, 行业…)
_W_DIRECTION = 0.20    # direction / target alignment
_W_HIGHLIGHTS = 0.15   # project / highlight richness

# Score floors for empty inputs
_FLOOR_NO_SKILLS = 40      # when job lists no skills — can't penalise
_FLOOR_NO_KEYWORDS = 50    # when job lists no keywords
_FLOOR_NO_HIGHLIGHTS = 50  # when resume has no highlights

# Risk deduction per risk note
_RISK_DEDUCTION = 3  # points per risk note

# Recommended action thresholds
_THRESHOLD_STRONG = 75   # ≥ 75 → 强烈建议投递
_THRESHOLD_OK = 50       # ≥ 50 → 可以尝试


# ── Public API ───────────────────────────────────────────────────────────

def calculate_match_rule_based(job: Job, resume: ResumeVersion) -> MatchResult:
    """Analyse how well *job* and *resume* match using rule-based scoring.

    Args:
        job: A Job (with jd_parsed_fields populated).
        resume: A ResumeVersion (with keywords / highlights populated).

    Returns:
        A MatchResult with score, matched/missing points, risk notes,
        optimisation suggestions, and a recommended action.
    """
    # ── 1. Gather inputs ──────────────────────────────────────────────
    job_skills_raw: list[str] = job.jd_parsed_fields.get("skills", []) or []
    job_keywords_raw: list[str] = job.jd_parsed_fields.get("keywords", []) or []
    job_risk_notes: list[str] = job.jd_parsed_fields.get("risk_notes", []) or []
    job_direction: str = (job.direction or "").strip()

    resume_keywords: list[str] = resume.keywords or []
    resume_highlights: list[str] = resume.highlights or []
    resume_direction: str = (resume.target_direction or "").strip()

    # ── 2. Match skills ───────────────────────────────────────────────
    matched_skills: list[str] = []
    missing_skills: list[str] = []

    for js in job_skills_raw:
        if not js.strip():
            continue
        if any(_skills_overlap(js, rk) for rk in resume_keywords):
            matched_skills.append(js.strip())
        elif any(_skills_overlap(js, rh) for rh in resume_highlights):
            matched_skills.append(js.strip())
        else:
            missing_skills.append(js.strip())

    # ── 3. Match keywords ─────────────────────────────────────────────
    matched_keywords: list[str] = []
    resume_text_pool = " ".join(resume_keywords + resume_highlights).lower()

    for jk in job_keywords_raw:
        if not jk.strip():
            continue
        if jk.lower() in resume_text_pool or any(
            w.lower() in resume_text_pool for w in jk.split()
        ):
            matched_keywords.append(jk.strip())

    # ── 4. Score calculation ──────────────────────────────────────────
    n_job_skills = len(job_skills_raw) if job_skills_raw else 0
    n_job_keywords = len(job_keywords_raw) if job_keywords_raw else 0

    # Skills score
    if n_job_skills > 0:
        skills_score = (len(matched_skills) / n_job_skills) * 100
    else:
        skills_score = _FLOOR_NO_SKILLS  # no skills specified → neutral

    # Keywords score
    if n_job_keywords > 0:
        keywords_score = (len(matched_keywords) / n_job_keywords) * 100
    else:
        keywords_score = _FLOOR_NO_KEYWORDS

    # Direction score
    if not job_direction:
        direction_score = 75  # no direction constraint → slightly positive
    elif not resume_direction or resume_direction == "不限":
        direction_score = 80  # resume is generic → mildly positive
    elif job_direction == resume_direction:
        direction_score = 100  # exact match
    else:
        # Partial credit for related directions
        direction_score = 30  # mismatch

    # Highlights score: reward having substantial project write-ups
    if resume_highlights:
        # Each highlight contributes up to 25 points, cap at 100
        highlights_score = min(100, len(resume_highlights) * 25)
    else:
        highlights_score = _FLOOR_NO_HIGHLIGHTS

    # Weighted total
    raw_score = (
        skills_score * _W_SKILLS
        + keywords_score * _W_KEYWORDS
        + direction_score * _W_DIRECTION
        + highlights_score * _W_HIGHLIGHTS
    )

    # Risk deduction
    risk_deduction = len(job_risk_notes) * _RISK_DEDUCTION
    raw_score = max(0, raw_score - risk_deduction)

    match_score = round(min(100, raw_score), 1)

    # ── 5. Build explanations ─────────────────────────────────────────
    matched_points: list[str] = []
    missing_points: list[str] = []

    # Matched
    if matched_skills:
        matched_points.append(
            f"技能匹配 ({len(matched_skills)}/{n_job_skills})：{', '.join(matched_skills)}"
        )
    if matched_keywords:
        matched_points.append(
            f"标签匹配 ({len(matched_keywords)}/{n_job_keywords})：{', '.join(matched_keywords)}"
        )
    if job_direction and resume_direction and job_direction == resume_direction:
        matched_points.append(f"岗位方向「{job_direction}」与简历方向一致")
    elif not resume_direction or resume_direction == "不限":
        matched_points.append("简历方向不限，适配面广")
    if resume_highlights:
        matched_points.append(
            f"简历包含 {len(resume_highlights)} 个项目亮点，有助于展示项目经验"
        )

    # Missing
    if missing_skills:
        missing_points.append(
            f"技能缺失 ({len(missing_skills)}/{n_job_skills})：{', '.join(missing_skills)}"
        )

    # Direction mismatch
    if job_direction and resume_direction and resume_direction != "不限" and job_direction != resume_direction:
        missing_points.append(
            f"岗位方向「{job_direction}」与简历方向「{resume_direction}」不匹配"
        )

    # ── 6. Risk notes (pass-through from JD) ──────────────────────────
    risk_notes: list[str] = list(job_risk_notes)

    # ── 7. Optimisation suggestions ───────────────────────────────────
    optimization_suggestions: list[str] = []

    if missing_skills:
        optimization_suggestions.append(
            f"在简历中补充或强化以下技能关键词：{', '.join(missing_skills[:5])}"
        )
    if not resume_keywords:
        optimization_suggestions.append(
            "简历尚未设置核心关键词，建议添加以提高匹配度和筛选通过率"
        )
    if len(resume_highlights) < 2:
        optimization_suggestions.append(
            "建议补充 2-3 个与目标岗位相关的项目亮点，展示实践能力"
        )
    if job_direction and resume_direction and job_direction != resume_direction and resume_direction != "不限":
        optimization_suggestions.append(
            f"建议准备一份面向「{job_direction}」方向的简历版本，突出相关技能和项目"
        )

    # If everything is good
    if not optimization_suggestions and match_score >= 80:
        optimization_suggestions.append(
            "当前简历与该岗位匹配度较高，建议尽快投递。可以关注面试准备中的常见问题。"
        )

    # ── 8. Recommended action ─────────────────────────────────────────
    if match_score >= _THRESHOLD_STRONG:
        recommended_action = f"强烈建议投递（匹配度 {match_score:.0f}%）"
    elif match_score >= _THRESHOLD_OK:
        recommended_action = f"可以尝试投递（匹配度 {match_score:.0f}%），建议先补齐缺失技能"
    else:
        recommended_action = f"建议优化简历后再投递（匹配度 {match_score:.0f}%），优先补齐核心技能"

    # ── 9. Assemble result ────────────────────────────────────────────
    return MatchResult(
        id=generate_id("match"),
        job_id=job.id,
        resume_id=resume.id,
        match_score=match_score,
        matched_points=matched_points,
        missing_points=missing_points,
        risk_notes=risk_notes,
        optimization_suggestions=optimization_suggestions,
        recommended_action=recommended_action,
        gaps=missing_points,                # backward compat
        suggestions=optimization_suggestions,  # backward compat
    )


# ── LLM-based match analysis ────────────────────────────────────────────

def calculate_match_with_llm(job: Job, resume: ResumeVersion) -> MatchResult:
    """Analyse job-resume match via LLM, with rule-based fallback.

    Uses ``call_llm_json()`` for robust JSON extraction — it handles
    markdown code fences, stray text, and other common LLM output quirks.

    On any failure (LLM error, invalid JSON, missing critical fields)
    automatically falls back to ``calculate_match_rule_based()`` and sets
    the ``_fallback`` flag on the result so the UI can warn the user.

    Args:
        job: A Job (with jd_parsed_fields and jd_raw_text populated).
        resume: A ResumeVersion (with keywords / highlights populated).

    Returns:
        A MatchResult.  Check ``_fallback`` to see whether rule-based
        fallback was used; ``_raw_output`` contains the raw LLM response.
    """
    from services.llm_client import call_llm_json

    # ── Gather inputs ────────────────────────────────────────────────
    job_skills = job.jd_parsed_fields.get("skills", []) or []
    job_keywords = job.jd_parsed_fields.get("keywords", []) or []
    job_direction = job.direction or ""
    job_location = job.location or ""
    job_priority = job.priority or "中"
    jd_text = (job.jd_raw_text or "")[:2500]  # truncate very long JDs

    resume_keywords = resume.keywords or []
    resume_highlights = resume.highlights or []
    resume_direction = resume.target_direction or ""

    # ── Build the prompts ────────────────────────────────────────────
    system_prompt = (
        "你是一个专业的求职顾问，帮助求职者评估岗位与简历的匹配度。\n\n"
        "重要规则：\n"
        "1. 只基于简历中已有的关键词和项目亮点给出建议，绝对不要编造或假设求职者拥有简历中没有的经历\n"
        "2. 如果简历信息不全（关键词为空、没有项目亮点），如实指出并建议补充，但不要猜测具体内容\n"
        "3. 优化建议应该是可操作的、具体的，例如「在简历中补充 XX 技能关键词」而不是「学习 XX 技能」\n"
        "4. 匹配度评分要客观：技能重合度高、方向一致→高分；方向不匹配或核心技能缺失→低分\n"
        "5. 只输出 JSON 对象，不要输出任何解释文字、Markdown 标记或代码块"
    )

    # Build highlights text
    if resume_highlights:
        highlights_str = "\n".join(f"- {h}" for h in resume_highlights)
    else:
        highlights_str = "（未填写）"

    user_prompt = (
        "请分析以下岗位与简历的匹配度，输出 JSON。\n\n"
        "输出 JSON 格式（严格遵循，所有字段必须存在）：\n"
        "{\n"
        '  "match_score": 75,\n'
        '  "matched_points": ["匹配点1", "匹配点2"],\n'
        '  "missing_points": ["缺失点1", "缺失点2"],\n'
        '  "risk_notes": ["风险提示1"],\n'
        '  "optimization_suggestions": ["优化建议1", "优化建议2"],\n'
        '  "recommended_action": "强烈建议投递（匹配度 75%）"\n'
        "}\n\n"
        "字段说明：\n"
        "- match_score: 0-100 的整数，综合评估匹配程度\n"
        "- matched_points: 匹配的点（技能重合、方向一致、项目经验相关等）\n"
        "- missing_points: 缺失的点（简历中没有覆盖的技能、关键词等）\n"
        "- risk_notes: 岗位风险提示（JD 中提及的 996、外包、薪资面议等）\n"
        "- optimization_suggestions: 针对当前简历的具体优化建议，必须基于简历已有内容\n"
        "- recommended_action: 最终建议（强烈建议投递 / 可以尝试投递 / 建议优化简历后再投递）\n\n"
        "=== 岗位信息 ===\n"
        f"公司：{job.company}\n"
        f"岗位：{job.title}\n"
        f"方向：{job_direction or '（未设置）'}\n"
        f"地点：{job_location or '（未设置）'}\n"
        f"优先级：{job_priority}\n"
        f"要求技能：{', '.join(job_skills) if job_skills else '（未提取）'}\n"
        f"岗位标签：{', '.join(job_keywords) if job_keywords else '（未提取）'}\n"
        f"JD 内容：\n{jd_text}\n\n"
        "=== 简历信息 ===\n"
        f"简历版本：{resume.version_name}\n"
        f"目标方向：{resume_direction or '不限'}\n"
        f"核心关键词：{', '.join(resume_keywords) if resume_keywords else '（未设置）'}\n"
        f"项目亮点：\n{highlights_str}\n\n"
        "请直接输出 JSON 对象。不要包含 ```json 标记或任何其他文字。"
    )

    # ── Build fallback result once (reused on any failure path) ───────
    fallback = calculate_match_rule_based(job, resume)
    fallback._fallback = True
    fallback._raw_output = ""

    # ── Call LLM ──────────────────────────────────────────────────────
    try:
        result = call_llm_json(user_prompt, system_prompt=system_prompt)
    except Exception as exc:
        fallback._fallback_reason = f"AI 调用异常（{exc}），已回退到规则匹配"
        return fallback

    if not result.get("success"):
        err = result.get("error", "未知错误")
        raw = result.get("raw_output", "")
        # Distinguish API errors (❌ prefix) from JSON parse failures
        if err.startswith("❌"):
            fallback._fallback_reason = (
                f"AI 匹配接口调用失败，已回退到规则匹配：\n\n{err}"
            )
        else:
            raw_preview = (raw[:500] + "...") if len(raw) > 500 else raw
            fallback._fallback_reason = (
                f"AI 返回 JSON 解析失败：{err}\n\n"
                f"AI 原始输出（前500字符）：\n{raw_preview}"
            )
        fallback._raw_output = raw
        return fallback

    # ── Normalize & validate ──────────────────────────────────────────
    data = result.get("data", {})
    raw_output = result.get("raw_output", "")

    try:
        match_result = _normalize_llm_match_result(data, job, resume)
        match_result._fallback = False
        match_result._raw_output = raw_output
        return match_result
    except (ValueError, TypeError) as exc:
        fallback._fallback_reason = (
            f"AI 返回数据格式异常（{exc}），已回退到规则匹配"
        )
        return fallback


def _normalize_llm_match_result(raw: dict, job: Job, resume: ResumeVersion) -> MatchResult:
    """Normalize and validate LLM JSON into a MatchResult.

    Ensures all fields are present with sensible defaults.  If the LLM
    return is too broken, we raise ValueError so the caller can fall back.
    """
    # ── Match score: must be an integer 0-100 ─────────────────────────
    match_score = raw.get("match_score", 0)
    try:
        match_score = int(match_score)
    except (ValueError, TypeError):
        match_score = int(float(match_score))
    match_score = max(0, min(100, match_score))

    def _list_of_str(key: str) -> list[str]:
        val = raw.get(key, [])
        if not isinstance(val, list):
            return []
        return [str(v).strip() for v in val if str(v).strip()]

    matched_points = _list_of_str("matched_points")
    missing_points = _list_of_str("missing_points")
    risk_notes = _list_of_str("risk_notes")
    optimization_suggestions = _list_of_str("optimization_suggestions")
    recommended_action = str(raw.get("recommended_action", "")).strip()

    # Fallback recommended_action if empty
    if not recommended_action:
        if match_score >= 75:
            recommended_action = f"强烈建议投递（匹配度 {match_score:.0f}%）"
        elif match_score >= 50:
            recommended_action = f"可以尝试投递（匹配度 {match_score:.0f}%），建议先补齐缺失技能"
        else:
            recommended_action = f"建议优化简历后再投递（匹配度 {match_score:.0f}%），优先补齐核心技能"

    return MatchResult(
        id=generate_id("match"),
        job_id=job.id,
        resume_id=resume.id,
        match_score=float(match_score),
        matched_points=matched_points,
        missing_points=missing_points,
        risk_notes=risk_notes,
        optimization_suggestions=optimization_suggestions,
        recommended_action=recommended_action,
        gaps=missing_points,
        suggestions=optimization_suggestions,
    )


# ── Legacy wrapper (keeps existing callers working) ──────────────────────

def match_job_to_resume(job_fields: dict, resume_fields: dict) -> dict:
    """Legacy wrapper. Returns a plain dict for callers using the old API.

    Prefer ``calculate_match_rule_based(job, resume)`` for new code.
    """
    return {
        "match_score": 0,
        "matched_points": [],
        "gaps": [],
        "suggestions": [],
    }
