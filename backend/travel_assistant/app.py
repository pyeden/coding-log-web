import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode
from urllib.request import Request as UrlRequest, urlopen

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from starlette.concurrency import run_in_threadpool

from models import TravelRequest
from planner import build_plan



def _load_root_env() -> None:
    """读取仓库根目录 .env（不提交到 git），供高德代理使用。"""
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    path = os.path.join(root, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_root_env()
AMAP_KEY = os.environ.get("AMAP_JS_KEY", "").strip()
AMAP_SECURITY_CODE = os.environ.get("AMAP_SECURITY_CODE", "").strip()
AMAP_ALLOWED_PREFIXES = ("v3/", "v4/", "v5/", "ws/")
AMAP_HOST = "https://restapi.amap.com"


app = FastAPI(
    title="Travel Assistant API",
    description="基于 FastAPI 的智能旅行助手：行程规划、预算估算与实用提示。",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


_DRIVE_CACHE: dict[tuple[float, float, float, float], tuple[float, int] | None] = {}


def _wgs84_to_gcj02(lng: float, lat: float) -> tuple[float, float]:
    """WGS-84 → GCJ-02（高德坐标系）。"""
    import math

    if not (73.66 < lng < 135.05 and 3.86 < lat < 53.55):
        return lng, lat
    a, ee = 6378245.0, 0.00669342162296594323
    dlat = -100.0 + 2.0 * (lng - 105.0) + 3.0 * (lat - 35.0) + 0.2 * (lat - 35.0) ** 2 + 0.1 * (lng - 105.0) * (lat - 35.0) + 0.2 * math.sqrt(abs(lng - 105.0))
    dlat += (20.0 * math.sin(6.0 * (lng - 105.0) * math.pi) + 20.0 * math.sin(2.0 * (lng - 105.0) * math.pi)) * 2.0 / 3.0
    dlat += (20.0 * math.sin((lat - 35.0) * math.pi) + 40.0 * math.sin((lat - 35.0) / 3.0 * math.pi)) * 2.0 / 3.0
    dlat += (160.0 * math.sin((lat - 35.0) / 12.0 * math.pi) + 320 * math.sin((lat - 35.0) * math.pi / 30.0)) * 2.0 / 3.0
    dlng = 300.0 + (lng - 105.0) + 2.0 * (lat - 35.0) + 0.1 * (lng - 105.0) ** 2 + 0.1 * (lng - 105.0) * (lat - 35.0) + 0.1 * math.sqrt(abs(lng - 105.0))
    dlng += (20.0 * math.sin(6.0 * (lng - 105.0) * math.pi) + 20.0 * math.sin(2.0 * (lng - 105.0) * math.pi)) * 2.0 / 3.0
    dlng += (20.0 * math.sin((lng - 105.0) * math.pi) + 40.0 * math.sin((lng - 105.0) / 3.0 * math.pi)) * 2.0 / 3.0
    dlng += (150.0 * math.sin((lng - 105.0) / 12.0 * math.pi) + 300.0 * math.sin((lng - 105.0) / 30.0 * math.pi)) * 2.0 / 3.0
    rad = lat / 180.0 * math.pi
    magic = 1 - ee * math.sin(rad) ** 2
    sqrt_magic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrt_magic) * math.pi)
    dlng = (dlng * 180.0) / (a / sqrt_magic * math.cos(rad) * math.pi)
    return lng + dlng, lat + dlat


def _amap_web_get(path: str, params: dict) -> dict:
    """调用高德 Web 服务（带数字签名）。"""
    import hashlib
    import urllib.request
    from urllib.parse import urlencode

    query = {k: v for k, v in params.items() if v is not None}
    query["key"] = AMAP_WEB_KEY
    query["output"] = "json"
    if AMAP_WEB_SECRET:
        raw = "&".join(f"{k}={query[k]}" for k in sorted(query))
        query["sig"] = hashlib.md5((raw + AMAP_WEB_SECRET).encode("utf-8")).hexdigest()
    url = f"https://restapi.amap.com/{path}?{urlencode(query)}"
    with urllib.request.urlopen(url, timeout=6) as response:
        return json.load(response)


def _driving(origin: tuple[float, float], destination: tuple[float, float]) -> tuple[float, int] | None:
    """两点驾车距离（km）与耗时（分钟）。"""
    key = (origin[0], origin[1], destination[0], destination[1])
    if key in _DRIVE_CACHE:
        return _DRIVE_CACHE[key]
    result = None
    if AMAP_WEB_KEY:
        try:
            data = _amap_web_get("v3/direction/driving", {
                "origin": f"{origin[0]:.6f},{origin[1]:.6f}",
                "destination": f"{destination[0]:.6f},{destination[1]:.6f}",
                "strategy": 0,
                "extensions": "base",
            })
            if data.get("status") == "1" and data.get("routes"):
                route = data["routes"][0]
                result = (round(int(route["distance"]) / 1000, 1), max(1, round(int(route["time"]) / 60)))
        except Exception:
            result = None
    _DRIVE_CACHE[key] = result
    return result


def _enrich_routes(plan_data: dict) -> dict:
    """用真实驾车路线替换直线距离（失败时保留原 distance_km）。"""
    if not AMAP_WEB_KEY:
        return plan_data
    for day in plan_data.get("days", []):
        stops = [
            _wgs84_to_gcj02(item["lng"], item["lat"])
            for item in day.get("items", [])
            if isinstance(item.get("lat"), (int, float)) and isinstance(item.get("lng"), (int, float))
        ]
        if len(stops) < 2:
            continue
        total_km = 0.0
        total_min = 0
        ok = False
        for prev, cur in zip(stops, stops[1:]):
            segment = _driving(prev, cur)
            if segment:
                total_km += segment[0]
                total_min += segment[1]
                ok = True
        if ok:
            day["route_km"] = round(total_km, 1)
            day["route_min"] = total_min
    return plan_data


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
    return {"status": "ok", "service": "travel-assistant", "version": "1.0.0"}


@app.get("/api/travel/")
def index():
    return {
        "service": "travel-assistant",
        "endpoints": ["/api/travel/health", "/api/travel/plan", "/docs"],
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
        )
        return _enrich_routes(plan_data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
