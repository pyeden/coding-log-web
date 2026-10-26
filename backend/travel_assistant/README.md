# 智能旅行助手 API（P0 v2）

FastAPI 实现：旅行画像、逐日行程（天气/穿衣/住宿区域/交通缓冲/用餐窗口/室内备选）、附近 POI、打包清单、分享与反馈。规则版规划器不依赖 LLM；高德 Web 服务可选，失败自动降级。

## 运行（本地）

```bash
cd backend/travel_assistant
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8091
```

API 文档：`http://127.0.0.1:8091/docs`。生产环境仍由 nginx 反代到后端，本地调试不要占用 8090。

高德 Key 从仓库根目录 `.env` 读取（`AMAP_WEB_KEY` / `AMAP_WEB_SECRET` / `AMAP_JS_KEY` / `AMAP_SECURITY_CODE`），不会返回给前端。无 key 时所有相关接口使用静态/季节规则兜底。

## 接口

- `GET /api/travel/health`
- `POST /api/travel/plan`（兼容旧字段，新增 `profile`）
- `GET /api/travel/poi`（food/lodging/transport/emergency）
- `GET /api/travel/weather`
- `POST /api/travel/share`、`GET /api/travel/share/{id}`
- `POST /api/travel/feedback`

完整字段、枚举、示例与降级说明见 [API.md](./API.md)。

## 运行数据

- `data/travel.db`：分享（30 天 TTL）
- `data/feedback.jsonl`：反馈追加日志

两者均不提交 git；可用 `TRAVEL_DATA_DIR` 覆盖目录。

## 前端接入

页面通过 `/api/travel/*` 调用；VuePress dev server 在 `docs/.vuepress/config.ts` 的 `devServer.proxy` 中把 `/api/travel` 转发到后端。生产环境由 nginx 反代。所有价格/营业时间为参考，不提供预订或支付承诺。
