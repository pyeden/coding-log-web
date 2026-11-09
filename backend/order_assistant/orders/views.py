import json
from datetime import datetime

from django.db import connection, transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import llm
from .models import PriceBook, Quote, Requirement, RequirementRound
from .pricing import (
    CURRENCY,
    DEFAULT_CATALOG,
    PRICING_VERSION,
    catalog_map,
    compare_quotes,
    fallback_modules,
    price_modules,
)


def _json(data, status=200):
    return JsonResponse(data, status=status, json_dumps_params={"ensure_ascii": False})


def _error(code, status=400, **extra):
    payload = {"error": code}
    payload.update(extra)
    return _json(payload, status=status)


def _parse_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return None


def _get_catalog():
    try:
        rows = list(PriceBook.objects.filter(active=True))
        if rows:
            return catalog_map(rows)
    except Exception:
        pass
    return catalog_map(DEFAULT_CATALOG)


def _clean_str(value, max_length, field, errors, required=False):
    if value is None:
        value = ""
    if not isinstance(value, str):
        errors[field] = "必须为字符串"
        return ""
    value = value.strip()
    if required and not value:
        errors[field] = "不能为空"
    if len(value) > max_length:
        errors[field] = f"长度不能超过 {max_length} 字"
    return value


def _clean_deliverables(value, errors):
    if value is None:
        return []
    if not isinstance(value, list):
        errors["deliverables"] = "必须为字符串数组"
        return []
    items = []
    for raw in value:
        if not isinstance(raw, str):
            errors["deliverables"] = "交付物必须为字符串"
            return []
        text = raw.strip()
        if not text:
            continue
        if len(text) > 40:
            errors["deliverables"] = "单项交付物不能超过 40 字"
            return []
        items.append(text)
    if len(items) > 20:
        errors["deliverables"] = "交付物不能超过 20 项"
    return items


def validate_requirement_payload(payload, catalog, partial=False):
    errors = {}
    cleaned = {}

    if not partial or "title" in payload:
        cleaned["title"] = _clean_str(payload.get("title"), 120, "title", errors, required=True)
        if "title" not in errors and len(cleaned["title"]) < 2:
            errors["title"] = "项目名称至少 2 个字"
    if not partial or "description" in payload:
        cleaned["description"] = _clean_str(
            payload.get("description"), 5000, "description", errors, required=True
        )
        if "description" not in errors and len(cleaned["description"]) < 10:
            errors["description"] = "需求描述至少 10 个字"
    if not partial or "client_name" in payload:
        cleaned["client_name"] = _clean_str(
            payload.get("client_name"), 80, "client_name", errors
        )
    if not partial or "contact" in payload:
        cleaned["contact"] = _clean_str(payload.get("contact"), 120, "contact", errors)
    if not partial or "notes" in payload:
        cleaned["notes"] = _clean_str(payload.get("notes"), 1000, "notes", errors)
    if not partial or "deliverables" in payload:
        cleaned["deliverables"] = _clean_deliverables(payload.get("deliverables"), errors)
    if not partial or "deadline_days" in payload:
        value = payload.get("deadline_days", 30)
        try:
            value = int(value)
        except (TypeError, ValueError):
            errors["deadline_days"] = "必须为整数天数"
            value = 30
        if not isinstance(value, int) or isinstance(value, bool):
            errors["deadline_days"] = "必须为整数天数"
        elif value < 1 or value > 365:
            errors["deadline_days"] = "工期需在 1–365 天之间"
        cleaned["deadline_days"] = value
    if not partial or "budget_expectation" in payload:
        value = payload.get("budget_expectation")
        if value in (None, ""):
            cleaned["budget_expectation"] = None
        else:
            try:
                value = int(value)
            except (TypeError, ValueError):
                errors["budget_expectation"] = "预算必须为整数金额"
                value = None
            if isinstance(value, bool):
                errors["budget_expectation"] = "预算必须为整数金额"
                value = None
            elif value is not None and (value < 0 or value > 100_000_000):
                errors["budget_expectation"] = "预算需在 0–1 亿元之间"
            cleaned["budget_expectation"] = value
    if "category" in payload and payload.get("category"):
        category = payload.get("category")
        if category not in catalog:
            errors["category"] = "未知的需求类别"
        cleaned["category"] = category
    elif not partial:
        cleaned["category"] = ""

    return cleaned, errors


def _quote_number():
    today = timezone.localdate()
    prefix = f"Q{today:%Y%m%d}-"
    seq = Quote.objects.filter(quote_no__startswith=prefix).count() + 1
    while Quote.objects.filter(quote_no=f"{prefix}{seq:04d}").exists():
        seq += 1
    return f"{prefix}{seq:04d}"


def _create_quote(req, round_obj, catalog):
    decomposition = llm.decompose(
        title=req.title,
        description=round_obj.description,
        deliverables=round_obj.deliverables,
        deadline_days=round_obj.deadline_days,
        category=req.category if req.category != "other" else None,
        categories=list(catalog.keys()),
    )
    if decomposition.get("ok"):
        modules = decomposition.get("modules") or []
        source = "llm"
        model_name = decomposition.get("model") or ""
        summary = decomposition.get("summary") or ""
        confidence_hint = decomposition.get("confidence")
        extra_assumptions = decomposition.get("assumptions") or []
        latency_ms = int(decomposition.get("latency_ms") or 0)
        raw = decomposition.get("raw") or {}
    else:
        fallback = fallback_modules(
            title=req.title,
            description=round_obj.description,
            deliverables=round_obj.deliverables,
            category=req.category if req.category != "other" else None,
            catalog=catalog,
        )
        modules = fallback["modules"]
        source = "fallback"
        model_name = ""
        summary = fallback["summary"]
        confidence_hint = fallback["confidence"]
        extra_assumptions = fallback["assumptions"]
        latency_ms = 0
        raw = {
            "error": decomposition.get("error"),
            "detail": decomposition.get("detail"),
            "model": decomposition.get("model"),
        }

    est = price_modules(
        modules=modules,
        catalog=catalog,
        category=req.category if req.category != "other" else None,
        contact=req.contact,
        deadline_days=round_obj.deadline_days,
        budget_expectation=req.budget_expectation,
        decomposition_source=source,
        decomposition_model=model_name,
        decomposition_summary=summary,
        confidence_hint=confidence_hint,
        extra_assumptions=extra_assumptions,
    )

    round_obj.modules = est.modules
    round_obj.decomposition_source = source
    round_obj.decomposition_model = model_name
    round_obj.decomposition_summary = summary
    round_obj.save(update_fields=[
        "modules", "decomposition_source", "decomposition_model", "decomposition_summary"
    ])

    if req.category == "other" and est.category != "other":
        req.category = est.category
        req.save(update_fields=["category", "updated_at"])

    return Quote.objects.create(
        round=round_obj,
        quote_no=_quote_number(),
        currency=est.currency,
        amount_min=est.amount_min,
        amount_max=est.amount_max,
        suggested_price=est.suggested_price,
        confidence=est.confidence,
        pricing_version=est.pricing_version,
        market_basis=est.market_basis,
        breakdown=est.breakdown,
        assumptions=est.assumptions,
        decomposition_source=source,
        decomposition_model=model_name,
        module_count=est.module_count,
        llm_latency_ms=latency_ms,
        llm_raw=raw,
        generated_at=timezone.now(),
    )


def _quote_dict(quote):
    if quote is None:
        return None
    round_obj = quote.round
    requirement = round_obj.requirement
    return {
        "id": quote.id,
        "quote_no": quote.quote_no,
        "round_no": round_obj.round_no,
        "currency": quote.currency,
        "amount_min": quote.amount_min,
        "amount_max": quote.amount_max,
        "suggested_price": quote.suggested_price,
        "effective_amount": quote.effective_amount,
        "confidence": quote.confidence,
        "pricing_version": quote.pricing_version,
        "market_basis": quote.market_basis,
        "breakdown": quote.breakdown,
        "assumptions": quote.assumptions,
        "decomposition_source": quote.decomposition_source,
        "decomposition_model": quote.decomposition_model,
        "module_count": quote.module_count,
        "llm_latency_ms": quote.llm_latency_ms,
        "modules": [
            {
                "name": row.get("name") or row.get("phase"),
                "days": row.get("days"),
                "category": row.get("category"),
                "category_label": row.get("category_label"),
            }
            for row in (quote.breakdown or [])
            if row.get("kind") == "module"
        ],
        "status": quote.status,
        "adjusted_amount": quote.adjusted_amount,
        "adjust_reason": quote.adjust_reason,
        "generated_at": quote.generated_at.isoformat(),
        "deliverable_count": len(round_obj.deliverables or []),
        "deadline_days": round_obj.deadline_days,
        "complexity": _complexity_of(round_obj),
        "category": requirement.category,
        "category_label": requirement.category_label,
    }


def _complexity_of(round_obj):
    modules = round_obj.modules or []
    if modules:
        values = [float(item.get("complexity", 1)) for item in modules if isinstance(item, dict)]
        if values:
            return round(sum(values) / len(values), 2)
    from .pricing import complexity_score

    value, _ = complexity_score(round_obj.description, round_obj.deliverables)
    return value


def _round_dict(round_obj):
    quote = getattr(round_obj, "quote", None)
    return {
        "round_no": round_obj.round_no,
        "description": round_obj.description,
        "deliverables": round_obj.deliverables,
        "deadline_days": round_obj.deadline_days,
        "change_note": round_obj.change_note,
        "modules": round_obj.modules or [],
        "decomposition_source": round_obj.decomposition_source,
        "decomposition_model": round_obj.decomposition_model,
        "decomposition_summary": round_obj.decomposition_summary,
        "submitted_at": round_obj.submitted_at.isoformat(),
        "quote": _quote_dict(quote),
    }


def _latest_quote(req):
    latest_round = req.rounds.order_by("-round_no").first()
    if not latest_round:
        return None
    return getattr(latest_round, "quote", None)


def _requirement_summary(req):
    quote = _latest_quote(req)
    return {
        "id": req.id,
        "public_id": req.public_id,
        "title": req.title,
        "client_name": req.client_name,
        "category": req.category,
        "category_label": req.category_label,
        "status": req.status,
        "status_label": req.status_label,
        "current_round": req.current_round,
        "latest_quote": None
        if quote is None
        else {
            "id": quote.id,
            "quote_no": quote.quote_no,
            "suggested_price": quote.suggested_price,
            "amount_min": quote.amount_min,
            "amount_max": quote.amount_max,
            "currency": quote.currency,
            "generated_at": quote.generated_at.isoformat(),
        },
        "created_at": req.created_at.isoformat(),
        "updated_at": req.updated_at.isoformat(),
    }


def _requirement_detail(req):
    data = _requirement_summary(req)
    data.update(
        {
            "contact": req.contact,
            "description": req.description,
            "deliverables": req.deliverables,
            "deadline_days": req.deadline_days,
            "budget_expectation": req.budget_expectation,
            "notes": req.notes,
            "rounds": [_round_dict(r) for r in req.rounds.order_by("round_no")],
        }
    )
    quote = _latest_quote(req)
    data["latest_quote"] = _quote_dict(quote)
    return data


def _find_requirement(public_id):
    try:
        return Requirement.objects.get(public_id=public_id)
    except Requirement.DoesNotExist:
        return None


@require_http_methods(["GET"])
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_status = "ok"
    except Exception:
        db_status = "error"
    return _json(
        {
            "ok": db_status == "ok",
            "version": "1.0.0",
            "pricing_version": PRICING_VERSION,
            "currency": CURRENCY,
            "db": db_status,
            "time": timezone.now().isoformat(),
        }
    )


@require_http_methods(["GET"])
def meta(request):
    catalog = _get_catalog()
    categories = [
        {
            "key": item["category"],
            "label": item["label"],
            "day_rate": item["day_rate"],
            "base_days": item["base_days"],
        }
        for item in catalog.values()
        if item["category"] != "other"
    ]
    categories.sort(key=lambda x: x["key"])
    return _json(
        {
            "currency": CURRENCY,
            "pricing_version": PRICING_VERSION,
            "categories": categories,
        }
    )


@csrf_exempt
@require_http_methods(["GET", "POST"])
def requirements(request):
    if request.method == "GET":
        raw_ids = request.GET.get("ids", "").strip()
        if not raw_ids:
            return _error("missing_ids", 400)
        ids = [item.strip() for item in raw_ids.split(",") if item.strip()][:50]
        rows = Requirement.objects.filter(public_id__in=ids)
        by_id = {row.public_id: row for row in rows}
        items = [_requirement_summary(by_id[pid]) for pid in ids if pid in by_id]
        return _json({"items": items, "total": len(items)})

    payload = _parse_body(request)
    if payload is None:
        return _error("invalid_json", 400)
    catalog = _get_catalog()
    cleaned, errors = validate_requirement_payload(payload, catalog)
    if errors:
        return _error("validation_error", 400, fields=errors)

    with transaction.atomic():
        req = Requirement.objects.create(
            title=cleaned["title"],
            client_name=cleaned.get("client_name", ""),
            contact=cleaned.get("contact", ""),
            category=cleaned.get("category") or "other",
            description=cleaned["description"],
            deliverables=cleaned.get("deliverables", []),
            deadline_days=cleaned.get("deadline_days", 30),
            budget_expectation=cleaned.get("budget_expectation"),
            notes=cleaned.get("notes", ""),
            status="quoted",
            current_round=1,
        )
        round_obj = RequirementRound.objects.create(
            requirement=req,
            round_no=1,
            description=req.description,
            deliverables=req.deliverables,
            deadline_days=req.deadline_days,
            change_note="首次提交",
        )
        _create_quote(req, round_obj, catalog)
        req.refresh_from_db()

    return _json(_requirement_detail(req), 201)


@csrf_exempt
@require_http_methods(["GET", "PATCH"])
def requirement_detail(request, public_id):
    req = _find_requirement(public_id)
    if req is None:
        return _error("not_found", 404)

    if request.method == "GET":
        return _json(_requirement_detail(req))

    if req.status in {"closed", "cancelled"}:
        return _error("locked", 409)

    payload = _parse_body(request)
    if payload is None:
        return _error("invalid_json", 400)
    catalog = _get_catalog()
    cleaned, errors = validate_requirement_payload(payload, catalog, partial=True)
    if errors:
        return _error("validation_error", 400, fields=errors)

    for field, value in cleaned.items():
        if field == "category" and not value:
            continue
        setattr(req, field, value)
    req.save()
    return _json(_requirement_detail(req))


@csrf_exempt
@require_http_methods(["POST"])
def requirement_rounds(request, public_id):
    req = _find_requirement(public_id)
    if req is None:
        return _error("not_found", 404)
    if req.status in {"closed", "cancelled"}:
        return _error("locked", 409)

    payload = _parse_body(request)
    if payload is None:
        return _error("invalid_json", 400)

    catalog = _get_catalog()
    errors = {}
    description = _clean_str(
        payload.get("description"), 5000, "description", errors, required=True
    )
    if "description" not in errors and len(description) < 10:
        errors["description"] = "需求描述至少 10 个字"
    deliverables = _clean_deliverables(payload.get("deliverables"), errors)
    try:
        deadline_days = int(payload.get("deadline_days", req.deadline_days))
    except (TypeError, ValueError):
        errors["deadline_days"] = "必须为整数天数"
        deadline_days = req.deadline_days
    if deadline_days < 1 or deadline_days > 365:
        errors["deadline_days"] = "工期需在 1–365 天之间"
    change_note = _clean_str(payload.get("change_note"), 300, "change_note", errors)
    category = payload.get("category")
    if category and category not in catalog:
        errors["category"] = "未知的需求类别"
    if errors:
        return _error("validation_error", 400, fields=errors)

    previous_quote = _latest_quote(req)
    previous_data = _quote_dict(previous_quote) if previous_quote else None

    with transaction.atomic():
        next_round_no = req.current_round + 1
        req.description = description
        req.deliverables = deliverables
        req.deadline_days = deadline_days
        req.current_round = next_round_no
        if category:
            req.category = category
        req.save()
        round_obj = RequirementRound.objects.create(
            requirement=req,
            round_no=next_round_no,
            description=description,
            deliverables=deliverables,
            deadline_days=deadline_days,
            change_note=change_note,
        )
        new_quote = _create_quote(req, round_obj, catalog)
        req.refresh_from_db()

    current_data = _quote_dict(new_quote)
    comparison = compare_quotes(previous_data, current_data)

    return _json(
        {
            "round": _round_dict(round_obj),
            "quote": current_data,
            "comparison": comparison,
            "requirement": _requirement_detail(req),
        },
        201,
    )


@csrf_exempt
@require_http_methods(["POST"])
def requirement_status(request, public_id):
    req = _find_requirement(public_id)
    if req is None:
        return _error("not_found", 404)
    payload = _parse_body(request)
    if payload is None:
        return _error("invalid_json", 400)
    target = payload.get("status")
    transitions = {
        "quoted": {"confirmed", "cancelled"},
        "confirmed": {"in_progress", "cancelled"},
        "in_progress": {"closed", "cancelled"},
        "closed": set(),
        "cancelled": set(),
    }
    if target not in transitions:
        return _error("invalid_transition", 409, allowed=[])
    if target != req.status and target not in transitions.get(req.status, set()):
        return _error(
            "invalid_transition", 409, allowed=sorted(transitions.get(req.status, set()))
        )
    if target != req.status:
        req.status = target
        req.save(update_fields=["status", "updated_at"])
    return _json(_requirement_detail(req))


@require_http_methods(["GET"])
def quotes(request):
    requirement = request.GET.get("requirement", "").strip()
    rows = Quote.objects.select_related("round__requirement").order_by("-generated_at")
    if requirement:
        rows = rows.filter(round__requirement__public_id=requirement)
    limit = min(max(int(request.GET.get("limit", 50) or 50), 1), 200)
    return _json({"items": [_quote_dict(q) for q in rows[:limit]]})


@require_http_methods(["GET"])
def quote_detail(request, quote_id):
    try:
        quote = Quote.objects.select_related("round__requirement").get(pk=quote_id)
    except Quote.DoesNotExist:
        return _error("not_found", 404)
    return _json(_quote_dict(quote))
