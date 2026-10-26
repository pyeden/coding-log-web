"""规则版旅行规划器 v2：画像驱动的行程、天气/穿衣、住宿、交通缓冲、打包与预算。

所有价格与营业时间均为参考估算，不构成预订/支付承诺。
"""

from __future__ import annotations

import math
import uuid
from datetime import date, timedelta

from amap import external_url, navigation_url, search_url
from data import CITY_DATA, GENERIC
from models import TravelProfile
from weather import clothing_advice, get_weather

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
LEVELS = ["经济", "舒适", "品质"]
HOTEL_MULT = {"经济": 0.6, "舒适": 1.0, "品质": 1.5}
FOOD_DAY = {"经济": 100, "舒适": 120, "品质": 220}
TRANSPORT_DAY = {"经济": 40, "舒适": 50, "品质": 80}
LODGING_LEVEL = {"budget": "经济", "comfort": "舒适", "premium": "品质"}

PACE_ATTRACTIONS = {"relaxed": 2, "balanced": 2, "packed": 3}
PACE_LABEL = {"relaxed": "轻松", "balanced": "适中", "packed": "紧凑"}
COMPANION_LABEL = {
    "solo": "独自出行",
    "couple": "情侣/夫妻",
    "friends": "朋友同行",
    "family_kids": "亲子家庭",
    "family_elderly": "带长辈",
}
TRANSPORT_LABEL = {"public": "地铁/公交", "taxi": "打车", "drive": "自驾", "walk": "步行"}
BUFFER_BASE = {"public": 30, "taxi": 20, "drive": 30, "walk": 15}
TRANSPORT_COST = {"public": 5, "taxi": 30, "drive": 40, "walk": 0}

CLOSED_WEEKDAYS = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4, "周六": 5, "周日": 6}

SPICY_WORDS = ("辣", "火锅", "担担", "钵钵鸡", "毛血旺", "酸辣", "小面", "串串", "香锅", "水煮")
SEAFOOD_WORDS = ("海鲜", "鱼", "虾", "蟹", "蚝", "贝", "海蛎", "鱿", "沙茶")
INDOOR_WORDS = ("博物馆", "美术馆", "艺术", "展览", "科技馆", "祠", "寺", "宫", "剧院", "商场")


def _distance_km(a: dict, b: dict) -> float:
    """两点球面距离（km），缺坐标返回 0。"""
    if not all(a.get(k) is not None for k in ("lat", "lng")) or not all(b.get(k) is not None for k in ("lat", "lng")):
        return 0.0
    lat1, lon1, lat2, lon2 = map(math.radians, [a["lat"], a["lng"], b["lat"], b["lng"]])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def _day_distance(points: list) -> float:
    total = 0.0
    for prev, cur in zip(points, points[1:]):
        total += _distance_km(prev, cur)
    return total


def _is_closed(item: dict, current: date) -> bool:
    """根据 note 里的“周X闭馆/闭陵”判断当天是否闭馆。"""
    note = item.get("note") or ""
    for label, weekday in CLOSED_WEEKDAYS.items():
        if (f"{label}闭馆" in note or f"{label}闭陵" in note) and current.weekday() == weekday:
            return True
    return False


def _order_stops(stops: list) -> list:
    """最近邻排序：景点 >= 3 个时减少折返（不足 3 个原样返回）。"""
    if len(stops) < 3:
        return stops
    remaining = stops[:]
    ordered = [remaining.pop(0)]
    while remaining:
        last = ordered[-1]
        nxt = min(remaining, key=lambda item: _distance_km(last, item))
        ordered.append(nxt)
        remaining.remove(nxt)
    return ordered


def _profile_for(destination: str) -> tuple[str, dict]:
    destination = destination.strip()
    for name, data in CITY_DATA.items():
        if name in destination or destination in name:
            return name, data
    profile = dict(GENERIC)
    profile["foods"] = list(GENERIC["foods"])
    profile["attractions"] = [
        {**item, "name": f"{destination}{item['name']}"} for item in GENERIC["attractions"]
    ]
    profile["hotel_area"] = f"{destination}市中心 / 交通便利区域"
    return destination, profile


def _score(item: dict, preferences: list, profile: TravelProfile) -> int:
    score = 3 if item.get("category") in preferences else 0
    if profile.companions == "family_kids" and item.get("category") == "亲子":
        score += 4
    if profile.companions == "family_elderly" and (item.get("duration") or 0) <= 2:
        score += 1
    if profile.pace == "relaxed" and (item.get("duration") or 0) >= 4:
        score -= 1
    if profile.pace == "packed" and (item.get("duration") or 0) <= 2:
        score += 1
    return score


def _candidate_pool(profile: dict, city: str, needed: int) -> list:
    """城市景点 + 通用补充景点，保证紧凑行程也有足够候选。"""
    pool = [dict(item) for item in profile["attractions"]]
    seen = {item["name"] for item in pool}
    index = 0
    while len(pool) < needed:
        base = dict(GENERIC["attractions"][index % len(GENERIC["attractions"])])
        base["name"] = f"{city}{base['name']}"
        base["ticket"] = 0
        base["lat"] = None
        base["lng"] = None
        if base["name"] in seen:
            base["name"] = f"{base['name']}（{index + 1}）"
        seen.add(base["name"])
        pool.append(base)
        index += 1
    return pool


def _pick_attractions(pool: list, used: set, current: date, count: int, preferences: list, profile: TravelProfile, city: str):
    """当天开放景点；优先未使用，其次复用；不足时用城市漫步补齐。"""
    warnings = []
    closed = [item for item in pool if _is_closed(item, current)]
    if closed:
        warnings.append("已避开闭馆：" + "、".join(item["name"] for item in closed[:3]))

    def sort_key(item):
        return (-_score(item, preferences, profile), pool.index(item))

    open_items = [item for item in pool if not _is_closed(item, current)]
    fresh = sorted([item for item in open_items if item["name"] not in used], key=sort_key)
    reused = sorted([item for item in open_items if item["name"] in used], key=sort_key)
    picked = (fresh + reused)[:count]

    while len(picked) < count:
        name = f"{city}城市漫步" if len(picked) == 0 else f"{city}街区漫步（{len(picked) + 1}）"
        picked.append({
            "name": name,
            "category": "自由",
            "duration": 2,
            "ticket": 0,
            "area": "市区",
            "note": "临时发现的小店与街区，作为机动安排",
            "lat": None,
            "lng": None,
        })
    return _order_stops(picked), warnings


def _indoor_alternative(pool: list, current: dict) -> str:
    for item in pool:
        if item["name"] == current["name"]:
            continue
        if any(word in item["name"] for word in INDOOR_WORDS):
            return item["name"]
    return "当地博物馆 / 大型商场（雨天备选）"


def _attraction_reason(item: dict, preferences: list, profile: TravelProfile, first: bool) -> str:
    parts = []
    matched = [pref for pref in preferences if pref and pref == item.get("category")]
    if matched:
        parts.append(f"符合{'、'.join(matched)}偏好")
    if profile.companions == "family_kids" and item.get("category") == "亲子":
        parts.append("适合亲子")
    if profile.companions == "couple":
        parts.append("适合两人慢慢逛")
    if profile.companions == "family_elderly":
        parts.append("步行强度相对可控" if (item.get("duration") or 0) <= 3 else "可分段游览并留出休息")
    if profile.pace == "relaxed":
        parts.append("节奏不赶")
    if first:
        parts.append("上午光线好、人相对少")
    if not parts:
        parts.append("当地经典去处")
    return "；".join(parts)


def _dietary_note(dietary: list) -> str:
    labels = {
        "vegetarian": "素食，点单时确认无肉、无荤油",
        "halal": "清真饮食，请确认清真标识",
        "no_spicy": "不辣，请店家少辣或去辣",
        "no_seafood": "不吃海鲜，注意汤底与酱料",
        "nut_allergy": "坚果过敏，务必提前告知店家",
    }
    notes = [labels[item] for item in dietary if item in labels]
    return "；".join(notes)


def _foods_for(city: str, profile: dict, dietary: list) -> list:
    foods = list(profile.get("foods") or [])
    words = set(dietary)
    if "vegetarian" in words:
        foods = [f"{city}素食餐厅", "寺院素斋", "菌菇豆腐家常菜"]
    elif "halal" in words:
        foods = [f"{city}清真餐厅", "兰州牛肉面", "新疆餐厅"]
    else:
        if "no_spicy" in words:
            foods = [item for item in foods if not any(word in item for word in SPICY_WORDS)]
        if "no_seafood" in words:
            foods = [item for item in foods if not any(word in item for word in SEAFOOD_WORDS)]
        if not foods:
            foods = ["清汤面 / 粥铺", "蒸菜馆", "家常菜馆"]
    if not foods:
        foods = ["当地特色菜（点单前说明忌口）"]
    return foods


def _buffer_min(profile: TravelProfile) -> int:
    buffer = BUFFER_BASE.get(profile.transport, 30)
    if profile.companions == "family_elderly":
        buffer += 10
    if profile.companions == "family_kids":
        buffer += 5
    if profile.pace == "relaxed":
        buffer += 5
    if "avoid_long_walk" in profile.accessibility or "step_free" in profile.accessibility:
        buffer += 5
    return min(buffer, 60)


def _transport_note(profile: TravelProfile, buffer: int) -> str:
    if profile.transport == "public":
        base = f"地铁 + 步行为主，景点间预留 {buffer}–{buffer + 10} 分钟"
    elif profile.transport == "taxi":
        base = f"打车为主，高峰时段预留 {buffer + 10} 分钟等车与拥堵"
    elif profile.transport == "drive":
        base = f"自驾为主，预留 {buffer + 15} 分钟停车与拥堵时间"
    else:
        base = "步行为主，单段控制在 20 分钟内，远距离改打车"
    if "step_free" in profile.accessibility or "elevator" in profile.accessibility:
        base += "；优先电梯与无障碍通道"
    if "avoid_long_walk" in profile.accessibility:
        base += "；减少连续步行"
    return base


def _meal_item(city: str, foods: list, slot_index: int, meal: str, time_text: str, duration: str, cost: int, dietary: list) -> dict:
    food = foods[slot_index % len(foods)]
    note = f"参考人均 ¥{cost}，以商家为准"
    diet_note = _dietary_note(dietary)
    if diet_note:
        note += "；" + diet_note
    return {
        "id": "",
        "type": "meal",
        "name": f"{meal} · {food}",
        "title": f"{meal} · {food}",
        "time": time_text,
        "duration": duration,
        "note": note,
        "cost": cost,
        "cost_estimated": True,
        "lat": None,
        "lng": None,
        "address": f"{city}（就近选择，具体门店参考导航）",
        "reason": "按你的忌口与预算筛选" if dietary else "本地口味推荐",
        "indoor_alternative": "",
        "navigation_url": search_url(food, city),
        "external_url": external_url("food", food, city),
    }


def _build_days(city: str, start: date, days: int, profile_data: dict, profile: TravelProfile, preferences: list, travelers: int, level: str, pool: list) -> tuple:
    per_day = PACE_ATTRACTIONS.get(profile.pace, 2)
    foods = _foods_for(city, profile_data, profile.dietary)
    hotel_night = round(profile_data["hotel_base"] * HOTEL_MULT[level])
    rooms = max(1, math.ceil(travelers / 2))
    buffer = _buffer_min(profile)
    transport_note = _transport_note(profile, buffer)
    used = set()
    payload = []
    tickets_per_day = []

    for index in range(days):
        current = start + timedelta(days=index)
        weather = get_weather(city, current)
        today, warnings = _pick_attractions(pool, used, current, per_day, preferences, profile, city)
        items = []
        tickets = 0

        # 早间交通 / 缓冲
        items.append({
            "id": "",
            "type": "transport",
            "name": f"前往第一站 · {TRANSPORT_LABEL.get(profile.transport, '地铁')}",
            "title": f"前往第一站 · {TRANSPORT_LABEL.get(profile.transport, '地铁')}",
            "time": "08:30",
            "duration": f"{buffer}min",
            "note": transport_note + "；实际路况以导航为准",
            "cost": TRANSPORT_COST.get(profile.transport, 5),
            "cost_estimated": True,
            "lat": None,
            "lng": None,
            "address": "",
            "reason": "为第一站预留通勤与缓冲",
            "indoor_alternative": "",
            "navigation_url": "",
            "external_url": "",
        })

        for slot, attraction in enumerate(today):
            used.add(attraction["name"])
            if slot >= per_day:
                break
            tickets += attraction.get("ticket") or 0
            time_text = ["09:00", "13:30", "16:00"][slot]
            duration = attraction.get("duration") or 2
            note = attraction.get("note") or ""
            if attraction.get("ticket"):
                note = (note + "；" if note else "") + f"门票参考 ¥{attraction['ticket']}，以景区为准"
            item = {
                "id": "",
                "type": "attraction",
                "name": attraction["name"],
                "title": attraction["name"],
                "time": time_text,
                "duration": f"{duration}h",
                "note": f"{attraction.get('area') or '市区'} · {note}" if note else (attraction.get("area") or "市区"),
                "cost": attraction.get("ticket") or 0,
                "cost_estimated": bool(attraction.get("ticket")),
                "lat": attraction.get("lat"),
                "lng": attraction.get("lng"),
                "address": f"{city}{attraction.get('area') or '市区'}（参考地址，以导航为准）",
                "reason": _attraction_reason(attraction, preferences, profile, slot == 0),
                "indoor_alternative": _indoor_alternative(pool, attraction),
                "navigation_url": navigation_url(
                    attraction["name"], attraction.get("lat"), attraction.get("lng"), city
                ),
                "external_url": external_url("attraction", attraction["name"], city),
            }
            items.append(item)
            if weather.get("rain_prob", 0) >= 50:
                warnings.append(f"{attraction['name']} 为户外/半户外，降雨概率 {weather['rain_prob']}%，可改用室内备选：{item['indoor_alternative']}")

        lunch_cost = 30 if level == "经济" else 50 if level == "舒适" else 80
        dinner_cost = 50 if level == "经济" else 70 if level == "舒适" else 120
        items.append(_meal_item(city, foods, index * 2, "午餐", "12:00", "1h", lunch_cost, profile.dietary))
        dinner_time = "17:30" if profile.companions in ("family_kids", "family_elderly") else "18:30"
        items.append(_meal_item(city, foods, index * 2 + 1, "晚餐", dinner_time, "1.5h", dinner_cost, profile.dietary))

        if profile.pace != "packed" and (
            profile.pace == "relaxed"
            or profile.companions in ("family_kids", "family_elderly")
            or "avoid_long_walk" in profile.accessibility
        ):
            items.append({
                "id": "",
                "type": "rest",
                "name": "午后休息 / 咖啡时间",
                "title": "午后休息 / 咖啡时间",
                "time": "16:00",
                "duration": "45min",
                "note": "找一处咖啡馆或公园长椅，补充体力",
                "cost": 30,
                "cost_estimated": True,
                "lat": None,
                "lng": None,
                "address": f"{city}（就近选择）",
                "reason": "按同行人与节奏安排休息",
                "indoor_alternative": "",
                "navigation_url": "",
                "external_url": "",
            })

        items.sort(key=lambda item: item["time"])

        if index < days - 1:
            items.append({
                "id": "",
                "type": "lodging",
                "name": f"返回住宿区 · {profile_data['hotel_area']}",
                "title": f"返回住宿区 · {profile_data['hotel_area']}",
                "time": "21:00",
                "duration": "—",
                "note": f"每间夜参考 ¥{hotel_night}，价格以平台为准；建议住 {profile_data['hotel_area']}",
                "cost": hotel_night,
                "cost_estimated": True,
                "lat": None,
                "lng": None,
                "address": profile_data["hotel_area"],
                "reason": "交通便利，减少次日通勤",
                "indoor_alternative": "",
                "navigation_url": search_url(profile_data["hotel_area"], city),
                "external_url": external_url("lodging", profile_data["hotel_area"], city),
            })
        else:
            items.append({
                "id": "",
                "type": "transport",
                "name": "返程 / 前往车站机场",
                "title": "返程 / 前往车站机场",
                "time": "16:30",
                "duration": f"{buffer}min",
                "note": "按车次/航班时间提前出发，价格与时刻以官方为准",
                "cost": TRANSPORT_COST.get(profile.transport, 5),
                "cost_estimated": True,
                "lat": None,
                "lng": None,
                "address": "",
                "reason": "为返程预留交通缓冲",
                "indoor_alternative": "",
                "navigation_url": "",
                "external_url": "",
            })

        items.sort(key=lambda item: item["time"])
        for number, item in enumerate(items, start=1):
            item["id"] = f"d{index + 1}-{number}"

        tickets_per_day.append(tickets)
        stops = [item for item in items if item.get("lat") is not None and item.get("lng") is not None]
        distance = _day_distance(stops)
        nights_here = 1 if index < days - 1 else 0
        spend = (
            tickets * travelers
            + FOOD_DAY[level] * travelers
            + TRANSPORT_DAY[level] * travelers
            + hotel_night * rooms * nights_here
        )

        if weather.get("rain_prob", 0) >= 50:
            warnings.append("可能降雨，带伞并优先室内备选")
        if weather.get("temp_max", 0) >= 35:
            warnings.append("高温时段减少正午户外活动，注意补水")

        payload.append({
            "date": current.isoformat(),
            "weekday": WEEKDAYS[current.weekday()],
            "theme": _theme(today),
            "weather": weather,
            "clothing": clothing_advice(
                weather, profile.pace, profile.companions, profile.accessibility
            ),
            "lodging_area": profile_data["hotel_area"],
            "transport_note": transport_note,
            "buffer_min": buffer,
            "meal_windows": [
                {"type": "lunch", "start": "12:00", "end": "13:00"},
                {"type": "dinner", "start": dinner_time, "end": "20:00" if dinner_time == "18:30" else "19:00"},
            ],
            "items": items,
            "warnings": warnings,
            "distance_km": round(distance, 1),
            "spend": spend,
        })

    return payload, tickets_per_day


def _theme(items: list) -> str:
    categories = []
    for item in items:
        category = item.get("category")
        if category and category not in categories:
            categories.append(category)
    return "、".join(categories) if categories else "城市漫步"


def _calc_budget(profile_data: dict, days: int, travelers: int, level: str, tickets_per_day: list) -> dict:
    nights = max(0, days - 1)
    rooms = max(1, math.ceil(travelers / 2))
    hotel_night = round(profile_data["hotel_base"] * HOTEL_MULT[level])
    hotel_total = hotel_night * rooms * nights
    food_total = FOOD_DAY[level] * travelers * days
    ticket_total = sum(tickets_per_day) * travelers
    transport_total = TRANSPORT_DAY[level] * travelers * days
    subtotal = hotel_total + food_total + ticket_total + transport_total
    buffer = round(subtotal * 0.15)
    total = subtotal + buffer
    return {
        "level": level,
        "hotel_night": hotel_night,
        "nights": nights,
        "hotel": hotel_total,
        "food": food_total,
        "tickets": ticket_total,
        "transport": transport_total,
        "buffer": buffer,
        "total": total,
        "per_person": round(total / travelers),
    }


def _season_tip(month: int) -> str:
    if month in (3, 4, 5):
        return "春季早晚温差大，带一件薄外套，并留意花粉。"
    if month in (6, 7, 8):
        return "夏季炎热多雨，备好防晒、雨具和补水。"
    if month in (9, 10, 11):
        return "秋季适合出行，热门景点仍建议错峰。"
    return "冬季注意保暖，部分户外景点可能缩短开放时间。"


def _packing(city: str, profile: TravelProfile, weather: dict, days: int, level: str) -> dict:
    categories = []
    ids = [
        ("身份证", True, "入住/预约/购票"),
        ("预约凭证/截图", True, "热门场馆需实名预约"),
        ("少量现金", False, "小店或应急使用"),
    ]
    if profile.transport == "drive":
        ids.append(("驾驶证", True, "自驾取车/租车"))
    if profile.companions == "family_elderly":
        ids.append(("老年证", False, "部分景点有优惠"))
    if profile.companions == "family_kids":
        ids.append(("儿童证件/户口本", False, "购票或入住可能需要"))
    categories.append({
        "name": "证件",
        "items": [{"name": name, "required": required, "reason": reason} for name, required, reason in ids],
    })

    clothes = [("换洗衣物", True, f"{days} 天行程")]
    tmax = weather.get("temp_max") or 20
    tmin = weather.get("temp_min") or 10
    if tmax <= 5:
        clothes.append(("羽绒服/厚外套", True, "气温较低"))
    elif tmax <= 12:
        clothes.append(("厚外套", True, "早晚偏冷"))
    elif tmin <= 8:
        clothes.append(("薄外套", False, "早晚温差大"))
    if tmax >= 30:
        clothes.append(("防晒衣/遮阳帽", False, "紫外线较强"))
    if weather.get("rain_prob", 0) >= 40:
        clothes.append(("折叠伞/轻便雨衣", True, f"降雨概率 {weather.get('rain_prob')}%"))
    clothes.append(("舒适步行鞋", True, "每天步行较多"))
    if profile.companions == "family_elderly" or "avoid_long_walk" in profile.accessibility:
        clothes.append(("防滑鞋", True, "减少湿滑路面风险"))
    categories.append({
        "name": "衣物",
        "items": [{"name": name, "required": required, "reason": reason} for name, required, reason in clothes],
    })

    categories.append({
        "name": "电子",
        "items": [
            {"name": "手机充电器", "required": True, "reason": "每天导航与预约"},
            {"name": "充电宝", "required": True, "reason": "户外时间长"},
            {"name": "相机", "required": False, "reason": "按需携带"},
        ],
    })

    health = [
        ("常用药", True, "个人长期用药"),
        ("创可贴/消毒湿巾", False, "小擦伤处理"),
    ]
    if profile.dietary:
        health.append(("肠胃药", False, "饮食变化或忌口沟通时备用"))
    if profile.transport in ("taxi", "drive") or days >= 5:
        health.append(("晕车药", False, "长途或山路备用"))
    categories.append({
        "name": "健康",
        "items": [{"name": name, "required": required, "reason": reason} for name, required, reason in health],
    })

    extra = []
    if profile.companions == "family_kids":
        extra += [
            ("儿童零食/水杯", False, "补充能量"),
            ("湿巾/纸巾", True, "亲子出行常用"),
        ]
    if "step_free" in profile.accessibility or "elevator" in profile.accessibility:
        extra.append(("无障碍路线截图", False, "提前确认电梯与坡道"))
    if "avoid_long_walk" in profile.accessibility:
        extra.append(("折叠凳/拐杖", False, "随时休息"))
    extra.append(("水杯", False, f"{city}气候干燥/炎热时补水"))
    categories.append({
        "name": "其他",
        "items": [{"name": name, "required": required, "reason": reason} for name, required, reason in extra],
    })

    notes = ["价格为参考估算，营业时间与门票以景区/商家公告为准。"]
    if profile.dietary:
        notes.append("已按忌口调整用餐建议，点单前请再次与店家确认。")
    if weather.get("source") == "fallback":
        notes.append("天气为季节规则估算，出发前请查看最新预报。")
    return {"categories": categories, "notes": notes}


def _emergency(city: str) -> dict:
    return {
        "numbers": [
            {"name": "报警", "number": "110"},
            {"name": "急救", "number": "120"},
            {"name": "火警", "number": "119"},
            {"name": "交通事故", "number": "122"},
        ],
        "hospital": {
            "name": f"{city}就近医院（导航搜索）",
            "address": "请用地图搜索最近的医院/急诊",
            "navigation_url": search_url("医院", city),
        },
    }


def build_plan(destination: str, start_date: date, end_date: date, budget: float, travelers: int, preferences: list, profile: TravelProfile | None = None) -> dict:
    if end_date < start_date:
        raise ValueError("返程日期不能早于出发日期")
    days = (end_date - start_date).days + 1
    if days > 10:
        raise ValueError("单次最多规划 10 天，更长的行程请拆成多段")

    profile = profile or TravelProfile()
    if isinstance(profile, dict):
        profile = TravelProfile(**profile)
    city, profile_data = _profile_for(destination)
    preferences = [item for item in preferences if item]
    level = LODGING_LEVEL.get(profile.lodging_budget, "舒适")

    needed = days * PACE_ATTRACTIONS.get(profile.pace, 2) + 3
    pool = _candidate_pool(profile_data, city, needed)

    day_payload = []
    budget_payload = {}
    tickets_per_day = []
    for attempt in range(3):
        day_payload, tickets_per_day = _build_days(
            city, start_date, days, profile_data, profile, preferences, travelers, level, pool
        )
        budget_payload = _calc_budget(profile_data, days, travelers, level, tickets_per_day)
        if budget_payload["total"] <= budget or level == "经济":
            break
        level = LEVELS[max(0, LEVELS.index(level) - 1)]

    remaining = round(budget - budget_payload["total"])
    budget_payload.update({"budget": round(budget), "remaining": remaining})

    first_weather = day_payload[0]["weather"] if day_payload else get_weather(city, start_date)
    packing = _packing(city, profile, first_weather, days, level)

    tips = list(profile_data.get("tips") or [])
    tips.append("热门景点通常需要提前 1–7 天实名预约，出发前再确认开放时间。")
    tips.append(_season_tip(start_date.month))
    if profile.dietary:
        tips.append("点单前说明忌口：" + _dietary_note(profile.dietary) + "。")
    if profile.accessibility:
        tips.append("无障碍设施以景区现场为准，建议出发前电话确认电梯/坡道开放情况。")
    if profile.transport == "public":
        tips.append("地铁末班时间通常在 22:30–23:30，夜归建议打车。")
    if profile.companions == "family_kids":
        tips.append("亲子行程每天留出午休或自由活动时间，避免连续赶路。")
    if profile.companions == "family_elderly":
        tips.append("带长辈出行优先电梯、少爬坡，随身携带常用药。")
    if remaining < 0:
        tips.append(f"当前方案超出预算约 {abs(remaining)} 元，可降低酒店档位或减少付费景点。")
    elif remaining > budget * 0.3:
        tips.append(f"预算还有约 {remaining} 元余量，可以升级一晚酒店或增加一个体验项目。")
    if days >= 5:
        tips.append("行程较长，建议中间留半天机动时间，避免每天赶路。")
    tips.append("所有价格与营业时间均为参考，不提供预订或支付承诺。")

    summary = (
        f"为 {city} 规划 {days} 天 {travelers} 人的"
        f"{'、'.join(preferences) if preferences else '经典'}路线"
        f"（{COMPANION_LABEL.get(profile.companions, '出行')}，{PACE_LABEL.get(profile.pace, '适中')}节奏），"
        f"预计总花费 ¥{budget_payload['total']}，预算剩余 ¥{remaining}。"
    )

    return {
        "plan_id": str(uuid.uuid4()),
        "destination": city,
        "summary": summary,
        "days": day_payload,
        "budget": budget_payload,
        "packing": packing,
        "emergency": _emergency(city),
        "tips": tips,
        "meta": {
            "travelers": travelers,
            "days": days,
            "preferences": preferences,
            "profile": profile.model_dump(),
            "generated_by": "rule-based-v2",
        },
    }
