import streamlit as st
from datetime import datetime

from core.data_store import store
from core.models import InterviewJournal, PrepNote
from core.utils import generate_id
from services.interview_prep import generate_interview_prep, generate_interview_prep_with_llm
from services.llm_client import get_llm_config

st.set_page_config(page_title="面试准备 - OfferPilot", page_icon="🎤", layout="wide")

from core.auth import require_login
if not require_login():
    st.stop()

# ── CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.interview-card {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.interview-card.upcoming {
    border-left: 4px solid #ea4335;
    background: #fff5f5;
}
.interview-card.past {
    border-left: 4px solid #2e7d32;
}
.round-badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 700;
}
.round-past { background: #e8f5e9; color: #2e7d32; }
.round-upcoming { background: #fce4ec; color: #c62828; }
.rating-stars {
    color: #fbbc04;
    font-size: 16px;
    letter-spacing: 2px;
}
.feedback-box {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 14px 16px;
    margin-top: 10px;
    font-size: 13px;
    color: #5f6368;
}
.prep-section {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 16px 20px;
    margin: 12px 0;
    border: 1px solid #e0e0e0;
}
.prep-section h4 {
    margin: 0 0 8px 0;
    font-size: 15px;
    color: #202124;
}
.prep-item {
    padding: 6px 10px;
    margin: 3px 0;
    border-radius: 6px;
    font-size: 13px;
    line-height: 1.5;
}
.prep-question {
    background: #e8f0fe;
    border-left: 3px solid #1967d2;
}
.prep-counter {
    background: #e8f5e9;
    border-left: 3px solid #2e7d32;
}
.prep-experience {
    background: #fff3e0;
    border-left: 3px solid #e65100;
}
.prep-tip {
    background: #f3e5f5;
    border-left: 3px solid #7b1fa2;
}
.app-info-card {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 12px;
}
.app-info-card .info-label {
    font-size: 11px;
    color: #80868b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.app-info-card .info-value {
    font-size: 15px;
    font-weight: 600;
    color: #202124;
}
/* Formatting toolbar (injected by JS) */
.fmt-toolbar {
    display: flex; gap: 2px; padding: 4px 0; margin-top: 2px;
}
.fmt-toolbar button {
    padding: 3px 10px; border: 1px solid #d0d0d0; border-radius: 4px;
    background: #fff; cursor: pointer; font-size: 13px;
    color: #333; line-height: 1.4;
}
.fmt-toolbar button:hover { background: #e8e8e8; border-color: #b0b0b0; }
.fmt-toolbar button.fmt-bold { font-weight: bold; }
.fmt-toolbar button.fmt-highlight { background: #FFEB3B; border-color: #FDD835; }
.fmt-toolbar button.fmt-highlight:hover { background: #FDD835; }
.fmt-toolbar .fmt-hint {
    font-size: 11px; color: #999; margin-left: 4px; line-height: 2.2;
}
</style>
""", unsafe_allow_html=True)

# ── JavaScript: Formatting toolbar for textareas ─────────────────────────
st.markdown("""
<script>
(function() {
    if (window.__fmtToolbarInstalled) return;
    window.__fmtToolbarInstalled = true;

    function enhanceTextareas() {
        document.querySelectorAll('textarea').forEach(function(ta) {
            if (ta.dataset.fmtEnhanced) return;
            ta.dataset.fmtEnhanced = '1';

            var toolbar = document.createElement('div');
            toolbar.className = 'fmt-toolbar';
            toolbar.innerHTML = '<button class="fmt-bold" title="加粗 Ctrl+B">B</button>'
                + '<button class="fmt-highlight" title="高亮">H</button>'
                + '<button title="缩进">\\u21B3</button>'
                + '<span class="fmt-hint">选中文字后点击按钮</span>';

            ta.parentNode.insertBefore(toolbar, ta);

            toolbar.querySelectorAll('button').forEach(function(btn, idx) {
                btn.addEventListener('mousedown', function(e) {
                    e.preventDefault();
                    var start = ta.selectionStart;
                    var end = ta.selectionEnd;
                    var text = ta.value;
                    var selected = text.substring(start, end) || '文本';

                    var replacement, cursorOffset;
                    if (idx === 0) {
                        replacement = '**' + selected + '**';
                        cursorOffset = 2;
                    } else if (idx === 1) {
                        replacement = '<mark>' + selected + '</mark>';
                        cursorOffset = 6;
                    } else {
                        replacement = '> ' + selected;
                        cursorOffset = 2;
                    }

                    ta.value = text.substring(0, start) + replacement + text.substring(end);
                    var newPos = start + replacement.length;
                    if (start !== end) {
                        ta.selectionStart = start + cursorOffset;
                        ta.selectionEnd = newPos - cursorOffset;
                    } else {
                        ta.selectionStart = ta.selectionEnd = newPos;
                    }
                    ta.dispatchEvent(new Event('input', {bubbles: true}));
                    ta.focus();
                });
            });
        });
    }

    enhanceTextareas();
    var observer = new MutationObserver(function() {
        enhanceTextareas();
    });
    observer.observe(document.body, {childList: true, subtree: true});
})();
</script>
""", unsafe_allow_html=True)

# ── Helpers ──────────────────────────────────────────────────────────────

def _has_formatting(text: str) -> bool:
    """Check if text contains markdown/HTML formatting markers."""
    import re
    return bool(re.search(r'\*\*|<mark>|<b>|<i>|^> |^\- |^\d+\. ', text, re.MULTILINE))


def _render_content(content: str, css_class: str = "", extra_style: str = ""):
    """Render journal content — markdown if formatted, plain text with pre-wrap if not."""
    if not content:
        return
    if _has_formatting(content):
        st.markdown(content, unsafe_allow_html=True)
    else:
        style = "white-space:pre-wrap;" + extra_style
        st.markdown(
            f"<div class='{css_class}' style='{style}'>{content}</div>",
            unsafe_allow_html=True,
        )

# ── Data ───────────────────────────────────────────────────────────────
applications = store.get_all_applications()
interviews = store.get_all_interviews()
now = datetime.now()

# ═══════════════════════════════════════════════════════════════════════════
# Section 1: Interview Prep Generator
# ═══════════════════════════════════════════════════════════════════════════

st.title("面试准备")
st.caption("AI 面试准备包 — 基于岗位要求和简历项目，生成个性化面试准备内容")

if not applications:
    st.info("还没有投递记录，请先前往 Job Tracker 创建投递记录")
else:
    # ── Application selector ──────────────────────────────────────────
    app_options = {}
    for a in applications:
        job = store.get_job(a.job_id)
        resume = store.get_resume(a.resume_id)
        if job:
            label = f"{job.company} — {job.title} [{a.status}]"
            app_options[label] = a.id

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        if not app_options:
            st.info("当前投递记录缺少关联岗位信息，请检查投递池")
            st.stop()
        selected_label = st.selectbox(
            "选择投递记录", list(app_options.keys()), key="prep_select_app",
        )
        selected_app_id = app_options[selected_label]
    with c2:
        prep_mode = st.radio(
            "生成模式", ["🔧 规则生成", "🤖 AI 生成"],
            key="prep_mode", horizontal=True,
        )
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        generate_clicked = st.button(
            "🎯 生成面试准备包", type="primary", use_container_width=True,
        )

    # ── Load selected data ────────────────────────────────────────────
    app = store.get_application(selected_app_id)
    if app:
        job = store.get_job(app.job_id)
        resume = store.get_resume(app.resume_id) if app.resume_id else None

        if job:
            # ── Application info card ────────────────────────────────
            st.markdown("---")
            info_cols = st.columns(4)
            with info_cols[0]:
                st.markdown(
                    f"<div class='app-info-card'>"
                    f"<div class='info-label'>公司</div>"
                    f"<div class='info-value'>{job.company}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with info_cols[1]:
                st.markdown(
                    f"<div class='app-info-card'>"
                    f"<div class='info-label'>岗位</div>"
                    f"<div class='info-value' style='font-size:13px;'>{job.title}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with info_cols[2]:
                resume_name = resume.version_name if resume else "—"
                st.markdown(
                    f"<div class='app-info-card'>"
                    f"<div class='info-label'>简历版本</div>"
                    f"<div class='info-value' style='font-size:13px;'>{resume_name}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            with info_cols[3]:
                st.markdown(
                    f"<div class='app-info-card'>"
                    f"<div class='info-label'>当前状态</div>"
                    f"<div class='info-value' style='font-size:13px;'>{app.status}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            # ── AI disclaimer ─────────────────────────────────────
            use_ai = (prep_mode == "🤖 AI 生成")
            if use_ai:
                llm_cfg = get_llm_config()
                if llm_cfg["mode"] == "mock":
                    st.info(
                        "**AI 生成说明**：AI 建议仅基于当前简历记录和岗位 JD，"
                        "不应编造不存在的经历。当前为 Mock 模式，显示预设示例数据。"
                    )
                else:
                    st.info(
                        "**AI 生成说明**：AI 建议仅基于当前简历记录和岗位 JD，"
                        "不应编造不存在的经历。所有生成内容仅供准备参考，"
                        "请根据真实经历修改回答。"
                    )

            # ── Status warning ───────────────────────────────────────
            interview_statuses = {"一面", "二面", "HR面", "笔试/测评", "简历评估"}
            if app.status not in interview_statuses:
                st.info(
                    f"当前状态为「{app.status}」，尚未进入面试阶段。"
                    f"以下是提前准备的面试内容，建议收藏备用。"
                )

            # ── Generate prep package ─────────────────────────────────
            if generate_clicked:
                with st.spinner("正在生成面试准备包..."):
                    try:
                        if use_ai:
                            prep = generate_interview_prep_with_llm(app, job, resume)
                        else:
                            prep = generate_interview_prep(app, job, resume)
                    except Exception as exc:
                        st.error(f"生成面试准备包失败：{exc}")
                        import traceback
                        with st.expander("🔧 错误详情（调试用）"):
                            st.code(traceback.format_exc())
                        st.stop()

                st.divider()

                # ── Mode badge ──────────────────────────────────────────
                if use_ai:
                    llm_cfg = get_llm_config()
                    mode_label = "🤖 AI 生成" if llm_cfg["mode"] == "mock" else "🤖 AI 生成（真实模型）"
                else:
                    mode_label = "🔧 规则生成"
                st.subheader(f"🎯 面试准备包  —  {mode_label}")

                # ── Fallback warning ──────────────────────────────────
                if use_ai and prep.get("_fallback"):
                    reason = prep.get("_fallback_reason", "")
                    st.warning(
                        f"⚠️ AI 生成失败，已自动回退到规则生成。\n\n"
                        f"原因：{reason}\n\n"
                        f"当前显示的是规则生成结果，如需 AI 生成请稍后重试。"
                    )

                # ── Raw LLM output (debug) ────────────────────────────
                if use_ai:
                    raw_output = prep.get("_raw_output", "")
                    if raw_output:
                        with st.expander("🔍 查看 AI 原始输出（调试用）"):
                            st.code(raw_output, language="json")

                # Job summary
                st.markdown("#### 📋 岗位要求摘要")
                st.markdown(
                    f"<div class='prep-section'>"
                    f"<p style='font-size:13px;color:#5f6368;margin:0;'>{prep['job_summary']}</p>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                # Key experiences
                st.markdown("#### 🚀 重点强调的经历")
                for exp in prep["key_experiences"]:
                    st.markdown(
                        f"<div class='prep-item prep-experience'>{exp}</div>",
                        unsafe_allow_html=True,
                    )

                # Likely questions
                st.markdown("#### ❓ 可能被问到的 5 个问题")
                for i, q in enumerate(prep["likely_questions"], 1):
                    st.markdown(
                        f"<div class='prep-item prep-question'>"
                        f"<b>Q{i}.</b> {q}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                # Counter questions
                st.markdown("#### 💬 建议反问面试官的 3 个问题")
                for i, q in enumerate(prep["counter_questions"], 1):
                    st.markdown(
                        f"<div class='prep-item prep-counter'>"
                        f"<b>{i}.</b> {q}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                # Prep tips
                st.markdown("#### 📝 面试准备小贴士")
                for tip in prep["prep_tips"]:
                    st.markdown(
                        f"<div class='prep-item prep-tip'>💡 {tip}</div>",
                        unsafe_allow_html=True,
                    )

            elif not generate_clicked:
                st.info("👆 点击上方「生成面试准备包」按钮，获取个性化面试准备内容")


# ═══════════════════════════════════════════════════════════════════════════
# Section 2: Interview Journal (manual entry)
# ═══════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("📋 面试复盘记录")
st.caption("手动记录每次面试的复盘，包括面试体验、被问到的问题和自我总结")

# ── Initialize edit state ─────────────────────────────────────────────────
if "editing_journal_id" not in st.session_state:
    st.session_state.editing_journal_id = None

# ── Build job options for the selector ─────────────────────────────────
job_options_list = []
for a in applications:
    job = store.get_job(a.job_id)
    if job:
        label = f"{job.company} — {job.title}"
        job_options_list.append(label)

# ── Add Journal Form (only show when NOT editing) ─────────────────────────
if not st.session_state.editing_journal_id:
    with st.expander("➕ 添加面试复盘记录", expanded=False):
        with st.form("add_interview_journal_form", clear_on_submit=True):
            jc1, jc2 = st.columns(2)
            with jc1:
                # Let user either select from applications or type custom
                selected_job = st.selectbox(
                    "选择投递记录（可选）",
                    ["（手动输入）"] + job_options_list,
                    key="journal_select_job",
                )
                if selected_job and selected_job != "（手动输入）":
                    # Pre-fill from application
                    default_position = selected_job
                    # Find the application to get status
                    for a in applications:
                        job = store.get_job(a.job_id)
                        if job and f"{job.company} — {job.title}" == selected_job:
                            default_round = a.status if a.status in ("一面", "二面", "HR面", "笔试/测评") else ""
                            break
                    else:
                        default_round = ""
                else:
                    default_position = ""
                    default_round = ""

                job_position = st.text_input(
                    "岗位（部门 + 岗位名称）",
                    value=default_position,
                    placeholder="如：技术中台 — 后端开发工程师",
                    key="journal_position",
                )
                round_options = ["", "笔试/测评", "群面", "一面", "二面", "三面", "HR面", "终面"]
                round_progress = st.selectbox(
                    "面试进度",
                    round_options,
                    index=0 if not default_round else (round_options.index(default_round) if default_round in round_options else 0),
                    key="journal_round",
                )
            with jc2:
                interview_date = st.date_input(
                    "面试日期",
                    value=datetime.now().date(),
                    key="journal_date",
                )

            st.markdown("---")
            experience = st.text_area(
                "面试体验",
                placeholder="面试整体感受如何？面试官态度怎么样？面试流程是否顺畅？氛围如何？",
                height=200,
                key="journal_experience",
            )
            questions_asked = st.text_area(
                "被问到的问题",
                placeholder="面试中问了哪些技术题、算法题、行为面试题？分别是怎么回答的？哪些答得好，哪些答得不好？",
                height=250,
                key="journal_questions",
            )
            summary = st.text_area(
                "总结反思",
                placeholder="这次面试最大的收获是什么？暴露了哪些不足？下次面试前需要重点准备什么？",
                height=250,
                key="journal_summary",
            )

            submitted = st.form_submit_button("💾 保存面试复盘", type="primary", use_container_width=True)
            if submitted:
                if not job_position.strip():
                    st.error("请至少填写「岗位」字段")
                else:
                    journal = InterviewJournal(
                        id=generate_id("journal"),
                        job_position=job_position.strip(),
                        round_progress=round_progress,
                        interview_date=datetime.combine(interview_date, datetime.min.time()) if interview_date else None,
                        experience=experience.strip(),
                        questions_asked=questions_asked.strip(),
                        summary=summary.strip(),
                    )
                    store.add_interview_journal(journal)
                    st.success(f"面试复盘「{job_position.strip()}」已保存！")
                    st.rerun()

# ── Edit Journal Form (only show when editing) ────────────────────────────
if st.session_state.editing_journal_id:
    edit_journal = store.get_interview_journal(st.session_state.editing_journal_id)
    if edit_journal:
        with st.expander("✏️ 编辑面试复盘记录", expanded=True):
            with st.form("edit_interview_journal_form", clear_on_submit=True):
                ejc1, ejc2 = st.columns(2)
                with ejc1:
                    edit_job_position = st.text_input(
                        "岗位（部门 + 岗位名称）",
                        value=edit_journal.job_position,
                        placeholder="如：技术中台 — 后端开发工程师",
                        key="edit_journal_position",
                    )
                    edit_round_options = ["", "笔试/测评", "群面", "一面", "二面", "三面", "HR面", "终面"]
                    edit_default_index = 0
                    if edit_journal.round_progress in edit_round_options:
                        edit_default_index = edit_round_options.index(edit_journal.round_progress)
                    edit_round_progress = st.selectbox(
                        "面试进度",
                        edit_round_options,
                        index=edit_default_index,
                        key="edit_journal_round",
                    )
                with ejc2:
                    edit_interview_date = st.date_input(
                        "面试日期",
                        value=edit_journal.interview_date.date() if edit_journal.interview_date else datetime.now().date(),
                        key="edit_journal_date",
                    )

                st.markdown("---")
                edit_experience = st.text_area(
                    "面试体验",
                    value=edit_journal.experience,
                    placeholder="面试整体感受如何？面试官态度怎么样？面试流程是否顺畅？氛围如何？",
                    height=200,
                    key="edit_journal_experience",
                )
                edit_questions_asked = st.text_area(
                    "被问到的问题",
                    value=edit_journal.questions_asked,
                    placeholder="面试中问了哪些技术题、算法题、行为面试题？分别是怎么回答的？哪些答得好，哪些答得不好？",
                    height=250,
                    key="edit_journal_questions",
                )
                edit_summary = st.text_area(
                    "总结反思",
                    value=edit_journal.summary,
                    placeholder="这次面试最大的收获是什么？暴露了哪些不足？下次面试前需要重点准备什么？",
                    height=250,
                    key="edit_journal_summary",
                )

                col1, col2 = st.columns(2)
                with col1:
                    update_submitted = st.form_submit_button("💾 更新面试复盘", type="primary", use_container_width=True)
                with col2:
                    cancel_edit = st.form_submit_button("取消编辑", use_container_width=True)

                if update_submitted:
                    if not edit_job_position.strip():
                        st.error("请至少填写「岗位」字段")
                    else:
                        edit_journal.job_position = edit_job_position.strip()
                        edit_journal.round_progress = edit_round_progress
                        edit_journal.interview_date = datetime.combine(edit_interview_date, datetime.min.time()) if edit_interview_date else None
                        edit_journal.experience = edit_experience.strip()
                        edit_journal.questions_asked = edit_questions_asked.strip()
                        edit_journal.summary = edit_summary.strip()
                        store.update_interview_journal(edit_journal)
                        st.session_state.editing_journal_id = None
                        st.success(f"面试复盘「{edit_job_position.strip()}」已更新！")
                        st.rerun()

                if cancel_edit:
                    st.session_state.editing_journal_id = None
                    st.rerun()

# ── Display existing journals ─────────────────────────────────────────
journals = store.get_all_interview_journals()

if journals:
    for j in journals:
        date_str = j.interview_date.strftime("%Y-%m-%d") if j.interview_date else "日期未记录"
        with st.expander(
            f"{'🎯' if j.round_progress else '📝'} {j.job_position} · {date_str}"
            f"{' · ' + j.round_progress if j.round_progress else ''}"
        ):
            # Meta info
            meta_cols = st.columns(3)
            with meta_cols[0]:
                if j.round_progress:
                    st.caption(f"进度：{j.round_progress}")
            with meta_cols[1]:
                st.caption(f"日期：{date_str}")
            with meta_cols[2]:
                st.caption(f"记录于：{j.created_at.strftime('%Y-%m-%d %H:%M') if j.created_at else '—'}")

            # Experience
            if j.experience:
                st.markdown("**💬 面试体验**")
                _render_content(j.experience, "feedback-box")

            # Questions asked
            if j.questions_asked:
                st.markdown("**❓ 被问到的问题**")
                _render_content(j.questions_asked, "prep-section")

            # Summary
            if j.summary:
                st.markdown("**📝 总结反思**")
                _render_content(j.summary, "prep-section", "border-left:3px solid #2e7d32;")

            # Edit and Delete buttons
            btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 4])
            with btn_col1:
                if st.button("✏️ 编辑", key=f"edit_journal_{j.id}"):
                    st.session_state.editing_journal_id = j.id
                    st.rerun()
            with btn_col2:
                if st.button("🗑️ 删除", key=f"del_journal_{j.id}", type="secondary"):
                    success, msg = store.delete_interview_journal(j.id)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
else:
    st.info("还没有面试复盘记录。点击上方「➕ 添加面试复盘记录」开始记录你的面试经历。")


# ═══════════════════════════════════════════════════════════════════════════
# Section 3: Interview Prep Notes (manual preparation records)
# ═══════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("📝 面试准备记录")
st.caption("记录你平时的面试准备内容，如知识点总结、常见题整理、项目话术草稿等")

# ── Initialize edit state ─────────────────────────────────────────────────
if "editing_prep_note_id" not in st.session_state:
    st.session_state.editing_prep_note_id = None

# ── Add PrepNote Form ──────────────────────────────────────────────────
if not st.session_state.editing_prep_note_id:
    with st.expander("➕ 添加面试准备记录", expanded=False):
        with st.form("add_prep_note_form", clear_on_submit=True):
            pn1, pn2 = st.columns([1, 2])
            with pn1:
                note_date = st.date_input(
                    "记录日期", value=datetime.now().date(), key="prep_note_date",
                )
            with pn2:
                note_topic = st.text_input(
                    "记录主题", placeholder="如：Java 并发编程常见面试题整理",
                    key="prep_note_topic",
                )
            note_content = st.text_area(
                "详细内容",
                placeholder="在这里写下你的面试准备内容、知识点总结、回答话术草稿...",
                height=300,
                key="prep_note_content",
            )
            submitted = st.form_submit_button("💾 保存准备记录", type="primary", use_container_width=True)
            if submitted:
                if not note_topic.strip():
                    st.error("请至少填写「记录主题」")
                else:
                    prep_note = PrepNote(
                        id=generate_id("prepnote"),
                        date=datetime.combine(note_date, datetime.min.time()) if note_date else None,
                        topic=note_topic.strip(),
                        content=note_content.strip(),
                    )
                    store.add_prep_note(prep_note)
                    st.success(f"面试准备记录「{note_topic.strip()}」已保存！")
                    st.rerun()

# ── Edit PrepNote Form ──────────────────────────────────────────────────
if st.session_state.editing_prep_note_id:
    edit_note = store.get_prep_note(st.session_state.editing_prep_note_id)
    if edit_note:
        with st.expander("✏️ 编辑面试准备记录", expanded=True):
            with st.form("edit_prep_note_form", clear_on_submit=True):
                epn1, epn2 = st.columns([1, 2])
                with epn1:
                    edit_note_date = st.date_input(
                        "记录日期",
                        value=edit_note.date.date() if edit_note.date else datetime.now().date(),
                        key="edit_prep_note_date",
                    )
                with epn2:
                    edit_note_topic = st.text_input(
                        "记录主题",
                        value=edit_note.topic,
                        placeholder="如：Java 并发编程常见面试题整理",
                        key="edit_prep_note_topic",
                    )
                edit_note_content = st.text_area(
                    "详细内容",
                    value=edit_note.content,
                    placeholder="在这里写下你的面试准备内容、知识点总结、回答话术草稿...",
                    height=300,
                    key="edit_prep_note_content",
                )
                col1, col2 = st.columns(2)
                with col1:
                    update_submitted = st.form_submit_button("💾 更新记录", type="primary", use_container_width=True)
                with col2:
                    cancel_edit = st.form_submit_button("取消编辑", use_container_width=True)

                if update_submitted:
                    if not edit_note_topic.strip():
                        st.error("请至少填写「记录主题」")
                    else:
                        edit_note.date = datetime.combine(edit_note_date, datetime.min.time()) if edit_note_date else None
                        edit_note.topic = edit_note_topic.strip()
                        edit_note.content = edit_note_content.strip()
                        store.update_prep_note(edit_note)
                        st.session_state.editing_prep_note_id = None
                        st.success(f"面试准备记录「{edit_note_topic.strip()}」已更新！")
                        st.rerun()

                if cancel_edit:
                    st.session_state.editing_prep_note_id = None
                    st.rerun()

# ── Display existing prep notes ─────────────────────────────────────────
prep_notes = store.get_all_prep_notes()

if prep_notes:
    for pn in prep_notes:
        date_str = pn.date.strftime("%Y-%m-%d") if pn.date else "日期未记录"
        with st.expander(f"📝 {pn.topic} · {date_str}"):
            st.caption(f"记录日期：{date_str}  |  创建于：{pn.created_at.strftime('%Y-%m-%d %H:%M') if pn.created_at else '—'}")
            if pn.content:
                _render_content(pn.content, "prep-section", "border-left:3px solid #1a73e8;")

            btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 4])
            with btn_col1:
                if st.button("✏️ 编辑", key=f"edit_prep_note_{pn.id}"):
                    st.session_state.editing_prep_note_id = pn.id
                    st.rerun()
            with btn_col2:
                if st.button("🗑️ 删除", key=f"del_prep_note_{pn.id}", type="secondary"):
                    success, msg = store.delete_prep_note(pn.id)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
else:
    st.info("还没有面试准备记录。点击上方「➕ 添加面试准备记录」开始整理你的面试准备资料。")


# ═══════════════════════════════════════════════════════════════════════════
# Stats bar
# ═══════════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("面试统计")

interview_statuses = {"一面", "二面", "HR面", "笔试/测评", "简历评估"}
upcoming_apps = [a for a in applications if a.status in interview_statuses]
past_apps = [a for a in applications if a.status in ("offer", "终止", "放弃")]

s1, s2, s3, s4 = st.columns(4)
with s1:
    st.metric("投递总数", len(applications))
with s2:
    st.metric("面试中", len(upcoming_apps))
with s3:
    st.metric("复盘记录", len(journals))
with s4:
    offers = len([a for a in applications if a.status == "offer"])
    st.metric("已获 Offer", offers)
