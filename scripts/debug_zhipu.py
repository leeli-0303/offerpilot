"""Minimal diagnostic script for GLM-4.7-Flash API debugging.

Usage:
    python scripts/debug_zhipu.py

This bypasses all OfferPilot code and calls the API directly with
the requests library, printing the raw response for diagnosis.
"""

import sys
import os

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Load .env
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
except ImportError:
    pass

import requests
import json

API_KEY = os.environ.get("LLM_API_KEY", "")
BASE_URL = os.environ.get("LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
MODEL = os.environ.get("LLM_MODEL_NAME", "glm-4.7-flash")

print("=" * 60)
print("  GLM-4.7-Flash 最小化连接诊断")
print("=" * 60)
print(f"  API Key  : {API_KEY[:10]}***")
print(f"  Base URL : {BASE_URL}")
print(f"  Model    : {MODEL}")
print()

# ── Test 1: Try the documented base URL ──────────────────────────────
base_url_clean = BASE_URL.rstrip("/")
url = f"{base_url_clean}/chat/completions"
print(f"  请求 URL : {url}")

payload = {
    "model": MODEL,
    "messages": [
        {"role": "user", "content": "你好，请用一句话回复。"}
    ],
    "max_tokens": 50,
    "temperature": 0.3,
}
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

print("  正在发送请求...")
try:
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    print(f"  HTTP 状态码: {resp.status_code}")
    print(f"  响应头: {dict(resp.headers)}")
    print(f"  响应体:")
    body = resp.json()
    print(json.dumps(body, ensure_ascii=False, indent=2))

    if resp.status_code == 200:
        print()
        print("✅ 连接成功！")
        content = body["choices"][0]["message"]["content"]
        print(f"  模型回复: {content}")
        if "usage" in body:
            u = body["usage"]
            print(f"  Token 消耗: prompt={u.get('prompt_tokens')}, "
                  f"completion={u.get('completion_tokens')}, "
                  f"total={u.get('total_tokens')}")
    elif resp.status_code == 429:
        print()
        error_code = body.get("error", {}).get("code", "N/A")
        error_msg = body.get("error", {}).get("message", "")
        print(f"❌ 429 速率限制 (错误码: {error_code})")
        print(f"   消息: {error_msg}")
        print()
        print("   可能的原因：")
        print("   1. 账号并发限制为 1，上一请求未释放 → 等 30 秒重试")
        print("   2. 免费模型需要先在体验中心激活 → 访问")
        print("      https://bigmodel.cn/trialcenter/modeltrial/text?modelCode=glm-4.7-flash")
        print("   3. 高峰期（15:00-23:00）免费通道拥堵 → 换个时间")
        print("   4. API Key 格式不对 → 应为 32 位字符串（含英文+数字+点号）")
    else:
        print(f"❌ 未预期的状态码: {resp.status_code}")
except Exception as e:
    print(f"❌ 请求异常: {e}")

print()
print("=" * 60)

# ── Test 2: Try with glm-4-flash (legacy free model) ────────────────
print("  尝试备用模型名 glm-4-flash ...")
payload["model"] = "glm-4-flash"
try:
    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    print(f"  HTTP 状态码: {resp.status_code}")
    if resp.status_code == 200:
        body = resp.json()
        print(f"  ✅ glm-4-flash 可用！")
        print(f"  回复: {body['choices'][0]['message']['content'][:50]}...")
    else:
        body = resp.json()
        print(f"  响应: {json.dumps(body, ensure_ascii=False, indent=2)[:300]}")
except Exception as e:
    print(f"  请求异常: {e}")

print("=" * 60)
