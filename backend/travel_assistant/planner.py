"""规则版旅行规划器：景点选择、每日行程与预算估算。"""

import math
from datetime import date, timedelta
from typing import Dict, List, Tuple

from data import CITY_DATA, GENERIC

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
LEVELS = ["经济", "舒适", "品质"]
HOTEL_MULT = {"经济": 0.6, "舒适": 1.0, "品质": 1.5}
FOOD_DAY = {"经济": 100, "舒适": 180, "品质": 300}
TRANSPORT_DAY = {"经济": 40, "舒适": 70, "品质": 120}


def _distance_km(a: Dict, b: Dict) -> float:
    """两点球面距离（km），缺坐标返回 0。"""
    if not all(a.get(k) is not None for k in ("lat", "lng")) or not all(b.get(k) is not None for k in ("lat", "lng")):
        return 0.0
    lat1, lon1, lat2, lon2 = map(math.radians, [a["lat"], a["lng"], b["lat"], b["lng"]])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def _day_distance(points: List[Dict]) -> float:
    total = 0.0
    for prev, cur in zip(points, points[1:]):
        total += _distance_km(prev, cur)
    return total


def _profile_for(destination: str) -> Tuple[str, Dict]:
    destination = destination.strip()
    for name, data in CITY_DATA.items():
        if name in destination or destination in name:
            return name, data
    profile = dict(GENERIC)
    profile["attractions"] = [
        {**item, "name": f"{destination}{item['name']}"} for item in GENERIC["attractions"]
    ]
    profile["hotel_area"] = f"{destination}市中心 / 交通便利区域"
    return destination, profile


def _score(item: Dict, preferences: List[str]) -> int:
    return 3 if item["category"] in preferences else 0


def _pick_attractions(profile: Dict, preferences: List[str], count: int) -> List[Dict]:
    ordered = sorted(
        enumerate(profile["attractions"]),
        key=lambda pair: (-_score(pair[1], preferences), pair[0]),
    )
    picked = [item for _, item in ordered[:count]]
    return picked


def _theme(items: List[Dict]) -> str:
    categories = []
    for item in items:
        if item["category"] not in categories:
            categories.append(item["category"])
    return "、".join(categories) if categories else "城市漫步"


def _build_days(city: str, start: date, days: int, profile: Dict, preferences: List[str], travelers: int, food_level: str) -> Tuple[List[Dict], List[int]]:
    pool = _pick_attractions(profile, preferences, days * 2)
    foods = profile["foods"]
    payload = []
    tickets_per_day = []

    for index in range(days):
        current = start + timedelta(days=index)
        today = pool[index * 2:index * 2 + 2]
        items = []
        tickets = 0

        for slot, item in enumerate(today):
            time = "09:00" if slot == 0 else "14:00"
            tickets += item["ticket"]
            items.append({
                "time": time,
                "title": item["name"],
                "type": "景点",
                "duration": f"{item['duration']} 小时",
                "cost": item["ticket"],
                "note": f"{item['area']} · {item['note']}" if item.get("note") else item["area"],
                "lat": item.get("lat"),
                "lng": item.get("lng"),
            })

        if not today:
            items.append({
                "time": "09:00",
                "title": "自由活动 / 城市漫步",
                "type": "自由",
                "duration": "半天",
                "cost": 0,
                "note": "留给临时发现的小店和街区",
            })

        lunch = 60 if food_level == "经济" else 100 if food_level == "舒适" else 160
        dinner = 90 if food_level == "经济" else 150 if food_level == "舒适" else 240
        items.append({
            "time": "12:00",
            "title": f"午餐 · {foods[index % len(foods)]}",
            "type": "餐饮",
            "duration": "1 小时",
            "cost": lunch,
            "note": "按当地口味选择的简餐",
        })
        items.append({
            "time": "18:00",
            "title": f"晚餐 · {foods[(index + 1) % len(foods)]}",
            "type": "餐饮",
            "duration": "1.5 小时",
            "cost": dinner,
            "note": "晚餐后可就近散步",
        })

        if index < days - 1:
            items.append({
                "time": "21:00",
                "title": "返回酒店休息",
                "type": "住宿",
                "duration": "—",
                "cost": 0,
                "note": f"建议住在 {profile['hotel_area']}",
            })
        else:
            items.append({
                "time": "16:30",
                "title": "返程 / 自由活动",
                "type": "交通",
                "duration": "—",
                "cost": 0,
                "note": "根据车次或航班时间预留通勤",
            })

        items.sort(key=lambda item: item["time"])
        tickets_per_day.append(tickets)

        # 当日通勤距离（按景点顺序）
        stops = [item for item in items if item.get("lat") is not None and item.get("lng") is not None]
        distance = _day_distance(stops)

        # 当日花费：门票 + 餐饮 + 市内交通（按人）+ 当晚住宿（最后一晚不计）
        nights_here = 1 if index < days - 1 else 0
        spend = (
            tickets * travelers
            + FOOD_DAY[food_level] * travelers
            + TRANSPORT_DAY[food_level] * travelers
            + round(profile["hotel_base"] * HOTEL_MULT[food_level]) * travelers * nights_here
        )

        payload.append({
            "date": current.isoformat(),
            "weekday": WEEKDAYS[current.weekday()],
            "theme": _theme(today),
            "items": items,
            "distance_km": round(distance, 1),
            "spend": spend,
        })

    return payload, tickets_per_day


def _calc_budget(profile: Dict, days: int, travelers: int, level: str, tickets_per_day: List[int]) -> Dict:
    nights = max(0, days - 1)
    hotel_night = round(profile["hotel_base"] * HOTEL_MULT[level])
    hotel_total = hotel_night * nights
    food_total = FOOD_DAY[level] * travelers * days
    ticket_total = sum(tickets_per_day) * travelers
    transport_total = TRANSPORT_DAY[level] * travelers * days
    total = hotel_total + food_total + ticket_total + transport_total
    return {
        "level": level,
        "hotel_night": hotel_night,
        "nights": nights,
        "hotel": hotel_total,
        "food": food_total,
        "tickets": ticket_total,
        "transport": transport_total,
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


def build_plan(destination: str, start_date: date, end_date: date, budget: float, travelers: int, preferences: List[str]) -> Dict:
    if end_date < start_date:
        raise ValueError("返程日期不能早于出发日期")
    days = (end_date - start_date).days + 1
    if days > 10:
        raise ValueError("单次最多规划 10 天，更长的行程请拆成多段")

    city, profile = _profile_for(destination)
    preferences = [item for item in preferences if item]
    per_person_day = budget / (travelers * days)
    if per_person_day < 700:
        level = "经济"
    elif per_person_day < 1400:
        level = "舒适"
    else:
        level = "品质"

    day_payload, tickets_per_day = _build_days(city, start_date, days, profile, preferences, travelers, level)
    budget_payload = _calc_budget(profile, days, travelers, level, tickets_per_day)

    if budget_payload["total"] > budget and level != "经济":
        level = LEVELS[max(0, LEVELS.index(level) - 1)]
        day_payload, tickets_per_day = _build_days(city, start_date, days, profile, preferences, travelers, level)
        budget_payload = _calc_budget(profile, days, travelers, level, tickets_per_day)

    remaining = round(budget - budget_payload["total"])
    budget_payload.update({"budget": round(budget), "remaining": remaining})

    tips = list(profile["tips"])
    tips.append("热门景点通常需要提前 1–7 天实名预约，出发前再确认开放时间。")
    tips.append(_season_tip(start_date.month))
    if remaining < 0:
        tips.append(f"当前方案超出预算约 {abs(remaining)} 元，可降低酒店档位或减少付费景点。")
    elif remaining > budget * 0.3:
        tips.append(f"预算还有约 {remaining} 元余量，可以升级一晚酒店或增加一个体验项目。")
    if days >= 5:
        tips.append("行程较长，建议中间留半天机动时间，避免每天赶路。")

    summary = (
        f"为你规划了 {city} {days} 天 {travelers} 人的"
        f"{'、'.join(preferences) if preferences else '经典'}路线，"
        f"预计总花费 ¥{budget_payload['total']}，预算剩余 ¥{remaining}。"
    )

    return {
        "destination": city,
        "days": day_payload,
        "budget": budget_payload,
        "tips": tips,
        "summary": summary,
        "meta": {
            "travelers": travelers,
            "days": days,
            "preferences": preferences,
            "generated_by": "rule-based",
        },
    }
