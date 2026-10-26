"""高德 Web 服务封装：环境变量、坐标转换、路线、POI 与导航链接。

密钥只从仓库根目录 .env 或进程环境读取，不写日志、不回传给前端。
所有调用都可能失败，调用方必须自行降级。
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import urllib.request
from urllib.parse import quote, urlencode

AMAP_HOST = "https://restapi.amap.com"


def load_root_env() -> None:
    """读取仓库根目录 .env（不提交到 git）；已存在的环境变量优先。"""
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


load_root_env()

AMAP_KEY = os.environ.get("AMAP_JS_KEY", "").strip()
AMAP_SECURITY_CODE = os.environ.get("AMAP_SECURITY_CODE", "").strip()
AMAP_WEB_KEY = os.environ.get("AMAP_WEB_KEY", "").strip()
AMAP_WEB_SECRET = os.environ.get("AMAP_WEB_SECRET", "").strip()


def amap_web_get(path: str, params: dict, timeout: float = 6) -> dict:
    """调用高德 Web 服务（带数字签名）。无 key 或网络失败时抛异常。"""
    if not AMAP_WEB_KEY:
        raise RuntimeError("AMAP_WEB_KEY_NOT_CONFIGURED")
    query = {k: v for k, v in params.items() if v is not None}
    query["key"] = AMAP_WEB_KEY
    query["output"] = "json"
    if AMAP_WEB_SECRET:
        raw = "&".join(f"{k}={query[k]}" for k in sorted(query))
        query["sig"] = hashlib.md5((raw + AMAP_WEB_SECRET).encode("utf-8")).hexdigest()
    url = f"{AMAP_HOST}/{path}?{urlencode(query)}"
    with urllib.request.urlopen(url, timeout=timeout) as response:
        data = json.load(response)
    if isinstance(data, dict) and data.get("status") not in (None, "1", 1):
        raise RuntimeError(data.get("info") or "AMAP_ERROR")
    return data


def wgs84_to_gcj02(lng: float, lat: float) -> tuple[float, float]:
    """WGS-84 → GCJ-02（高德坐标系）。"""
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


def haversine_m(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    """两点球面距离（米）。"""
    rad = math.radians
    dlat = rad(lat2 - lat1)
    dlon = rad(lng2 - lng1)
    h = math.sin(dlat / 2) ** 2 + math.cos(rad(lat1)) * math.cos(rad(lat2)) * math.sin(dlon / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(h))


_DRIVE_CACHE: dict = {}


def driving(origin: tuple, destination: tuple):
    """两点驾车信息：km / min / tolls / lights。"""
    key = (origin[0], origin[1], destination[0], destination[1])
    if key in _DRIVE_CACHE:
        return _DRIVE_CACHE[key]
    result = None
    if AMAP_WEB_KEY:
        try:
            data = amap_web_get("v3/direction/driving", {
                "origin": f"{origin[0]:.6f},{origin[1]:.6f}",
                "destination": f"{destination[0]:.6f},{destination[1]:.6f}",
                "strategy": 0,
                "extensions": "base",
            })
            paths = ((data.get("route") or {}).get("paths") or [])
            if data.get("status") == "1" and paths:
                path = paths[0]
                distance = int(path.get("distance") or 0)
                duration = int(path.get("duration") or 0)
                if distance:
                    result = {
                        "km": round(distance / 1000, 1),
                        "min": max(1, round(duration / 60)),
                        "tolls": int(path.get("tolls") or 0),
                        "lights": int(path.get("traffic_lights") or 0),
                    }
        except Exception:
            result = None
    _DRIVE_CACHE[key] = result
    return result


def geocode_origin(origin: str, city: str = ""):
    """把地名解析为 GCJ-02 坐标。"""
    if not origin or not AMAP_WEB_KEY:
        return None
    try:
        data = amap_web_get("v3/geocode/geo", {"address": origin, "city": city})
        geocodes = data.get("geocodes") or []
        if data.get("status") == "1" and geocodes:
            lng, lat = geocodes[0]["location"].split(",")
            return float(lng), float(lat)
    except Exception:
        return None
    return None


def enrich_routes(plan_data: dict, origin_name: str = "", origin_lng=None, origin_lat=None) -> dict:
    """用真实驾车路线替换直线距离（失败时保留原 distance_km）；支持出发点 → 首站路段。"""
    if not AMAP_WEB_KEY:
        return plan_data
    for day in plan_data.get("days", []):
        located = [
            item for item in day.get("items", [])
            if isinstance(item.get("lat"), (int, float)) and isinstance(item.get("lng"), (int, float))
        ]
        stops = [wgs84_to_gcj02(item["lng"], item["lat"]) for item in located]
        if len(stops) < 2:
            continue
        total_km = 0.0
        total_min = 0
        total_tolls = 0
        total_lights = 0
        segments = []
        ok = False
        titles = [item.get("name") or item.get("title") or "" for item in located]
        for index, (prev, cur) in enumerate(zip(stops, stops[1:])):
            segment = driving(prev, cur)
            if segment:
                total_km += segment["km"]
                total_min += segment["min"]
                total_tolls += segment["tolls"]
                total_lights += segment["lights"]
                ok = True
                segments.append({
                    "from": titles[index] if index < len(titles) else "",
                    "to": titles[index + 1] if index + 1 < len(titles) else "",
                    **segment,
                })
        if ok:
            day["route_km"] = round(total_km, 1)
            day["route_min"] = total_min
            day["tolls"] = total_tolls
            day["lights"] = total_lights
            day["segments"] = segments

    # 出发点 → 第一天首站
    day0 = (plan_data.get("days") or [None])[0]
    first_stop = None
    if day0:
        for item in day0.get("items", []):
            if isinstance(item.get("lat"), (int, float)) and isinstance(item.get("lng"), (int, float)):
                first_stop = wgs84_to_gcj02(item["lng"], item["lat"])
                break

    if origin_lng is not None and origin_lat is not None:
        origin_point = wgs84_to_gcj02(origin_lng, origin_lat)
        origin_display = origin_name or "当前定位"
    else:
        origin_point = geocode_origin(origin_name, plan_data.get("destination", "")) if origin_name else None
        origin_display = origin_name

    if origin_point:
        plan_data["origin"] = {
            "name": origin_display,
            "lng": round(origin_point[0], 6),
            "lat": round(origin_point[1], 6),
        }
        if first_stop:
            leg = driving(origin_point, first_stop)
            if leg and day0:
                plan_data["origin"]["to_first_km"] = leg["km"]
                plan_data["origin"]["to_first_min"] = leg["min"]
                plan_data["origin"]["tolls"] = leg["tolls"]
                plan_data["origin"]["lights"] = leg["lights"]
                day0["route_km"] = round((day0.get("route_km") or 0) + leg["km"], 1)
                day0["route_min"] = (day0.get("route_min") or 0) + leg["min"]
                day0["tolls"] = (day0.get("tolls") or 0) + leg["tolls"]
                day0["lights"] = (day0.get("lights") or 0) + leg["lights"]

    # 返程：最后一天最后一个景点 → 出发地
    last_day = (plan_data.get("days") or [None])[-1]
    last_stop = None
    if last_day:
        for item in reversed(last_day.get("items", [])):
            if isinstance(item.get("lat"), (int, float)) and isinstance(item.get("lng"), (int, float)):
                last_stop = wgs84_to_gcj02(item["lng"], item["lat"])
                break
    if origin_point and last_stop:
        back = driving(last_stop, origin_point)
        if back:
            plan_data["return_leg"] = {
                "from": "最后一站",
                "to": origin_display,
                **back,
            }
    return plan_data


def navigation_url(name: str, lat=None, lng=None, city: str = "") -> str:
    """高德 URI：有坐标用 marker，无坐标用关键词搜索。"""
    if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
        return (
            "https://uri.amap.com/marker?"
            + urlencode({
                "position": f"{lng:.6f},{lat:.6f}",
                "name": name,
                "src": "travel-assistant",
                "coordinate": "gaode",
                "callnative": "0",
            })
        )
    params = {"keyword": name, "src": "travel-assistant", "callnative": "0"}
    if city:
        params["city"] = city
    return "https://uri.amap.com/search?" + urlencode(params)


def search_url(keyword: str, city: str = "") -> str:
    params = {"keyword": keyword, "src": "travel-assistant", "callnative": "0"}
    if city:
        params["city"] = city
    return "https://uri.amap.com/search?" + urlencode(params)


def external_url(category: str, name: str, city: str = "") -> str:
    """点评/美团/携程等外部搜索链接；只做搜索跳转，不抓取。"""
    q = quote(name)
    if category == "food":
        return f"https://www.dianping.com/search/keyword/2/0_{q}"
    if category == "lodging":
        return f"https://hotels.ctrip.com/hotels/list?keyword={q}"
    if category in ("transport", "emergency"):
        return f"https://uri.amap.com/search?keyword={q}&src=travel-assistant&callnative=0"
    return f"https://www.baidu.com/s?wd={q}"
