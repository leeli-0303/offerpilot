"""Export utilities for OfferPilot.

Writes markdown reports to data/exports/ and provides download-ready content.
"""

import os
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = PROJECT_ROOT / "data" / "exports"


def ensure_export_dir() -> Path:
    """Create and return the export directory path."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    return EXPORT_DIR


def export_to_markdown(content: str, filename: str) -> str:
    """Save markdown content to data/exports/ and return the absolute file path.

    Args:
        content: The markdown string to write.
        filename: The file name (e.g. ``weekly-review-20260518.md``).

    Returns:
        The absolute path to the saved file.
    """
    ensure_export_dir()
    filepath = EXPORT_DIR / filename
    filepath.write_text(content, encoding="utf-8")
    return str(filepath.resolve())


def _timestamp() -> str:
    """Return a compact timestamp string for filenames."""
    return datetime.now().strftime("%Y%m%d-%H%M%S")


# ═══════════════════════════════════════════════════════════════════════════
# Weekly Review → Markdown
# ═══════════════════════════════════════════════════════════════════════════

def build_weekly_review_markdown(review, mode_label: str = "") -> str:
    """Build a markdown report from a WeeklyReview instance."""
    stats = review.stats
    lines = [
        f"# 求职周报",
        f"",
        f"**{review.week_label}** · {review.date_range}",
    ]
    if mode_label:
        lines.append(f"")
        lines.append(f"> 生成模式：{mode_label}")
    lines.append(f"")
    lines.append(f"> 导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"")

    # ── Core stats ────────────────────────────────────────────────────
    lines.append(f"## 核心统计")
    lines.append(f"")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 投递总数 | {stats.get('total_applications', 0)} |")
    lines.append(f"| 本周新增 | {stats.get('new_this_week', 0)} |")
    lines.append(f"| 面试中 | {stats.get('interviewing', 0)} |")
    lines.append(f"| Offer | {stats.get('offers', 0)} |")
    lines.append(f"| 已拒绝 | {stats.get('rejected', 0)} |")
    lines.append(f"| 无反馈 | {stats.get('no_feedback', 0)} |")
    lines.append(f"")

    # ── Direction distribution ────────────────────────────────────────
    directions = stats.get("directions", {})
    if directions:
        lines.append(f"## 岗位方向分布")
        lines.append(f"")
        lines.append(f"| 方向 | 投递数 |")
        lines.append(f"|------|--------|")
        for d, cnt in directions.items():
            lines.append(f"| {d} | {cnt} |")
        lines.append(f"")

    # ── Resume usage ──────────────────────────────────────────────────
    resume_usage = stats.get("resume_usage", {})
    if resume_usage:
        lines.append(f"## 简历版本使用")
        lines.append(f"")
        lines.append(f"| 版本 | 使用次数 |")
        lines.append(f"|------|----------|")
        for name, cnt in resume_usage.items():
            lines.append(f"| {name} | {cnt} |")
        lines.append(f"")

    # ── AI summary ────────────────────────────────────────────────────
    ai_summary = stats.get("ai_summary", "")
    if ai_summary:
        lines.append(f"## AI 策略分析")
        lines.append(f"")
        lines.append(f"{ai_summary}")
        lines.append(f"")

    # ── Highlights / Problems ─────────────────────────────────────────
    highlights = review.highlights or []
    insight_items = [h for h in highlights if not h.startswith("⚠️")]
    problem_items = [h.replace("⚠️ ", "") for h in highlights if h.startswith("⚠️")]

    if insight_items:
        lines.append(f"## 本周总结 & 亮点")
        lines.append(f"")
        for h in insight_items:
            lines.append(f"- {h}")
        lines.append(f"")

    if problem_items:
        lines.append(f"## 发现的问题")
        lines.append(f"")
        for p in problem_items:
            lines.append(f"- ⚠️ {p}")
        lines.append(f"")

    # ── Next-week focus ───────────────────────────────────────────────
    focus_items = review.next_week_focus or []
    if focus_items:
        lines.append(f"## 下周关注 & 行动建议")
        lines.append(f"")
        for i, item in enumerate(focus_items, 1):
            lines.append(f"{i}. {item}")
        lines.append(f"")

    lines.append(f"---")
    lines.append(f"*此报告由 OfferPilot 自动生成*")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Match Analysis → Markdown
# ═══════════════════════════════════════════════════════════════════════════

def build_match_analysis_markdown(job, resume, result, mode_label: str = "") -> str:
    """Build a markdown report from a match analysis result."""
    lines = [
        f"# 岗位-简历匹配分析",
        f"",
        f"**{job.company} — {job.title}**",
        f"",
        f"简历版本：{resume.version_name}",
    ]
    if mode_label:
        lines.append(f"")
        lines.append(f"> 匹配模式：{mode_label}")
    lines.append(f"")
    lines.append(f"> 导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"")

    # ── Score ─────────────────────────────────────────────────────────
    lines.append(f"## 匹配度：{result.match_score:.0f}/100")
    lines.append(f"")

    lines.append(f"**建议行动：** {result.recommended_action}")
    lines.append(f"")

    # ── Job info ──────────────────────────────────────────────────────
    lines.append(f"## 岗位信息")
    lines.append(f"")
    if job.company:
        lines.append(f"- 公司：{job.company}")
    if job.title:
        lines.append(f"- 岗位：{job.title}")
    if job.direction:
        lines.append(f"- 方向：{job.direction}")
    if job.location:
        lines.append(f"- 地点：{job.location}")
    skills = job.jd_parsed_fields.get("skills", []) or []
    if skills:
        lines.append(f"- 要求技能：{', '.join(skills)}")
    keywords = job.jd_parsed_fields.get("keywords", []) or []
    if keywords:
        lines.append(f"- 岗位标签：{', '.join(keywords)}")
    lines.append(f"")

    # ── Resume info ───────────────────────────────────────────────────
    lines.append(f"## 简历信息")
    lines.append(f"")
    lines.append(f"- 版本名称：{resume.version_name}")
    if resume.target_direction:
        lines.append(f"- 目标方向：{resume.target_direction}")
    if resume.keywords:
        lines.append(f"- 关键词：{', '.join(resume.keywords)}")
    if resume.highlights:
        lines.append(f"- 项目亮点：{', '.join(resume.highlights[:3])}")
    lines.append(f"")

    # ── Matched points ────────────────────────────────────────────────
    matched = result.matched_points or []
    if matched:
        lines.append(f"## 匹配点（{len(matched)}）")
        lines.append(f"")
        for point in matched:
            lines.append(f"- ✅ {point}")
        lines.append(f"")

    # ── Missing points ────────────────────────────────────────────────
    missing = result.missing_points or []
    if missing:
        lines.append(f"## 缺失项（{len(missing)}）")
        lines.append(f"")
        for point in missing:
            lines.append(f"- 🔻 {point}")
        lines.append(f"")

    # ── Risk notes ────────────────────────────────────────────────────
    risks = result.risk_notes or []
    if risks:
        lines.append(f"## 风险提示（{len(risks)}）")
        lines.append(f"")
        for note in risks:
            lines.append(f"- ⚠️ {note}")
        lines.append(f"")

    # ── Optimization suggestions ──────────────────────────────────────
    suggestions = result.optimization_suggestions or []
    if suggestions:
        lines.append(f"## 优化建议（{len(suggestions)}）")
        lines.append(f"")
        for s in suggestions:
            lines.append(f"- 💡 {s}")
        lines.append(f"")

    lines.append(f"---")
    lines.append(f"*此报告由 OfferPilot 自动生成*")

    return "\n".join(lines)
