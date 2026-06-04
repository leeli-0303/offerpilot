import streamlit as st

from core.data_store import store
from services.match_agent import calculate_match_rule_based, calculate_match_with_llm
from services.llm_client import get_llm_config
from services.export_utils import (
    build_match_analysis_markdown, export_to_markdown, _timestamp,
)

st.set_page_config(page_title="匹配分析 - OfferPilot", page_icon="🔬", layout="wide")

from core.auth import require_login
if not require_login():
    st.stop()

# ── CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.match-score-circle {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 36px;
    font-weight: 800;
    margin: 0 auto 12px auto;
}
.match-item {
    padding: 8px 12px;
    margin: 4px 0;
    border-radius: 6px;
    font-size: 13px;
}
.match-positive {
    background: #e8f5e9;
    border-left: 3px solid #2e7d32;
}
.match-gap {
    background: #fce4ec;
    border-left: 3px solid #c62828;
}
.match-suggestion {
    background: #fff3e0;
    border-left: 3px solid #e65100;
}
.action-banner {
    padding: 12px 20px;
    border-radius: 8px;
    font-size: 15px;
    font-weight: 600;
    text-align: center;
    margin: 12px 0;
}
.action-strong { background: #e8f5e9; color: #2e7d32; border: 1px solid #a5d6a7; }
.action-try    { background: #fff3e0; color: #e65100; border: 1px solid #ffcc80; }
.action-wait   { background: #fce4ec; color: #c62828; border: 1px solid #ef9a9a; }
.dim-label {
    font-size: 11px; color: #80868b; margin-top: 2px;
}
</style>
""", unsafe_allow_html=True)

# ── Data ───────────────────────────────────────────────────────────────
jobs = store.get_all_jobs()
resumes = store.get_all_resumes()

# ── Header ─────────────────────────────────────────────────────────────
st.title("匹配分析")
st.caption("AI 岗位-简历匹配分析 — 量化匹配度，找出差距，精准优化简历")

# ── Data check ──────────────────────────────────────────────────────────
if not jobs:
    st.info("还没有添加岗位，请先前往 Job Tracker 添加岗位")
    st.stop()
if not resumes:
    st.info("还没有简历版本，请先前往 Resume Vault 添加简历")
    st.stop()

# ── Selectors ──────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    job_options = {f"{j.company} — {j.title}": j.id for j in jobs}
    selected_job_label = st.selectbox(
        "选择岗位", list(job_options.keys()), key="match_job",
    )
    selected_job_id = job_options[selected_job_label]
with c2:
    resume_options = {r.version_name: r.id for r in resumes}
    selected_resume_label = st.selectbox(
        "选择简历版本", list(resume_options.keys()), key="match_resume",
    )
    selected_resume_id = resume_options[selected_resume_label]
with c3:
    match_mode = st.radio(
        "匹配模式",
        options=["rule", "llm"],
        format_func=lambda x: "🔧 规则匹配" if x == "rule" else "🤖 AI 匹配",
        horizontal=False,
        label_visibility="collapsed",
        key="match_mode",
    )
    analyze_clicked = st.button("🔍 开始分析", type="primary", use_container_width=True)

# ── AI disclaimer ─────────────────────────────────────────────────────
if match_mode == "llm":
    st.info(
        "**AI 匹配说明**：AI 建议仅基于当前简历记录和岗位 JD，不应编造不存在的经历。"
        "模型只基于简历中已有的关键词和项目亮点进行分析，"
        "如果简历信息不完整，建议先前往 Resume Vault 完善简历后再进行匹配。",
    )

if not analyze_clicked:
    st.info("👆 选择岗位和简历后，点击「开始分析」查看匹配结果")

else:
    job = store.get_job(selected_job_id)
    resume = store.get_resume(selected_resume_id)

    if not job or not resume:
        st.error("岗位或简历数据未找到，请刷新后重试")
    else:
        # ── Run match analysis ────────────────────────────────────────
        try:
            if match_mode == "llm":
                result = calculate_match_with_llm(job, resume)
            else:
                result = calculate_match_rule_based(job, resume)
        except Exception as exc:
            st.error(f"匹配分析失败：{exc}")
            import traceback
            with st.expander("🔧 错误详情（调试用）"):
                st.code(traceback.format_exc())
            st.stop()
        score = result.match_score

        st.divider()

        # ── Mode badge ────────────────────────────────────────────────
        llm_cfg = get_llm_config()
        if match_mode == "llm":
            mode_label = "🤖 AI 匹配" if llm_cfg["mode"] == "mock" else "🤖 AI 匹配（真实模型）"
        else:
            mode_label = "🔧 规则匹配"
        st.caption(f"匹配模式：{mode_label}")

        # ── Fallback warning ──────────────────────────────────────────
        if match_mode == "llm" and getattr(result, "_fallback", False):
            reason = getattr(result, "_fallback_reason", "")
            st.warning(
                f"⚠️ AI 匹配失败，已自动回退到规则匹配。\n\n"
                f"原因：{reason}\n\n"
                f"当前显示的是规则匹配结果，如需 AI 匹配请稍后重试。"
            )

        # ── Raw LLM output (debug) ────────────────────────────────────
        if match_mode == "llm":
            raw_output = getattr(result, "_raw_output", "")
            if raw_output:
                with st.expander("🔍 查看 AI 原始输出（调试用）"):
                    st.code(raw_output, language="json")

        # ── Results Layout: left score + action, right job/resume info ─
        left, right = st.columns([1, 2])

        with left:
            # Score circle
            if score >= 75:
                circle_color = "#2e7d32"
                gradient = "rgba(46,125,50,0.15),rgba(200,230,201,0.8)"
            elif score >= 50:
                circle_color = "#e65100"
                gradient = "rgba(230,81,0,0.12),rgba(255,224,178,0.8)"
            else:
                circle_color = "#c62828"
                gradient = "rgba(198,40,40,0.12),rgba(255,205,210,0.8)"

            st.markdown(
                f"<div class='match-score-circle' style='background:linear-gradient(135deg,{gradient});"
                f"color:{circle_color};'>{score:.0f}</div>"
                f"<div style='text-align:center;font-size:12px;color:#888;margin-bottom:4px;'>"
                f"综合匹配度（满分100）</div>",
                unsafe_allow_html=True,
            )
            st.progress(score / 100, text=f"匹配度 {score:.0f}/100")

            # Recommended action
            if "强烈建议投递" in result.recommended_action:
                banner_class = "action-strong"
            elif "可以尝试" in result.recommended_action:
                banner_class = "action-try"
            else:
                banner_class = "action-wait"

            st.markdown(
                f"<div class='action-banner {banner_class}'>{result.recommended_action}</div>",
                unsafe_allow_html=True,
            )

            # Quick stats
            n_matched = len(result.matched_points)
            n_missing = len(result.missing_points)
            n_risks = len(result.risk_notes)
            stat_cols = st.columns(3)
            with stat_cols[0]:
                st.metric("匹配项", n_matched)
            with stat_cols[1]:
                st.metric("缺失项", n_missing)
            with stat_cols[2]:
                st.metric("风险点", n_risks)

        with right:
            st.markdown(f"### {job.company} — {job.title}")
            st.markdown(f"**简历版本：** {resume.version_name}")

            # Job summary
            with st.expander("📋 岗位信息摘要", expanded=True):
                meta_items = []
                if job.direction:
                    meta_items.append(f"📌 方向：{job.direction}")
                if job.location:
                    meta_items.append(f"📍 地点：{job.location}")
                if job.priority:
                    priority_label = {"高": "🔴 高优先级", "中": "🟡 中优先级", "低": "⚪ 低优先级"}.get(job.priority, job.priority)
                    meta_items.append(priority_label)
                if job.jd_parsed_fields.get("skills"):
                    meta_items.append(
                        f"🛠 要求技能：{', '.join(job.jd_parsed_fields['skills'])}"
                    )
                if job.jd_parsed_fields.get("keywords"):
                    meta_items.append(
                        f"🏷 岗位标签：{', '.join(job.jd_parsed_fields['keywords'])}"
                    )
                for item in meta_items:
                    st.markdown(f"- {item}")

            # Resume summary
            with st.expander("📄 简历版本摘要", expanded=False):
                r_meta = []
                if resume.target_direction:
                    r_meta.append(f"📌 方向：{resume.target_direction}")
                if resume.keywords:
                    r_meta.append(f"🔑 关键词：{', '.join(resume.keywords)}")
                if resume.highlights:
                    r_meta.append(f"🚀 亮点：{len(resume.highlights)} 项")
                for item in r_meta:
                    st.markdown(f"- {item}")

        # ── Risk warnings ─────────────────────────────────────────────
        if result.risk_notes:
            st.divider()
            st.markdown("#### ⚠️ 岗位风险提示")
            for note in result.risk_notes:
                icon = "⚠️" if "注意" in note else "🟡"
                st.warning(f"{icon} {note}")

        # ── Detailed Analysis Tabs ────────────────────────────────────
        st.divider()

        tab1, tab2, tab3 = st.tabs([
            f"✅ 匹配点（{len(result.matched_points)}）",
            f"🔻 缺失项（{len(result.missing_points)}）",
            f"💡 优化建议（{len(result.optimization_suggestions)}）",
        ])

        with tab1:
            if result.matched_points:
                for point in result.matched_points:
                    st.markdown(
                        f"<div class='match-item match-positive'>✅ {point}</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.info("未检测到明确的匹配点，建议查看下方优化建议")

        with tab2:
            if result.missing_points:
                for point in result.missing_points:
                    st.markdown(
                        f"<div class='match-item match-gap'>🔻 {point}</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.success("未检测到明显的技能或标签缺失")

        with tab3:
            if result.optimization_suggestions:
                for s in result.optimization_suggestions:
                    st.markdown(
                        f"<div class='match-item match-suggestion'>💡 {s}</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.info("暂无特定的优化建议")

        # ── Bottom: score breakdown ───────────────────────────────────
        st.divider()
        if match_mode == "rule":
            st.caption("评分维度说明：技能匹配 45% · 标签匹配 20% · 方向匹配 20% · 项目亮点 15%")
            st.caption(
                "风险扣分：" + (
                    f"本岗位有 {len(result.risk_notes)} 条风险提示，"
                    f"共扣除 {len(result.risk_notes) * 3:.0f} 分" if result.risk_notes
                    else "本岗位无风险提示，未扣除分数"
                )
            )
        else:
            st.caption("AI 综合评估，无固定评分公式。分数和结论由模型基于岗位要求和简历内容综合判断。")
            st.caption("AI 建议仅基于当前简历记录和岗位 JD，不应编造不存在的经历。")
            if llm_cfg["mode"] == "mock":
                st.caption("当前为 Mock 模式，显示的是预设示例数据。设置 LLM_MODE=real 并配置 API Key 以启用真实 AI。")
            st.caption("如果对分数有疑问，可以切换到「规则匹配」模式查看量化对比。")

        # ── Export ──────────────────────────────────────────────────
        st.divider()
        st.subheader("📥 导出匹配分析")

        mode_label = "AI 匹配" if match_mode == "llm" else "规则匹配"
        md_content = build_match_analysis_markdown(job, resume, result, mode_label)

        exp_col1, exp_col2, exp_col3 = st.columns([2, 1, 1])
        with exp_col1:
            safe_company = job.company.replace(" ", "-") if job.company else "company"
            export_filename = st.text_input(
                "文件名",
                value=f"match-{safe_company}-{_timestamp()}.md",
                key="match_export_filename",
            )
        with exp_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 导出为 Markdown", use_container_width=True, key="match_export_btn"):
                filepath = export_to_markdown(md_content, export_filename)
                st.session_state["match_saved_path"] = filepath
                st.session_state["match_saved_content"] = md_content
                st.session_state["match_saved_filename"] = export_filename
        with exp_col3:
            if "match_saved_path" in st.session_state:
                st.markdown("<br>", unsafe_allow_html=True)
                st.download_button(
                    label="⬇️ 下载文件",
                    data=st.session_state["match_saved_content"],
                    file_name=st.session_state["match_saved_filename"],
                    mime="text/markdown",
                    use_container_width=True,
                    key="match_download_btn",
                )

        if "match_saved_path" in st.session_state:
            st.success(f"已保存到：`{st.session_state['match_saved_path']}`")
