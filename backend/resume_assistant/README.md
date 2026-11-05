# 简历维护助手 API

由简历知识库（`/Users/mac/resume-kb`）与博客文章元数据生成可公开的正式简历 JSON。
简历只发布知识库中有依据的事实；缺失栏目写入 `missing`，由前端显示为「知识库未收录」，不会编造公司、学校、奖项或经历。

## 目录

```
backend/resume_assistant/
├── app.py          # FastAPI 应用与刷新/鉴权/限流
├── generator.py    # 确定性生成、解析、哈希、原子写
├── models.py       # ResumeDocument schema 1.1
├── requirements.txt
├── tests/
└── data/resume.json  # 运行时快照（已 gitignore）
```

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `RESUME_KB_DIR` | `/Users/mac/resume-kb` | 知识库目录 |
| `BLOG_DOCS_DIR` | `/Users/mac/coding-log-web/docs` | 博客 `docs` 目录 |
| `RESUME_DATA_DIR` | 服务目录下 `data/` | 快照输出目录 |
| `RESUME_REFRESH_TOKEN` | 无 | 刷新 token；优先于 token 文件 |
| `RESUME_TOKEN_FILE` | `$RESUME_KB_DIR/.refresh_token` | token 文件（建议权限 600） |
| `RESUME_REFRESH_INTERVAL_SECONDS` | `30` | 刷新限流窗口，仅用于测试调优 |

## 接口

- `GET /api/resume/health` → `{"status":"ok","service":"resume-assistant","version":"1.0.0"}`
- `GET /api/resume/latest` → `ResumeDocument`；无快照时即时生成并缓存；`Cache-Control: no-store`
- `GET /api/resume/status` → `generated_at` / `source_hash` / `article_count` / `kb_files` / `missing` / `next_scheduled_at`
- `POST /api/resume/refresh`，Header `X-Resume-Token`
  - `200 {"ok":true,"generated_at","changed","source_hash"}`
  - `401 {"detail":"unauthorized"}`
  - `429 {"detail":"too_frequent"}`（30 秒内重复触发）
  - `500 {"detail":"generation_failed","reason":"..."}`，失败时保留上一版快照

CORS 允许 `https://seres-ai.com`、`http://127.0.0.1:8080`、`http://localhost:8080`。

## 生成规则

- 读取 `profile.md`、`skills.md`、`projects.md`，以及可选的 `experience.md`、`education.md`、`honors.md`。
- `profile.md` 只取 `name` / `title` / `summary` / `github` / `site` / `directions`；不会输出邮箱、手机号等字段。
- `skills.md` 每个 `## 分组` 下的 `- 条目` 可带分值：`- Python | 95`。分隔符为半角 `|`，按最后一个 `|` 切分（名称本身可含其他 `|`）；右侧仅当匹配 `^\d{1,3}$` 且 `0 <= n <= 100` 时作为分值，否则整行作为名称、分值记 `0`。名称与分值均去除首尾空白。
- 技能输出为 `{"group": "编程语言", "items": ["Python", "Go"], "levels": [95, 80]}`：`items` 保持字符串数组（兼容旧前端），`levels` 与 `items` 等长，无分值补 `0`。
- 博客扫描 `docs/**/*.md`：frontmatter 含 `permalink` 计为一篇文章；`categories` 取前 12 个系列。
- `docs/08.项目/*.md` 中未在知识库出现的项目只补 `title` + `permalink`，摘要等留空。
- `source_hash` 覆盖所有 KB 文件内容（含缺失标记）与排序后的 permalink 列表；相同输入除 `generated_at` 外输出完全一致。
- 快照通过临时文件 + `os.replace` 原子写入 `data/resume.json`。

## 技能分值格式

```md
## 编程语言
- Python | 95
- Go | 80
- TypeScript / JavaScript | 75
- 无分值条目
```

- 分值范围 0–100 的整数；`0` 表示无分值，前端对整组无正分值时回退为 chips。
- 非法分值（如 `101`、`abc`、空值）不会报错：整行按技能名称处理，分值 `0`。
- 名称允许包含括号、斜杠等符号，例如 `- MySQL（含 Binlog 双向同步）| 88`。

## 本地运行

```bash
cd backend/resume_assistant
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 生产端口
cd .. && RESUME_REFRESH_TOKEN=dev-token \
  resume_assistant/.venv/bin/python -m uvicorn resume_assistant.app:app --host 127.0.0.1 --port 8092

# 本地联调端口
cd .. && BLOG_DOCS_DIR=/Users/futuredeng/clw/docs \
  RESUME_DATA_DIR=/tmp/resume-data RESUME_REFRESH_TOKEN=dev-token \
  resume_assistant/.venv/bin/python -m uvicorn resume_assistant.app:app --host 127.0.0.1 --port 8097
```

## 测试

```bash
cd backend
resume_assistant/.venv/bin/python -m pytest resume_assistant/tests -q
```

覆盖：schema 与缺文件 `missing`、确定性 `source_hash`、token 401/200、30 秒 429、
KB 追加技能反映到 latest、失败保留上一版、token 文件、CORS、隐私字段过滤、
技能分值解析（带分值 / 无分值 / 非法分值）、`levels` 与 `items` 等长、无 `levels` 旧快照兼容。

## 部署说明

生产端口 8092。nginx、LaunchDaemon `ai.openclaw.resume-api` 与每月 1 号 03:10 的定时任务
由 pm 负责，本服务只提供应用本身。
