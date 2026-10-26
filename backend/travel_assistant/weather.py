"""天气与穿衣建议：AMap 预报 + 季节规则兜底。

无 key、接口失败或日期超出预报范围时都返回 source=fallback，HTTP 200。
"""

from __future__ import annotations

import time
from datetime import date, timedelta

from amap import AMAP_WEB_KEY, amap_web_get

_CACHE: dict = {}
_TTL_SECONDS = 30 * 60

# 月份基准（全国大致平均）: (最低温, 最高温, 天气, 降雨概率, 紫外线)
_MONTH_RULES = {
    1: (-6, 4, "晴", 10, "弱"),
    2: (-3, 8, "多云", 15, "弱"),
    3: (4, 16, "多云", 20, "中等"),
    4: (10, 22, "晴", 25, "中等"),
    5: (15, 27, "多云", 35, "中等"),
    6: (20, 31, "多云", 45, "强"),
    7: (23, 34, "雷阵雨", 60, "强"),
    8: (22, 32, "多云", 50, "强"),
    9: (17, 28, "晴", 30, "中等"),
    10: (10, 22, "晴", 20, "中等"),
    11: (3, 15, "多云", 15, "弱"),
    12: (-4, 6, "晴", 10, "弱"),
}

_CITY_OFFSET = {
    "北京": -1,
    "上海": 1,
    "成都": 2,
    "西安": 0,
    "杭州": 1,
    "广州": 6,
    "深圳": 6,
    "重庆": 4,
    "南京": 1,
    "厦门": 5,
}

_RAIN_PROB = (
    ("雷阵雨", 85),
    ("暴雨", 90),
    ("大雨", 85),
    ("中雨", 75),
    ("小雨", 65),
    ("阵雨", 60),
    ("雨", 60),
    ("雪", 55),
    ("阴", 40),
    ("多云", 25),
    ("晴", 5),
)


def _city_offset(destination: str) -> int:
    for name, offset in _CITY_OFFSET.items():
        if name in destination or destination in name:
            return offset
    return 0


def fallback_weather(destination: str, day: date) -> dict:
    tmin, tmax, text, rain_prob, uv = _MONTH_RULES.get(day.month, _MONTH_RULES[10])
    offset = _city_offset(destination)
    if 11 <= day.month or day.month <= 2:
        text = "晴冷" if offset <= 0 else text
    return {
        "text": text,
        "temp_min": tmin + offset,
        "temp_max": tmax + offset,
        "rain_prob": rain_prob,
        "uv": uv,
        "source": "fallback",
    }


def _parse_day(value) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _rain_prob(text: str) -> int:
    for word, prob in _RAIN_PROB:
        if word in text:
            return prob
    return 20


def _uv(text: str, month: int) -> str:
    if "雨" in text or "阴" in text or "雪" in text:
        return "弱"
    if "晴" in text and month in (5, 6, 7, 8, 9):
        return "强"
    if "晴" in text:
        return "中等"
    return "弱"


def _geocode_adcode(destination: str) -> str:
    key = ("adcode", destination)
    cached = _CACHE.get(key)
    now = time.time()
    if cached and now - cached[0] < 86400:
        return cached[1]
    adcode = ""
    try:
        data = amap_web_get("v3/geocode/geo", {"address": destination}, timeout=5)
        geocodes = data.get("geocodes") or []
        if geocodes:
            adcode = str(geocodes[0].get("adcode") or "")
    except Exception:
        adcode = ""
    _CACHE[key] = (now, adcode)
    return adcode


def get_weather(destination: str, when) -> dict:
    """返回天气 dict；任何异常都降级为季节规则。"""
    day = _parse_day(when)
    if day is None:
        return fallback_weather(destination, date.today())
    today = date.today()
    if not AMAP_WEB_KEY or day < today or day > today + timedelta(days=3):
        return fallback_weather(destination, day)

    cache_key = ("weather", destination, day.isoformat())
    now = time.time()
    cached = _CACHE.get(cache_key)
    if cached and now - cached[0] < _TTL_SECONDS:
        return dict(cached[1])

    result = None
    try:
        adcode = _geocode_adcode(destination)
        data = amap_web_get(
            "v3/weather/weatherInfo",
            {"city": adcode or destination, "extensions": "all"},
            timeout=5,
        )
        forecasts = data.get("forecasts") or []
        casts = (forecasts[0].get("casts") if forecasts else []) or []
        for cast in casts:
            if str(cast.get("date")) != day.isoformat():
                continue
            day_weather = str(cast.get("dayweather") or "").strip()
            night_weather = str(cast.get("nightweather") or "").strip()
            text = day_weather
            if night_weather and night_weather != day_weather:
                text = f"{day_weather}转{night_weather}"
            if not text:
                continue
            result = {
                "text": text,
                "temp_min": int(float(cast.get("nighttemp") or 0)),
                "temp_max": int(float(cast.get("daytemp") or 0)),
                "rain_prob": _rain_prob(text),
                "uv": _uv(text, day.month),
                "source": "amap",
            }
            break
    except Exception:
        result = None

    if not result:
        return fallback_weather(destination, day)
    _CACHE[cache_key] = (now, result)
    return dict(result)


def clothing_advice(weather: dict, pace: str = "balanced", companions: str = "solo", accessibility=()) -> str:
    """根据天气与画像给出一句穿衣建议（保证非空）。"""
    tmin = int(weather.get("temp_min") or 0)
    tmax = int(weather.get("temp_max") or 0)
    rain = int(weather.get("rain_prob") or 0)
    uv = str(weather.get("uv") or "")
    parts = []

    if tmax <= 5:
        parts.append("羽绒服或厚外套")
    elif tmax <= 12:
        parts.append("厚外套 + 毛衣")
    elif tmin <= 8 and tmax >= 15:
        parts.append("早晚温差大，建议薄外套")
    elif tmax >= 30:
        parts.append("短袖 + 透气衣物")
    elif tmax >= 24:
        parts.append("短袖或薄长袖")
    else:
        parts.append("长袖 + 薄外套")

    if rain >= 40 or "雨" in str(weather.get("text") or ""):
        parts.append("带折叠伞/轻便雨衣")
    if uv == "强":
        parts.append("注意防晒")
    if pace != "relaxed" or companions in ("solo", "friends"):
        parts.append("舒适步行鞋")
    if companions == "family_elderly" or "avoid_long_walk" in accessibility:
        parts.append("防滑鞋，减少长时间步行")
    if companions == "family_kids":
        parts.append("给孩子备一套换洗衣物")
    return "，".join(parts) + "。"
