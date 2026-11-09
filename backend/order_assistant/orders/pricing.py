"""确定性市场价报价引擎（market-2026.1）。

设计约束：同一输入必须产生完全相同结果；不依赖随机数、网络与当前时间。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

PRICING_VERSION = "market-2026.1"
CURRENCY = "CNY"

DEFAULT_CATALOG = [
    {"category": "web_fullstack", "label": "全栈 Web", "day_rate": 1400, "base_days": 12,
     "keywords": ["网站", "官网", "web", "后台管理", "管理系统", "门户", "全栈"]},
    {"category": "frontend", "label": "前端开发", "day_rate": 1100, "base_days": 8,
     "keywords": ["前端", "页面", "vue", "react", "h5", "响应式", "组件"]},
    {"category": "backend", "label": "后端 / API", "day_rate": 1300, "base_days": 10,
     "keywords": ["后端", "接口", "api", "服务端", "数据库", "微服务", "权限"]},
    {"category": "miniprogram", "label": "小程序", "day_rate": 1200, "base_days": 10,
     "keywords": ["小程序", "微信", "支付宝", "uni-app"]},
    {"category": "ai_app", "label": "AI 应用 / Agent", "day_rate": 1800, "base_days": 14,
     "keywords": ["ai", "智能体", "agent", "大模型", "llm", "rag", "知识库", "问答"]},
    {"category": "data", "label": "数据 / 报表", "day_rate": 1200, "base_days": 8,
     "keywords": ["数据", "报表", "分析", "可视化", "bi", "数仓"]},
    {"category": "automation", "label": "自动化 / 脚本", "day_rate": 1000, "base_days": 6,
     "keywords": ["自动化", "脚本", "批处理", "定时", "rpa", "爬虫"]},
    {"category": "design", "label": "UI / 视觉设计", "day_rate": 900, "base_days": 6,
     "keywords": ["设计", "ui", "ux", "视觉", "原型", "figma"]},
    {"category": "ops", "label": "部署 / 运维", "day_rate": 1000, "base_days": 5,
     "keywords": ["部署", "运维", "服务器", "docker", "k8s", "监控"]},
    {"category": "other", "label": "其他", "day_rate": 1000, "base_days": 8, "keywords": []},
]

DEFAULT_CATALOG_MAP = {item["category"]: item for item in DEFAULT_CATALOG}

COMPLEXITY_KEYWORDS = [
    "支付", "权限", "多端", "实时", "高并发", "第三方", "对接", "迁移", "国际化", "审批",
]

PHASES = [
    ("需求澄清与方案", 0.10, "需求边界确认、验收标准与里程碑"),
    ("方案与设计", 0.15, "信息架构、交互原型与数据结构设计"),
    ("核心开发", 0.55, "功能开发、接口联调与主要业务逻辑"),
    ("联调测试", 0.12, "端到端联调、缺陷修复与回归"),
    ("交付文档", 0.08, "部署说明、使用文档与交付培训"),
]

DESIGN_LIGHT_CATEGORIES = {"backend", "data", "automation", "ops"}


def _round100(value: float) -> int:
    return int(round(value / 100.0) * 100)


def catalog_map(pricebook_rows=None) -> dict:
    if not pricebook_rows:
        return {k: dict(v) for k, v in DEFAULT_CATALOG_MAP.items()}
    result = {}
    for row in pricebook_rows:
        if isinstance(row, dict):
            item = dict(row)
        else:
            item = {
                "category": row.category,
                "label": row.label,
                "day_rate": int(row.day_rate),
                "base_days": int(row.base_days),
                "keywords": list(row.keywords or []),
            }
        result[item["category"]] = item
    for key, default in DEFAULT_CATALOG_MAP.items():
        result.setdefault(key, dict(default))
    return result


def classify_category(title: str, description: str, catalog: dict) -> tuple[str, dict]:
    """按关键词命中计分；全 0 或并列最高时归入 other。"""
    text = f"{title}\n{description}".lower()
    scores = {}
    for key, item in catalog.items():
        if key == "other":
            continue
        score = 0
        for keyword in item.get("keywords", []):
            if keyword and keyword.lower() in text:
                score += 1
        scores[key] = score
    if not scores:
        return "other", {}
    best = max(scores.values())
    if best == 0:
        return "other", scores
    winners = [k for k, v in scores.items() if v == best]
    if len(winners) > 1:
        return "other", scores
    return winners[0], scores


def complexity_score(description: str, deliverables: list) -> tuple[float, list[str]]:
    text = description or ""
    reasons = []
    score = 1.0
    count = len(deliverables or [])
    if count >= 3:
        score += 0.15
        reasons.append(f"交付物 {count} 项，跨界协作 +0.15")
    if count >= 5:
        score += 0.10
        reasons.append("交付物 ≥5 项，规模 +0.10")
    length = len(text)
    if length >= 400:
        score += 0.20
        reasons.append("需求描述 ≥400 字，细节密度 +0.20")
    if length >= 800:
        score += 0.10
        reasons.append("需求描述 ≥800 字，复杂度 +0.10")
    hits = [k for k in COMPLEXITY_KEYWORDS if k in text]
    if hits:
        bonus = min(len(hits) * 0.06, 0.30)
        score += bonus
        reasons.append("命中复杂要素（" + "、".join(hits[:5]) + f"）+{bonus:.2f}")
    if length < 80:
        score -= 0.15
        reasons.append("需求描述 <80 字，范围偏简单 -0.15")
    score = max(0.8, min(1.6, round(score, 2)))
    return score, reasons


def deadline_factor(effort_days: float, deadline_days: int) -> tuple[float, str]:
    if deadline_days < effort_days * 0.7:
        return 1.25, "排期明显紧于估算工期，加急系数 1.25"
    if deadline_days < effort_days:
        return 1.12, "排期略紧于估算工期，系数 1.12"
    return 1.0, "排期充裕，无加急系数"


def confidence_score(fields: dict, description_length: int) -> float:
    score = 0.60
    if fields.get("contact"):
        score += 0.07
    if fields.get("category") and fields.get("category") != "other":
        score += 0.07
    if fields.get("deliverables"):
        score += 0.07
    if fields.get("deadline_days"):
        score += 0.07
    if fields.get("budget_expectation") is not None:
        score += 0.07
    if description_length < 80:
        score -= 0.15
    return round(max(0.35, min(0.95, score)), 2)


@dataclass
class Estimate:
    category: str
    category_label: str
    day_rate: int
    complexity: float
    effort_days: float
    deadline_factor: float
    amount_min: int
    amount_max: int
    suggested_price: int
    confidence: float
    pricing_version: str = PRICING_VERSION
    currency: str = CURRENCY
    market_basis: str = ""
    breakdown: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)


def estimate(
    *,
    title: str,
    description: str,
    deliverables: list | None = None,
    deadline_days: int = 30,
    budget_expectation: int | None = None,
    contact: str = "",
    category: str | None = None,
    catalog: dict | None = None,
) -> Estimate:
    deliverables = list(deliverables or [])
    catalog = catalog or catalog_map()

    if category and category in catalog:
        chosen = category
    else:
        chosen, _ = classify_category(title, description, catalog)
    item = catalog.get(chosen, DEFAULT_CATALOG_MAP["other"])
    day_rate = int(item["day_rate"])
    base_days = int(item["base_days"])

    complexity, _ = complexity_score(description, deliverables)
    effort_days = round((base_days + 1.5 * len(deliverables)) * complexity, 1)
    factor, factor_note = deadline_factor(effort_days, max(1, int(deadline_days or 30)))

    raw = effort_days * day_rate * factor
    suggested = _round100(raw)
    amount_min = _round100(raw * 0.88)
    amount_max = _round100(raw * 1.15)
    # 保证区间严格包住建议价
    if amount_min >= suggested:
        amount_min = max(0, suggested - 100)
    if amount_max <= suggested:
        amount_max = suggested + 100

    conf = confidence_score(
        {
            "contact": contact,
            "category": category,
            "deliverables": deliverables,
            "deadline_days": deadline_days,
            "budget_expectation": budget_expectation,
        },
        len(description or ""),
    )

    phases = []
    for name, ratio, note in PHASES:
        if name == "方案与设计" and chosen in DESIGN_LIGHT_CATEGORIES:
            ratio = 0.10
        phases.append((name, ratio, note))
    total_ratio = sum(p[1] for p in phases)
    breakdown = []
    allocated = 0
    for index, (name, ratio, note) in enumerate(phases):
        norm = ratio / total_ratio
        if index == len(phases) - 1:
            amount = suggested - allocated
        else:
            amount = int(round(suggested * norm))
            allocated += amount
        breakdown.append(
            {
                "phase": name,
                "ratio": round(norm, 4),
                "days": round(effort_days * norm, 1),
                "unit_price": day_rate,
                "amount": amount,
                "note": note,
            }
        )

    market_basis = (
        f"2026 年国内市场：{item['label']} {day_rate} 元/人日；"
        f"估算 {effort_days} 人日；复杂度系数 {complexity}；{factor_note}。"
    )
    assumptions = [
        "按标准交付流程估算，含需求澄清、开发、联调与交付文档",
        "不含第三方平台年费、服务器与短信等外部成本",
        "需求范围以本轮提交内容为准，范围变更按新一轮重新报价",
    ]
    if budget_expectation is not None and budget_expectation > 0:
        assumptions.append(
            f"客户预算参考 {budget_expectation} 元；报价按市场价独立计算，不向预算倒推"
        )

    return Estimate(
        category=chosen,
        category_label=item["label"],
        day_rate=day_rate,
        complexity=complexity,
        effort_days=effort_days,
        deadline_factor=factor,
        amount_min=amount_min,
        amount_max=amount_max,
        suggested_price=suggested,
        confidence=conf,
        market_basis=market_basis,
        breakdown=breakdown,
        assumptions=assumptions,
    )


def compare_quotes(previous: dict | None, current: dict) -> dict:
    if not previous:
        return {
            "previous_quote_id": None,
            "previous_suggested_price": None,
            "delta": 0,
            "delta_pct": 0.0,
            "reasons": ["首轮报价，无历史对比"],
        }
    prev_amount = int(previous.get("suggested_price") or 0)
    curr_amount = int(current.get("suggested_price") or 0)
    delta = curr_amount - prev_amount
    pct = round(delta / prev_amount * 100, 2) if prev_amount else 0.0
    reasons = []
    prev_deliverables = int(previous.get("deliverable_count") or 0)
    curr_deliverables = int(current.get("deliverable_count") or 0)
    if curr_deliverables != prev_deliverables:
        change = curr_deliverables - prev_deliverables
        reasons.append(f"交付物 {change:+d} 项（{prev_deliverables} → {curr_deliverables}）")
    prev_days = int(previous.get("deadline_days") or 0)
    curr_days = int(current.get("deadline_days") or 0)
    if curr_days != prev_days:
        reasons.append(f"期望工期 {prev_days} → {curr_days} 天")
    if previous.get("category") and current.get("category") != previous.get("category"):
        reasons.append(
            f"需求类别 {previous.get('category_label')} → {current.get('category_label')}"
        )
    prev_complexity = float(previous.get("complexity") or 0)
    curr_complexity = float(current.get("complexity") or 0)
    if abs(curr_complexity - prev_complexity) >= 0.01:
        reasons.append(f"复杂度系数 {prev_complexity} → {curr_complexity}")
    if not reasons:
        reasons.append("本轮范围与上一轮基本一致，价格差异来自工期或描述细节")
    return {
        "previous_quote_id": previous.get("id"),
        "previous_suggested_price": prev_amount,
        "delta": delta,
        "delta_pct": pct,
        "reasons": reasons,
    }
