"""模块化市场报价引擎（market-2026.2）。

流程：LLM 把需求拆成功能模块（名称/说明/类别/人日）→ 本引擎按类别市场人日价
逐模块计价 → 叠加项目管理、联调测试、交付文档成本 → 区间价与建议价。

原则：价格数字只由本引擎计算；LLM 只能给出模块与人日，不能直接给总价。
"""
from __future__ import annotations

from dataclasses import dataclass, field

PRICING_VERSION = "market-2026.2"
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

OVERHEAD = [
    ("项目管理", 0.08, "需求边界、排期、沟通与验收组织"),
    ("联调测试", 0.10, "前后端联调、缺陷修复与回归"),
    ("交付文档", 0.05, "部署说明、使用文档与交付培训"),
]
OVERHEAD_RATE = sum(item[1] for item in OVERHEAD)

COMPLEXITY_KEYWORDS = [
    "支付", "权限", "多端", "实时", "高并发", "第三方", "对接", "迁移", "国际化", "审批",
]

MODULE_CATEGORIES = [item["category"] for item in DEFAULT_CATALOG]


def _round100(value: float) -> int:
    return int(round(value / 100.0) * 100)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _round_half_day(value: float) -> float:
    return max(0.5, round(float(value) * 2) / 2)


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
        reasons.append(f"交付物 {count} 项 +0.15")
    if count >= 5:
        score += 0.10
        reasons.append("交付物 ≥5 项 +0.10")
    length = len(text)
    if length >= 400:
        score += 0.20
        reasons.append("描述 ≥400 字 +0.20")
    if length >= 800:
        score += 0.10
        reasons.append("描述 ≥800 字 +0.10")
    hits = [k for k in COMPLEXITY_KEYWORDS if k in text]
    if hits:
        bonus = min(len(hits) * 0.06, 0.30)
        score += bonus
        reasons.append("复杂要素（" + "、".join(hits[:5]) + f"）+{bonus:.2f}")
    if length < 80:
        score -= 0.15
        reasons.append("描述 <80 字 -0.15")
    return _clamp(round(score, 2), 0.8, 1.6), reasons


def normalize_modules(modules, catalog: dict) -> list[dict]:
    """把 LLM / 规则的模块输出收敛到可计价的安全范围。"""
    result = []
    seen = set()
    for raw in list(modules or [])[:20]:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "").strip()[:60]
        if not name or name in seen:
            continue
        category = str(raw.get("category") or "other")
        if category not in catalog:
            category = "other"
        try:
            days = float(raw.get("days", 1))
        except (TypeError, ValueError):
            days = 1.0
        try:
            complexity = float(raw.get("complexity", 1.0))
        except (TypeError, ValueError):
            complexity = 1.0
        seen.add(name)
        result.append(
            {
                "name": name,
                "description": str(raw.get("description") or "")[:400],
                "category": category,
                "category_label": catalog[category]["label"],
                "days": _round_half_day(_clamp(days, 0.5, 60)),
                "complexity": _clamp(round(complexity, 2), 0.8, 1.6),
            }
        )
    # 兜底：LLM 输出不可用时至少给一个可执行模块
    if not result:
        result.append(
            {
                "name": "需求实现",
                "description": "需求主体功能开发",
                "category": "other",
                "category_label": catalog["other"]["label"],
                "days": 5.0,
                "complexity": 1.0,
            }
        )
    return result


def fallback_modules(
    *,
    title: str,
    description: str,
    deliverables: list | None = None,
    category: str | None = None,
    catalog: dict | None = None,
) -> dict:
    """无 LLM 时的确定性拆解：优先按交付物，其次按关键词。"""
    catalog = catalog or catalog_map()
    deliverables = [str(item).strip() for item in (deliverables or []) if str(item).strip()]
    chosen = category if category in catalog else classify_category(title, description, catalog)[0]
    base_days = int(catalog[chosen]["base_days"])
    text = f"{title} {description}"
    modules = []

    if len(deliverables) >= 2:
        share = max(0.5, round(base_days * 0.65 / len(deliverables) * 2) / 2)
        for item in deliverables[:8]:
            modules.append(
                {
                    "name": item,
                    "description": f"{item}的界面、交互与功能实现",
                    "category": chosen,
                    "days": share,
                    "complexity": 1.0,
                }
            )
        modules.append(
            {
                "name": "联调与交付",
                "description": "接口联调、缺陷修复、部署与交付文档",
                "category": "ops",
                "days": _round_half_day(base_days * 0.35),
                "complexity": 1.0,
            }
        )
    else:
        rules = [
            (("登录", "权限", "账号", "角色"), "用户与权限", "backend", 0.20),
            (("支付", "订单", "购物车", "交易"), "支付与订单", "backend", 0.22),
            (("后台", "管理", "审批"), "管理后台", "backend", 0.20),
            (("新闻", "文章", "内容", "博客"), "内容管理", "backend", 0.16),
            (("表单", "留言", "线索"), "表单与线索", "backend", 0.12),
            (("数据", "报表", "统计", "可视"), "数据报表", "data", 0.16),
            (("小程序", "微信"), "小程序端", "miniprogram", 0.45),
            (("官网", "页面", "前端", "展示", "响应式"), "前端页面", "frontend", 0.30),
            (("接口", "api", "服务"), "接口服务", "backend", 0.18),
            (("部署", "上线", "运维"), "部署上线", "ops", 0.10),
            (("ai", "智能体", "大模型", "agent", "知识库"), "AI 能力", "ai_app", 0.35),
        ]
        for keywords, name, cat, ratio in rules:
            if any(keyword.lower() in text.lower() for keyword in keywords):
                modules.append(
                    {
                        "name": name,
                        "description": f"{name}相关功能",
                        "category": cat,
                        "days": max(0.5, round(base_days * ratio * 2) / 2),
                        "complexity": 1.0,
                    }
                )
        if not modules:
            modules = [
                {"name": "需求与方案", "description": "需求澄清、方案与数据设计", "category": "other", "days": 2.0, "complexity": 1.0},
                {"name": "核心功能开发", "description": "主体业务功能实现", "category": chosen, "days": max(2.0, base_days * 0.7), "complexity": 1.0},
                {"name": "联调与交付", "description": "联调测试、部署与文档", "category": "ops", "days": 2.0, "complexity": 1.0},
            ]
        else:
            modules.append(
                {
                    "name": "联调与交付",
                    "description": "联调测试、部署与交付文档",
                    "category": "ops",
                    "days": 2.0,
                    "complexity": 1.0,
                }
            )

    modules = normalize_modules(modules, catalog)
    total_days = sum(item["days"] for item in modules)
    return {
        "modules": modules,
        "summary": f"规则拆解：按交付物/关键词生成 {len(modules)} 个模块，合计 {total_days:g} 人日",
        "confidence": 0.62,
        "assumptions": ["未启用 LLM 或 LLM 暂不可用，模块由规则拆解生成"],
    }


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
    modules: list = field(default_factory=list)
    module_count: int = 0
    total_days: float = 0.0
    decomposition_source: str = "fallback"
    decomposition_model: str = ""
    decomposition_summary: str = ""


def price_modules(
    *,
    modules: list,
    catalog: dict,
    category: str | None = None,
    contact: str = "",
    deadline_days: int | None = None,
    budget_expectation: int | None = None,
    decomposition_source: str = "fallback",
    decomposition_model: str = "",
    decomposition_summary: str = "",
    confidence_hint: float | None = None,
    extra_assumptions: list | None = None,
) -> Estimate:
    """按模块计价。模块人日已含复杂度，不再二次乘系数。"""
    normalized = normalize_modules(modules, catalog)
    rows = []
    subtotal = 0
    total_days = 0.0
    for item in normalized:
        rate = int(catalog[item["category"]]["day_rate"])
        amount = int(round(item["days"] * rate))
        subtotal += amount
        total_days += item["days"]
        rows.append(
            {
                "kind": "module",
                "phase": item["name"],
                "name": item["name"],
                "category": item["category"],
                "category_label": item["category_label"],
                "complexity": item["complexity"],
                "days": item["days"],
                "unit_price": rate,
                "amount": amount,
                "note": item["description"],
            }
        )

    suggested = _round100(subtotal * (1 + OVERHEAD_RATE))
    if suggested <= subtotal:
        suggested = subtotal + 100
    overhead_total = suggested - subtotal
    allocated = 0
    for index, (name, ratio, note) in enumerate(OVERHEAD):
        if index == len(OVERHEAD) - 1:
            amount = overhead_total - allocated
        else:
            amount = int(round(overhead_total * ratio / OVERHEAD_RATE))
            allocated += amount
        rows.append(
            {
                "kind": "overhead",
                "phase": name,
                "name": name,
                "category": "",
                "category_label": "",
                "complexity": 1.0,
                "days": round(total_days * ratio / OVERHEAD_RATE, 1),
                "unit_price": 0,
                "amount": amount,
                "note": note,
            }
        )

    amount_min = _round100(suggested * 0.88)
    amount_max = _round100(suggested * 1.15)
    if amount_min >= suggested:
        amount_min = max(0, suggested - 100)
    if amount_max <= suggested:
        amount_max = suggested + 100

    chosen = category
    if chosen not in catalog:
        chosen = classify_category("", " ".join(item["name"] for item in normalized), catalog)[0]
    avg_complexity = round(
        sum(item["complexity"] for item in normalized) / len(normalized), 2
    )

    confidence = 0.60
    if decomposition_source == "llm":
        confidence = 0.70
    if confidence_hint is not None:
        confidence = max(confidence, float(confidence_hint))
    if contact:
        confidence += 0.05
    if deadline_days:
        confidence += 0.05
    if budget_expectation is not None:
        confidence += 0.05
    confidence = round(_clamp(confidence, 0.35, 0.95), 2)

    source_label = "LLM" if decomposition_source == "llm" else "规则"
    market_basis = (
        f"{source_label}拆解 {len(normalized)} 个功能模块，合计 {total_days:g} 人日；"
        f"按类别市场人日价计算模块小计 {subtotal:,} 元；"
        f"项目管理 / 联调测试 / 交付文档加成 {int(OVERHEAD_RATE * 100)}%，"
        f"建议价 {suggested:,} 元。"
    )
    assumptions = list(extra_assumptions or [])
    assumptions.extend(
        [
            "模块人日为常规交付估算，含该模块的设计、开发与自测",
            "不含第三方平台年费、服务器、短信等外部成本",
            "范围变更按新一轮重新拆解与报价",
        ]
    )
    if budget_expectation is not None and budget_expectation > 0:
        assumptions.append(f"客户预算参考 {budget_expectation} 元；报价按市场价独立计算，不向预算倒推")

    return Estimate(
        category=chosen,
        category_label=catalog[chosen]["label"],
        day_rate=int(catalog[chosen]["day_rate"]),
        complexity=avg_complexity,
        effort_days=total_days,
        deadline_factor=1.0,
        amount_min=amount_min,
        amount_max=amount_max,
        suggested_price=suggested,
        confidence=confidence,
        market_basis=market_basis,
        breakdown=rows,
        assumptions=assumptions,
        modules=normalized,
        module_count=len(normalized),
        total_days=total_days,
        decomposition_source=decomposition_source,
        decomposition_model=decomposition_model,
        decomposition_summary=decomposition_summary,
    )


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
    """兼容旧调用的确定性报价：规则拆解 + 模块计价。"""
    catalog = catalog or catalog_map()
    decomposed = fallback_modules(
        title=title,
        description=description,
        deliverables=deliverables,
        category=category,
        catalog=catalog,
    )
    return price_modules(
        modules=decomposed["modules"],
        catalog=catalog,
        category=category,
        contact=contact,
        deadline_days=deadline_days,
        budget_expectation=budget_expectation,
        decomposition_source="fallback",
        decomposition_summary=decomposed["summary"],
        confidence_hint=decomposed["confidence"],
        extra_assumptions=decomposed["assumptions"],
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

    prev_modules = {
        str(item.get("name")): float(item.get("days") or 0)
        for item in (previous.get("modules") or [])
        if isinstance(item, dict)
    }
    curr_modules = {
        str(item.get("name")): float(item.get("days") or 0)
        for item in (current.get("modules") or [])
        if isinstance(item, dict)
    }
    added = [name for name in curr_modules if name not in prev_modules]
    removed = [name for name in prev_modules if name not in curr_modules]
    if added:
        reasons.append("新增模块：" + "、".join(added[:5]))
    if removed:
        reasons.append("移除模块：" + "、".join(removed[:5]))
    changed = [
        f"{name} {prev_modules[name]:g}→{curr_modules[name]:g} 人日"
        for name in curr_modules
        if name in prev_modules and abs(curr_modules[name] - prev_modules[name]) >= 0.5
    ]
    if changed:
        reasons.append("模块人日变化：" + "；".join(changed[:5]))

    prev_days = int(previous.get("deadline_days") or 0)
    curr_days = int(current.get("deadline_days") or 0)
    if curr_days != prev_days:
        reasons.append(f"期望工期 {prev_days} → {curr_days} 天")
    if previous.get("category") and current.get("category") != previous.get("category"):
        reasons.append(
            f"需求类别 {previous.get('category_label')} → {current.get('category_label')}"
        )
    if not reasons:
        reasons.append("本轮模块与上一轮基本一致，价格差异来自模块人日或范围细节")
    return {
        "previous_quote_id": previous.get("id"),
        "previous_suggested_price": prev_amount,
        "delta": delta,
        "delta_pct": pct,
        "reasons": reasons,
    }
