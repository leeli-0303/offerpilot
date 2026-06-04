import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from core.data_store import store
from services.weekly_review import generate_weekly_review, generate_weekly_review_with_llm
from services.llm_client import get_llm_config
from services.export_utils import (
    build_weekly_review_markdown, export_to_markdown, _timestamp,
)

st.set_page_config(page_title="求职复盘 - OfferPilot", page_icon="📋", layout="wide")

from core.auth import require_login
if not require_login():
    st.stop()

# ── CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.week-header {
    background: linear-gradient(135deg, #4285f4, #1967d2);
    color: #fff;
    border-radius: 12px;
    padding: 24px 32px;
    margin-bottom: 20px;
}
.week-header .week-label {
    font-size: 14px;
    opacity: 0.9;
}
.week-header .week-date {
    font-size: 28px;
    font-weight: 800;
    margin-top: 4px;
}
.stat-card {
    text-align: center;
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 16px 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.stat-card .stat-number {
    font-size: 30px;
    font-weight: 800;
    color: #202124;
}
.stat-card .stat-label {
    font-size: 12px;
    color: #80868b;
    margin-top: 4px;
}
.stats-evidence {
    font-size: 11px;
    color: #80868b;
    text-align: center;
    margin-bottom: 8px;
    letter-spacing: 0.5px;
}
.highlight-item {
    padding: 10px 14px;
    margin: 6px 0;
    border-radius: 8px;
    font-size: 14px;
    background: #f8f9fa;
    border-left: 3px solid #4285f4;
}
.focus-item {
    padding: 10px 14px;
    margin: 6px 0;
    border-radius: 8px;
    font-size: 14px;
    background: #e8f5e9;
    border-left: 3px solid #2e7d32;
}
.problem-item {
    padding: 10px 14px;
    margin: 6px 0;
    border-radius: 8px;
    font-size: 14px;
    background: #fff3e0;
    border-left: 3px solid #e65100;
}
.ai-summary-box {
    background: #e8f0fe;
    border: 1px solid #c5d9f5;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 16px;
    font-size: 14px;
    line-height: 1.6;
    color: #202124;
}
.mode-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 600;
    margin-left: 8px;
}
.mode-ai { background: #e8f0fe; color: #1967d2; }
.mode-rule { background: #f3e5f5; color: #7b1fa2; }
</style>
""", unsafe_allow_html=True)

# ── Data ───────────────────────────────────────────────────────────────
applications = store.get_all_applications()
jobs = store.get_all_jobs()
resumes = store.get_all_resumes()

# ── Header ─────────────────────────────────────────────────────────────
st.title("求职复盘")
st.caption("求职策略复盘 — 数据统计 + AI 分析，每周迭代求职策略")

# ── Mode toggle & Generate button ──────────────────────────────────────
c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    st.write("")  # spacer
with c2:
    review_mode = st.radio(
        "周报模式", ["🔧 规则周报", "🤖 AI 周报"],
        key="review_mode", horizontal=True,
    )
with c3:
    st.markdown("<br>", unsafe_allow_html=True)
    generate_clicked = st.button(
        "🔄 生成本周周报", type="primary", use_container_width=True,
    )

use_ai = (review_mode == "🤖 AI 周报")

# ── AI disclaimer ──────────────────────────────────────────────────────
if use_ai:
    llm_cfg = get_llm_config()
    if llm_cfg["mode"] == "mock":
        st.info(
            "**AI 周报说明**：AI 仅基于统计摘要生成策略分析，"
            "不会编造不存在的数据。当前为 Mock 模式，显示预设示例数据。"
        )
    else:
        st.info(
            "**AI 周报说明**：AI 仅基于统计摘要生成策略分析，"
            "不会编造不存在的数据。所有结论和行动建议均源于真实求职数据。"
        )

# ── Generate ───────────────────────────────────────────────────────────
weekly_report = store.get_latest_weekly_review()

if generate_clicked:
    with st.spinner("正在分析求职数据，生成周报..."):
        try:
            if use_ai:
                weekly_report = generate_weekly_review_with_llm(applications, jobs, resumes)
            else:
                weekly_report = generate_weekly_review(applications, jobs, resumes)
            store.add_weekly_review(weekly_report)
        except Exception as exc:
            st.error(f"生成周报失败：{exc}")
            import traceback
            with st.expander("🔧 错误详情（调试用）"):
                st.code(traceback.format_exc())
            st.stop()

    # ── Success message with mode indicator ──────────────────────────
    if use_ai:
        llm_cfg = get_llm_config()
        if llm_cfg["mode"] == "mock":
            msg = "🤖 AI 周报已生成并保存！（Mock 模式）"
        else:
            msg = "🤖 AI 周报已生成并保存！（真实模型）"
    else:
        msg = "📋 规则周报已生成并保存！"
    st.success(msg)

    # ── Fallback warning ────────────────────────────────────────────
    if use_ai and getattr(weekly_report, "_fallback", False):
        reason = getattr(weekly_report, "_fallback_reason", "")
        st.warning(
            f"⚠️ AI 周报生成失败，已自动回退到规则周报。\n\n"
            f"原因：{reason}\n\n"
            f"当前显示的是规则周报结果，如需 AI 周报请稍后重试。"
        )

if weekly_report is None and not applications:
    st.warning("暂无投递记录和求职数据，请先前往 Job Tracker 添加投递记录。")
    st.stop()

if weekly_report is None:
    st.info("👆 点击「生成本周周报」按钮，基于当前求职数据生成策略复盘报告")
    st.stop()

# ═══════════════════════════════════════════════════════════════════════════
# Week Banner
# ═══════════════════════════════════════════════════════════════════════════

# Detect mode from review fields (AI summary present + not fallback = AI generated)
has_ai_summary = "ai_summary" in weekly_report.stats
is_ai_mode = has_ai_summary and not getattr(weekly_report, "_fallback", False)
mode_class = "mode-ai" if is_ai_mode else "mode-rule"
mode_text = "🤖 AI 生成" if is_ai_mode else "🔧 规则生成"

st.markdown(
    f"<div class='week-header'>"
    f"<div class='week-label'>📋 求职周报 "
    f"<span class='mode-badge {mode_class}'>{mode_text}</span></div>"
    f"<div class='week-date'>{weekly_report.week_label} · {weekly_report.date_range}</div>"
    f"</div>",
    unsafe_allow_html=True,
)

# ── Raw LLM output (debug) ─────────────────────────────────
raw_output = getattr(weekly_report, "_raw_output", "")
if raw_output:
    with st.expander("🔍 查看 AI 原始输出（调试用）"):
        st.code(raw_output, language="json")

# ═══════════════════════════════════════════════════════════════════════════
# Stats Row (always shown — serves as evidence for AI-generated content)
# ═══════════════════════════════════════════════════════════════════════════

stats = weekly_report.stats

if has_ai_summary:
    st.markdown(
        "<div class='stats-evidence'>📊 以下为真实统计数据，AI 分析以上述数据为依据</div>",
        unsafe_allow_html=True,
    )

s1, s2, s3, s4, s5, s6 = st.columns(6)
stat_items = [
    (s1, stats.get("total_applications", 0), "#1967d2", "投递总数"),
    (s2, stats.get("new_this_week", 0), "#4285f4", "本周新增"),
    (s3, stats.get("interviewing", 0), "#7b1fa2", "面试中"),
    (s4, stats.get("offers", 0), "#2e7d32", "Offer"),
    (s5, stats.get("rejected", 0), "#c62828", "已拒绝"),
    (s6, stats.get("no_feedback", 0), "#e65100", "无反馈"),
]
for col, val, color, label in stat_items:
    with col:
        st.markdown(
            f"<div class='stat-card'>"
            f"<div class='stat-number' style='color:{color};'>{val}</div>"
            f"<div class='stat-label'>{label}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# AI Summary (only for AI-generated reviews)
# ═══════════════════════════════════════════════════════════════════════════

if has_ai_summary:
    ai_summary = stats.get("ai_summary", "")
    if ai_summary:
        st.subheader("📋 AI 策略分析")
        st.markdown(
            f"<div class='ai-summary-box'>{ai_summary}</div>",
            unsafe_allow_html=True,
        )

# ═══════════════════════════════════════════════════════════════════════════
# Charts: Direction distribution & Resume usage
# ═══════════════════════════════════════════════════════════════════════════

chart_left, chart_right = st.columns(2)

with chart_left:
    st.subheader("📊 岗位方向分布")
    directions = stats.get("directions", {})
    if directions:
        df_dir = pd.DataFrame({
            "方向": list(directions.keys()),
            "投递数": list(directions.values()),
        })
        st.bar_chart(df_dir.set_index("方向"), use_container_width=True)
    else:
        st.info("暂无方向数据")

with chart_right:
    st.subheader("📄 简历版本使用次数")
    resume_usage = stats.get("resume_usage", {})
    if resume_usage:
        df_resume = pd.DataFrame({
            "简历版本": list(resume_usage.keys()),
            "使用次数": list(resume_usage.values()),
        })
        st.bar_chart(df_resume.set_index("简历版本"), use_container_width=True)
    else:
        st.info("暂无简历使用数据")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# Status Pipeline
# ═══════════════════════════════════════════════════════════════════════════

st.subheader("📈 投递漏斗")
status_order = ["已投递", "简历评估", "笔试/测评", "一面", "二面", "HR面", "offer", "终止", "放弃"]
status_map = {s: 0 for s in status_order}
for a in applications:
    s = a.status
    if s in status_map:
        status_map[s] += 1

pipeline_data = [{"状态": k, "数量": v} for k, v in status_map.items() if v > 0]
if pipeline_data:
    df_pipeline = pd.DataFrame(pipeline_data)
    st.bar_chart(df_pipeline.set_index("状态"), use_container_width=True)
else:
    st.info("暂无投递数据")

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# Highlights & Problems → 本周总结
# Next Week Focus → 下周关注
# ═══════════════════════════════════════════════════════════════════════════

# Separate highlights into insights and problems for display
highlights = weekly_report.highlights or []
insight_items = [h for h in highlights if not h.startswith("⚠️")]
problem_items = [h.replace("⚠️ ", "") for h in highlights if h.startswith("⚠️")]

left, right = st.columns(2)

with left:
    st.subheader("🌟 本周总结 & 亮点")
    if insight_items:
        for h in insight_items:
            st.markdown(f"<div class='highlight-item'>{h}</div>", unsafe_allow_html=True)
    else:
        st.info("暂无总结")

    if problem_items:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("⚠️ 发现的问题")
        for p in problem_items:
            st.markdown(f"<div class='problem-item'>{p}</div>", unsafe_allow_html=True)

with right:
    st.subheader("🎯 下周关注 & 行动建议")
    focus_items = weekly_report.next_week_focus
    if focus_items:
        for item in focus_items:
            st.markdown(f"<div class='focus-item'>📌 {item}</div>", unsafe_allow_html=True)
    else:
        st.info("暂无关注项")

# ═══════════════════════════════════════════════════════════════════════════
# Export
# ═══════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("📥 导出周报")

mode_label = "AI 周报" if is_ai_mode else "规则周报"
md_content = build_weekly_review_markdown(weekly_report, mode_label)

export_col1, export_col2, export_col3 = st.columns([2, 1, 1])
with export_col1:
    export_filename = st.text_input(
        "文件名", value=f"weekly-review-{_timestamp()}.md",
        key="weekly_export_filename",
    )
with export_col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("💾 导出为 Markdown", use_container_width=True, key="weekly_export_btn"):
        filepath = export_to_markdown(md_content, export_filename)
        st.session_state["weekly_saved_path"] = filepath
        st.session_state["weekly_saved_content"] = md_content
        st.session_state["weekly_saved_filename"] = export_filename
with export_col3:
    if "weekly_saved_path" in st.session_state:
        st.markdown("<br>", unsafe_allow_html=True)
        st.download_button(
            label="⬇️ 下载文件",
            data=st.session_state["weekly_saved_content"],
            file_name=st.session_state["weekly_saved_filename"],
            mime="text/markdown",
            use_container_width=True,
            key="weekly_download_btn",
        )

if "weekly_saved_path" in st.session_state:
    st.success(f"已保存到：`{st.session_state['weekly_saved_path']}`")

# ═══════════════════════════════════════════════════════════════════════════
# Historical Reviews
# ═══════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("📋 历史周报")

all_reviews = store.get_all_weekly_reviews()
historical_reviews = all_reviews[1:] if len(all_reviews) > 1 else []
# Also treat the current review as historical once we have more than one
if len(all_reviews) > 1:
    historical_reviews = all_reviews[1:]

if historical_reviews:
    for r in historical_reviews:
        with st.expander(f"{r.week_label} · {r.date_range}", expanded=False):
            # Stats row
            rs = r.stats
            cs = st.columns(6)
            metrics = [
                ("投递总数", rs.get("total_applications", rs.get("applications_sent", 0))),
                ("本周新增", rs.get("new_this_week", rs.get("new_jobs", 0))),
                ("面试中", rs.get("interviewing", rs.get("interviews_completed", 0))),
                ("Offer", rs.get("offers", rs.get("offers_received", 0))),
                ("已拒绝", rs.get("rejected", 0)),
                ("无反馈", rs.get("no_feedback", 0)),
            ]
            for col, (label, val) in zip(cs, metrics):
                with col:
                    st.metric(label, val)

            # AI summary
            if "ai_summary" in rs:
                st.markdown("##### 📋 AI 策略分析")
                st.info(rs["ai_summary"])

            # Highlights
            highlights = r.highlights or []
            insights = [h for h in highlights if not h.startswith("⚠️")]
            problems = [h.replace("⚠️ ", "") for h in highlights if h.startswith("⚠️")]

            if insights:
                st.markdown("##### 🌟 本周总结")
                for item in insights:
                    st.markdown(
                        f"<div class='highlight-item'>{item}</div>",
                        unsafe_allow_html=True,
                    )
            if problems:
                st.markdown("##### ⚠️ 发现的问题")
                for item in problems:
                    st.markdown(
                        f"<div class='problem-item'>{item}</div>",
                        unsafe_allow_html=True,
                    )

            # Next week focus
            if r.next_week_focus:
                st.markdown("##### 🎯 下周关注")
                for item in r.next_week_focus:
                    st.markdown(
                        f"<div class='focus-item'>📌 {item}</div>",
                        unsafe_allow_html=True,
                    )

            # Direction distribution
            directions = rs.get("directions", {})
            if directions:
                st.markdown("##### 📊 方向分布")
                st.caption(
                    " · ".join(f"{d}: {c}次" for d, c in directions.items())
                )

            # ── User Notes (editable) ─────────────────────────────────
            st.markdown("---")
            st.markdown("##### 📝 我的备注")
            notes_key = f"history_notes_{r.id}"
            saved_key = f"history_saved_{r.id}"

            current_notes = st.text_area(
                "备注内容",
                value=r.user_notes,
                placeholder="记录你的想法、反思、经验教训...",
                height=80,
                key=notes_key,
                label_visibility="collapsed",
            )
            if st.button("💾 保存备注", key=f"save_notes_{r.id}", use_container_width=True):
                ok, msg = store.update_weekly_review(r.id, {"user_notes": current_notes})
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
else:
    st.info("生成更多周报后，可在此查看历史趋势")
