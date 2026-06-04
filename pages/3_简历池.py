import streamlit as st
import os
from datetime import datetime
from pathlib import Path

from core.data_store import store
from core.models import ResumeVersion
from core.utils import generate_id

st.set_page_config(page_title="简历池 - OfferPilot", page_icon="📄", layout="wide")

from core.auth import require_login
if not require_login():
    st.stop()

# ── Constants ──────────────────────────────────────────────────────────
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "data" / "resumes"
ALLOWED_TYPES = ["pdf", "docx", "txt"]
DIRECTION_OPTIONS = ["后端", "前端", "算法", "数据", "产品", "设计", "运营", "客户端", "安全", "其他", "不限"]

# ── CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.resume-card {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    padding: 20px 24px;
    height: 100%;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: box-shadow 0.2s;
}
.resume-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.10); }
.resume-card .version-name { font-size: 18px; font-weight: 700; color: #202124; margin-bottom: 4px; }
.resume-card .resume-meta { font-size: 12px; color: #5f6368; margin-bottom: 12px; }
.resume-card .section-title {
    font-size: 10px; font-weight: 700; text-transform: uppercase;
    color: #80868b; letter-spacing: 0.5px; margin: 14px 0 6px 0;
}
.keyword-tag {
    display: inline-block;
    background: #e8f0fe;
    color: #1967d2;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 500;
    margin: 2px 4px 2px 0;
}
.direction-tag {
    display: inline-block;
    background: #e8f5e9;
    color: #2e7d32;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
    margin: 2px 4px 2px 0;
}
.resume-tag {
    display: inline-block;
    background: #f1f3f4;
    color: #5f6368;
    padding: 1px 8px;
    border-radius: 4px;
    font-size: 11px;
    margin-right: 4px;
}
.stat-mini {
    display: inline-block;
    text-align: center;
    min-width: 60px;
    margin-right: 16px;
}
.stat-mini .num { font-size: 22px; font-weight: 800; color: #202124; }
.stat-mini .lbl { font-size: 10px; color: #80868b; }
.highlight-item {
    font-size: 12px;
    color: #5f6368;
    margin: 2px 0;
    padding-left: 8px;
    border-left: 2px solid #e0e0e0;
}
.file-badge {
    display: inline-block;
    background: #f1f3f4;
    color: #5f6368;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-family: monospace;
}
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────
st.title("简历池")
st.caption("多版本简历管理 — 为不同岗位方向维护专属简历，精准投递")

# ═══════════════════════════════════════════════════════════════════════
# 新增简历版本 Form
# ═══════════════════════════════════════════════════════════════════════

with st.expander("➕ 新增简历版本", expanded=False):
    with st.form("add_resume_form", clear_on_submit=True):
        col_left, col_right = st.columns(2)

        with col_left:
            version_name = st.text_input(
                "简历版本名称 *",
                placeholder="例：后端开发-中文 / 算法工程师-AI方向",
                key="form_resume_name",
            )
            target_direction = st.selectbox(
                "适用岗位方向",
                DIRECTION_OPTIONS,
                index=len(DIRECTION_OPTIONS) - 1,  # default to "不限"
                key="form_resume_direction",
            )

        with col_right:
            uploaded_file = st.file_uploader(
                "上传简历文件",
                type=ALLOWED_TYPES,
                key="form_resume_file",
                help="支持 PDF、DOCX、TXT 格式",
            )
            keywords_str = st.text_input(
                "核心关键词",
                placeholder="用逗号分隔，例：Python, Java, Go, Redis",
                key="form_resume_keywords",
            )

        highlights_str = st.text_area(
            "项目亮点",
            placeholder="每行一个亮点，例：\n分布式KV存储系统 · 支持10万QPS\n基于Go的微服务网关 · 日均处理千万请求",
            height=80,
            key="form_resume_highlights",
        )

        submitted = st.form_submit_button("✅ 提交新增", type="primary", use_container_width=True)

        if submitted:
            # ── Validation ──────────────────────────────────────────
            errors = []
            if not version_name.strip():
                errors.append("简历版本名称不能为空")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                # ── Save uploaded file ──────────────────────────────
                resume_id = generate_id("resume")
                file_path = ""

                if uploaded_file is not None:
                    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
                    ext = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else "bin"
                    saved_name = f"{resume_id}_{uploaded_file.name}"
                    saved_path = UPLOAD_DIR / saved_name
                    with open(saved_path, "wb") as fh:
                        fh.write(uploaded_file.getbuffer())
                    file_path = str(saved_path)

                # ── Parse keywords ──────────────────────────────────
                keywords = [k.strip() for k in keywords_str.split(",") if k.strip()] if keywords_str.strip() else []

                # ── Parse highlights ────────────────────────────────
                highlights = [h.strip() for h in highlights_str.strip().split("\n") if h.strip()]

                # ── Create ResumeVersion ────────────────────────────
                resume = ResumeVersion(
                    id=resume_id,
                    version_name=version_name.strip(),
                    file_path=file_path,
                    target_direction=target_direction,
                    keywords=keywords,
                    highlights=highlights,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                store.add_resume(resume)
                st.success(f"✅ 已添加：{resume.version_name}")
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════
# Resume cards
# ═══════════════════════════════════════════════════════════════════════

# ── Stats bar above cards ────────────────────────────────────────────
apps = store.get_all_applications()
interviews = store.get_all_interviews()

# Build interview count per application
app_interview_counts: dict[str, int] = {}
for iv in interviews:
    app_interview_counts[iv.application_id] = app_interview_counts.get(iv.application_id, 0) + 1

# Aggregate per resume
resume_usage: dict[str, int] = {}       # app count
resume_interview_count: dict[str, int] = {}  # interview count
for a in apps:
    resume_usage[a.resume_id] = resume_usage.get(a.resume_id, 0) + 1
    iv_count = app_interview_counts.get(a.id, 0)
    if iv_count:
        resume_interview_count[a.resume_id] = resume_interview_count.get(a.resume_id, 0) + iv_count

# ── Display ────────────────────────────────────────────────────────────
resumes = store.get_all_resumes()
st.caption(f"共 {len(resumes)} 个简历版本 — 每个版本可关联不同岗位方向")

if resumes:
    cols = st.columns(len(resumes))
    for idx, r in enumerate(resumes):
        with cols[idx]:
            # Keyword tags
            keywords_html = " ".join(
                [f'<span class="keyword-tag">{kw}</span>' for kw in r.keywords]
            ) if r.keywords else '<span style="font-size:12px;color:#aaa;">暂无</span>'

            # Direction tag
            direction_html = ""
            if r.target_direction and r.target_direction != "不限":
                direction_html = f'<span class="direction-tag">{r.target_direction}</span>'

            # Tags (legacy)
            tags_html = " ".join([f'<span class="resume-tag">{t}</span>' for t in r.tags])

            # File info
            file_info = "未上传文件"
            fname_display = ""
            if r.file_path:
                fname = Path(r.file_path).name if r.file_path else ""
                if "_" in fname and fname.startswith(r.id):
                    fname_display = fname[len(r.id) + 1:]
                else:
                    fname_display = fname
                file_info = f'<span class="file-badge">📎 {fname_display}</span>'

            # Usage stats
            use_count = resume_usage.get(r.id, 0)
            iv_count = resume_interview_count.get(r.id, 0)

            # Highlights
            highlights_html = ""
            if r.highlights:
                highlights_html = "".join(
                    [f'<div class="highlight-item">{h}</div>' for h in r.highlights]
                )
            else:
                highlights_html = '<span style="font-size:12px;color:#aaa;">暂无</span>'

            # Build card
            st.markdown(
                f"<div class='resume-card'>"
                # Header
                f"<div class='version-name'>{r.version_name}</div>"
                f"<div class='resume-meta'>{file_info} | 更新于 {r.updated_at.strftime('%Y-%m-%d')}</div>"
                # Tags row
                f"<div>{direction_html} {tags_html}</div>"
                # Usage stats
                f"<div style='margin-top:12px;'>"
                f"<div class='stat-mini'><div class='num'>{use_count}</div><div class='lbl'>投递次数</div></div>"
                f"<div class='stat-mini'><div class='num'>{iv_count}</div><div class='lbl'>面试次数</div></div>"
                f"</div>"
                # Keywords
                f"<div class='section-title'>🔑 核心关键词</div>"
                f"<div>{keywords_html}</div>"
                # Highlights
                f"<div class='section-title'>🚀 项目亮点</div>"
                f"<div>{highlights_html}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

            # ── Preview expander ────────────────────────────────────
            with st.expander("👁 预览", expanded=False):
                if not r.file_path:
                    st.info("该简历未上传文件")
                else:
                    fpath = Path(r.file_path)
                    if not fpath.exists():
                        st.warning("文件不存在或已移动")
                    else:
                        fsize = fpath.stat().st_size
                        st.caption(f"文件：{fpath.name}  ·  {fsize / 1024:.1f} KB")

                        # Use resume_viewer for text extraction
                        from services.resume_viewer import (
                            extract_text, get_file_type, preview_status,
                        )

                        preview = preview_status(str(fpath))
                        if preview["ok"] and preview["text"]:
                            file_type = get_file_type(str(fpath))
                            if file_type == "txt":
                                st.text_area(
                                    "文本内容", value=preview["text"], height=300,
                                    key=f"preview_txt_{r.id}", disabled=True,
                                )
                            else:
                                # PDF / DOCX — show extracted text
                                st.text_area(
                                    f"{file_type.upper()} 文本内容（自动提取）",
                                    value=preview["text"], height=300,
                                    key=f"preview_txt_{r.id}", disabled=True,
                                )
                                st.caption(
                                    "文本为自动提取，格式可能与原文件有差异。"
                                )
                        elif not preview["ok"]:
                            st.info(preview["reason"])

                        # Download button (always available)
                        try:
                            with open(fpath, "rb") as fh:
                                st.download_button(
                                    "⬇️ 下载原文件",
                                    data=fh.read(),
                                    file_name=fpath.name,
                                    mime="application/octet-stream",
                                    key=f"dl_{r.id}",
                                )
                        except Exception as ex:
                            st.error(f"无法读取文件用于下载：{ex}")

            # ── Edit / Delete expander ──────────────────────────────
            with st.expander("✏️ 编辑 / 🗑 删除", expanded=False):
                st.markdown("**编辑简历信息**")
                e1, e2 = st.columns(2)
                with e1:
                    new_name = st.text_input(
                        "简历版本名称", value=r.version_name,
                        key=f"resume_name_{r.id}",
                    )
                with e2:
                    try:
                        dir_idx = DIRECTION_OPTIONS.index(r.target_direction) if r.target_direction in DIRECTION_OPTIONS else len(DIRECTION_OPTIONS) - 1
                    except ValueError:
                        dir_idx = len(DIRECTION_OPTIONS) - 1
                    new_direction = st.selectbox(
                        "适用岗位方向", DIRECTION_OPTIONS,
                        index=dir_idx,
                        key=f"resume_direction_{r.id}",
                    )

                new_keywords_str = st.text_input(
                    "核心关键词（逗号分隔）",
                    value=", ".join(r.keywords) if r.keywords else "",
                    placeholder="例：Python, Java, Go, Redis",
                    key=f"resume_keywords_{r.id}",
                )
                new_highlights_str = st.text_area(
                    "项目亮点（每行一个）",
                    value="\n".join(r.highlights) if r.highlights else "",
                    placeholder="例：\n分布式KV存储系统 · 支持10万QPS\n基于Go的微服务网关",
                    height=80,
                    key=f"resume_highlights_{r.id}",
                )

                if st.button("💾 保存修改", type="primary", use_container_width=True,
                             key=f"save_resume_{r.id}"):
                    keywords = [k.strip() for k in new_keywords_str.split(",") if k.strip()]
                    highlights = [h.strip() for h in new_highlights_str.strip().split("\n") if h.strip()]
                    fields = {
                        "version_name": new_name.strip(),
                        "target_direction": new_direction,
                        "keywords": keywords,
                        "highlights": highlights,
                    }
                    ok, msg = store.update_resume(r.id, fields)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

                # ── Delete section ──────────────────────────────────
                st.markdown("---")
                st.markdown("⚠️ **删除简历版本**")
                ref_count = store.get_resume_application_count(r.id)
                if ref_count > 0:
                    st.warning(
                        f"该简历已被 **{ref_count}** 条投递记录使用，暂不能删除。"
                        f"请先修改或删除相关投递记录。"
                    )
                else:
                    del_confirm = st.checkbox(
                        "我确认要删除此简历版本（不可恢复）",
                        key=f"del_resume_confirm_{r.id}",
                    )
                    if st.button("🗑 确认删除", disabled=not del_confirm,
                                 use_container_width=True, key=f"del_resume_{r.id}"):
                        ok, msg = store.delete_resume(r.id)
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
else:
    st.info("还没有简历版本，点击上方「➕ 新增简历版本」开始")

# ═══════════════════════════════════════════════════════════════════════
# Summary stats bar
# ═══════════════════════════════════════════════════════════════════════

st.divider()
st.subheader("简历使用统计")

total_apps = len(apps)
total_interviews = len(interviews)
total_resumes = len(resumes)

s1, s2, s3, s4 = st.columns(4)
with s1:
    st.metric("简历版本数", total_resumes)
with s2:
    st.metric("总投递次数", total_apps)
with s3:
    st.metric("总面试次数", total_interviews)
with s4:
    top_resume = max(resume_usage, key=resume_usage.get) if resume_usage else None
    top_name = store.get_resume(top_resume).version_name if top_resume else "—"
    st.metric("最常用简历", top_name)
