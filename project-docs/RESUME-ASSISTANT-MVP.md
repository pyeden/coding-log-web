# 简历维护助手 MVP 规格（v1）

## 目标与范围

在博客项目页新增「简历维护助手」入口；页面展示由知识库生成的正式技术简历；每月 1 号自动重建，也支持手动触发。简历是可公开版本，只写知识库中有依据的事实，缺项标注「知识库未收录」，不编造经历。

- 知识库：`/Users/mac/resume-kb`（profile.md / skills.md / projects.md，可选 experience.md / education.md / honors.md）
- 站点知识库：博客 `docs/**/*.md` 的文章与分类统计（项目/文章数量、系列）
- 服务：新增 FastAPI `backend/resume_assistant`，生产端口 8092
- 前端：`/projects/resume/` 页面 + 项目页卡片 + 导航项

## 数据契约 `ResumeDocument`

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-11-04T10:45:00+08:00",
  "source": {
    "knowledge_base": "resume-kb+blog-docs",
    "source_hash": "<sha256 hex>",
    "article_count": 394,
    "kb_files": ["profile.md", "skills.md", "projects.md"]
  },
  "profile": {
    "name": "三木先生",
    "title": "软件工程师",
    "summary": "...",
    "links": [{"label": "GitHub", "url": "https://github.com/pyeden"}],
    "directions": ["软件工程", "..."]
  },
  "skills": [{"group": "编程语言", "items": ["Go", "..."]}],
  "projects": [{"name": "PanguVerse", "role": "作者", "period": "2026", "summary": "...", "tech": ["Python"], "link": "...", "highlights": ["..."]}],
  "experience": [],
  "education": [],
  "honors": [],
  "writing": {"article_count": 394, "series": [{"name": "AI技术", "count": 54}]},
  "missing": ["工作经历", "教育经历"]
}
```

- `missing` 列出 KB 未提供的栏目；前端显示为「知识库未收录」。
- 禁止输出手机号、私人邮箱等未在 KB 中明确要求公开的联系方式；当前 KB 只有 GitHub 与站点链接。
- JSON 使用 UTF-8、`ensure_ascii=false`、键顺序稳定；`source_hash` 覆盖 KB 文件内容 + 文章 permalink 列表。

## API 契约

- `GET /api/resume/health` → `200 {"status":"ok","service":"resume-assistant","version":"1.0.0"}`
- `GET /api/resume/latest` → `200 ResumeDocument`；无快照时即时生成并缓存；KB 缺文件不报 500
- `GET /api/resume/status` → `200 {"generated_at","source_hash","article_count","kb_files","missing","next_scheduled_at"}`
- `POST /api/resume/refresh`
  - Header `X-Resume-Token: <token>`，token 来自环境变量 `RESUME_REFRESH_TOKEN` 或文件 `RESUME_TOKEN_FILE`（默认 `/Users/mac/resume-kb/.refresh_token`）
  - `200 {"ok":true,"generated_at","changed":bool,"source_hash"}`
  - `401 {"detail":"unauthorized"}`；`429 {"detail":"too_frequent"}`（30 秒内重复触发）
- `GET /api/resume/latest` 响应头 `Cache-Control: no-store`。
- CORS：允许 `https://seres-ai.com`、`http://127.0.0.1:8080`、`http://localhost:8080`。

## 生成规则

- 环境变量：`RESUME_KB_DIR`（默认 `/Users/mac/resume-kb`）、`BLOG_DOCS_DIR`（默认 `/Users/mac/coding-log-web/docs`）、`RESUME_DATA_DIR`（默认服务目录 `data`）。
- `profile.md`：`key: value`；`directions:` 为缩进列表；`github`/`site` 生成 links。
- `skills.md`：`## 分组` + `- 条目`。
- `projects.md`：每个 `## 名称` 一段；字段 `role`/`period`/`summary`/`tech`/`link`；`highlights:` 缩进列表。
- `experience.md` / `education.md`：格式同 projects；`honors.md` 为 `- 条目`。
- 博客统计：扫描 `docs/**/*.md`，frontmatter 含 `permalink` 计一篇文章；`categories` 计数取前 12 个系列。
- `projects` 合并 KB 项目与 `docs/08.项目/*.md` 中未在 KB 出现的项目（只取 title/permalink，摘要留空，避免编造）。
- 原子写 `data/resume.json`；生成失败保留上一版并返回 500 + 原因。

## 文件归属

- coder：`backend/resume_assistant/**`（app.py / generator.py / models.py / tests / README / requirements）
- ui：`docs/08.项目/03.简历维护助手.md`、`docs/.vuepress/components/ResumeAssistant.vue`、`docs/.vuepress/components/ProjectShowcase.vue`、`docs/.vuepress/config.ts`（仅项目导航）
- pm：本规格、`project-docs/ops/*`、部署与 nginx

双方只 `git add` 自己的文件，不 push，不部署，不重启生产服务。

## 验收标准（QA 按此逐项）

1. health 200 且 service=resume-assistant。
2. latest：schema_version=1.0；profile.name=三木先生；directions 含「软件工程」；skills≥5 组；projects≥3；writing.article_count>300；source_hash 为 64 位 hex；experience/education 为空且 missing 含「工作经历」「教育经历」。
3. refresh 无 token=401；错 token=401；对 token=200；30 秒内重复=429；成功后 generated_at 变化。
4. 相同输入两次生成的 source_hash 相同，除 generated_at 外内容一致。
5. 在 KB 追加一条技能后 refresh，latest 含该条目；删除后恢复。
6. latest 与页面不含手机号/私人邮箱；不出现未在 KB 中的公司、学校、奖项。
7. `/projects/resume/` 200；项目页有卡片；导航有入口；API 正常时展示各栏目与更新时间；API 断开时展示可读错误与重试；`?admin=1` 才显示刷新面板。
8. 线上 `/api/resume/health`、`/api/resume/latest` 经 nginx 返回 200；刷新接口经线上返回 401/200 符合契约。
9. 构建成功且日志无「序号」「未获取到目录数据」；`/projects/`、`/projects/travel/`、`/projects/panguverse/`、首页不回归。
10. 每月 1 号 03:10 的定时任务已安装并可列出；token 文件权限 600。

## 部署（pm 执行）

1. MacBook 构建、提交、push、发布 release。
2. Mac mini `git pull --ff-only`；创建 venv 安装依赖；安装 LaunchDaemon `ai.openclaw.resume-api`；启动并验证 8092。
3. nginx 增加 `location /api/resume/` → 127.0.0.1:8092，`nginx -t` 后 reload。
4. 安装 `ai.openclaw.resume-refresh` 日历任务（每月 1 号 03:10）与 token。
