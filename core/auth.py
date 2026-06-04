"""Multi-user authentication for OfferPilot.

Uses SHA-256 hashed passwords stored in the SQLite users table.
Session state tracks login status via ``st.session_state``.
"""

import hashlib
import os
import streamlit as st

SESSION_AUTH_KEY = "_offerpilot_authenticated"
SESSION_USER_ID_KEY = "_offerpilot_user_id"


# ── Password helpers ─────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Return a SHA-256 hex digest of *password* (salted with a fixed pepper)."""
    pepper = os.environ.get("LLM_API_KEY", "offerpilot-default-pepper")[:16]
    return hashlib.sha256((pepper + password).encode("utf-8")).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    """Check *password* against *stored_hash*."""
    return hash_password(password) == stored_hash


# ── Session helpers ──────────────────────────────────────────────────────

def is_logged_in() -> bool:
    return st.session_state.get(SESSION_AUTH_KEY, False)


def get_current_user_id() -> str:
    """Return the current logged-in user's ID, or empty string if not logged in."""
    return st.session_state.get(SESSION_USER_ID_KEY, "")


def login_user(user_id: str):
    st.session_state[SESSION_AUTH_KEY] = True
    st.session_state[SESSION_USER_ID_KEY] = user_id
    # Wire up the data store to this user
    from core.data_store import store
    store.set_current_user(user_id)


def logout_user():
    st.session_state[SESSION_AUTH_KEY] = False
    st.session_state.pop(SESSION_USER_ID_KEY, None)


# ── Gate ─────────────────────────────────────────────────────────────────

def require_login():
    """Call at the top of every protected page. Redirects to login if needed.

    Returns True when the user is authenticated, False when the login
    form was rendered (caller should ``st.stop()``).
    """
    if is_logged_in():
        # Restore user context on store (needed after server restart)
        uid = get_current_user_id()
        if uid:
            from core.data_store import store
            store.set_current_user(uid)
            return True
        else:
            # Invalid state: authenticated flag set but no user_id
            # Clear the stale session and fall through to login form
            logout_user()

    from core.data_store import store

    # ── CSS ────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    .login-container {
        max-width: 440px;
        margin: 60px auto 0 auto;
        background: #fff;
        border: 1px solid #e0e0e0;
        border-radius: 16px;
        padding: 40px 36px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.06);
    }
    .login-hero {
        text-align: center;
        margin-bottom: 28px;
    }
    .login-hero .logo {
        font-size: 40px;
        margin-bottom: 8px;
    }
    .login-hero h1 {
        font-size: 26px;
        font-weight: 800;
        color: #202124;
        margin: 0 0 4px 0;
    }
    .login-hero .sub {
        font-size: 13px;
        color: #80868b;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Tabs: Login / Register ─────────────────────────────────────────
    tab1, tab2 = st.tabs(["🔐 登录", "✨ 注册"])

    with tab1:
        _render_login_tab(store)

    with tab2:
        _render_register_tab(store)

    return False


# ── Login tab ────────────────────────────────────────────────────────────

def _render_login_tab(store):
    st.markdown(
        "<div class='login-hero'>"
        "<div class='logo'>🎯</div>"
        "<h1>OfferPilot</h1>"
        "<div class='sub'>AI 求职管理助手</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        username = st.text_input(
            "用户名", placeholder="请输入用户名",
            key="login_username",
        )
        password = st.text_input(
            "密码", type="password", placeholder="请输入密码",
            key="login_password",
        )
        submitted = st.form_submit_button(
            "🔐 登录", type="primary", use_container_width=True,
        )

        if submitted:
            if not username.strip():
                st.error("请输入用户名")
            elif not password:
                st.error("请输入密码")
            else:
                user_row = store.get_user_by_username(username.strip())
                if user_row is None:
                    st.error("用户名不存在，请先注册")
                elif not verify_password(password, user_row.get("password_hash", "")):
                    st.error("密码错误，请重试")
                else:
                    login_user(user_row["id"])
                    st.success("登录成功！")
                    st.rerun()


# ── Register tab ─────────────────────────────────────────────────────────

def _render_register_tab(store):
    st.info("**已有账号？** 请切换到左侧「🔐 登录」标签页，使用已注册的用户名登录。注册新账号后之前的投递记录将不可见。")
    st.markdown(
        "<div class='login-hero'>"
        "<div class='logo'>🚀</div>"
        "<h1>创建账号</h1>"
        "<div class='sub'>注册后即可开始管理求职进度</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    with st.form("register_form"):
        username = st.text_input(
            "用户名 *", placeholder="字母、数字或下划线",
            key="reg_username",
        )
        display_name = st.text_input(
            "昵称（选填）", placeholder="如何称呼你？",
            key="reg_display_name",
        )
        password = st.text_input(
            "密码 *", type="password", placeholder="至少 4 位字符",
            key="reg_password",
        )
        confirm_password = st.text_input(
            "确认密码 *", type="password", placeholder="再次输入密码",
            key="reg_confirm",
        )
        submitted = st.form_submit_button(
            "✨ 注册并开始使用", type="primary", use_container_width=True,
        )

        if submitted:
            # Validation
            if not username.strip():
                st.error("请输入用户名")
            elif not username.strip().replace("_", "").replace("-", "").isalnum():
                st.error("用户名只能包含字母、数字、下划线和连字符")
            elif len(password) < 4:
                st.error("密码至少需要 4 位字符")
            elif password != confirm_password:
                st.error("两次输入的密码不一致")
            else:
                ok, result = store.create_user(
                    username=username.strip(),
                    display_name=display_name.strip(),
                    password_hash=hash_password(password),
                )
                if not ok:
                    st.error(result)  # result is error message (e.g. username taken)
                else:
                    user_id = result  # result is user_id on success
                    login_user(user_id)
                    st.success("注册成功！正在进入 OfferPilot...")
                    st.rerun()
