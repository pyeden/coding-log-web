from datetime import date
from typing import List

from pydantic import BaseModel, Field


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
