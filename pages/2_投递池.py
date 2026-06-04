import streamlit as st
from datetime import datetime, date

from core.data_store import store
from core.models import Job, JobStatus, Application, APPLICATION_STATUSES_V2, NEXT_ACTION_MAP_V2
from core.utils import generate_id
from services.jd_parser import parse_jd_rule_based, parse_jd_with_llm
from services.match_agent import calculate_match_rule_based
from services.action_planner import generate_next_action

st.set_page_config(page_title="投递池 - OfferPilot", page_icon="💼", layout="wide")

from core.auth import require_login
if not require_login():
    st.stop()

# ── CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.job-card {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 10px;
    font-size: 13px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.job-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.job-card .company { font-weight: 700; font-size: 14px; color: #202124; }
.job-card .title   { font-size: 13px; color: #5f6368; margin: 2px 0; }
.job-card .meta    { font-size: 12px; color: #80868b; margin-top: 4px; }
.job-card .tags    { margin-top: 6px; }
.tag {
    display: inline-block;
    background: #f1f3f4;
    color: #5f6368;
    padding: 1px 8px;
    border-radius: 4px;
    font-size: 11px;
    margin-right: 4px;
}
.kanban-col {
    background: #f5f5f5;
    border-radius: 8px;
    padding: 10px;
    min-height: 200px;
}
.kanban-col-title {
    font-weight: 700;
    font-size: 13px;
    padding: 4px 8px;
    border-radius: 4px;
    margin-bottom: 8px;
    text-align: center;
    color: #fff;
}
.col-interested  .kanban-col-title { background: #1967d2; }
.col-applied     .kanban-col-title { background: #e65100; }
.col-interviewing .kanban-col-title{ background: #7b1fa2; }
.col-offered     .kanban-col-title { background: #2e7d32; }
.col-rejected    .kanban-col-title { background: #c62828; }
.stage-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 8px;
    font-size: 11px;
    font-weight: 600;
    margin-top: 4px;
}
.stage-interested   { background: #e8f0fe; color: #1967d2; }
.stage-applied      { background: #fff3e0; color: #e65100; }
.stage-interviewing { background: #f3e5f5; color: #7b1fa2; }
.stage-offered      { background: #e8f5e9; color: #2e7d32; }
.stage-rejected     { background: #fce4ec; color: #c62828; }
.priority-high { color: #ea4335; font-weight: 700; }
.priority-medium { color: #fbbc04; font-weight: 700; }
.priority-low { color: #80868b; }
/* Application kanban cards */
.app-kanban-card {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    padding: 8px 10px;
    margin-bottom: 6px;
    font-size: 11px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.app-kanban-card:hover { box-shadow: 0 2px 6px rgba(0,0,0,0.10); }
.app-kanban-card .ak-company { font-weight: 700; font-size: 12px; color: #202124; }
.app-kanban-card .ak-title   { font-size: 11px; color: #5f6368; margin: 1px 0; }
.app-kanban-card .ak-meta    { font-size: 10px; color: #80868b; margin-top: 2px; line-height: 1.4; }
.app-kanban-card .ak-score   { font-weight: 700; font-size: 13px; }
.ak-score-high  { color: #2e7d32; }
.ak-score-mid   { color: #e65100; }
.ak-score-low   { color: #c62828; }
.ak-status-col-header {
    font-weight: 700;
    font-size: 11px;
    padding: 4px 6px;
    border-radius: 4px;
    margin-bottom: 6px;
    text-align: center;
    color: #fff;
}
.ak-status-pending   { background: #1967d2; }
.ak-status-sent      { background: #e65100; }
.ak-status-exam      { background: #f9a825; color: #333; }
.ak-status-tech1     { background: #7b1fa2; }
.ak-status-tech2     { background: #6a1b9a; }
.ak-status-hr        { background: #00838f; }
.ak-status-offer     { background: #2e7d32; }
.ak-status-rejected  { background: #c62828; }
.ak-status-abandoned { background: #546e7a; }
</style>
""", unsafe_allow_html=True)

# ── Data ───────────────────────────────────────────────────────────────
STATUS_LABEL = {
    JobStatus.INTERESTED:   ("有意向",  "👀"),
    JobStatus.APPLIED:      ("已投递",  "📤"),
    JobStatus.INTERVIEWING: ("面试中",  "🎤"),
    JobStatus.OFFERED:      ("已 Offer","🎉"),
    JobStatus.REJECTED:     ("已拒绝",  "✕"),
}
STATUS_ORDER = [JobStatus.INTERESTED, JobStatus.APPLIED, JobStatus.INTERVIEWING, JobStatus.OFFERED, JobStatus.REJECTED]
DIRECTION_OPTIONS = ["后端", "前端", "算法", "数据", "产品", "设计", "运营", "客户端", "安全", "其他"]
PRIORITY_OPTIONS = ["高", "中", "低"]
PRIORITY_LABEL = {"高": "🔴 高", "中": "🟡 中", "低": "⚪ 低"}

# ── Header ─────────────────────────────────────────────────────────────
st.title("投递池")
st.caption("投递记录管理 — 创建、编辑、追踪每一份投递，从投递到 Offer 全流程管理")

# ── Load data early (needed by the form and the rest of the page) ──────
jobs = store.get_all_jobs()
applications = store.get_all_applications()
resumes = store.get_all_resumes()

# ═══════════════════════════════════════════════════════════════════════
# 新增投递 (JD parsing + form — creates Job + Application together)
# ═══════════════════════════════════════════════════════════════════════

with st.expander("➕ 新增投递", expanded=False):

    # ── Step 1: Paste JD & Parse ────────────────────────────────────
    st.markdown("#### 📋 Step 1: 粘贴 JD 并解析")

    jd_paste = st.text_area(
        "JD 原文",
        placeholder="在此粘贴岗位描述全文，然后点击「解析 JD」自动识别方向、技能和风险...",
        height=140,
        key="jd_paste_area",
        label_visibility="collapsed",
    )

    c_mode, c_btn1, c_btn2, c_spacer = st.columns([3, 2, 2, 4])
    with c_mode:
        parse_mode = st.radio(
            "解析模式",
            options=["rule", "llm"],
            format_func=lambda x: "🔧 规则解析" if x == "rule" else "🤖 AI 解析",
            horizontal=True,
            label_visibility="collapsed",
            key="parse_mode",
        )
    with c_btn1:
        parse_clicked = st.button("🔍 解析 JD", key="btn_parse_jd", type="secondary",
                                   use_container_width=True)
    with c_btn2:
        if st.button("🗑 清除解析", key="btn_clear_parse", use_container_width=True):
            for key in ("jd_parse_result", "jd_parse_mode", "jd_raw_text"):
                st.session_state.pop(key, None)
            st.rerun()

    if parse_clicked:
        if not jd_paste.strip():
            st.warning("请先粘贴 JD 文本再解析")
        else:
            try:
                if parse_mode == "llm":
                    parsed = parse_jd_with_llm(jd_paste.strip())
                    st.session_state.jd_parse_mode = "llm"
                else:
                    parsed = parse_jd_rule_based(jd_paste.strip())
                    st.session_state.jd_parse_mode = "rule"
                st.session_state.jd_parse_result = parsed
                st.session_state.jd_raw_text = jd_paste.strip()

                # ── Auto-fill Step 2 form fields ───────────────────
                # Streamlit's text_input value= / selectbox index= only
                # work on first render.  After that the widget values
                # persist in their own session_state slots and ignore
                # the constructor parameters.  We explicitly overwrite
                # those slots so the form pre-fills on the next rerun.
                st.session_state.form_company = parsed.get("company", "")
                st.session_state.form_title = parsed.get("title", "")
                st.session_state.form_location = parsed.get("location", "")
                st.session_state.form_skills = ", ".join(parsed.get("skills", []))
                st.session_state.form_keywords = ", ".join(parsed.get("keywords", []))
                st.session_state.form_jd = jd_paste.strip()

                # Selectbox indexes
                jd_dir = parsed.get("job_type_direction", "")
                if jd_dir in DIRECTION_OPTIONS:
                    st.session_state.form_direction = DIRECTION_OPTIONS.index(jd_dir)
                jd_pri = parsed.get("priority", "中")
                if jd_pri in PRIORITY_OPTIONS:
                    st.session_state.form_priority = PRIORITY_OPTIONS.index(jd_pri)
            except Exception as e:
                st.error(f"解析失败：{e}")
                st.info("请尝试切换到「规则解析」模式，或缩短 JD 文本后重试")
            else:
                st.rerun()

    # ── Display parse results ───────────────────────────────────────
    parsed = st.session_state.get("jd_parse_result")
    parse_mode_used = st.session_state.get("jd_parse_mode", "rule")

    if parsed:
        st.markdown("---")
        mode_badge = "🤖 AI 解析" if parse_mode_used == "llm" else "🔧 规则解析"

        # ── Real / Mock indicator ────────────────────────────────────
        from services.llm_client import get_llm_config
        llm_cfg = get_llm_config()
        env_mode = llm_cfg["mode"]
        if parse_mode_used == "llm":
            if env_mode == "real":
                mode_badge += " <span style='font-size:11px;color:#2e7d32;'>(✅ 真实 {})</span>".format(llm_cfg["model_name"])
            else:
                mode_badge += " <span style='font-size:11px;color:#f9a825;'>(⚠️ Mock 模式)</span>"

        st.markdown(f"##### 🔍 解析结果  <span style='font-size:12px;color:#80868b;'>({mode_badge})</span>", unsafe_allow_html=True)

        # ── Fallback warning (AI parse fell back to rule-based) ──────
        if parse_mode_used == "llm" and parsed.get("_fallback"):
            reason = parsed.get("_fallback_reason", "AI 解析失败，已自动回退到规则解析")
            st.warning(f"⚠️ {reason}。当前显示的是规则解析结果，如有偏差请手动修正。")

        # ── Raw LLM output (for debugging / verification) ─────────────
        if parse_mode_used == "llm" and parsed.get("_raw_output"):
            with st.expander("📝 查看 AI 原始输出（调试用）", expanded=False):
                st.code(parsed["_raw_output"], language="json")

        # Row 1: company / title / location (LLM-only), job_type / priority / counts
        if parse_mode_used == "llm":
            ri, ri2, ri3, ri4 = st.columns(4)
            with ri:
                st.metric("识别公司", parsed.get("company") or "未识别")
            with ri2:
                st.metric("识别岗位名称", parsed.get("title") or "未识别")
            with ri3:
                st.metric("识别工作地点", parsed.get("location") or "未识别")
            with ri4:
                jt = parsed.get("job_type") or "未识别"
                jd_dir = parsed.get("job_type_direction") or "—"
                st.metric("识别岗位类型", jt, delta=jd_dir)
        else:
            ri, ri2, ri3 = st.columns(3)
            with ri:
                jt = parsed.get("job_type") or "未识别"
                jd_dir = parsed.get("job_type_direction") or "—"
                st.metric("识别岗位类型", jt, delta=jd_dir)
            with ri2:
                st.metric("建议优先级", parsed.get("priority", "中"))
            with ri3:
                skills_count = len(parsed.get("skills", []))
                kw_count = len(parsed.get("keywords", []))
                st.metric("识别技能 / 标签", f"{skills_count} 技能 + {kw_count} 标签")

        # Row 2: LLM extra fields
        if parse_mode_used == "llm":
            ri_a, ri_b, ri_c = st.columns(3)
            with ri_a:
                st.metric("建议优先级", parsed.get("priority", "中"))
            with ri_b:
                edu = parsed.get("education_requirement", "") or "未提及"
                st.metric("学历要求", edu)
            with ri_c:
                dl = parsed.get("deadline", "") or "未提及"
                st.metric("截止时间", dl)

        # Row 3: skills/kw counts for LLM mode
        if parse_mode_used == "llm":
            skills_count = len(parsed.get("skills", []))
            kw_count = len(parsed.get("keywords", []))
            st.caption(f"识别 {skills_count} 项技能 · {kw_count} 个标签")

        # Skills chips
        if parsed.get("skills"):
            skills_html = " ".join(
                [f'<span style="display:inline-block;background:#e8f0fe;color:#1967d2;'
                 f'padding:2px 10px;border-radius:12px;font-size:12px;margin:2px;">{s}</span>'
                 for s in parsed["skills"]])
            st.markdown(f"**🛠 技能：** {skills_html}", unsafe_allow_html=True)

        # Keywords chips
        if parsed.get("keywords"):
            kw_html = " ".join(
                [f'<span style="display:inline-block;background:#f1f3f4;color:#5f6368;'
                 f'padding:2px 8px;border-radius:4px;font-size:11px;margin:2px;">{k}</span>'
                 for k in parsed["keywords"]])
            st.markdown(f"**🏷 标签：** {kw_html}", unsafe_allow_html=True)

        # Risk notes
        if parsed.get("risk_notes"):
            for note in parsed["risk_notes"]:
                icon = "⚠️" if "注意" in note else "🟡"
                st.warning(f"{icon} {note}")

    # ── Step 2: Fill form ───────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📝 Step 2: 核对并补充信息")

    # Compute defaults from parse result
    default_direction_index = 0
    default_priority_index = 1  # "中"
    default_company = ""
    default_title = ""
    default_location = ""
    default_skills_str = ""
    default_keywords_str = ""
    default_jd_text = st.session_state.get("jd_raw_text", "")

    if parsed:
        jd_dir = parsed.get("job_type_direction", "")
        if jd_dir in DIRECTION_OPTIONS:
            default_direction_index = DIRECTION_OPTIONS.index(jd_dir)
        jd_pri = parsed.get("priority", "中")
        if jd_pri in PRIORITY_OPTIONS:
            default_priority_index = PRIORITY_OPTIONS.index(jd_pri)
        default_company = parsed.get("company", "")
        default_title = parsed.get("title", "")
        default_location = parsed.get("location", "")
        default_skills_str = ", ".join(parsed.get("skills", []))
        default_keywords_str = ", ".join(parsed.get("keywords", []))

    with st.form("add_job_form", clear_on_submit=True):
        col_left, col_right = st.columns(2)

        with col_left:
            company = st.text_input(
                "公司名称 *", placeholder="例：字节跳动",
                value=default_company, key="form_company",
            )
            title = st.text_input(
                "岗位名称 *", placeholder="例：后端开发工程师（校招）",
                value=default_title, key="form_title",
            )
            direction = st.selectbox("岗位方向", DIRECTION_OPTIONS,
                                     index=default_direction_index, key="form_direction")

        with col_right:
            location = st.text_input(
                "工作地点", placeholder="例：北京",
                value=default_location, key="form_location",
            )
            deadline_date = st.date_input("截止时间", value=None, key="form_deadline",
                                          help="留空表示暂无截止日期")
            priority = st.selectbox(
                "优先级", PRIORITY_OPTIONS, index=default_priority_index,
                format_func=lambda x: PRIORITY_LABEL[x], key="form_priority",
            )

        st.caption("💡 以下技能/标签可手动修改，用逗号分隔")
        skills_str = st.text_input(
            "技能标签",
            placeholder="例：Java, Spring Boot, MySQL, Redis",
            value=default_skills_str, key="form_skills",
        )
        keywords_str = st.text_input(
            "关键词标签",
            placeholder="例：校招, 应届, 本科及以上",
            value=default_keywords_str, key="form_keywords",
        )

        jd_text = st.text_area(
            "原始 JD 文本 *",
            placeholder="粘贴岗位描述全文...",
            value=default_jd_text,
            height=120,
            key="form_jd",
        )

        # ── Application fields ──
        st.markdown("---")
        st.markdown("#### 📤 投递信息")

        if not resumes:
            st.warning("请先前往 **Resume Vault** 添加简历版本，否则无法创建投递记录")
            resume_disabled = True
        else:
            resume_disabled = False

        c_app1, c_app2 = st.columns(2)
        with c_app1:
            resume_options_form = {r.version_name: r.id for r in resumes}
            default_resume_idx = 0
            if not resume_disabled:
                selected_resume_label_form = st.selectbox(
                    "简历版本 *", list(resume_options_form.keys()),
                    key="form_resume_select",
                )
            else:
                selected_resume_label_form = st.selectbox(
                    "简历版本 *", ["（暂无简历）"],
                    key="form_resume_select",
                )
            initial_status = st.selectbox(
                "投递状态", APPLICATION_STATUSES_V2, index=0, key="form_status",
            )
        with c_app2:
            applied_date = st.date_input(
                "投递日期", value=date.today(), key="form_applied_date",
            )

        application_url = st.text_input(
            "投递链接", placeholder="https://... 招聘官网或内推链接",
            key="form_app_url",
        )
        notes = st.text_area(
            "备注", placeholder="投递渠道、内推人、后续安排等...",
            height=60, key="form_app_notes",
        )
        termination_reason = st.text_input(
            "终止原因（仅状态为「终止」时需要填写）",
            placeholder="例：简历未通过 / 笔试未通过 / 面试未通过 / 岗位关闭 / 其他",
            key="form_term_reason",
        )

        submitted = st.form_submit_button("✅ 提交新增投递", type="primary", use_container_width=True)

        if submitted:
            errors = []
            if not company.strip():
                errors.append("公司名称不能为空")
            if not title.strip():
                errors.append("岗位名称不能为空")
            if not jd_text.strip():
                errors.append("JD 文本不能为空")
            if not resumes:
                errors.append("请先前往 Resume Vault 添加简历版本")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                # Parse skills / keywords from form (user may have edited)
                form_skills = [s.strip() for s in skills_str.split(",") if s.strip()] if skills_str.strip() else []
                form_keywords = [k.strip() for k in keywords_str.split(",") if k.strip()] if keywords_str.strip() else []

                # Build JD parsed fields
                jd_parsed = {
                    "job_type": parsed.get("job_type", "") if parsed else "",
                    "skills": form_skills,
                    "keywords": form_keywords,
                    "risk_notes": parsed.get("risk_notes", []) if parsed else [],
                }

                # Create Job
                job_id = generate_id("job")
                new_job = Job(
                    id=job_id,
                    company=company.strip(),
                    title=title.strip(),
                    status=JobStatus.INTERESTED,
                    jd_raw_text=jd_text.strip(),
                    jd_parsed_fields=jd_parsed,
                    location=location.strip(),
                    direction=direction,
                    deadline=datetime.combine(deadline_date, datetime.min.time()) if deadline_date else None,
                    priority=priority,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                store.add_job(new_job)

                # Create Application
                url = application_url.strip()
                if url and not (url.startswith("http://") or url.startswith("https://")):
                    st.warning("投递链接建议以 http:// 或 https:// 开头，已保存原值")
                final_term = termination_reason.strip() if initial_status == "终止" else ""
                resume_id = resume_options_form[selected_resume_label_form]

                new_app = Application(
                    id=generate_id("app"),
                    job_id=job_id,
                    resume_id=resume_id,
                    applied_date=datetime.combine(applied_date, datetime.min.time()) if applied_date else None,
                    current_stage=initial_status,
                    status=initial_status,
                    application_url=url,
                    termination_reason=final_term,
                    notes=notes.strip(),
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                store.add_application(new_app)

                st.session_state.pop("jd_parse_result", None)
                st.session_state.pop("jd_parse_mode", None)
                st.session_state.pop("jd_raw_text", None)
                st.success(f"✅ 已添加投递：{new_job.company} — {new_job.title} [{initial_status}]")
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════
# Toolbar
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("---")
toolbar_left, toolbar_mid, toolbar_right = st.columns([2, 2, 1])
with toolbar_left:
    view_mode = st.radio(
        "视图模式",
        ["📌 投递看板", "📋 岗位列表"],
        horizontal=True,
        key="view_mode",
    )
with toolbar_mid:
    if "看板" in view_mode or "投递" in view_mode:
        st.caption("拖拽式状态管理 — 点击状态下拉框即可更新进度，9 种状态覆盖求职全流程")
    else:
        st.caption("岗位基本信息管理 — 点击「新增投递」录入 JD 并创建投递，AI 自动解析")
with toolbar_right:
    search = st.text_input("搜索", placeholder="公司或岗位名...", label_visibility="collapsed", key="search_app")

# ── Status change handler ───────────────────────────────────────────────
# We detect status changes via individual session_state keys
for app in applications:
    change_key = f"status_change_{app.id}"
    if change_key in st.session_state and st.session_state[change_key] != app.status:
        new_status = st.session_state[change_key]
        store.update_application_status(app.id, new_status)
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# 投递看板 (Application Kanban)
# ═══════════════════════════════════════════════════════════════════════════

if "看板" in view_mode or "投递" in view_mode:
    # Map status to CSS class suffix (V2)
    STATUS_CSS = {
        "已投递": "ak-status-sent",
        "简历评估": "ak-status-pending",
        "笔试/测评": "ak-status-exam",
        "一面": "ak-status-tech1",
        "二面": "ak-status-tech2",
        "HR面": "ak-status-hr",
        "offer": "ak-status-offer",
        "终止": "ak-status-rejected",
        "放弃": "ak-status-abandoned",
    }

    # Filter applications by search
    filtered_apps = applications
    if search:
        filtered_apps = []
        for a in applications:
            job = store.get_job(a.job_id)
            if job and (search.lower() in job.company.lower() or search.lower() in job.title.lower()):
                filtered_apps.append(a)

    if not applications:
        st.info("还没有投递记录，点击上方「➕ 新增投递」开始")
    else:
        # ── Pagination (9 items per page) ──────────────────────────────
        PAGE_SIZE = 9
        total_pages = max(1, (len(filtered_apps) + PAGE_SIZE - 1) // PAGE_SIZE)
        if "kanban_page" not in st.session_state:
            st.session_state.kanban_page = 1
        # Clamp to valid range
        st.session_state.kanban_page = max(1, min(st.session_state.kanban_page, total_pages))

        start_idx = (st.session_state.kanban_page - 1) * PAGE_SIZE
        paged_apps = filtered_apps[start_idx:start_idx + PAGE_SIZE]

        # Page navigation (always visible)
        nav_cols = st.columns([1, 2, 2, 2, 1])
        with nav_cols[0]:
            if st.button("◀ 上一页", disabled=(st.session_state.kanban_page <= 1),
                         use_container_width=True, key="kanban_prev"):
                st.session_state.kanban_page -= 1
                st.rerun()
        with nav_cols[1]:
            st.caption(f"")
        with nav_cols[2]:
            if total_pages > 1:
                page_num = st.number_input(
                    "跳转页码", min_value=1, max_value=total_pages,
                    value=st.session_state.kanban_page, label_visibility="collapsed",
                    key="kanban_page_input",
                )
                if page_num != st.session_state.kanban_page:
                    st.session_state.kanban_page = page_num
        with nav_cols[3]:
            st.caption(f"第 {st.session_state.kanban_page}/{total_pages} 页 · 共 {len(filtered_apps)} 条")
        with nav_cols[4]:
            if st.button("下一页 ▶", disabled=(st.session_state.kanban_page >= total_pages),
                         use_container_width=True, key="kanban_next"):
                st.session_state.kanban_page += 1
                st.rerun()

        # Kanban: 9 columns grouped into 3 rows of 3
        status_groups = [
            APPLICATION_STATUSES_V2[0:3],  # 已投递, 简历评估, 笔试/测评
            APPLICATION_STATUSES_V2[3:6],  # 一面, 二面, HR面
            APPLICATION_STATUSES_V2[6:9],  # offer, 终止, 放弃
        ]

        for row_statuses in status_groups:
            cols = st.columns(3)
            for col, status in zip(cols, row_statuses):
                apps_in_status = [a for a in paged_apps if a.status == status]
                # Show total count across ALL apps, not just this page
                total_in_status = sum(1 for a in filtered_apps if a.status == status)
                css_class = STATUS_CSS.get(status, "")
                with col:
                    st.markdown(
                        f"<div class='ak-status-col-header {css_class}'>"
                        f"{status} · {total_in_status}</div>",
                        unsafe_allow_html=True,
                    )
                    for a in apps_in_status:
                        job = store.get_job(a.job_id)
                        resume = store.get_resume(a.resume_id)
                        if not job:
                            continue

                        # Match score (use existing or compute on the fly)
                        if resume:
                            match_result = store.get_match_result_by_job_resume(job.id, resume.id)
                            if match_result:
                                match_score = match_result.match_score
                            else:
                                try:
                                    mr = calculate_match_rule_based(job, resume)
                                    match_score = mr.match_score
                                except Exception:
                                    match_score = None
                        else:
                            match_score = None

                        # Score display
                        if match_score is not None:
                            if match_score >= 75:
                                score_class = "ak-score-high"
                            elif match_score >= 50:
                                score_class = "ak-score-mid"
                            else:
                                score_class = "ak-score-low"
                            score_str = f"<span class='ak-score {score_class}'>{match_score:.0f}分</span>"
                        else:
                            score_str = '<span style="color:#aaa;">未分析</span>'

                        # Next action from planner
                        plan = generate_next_action(a, job, resume)
                        next_action = plan.get("next_action", "—")
                        reason = plan.get("reason", "")
                        urgency = plan.get("urgency", "低")
                        # Truncate for card display
                        if len(next_action) > 18:
                            next_action = next_action[:18] + "..."
                        if len(reason) > 30:
                            reason = reason[:30] + "..."

                        # Urgency badge
                        urgency_color = {"高": "#ea4335", "中": "#f9a825", "低": "#80868b"}
                        uc = urgency_color.get(urgency, "#80868b")
                        urgency_html = (
                            f"<span style='color:{uc};font-weight:700;font-size:10px;'>"
                            f"● {urgency}紧急</span>"
                        )

                        resume_name = resume.version_name if resume else "—"

                        # Build URL display
                        url_html = ""
                        if a.application_url:
                            url_html = (
                                f"🔗 <a href='{a.application_url}' target='_blank' "
                                f"style='font-size:11px;color:#1967d2;'>投递链接</a><br>"
                            )

                        # Termination reason display
                        term_html = ""
                        if a.status == "终止" and a.termination_reason:
                            term_html = (
                                f"<span style='font-size:10px;color:#c62828;'>"
                                f"终止原因：{a.termination_reason}</span><br>"
                            )

                        # Date display: three time nodes
                        date_parts = []
                        if a.applied_date:
                            date_parts.append(f"📅 投递 {a.applied_date.strftime('%m-%d')}")
                        if a.interview_date:
                            date_parts.append(f"🎤 面试 {a.interview_date.strftime('%m-%d')}")
                        if a.termination_date:
                            date_parts.append(f"✕ 终止 {a.termination_date.strftime('%m-%d')}")
                        date_str = " | ".join(date_parts) if date_parts else "—"

                        # Notes display
                        notes_html = ""
                        if a.notes:
                            notes_display = a.notes[:50] + "..." if len(a.notes) > 50 else a.notes
                            notes_html = (
                                f"<div style='background:#fff9c4;border-left:3px solid #f9a825;"
                                f"padding:3px 8px;border-radius:4px;margin:3px 0;font-size:11px;"
                                f"color:#5d4037;line-height:1.4;'>📝 {notes_display}</div>"
                            )

                        # Status change selectbox
                        try:
                            current_idx = APPLICATION_STATUSES_V2.index(status)
                        except ValueError:
                            current_idx = 0
                        new_status = st.selectbox(
                            "状态",
                            APPLICATION_STATUSES_V2,
                            index=current_idx,
                            key=f"status_change_{a.id}",
                            label_visibility="collapsed",
                        )

                        # Application card with edit/delete buttons
                        st.markdown(
                            f"<div class='app-kanban-card'>"
                            f"<div class='ak-company'>{job.company}</div>"
                            f"<div class='ak-title'>{job.title}</div>"
                            f"<div class='ak-meta'>"
                            f"📄 {resume_name}<br>"
                            f"{date_str}<br>"
                            f"{notes_html}"
                            f"{score_str}<br>"
                            f"→ {next_action}<br>"
                            f"{url_html}"
                            f"{term_html}"
                            f"<span style='font-size:10px;color:#80868b;' title='{reason}'>{reason}</span>"
                            f"</div>"
                            f"<div style='margin-top:4px;'>{urgency_html}</div>"
                            f"</div>",
                            unsafe_allow_html=True,
                        )

                        # Inline edit/delete expander
                        with st.expander("✏️ 编辑 / 🗑 删除", expanded=False):
                            st.markdown("**岗位信息**")
                            jc1, jc2 = st.columns(2)
                            with jc1:
                                new_company = st.text_input(
                                    "公司名称", value=job.company,
                                    key=f"inline_company_{a.id}",
                                )
                                try:
                                    dir_idx = DIRECTION_OPTIONS.index(job.direction) if job.direction in DIRECTION_OPTIONS else 0
                                except ValueError:
                                    dir_idx = 0
                                new_direction = st.selectbox(
                                    "岗位方向", DIRECTION_OPTIONS,
                                    index=dir_idx,
                                    key=f"inline_direction_{a.id}",
                                )
                            with jc2:
                                new_title = st.text_input(
                                    "岗位名称", value=job.title,
                                    key=f"inline_title_{a.id}",
                                )
                                try:
                                    pri_idx = PRIORITY_OPTIONS.index(job.priority) if job.priority in PRIORITY_OPTIONS else 1
                                except ValueError:
                                    pri_idx = 1
                                new_priority = st.selectbox(
                                    "优先级", PRIORITY_OPTIONS,
                                    index=pri_idx,
                                    format_func=lambda x: PRIORITY_LABEL[x],
                                    key=f"inline_priority_{a.id}",
                                )
                            new_location = st.text_input(
                                "工作地点", value=job.location or "",
                                key=f"inline_location_{a.id}",
                            )

                            st.markdown("---")
                            st.markdown("**投递信息**")

                            ac1, ac2 = st.columns(2)
                            with ac1:
                                resume_options_inline = {r.version_name: r.id for r in resumes}
                                current_resume_name = None
                                for rname, rid in resume_options_inline.items():
                                    if rid == a.resume_id:
                                        current_resume_name = rname
                                        break
                                new_resume_label = st.selectbox(
                                    "简历版本",
                                    list(resume_options_inline.keys()),
                                    index=list(resume_options_inline.keys()).index(current_resume_name) if current_resume_name else 0,
                                    key=f"inline_resume_{a.id}",
                                )
                                try:
                                    status_idx = APPLICATION_STATUSES_V2.index(a.status)
                                except ValueError:
                                    status_idx = 0
                                new_status = st.selectbox(
                                    "投递状态", APPLICATION_STATUSES_V2,
                                    index=status_idx,
                                    key=f"inline_status_{a.id}",
                                )
                            with ac2:
                                a_date = a.applied_date.date() if a.applied_date else date.today()
                                new_date = st.date_input(
                                    "投递日期", value=a_date,
                                    key=f"inline_date_{a.id}",
                                )

                            ac3, ac4 = st.columns(2)
                            with ac3:
                                i_date = a.interview_date.date() if a.interview_date else None
                                new_interview_date = st.date_input(
                                    "面试时间", value=i_date,
                                    key=f"inline_interview_date_{a.id}",
                                    help="进入面试环节的日期（留空表示未进入面试）",
                                )
                            with ac4:
                                t_date = a.termination_date.date() if a.termination_date else None
                                new_termination_date = st.date_input(
                                    "终止时间", value=t_date,
                                    key=f"inline_termination_date_{a.id}",
                                    help="终止投递的日期（留空表示未终止）",
                                )

                            new_url = st.text_input(
                                "投递链接", value=a.application_url or "",
                                placeholder="https://... 招聘官网或内推链接",
                                key=f"inline_url_{a.id}",
                            )
                            new_notes = st.text_area(
                                "备注", value=a.notes or "",
                                height=60, key=f"inline_notes_{a.id}",
                            )
                            new_term_reason = st.text_input(
                                "终止原因（仅状态为「终止」时需要填写）",
                                value=a.termination_reason or "",
                                placeholder="例：简历未通过 / 笔试未通过 / 面试未通过 / 岗位关闭 / 其他",
                                key=f"inline_term_{a.id}",
                            )

                            # ── Save ──
                            if st.button("💾 保存修改", type="primary", use_container_width=True, key=f"inline_save_{a.id}"):
                                url = new_url.strip()
                                if url and not (url.startswith("http://") or url.startswith("https://")):
                                    st.warning("投递链接建议以 http:// 或 https:// 开头，已保存原值")
                                final_term = new_term_reason.strip() if new_status == "终止" else ""

                                # Update job
                                job.company = new_company.strip()
                                job.title = new_title.strip()
                                job.direction = new_direction
                                job.priority = new_priority
                                job.location = new_location.strip()
                                store.update_job(job)

                                # Update application
                                # Only save termination_date when status is 终止
                                term_dt = None
                                if new_status == "终止" and new_termination_date is not None:
                                    term_dt = datetime.combine(new_termination_date, datetime.min.time())
                                # Only save interview_date when in interview stages
                                interview_stages = {"笔试/测评", "一面", "二面", "HR面"}
                                interview_dt = None
                                if new_status in interview_stages and new_interview_date is not None:
                                    interview_dt = datetime.combine(new_interview_date, datetime.min.time())
                                app_fields = {
                                    "resume_id": resume_options_inline[new_resume_label],
                                    "status": new_status,
                                    "applied_date": datetime.combine(new_date, datetime.min.time()) if new_date else None,
                                    "interview_date": interview_dt,
                                    "termination_date": term_dt,
                                    "application_url": url,
                                    "notes": new_notes.strip(),
                                    "termination_reason": final_term,
                                }
                                ok, msg = store.update_application(a.id, app_fields)
                                if ok:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)

                            # ── Delete ──
                            st.markdown("---")
                            st.markdown("⚠️ **删除投递记录**")
                            del_confirm = st.checkbox(
                                "我确认要删除此投递记录",
                                key=f"inline_del_confirm_{a.id}",
                            )
                            if st.button("🗑 确认删除", disabled=not del_confirm, use_container_width=True, key=f"inline_delete_{a.id}"):
                                ok, msg = store.delete_application(a.id)
                                if ok:
                                    st.success(msg)
                                    st.rerun()
                                else:
                                    st.error(msg)

# ═══════════════════════════════════════════════════════════════════════════
# 岗位列表 (Job List)
# ═══════════════════════════════════════════════════════════════════════════

else:
    filtered_jobs = [j for j in jobs if search.lower() in j.company.lower() or search.lower() in j.title.lower()] if search else jobs

    # ── Pagination for job list (9 per page) ──────────────────────
    LIST_PAGE_SIZE = 9
    list_total_pages = max(1, (len(filtered_jobs) + LIST_PAGE_SIZE - 1) // LIST_PAGE_SIZE)
    if "list_page" not in st.session_state:
        st.session_state.list_page = 1
    st.session_state.list_page = max(1, min(st.session_state.list_page, list_total_pages))
    list_start = (st.session_state.list_page - 1) * LIST_PAGE_SIZE
    paged_jobs = filtered_jobs[list_start:list_start + LIST_PAGE_SIZE]

    # Page navigation
    lnav_cols = st.columns([1, 2, 2, 2, 1])
    with lnav_cols[0]:
        if st.button("◀ 上一页", disabled=(st.session_state.list_page <= 1),
                     use_container_width=True, key="list_prev"):
            st.session_state.list_page -= 1
            st.rerun()
    with lnav_cols[1]:
        st.caption(f"")
    with lnav_cols[2]:
        if list_total_pages > 1:
            lpage_num = st.number_input(
                "跳转页码", min_value=1, max_value=list_total_pages,
                value=st.session_state.list_page, label_visibility="collapsed",
                key="list_page_input",
            )
            if lpage_num != st.session_state.list_page:
                st.session_state.list_page = lpage_num
    with lnav_cols[3]:
        st.caption(f"第 {st.session_state.list_page}/{list_total_pages} 页 · 共 {len(filtered_jobs)} 个岗位")
    with lnav_cols[4]:
        if st.button("下一页 ▶", disabled=(st.session_state.list_page >= list_total_pages),
                     use_container_width=True, key="list_next"):
            st.session_state.list_page += 1
            st.rerun()

    if filtered_jobs:
        for j in paged_jobs:
            # Count applications for this job
            job_apps = [a for a in applications if a.job_id == j.id]
            app_count = len(job_apps)
            tags_html = " ".join([f'<span class="tag">{t}</span>' for t in j.tags])
            if j.direction:
                tags_html = f'<span class="tag" style="background:#e8f0fe;color:#1967d2;">{j.direction}</span> ' + tags_html
            priority_class = {"高": "priority-high", "中": "priority-medium", "低": "priority-low"}.get(j.priority, "")
            priority_str = f'<span class="{priority_class}">{PRIORITY_LABEL.get(j.priority, j.priority)}</span>' if j.priority else ""
            deadline_str = ""
            if j.deadline:
                days_left = (j.deadline.date() - date.today()).days
                if days_left < 0:
                    deadline_str = f" | ⏰ 已过期"
                elif days_left <= 3:
                    deadline_str = f" | ⏰ <span style='color:#ea4335;'>{days_left}天后截止</span>"
                else:
                    deadline_str = f" | ⏰ {j.deadline.strftime('%m-%d')} 截止"
            app_str = f" | 📤 {app_count} 次投递" if app_count > 0 else ""
            st.markdown(
                f"<div class='job-card'>"
                f"<span class='company'>{j.company}</span>"
                f"<div class='title'>{j.title}</div>"
                f"<div class='meta'>📍 {j.location or '—'} | 🕐 {j.updated_at.strftime('%m-%d %H:%M')}{deadline_str}{app_str} | {priority_str}</div>"
                f"<div class='tags'>{tags_html}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # Show applications for this job with inline edit/delete
            if job_apps:
                for a in job_apps:
                    resume = store.get_resume(a.resume_id)
                    resume_name = resume.version_name if resume else "—"
                    date_str = a.applied_date.strftime("%Y-%m-%d") if a.applied_date else "—"

                    # Status badge color
                    status_color_map = {
                        "已投递": "#e65100", "简历评估": "#1967d2", "笔试/测评": "#f9a825",
                        "一面": "#7b1fa2", "二面": "#6a1b9a", "HR面": "#00838f",
                        "offer": "#2e7d32", "终止": "#c62828", "放弃": "#546e7a",
                    }
                    sc = status_color_map.get(a.status, "#80868b")

                    # Application summary line
                    col_info, col_expand = st.columns([4, 1])
                    with col_info:
                        url_link = f" [🔗]({a.application_url})" if a.application_url else ""
                        st.markdown(
                            f"📌 **{a.status}** | 📄 {resume_name} | 📅 {date_str}{url_link}",
                        )
                        if a.notes:
                            st.caption(f"📝 {a.notes[:60]}{'...' if len(a.notes) > 60 else ''}")
                        if a.status == "终止" and a.termination_reason:
                            st.caption(f"⚠️ 终止原因：{a.termination_reason}")
                    with col_expand:
                        # Small inline expander for edit/delete
                        pass

                    with st.expander("✏️ 编辑 / 🗑 删除", expanded=False):
                        st.markdown("**岗位信息**")
                        jc1, jc2 = st.columns(2)
                        with jc1:
                            new_company = st.text_input(
                                "公司名称", value=j.company,
                                key=f"list_company_{a.id}",
                            )
                            try:
                                dir_idx = DIRECTION_OPTIONS.index(j.direction) if j.direction in DIRECTION_OPTIONS else 0
                            except ValueError:
                                dir_idx = 0
                            new_direction = st.selectbox(
                                "岗位方向", DIRECTION_OPTIONS,
                                index=dir_idx,
                                key=f"list_direction_{a.id}",
                            )
                        with jc2:
                            new_title = st.text_input(
                                "岗位名称", value=j.title,
                                key=f"list_title_{a.id}",
                            )
                            try:
                                pri_idx = PRIORITY_OPTIONS.index(j.priority) if j.priority in PRIORITY_OPTIONS else 1
                            except ValueError:
                                pri_idx = 1
                            new_priority = st.selectbox(
                                "优先级", PRIORITY_OPTIONS,
                                index=pri_idx,
                                format_func=lambda x: PRIORITY_LABEL[x],
                                key=f"list_priority_{a.id}",
                            )
                        new_location = st.text_input(
                            "工作地点", value=j.location or "",
                            key=f"list_location_{a.id}",
                        )

                        st.markdown("---")
                        st.markdown("**投递信息**")

                        ac1, ac2 = st.columns(2)
                        with ac1:
                            resume_opts = {r.version_name: r.id for r in resumes}
                            cur_resume = None
                            for rname, rid in resume_opts.items():
                                if rid == a.resume_id:
                                    cur_resume = rname
                                    break
                            new_resume_label = st.selectbox(
                                "简历版本",
                                list(resume_opts.keys()),
                                index=list(resume_opts.keys()).index(cur_resume) if cur_resume else 0,
                                key=f"list_resume_{a.id}",
                            )
                            try:
                                status_idx = APPLICATION_STATUSES_V2.index(a.status)
                            except ValueError:
                                status_idx = 0
                            new_status = st.selectbox(
                                "投递状态", APPLICATION_STATUSES_V2,
                                index=status_idx,
                                key=f"list_status_{a.id}",
                            )
                        with ac2:
                            a_date = a.applied_date.date() if a.applied_date else date.today()
                            new_date = st.date_input(
                                "投递日期", value=a_date,
                                key=f"list_date_{a.id}",
                            )

                        ac3, ac4 = st.columns(2)
                        with ac3:
                            i_date = a.interview_date.date() if a.interview_date else None
                            new_interview_date = st.date_input(
                                "面试时间", value=i_date,
                                key=f"list_interview_date_{a.id}",
                                help="进入面试环节的日期（留空表示未进入面试）",
                            )
                        with ac4:
                            t_date = a.termination_date.date() if a.termination_date else None
                            new_termination_date = st.date_input(
                                "终止时间", value=t_date,
                                key=f"list_termination_date_{a.id}",
                                help="终止投递的日期（留空表示未终止）",
                            )

                        new_url = st.text_input(
                            "投递链接", value=a.application_url or "",
                            placeholder="https://... 招聘官网或内推链接",
                            key=f"list_url_{a.id}",
                        )
                        new_notes = st.text_area(
                            "备注", value=a.notes or "",
                            height=60, key=f"list_notes_{a.id}",
                        )
                        new_term_reason = st.text_input(
                            "终止原因（仅状态为「终止」时需要填写）",
                            value=a.termination_reason or "",
                            placeholder="例：简历未通过 / 笔试未通过 / 面试未通过 / 岗位关闭 / 其他",
                            key=f"list_term_{a.id}",
                        )

                        # ── Save ──
                        if st.button("💾 保存修改", type="primary", use_container_width=True, key=f"list_save_{a.id}"):
                            url = new_url.strip()
                            if url and not (url.startswith("http://") or url.startswith("https://")):
                                st.warning("投递链接建议以 http:// 或 https:// 开头，已保存原值")
                            final_term = new_term_reason.strip() if new_status == "终止" else ""

                            j.company = new_company.strip()
                            j.title = new_title.strip()
                            j.direction = new_direction
                            j.priority = new_priority
                            j.location = new_location.strip()
                            store.update_job(j)

                            # Only save termination_date when status is 终止
                            term_dt = None
                            if new_status == "终止" and new_termination_date is not None:
                                term_dt = datetime.combine(new_termination_date, datetime.min.time())
                            # Only save interview_date when in interview stages
                            interview_stages = {"笔试/测评", "一面", "二面", "HR面"}
                            interview_dt = None
                            if new_status in interview_stages and new_interview_date is not None:
                                interview_dt = datetime.combine(new_interview_date, datetime.min.time())
                            app_fields = {
                                "resume_id": resume_opts[new_resume_label],
                                "status": new_status,
                                "applied_date": datetime.combine(new_date, datetime.min.time()) if new_date else None,
                                "interview_date": interview_dt,
                                "termination_date": term_dt,
                                "application_url": url,
                                "notes": new_notes.strip(),
                                "termination_reason": final_term,
                            }
                            ok, msg = store.update_application(a.id, app_fields)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

                        # ── Delete ──
                        st.markdown("---")
                        st.markdown("⚠️ **删除投递记录**")
                        del_confirm = st.checkbox(
                            "我确认要删除此投递记录",
                            key=f"list_del_confirm_{a.id}",
                        )
                        if st.button("🗑 确认删除", disabled=not del_confirm, use_container_width=True, key=f"list_delete_{a.id}"):
                            ok, msg = store.delete_application(a.id)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
    else:
        st.info("没有匹配的岗位")


# ═══════════════════════════════════════════════════════════════════════════
# Stats bar
# ═══════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("投递统计")

# Show count per application status (V2)
stat_cols = st.columns(3)
status_counts = {s: 0 for s in APPLICATION_STATUSES_V2}
for a in applications:
    status_counts[a.status] = status_counts.get(a.status, 0) + 1

# Row 1: total / resume_review / exam
with stat_cols[0]:
    st.metric("📌 投递总数", len(applications))
with stat_cols[1]:
    st.metric(f"📌 {APPLICATION_STATUSES_V2[1]}", status_counts.get(APPLICATION_STATUSES_V2[1], 0))
with stat_cols[2]:
    st.metric(f"📌 {APPLICATION_STATUSES_V2[2]}", status_counts.get(APPLICATION_STATUSES_V2[2], 0))

# Row 2: interviews
stat_cols2 = st.columns(3)
for idx, (sc, status) in enumerate(zip(stat_cols2, APPLICATION_STATUSES_V2[3:6])):
    with sc:
        st.metric(f"🎤 {status}", status_counts.get(status, 0))

# Row 3: offer / terminated / abandoned
stat_cols3 = st.columns(3)
for idx, (sc, status) in enumerate(zip(stat_cols3, APPLICATION_STATUSES_V2[6:9])):
    with sc:
        st.metric(f"📋 {status}", status_counts.get(status, 0))
