from datetime import datetime, timedelta
from collections import Counter

import streamlit as st

from core.data_store import store
from services.action_planner import generate_next_action

st.set_page_config(page_title="概览 - OfferPilot", page_icon="🎯", layout="wide")

from core.auth import require_login
if not require_login():
    st.stop()

# ── CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.hero-banner {
    background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
    border-radius: 16px;
    padding: 36px 44px;
    margin-bottom: 24px;
    color: #fff;
}
.hero-banner .welcome {
    font-size: 14px;
    opacity: 0.85;
    margin-bottom: 4px;
}
.hero-banner .headline {
    font-size: 28px;
    font-weight: 800;
    line-height: 1.3;
}
.hero-banner .subline {
    font-size: 15px;
    opacity: 0.85;
    margin-top: 8px;
}
.metric-card {
    background: #fff;
    border: 1px solid #e8eaed;
    border-radius: 12px;
    padding: 18px 20px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.metric-card .big-num {
    font-size: 36px;
    font-weight: 800;
    line-height: 1;
}
.metric-card .big-label {
    font-size: 12px;
    color: #5f6368;
    margin-top: 6px;
}
.metric-card .sub-note {
    font-size: 11px;
    color: #80868b;
    margin-top: 2px;
}
.section-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
}
.section-header .section-title {
    font-size: 16px;
    font-weight: 700;
    color: #202124;
}
.action-row {
    background: #fff;
    border: 1px solid #e8eaed;
    border-radius: 10px;
    padding: 14px 18px;
    margin-bottom: 8px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    display: flex;
    align-items: flex-start;
    gap: 12px;
}
.action-row.urgent {
    border-left: 4px solid #ea4335;
    background: #fef7f7;
}
.action-row.normal {
    border-left: 4px solid #4285f4;
    background: #f8faff;
}
.action-row .urgency-dot {
    font-size: 20px;
    line-height: 1;
}
.action-row .action-text {
    flex: 1;
    font-size: 13px;
    line-height: 1.5;
    color: #202124;
}
.action-row .action-reason {
    font-size: 11px;
    color: #5f6368;
}
.action-row .action-company {
    font-weight: 700;
}
.event-item {
    padding: 8px 0;
    border-bottom: 1px solid #f0f0f0;
    font-size: 13px;
}
.event-item .event-date {
    font-size: 11px;
    color: #80868b;
    min-width: 48px;
    display: inline-block;
}
.event-item .event-company {
    font-weight: 600;
    color: #202124;
}
.empty-state {
    text-align: center;
    padding: 32px 16px;
    color: #80868b;
    font-size: 14px;
}
.empty-state .big-icon {
    font-size: 36px;
    margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)

# ── Data ───────────────────────────────────────────────────────────────
applications = store.get_all_applications()
jobs = store.get_all_jobs()
resumes = store.get_all_resumes()
now = datetime.now()
today = now.date()
monday = today - timedelta(days=today.weekday())
week_start = datetime.combine(monday, datetime.min.time())

jobs_dict = {j.id: j for j in jobs}
resumes_dict = {r.id: r for r in resumes}

# ── Compute real metrics ───────────────────────────────────────────────
total = len(applications)
# This week: applications whose created_at >= Monday OR whose updated_at >= Monday
new_this_week = sum(1 for a in applications if a.created_at and a.created_at >= week_start)

status_counts = Counter(a.status for a in applications)
interviewing = sum(status_counts.get(s, 0) for s in ("一面", "二面", "HR面", "笔试/测评", "简历评估"))
offers = status_counts.get("offer", 0)
rejected = status_counts.get("终止", 0)
applied_waiting = status_counts.get("已投递", 0) + status_counts.get("简历评估", 0)
pending = 0  # "待投递" removed in V2

# Conversion: offers / applications that entered interview pipeline
entered_pipeline = interviewing + offers + rejected
conversion = f"{offers / max(entered_pipeline, 1) * 100:.0f}%" if entered_pipeline > 0 else "—"

# ── Header ─────────────────────────────────────────────────────────────
st.title("概览")
greeting = "早上好" if now.hour < 12 else ("下午好" if now.hour < 18 else "晚上好")

st.markdown(
    f"<div class='hero-banner'>"
    f"<div class='welcome'>{greeting}，今日求职概览</div>"
    f"<div class='headline'>"
    f"{total} 条投递 · {interviewing} 个面试中"
    f"{' · ' + str(offers) + ' 个 Offer' if offers > 0 else ''}"
    f"</div>"
    f"<div class='subline'>"
    f"本周新增 {new_this_week} 条投递 | 投递→Offer 转化率 {conversion} | "
    f"数据更新于 {now.strftime('%m月%d日 %H:%M')}"
    f"</div>"
    f"</div>",
    unsafe_allow_html=True,
)

# ── Metric Cards ───────────────────────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)
metrics = [
    (m1, total, "#1a73e8", "投递总数", f"本周 +{new_this_week}"),
    (m2, applied_waiting + pending, "#e65100", "待反馈", f"已投递 {applied_waiting} + 待投递 {pending}"),
    (m3, interviewing, "#7b1fa2", "面试中", f"一面/二面/HR面/测评"),
    (m4, offers, "#2e7d32", "Offer", f"转化率 {conversion}"),
    (m5, rejected, "#c62828", "已拒绝", "持续优化策略"),
]
for col, val, color, label, note in metrics:
    with col:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='big-num' style='color:{color};'>{val}</div>"
            f"<div class='big-label'>{label}</div>"
            f"<div class='sub-note'>{note}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# Two-column: AI Actions + Recent Activity
# ═══════════════════════════════════════════════════════════════════════════

left, right = st.columns([1, 1])

with left:
    st.markdown(
        "<div class='section-header'>"
        "<span class='section-title'>🤖 AI 下一步行动建议</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    if applications:
        # Generate action plans for all applications, sort by urgency
        action_items: list[dict] = []
        for a in applications:
            job = jobs_dict.get(a.job_id)
            resume = resumes_dict.get(a.resume_id)
            if not job:
                continue
            plan = generate_next_action(a, job, resume)
            plan["_company"] = job.company
            plan["_title"] = job.title
            plan["_status"] = a.status
            action_items.append(plan)

        # Sort: 高 urgency first
        urgency_rank = {"高": 0, "中": 1, "低": 2}
        action_items.sort(key=lambda x: urgency_rank.get(x.get("urgency", "低"), 2))

        shown = 0
        for item in action_items:
            if shown >= 6:
                break
            urgency = item.get("urgency", "低")
            if urgency == "低" and shown >= 4:
                continue  # skip low urgency if we already have enough items
            shown += 1

            is_urgent = (urgency == "高")
            row_class = "urgent" if is_urgent else "normal"
            urgency_text = "高优先" if urgency == "高" else ("中优先" if urgency == "中" else "普通")

            st.markdown(
                f"<div class='action-row {row_class}'>"
                f"<div class='urgency-dot'>{'🔴' if urgency == '高' else ('🟡' if urgency == '中' else '🔵')}</div>"
                f"<div>"
                f"<div class='action-text'>"
                f"<span class='action-company'>{item['_company']}</span>"
                f" <span style='font-size:11px;color:#80868b;'>({item['_status']})</span>"
                f"<br>{item['next_action']}"
                f"</div>"
                f"<div class='action-reason'>{item['reason']}</div>"
                f"</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            "<div class='empty-state'>"
            "<div class='big-icon'>📋</div>"
            "还没有投递记录<br>"
            "<small>前往 <b>Job Tracker</b> 创建第一条投递记录，AI 将为你生成行动建议</small>"
            "</div>",
            unsafe_allow_html=True,
        )

with right:
    st.markdown(
        "<div class='section-header'>"
        "<span class='section-title'>📌 近期投递动态</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    if applications:
        # Show last 8 applications sorted by updated_at
        recent = sorted(applications, key=lambda a: a.updated_at or a.created_at or datetime.min, reverse=True)[:8]
        for a in recent:
            job = jobs_dict.get(a.job_id)
            if not job:
                continue
            date_str = (a.updated_at or a.created_at).strftime("%m/%d %H:%M") if (a.updated_at or a.created_at) else "—"
            status_icon = {
                "已投递": "📤", "简历评估": "📋", "笔试/测评": "📝",
                "一面": "🎤", "二面": "🎤", "HR面": "💬",
                "offer": "🎉", "终止": "✕", "放弃": "⏹",
            }.get(a.status, "📋")

            st.markdown(
                f"<div class='event-item'>"
                f"<span class='event-date'>{date_str}</span>"
                f"<span class='event-company'>{job.company}</span>"
                f" <span style='color:#5f6368;'>{job.title[:20]}</span>"
                f" <span style='font-size:11px;'>{status_icon} {a.status}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            "<div class='empty-state'>"
            "<div class='big-icon'>📤</div>"
            "暂无投递活动<br>"
            "<small>去 <b>Job Tracker</b> 开始你的求职之旅</small>"
            "</div>",
            unsafe_allow_html=True,
        )

# ── Quick links ───────────────────────────────────────────────────────
st.divider()
st.markdown("### 🚀 快捷操作")
ql1, ql2, ql3, ql4, ql5 = st.columns(5)
with ql1:
    st.page_link("pages/2_投递池.py", label="➕ 新增投递", icon="💼")
with ql2:
    st.page_link("pages/3_简历池.py", label="📄 管理简历版本", icon="📄")
with ql3:
    st.page_link("pages/4_匹配分析.py", label="🔬 匹配分析", icon="🔬")
with ql4:
    st.page_link("pages/5_面试准备.py", label="🎤 面试准备", icon="🎤")
with ql5:
    st.page_link("pages/6_求职复盘.py", label="📋 生成周报", icon="📋")
