import json
import logging
from datetime import date, datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode
from urllib.request import Request as UrlRequest, urlopen

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.concurrency import run_in_threadpool

from amap import (
    AMAP_KEY,
    AMAP_SECURITY_CODE,
    enrich_routes,
)
from models import FeedbackRequest, ShareRequest, TravelRequest
from planner import build_plan
from pois import CATEGORIES, find_pois
from store import append_feedback, get_share, save_share
from weather import get_weather

logger = logging.getLogger("travel_assistant")

AMAP_ALLOWED_PREFIXES = ("v3/", "v4/", "v5/", "ws/")
AMAP_HOST = "https://restapi.amap.com"
MAX_SHARE_BYTES = 512 * 1024

app = FastAPI(
    title="Travel Assistant API",
    description="基于 FastAPI 的智能旅行助手：画像行程、天气穿衣、附近推荐、分享与反馈。",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _amap_fetch(url: str, body: bytes | None, method: str, content_type: str):
    headers = {"Content-Type": content_type} if body else {}
    request = UrlRequest(url, data=body, method=method, headers=headers)
    try:
        with urlopen(request, timeout=12) as response:
            return response.read(), response.status, response.headers.get("Content-Type", "application/json")
    except HTTPError as exc:
        return exc.read(), exc.code, "application/json"
    except URLError as exc:
        payload = json.dumps({"status": "0", "info": "UPSTREAM_ERROR", "detail": str(exc)}).encode()
        return payload, 502, "application/json"


@app.api_route("/_AMapService/{path:path}", methods=["GET", "POST"])
async def amap_proxy(path: str, request: Request):
    """高德 JS API 安全密钥代理：前端 serviceHost 指向这里，密钥只在服务端拼接。"""
    if not AMAP_KEY or not AMAP_SECURITY_CODE:
        return Response(
            json.dumps({"status": "0", "info": "AMAP_NOT_CONFIGURED"}),
            status_code=400,
            media_type="application/json",
        )
    if not path.startswith(AMAP_ALLOWED_PREFIXES):
        return Response(
            json.dumps({"status": "0", "info": "AMAP_PATH_NOT_ALLOWED"}),
            status_code=404,
            media_type="application/json",
        )

    params = dict(parse_qsl(request.url.query, keep_blank_values=True))
    params["key"] = AMAP_KEY
    params["jscode"] = AMAP_SECURITY_CODE
    target = f"{AMAP_HOST}/{path}?{urlencode(params)}"
    body = await request.body() if request.method == "POST" else None
    content_type = request.headers.get("content-type", "application/json")

    content, status, media = await run_in_threadpool(_amap_fetch, target, body, request.method, content_type)
    return Response(content, status_code=status, media_type=media)


@app.get("/api/travel/health")
def health():
    return {"status": "ok", "service": "travel-assistant", "version": "2.0.0"}


@app.get("/api/travel/")
def index():
    return {
        "service": "travel-assistant",
        "version": "2.0.0",
        "endpoints": [
            "/api/travel/health",
            "/api/travel/plan",
            "/api/travel/poi",
            "/api/travel/weather",
            "/api/travel/share",
            "/api/travel/share/{id}",
            "/api/travel/feedback",
            "/docs",
        ],
    }


@app.post("/api/travel/plan")
def plan(request: TravelRequest):
    try:
        plan_data = build_plan(
            destination=request.destination,
            start_date=request.start_date,
            end_date=request.end_date,
            budget=request.budget,
            travelers=request.travelers,
            preferences=request.preferences,
            profile=request.profile,
        )
        return enrich_routes(plan_data, request.origin, request.origin_lng, request.origin_lat)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("plan generation failed")
        raise HTTPException(status_code=500, detail="生成行程失败，请稍后重试") from exc


@app.get("/api/travel/weather")
def weather_endpoint(
    destination: str = Query(..., min_length=1, max_length=40),
    day: str = Query(..., alias="date", description="YYYY-MM-DD"),
):
    try:
        wanted = date.fromisoformat(day[:10])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="date 需为 YYYY-MM-DD") from exc
    return get_weather(destination, wanted)


@app.get("/api/travel/poi")
def poi_endpoint(
    category: str = Query(..., description="food|lodging|transport|emergency"),
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius: int = Query(1500, description="米，最大 5000"),
    destination: str = Query("", max_length=40),
    dietary: str = Query("", max_length=100, description="逗号分隔"),
    budget: float | None = Query(None, ge=0, le=100000, description="人均预算"),
    limit: int = Query(6, description="1-12"),
):
    if category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="category 必须是 food/lodging/transport/emergency")
    radius = max(100, min(radius, 5000))
    limit = max(1, min(limit, 12))
    diet_list = [item.strip() for item in dietary.split(",") if item.strip()]
    return find_pois(
        category=category,
        lat=lat,
        lng=lng,
        radius=radius,
        destination=destination,
        dietary=diet_list,
        budget=budget,
        limit=limit,
    )


@app.post("/api/travel/share")
def share_endpoint(request: ShareRequest):
    payload = request.plan
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="plan 必须是对象")
    try:
        raw = json.dumps(payload, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="plan 不是合法 JSON") from exc
    if len(raw.encode("utf-8")) > MAX_SHARE_BYTES:
        raise HTTPException(status_code=413, detail="plan 过大")
    try:
        share_id = save_share(payload)
    except Exception as exc:
        logger.exception("save share failed")
        raise HTTPException(status_code=500, detail="保存分享失败，请稍后重试") from exc
    return {"id": share_id}


@app.get("/api/travel/share/{share_id}")
def shared_plan(share_id: str):
    payload = get_share(share_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="分享不存在或已过期")
    return JSONResponse(payload)


@app.post("/api/travel/feedback")
def feedback_endpoint(request: FeedbackRequest):
    note = "".join(ch for ch in request.note if ch >= " " or ch == "\n").strip()[:500]
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "plan_id": request.plan_id,
        "item_id": request.item_id,
        "helpful": request.helpful,
        "visited": request.visited,
        "note": note,
    }
    try:
        append_feedback(record)
    except Exception as exc:
        logger.exception("write feedback failed")
        raise HTTPException(status_code=500, detail="反馈保存失败，请稍后重试") from exc
    return {"ok": True}
