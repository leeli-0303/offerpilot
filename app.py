import streamlit as st

st.set_page_config(
    page_title="OfferPilot — 首页",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Auth gate ──────────────────────────────────────────────────────────
from core.auth import require_login, logout_user, is_logged_in, get_current_user_id
from core.data_store import store

if not require_login():
    st.stop()

uid = get_current_user_id()

# ── Sidebar: user info ─────────────────────────────────────────────────
user_profile = store.get_user_profile(uid)
with st.sidebar:
    if user_profile:
        name = user_profile.display_name or user_profile.username or "求职者"
        st.markdown(f"👤 **{name}**")
        if user_profile.school:
            st.caption(f"🏫 {user_profile.school} · {user_profile.major or '—'}")
        if user_profile.target_directions:
            st.caption(f"🎯 {' / '.join(user_profile.target_directions)}")
    if st.button("🚪 退出登录", use_container_width=True):
        logout_user()
        st.rerun()

# ── CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.hero {
    background: linear-gradient(135deg, #1a73e8 0%, #0d47a1 100%);
    color: #fff;
    border-radius: 16px;
    padding: 48px 56px;
    margin-bottom: 32px;
}
.hero .eyebrow {
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 2px;
    opacity: 0.7;
    margin-bottom: 8px;
}
.hero h1 {
    font-size: 44px;
    font-weight: 800;
    margin: 0 0 8px 0;
    color: #fff;
    line-height: 1.2;
}
.hero .subtitle {
    font-size: 18px;
    opacity: 0.9;
    margin: 0 0 24px 0;
    line-height: 1.5;
}
.hero .hero-cta {
    display: inline-block;
    background: #fff;
    color: #1a73e8;
    padding: 8px 20px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 600;
    text-decoration: none;
}
.feature-card {
    background: #fff;
    border: 1px solid #e8eaed;
    border-radius: 12px;
    padding: 24px 20px;
    height: 100%;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: box-shadow 0.2s, transform 0.15s;
}
.feature-card:hover {
    box-shadow: 0 6px 20px rgba(0,0,0,0.10);
    transform: translateY(-2px);
}
.feature-card .icon {
    font-size: 32px;
    margin-bottom: 10px;
}
.feature-card .title {
    font-size: 16px;
    font-weight: 700;
    color: #202124;
    margin-bottom: 8px;
}
.feature-card .desc {
    font-size: 13px;
    color: #5f6368;
    line-height: 1.6;
}
.feature-card .badge-row {
    margin-top: 12px;
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
}
.feature-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 500;
}
.badge-ai  { background: #e8f0fe; color: #1967d2; }
.badge-rule { background: #f3e5f5; color: #7b1fa2; }
.how-it-works {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 28px 32px;
    margin: 24px 0;
    border: 1px solid #e8eaed;
}
.how-it-works .step-num {
    display: inline-block;
    width: 28px;
    height: 28px;
    line-height: 28px;
    border-radius: 50%;
    background: #1a73e8;
    color: #fff;
    text-align: center;
    font-size: 14px;
    font-weight: 700;
    margin-right: 8px;
}
.how-it-works .step-text {
    font-size: 14px;
    color: #202124;
}
</style>
""", unsafe_allow_html=True)

# ── Hero ───────────────────────────────────────────────────────────────
st.markdown(
    "<div class='hero'>"
    "<div class='eyebrow'>AI-Powered Job Hunting Assistant</div>"
    "<h1>OfferPilot</h1>"
    "<p class='subtitle'>"
    "从 JD 录入到 Offer 决策，一站式管理求职全流程。<br>"
    "AI 做信息提取和策略分析，你专注准备和面试。"
    "</p>"
    "</div>",
    unsafe_allow_html=True,
)

# ── How it works ──────────────────────────────────────────────────────
st.markdown("### 求职管理三步走")
steps_cols = st.columns(3)
with steps_cols[0]:
    st.markdown(
        "<div class='how-it-works' style='text-align:center;'>"
        "<div style='font-size:32px;margin-bottom:8px;'>📋</div>"
        "<div style='font-weight:700;font-size:16px;margin-bottom:6px;'>1. 录入 & 解析</div>"
        "<div style='font-size:13px;color:#5f6368;'>粘贴 JD，AI 自动提取<br>公司、技能和岗位方向</div>"
        "</div>",
        unsafe_allow_html=True,
    )
with steps_cols[1]:
    st.markdown(
        "<div class='how-it-works' style='text-align:center;'>"
        "<div style='font-size:32px;margin-bottom:8px;'>🔬</div>"
        "<div style='font-weight:700;font-size:16px;margin-bottom:6px;'>2. 匹配 & 投递</div>"
        "<div style='font-size:13px;color:#5f6368;'>AI 量化匹配度，<br>优先投递把握最大的岗位</div>"
        "</div>",
        unsafe_allow_html=True,
    )
with steps_cols[2]:
    st.markdown(
        "<div class='how-it-works' style='text-align:center;'>"
        "<div style='font-size:32px;margin-bottom:8px;'>📈</div>"
        "<div style='font-weight:700;font-size:16px;margin-bottom:6px;'>3. 追踪 & 复盘</div>"
        "<div style='font-size:13px;color:#5f6368;'>看板管理进度，<br>每周 AI 策略复盘</div>"
        "</div>",
        unsafe_allow_html=True,
    )

# ── Feature Cards ──────────────────────────────────────────────────────
st.markdown("### 功能导航")
st.caption("在左侧侧边栏选择页面，或点击下方卡片直接进入")

features = [
    ("📊", "概览", "求职总览", "投递统计、面试日程、AI 行动建议一览"),
    ("💼", "投递池", "岗位 & 投递管理", "JD 智能解析 · 9 状态看板 · 进度追踪"),
    ("📄", "简历池", "多版本简历", "按岗位方向维护多版简历 · 关键词和亮点管理"),
    ("🔬", "匹配分析", "AI 匹配分析", "岗位 vs 简历量化评分 · 差距分析 · 优化建议"),
    ("🎤", "面试准备", "面试准备", "个性化面试题生成 · STAR 技巧 · 反问建议"),
    ("📋", "求职复盘", "策略复盘", "数据统计 · AI 策略分析 · 下周计划 · 导出"),
]

cols = st.columns(3)
for i, (icon, title, subtitle, desc) in enumerate(features):
    with cols[i % 3]:
        st.markdown(
            f"<div class='feature-card'>"
            f"<div class='icon'>{icon}</div>"
            f"<div class='title'>{title}</div>"
            f"<div style='font-size:12px;color:#80868b;margin-bottom:4px;'>{subtitle}</div>"
            f"<div class='desc'>{desc}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

# ── User Profile ──────────────────────────────────────────────────────
st.divider()
st.subheader("👤 个人设置")

from core.models import UserProfile

profile = store.get_user_profile(uid)
if profile is None:
    profile = UserProfile(id=uid)

with st.expander("编辑个人资料", expanded=False):
    with st.form("profile_form"):
        p1, p2 = st.columns(2)
        with p1:
            display_name = st.text_input(
                "昵称", value=profile.display_name,
                placeholder="如何称呼你？",
            )
            school = st.text_input(
                "学校", value=profile.school,
                placeholder="例：北京大学",
            )
            degree = st.selectbox(
                "学历", ["", "本科", "硕士", "博士"],
                index=(["", "本科", "硕士", "博士"].index(profile.degree)
                        if profile.degree in ["本科", "硕士", "博士"] else 0),
            )
        with p2:
            major = st.text_input(
                "专业", value=profile.major,
                placeholder="例：计算机科学与技术",
            )
            graduation_year = st.text_input(
                "毕业年份", value=profile.graduation_year,
                placeholder="例：2026",
            )

        direction_options = ["后端", "前端", "算法", "数据", "产品", "设计", "运营", "客户端", "安全"]
        current_dirs = [d for d in profile.target_directions if d in direction_options]
        target_directions = st.multiselect(
            "意向方向", direction_options, default=current_dirs,
        )
        target_cities_str = st.text_input(
            "意向城市（逗号分隔）", value=", ".join(profile.target_cities),
            placeholder="例：北京, 上海, 深圳",
        )
        bio = st.text_area(
            "个人简介", value=profile.bio,
            placeholder="简单介绍一下自己...",
            height=80,
        )

        # Password change
        st.markdown("---")
        st.caption("修改密码（留空则不修改）")
        pw1, pw2 = st.columns(2)
        with pw1:
            new_pwd = st.text_input("新密码", type="password", placeholder="至少 4 位")
        with pw2:
            confirm_pwd = st.text_input("确认新密码", type="password", placeholder="再次输入")

        submitted = st.form_submit_button("💾 保存设置", type="primary", use_container_width=True)
        if submitted:
            if new_pwd and len(new_pwd) < 4:
                st.error("密码至少需要 4 位字符")
            elif new_pwd and new_pwd != confirm_pwd:
                st.error("两次输入的密码不一致")
            else:
                from core.auth import hash_password
                profile.display_name = display_name.strip()
                profile.school = school.strip()
                profile.major = major.strip()
                profile.degree = degree
                profile.graduation_year = graduation_year.strip()
                profile.target_directions = target_directions
                profile.target_cities = [c.strip() for c in target_cities_str.split(",") if c.strip()]
                profile.bio = bio.strip()
                if new_pwd:
                    profile.password_hash = hash_password(new_pwd)
                store.save_user_profile(profile)
                st.success("设置已保存！")
                st.rerun()

# ── AI Model Configuration ──────────────────────────────────────────────
st.divider()
st.subheader("🤖 AI 模型配置")
st.caption("配置你自己的大模型 API，不配置则使用系统默认设置")

# Load current user LLM settings
llm_settings = profile.llm_settings if profile else {}
current_mode = llm_settings.get("mode", "mock")
current_api_key = llm_settings.get("api_key", "")
current_base_url = llm_settings.get("base_url", "")
current_model = llm_settings.get("model_name", "")
current_temp = float(llm_settings.get("temperature", 0.3))
current_max_tokens = int(llm_settings.get("max_tokens", 2048))

# Preset providers
PRESETS = {
    "智谱 (GLM)": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "model_name": "glm-4-air",
    },
    "DeepSeek": {
        "base_url": "https://api.deepseek.com/v1",
        "model_name": "deepseek-chat",
    },
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "model_name": "gpt-4o",
    },
}

with st.expander("🤖 AI 模型配置", expanded=False):
    # Determine effective values: session state presets override saved settings
    eff_base_url = st.session_state.get("_preset_base_url", current_base_url)
    eff_model = st.session_state.get("_preset_model", current_model)

    col1, col2 = st.columns(2)

    with col1:
        mode = st.selectbox(
            "运行模式",
            options=["mock", "real"],
            index=0 if current_mode == "mock" else 1,
            help="mock = 使用模拟数据（无需 API）; real = 调用真实大模型 API",
        )

        api_key = st.text_input(
            "API Key",
            value=current_api_key,
            type="password",
            placeholder="请输入你的 API Key",
            help="在模型提供商的开放平台获取",
        )

        base_url = st.text_input(
            "Base URL",
            value=eff_base_url,
            placeholder="https://api.openai.com/v1",
            help="OpenAI 兼容的 API 端点地址",
        )

        model_name = st.text_input(
            "模型名称",
            value=eff_model,
            placeholder="例如: gpt-4o, deepseek-chat, glm-4-air",
        )

    with col2:
        st.caption("快捷预设（点击填入）")
        preset_cols = st.columns(len(PRESETS))
        for i, (label, preset) in enumerate(PRESETS.items()):
            with preset_cols[i]:
                if st.button(label, use_container_width=True, key=f"preset_{i}"):
                    st.session_state._preset_base_url = preset["base_url"]
                    st.session_state._preset_model = preset["model_name"]
                    st.rerun()

        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=current_temp,
            step=0.05,
            help="生成随机性：0 = 确定性，1 = 高创造性",
        )

        max_tokens = st.number_input(
            "Max Tokens",
            min_value=256,
            max_value=8192,
            value=current_max_tokens,
            step=256,
            help="单次回复最大 token 数",
        )

    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])

    with btn_col1:
        if st.button("🔗 测试连接", use_container_width=True):
            if mode == "mock":
                st.info("Mock 模式无需测试连接")
            elif not api_key:
                st.error("请先填写 API Key")
            else:
                from services.llm_client import _call_real
                with st.spinner("正在测试 API 连接..."):
                    test_result = _call_real(
                        "请用中文回复：你好，请确认你能正常回复。只用回复'连接成功，模型为 [你的模型名]'即可。",
                        system_prompt="你是一个API测试助手。请简短回复。",
                        config_overrides={
                            "api_key": api_key.strip(),
                            "base_url": base_url.strip(),
                            "model_name": model_name.strip(),
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                        },
                    )
                if test_result.startswith("❌"):
                    st.error(f"连接失败：\n\n{test_result}")
                else:
                    st.success(f"连接成功！\n\n模型回复：{test_result}")

    with btn_col2:
        if st.button("💾 保存配置", type="primary", use_container_width=True):
            settings = {
                "mode": mode,
                "api_key": api_key.strip(),
                "base_url": base_url.strip(),
                "model_name": model_name.strip(),
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            store.save_llm_settings(settings)
            # Also update the profile cache
            if profile:
                profile.llm_settings = settings
            # Clear preset session state
            st.session_state.pop("_preset_base_url", None)
            st.session_state.pop("_preset_model", None)
            st.success("AI 配置已保存！")
            st.rerun()

# ── Footer ─────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "OfferPilot MVP — 面向应届生的 AI 求职管理工具 | "
    "在左侧侧边栏选择页面开始使用 | "
    "默认 Mock 模式，设置 LLM_MODE=real 可接入真实 AI"
)
