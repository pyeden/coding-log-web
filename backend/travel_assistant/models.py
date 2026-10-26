from __future__ import annotations

from datetime import date
from typing import List, Literal

from pydantic import BaseModel, Field

Companion = Literal["solo", "couple", "friends", "family_kids", "family_elderly"]
Pace = Literal["relaxed", "balanced", "packed"]
Dietary = Literal["vegetarian", "halal", "no_spicy", "no_seafood", "nut_allergy"]
Accessibility = Literal["step_free", "elevator", "avoid_long_walk"]
Transport = Literal["public", "taxi", "drive", "walk"]
LodgingBudget = Literal["budget", "comfort", "premium"]


class TravelProfile(BaseModel):
    """旅行画像；全部有默认值，旧请求不带 profile 也能工作。"""

    companions: Companion = Field("solo", description="同行人")
    pace: Pace = Field("balanced", description="行程节奏")
    dietary: List[Dietary] = Field(default_factory=list, description="忌口")
    accessibility: List[Accessibility] = Field(default_factory=list, description="无障碍需求")
    transport: Transport = Field("public", description="交通偏好")
    lodging_budget: LodgingBudget = Field("comfort", description="住宿预算档位")


class TravelRequest(BaseModel):
    destination: str = Field(..., min_length=1, max_length=40, description="目的地城市")
    start_date: date = Field(..., description="出发日期")
    end_date: date = Field(..., description="返程日期")
    budget: float = Field(..., gt=0, le=1_000_000, description="总预算（元）")
    travelers: int = Field(1, ge=1, le=10, description="出行人数")
    preferences: List[str] = Field(default_factory=list, description="偏好标签")
    origin: str = Field("", max_length=60, description="出发地名称（可选）")
    origin_lng: float | None = Field(None, description="出发地经度（WGS-84，可选）")
    origin_lat: float | None = Field(None, description="出发地纬度（WGS-84，可选）")
    profile: TravelProfile = Field(default_factory=TravelProfile, description="旅行画像（可选）")


class ShareRequest(BaseModel):
    plan: dict = Field(..., description="完整的 plan 响应 JSON")


class FeedbackRequest(BaseModel):
    plan_id: str = Field(..., min_length=1, max_length=100)
    item_id: str = Field("", max_length=100)
    helpful: bool | None = Field(None, description="是否有用")
    visited: bool | None = Field(None, description="是否实际去了")
    note: str = Field("", max_length=500, description="补充说明（请勿填写个人信息）")
