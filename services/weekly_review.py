"""Rule-based + LLM weekly review report generator.

Computes stats from applications, jobs, and resumes, then generates
strategy analysis and next-week suggestions.
"""

from collections import Counter
from datetime import datetime, timedelta

from core.models import WeeklyReview


# ── Public API ───────────────────────────────────────────────────────────

def generate_weekly_review(applications: list, jobs: list, resumes: list) -> WeeklyReview:
    """Generate a rule-based weekly job-hunting review.

    Args:
        applications: List of ``Application`` instances.
        jobs: List of ``Job`` instances.
        resumes: List of ``ResumeVersion`` instances.

    Returns:
        A ``WeeklyReview`` with computed stats, highlights, and next-week focus.
    """
    now = datetime.now()

    # ── Week label & date range ─────────────────────────────────────────
    iso = now.isocalendar()
    week_label = f"{now.year}年第{iso.week}周"
    today = now.date()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    date_range = f"{monday.strftime('%Y.%m.%d')} - {sunday.strftime('%Y.%m.%d')}"

    # Build lookup dicts
    jobs_dict = {j.id: j for j in jobs}
    resumes_dict = {r.id: r for r in resumes}

    # ── Stats ───────────────────────────────────────────────────────────
    total = len(applications)

    # This week's new applications (by created_at)
    week_start = datetime.combine(monday, datetime.min.time())
    week_end_dt = datetime.combine(sunday, datetime.max.time())
    new_this_week = sum(
        1 for a in applications
        if a.created_at and week_start <= a.created_at <= week_end_dt
    )

    # Status breakdown
    status_counts = Counter(a.status for a in applications)
    interviewing = sum(status_counts.get(s, 0) for s in ("一面", "二面", "HR面", "笔试/测评", "简历评估"))
    offers = status_counts.get("offer", 0)
    rejected = status_counts.get("终止", 0)
    abandoned = status_counts.get("放弃", 0)
    no_feedback = status_counts.get("已投递", 0) + status_counts.get("简历评估", 0)
    applied = status_counts.get("已投递", 0)

    # Direction distribution
    direction_counter: Counter = Counter()
    for a in applications:
        job = jobs_dict.get(a.job_id)
        if job and job.direction:
            direction_counter[job.direction] += 1
    direction_labels = [d for d, _ in direction_counter.most_common()]

    # Resume version usage
    resume_counter: Counter = Counter()
    for a in applications:
        resume = resumes_dict.get(a.resume_id)
        if resume:
            resume_counter[resume.version_name] += 1

    # ── Direction feedback analysis ─────────────────────────────────────
    # Per direction: count offers, interviewing, rejected
    direction_feedback: dict[str, dict] = {}
    for d in direction_labels:
        direction_feedback[d] = {"total": 0, "offers": 0, "interviewing": 0, "rejected": 0}
    for a in applications:
        job = jobs_dict.get(a.job_id)
        if not job or not job.direction:
            continue
        d = job.direction
        if d not in direction_feedback:
            continue
        direction_feedback[d]["total"] += 1
        if a.status == "offer":
            direction_feedback[d]["offers"] += 1
        elif a.status in ("一面", "二面", "HR面", "笔试/测评", "简历评估"):
            direction_feedback[d]["interviewing"] += 1
        elif a.status == "终止":
            direction_feedback[d]["rejected"] += 1

    # ── Resume performance ──────────────────────────────────────────────
    resume_performance: dict[str, dict] = {}
    for name in resume_counter:
        resume_performance[name] = {"total": 0, "offers": 0, "interviewing": 0, "rejected": 0}
    for a in applications:
        resume = resumes_dict.get(a.resume_id)
        if not resume:
            continue
        name = resume.version_name
        if name not in resume_performance:
            continue
        resume_performance[name]["total"] += 1
        if a.status == "offer":
            resume_performance[name]["offers"] += 1
        elif a.status in ("一面", "二面", "HR面", "笔试/测评", "简历评估"):
            resume_performance[name]["interviewing"] += 1
        elif a.status == "终止":
            resume_performance[name]["rejected"] += 1

    # ── Build highlights ────────────────────────────────────────────────
    highlights = _build_highlights(
        total, new_this_week, interviewing, offers, rejected,
        direction_feedback, resume_counter, no_feedback, applied,
    )

    # ── Build next-week focus ───────────────────────────────────────────
    next_week_focus = _build_next_week_focus(
        applications, jobs_dict, resumes_dict,
        direction_feedback, resume_performance,
        interviewing, offers, no_feedback, applied,
    )

    return WeeklyReview(
        id=f"review-{now.strftime('%Y%m%d%H%M%S')}",
        week_label=week_label,
        date_range=date_range,
        stats={
            "total_applications": total,
            "new_this_week": new_this_week,
            "applied": applied,
            "interviewing": interviewing,
            "offers": offers,
            "rejected": rejected,
            "abandoned": abandoned,
            "no_feedback": no_feedback,
            "directions": dict(direction_counter),
            "resume_usage": dict(resume_counter),
        },
        highlights=highlights,
        next_week_focus=next_week_focus,
    )


# ── Internal helpers ──────────────────────────────────────────────────────

def _build_highlights(
    total: int,
    new_this_week: int,
    interviewing: int,
    offers: int,
    rejected: int,
    direction_feedback: dict,
    resume_counter: Counter,
    no_feedback: int,
    applied: int,
) -> list[str]:
    """Generate highlight bullets from stats."""
    highlights: list[str] = []

    # Overall progress
    highlights.append(f"当前共有 {total} 条投递记录，其中 {interviewing} 个岗位正在面试流程中")

    # This week activity
    if new_this_week > 0:
        highlights.append(f"本周新增 {new_this_week} 条投递记录，保持了活跃的投递节奏")
    else:
        highlights.append("本周暂无新增投递，建议加快投递节奏")

    # Offers
    if offers > 0:
        highlights.append(f"已获得 {offers} 个 Offer，建议综合评估后尽快决策")

    # Direction with best feedback
    best_direction = _best_direction(direction_feedback)
    if best_direction:
        highlights.append(f"「{best_direction}」方向反馈最好，建议持续关注该方向的岗位机会")

    # No-feedback warning
    if no_feedback > total * 0.5 and total >= 4:
        highlights.append(f"⚠️ {no_feedback} 条投递尚未收到反馈，建议主动跟进或检查简历匹配度")

    # Rejected lessons
    if rejected > 0:
        highlights.append(f"{rejected} 条投递被拒，建议复盘面试/简历问题，针对性地补充短板")

    # Resume usage insight
    if resume_counter:
        top_resume = resume_counter.most_common(1)[0][0]
        highlights.append(f"使用最多的简历版本是「{top_resume}」，可考虑根据岗位方向调整简历侧重")

    return highlights


def _build_next_week_focus(
    applications: list,
    jobs_dict: dict,
    resumes_dict: dict,
    direction_feedback: dict,
    resume_performance: dict,
    interviewing: int,
    offers: int,
    no_feedback: int,
    applied: int,
) -> list[str]:
    """Generate actionable next-week suggestions."""
    items: list[str] = []

    # 1. Interview preparation
    interview_apps = [a for a in applications if a.status in ("一面", "二面", "HR面", "笔试/测评", "简历评估")]
    if interview_apps:
        next_interview = None
        for a in applications:
            job = jobs_dict.get(a.job_id)
            if job and a.status in ("一面", "二面", "HR面", "笔试/测评", "简历评估"):
                next_interview = (a, job)
                break
        count = len(interview_apps)
        items.append(f"准备 {count} 个正在进行中的面试（重点复习技术基础、项目经验和系统设计）")
    else:
        items.append("本周暂无面试安排，利用空档期补充目标方向的技术知识点")

    # 2. Follow up on no-feedback
    if no_feedback >= 3:
        items.append(f"跟进 {no_feedback} 条无反馈投递：超过 5 个工作日的可礼貌邮件/平台追问进度")
    elif applied > 0:
        items.append("关注已投递岗位的反馈动态，准备好可能的笔试/面试通知")

    # 3. Offer decision
    if offers >= 2:
        items.append(f"对比 {offers} 个 Offer 条件（薪资/团队/发展/地点），做出最优选择")
    elif offers == 1:
        items.append("评估 Offer 条件，注意回复截止日期，避免过期作废")

    # 4. Direction strategy
    best_d = _best_direction(direction_feedback)
    if best_d:
        items.append(f"继续投递「{best_d}」方向的岗位 — 该方向反馈最好，建议加大投递力度")
    # Underperforming direction
    worst_d = _worst_direction(direction_feedback)
    if worst_d and worst_d != best_d:
        items.append(f"审视「{worst_d}」方向的投递策略：检查简历匹配度或考虑调整目标公司档次")

    # 5. Resume optimization
    best_resume = _best_resume(resume_performance)
    if best_resume:
        items.append(f"优先使用「{best_resume}」简历版本，该版本面试转化率较高")
    # Underperforming resume
    worst_resume = _worst_resume(resume_performance)
    if worst_resume:
        items.append(f"优化「{worst_resume}」简历版本，补充关键词和项目亮点以提高通过率")

    # 6. Broaden channels
    items.append("拓展投递渠道：除了官网和内推，关注校园宣讲会、技术社区招聘帖、LinkedIn")

    # 7. Learning & preparation
    items.append("利用碎片时间刷算法题（LeetCode Hot 100），准备常见行为面试问题")

    return items


# ── Direction / resume analysis helpers ────────────────────────────────────

def _best_direction(direction_feedback: dict) -> str | None:
    """Return the direction with the highest positive-outcome rate."""
    best = None
    best_score = -1
    for d, fb in direction_feedback.items():
        total = fb["total"]
        if total == 0:
            continue
        # Weight: offers * 3 + interviewing * 1 - rejected * 1
        score = (fb["offers"] * 3 + fb["interviewing"] * 1 - fb["rejected"] * 1) / total
        if score > best_score:
            best_score = score
            best = d
    return best


def _worst_direction(direction_feedback: dict) -> str | None:
    """Return the direction with the lowest positive-outcome rate (min 2 applications)."""
    worst = None
    worst_score = float("inf")
    for d, fb in direction_feedback.items():
        total = fb["total"]
        if total < 2:
            continue
        score = (fb["offers"] * 3 + fb["interviewing"] * 1 - fb["rejected"] * 1) / total
        if score < worst_score:
            worst_score = score
            worst = d
    return worst


def _best_resume(resume_performance: dict) -> str | None:
    """Return the resume version with the highest interview/offer conversion rate."""
    best = None
    best_score = -1
    for name, perf in resume_performance.items():
        total = perf["total"]
        if total == 0:
            continue
        score = (perf["offers"] * 3 + perf["interviewing"] * 1 - perf["rejected"] * 1) / total
        if score > best_score:
            best_score = score
            best = name
    return best


def _worst_resume(resume_performance: dict) -> str | None:
    """Return the resume version with the lowest conversion rate (min 2 uses)."""
    worst = None
    worst_score = float("inf")
    for name, perf in resume_performance.items():
        total = perf["total"]
        if total < 2:
            continue
        score = (perf["offers"] * 3 + perf["interviewing"] * 1 - perf["rejected"] * 1) / total
        if score < worst_score:
            worst_score = score
            worst = name
    return worst


# ═══════════════════════════════════════════════════════════════════════════
# LLM-based weekly review
# ═══════════════════════════════════════════════════════════════════════════

def _compute_stats_dict(applications: list, jobs: list, resumes: list,
                        week_start: datetime, week_end_dt: datetime) -> dict:
    """Compute the statistical summary dict from raw data.

    This runs entirely in Python — no data is sent to the LLM at this stage.
    The returned dict is used both as the ``stats`` field of the WeeklyReview
    and as the input to build the text summary sent to the LLM.
    """
    jobs_dict = {j.id: j for j in jobs}
    resumes_dict = {r.id: r for r in resumes}

    total = len(applications)
    new_this_week = sum(
        1 for a in applications
        if a.created_at and week_start <= a.created_at <= week_end_dt
    )

    status_counts = Counter(a.status for a in applications)
    interviewing = sum(status_counts.get(s, 0) for s in ("一面", "二面", "HR面", "笔试/测评", "简历评估"))
    offers = status_counts.get("offer", 0)
    rejected = status_counts.get("终止", 0)
    abandoned = status_counts.get("放弃", 0)
    no_feedback = status_counts.get("已投递", 0) + status_counts.get("简历评估", 0)
    applied = status_counts.get("已投递", 0)

    # Direction distribution + per-direction feedback
    direction_counter: Counter = Counter()
    direction_feedback: dict[str, dict] = {}
    for a in applications:
        job = jobs_dict.get(a.job_id)
        if job and job.direction:
            d = job.direction
            direction_counter[d] += 1
            if d not in direction_feedback:
                direction_feedback[d] = {"total": 0, "offers": 0, "interviewing": 0, "rejected": 0}
            direction_feedback[d]["total"] += 1
            if a.status == "offer":
                direction_feedback[d]["offers"] += 1
            elif a.status in ("一面", "二面", "HR面", "笔试/测评", "简历评估"):
                direction_feedback[d]["interviewing"] += 1
            elif a.status == "终止":
                direction_feedback[d]["rejected"] += 1

    # Resume version usage
    resume_counter: Counter = Counter()
    for a in applications:
        resume = resumes_dict.get(a.resume_id)
        if resume:
            resume_counter[resume.version_name] += 1

    # Status pipeline
    status_order = ["已投递", "简历评估", "笔试/测评", "一面", "二面", "HR面", "offer", "终止", "放弃"]
    pipeline = {s: status_counts.get(s, 0) for s in status_order}

    return {
        "total_applications": total,
        "new_this_week": new_this_week,
        "applied": applied,
        "interviewing": interviewing,
        "offers": offers,
        "rejected": rejected,
        "abandoned": abandoned,
        "no_feedback": no_feedback,
        "directions": dict(direction_counter),
        "resume_usage": dict(resume_counter),
        "_direction_feedback": direction_feedback,
        "_pipeline": pipeline,
    }


def _build_statistical_summary(stats_dict: dict, applications: list, jobs_dict: dict) -> str:
    """Build a text version of the statistical summary for the LLM prompt.

    The text is structured in sections: overview, funnel, directions, resumes,
    and company list.  It only contains aggregated numbers — no individual
    personal data is sent.
    """
    status_order = ["已投递", "简历评估", "笔试/测评", "一面", "二面", "HR面", "offer", "终止", "放弃"]
    pipeline = stats_dict.get("_pipeline", {})
    direction_feedback = stats_dict.get("_direction_feedback", {})
    resume_usage = stats_dict.get("resume_usage", {})

    # Companies with status (names only, for context)
    company_statuses: list[str] = []
    for a in applications:
        job = jobs_dict.get(a.job_id)
        if job:
            company_statuses.append(f"{job.company}（{a.status}）")

    lines = [
        "## 本周求职统计摘要",
        "",
        "### 整体数据",
        f"- 投递总数：{stats_dict['total_applications']}",
        f"- 本周新增投递：{stats_dict['new_this_week']}",
        f"- 面试中：{stats_dict['interviewing']}",
        f"- 已获Offer：{stats_dict['offers']}",
        f"- 已被拒：{stats_dict['rejected']}",
        f"- 已放弃：{stats_dict['abandoned']}",
        f"- 无反馈（已投递+简历评估）：{stats_dict['no_feedback']}",
        "",
        "### 投递漏斗",
    ]
    for s in status_order:
        cnt = pipeline.get(s, 0)
        if cnt > 0:
            lines.append(f"- {s}：{cnt}")

    lines.append("")
    lines.append("### 岗位方向分布")
    if direction_feedback:
        for d, fb in direction_feedback.items():
            lines.append(
                f"- {d}：共{fb['total']}个（Offer {fb['offers']}, "
                f"面试中 {fb['interviewing']}, 被拒 {fb['rejected']}）"
            )
    else:
        lines.append("- 暂无方向数据")

    lines.append("")
    lines.append("### 简历版本使用次数")
    if resume_usage:
        for name, cnt in sorted(resume_usage.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"- {name}：{cnt}次")
    else:
        lines.append("- 暂无简历数据")

    lines.append("")
    lines.append("### 公司 & 状态一览")
    for cs in company_statuses[:20]:
        lines.append(f"- {cs}")
    if len(company_statuses) > 20:
        lines.append(f"- ...还有 {len(company_statuses) - 20} 条")

    return "\n".join(lines)


def generate_weekly_review_with_llm(applications: list, jobs: list, resumes: list) -> WeeklyReview:
    """Generate a weekly review via LLM, with rule-based fallback.

    **Architecture**: Raw data never reaches the LLM.  Instead we:
    1. Compute a statistical summary entirely in Python (``_compute_stats_dict``)
    2. Build a text version of the summary (``_build_statistical_summary``)
    3. Send only the text summary to the LLM for strategy analysis
    4. Merge the LLM's analysis with the real stats into a ``WeeklyReview``

    Uses ``call_llm_json()`` for robust JSON extraction.  On any failure
    (LLM error, invalid JSON, empty result) automatically falls back to
    ``generate_weekly_review()`` and sets ``_fallback`` on the result.

    Args:
        applications: List of ``Application`` instances.
        jobs: List of ``Job`` instances.
        resumes: List of ``ResumeVersion`` instances.

    Returns:
        A ``WeeklyReview`` with real stats plus LLM-generated highlights
        and next-week plan.  Check ``_fallback`` for fallback status.
    """
    from services.llm_client import call_llm_json

    # ── Week label & date range ─────────────────────────────────────────
    now = datetime.now()
    iso = now.isocalendar()
    week_label = f"{now.year}年第{iso.week}周"
    today = now.date()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    date_range = f"{monday.strftime('%Y.%m.%d')} - {sunday.strftime('%Y.%m.%d')}"

    week_start = datetime.combine(monday, datetime.min.time())
    week_end_dt = datetime.combine(sunday, datetime.max.time())

    jobs_dict = {j.id: j for j in jobs}

    # ── Step 1: Compute stats in Python (no data sent to LLM yet) ──────
    stats_dict = _compute_stats_dict(applications, jobs, resumes, week_start, week_end_dt)

    # ── Step 2: Build text summary for the LLM ─────────────────────────
    statistical_summary = _build_statistical_summary(stats_dict, applications, jobs_dict)

    # ── Step 3: Build fallback result (reused on any failure path) ─────
    fallback = generate_weekly_review(applications, jobs, resumes)
    fallback._fallback = True
    fallback._raw_output = ""

    # ── Step 4: Call LLM with the summary ──────────────────────────────
    system_prompt = (
        "你是一个求职策略顾问，专门帮助中国应届生分析求职进展并给出策略建议。\n\n"
        "重要规则：\n"
        "1. 你只能基于提供的统计摘要进行分析，绝对不要编造或假设数据中没有的信息\n"
        "2. 每条 key_insight 和 problem 都必须能从统计摘要中找到数字依据\n"
        "3. next_week_plan 中的建议必须具体、可执行，而非泛泛而谈，每条建议要有明确的目标和行动\n"
        "4. 用中文输出，语气专业但平易近人\n"
        "5. summary 应包含关键数字（投递总数、面试中数量、Offer 数量）\n"
        "6. 只输出 JSON 对象，不要输出任何解释文字、Markdown 标记或代码块"
    )

    user_prompt = (
        "请基于以下求职统计摘要，生成策略分析 JSON。\n\n"
        "输出 JSON 格式（严格遵循，所有字段必须存在）：\n"
        "{\n"
        '  "summary": "本周求职总体情况的简要概述（2-3句话，必须包含关键数字）",\n'
        '  "key_insights": ["洞察1", "洞察2", "洞察3"],\n'
        '  "problems": ["问题1", "问题2"],\n'
        '  "next_week_plan": ["行动1", "行动2", "行动3", "行动4", "行动5"]\n'
        "}\n\n"
        "字段说明：\n"
        "- summary: 本周整体概述，包含投递总数、面试中数量、Offer 数量等关键数字\n"
        "- key_insights: 基于数据的关键洞察（如某方向转化率高、某简历版本效果好）\n"
        "- problems: 需要关注的问题（如无反馈比例高、某方向被拒率高）\n"
        "- next_week_plan: 5 条具体的下周行动建议，每条可执行\n\n"
        + statistical_summary
        + "\n\n请直接输出 JSON 对象。不要包含 ```json 标记或任何其他文字。"
    )

    # ── Step 5: Call LLM ───────────────────────────────────────────────
    try:
        result = call_llm_json(user_prompt, system_prompt=system_prompt)
    except Exception as exc:
        fallback._fallback_reason = f"AI 调用异常（{exc}），已回退到规则周报"
        return fallback

    if not result.get("success"):
        err = result.get("error", "未知错误")
        if err.startswith("❌"):
            fallback._fallback_reason = f"AI 周报接口调用失败，已回退到规则周报：\n\n{err}"
        else:
            fallback._fallback_reason = f"AI 返回 JSON 解析失败：{err}"
        return fallback

    # ── Step 6: Normalize & validate ───────────────────────────────────
    data = result.get("data", {})
    raw_output = result.get("raw_output", "")

    try:
        ai_summary = str(data.get("summary", "")).strip()
        key_insights = _list_of_str(data.get("key_insights", []))
        problems = _list_of_str(data.get("problems", []))
        next_week_plan = _list_of_str(data.get("next_week_plan", []))
    except Exception as exc:
        fallback._fallback_reason = f"AI 返回数据格式异常（{exc}），已回退到规则周报"
        return fallback

    # Validate: at minimum need summary or some next_week_plan
    if not ai_summary and not next_week_plan:
        fallback._fallback_reason = (
            "AI 返回的关键字段为空（summary 和 next_week_plan 均为空），已回退到规则周报"
        )
        return fallback

    # ── Step 7: Merge AI analysis with real stats ──────────────────────
    # Store AI summary in stats for page display
    stats_dict["ai_summary"] = ai_summary

    # Build highlights: summary first, then insights, then problems (⚠️ prefixed)
    highlights: list[str] = []
    if ai_summary:
        highlights.append(f"📋 {ai_summary}")
    for ins in key_insights:
        highlights.append(ins)
    for prob in problems:
        highlights.append(f"⚠️ {prob}")

    # If next_week_plan is empty, fall back
    if not highlights and not next_week_plan:
        fallback._fallback_reason = (
            "AI 生成的亮点和建议均为空，已回退到规则周报"
        )
        return fallback

    review = WeeklyReview(
        id=f"review-{now.strftime('%Y%m%d%H%M%S')}",
        week_label=week_label,
        date_range=date_range,
        stats=stats_dict,
        highlights=highlights,
        next_week_focus=next_week_plan,
        _fallback=False,
        _raw_output=raw_output,
    )
    return review


def _list_of_str(val) -> list[str]:
    """Coerce a value to a list of non-empty strings."""
    if not isinstance(val, list):
        return []
    return [str(v).strip() for v in val if str(v).strip()]

