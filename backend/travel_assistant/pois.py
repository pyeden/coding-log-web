"""附近推荐：AMap 周边搜索 + 城市静态数据兜底。

失败/无 key 时返回 source=fallback，HTTP 仍 200；不抓取、不承诺库存与价格。
"""

from __future__ import annotations

import time

from amap import (
    AMAP_WEB_KEY,
    amap_web_get,
    external_url,
    haversine_m,
    navigation_url,
    search_url,
    wgs84_to_gcj02,
)
from data import CITY_DATA, GENERIC

_CACHE: dict = {}
_TTL_SECONDS = 10 * 60

CATEGORIES = ("food", "lodging", "transport", "emergency")

_AMAP_TYPES = {
    "food": "050000",
    "lodging": "100000",
    "transport": "150000",
    "emergency": "090000|130100",
}

_EMERGENCY_NUMBERS = [
    {"name": "报警", "number": "110"},
    {"name": "急救", "number": "120"},
    {"name": "火警", "number": "119"},
    {"name": "交通事故", "number": "122"},
]

_SPICY_WORDS = ("辣", "火锅", "担担", "钵钵鸡", "毛血旺", "酸辣", "小面", "串串", "香锅", "水煮")
_SEAFOOD_WORDS = ("海鲜", "鱼", "虾", "蟹", "蚝", "贝", "海蛎", "鱿", "沙茶")


def _city_profile(destination: str) -> tuple[str, dict]:
    destination = (destination or "").strip()
    for name, data in CITY_DATA.items():
        if name in destination or destination in name:
            return name, data
    profile = dict(GENERIC)
    profile["foods"] = list(GENERIC["foods"])
    profile["attractions"] = list(GENERIC["attractions"])
    if destination:
        profile["hotel_area"] = f"{destination}市中心 / 交通便利区域"
    return destination or "当地", profile


def _text(value) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def _number(value):
    if value in (None, "", []):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number == int(number) else round(number, 1)


def _distance_label(distance_m) -> str:
    if distance_m is None:
        return "距离请以导航为准"
    if distance_m < 1200:
        return f"步行约 {max(1, round(distance_m / 80))} 分钟"
    return f"约 {distance_m / 1000:.1f} km"


def _dietary_keywords(dietary) -> str:
    words = set(dietary or [])
    if "vegetarian" in words:
        return "素食"
    if "halal" in words:
        return "清真"
    if "no_seafood" in words:
        return "家常菜"
    return ""


def _dietary_reason(dietary) -> str:
    labels = {
        "vegetarian": "素食",
        "halal": "清真",
        "no_spicy": "不辣",
        "no_seafood": "不吃海鲜",
        "nut_allergy": "坚果过敏",
    }
    chosen = [labels[item] for item in (dietary or []) if item in labels]
    if not chosen:
        return ""
    return "已按忌口（" + "、".join(chosen) + "）筛选，点单前请再与店家确认"


def _open_status(biz: dict) -> str:
    for key in ("open_time", "opentime2", "opentime"):
        value = _text(biz.get(key))
        if value:
            return f"参考：{value}"
    return "营业时间参考商家"


def _parse_poi(poi: dict, index: int, category: str, dietary) -> dict | None:
    name = _text(poi.get("name"))
    if not name:
        return None
    location = _text(poi.get("location"))
    lat = lng = None
    if "," in location:
        try:
            lng_s, lat_s = location.split(",", 1)
            lng, lat = float(lng_s), float(lat_s)
        except ValueError:
            lat = lng = None
    biz = poi.get("biz_ext") if isinstance(poi.get("biz_ext"), dict) else {}
    raw_type = _text(poi.get("type"))
    type_name = raw_type.split(";")[-1] if raw_type else "本地服务"
    distance = _number(poi.get("distance"))
    rating = _text(biz.get("rating"))
    cost = _number(biz.get("cost"))
    reason_parts = [_distance_label(distance)]
    if rating:
        reason_parts.append(f"评分 {rating}（参考）")
    if cost is not None:
        reason_parts.append(f"人均约 ¥{cost}（参考）")
    dietary_reason = _dietary_reason(dietary) if category == "food" else ""
    if dietary_reason:
        reason_parts.append(dietary_reason)
    return {
        "id": f"poi-{index}",
        "category": category,
        "name": name,
        "type": type_name,
        "address": _text(poi.get("address")) or "地址参考导航",
        "distance_m": distance,
        "rating": rating or None,
        "cost": cost,
        "cost_estimated": cost is not None,
        "open_status": _open_status(biz),
        "lat": lat,
        "lng": lng,
        "reason": " · ".join(reason_parts),
        "navigation_url": navigation_url(name, lat, lng),
        "external_url": external_url(category, name),
    }


def _fetch_amap(category: str, lat: float, lng: float, radius: int, destination: str, dietary, limit: int):
    gcj_lng, gcj_lat = wgs84_to_gcj02(lng, lat)
    params = {
        "location": f"{gcj_lng:.6f},{gcj_lat:.6f}",
        "types": _AMAP_TYPES[category],
        "radius": radius,
        "offset": limit,
        "page": 1,
        "extensions": "all",
        "sortrule": "distance",
    }
    keywords = _dietary_keywords(dietary)
    if category == "food" and keywords:
        params["keywords"] = keywords
    if category == "emergency":
        params["keywords"] = "医院|药店|派出所"
    if destination:
        params["city"] = destination
    data = amap_web_get("v3/place/around", params, timeout=6)
    pois = data.get("pois") or []
    items = []
    for poi in pois:
        if not isinstance(poi, dict):
            continue
        item = _parse_poi(poi, len(items) + 1, category, dietary)
        if item:
            items.append(item)
        if len(items) >= limit:
            break
    return items


def _fallback_foods(city: str, profile: dict, dietary) -> list:
    words = set(dietary or [])
    foods = list(profile.get("foods") or [])
    if "vegetarian" in words:
        foods = [f"{city}素食餐厅", "寺院素斋", "菌菇豆腐家常菜"]
    elif "halal" in words:
        foods = [f"{city}清真餐厅", "兰州牛肉面", "新疆餐厅"]
    else:
        if "no_spicy" in words:
            foods = [item for item in foods if not any(word in item for word in _SPICY_WORDS)]
        if "no_seafood" in words:
            foods = [item for item in foods if not any(word in item for word in _SEAFOOD_WORDS)]
        if not foods:
            foods = ["清汤面 / 粥铺", "蒸菜馆", "家常菜馆"]
    return foods or ["当地特色菜"]


def _fallback_items(category: str, city: str, lat: float, lng: float, budget, dietary, limit: int) -> list:
    profile = _city_profile(city)[1]
    dietary_reason = _dietary_reason(dietary) if category == "food" else ""
    hotel_area = profile.get("hotel_area") or f"{city}市中心"
    items = []

    if category == "food":
        for food in _fallback_foods(city, profile, dietary)[:limit]:
            items.append({
                "id": f"poi-{len(items) + 1}",
                "category": "food",
                "name": food,
                "type": "本地特色",
                "address": f"{city}（具体门店请导航搜索）",
                "distance_m": None,
                "rating": None,
                "cost": _number(budget),
                "cost_estimated": budget is not None,
                "open_status": "营业时间参考商家",
                "lat": None,
                "lng": None,
                "reason": "静态推荐 · 出发前请核实营业信息" + (f" · {dietary_reason}" if dietary_reason else ""),
                "navigation_url": search_url(food, city),
                "external_url": external_url("food", food, city),
            })
    elif category == "lodging":
        options = [
            (f"{city} · {hotel_area}", "住宿区域", "交通便利、餐饮集中，适合作为落脚点"),
            (f"{city}地铁沿线连锁酒店", "连锁酒店", "换乘方便，适合多日行程"),
            (f"{city}经济型连锁酒店", "连锁酒店", "预算友好，建议提前比价"),
        ]
        for name, type_name, reason in options[:limit]:
            items.append({
                "id": f"poi-{len(items) + 1}",
                "category": "lodging",
                "name": name,
                "type": type_name,
                "address": hotel_area,
                "distance_m": None,
                "rating": None,
                "cost": None,
                "cost_estimated": False,
                "open_status": "库存/价格以平台为准",
                "lat": None,
                "lng": None,
                "reason": reason + "（静态推荐）",
                "navigation_url": search_url(name, city),
                "external_url": external_url("lodging", name, city),
            })
    elif category == "transport":
        options = [
            ("地铁站（就近）", "地铁", "市区出行优先，避开高峰拥堵"),
            ("公交站（就近）", "公交", "短途接驳，注意末班时间"),
            ("出租车 / 网约车上车点", "打车", "老人小孩或赶时间时更省力"),
        ]
        for name, type_name, reason in options[:limit]:
            items.append({
                "id": f"poi-{len(items) + 1}",
                "category": "transport",
                "name": name,
                "type": type_name,
                "address": f"{city}（请用导航搜索最近站点）",
                "distance_m": None,
                "rating": None,
                "cost": None,
                "cost_estimated": False,
                "open_status": "运营时间参考当地公告",
                "lat": None,
                "lng": None,
                "reason": reason + "（静态推荐）",
                "navigation_url": search_url(name, city),
                "external_url": external_url("transport", name, city),
            })
    else:
        phone_items = [
            ("报警电话 110", "110"),
            ("急救电话 120", "120"),
            ("火警电话 119", "119"),
            ("交通事故 122", "122"),
        ]
        for name, number in phone_items[: min(len(phone_items), limit)]:
            items.append({
                "id": f"poi-{len(items) + 1}",
                "category": "emergency",
                "name": name,
                "type": "紧急电话",
                "address": "全国通用",
                "distance_m": None,
                "rating": None,
                "cost": None,
                "cost_estimated": False,
                "open_status": "24 小时",
                "lat": lat,
                "lng": lng,
                "reason": "紧急情况优先拨打，说明所在位置",
                "navigation_url": "",
                "external_url": "",
            })
        extras = [
            (f"{city}就近医院（搜索）", "医院", "请用地图搜索最近的医院/急诊"),
            (f"{city}24 小时药店（搜索）", "药店", "夜间购药请先电话确认营业"),
        ]
        for name, type_name, reason in extras[: max(0, limit - len(items))]:
            items.append({
                "id": f"poi-{len(items) + 1}",
                "category": "emergency",
                "name": name,
                "type": type_name,
                "address": f"{city}（请用导航搜索）",
                "distance_m": None,
                "rating": None,
                "cost": None,
                "cost_estimated": False,
                "open_status": "营业时间参考机构公告",
                "lat": None,
                "lng": None,
                "reason": f"{reason}（静态推荐）",
                "navigation_url": search_url(type_name, city),
                "external_url": external_url("emergency", name, city),
            })
    return items[:limit]


def find_pois(category: str, lat: float, lng: float, radius: int = 1500, destination: str = "", dietary=None, budget=None, limit: int = 6) -> dict:
    """附近 POI；AMap 失败或无 key 时静态兜底。"""
    city = _city_profile(destination)[0] if destination else ""
    cache_key = (category, round(lat, 3), round(lng, 3), radius, city, tuple(dietary or ()), budget, limit)
    now = time.time()
    cached = _CACHE.get(cache_key)
    if cached and now - cached[0] < _TTL_SECONDS:
        return dict(cached[1])

    items = []
    source = "fallback"
    notice = ""
    if AMAP_WEB_KEY:
        try:
            items = _fetch_amap(category, lat, lng, radius, city, dietary, limit)
            if items:
                source = "amap"
            else:
                notice = "高德暂未返回结果，已改为静态推荐"
        except Exception:
            items = []
            notice = "高德服务暂不可用，已改为静态推荐"
    else:
        notice = "未配置高德 Web 服务 Key，当前为静态推荐"

    if not items:
        items = _fallback_items(category, city or "当地", lat, lng, budget, dietary, limit)
        source = "fallback"

    result = {
        "source": source,
        "items": items,
        "notice": notice,
        "emergency_numbers": _EMERGENCY_NUMBERS if category == "emergency" else [],
    }
    _CACHE[cache_key] = (now, result)
    return dict(result)


def find_emergency_hospital(lat: float, lng: float, destination: str = "") -> dict | None:
    """给行程的紧急入口找一个附近医院；失败返回 None。"""
    if not AMAP_WEB_KEY:
        return None
    city = _city_profile(destination)[0] if destination else ""
    try:
        items = _fetch_amap("emergency", lat, lng, 3000, city, [], 5)
    except Exception:
        return None
    for item in items:
        if item.get("category") == "emergency" and ("医院" in (item.get("type") or "") or "医院" in item.get("name", "")):
            return {
                "name": item["name"],
                "address": item.get("address") or "地址参考导航",
                "navigation_url": item.get("navigation_url") or "",
            }
    return None
