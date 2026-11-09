"""LLM 需求拆解客户端（OpenAI 兼容接口）。

职责边界：LLM 只负责把需求拆成功能模块并估算人日；
价格由 pricing.price_modules 计算，LLM 不返回任何金额。
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4.1-Flash"
DEFAULT_ENV_FILE = "/Users/mac/.openclaw/.env"
ENV_FILE = os.environ.get("ORDER_LLM_ENV_FILE", DEFAULT_ENV_FILE)

SYSTEM_PROMPT = (
    "你是软件项目报价分析师与解决方案架构师。"
    "你的任务只有一件：把客户需求拆解为可独立开发、可独立验收的功能模块，并估算人日。"
    "不要输出任何价格、金额、报价或货币单位。只输出合法 JSON。"
)


def _read_key() -> str:
    key = os.environ.get("ORDER_LLM_API_KEY") or os.environ.get("SILICONFLOW_API_KEY")
    if key:
        return key.strip()
    try:
        path = Path(ENV_FILE)
        if path.exists():
            for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("SILICONFLOW_API_KEY="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def _extract_json(content: str) -> dict | None:
    text = (content or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def decompose(
    *,
    title: str,
    description: str,
    deliverables: list | None = None,
    deadline_days: int = 30,
    category: str | None = None,
    categories: list | None = None,
) -> dict:
    """返回 {"ok": bool, "modules": [...], "summary", "confidence", ...}。"""
    started = time.time()
    api_key = _read_key()
    model = os.environ.get("ORDER_LLM_MODEL", DEFAULT_MODEL)
    base_url = os.environ.get("ORDER_LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    timeout = int(os.environ.get("ORDER_LLM_TIMEOUT", "45"))
    if not api_key:
        return {"ok": False, "error": "missing_api_key", "model": model, "latency_ms": 0}

    category_keys = categories or [
        "web_fullstack", "frontend", "backend", "miniprogram", "ai_app",
        "data", "automation", "design", "ops", "other",
    ]
    deliverables = [str(item).strip() for item in (deliverables or []) if str(item).strip()]
    user_prompt = (
        "请拆解以下需求。\n\n"
        f"项目名称：{title}\n"
        f"需求类别（可选参考）：{category or '自动判断'}\n"
        f"期望工期：{deadline_days} 天\n"
        f"客户交付物：{('、'.join(deliverables) if deliverables else '未列明')}\n"
        f"需求描述：\n{description}\n\n"
        "拆解要求：\n"
        "1. 拆成 4–12 个可独立开发/验收的功能模块；模块不要过细，也不要只给一个笼统模块。\n"
        "2. 每个模块给出：name（≤30字）、description（≤120字）、"
        f"category（只能取：{', '.join(category_keys)}）、"
        "days（人日，0.5–60，已含复杂度与自测）、complexity（0.8–1.6，仅作说明）。\n"
        "3. 不要输出价格、金额、总价、货币单位。\n"
        "4. 只返回 JSON，格式：\n"
        '{"modules":[{"name":"模块名","description":"说明","category":"backend","days":3.0,"complexity":1.1}],'
        '"summary":"一句话说明拆解思路","confidence":0.8,'
        '"assumptions":["拆解假设1","拆解假设2"]}\n'
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 2000,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        base_url + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=timeout) as response:
            body = json.load(response)
        content = body["choices"][0]["message"]["content"]
        parsed = _extract_json(content)
        latency = int((time.time() - started) * 1000)
        if not parsed or not isinstance(parsed.get("modules"), list):
            return {
                "ok": False,
                "error": "invalid_json",
                "model": model,
                "latency_ms": latency,
                "raw": {"content": str(content)[:12000]},
            }
        modules = [item for item in parsed["modules"] if isinstance(item, dict)][:20]
        if not modules:
            return {
                "ok": False,
                "error": "empty_modules",
                "model": model,
                "latency_ms": latency,
                "raw": {"content": str(content)[:12000]},
            }
        try:
            confidence = float(parsed.get("confidence", 0.75))
        except (TypeError, ValueError):
            confidence = 0.75
        assumptions = parsed.get("assumptions")
        if not isinstance(assumptions, list):
            assumptions = []
        return {
            "ok": True,
            "modules": modules,
            "summary": str(parsed.get("summary") or "")[:500],
            "confidence": max(0.35, min(0.95, confidence)),
            "assumptions": [str(item)[:300] for item in assumptions[:8]],
            "model": model,
            "latency_ms": latency,
            "raw": {"content": str(content)[:12000]},
        }
    except Exception as exc:  # 网络/超时/解析失败统一回退
        latency = int((time.time() - started) * 1000)
        return {
            "ok": False,
            "error": type(exc).__name__,
            "detail": str(exc)[:300],
            "model": model,
            "latency_ms": latency,
        }
