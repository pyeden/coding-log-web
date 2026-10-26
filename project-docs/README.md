# coding-log-web 维护文档索引

这是给后续开发者/AI agent 的项目文档，**不参与站点构建**（位于 `docs/` 之外）。

## 文档地图

| 文档 | 内容 | 什么时候看 |
| --- | --- | --- |
| `ARCHITECTURE.md` | 技术栈、目录结构、路由与侧边栏生成、构建链路、部署拓扑、评论/旅行助手数据流、风险清单 | 接手项目、改动结构、排查线上问题 |
| `DEVELOPMENT.md` | 命名/frontmatter 规范、新增文章与栏目流程、主题样式、发布与排错、硬性约束 | 每次写内容或改配置前 |
| `STATIC-HOSTING-PLAN.md` | `vuepress build` + 静态托管的评估、nginx/launchd 方案、切换与回滚 | 讨论线上架构迁移时 |

## 30 秒速览

- 纯静态博客：VuePress 1.8.3 + `vuepress-theme-vdoing` 1.12.9，内容全在 `docs/`。
- 两个本地配套服务：自建 **Artalk** 评论（`127.0.0.1:23366`，SQLite `data/artalk.db`）和 **旅行助手** FastAPI（`127.0.0.1:8090`）。
- 开发：`npm run dev` → http://localhost:8080；构建：`npm run build` → `docs/.vuepress/dist`。
- 线上：Mac mini `/Users/mac/coding-log-web` 上常驻 `vuepress dev`，nginx `:8888`（TLS + proxy_protocol）按路径反代 8080/8090/23366/18789，frpc 暴露 80/443。
- 开发副本：MacBook；远端 `git@github.com:pyeden/coding-log-web.git`（`master`）。
- 固定分工：MacBook 开发 → Mac mini 部署运行；不在 Mac mini 上直接编辑。
- 侧边栏靠目录/文件名的「数字.」前缀排序；缺前缀会被跳过。
- `vdoing/` 是未启用的主题源码副本；`docs/@pages/`、`docs/.vuepress/dist/` 不要手改。
- 项目文档只放 `project-docs/`，不要放进 `docs/`。

## 端口速查

| 端口 | 服务 | 绑定 |
| --- | --- | --- |
| 8080 | VuePress dev server（当前线上） | `*:8080` |
| 8090 | 旅行助手 FastAPI（uvicorn） | `127.0.0.1:8090` |
| 23366 | Artalk 评论服务 | `127.0.0.1:23366` |
| 18789 | OpenClaw Gateway（与本博客同域不同路径） | `*:18789` |
| 8887 | nginx HTTP → 301 HTTPS | `*:8887` |
| 8888 | nginx HTTPS（ssl + proxy_protocol，frpc 目标） | `*:8888` |

## 最容易踩的六个坑

1. 改了 `vdoing/` 却没生效 —— 实际加载的是 `node_modules` 里的主题包。
2. 新增文件没加数字前缀 —— 侧边栏不显示，构建日志有 warning。
3. 修改已发布文章的 `permalink` —— 外链失效，Artalk 按页面路径关联的评论也会对不上。
4. 把维护文档写进 `docs/` —— 会被当成博客文章发布。
5. 在 nginx 里把 `/api/travel/` 放到 `/api/` 之后或删掉 —— Artalk 会接管旅行助手请求（按最长前缀匹配，`/api/travel/` 必须保留）。
6. 直接改线上 Mac mini 的文件 —— 线上是 dev server，改动立即对外生效且没有版本记录。

## 当前基线

- 核对日期：2026-10-26
- Git：`master` @ `c3874ef`（MacBook 与 Mac mini 两份副本 HEAD 一致）
- Node：v24.22.1 / npm 11.19.1；主题要求 Node >= 18
