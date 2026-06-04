"""Test script for OfferPilot LLM connection.

Usage:
    python scripts/test_llm_connection.py

This script:
  1. Loads .env from the project root (via python-dotenv)
  2. Prints the current LLM configuration (with API key masked)
  3. Sends a simple test prompt via call_llm()
  4. Prints the response (or error)
"""

import sys
import os
import json

# Fix Unicode output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure the project root is on sys.path so we can import services
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# Load .env before any other imports
try:
    from dotenv import load_dotenv
    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.isfile(env_path):
        load_dotenv(env_path)
        print(f"✅ 已加载环境变量：{env_path}")
    else:
        print(f"⚠️  未找到 .env 文件（{env_path}），使用系统环境变量")
except ImportError:
    print("⚠️  python-dotenv 未安装，跳过 .env 加载（将使用系统环境变量）")

import time

from services.llm_client import call_llm, call_llm_json, check_config, get_llm_config, get_last_usage


def main():
    print("=" * 60)
    print("  OfferPilot — LLM 连接测试")
    print("=" * 60)
    print()

    # ── 1. Show configuration ────────────────────────────────────────
    cfg = get_llm_config()
    print("📋 当前 LLM 配置（get_llm_config）：")
    for k, v in cfg.items():
        if k == "api_key":
            v = (v[:8] + "***") if len(v) > 8 else ("***" if v else "（未设置）")
        print(f"   {k:16s} = {v}")
    print()

    display = check_config()
    print("📋 显示用配置（check_config）：")
    for k, v in display.items():
        print(f"   {k:20s} = {v}")
    print()

    # ── 2. Test call_llm() ───────────────────────────────────────────
    print("🚀 正在测试 call_llm() ...")
    prompt = "请用一句话介绍 OfferPilot。"
    print(f"   Prompt: {prompt}")

    response = call_llm(prompt)
    print(f"   响应:")
    for line in response.strip().split("\n"):
        print(f"   │ {line}")
    print()

    # ── 3. Test call_llm_json() ──────────────────────────────────────
    mode = cfg["mode"]
    rate_limited = "429" in response or "速率限制" in response or "频率超限" in response

    if rate_limited:
        print("⚠️  已触发速率限制，跳过第二个测试以避免重复 429 错误。")
        print("   请等待 1-2 分钟后重试。")
        print()
    else:
        # GLM free tier has tight rate limits; 5s delay avoids 429
        if mode == "real":
            print("   （等待 5 秒以遵守免费版速率限制...）")
            time.sleep(5)

        print("🚀 正在测试 call_llm_json() ...")
        json_prompt = '请用 JSON 格式回答：{"name": "OfferPilot", "description": "一句话介绍"}'
        print(f"   Prompt: {json_prompt}")

        result = call_llm_json(json_prompt)
        print(f"   success    = {result.get('success')}")
        if result.get("success"):
            print(f"   data       = {json.dumps(result['data'], ensure_ascii=False, indent=2)}")
        else:
            print(f"   error      = {result.get('error', 'N/A')}")
        print()

    # ── 4. Summary ───────────────────────────────────────────────────
    print("=" * 60)
    if mode == "real":
        if cfg["api_key"]:
            if response.startswith("❌"):
                print("⚠️  真实模式已启用但调用失败，请检查 API Key 和网络连接。")
            else:
                print("✅ 真实模式连接成功！")
                # Show token usage
                usage = get_last_usage()
                if usage:
                    print()
                    print("📊 Token 消耗统计：")
                    print(f"   输入 Tokens  : {usage.get('prompt_tokens', 'N/A')}")
                    print(f"   输出 Tokens  : {usage.get('completion_tokens', 'N/A')}")
                    print(f"   总计 Tokens  : {usage.get('total_tokens', 'N/A')}")
                    print(f"   💰 费用      : 免费（GLM-4.7-Flash 不收费）")
        else:
            print("⚠️  真实模式已启用但 LLM_API_KEY 未设置。")
    else:
        print("ℹ️  当前为 Mock 模式。设置 LLM_MODE=real 并配置 API Key 以启用真实 AI。")
    print("=" * 60)


if __name__ == "__main__":
    main()
