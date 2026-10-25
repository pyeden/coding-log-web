from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import TravelRequest
from planner import build_plan

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
