# 智能旅行助手 API

《Hello-Agents》第十三章旅行助手的 FastAPI 实现。规则版规划器负责景点选择、每日行程、预算估算与提示，不依赖外部 API 密钥；后续可以在 `planner.py` 中接入 LLM、高德 MCP 或酒店/机票接口。

## 运行

```bash
cd backend/travel_assistant
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8090
```

API 文档：`http://127.0.0.1:8090/docs`

## 接口

- `GET /api/travel/health`
- `POST /api/travel/plan`

请求示例：

```json
{
  "destination": "北京",
  "start_date": "2026-11-01",
  "end_date": "2026-11-03",
  "budget": 3000,
  "travelers": 2,
  "preferences": ["历史", "美食"]
}
```

## 前端接入

页面通过 `/api/travel/plan` 调用；VuePress dev server 在 `docs/.vuepress/config.ts` 的 `devServer.proxy` 中把 `/api/travel` 转发到 `127.0.0.1:8090`。生产环境如果改为静态托管，需要在 nginx 增加同样的反代。
