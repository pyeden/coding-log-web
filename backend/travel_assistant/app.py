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
        return build_plan(
            destination=request.destination,
            start_date=request.start_date,
            end_date=request.end_date,
            budget=request.budget,
            travelers=request.travelers,
            preferences=request.preferences,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
