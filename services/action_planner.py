"""Rule-based next-action suggestion service.

Generates short, actionable next-step suggestions for each application
based on its current status, elapsed time, and job-resume match score.
No LLM calls.
"""

from datetime import datetime


# ── Urgency helpers ──────────────────────────────────────────────────────

def _days_since(date_value) -> int:
    """Return days elapsed since *date_value* (datetime or None)."""
    if date_value is None:
        return 0
    return (datetime.now() - date_value).days


def _urgency(level: str) -> str:
    """Normalize urgency to 高 / 中 / 低."""
    return level if level in ("高", "中", "低") else "中"


# ── Public API ───────────────────────────────────────────────────────────

def generate_next_action(application, job, resume=None) -> dict:
    """Suggest the next concrete action for an application.

    Args:
        application: An ``Application`` instance.
        job: The ``Job`` linked to this application.
        resume: Optional ``ResumeVersion`` for match-score-aware suggestions.

    Returns:
        A dict with keys:
          - **next_action** (str): short, actionable suggestion
          - **reason** (str): why this action is recommended
          - **urgency** (str): "高", "中", or "低"
    """
    status = (application.status or "").strip()
    days = _days_since(application.applied_date)

    # ── 已投递 ──────────────────────────────────────────────────────
    if status == "已投递":
        return _handle_applied(days)

    # ── 简历评估 ────────────────────────────────────────────────────
    if status == "简历评估":
        return {
            "next_action": "关注简历评估反馈",
            "reason": "简历已进入评估阶段，关注邮件/短信通知，同时准备笔试和面试内容",
            "urgency": _urgency("中"),
        }

    # ── 笔试/测评 ─────────────────────────────────────────────────
    if status == "笔试/测评":
        return {
            "next_action": "完成笔试 / 测评",
            "reason": "注意截止时间，提前复习相关知识点和常见题型",
            "urgency": _urgency("高"),
        }

    # ── 一面 / 二面 ─────────────────────────────────────────────────
    if status in ("一面", "二面"):
        if status == "一面":
            focus = "技术基础、项目经验和算法题"
        else:
            focus = "系统设计、项目深挖和行为面试"
        return {
            "next_action": f"准备{status}内容",
            "reason": f"重点准备{focus}；建议结合 JD 要求查漏补缺",
            "urgency": _urgency("高"),
        }

    # ── HR面 ───────────────────────────────────────────────────────
    if status == "HR面":
        return {
            "next_action": "准备 HR 面试和薪资谈判",
            "reason": "了解市场薪资范围，准备好期望薪资、入职时间和职业规划",
            "urgency": _urgency("中"),
        }

    # ── offer ───────────────────────────────────────────────────────
    if status == "offer":
        return {
            "next_action": "评估并决策 Offer",
            "reason": "综合评估薪资、团队、发展空间、工作地点；如有多个 Offer 可横向对比",
            "urgency": _urgency("中"),
        }

    # ── 终止 ────────────────────────────────────────────────────────
    if status == "终止":
        return {
            "next_action": "记录原因并复盘",
            "reason": "记录终止原因，分析是简历问题还是面试表现，为后续投递积累经验",
            "urgency": _urgency("低"),
        }

    # ── 放弃 ────────────────────────────────────────────────────────
    if status == "放弃":
        return {
            "next_action": "归档该投递记录",
            "reason": "已放弃该岗位，可归档或删除",
            "urgency": _urgency("低"),
        }

    # ── Legacy: 待投递 (mapped to 已投递) ──────────────────────────
    if status == "待投递":
        return _handle_pending(application, job, resume, days)

    # ── Fallback ────────────────────────────────────────────────────
    return {
        "next_action": "查看投递详情",
        "reason": "当前状态未识别，请手动确认下一步",
        "urgency": _urgency("低"),
    }


# ── Per-status handlers ──────────────────────────────────────────────────

def _handle_pending(application, job, resume, days: int) -> dict:
    """Handle the 待投递 (pending) status — optionally check match score."""
    if resume is not None:
        try:
            from services.match_agent import calculate_match_rule_based
            match = calculate_match_rule_based(job, resume)
            score = match.match_score
            if score >= 75:
                return {
                    "next_action": "建议立即投递",
                    "reason": f"岗位与简历匹配度 {score:.0f}%，建议尽快投递以抢占先机",
                    "urgency": _urgency("高"),
                }
            elif score >= 50:
                return {
                    "next_action": "优化简历后投递",
                    "reason": f"匹配度 {score:.0f}%，建议先补齐缺失技能关键词再投递",
                    "urgency": _urgency("中"),
                }
            else:
                return {
                    "next_action": "建议寻找更匹配的岗位",
                    "reason": f"匹配度仅 {score:.0f}%，方向或技能差距较大，建议优先投递匹配度更高的岗位",
                    "urgency": _urgency("低"),
                }
        except Exception:
            pass  # fall through to default

    # No resume or match failed — generic suggestion
    return {
        "next_action": "完成匹配分析后投递",
        "reason": "建议先前往 Match Lab 完成岗位-简历匹配分析，确认匹配度后再投递",
        "urgency": _urgency("中"),
    }


def _handle_applied(days: int) -> dict:
    """Handle 已投递 (applied) status — follow-up after 7 days."""
    if days > 7:
        return {
            "next_action": "跟进投递进度",
            "reason": f"已投递 {days} 天未收到反馈，建议通过邮件或招聘平台礼貌跟进",
            "urgency": _urgency("高"),
        }
    if days > 3:
        return {
            "next_action": "准备面试内容",
            "reason": f"投递 {days} 天，可以利用等待期提前准备面试",
            "urgency": _urgency("中"),
        }
    return {
        "next_action": "耐心等待反馈",
        "reason": f"刚投递 {days} 天，HR 筛选通常需要 3-7 个工作日",
        "urgency": _urgency("低"),
    }


# ── Legacy wrapper (keeps existing callers working) ──────────────────────

def generate_action_plan(jobs: list[dict], applications: list[dict],
                         interviews: list[dict]) -> list[dict]:
    """Legacy wrapper. Returns an empty list for backward compatibility.

    Prefer ``generate_next_action(application, job, resume)`` for new code.
    """
    return []
