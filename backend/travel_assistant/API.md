# 旅行助手 API（P0 v2）

本地默认：`http://127.0.0.1:8091`。所有价格、营业时间均为**参考估算**，不提供预订/支付承诺，也不抓取第三方库存。

## 旅行画像 `TravelProfile`

`profile` 可省略，省略时使用默认值，旧请求仍兼容。

```json
{
  "companions": "couple",
  "pace": "balanced",
  "dietary": ["no_spicy"],
  "accessibility": ["elevator"],
  "transport": "public",
  "lodging_budget": "comfort"
}
```

- `companions`: `solo` | `couple` | `friends` | `family_kids` | `family_elderly`
- `pace`: `relaxed` | `balanced` | `packed`
- `dietary`: `vegetarian` | `halal` | `no_spicy` | `no_seafood` | `nut_allergy`
- `accessibility`: `step_free` | `elevator` | `avoid_long_walk`
- `transport`: `public` | `taxi` | `drive` | `walk`
- `lodging_budget`: `budget` | `comfort` | `premium`

## `POST /api/travel/plan`

请求：

```json
{
  "destination": "北京",
  "start_date": "2026-11-01",
  "end_date": "2026-11-03",
  "budget": 3000,
  "travelers": 2,
  "preferences": ["历史", "美食"],
  "origin": "北京南站",
  "origin_lng": 116.38,
  "origin_lat": 39.86,
  "profile": {
    "companions": "couple",
    "pace": "balanced",
    "dietary": ["no_spicy"],
    "accessibility": ["elevator"],
    "transport": "public",
    "lodging_budget": "comfort"
  }
}
```

响应包含：

- `plan_id`、`summary`
- `days[]`：`date`、`weekday`、`theme`、`weather`、`clothing`、`lodging_area`、`transport_note`、`buffer_min`、`meal_windows`、`items[]`、`warnings[]`
- `items[]`：`id`、`type`（`attraction` | `meal` | `lodging` | `transport` | `rest`）、`name`、`time`、`duration`、`note`、`cost`、`lat`、`lng`、`address`、`reason`、`indoor_alternative`、`navigation_url`、`external_url`
- `budget`：`budget`、`total`、`remaining`、`hotel`、`food`、`transport`、`tickets`、`buffer`、`level`、`per_person`
- `packing`：`categories[]`、`notes[]`
- `emergency`：`numbers[]`、`hospital`
- `tips[]`
- `meta`：`travelers`、`days`、`preferences`、`profile`、`generated_by`

保证：每天至少 2 个 `attraction`、至少 1 个 `meal`、至少 1 条 `transport`；`clothing`、`lodging_area`、每个景点的 `indoor_alternative` 非空。天气超出高德预报范围时自动使用季节规则（`source=fallback`）。

示例（截取）：

```json
{
  "plan_id": "0d6f...",
  "summary": "为 北京 规划 3 天 2 人的历史、美食路线（情侣/夫妻，适中节奏），预计总花费 ¥2645，预算剩余 ¥355。",
  "days": [{
    "date": "2026-11-01",
    "weekday": "周日",
    "theme": "历史、美食",
    "weather": {"text": "晴冷", "temp_min": 2, "temp_max": 14, "rain_prob": 15, "uv": "弱", "source": "fallback"},
    "clothing": "长袖 + 薄外套，舒适步行鞋。",
    "lodging_area": "东城区 / 王府井",
    "transport_note": "地铁 + 步行为主，景点间预留 30–40 分钟；优先电梯与无障碍通道",
    "buffer_min": 30,
    "meal_windows": [{"type": "lunch", "start": "12:00", "end": "13:00"}],
    "items": [{"type": "attraction", "name": "故宫博物院", "time": "09:00", "duration": "3h", "cost": 60, "indoor_alternative": "国家博物馆", "navigation_url": "https://uri.amap.com/..."}],
    "warnings": []
  }],
  "budget": {"budget": 3000, "total": 2645, "remaining": 355, "hotel": 1040, "food": 720, "transport": 300, "tickets": 240, "buffer": 345},
  "packing": {"categories": [{"name": "证件", "items": [{"name": "身份证", "required": true, "reason": "入住/预约/购票"}]}], "notes": []},
  "emergency": {"numbers": [{"name": "报警", "number": "110"}], "hospital": {"name": "北京就近医院（导航搜索）", "address": "请用地图搜索最近的医院/急诊", "navigation_url": "https://uri.amap.com/..."}},
  "tips": ["所有价格与营业时间均为参考，不提供预订或支付承诺。"],
  "meta": {"travelers": 2, "days": 3, "preferences": ["历史", "美食"], "profile": {}, "generated_by": "rule-based-v2"}
}
```

## `GET /api/travel/poi`

Query：

- `category`（必填）：`food` | `lodging` | `transport` | `emergency`
- `lat`、`lng`（必填，WGS-84；服务端转为高德坐标）
- `radius`：默认 1500，最大 5000
- `destination`：城市名（兜底用）
- `dietary`：逗号分隔，如 `no_spicy,vegetarian`
- `budget`：人均预算（可选）
- `limit`：默认 6，最大 12

响应：

```json
{
  "source": "amap",
  "items": [{
    "id": "poi-1",
    "category": "food",
    "name": "四季民福烤鸭店",
    "type": "北京菜",
    "address": "东城区南池子大街",
    "distance_m": 620,
    "rating": "4.7",
    "cost": 150,
    "cost_estimated": true,
    "open_status": "营业时间参考商家",
    "lat": 39.91,
    "lng": 116.40,
    "reason": "步行约 8 分钟 · 评分 4.7（参考）",
    "navigation_url": "https://uri.amap.com/...",
    "external_url": "https://www.dianping.com/search/keyword/2/0_..."
  }],
  "notice": "",
  "emergency_numbers": []
}
```

无 key、AMap 失败、QPS 超限或空结果时返回 `source=fallback` 与静态推荐，HTTP 仍为 200。紧急类兜底包含 110/120/119/122 电话卡。

## `GET /api/travel/weather`

Query：`destination`、`date`（YYYY-MM-DD）。

```json
{"text": "晴", "temp_min": 6, "temp_max": 17, "rain_prob": 5, "uv": "中等", "source": "amap"}
```

无 key、请求失败或日期超出 4 天预报范围时返回季节规则兜底，`source=fallback`，HTTP 200。

## `POST /api/travel/share`

请求：`{"plan": { ...完整 plan... }}` → `{"id": "m8g7r5xt"}`（8 位短 id）。

存储：`backend/travel_assistant/data/travel.db`，表 `shares(id, payload, created_at)`，读取时判断 30 天 TTL。数据文件已加入 `.gitignore`。限制 512 KB。

## `GET /api/travel/share/{id}`

返回保存的 plan JSON；不存在或超过 30 天返回 404。

## `POST /api/travel/feedback`

```json
{"plan_id": "uuid", "item_id": "d1-2", "helpful": true, "visited": true, "note": ""}
```

追加到 `backend/travel_assistant/data/feedback.jsonl`，返回 `{"ok": true}`。只记录上述字段与时间戳，不收集姓名/手机号等 PII。

## 降级与限制

- AMap Web 服务失败/无 key：plan 天气、weather、poi 均降级，不返回 5xx。
- 分享/反馈写入失败才返回 500；非法参数返回 400/413/422。
- 所有价格、门票、营业时间均为参考，前端需标注「参考/estimated」。
