"""LLM client with mock / real dual-mode support.

Configuration via environment variables or .env file:
  LLM_MODE        – "mock" (default) or "real"
  LLM_PROVIDER    – Provider label for display (openai, deepseek, etc.)
  LLM_API_KEY     – API key for real mode
  LLM_BASE_URL    – Base URL for OpenAI-compatible endpoint
  LLM_MODEL_NAME  – Model name (e.g. deepseek-chat, gpt-4o)
  LLM_TEMPERATURE – Generation temperature (default 0.3)
  LLM_MAX_TOKENS  – Max tokens in response (default 2048)
"""

import os
import json
import re
from typing import Optional

# ── Auto-load .env (once, at import time) ──────────────────────────────
# Streamlit does not auto-load .env, so we do it here to ensure
# LLM_MODE / LLM_API_KEY / etc. are available in the running app.
_ENV_LOADED = False
if not _ENV_LOADED:
    try:
        from dotenv import load_dotenv as _load_dotenv
        _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _env_path = os.path.join(_project_root, ".env")
        if os.path.isfile(_env_path):
            _load_dotenv(_env_path)
    except ImportError:
        pass  # python-dotenv not installed — rely on system env vars
    _ENV_LOADED = True


# ── Mock response bank ──────────────────────────────────────────────────

_MOCK_JD_PARSE = """{
  "job_type": "后端开发",
  "skills": ["Java", "Spring Boot", "MySQL", "Redis", "Kafka", "微服务"],
  "keywords": ["校招", "应届", "本科及以上"],
  "priority": "高",
  "risk_notes": []
}"""

_MOCK_MATCH = """{
  "match_score": 78,
  "matched_points": [
    "技术栈高度匹配（Java / Spring Boot / MySQL）",
    "实习经验与目标行业一致",
    "学历满足岗位要求"
  ],
  "missing_points": [
    "简历中未提及消息队列相关项目经验（Kafka/RabbitMQ）",
    "缺少系统设计相关关键词（CAP、一致性哈希、负载均衡）"
  ],
  "risk_notes": [],
  "optimization_suggestions": [
    "在项目描述中突出分布式系统关键词（如微服务、RPC、分布式锁）",
    "补充消息队列相关经验或学习描述",
    "如有 ACM/编程竞赛经历请补充到简历中"
  ],
  "recommended_action": "强烈建议投递（匹配度 78%），技术栈高度匹配，建议补齐系统设计和消息队列关键词后投递"
}"""

_MOCK_INTERVIEW_PREP = """{
  "job_summary": "目标公司：字节跳动；岗位名称：后端开发工程师（校招）；核心技能要求：Java、Spring Boot、MySQL、Redis、Kafka、微服务。该岗位面向应届生，要求扎实的计算机基础和高并发系统设计能力。",
  "key_experiences_to_highlight": [
    "重点准备项目经历：电商平台后端开发（Spring Boot + MySQL + Redis），准备好 STAR 描述",
    "强调 Java 并发编程和 JVM 调优的实践经验",
    "突出微服务架构实践——服务拆分、RPC 调用、网关设计",
    "强调学习能力和快速上手能力 — 应届生的核心优势"
  ],
  "likely_questions": [
    "请谈谈你对 Java 中 JVM 内存模型的理解，以及常见的 GC 算法",
    "Spring Boot 的自动配置原理是什么？你如何自定义一个 starter？",
    "Redis 有哪些常见的数据结构？缓存穿透、击穿、雪崩分别是什么？",
    "微服务架构中如何处理服务发现、负载均衡和熔断降级？",
    "请描述一个你在项目中遇到的最大技术挑战，以及你是如何解决的"
  ],
  "star_answer_tips": [
    "回答「电商平台后端开发」项目时，先说明业务背景（S），再明确你的具体职责（T），然后重点讲技术选型和实现细节（A），最后用数据量化结果如 QPS 提升、延迟降低（R）",
    "技术栈匹配问题要结合项目中的实际使用场景，例如说明为什么选择 Redis 做缓存而不是其他方案",
    "行为面试题要准备一个「失败/冲突→反思→改进→再验证」的完整闭环案例"
  ],
  "questions_to_ask_interviewer": [
    "请问团队目前的技术栈和主要项目方向是什么？",
    "团队现在面临的最大技术挑战是什么？",
    "对于应届生，公司的培养体系和新员工培训是怎样的？"
  ]
}"""

_MOCK_WEEKLY_LLM = """{
  "summary": "本周共投递9个岗位，新增2条投递记录。目前2个岗位处于面试阶段，尚无正式Offer。后端方向投递最活跃（6个），但反馈转化率有待提升。简历版本「后端开发-中文」使用最多（4次）。整体求职节奏保持稳定，但需关注无反馈岗位的跟进。",
  "key_insights": [
    "后端方向占投递总量的67%，是绝对主力方向，建议继续深耕",
    "2个岗位已进入面试阶段，说明简历和技术栈匹配度基本达标",
    "本周新增2条投递，保持了每周2-3个的稳定节奏",
    "简历「后端开发-中文」使用4次，是最常投递的版本，可考虑针对不同公司微调"
  ],
  "problems": [
    "约22%的投递尚无反馈（2条），其中部分超过5个工作日，存在简历被筛掉的风险",
    "1条投递被拒，建议复盘该岗位的面试或简历匹配问题",
    "仅有后端方向有面试进展，其他方向（产品、前端、算法）尚未突破"
  ],
  "next_week_plan": [
    "跟进2条无反馈投递：超过5个工作日的通过邮件或招聘平台礼貌询问进度",
    "准备2个进行中的面试：重点复习技术基础、项目深挖和系统设计",
    "继续投递后端方向岗位2-3个，优先选择有内推渠道的公司",
    "复盘被拒岗位的失败原因（算法题？项目匹配度？），针对性补强",
    "每天刷2-3道LeetCode算法题，保持手感；准备1-2个行为面试的标准回答"
  ]
}"""

_MOCK_WEEKLY = """{
  "stats": {
    "new_jobs": 3,
    "applications_sent": 4,
    "interviews_completed": 2,
    "offers_received": 1
  },
  "highlights": [
    "本周完成了 4 次投递，覆盖字节跳动、阿里巴巴等目标公司",
    "通过字节跳动技术一面，成功进入二面",
    "收到腾讯正式 Offer，薪资符合预期"
  ],
  "next_week_focus": [
    "准备字节跳动技术二面（系统设计 + 项目深挖）",
    "决定是否接受腾讯 Offer（截止 5 月 25 日）",
    "继续投递 2-3 个外企岗位（Google、Microsoft）"
  ]
}"""

_MOCK_DEFAULT = "这是一个模拟的 LLM 响应。将 LLM_MODE 设置为 real 并配置 API Key 以获取真实回复。"

# ── Token usage tracking ─────────────────────────────────────────────────
# Stores usage info from the most recent real-mode LLM call.
# Shared across all callers so the app / test script can inspect consumption.

_last_usage: dict = {}


# ── Helpers ─────────────────────────────────────────────────────────────

def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _pick_mock(prompt: str) -> str:
    """Return a mock response whose flavour matches the prompt topic."""
    p = prompt.lower()
    # JD parse check must come first — the user prompt may contain the
    # word "匹配" inside format descriptions like "选择最匹配的",
    # which would otherwise be caught by the match-analysis check below.
    if any(kw in p for kw in ("解析jd", "解析以下岗位描述", "jd 原文", "jd 结束",
                                "job description", "parse jd", "jd_text")):
        return _MOCK_JD_PARSE
    if any(kw in p for kw in ("匹配度", "匹配", "match_score", "简历匹配", "match analysis")):
        return _MOCK_MATCH
    if any(kw in p for kw in ("生成准备包", "面试准备", "interview prep", "面试辅导", "star_answer_tips")):
        return _MOCK_INTERVIEW_PREP
    if any(kw in p for kw in ("统计摘要", "strategic summary", "求职策略")):
        return _MOCK_WEEKLY_LLM
    if any(kw in p for kw in ("周报", "weekly", "weekly review", "求职周报")):
        return _MOCK_WEEKLY
    return _MOCK_DEFAULT


def _call_real(prompt: str, system_prompt: Optional[str] = None,
               config_overrides: Optional[dict] = None) -> str:
    """Call an OpenAI-compatible chat-completion endpoint using the OpenAI SDK.

    On rate-limit (429) errors the function automatically retries with
    progressively longer back-off (15 s → 25 s → 40 s → 60 s) to stay
    within the free-tier rate-limit window (~3 RPM).

    Args:
        prompt: The user prompt to send.
        system_prompt: Optional system-level instruction.
        config_overrides: Optional dict of config values to override
            (api_key, base_url, model_name, temperature, max_tokens).
            When provided, these take precedence over get_llm_config().
    """
    import time as _time
    import random as _random

    cfg = get_llm_config()
    # Apply overrides if provided (used by connection test in UI)
    if config_overrides:
        for k in ("api_key", "base_url", "model_name"):
            if config_overrides.get(k):
                cfg[k] = config_overrides[k]
        if config_overrides.get("temperature") is not None:
            cfg["temperature"] = float(config_overrides["temperature"])
        if config_overrides.get("max_tokens") is not None:
            cfg["max_tokens"] = int(config_overrides["max_tokens"])

    api_key = cfg["api_key"]
    base_url = cfg["base_url"]
    model = cfg["model_name"]
    temperature = cfg["temperature"]
    max_tokens = cfg["max_tokens"]

    if not api_key:
        return (
            "❌ 错误：LLM_MODE=real 但 LLM_API_KEY 未设置。\n"
            "请在环境变量中设置 LLM_API_KEY 后重试。"
        )

    try:
        from openai import OpenAI
    except ImportError:
        return (
            "❌ 错误：real 模式需要 openai 库。\n"
            "请执行 pip install openai 后重试。"
        )

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # Progressive back-off targeting ~3 RPM free-tier limit.
    # Each retry waits long enough for the rate-limit window to reset,
    # with a small random jitter to avoid thundering-herd.
    _BACKOFF_SCHEDULE = (15, 25, 40, 60)  # seconds
    max_retries = len(_BACKOFF_SCHEDULE)

    for attempt in range(max_retries + 1):  # 1 initial + N retries
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Capture token usage for monitoring
            global _last_usage
            if hasattr(response, "usage") and response.usage:
                _last_usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
            else:
                _last_usage = {}

            return response.choices[0].message.content

        except Exception as e:
            error_str = str(e)

            # ── 429 Rate limit: retry with long back-off ────────────
            is_rate_limit = (
                "429" in error_str
                or "rate limit" in error_str.lower()
                or "速率限制" in error_str
            )
            if is_rate_limit and attempt < max_retries:
                wait = _BACKOFF_SCHEDULE[attempt] + _random.uniform(0, 3)
                _time.sleep(wait)
                continue  # retry

            # ── Non-retryable errors ────────────────────────────────
            if "timeout" in error_str.lower() or "timed out" in error_str.lower():
                return "❌ 错误：LLM API 请求超时。请检查网络或 API 服务状态。"
            if "connection" in error_str.lower() or "connect" in error_str.lower():
                return (
                    f"❌ 错误：无法连接到 LLM API 端点。\n"
                    f"端点：{base_url}\n"
                    f"请检查 LLM_BASE_URL 和网络连接。"
                )
            if "401" in error_str or "403" in error_str or "unauthorized" in error_str.lower():
                return "❌ 错误：API 认证失败，请检查 LLM_API_KEY。"
            if is_rate_limit:
                return (
                    "❌ 错误：API 调用频率超限（429 Rate Limit）。\n"
                    "免费模型有严格的速率限制（约 3 RPM），重试 4 次仍未成功。\n"
                    "请等待 60 秒后重试，或前往 bigmodel.cn 检查账户配额。"
                )
            return f"❌ 错误：调用 LLM API 时发生异常：{error_str}"


# ── Public API ──────────────────────────────────────────────────────────

def get_llm_config() -> dict:
    """Read LLM configuration, with per-user overrides from the database.

    Configuration precedence:
      1. User's saved llm_settings in the database (for the current user)
      2. Environment variables / .env file (shared defaults)

    Returns a dict with all configuration values used by the LLM client.
    Callers can use this to display current settings or override defaults.
    """
    config = {
        "mode": _env("LLM_MODE", "mock").lower(),
        "provider": _env("LLM_PROVIDER", "openai"),
        "api_key": _env("LLM_API_KEY"),
        "base_url": _env("LLM_BASE_URL", "https://api.openai.com/v1"),
        "model_name": _env("LLM_MODEL_NAME", "gpt-4o"),
        "temperature": float(_env("LLM_TEMPERATURE", "0.3")),
        "max_tokens": int(_env("LLM_MAX_TOKENS", "2048")),
    }

    # Try to load per-user overrides from database
    try:
        from core.data_store import store
        if getattr(store, "_current_user_id", None):
            us = store.get_llm_settings()
            for key in ("mode", "api_key", "base_url", "model_name"):
                val = us.get(key)
                if val:  # non-empty user value overrides env default
                    config[key] = val
            # numeric fields: only override if user explicitly set them
            if us.get("temperature") is not None and us["temperature"] != "":
                config["temperature"] = float(us["temperature"])
            if us.get("max_tokens") is not None and us["max_tokens"] != "":
                config["max_tokens"] = int(us["max_tokens"])
    except Exception:
        pass

    return config


def call_llm(prompt: str, system_prompt: Optional[str] = None) -> str:
    """Call the LLM and return the response text.

    Behaviour is controlled by the LLM_MODE environment variable:
      - "real"  → call an OpenAI-compatible chat-completion API
      - "mock"  → return a canned response matching the prompt topic (default)

    Args:
        prompt: The user prompt to send.
        system_prompt: Optional system-level instruction.

    Returns:
        The model response string, or an error message prefixed with ❌.
    """
    mode = _env("LLM_MODE", "mock").lower()

    if mode == "real":
        return _call_real(prompt, system_prompt)

    # Default: mock mode
    return _pick_mock(prompt)


def call_llm_json(prompt: str, system_prompt: Optional[str] = None) -> dict:
    """Call the LLM and parse the response as JSON.

    This is a convenience wrapper around call_llm() that attempts to
    extract and parse JSON from the model response.  It handles common
    LLM output patterns such as ```json fenced code blocks and stray
    text before/after the JSON object.

    Args:
        prompt: The user prompt to send.
        system_prompt: Optional system-level instruction.

    Returns:
        A dict with the following keys:
          - success (bool): Whether JSON was successfully parsed.
          - data (dict):   Parsed JSON object (only when success=True).
          - error (str):   Error description (only when success=False).
          - raw_output (str): The raw model response text, always present.
    """
    response = call_llm(prompt, system_prompt)

    # If the response is already an error message, bail out early
    if response.startswith("❌"):
        return {"success": False, "error": response, "raw_output": response}

    cleaned = response.strip()

    # Strategy 1: extract from ```json ... ``` fenced code block
    code_block_match = re.search(
        r"```(?:json)?\s*\n?(.*?)\n?```", cleaned, re.DOTALL
    )
    if code_block_match:
        cleaned = code_block_match.group(1).strip()

    # Strategy 2: try to parse the (cleaned) text directly
    try:
        return {"success": True, "data": json.loads(cleaned), "raw_output": response}
    except json.JSONDecodeError:
        pass

    # Strategy 3: find the first balanced { ... } object
    # Use balanced-brace extraction instead of greedy .* which grabs
    # everything through the last } (including trailing text/objects).
    json_str = _extract_balanced_json(cleaned)
    if json_str:
        try:
            return {
                "success": True,
                "data": json.loads(json_str),
                "raw_output": response,
            }
        except json.JSONDecodeError:
            pass

    return {
        "success": False,
        "error": "无法从 LLM 响应中解析 JSON",
        "raw_output": response,
    }


def _extract_balanced_json(text: str) -> str | None:
    """Extract the first balanced ``{...}`` JSON object from *text*.

    Walks character-by-character counting open/close braces so that
    nested objects (e.g. strings containing ``{``) and trailing text
    after the root-level closing brace are handled correctly.
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def check_config() -> dict:
    """Return current LLM configuration (safe for display — API key masked).

    Backward-compatible wrapper around get_llm_config().  Kept for
    existing callers that expect the old return-keys.
    """
    cfg = get_llm_config()
    api_key = cfg["api_key"]
    return {
        "mode": cfg["mode"],
        "base_url": cfg["base_url"],
        "model": cfg["model_name"],
        "api_key_configured": bool(api_key),
        "api_key_preview": (
            (api_key[:8] + "***")
            if len(api_key) > 8
            else ("***" if api_key else "—")
        ),
    }


def get_last_usage() -> dict:
    """Return token usage from the most recent real-mode LLM call.

    Returns an empty dict if no real call has been made yet or if
    the last call was in mock mode.  Keys when populated:
      - prompt_tokens (int)
      - completion_tokens (int)
      - total_tokens (int)
    """
    return dict(_last_usage)  # shallow copy so callers can't mutate
